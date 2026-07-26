"""
history_store.py
------------------
Lightweight investigation history log: every time a customer's risk score
is computed, a snapshot is appended. This lets the UI show "risk score
increased since your last check" deltas — the kind of audit trail a
regulator would expect to exist anyway.

In-memory dict for the hackathon demo; swap for a real database/audit log
table in production (record() / get_history() interface stays the same).
"""

from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_HISTORY: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
# dataset_id -> customer_id -> [ {timestamp, final_score, risk_level}, ... ]


def compute_delta(dataset_id: str, customer_id: str, current_score: float) -> Optional[Dict[str, Any]]:
    """Compares the current score to the most recent PRIOR snapshot, if one exists."""
    hist = _HISTORY[dataset_id][str(customer_id)]
    if not hist:
        return None
    prev = hist[-1]
    return {
        "previous_score": prev["final_score"],
        "previous_risk_level": prev["risk_level"],
        "previous_timestamp": prev["timestamp"],
        "change": round(current_score - prev["final_score"], 3),
    }


def record(dataset_id: str, customer_id: str, final_score: float, risk_level: str) -> None:
    _HISTORY[dataset_id][str(customer_id)].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "final_score": final_score,
        "risk_level": risk_level,
    })


def get_history(dataset_id: str, customer_id: str) -> List[Dict[str, Any]]:
    return list(_HISTORY[dataset_id][str(customer_id)])


def record_batch(dataset_id: str, risk_report: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Computes a delta for every customer in a risk report BEFORE recording
    the new snapshot, then records. Returns {customer_id: delta_or_None}.
    """
    deltas = {}
    for row in risk_report:
        cid = str(row["customer_id"])
        deltas[cid] = compute_delta(dataset_id, cid, row["final_score"])
        record(dataset_id, cid, row["final_score"], row["risk_level"])
    return deltas
