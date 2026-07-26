"""
eda_tool.py
-----------
Pure descriptive-statistics tool. No ML, no rules — just pandas/numpy.
The planner invokes this alone for questions like "average transaction
amount" or "show transaction distribution", so it must be cheap and fast.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import pandas as pd
import numpy as np


def missing_value_report(df: pd.DataFrame) -> Dict[str, Any]:
    """Count and percentage of missing values per column."""
    total = len(df)
    missing = df.isna().sum()
    return {
        col: {"missing": int(missing[col]), "pct": round(float(missing[col]) / total * 100, 2)}
        for col in df.columns if missing[col] > 0
    } or {"message": "No missing values detected."}


def transaction_statistics(df: pd.DataFrame, filters: Optional[Dict] = None) -> Dict[str, Any]:
    """Overall statistics on the (optionally filtered) transaction amounts."""
    data = apply_filters(df, filters)
    if data.empty:
        return {"message": "No transactions match the given filters."}
    amt = data["amount"]
    return {
        "count": int(len(data)),
        "total_amount": round(float(amt.sum()), 2),
        "average_amount": round(float(amt.mean()), 2),
        "median_amount": round(float(amt.median()), 2),
        "std_amount": round(float(amt.std() or 0), 2),
        "min_amount": round(float(amt.min()), 2),
        "max_amount": round(float(amt.max()), 2),
        "date_range": [str(data["timestamp"].min()), str(data["timestamp"].max())],
    }


def customer_statistics(df: pd.DataFrame, customer_id: Optional[str] = None) -> Dict[str, Any]:
    """Per-customer aggregate stats. If customer_id given, scope to that customer."""
    data = df if customer_id is None else df[df["customer_id"].astype(str) == str(customer_id)]
    if data.empty:
        return {"message": f"No transactions found for customer {customer_id}."}

    grouped = data.groupby("customer_id").agg(
        txn_count=("transaction_id", "count"),
        total_amount=("amount", "sum"),
        avg_amount=("amount", "mean"),
        unique_beneficiaries=("beneficiary_id", "nunique"),
        first_txn=("timestamp", "min"),
        last_txn=("timestamp", "max"),
    ).reset_index()

    grouped = grouped.sort_values("total_amount", ascending=False)
    return {"customers": grouped.head(50).to_dict(orient="records")}


def distribution_data(df: pd.DataFrame, filters: Optional[Dict] = None) -> Dict[str, Any]:
    """Data shaped for Plotly/Recharts histograms/timelines/breakdowns in the frontend."""
    data = apply_filters(df, filters)
    hist, edges = np.histogram(data["amount"].clip(upper=data["amount"].quantile(0.99)), bins=30)
    daily = data.set_index("timestamp").resample("D").size()
    hourly = data["timestamp"].dt.hour.value_counts().sort_index()

    result = {
        "amount_histogram": {"counts": hist.tolist(), "bin_edges": edges.tolist()},
        "daily_txn_counts": {"dates": [str(d.date()) for d in daily.index], "counts": daily.tolist()},
        "hourly_txn_counts": {"hours": hourly.index.tolist(), "counts": hourly.tolist()},
    }
    # These columns are optional depending on the uploaded schema — included only when present,
    # so this stays purely additive and never breaks on a minimal CSV.
    if "channel" in data.columns:
        vc = data["channel"].value_counts()
        result["channel_counts"] = {"labels": vc.index.tolist(), "counts": vc.tolist()}
    if "country" in data.columns:
        vc = data["country"].value_counts()
        result["country_counts"] = {"labels": vc.index.tolist(), "counts": vc.tolist()}
    return result


def apply_filters(df: pd.DataFrame, filters: Optional[Dict]) -> pd.DataFrame:
    """
    Shared helper used by every tool. Supports filtering on:
    country, channel, customer_id, min_amount, max_amount, date_from, date_to.
    """
    if not filters:
        return df
    data = df
    if filters.get("country"):
        data = data[data["country"].astype(str).str.lower() == str(filters["country"]).lower()]
    if filters.get("channel"):
        data = data[data["channel"].astype(str).str.lower() == str(filters["channel"]).lower()]
    if filters.get("customer_id"):
        data = data[data["customer_id"].astype(str) == str(filters["customer_id"])]
    if filters.get("min_amount") is not None:
        data = data[data["amount"] >= float(filters["min_amount"])]
    if filters.get("max_amount") is not None:
        data = data[data["amount"] <= float(filters["max_amount"])]
    if filters.get("date_from"):
        data = data[data["timestamp"] >= pd.to_datetime(filters["date_from"])]
    if filters.get("date_to"):
        data = data[data["timestamp"] <= pd.to_datetime(filters["date_to"])]
    return data


def run(df: pd.DataFrame, filters: Optional[Dict] = None) -> Dict[str, Any]:
    """Entry point the Tool Executor calls for the 'eda' tool."""
    return {
        "missing_values": missing_value_report(df),
        "transaction_stats": transaction_statistics(df, filters),
        "distribution": distribution_data(df, filters),
    }
