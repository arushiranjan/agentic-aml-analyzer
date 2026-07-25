"""
backend/main.py
----------------
FastAPI application exposing the AML Suspicious Activity Detection Agent.

Endpoints:
  POST /upload         - upload a transaction CSV, returns dataset_id
  POST /chat           - natural language query -> agent plan -> tool results
  POST /eda            - direct EDA-only call (bypasses the planner)
  POST /risk-report    - full risk pipeline for the whole dataset
  GET  /customer/{id}  - drill-down details for one customer
  GET  /graph/{id}     - transaction graph data (nodes/edges) for NetworkX viz
  GET  /health         - health check
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

# Make the project root importable (agent/, tools/, utils/ live one level up)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.planner import build_plan
from tools.executor import execute
from tools import eda_tool, feature_engineering, rule_engine
from utils.data_loader import register_dataset, get_dataset, latest_dataset_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AML Suspicious Activity Detection Agent",
    description="Agentic AI backend for anti-money-laundering detection.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    Core agentic endpoint. The planner decides which tools to run for
    this specific query, then the executor runs only those tools.
    """
    df = _resolve_dataset(req.dataset_id)
    plan = build_plan(req.query)

    results = execute(
        df=df,
        tools=plan.tools,
        filters=plan.filters,
        customer_id=plan.customer_id,
    )

    return {
        "query": req.query,
        "plan": {
            "intent": plan.intent,
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
    df = _resolve_dataset(req.dataset_id)
    filters = {k: v for k, v in req.dict().items() if k != "dataset_id" and v is not None}
    return eda_tool.run(df, filters)


@app.post("/risk-report")
def risk_report(dataset_id: Optional[str] = None):
    """Runs the full pipeline (features -> rules -> ml -> risk_score -> explanation) once."""
    df = _resolve_dataset(dataset_id)
    return execute(df, tools=["features", "rules", "ml", "risk_score", "explanation"])


@app.get("/customer/{customer_id}")
def customer_details(customer_id: str, dataset_id: Optional[str] = None):
    """Full drill-down for one customer: stats + features + rule hits + risk score."""
    df = _resolve_dataset(dataset_id)
    results = execute(
        df, tools=["eda", "features", "rules", "ml", "risk_score", "explanation"],
        customer_id=customer_id,
    )
    stats = eda_tool.customer_statistics(df, customer_id)
    results["customer_stats"] = stats
    return results


@app.get("/graph/{customer_id}")
def customer_graph(customer_id: str, dataset_id: Optional[str] = None, hops: int = 1):
    """
    Returns nodes/edges of the transaction graph centered on one customer,
    for the Streamlit NetworkX visualization page.
    """
    df = _resolve_dataset(dataset_id)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
