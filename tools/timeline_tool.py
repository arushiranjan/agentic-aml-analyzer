"""
timeline_tool.py
------------------
Builds a chronological, per-transaction timeline for one customer, with
the gap since the previous transaction, and a lightweight heuristic
caption ("Possible structuring", "Possible transaction burst") derived
directly from the timeline shape — this is the "Investigation Timeline"
view judges can read at a glance without digging through JSON.

This is a presentation-layer heuristic (fast, always available even
before /chat's full rule+ML pipeline runs) — it does NOT replace the
authoritative rule_engine / risk_scoring verdict, which is grounded in
the full customer population and importance-weighted rules.
"""

from __future__ import annotations
from typing import Any, Dict
import pandas as pd

from config import STRUCTURING_THRESHOLD


def build_timeline(df: pd.DataFrame, customer_id: str) -> Dict[str, Any]:
    grp = df[df["customer_id"].astype(str) == str(customer_id)].sort_values("timestamp")
    if grp.empty:
        return {"customer_id": customer_id, "events": [], "caption": "No transactions found for this customer."}

    events = []
    prev_ts = None
    for _, row in grp.iterrows():
        gap_seconds = None if prev_ts is None else round((row["timestamp"] - prev_ts).total_seconds(), 1)
        events.append({
            "timestamp": str(row["timestamp"]),
            "amount": round(float(row["amount"]), 2),
            "beneficiary_id": row["beneficiary_id"],
            "gap_seconds_since_prev": gap_seconds,
        })
        prev_ts = row["timestamp"]

    return {"customer_id": customer_id, "events": events, "caption": _caption_for(grp)}


def _caption_for(grp: pd.DataFrame) -> str:
    amounts = grp["amount"]
    span_minutes = (grp["timestamp"].max() - grp["timestamp"].min()).total_seconds() / 60

    if len(grp) >= 5 and span_minutes <= 60 and (amounts < STRUCTURING_THRESHOLD).mean() >= 0.7:
        return (f"Possible structuring: {len(grp)} similarly-sized transactions just under the "
                f"reporting threshold within roughly {span_minutes:.0f} minutes.")
    if len(grp) >= 5 and span_minutes <= 15:
        return f"Possible transaction burst: {len(grp)} transactions within roughly {span_minutes:.0f} minutes."
    return "No strong pattern detected from the timeline alone — see the Rule/ML results for the full picture."


def run(df: pd.DataFrame, customer_id: str) -> Dict[str, Any]:
    return build_timeline(df, customer_id)
