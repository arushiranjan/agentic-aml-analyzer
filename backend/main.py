"""
backend/main.py
----------------
FastAPI application exposing the AML Suspicious Activity Detection Agent.

Architecture: Planner -> Context Builder -> Executor (see agent/planner.py,
agent/context_builder.py, tools/executor.py).

Endpoints:
  POST /upload             - upload a transaction CSV, returns dataset_id
  POST /chat                - natural language query -> agent plan -> tool results
  POST /eda                 - direct EDA-only call (bypasses the planner)
  POST /risk-report          - full risk pipeline for the whole dataset
  POST /train                - explicitly (re)train the Isolation Forest for a dataset
  GET  /customer/{id}        - drill-down details for one customer (+ history delta)
  GET  /timeline/{id}        - chronological Investigation Timeline for one customer
  GET  /history/{id}         - past risk-score snapshots for one customer
  GET  /graph/{id}           - transaction graph data (nodes/edges) for NetworkX viz
  GET  /health               - health check
"""

from __future__ import annotations
import io
import sys
import os
import logging
from typing import Optional

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.planner import build_plan
from agent.context_builder import build_context
from tools.executor import execute
from tools import eda_tool, ml_tool, timeline_tool
from utils.data_loader import register_dataset, get_dataset, latest_dataset_id
from utils import history_store, model_store
from utils.llm_client import get_llm_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AML Suspicious Activity Detection Agent",
    description="Agentic AI backend for anti-money-laundering detection.",
    version="2.0.0",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    query: str
    dataset_id: Optional[str] = None


class EDARequest(BaseModel):
    dataset_id: Optional[str] = None
    country: Optional[str] = None
    channel: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None


def _resolve_dataset(dataset_id: Optional[str]) -> pd.DataFrame:
    ds_id = dataset_id or latest_dataset_id()
    if ds_id is None:
        raise HTTPException(status_code=400, detail="No dataset uploaded yet. Call /upload first.")
    df = get_dataset(ds_id)
    if df is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{ds_id}' not found.")
    return df


def _dataset_id_or_latest(dataset_id: Optional[str]) -> str:
    return dataset_id or latest_dataset_id()


def _apply_history(dataset_id: str, risk_report: list) -> None:
    """Attaches a 'history_delta' field to each row and records a new snapshot."""
    deltas = history_store.record_batch(dataset_id, risk_report)
    for row in risk_report:
        row["history_delta"] = deltas.get(str(row["customer_id"]))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Accepts a transaction CSV and registers it in the in-memory dataset store."""
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        dataset_id = register_dataset(df)
        return {
            "dataset_id": dataset_id,
            "rows": len(df),
            "columns": list(df.columns),
            "message": "Dataset uploaded and validated successfully.",
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=f"Failed to parse CSV: {e}")


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Core agentic endpoint. Planner -> Context Builder -> Executor.
    The planner decides which tools + WHY for this specific query; the
    context builder resolves filters/customer_id; the executor runs only
    the resolved tool chain.
    """
    dataset_id = _dataset_id_or_latest(req.dataset_id)
    df = _resolve_dataset(dataset_id)
    plan = build_plan(req.query)
    context = build_context(df, filters=plan.filters, customer_id=plan.customer_id, dataset_id=dataset_id)

    results = execute(context, tools=plan.tools)

    if "risk_score" in results:
        _apply_history(dataset_id, results["risk_score"]["risk_report"])

    return {
        "query": req.query,
        "plan": {
            "goal": plan.goal,
            "steps": plan.steps,
            "tools": plan.tools,
            "filters": plan.filters,
            "customer_id": plan.customer_id,
            "reasoning": plan.reasoning,
            "source": plan.source,
        },
        "results": results,
    }


@app.post("/eda")
def eda(req: EDARequest):
    """Direct EDA-only endpoint, bypassing the planner (used by dashboard widgets)."""
    dataset_id = _dataset_id_or_latest(req.dataset_id)
    df = _resolve_dataset(dataset_id)
    filters = {k: v for k, v in req.dict().items() if k != "dataset_id" and v is not None}
    context = build_context(df, filters=filters, dataset_id=dataset_id)
    return eda_tool.run(context.scoped_df)


@app.post("/risk-report")
def risk_report(dataset_id: Optional[str] = None):
    """Runs the full pipeline (features -> graph -> rules -> ml -> risk_score -> explanation) once."""
    ds_id = _dataset_id_or_latest(dataset_id)
    df = _resolve_dataset(ds_id)
    context = build_context(df, dataset_id=ds_id)
    results = execute(context, tools=["features", "graph", "rules", "ml", "risk_score", "explanation"])
    if "risk_score" in results:
        _apply_history(ds_id, results["risk_score"]["risk_report"])
    return results


@app.post("/train")
def train_model(dataset_id: Optional[str] = None):
    """
    Explicitly (re)trains the Isolation Forest for a dataset and caches it
    (see utils/model_store.py). Subsequent /chat and /risk-report calls
    against the same dataset_id reuse this cached model instead of
    refitting on every request.
    """
    ds_id = _dataset_id_or_latest(dataset_id)
    df = _resolve_dataset(ds_id)
    context = build_context(df, dataset_id=ds_id)
    results = execute(context, tools=["features", "ml"], force_retrain=True)
    return {
        "dataset_id": ds_id,
        "model_status": results.get("ml", {}).get("model_status"),
        "customers_scored": len(results.get("ml", {}).get("ml_results", [])),
    }


