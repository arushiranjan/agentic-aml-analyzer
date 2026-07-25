"""
risk_scoring.py
----------------
Combines the Rule Engine score and the ML anomaly score into one final
risk score and a Low / Medium / High label per customer.

final_score = (RULE_WEIGHT * rule_score) + (ML_WEIGHT * ml_score)
"""

from __future__ import annotations
from typing import Any, Dict, List

RULE_WEIGHT = 0.6
ML_WEIGHT = 0.4

HIGH_THRESHOLD = 0.65
MEDIUM_THRESHOLD = 0.35


def label_for(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "High"
    if score >= MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


def run(rule_results: List[Dict[str, Any]], ml_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Entry point for the Tool Executor. Merges rule + ML output on customer_id."""
    rule_map = {str(r["customer_id"]): r for r in rule_results}
    ml_map = {str(r["customer_id"]): r for r in ml_results}

    all_ids = set(rule_map.keys()) | set(ml_map.keys())
    combined = []
    for cid in all_ids:
        rule_score = rule_map.get(cid, {}).get("rule_score", 0.0)
        ml_score = ml_map.get(cid, {}).get("ml_score", 0.0)
        final_score = round(RULE_WEIGHT * rule_score + ML_WEIGHT * ml_score, 3)

        combined.append({
            "customer_id": cid,
            "rule_score": round(rule_score, 3),
            "ml_score": round(ml_score, 3),
            "final_score": final_score,
            "risk_level": label_for(final_score),
            "rule_hits": rule_map.get(cid, {}).get("rule_hits", []),
            "is_ml_anomaly": ml_map.get(cid, {}).get("is_anomaly", False),
        })

    combined.sort(key=lambda r: r["final_score"], reverse=True)
    return {"risk_report": combined}
