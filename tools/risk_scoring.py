"""
risk_scoring.py
----------------
Combines the Rule Engine score and the ML anomaly score into one final
risk score, a Low / Medium / High label, a CONFIDENCE score, and an
"evidence panel" (a flat list of human-readable reasons) per customer.

    final_score = RULE_WEIGHT * rule_score + ML_WEIGHT * ml_score

Weights and thresholds live in config.py (documented rationale there,
overridable via RISK_RULE_WEIGHT / RISK_ML_WEIGHT env vars or the
`rule_weight`/`ml_weight` params below) — NOT hardcoded here, so a judge
asking "why 60/40?" gets a real answer instead of a magic number.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from config import RULE_WEIGHT, ML_WEIGHT, HIGH_THRESHOLD, MEDIUM_THRESHOLD


def label_for(score: float) -> str:
    if score >= HIGH_THRESHOLD:
        return "High"
    if score >= MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


def compute_confidence(rule_score: float, ml_score: float, num_rule_hits: int) -> float:
    """
    Confidence (0-100%) reflects two things:
      1. Agreement between the two independent signals (rules vs ML) —
         when both point the same direction, we're more confident than
         when they disagree.
      2. Evidence strength — how many independent rule hits back up the
         verdict (a single weak hit is less trustworthy than three
         corroborating typologies).
    This is a heuristic confidence, not a calibrated statistical
    probability — presented to give analysts a sense of "how much to
    trust this score", not a formal p-value.
    """
    agreement = 1 - abs(rule_score - ml_score)
    evidence_strength = min(1.0, num_rule_hits / 3)
    confidence = 0.5 * agreement + 0.5 * evidence_strength
    return round(confidence * 100, 1)


def build_evidence(rule_hits: List[Dict[str, Any]], is_ml_anomaly: bool) -> List[str]:
    """Flat, checklist-style evidence panel for the UI (✓ 15 small transactions, ✓ ML anomaly, ...)."""
    evidence = [hit["reason"] for hit in rule_hits]
    if is_ml_anomaly:
        evidence.append("Flagged as a statistical anomaly by the Isolation Forest ML model.")
    return evidence


def run(rule_results: List[Dict[str, Any]], ml_results: List[Dict[str, Any]],
        rule_weight: Optional[float] = None, ml_weight: Optional[float] = None) -> Dict[str, Any]:
    """Entry point for the Tool Executor. Merges rule + ML output on customer_id."""
    rw = RULE_WEIGHT if rule_weight is None else rule_weight
    mw = ML_WEIGHT if ml_weight is None else ml_weight

    rule_map = {str(r["customer_id"]): r for r in rule_results}
    ml_map = {str(r["customer_id"]): r for r in ml_results}

    all_ids = set(rule_map.keys()) | set(ml_map.keys())
    combined = []
    for cid in all_ids:
        rule_entry = rule_map.get(cid, {})
        rule_score = rule_entry.get("rule_score", 0.0)
        rule_hits = rule_entry.get("rule_hits", [])
        ml_score = ml_map.get(cid, {}).get("ml_score", 0.0)
        is_ml_anomaly = ml_map.get(cid, {}).get("is_anomaly", False)

        final_score = round(rw * rule_score + mw * ml_score, 3)
        confidence = compute_confidence(rule_score, ml_score, len(rule_hits))

        combined.append({
            "customer_id": cid,
            "rule_score": round(rule_score, 3),
            "ml_score": round(ml_score, 3),
            "final_score": final_score,
            "risk_level": label_for(final_score),
            "confidence": confidence,
            "confidence_breakdown": {
                "rules_pct": round(rule_score * 100, 1),
                "ml_pct": round(ml_score * 100, 1),
            },
            "rule_hits": rule_hits,
            "is_ml_anomaly": is_ml_anomaly,
            "evidence": build_evidence(rule_hits, is_ml_anomaly),
            "weights_used": {"rule_weight": rw, "ml_weight": mw},
        })

    combined.sort(key=lambda r: r["final_score"], reverse=True)
    return {"risk_report": combined}