@app.get("/customer/{customer_id}")
def customer_details(customer_id: str, dataset_id: Optional[str] = None):
    """Full drill-down for one customer: stats + features + rule hits + risk score + history delta."""
    ds_id = _dataset_id_or_latest(dataset_id)
    df = _resolve_dataset(ds_id)
    context = build_context(df, customer_id=customer_id, dataset_id=ds_id)
    results = execute(context, tools=["eda", "features", "graph", "rules", "ml", "risk_score", "explanation"])

    if "risk_score" in results:
        _apply_history(ds_id, results["risk_score"]["risk_report"])

    results["customer_stats"] = eda_tool.customer_statistics(df, customer_id)
    results["history"] = history_store.get_history(ds_id, customer_id)
    return results


@app.get("/timeline/{customer_id}")
def customer_timeline(customer_id: str, dataset_id: Optional[str] = None):
    """Chronological Investigation Timeline for one customer (fast, no full pipeline needed)."""
    df = _resolve_dataset(_dataset_id_or_latest(dataset_id))
    return timeline_tool.run(df, customer_id)


@app.get("/history/{customer_id}")
def customer_history(customer_id: str, dataset_id: Optional[str] = None):
    """Past risk-score snapshots for one customer (investigation history log)."""
    ds_id = _dataset_id_or_latest(dataset_id)
    return {"customer_id": customer_id, "history": history_store.get_history(ds_id, customer_id)}


@app.get("/graph/{customer_id}")
def customer_graph(customer_id: str, dataset_id: Optional[str] = None, hops: int = 1):
    """
    Returns nodes/edges of the transaction graph centered on one customer,
    for the Streamlit NetworkX visualization page.
    """
    df = _resolve_dataset(_dataset_id_or_latest(dataset_id))
    frontier = {str(customer_id)}
    visited_edges = set()

    for _ in range(max(1, hops)):
        next_frontier = set()
        subset = df[
            df["customer_id"].astype(str).isin(frontier) | df["beneficiary_id"].astype(str).isin(frontier)
        ]
        for _, row in subset.iterrows():
            src, dst = str(row["customer_id"]), str(row["beneficiary_id"])
            visited_edges.add((src, dst, round(float(row["amount"]), 2)))
            next_frontier.update([src, dst])
        frontier |= next_frontier

    nodes = sorted(frontier)
    edges = [{"source": s, "target": t, "amount": a} for s, t, a in visited_edges]
    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# v3 additions below: read-only, additive endpoints added ONLY to support the
# React frontend (dashboard summary cards, system/model status widgets).
# None of these touch the planner, executor, rule engine, or ML pipeline —
# they just expose metadata that already exists for those pipelines to read.
# ---------------------------------------------------------------------------

@app.get("/dataset/summary")
def dataset_summary(dataset_id: Optional[str] = None):
    """Lightweight dataset-level counts for the Dashboard's stat cards."""
    ds_id = _dataset_id_or_latest(dataset_id)
    df = _resolve_dataset(ds_id)
    return {
        "dataset_id": ds_id,
        "num_transactions": int(len(df)),
        "num_customers": int(df["customer_id"].nunique()),
        "num_beneficiaries": int(df["beneficiary_id"].nunique()),
        "date_range": [str(df["timestamp"].min()), str(df["timestamp"].max())],
        "has_device_id": "device_id" in df.columns,
        "has_merchant_category": "merchant_category" in df.columns,
        "model_trained": model_store.is_trained(ds_id),
        "model_trained_at": model_store.get_trained_at(ds_id),
    }


@app.get("/system/status")
def system_status():
    """
    Static-ish capability report for the Dashboard's "Planner Status" /
    "Rule Engine Status" cards — sourced from the REAL tool catalogue and
    rule-importance table, not fabricated numbers.
    """
    from agent.planner import VALID_TOOLS
    from config import RULE_IMPORTANCE
    llm = get_llm_client()
    return {
        "planner_status": "active",
        "planner_mode": "llm" if getattr(llm, "available", False) else "keyword_fallback",
        "available_tools": sorted(VALID_TOOLS),
        "rule_engine_status": "active",
        "rule_count": len(RULE_IMPORTANCE),
        "rules": list(RULE_IMPORTANCE.keys()),
        "rule_importance": RULE_IMPORTANCE,
    }


@app.get("/model/status")
def model_status(dataset_id: Optional[str] = None):
    """Isolation Forest cache status + feature columns, for the Model Insights page."""
    ds_id = _dataset_id_or_latest(dataset_id)
    return {
        "dataset_id": ds_id,
        "trained": model_store.is_trained(ds_id),
        "trained_at": model_store.get_trained_at(ds_id),
        "feature_columns": ml_tool.FEATURE_COLUMNS,
        "contamination_default": 0.1,
        "algorithm": "IsolationForest (scikit-learn, n_estimators=200)",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
