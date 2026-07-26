"""
explanation_tool.py
--------------------
Turns a customer's structured evidence bundle (rule hits + ML flag +
confidence) into a natural-language explanation and a recommendation:

  "Customer performed 18 transactions below ₹10,000 within 20 minutes to
   7 beneficiaries. Pattern resembles structuring. Recommendation: Flag
   for manual review."

Grounding: the LLM is given a pre-built STRUCTURED EVIDENCE BUNDLE (not
raw numbers scattered across the pipeline) and is explicitly instructed
not to invent facts beyond it — evidence assembly happens first, then the
LLM only phrases/summarizes it. Falls back to a deterministic template
(no API key required) so the demo always works.
"""

from __future__ import annotations
from typing import Any, Dict, List
from utils.llm_client import get_llm_client

SYSTEM_PROMPT = (
    "You are an AML compliance analyst assistant. You will be given a structured "
    "EVIDENCE BUNDLE for one customer (rule hits with their reasons, an ML anomaly "
    "flag, and a confidence score). Write a concise (2-4 sentence) explanation of "
    "why the customer was flagged, in plain business language, ending with a clear "
    "recommendation (Flag for manual review / Monitor / No action needed). "
    "Only use facts present in the evidence bundle — do not invent transaction "
    "details, amounts, or counts that are not given to you."
)


def build_evidence_bundle(customer_risk: Dict[str, Any]) -> Dict[str, Any]:
    """
    Structured evidence assembly step, done BEFORE any LLM call (per the
    'explanations are grounded evidence, not post-hoc narrative' design
    goal). This same bundle is what a human reviewer would look at too.
    """
    return {
        "customer_id": customer_risk.get("customer_id"),
        "risk_level": customer_risk.get("risk_level"),
        "final_score": customer_risk.get("final_score"),
        "confidence_pct": customer_risk.get("confidence"),
        "rule_score": customer_risk.get("rule_score"),
        "ml_score": customer_risk.get("ml_score"),
        "is_ml_anomaly": customer_risk.get("is_ml_anomaly"),
        "evidence": customer_risk.get("evidence", []),
        "rule_hits": [
            {"rule": h["rule"], "reason": h["reason"]} for h in customer_risk.get("rule_hits", [])
        ],
    }


def _template_explanation(bundle: Dict[str, Any]) -> str:
    """Deterministic fallback used when no LLM is configured."""
    level = bundle.get("risk_level", "Low")
    cid = bundle.get("customer_id")
    evidence = bundle.get("evidence", [])

    recommendation = {
        "High": "Flag for manual review.",
        "Medium": "Monitor closely over the next reporting cycle.",
        "Low": "No immediate action needed.",
    }[level]

    if not evidence:
        return (f"Customer {cid} shows a final risk score of {bundle.get('final_score', 0)} "
                f"({level}, confidence {bundle.get('confidence_pct')}%) driven mainly by the ML "
                f"anomaly model, with no specific rule matches. Recommendation: {recommendation}")

    reasons = "; ".join(evidence[:3])
    return (f"Customer {cid} was flagged {level.lower()} risk (score {bundle.get('final_score')}, "
            f"confidence {bundle.get('confidence_pct')}%). {reasons}. Recommendation: {recommendation}")


def explain_customer(customer_risk: Dict[str, Any]) -> Dict[str, Any]:
    """Generate one explanation, preferring the LLM, falling back to template."""
    bundle = build_evidence_bundle(customer_risk)
    llm = get_llm_client()

    if not getattr(llm, "available", True):
        return {**bundle, "explanation": _template_explanation(bundle)}

    prompt = f"Evidence bundle:\n{bundle}\n\nWrite the explanation now."
    result = llm.complete(prompt, system=SYSTEM_PROMPT, temperature=0.3)

    if result.strip().startswith("{"):  # offline-fallback JSON slipped through
        return {**bundle, "explanation": _template_explanation(bundle)}
    return {**bundle, "explanation": result.strip()}


def run(risk_report: List[Dict[str, Any]], top_n: int = 10) -> Dict[str, Any]:
    """Entry point for the Tool Executor. Explains the top-N riskiest customers."""
    top_customers = risk_report[:top_n]
    explanations = [explain_customer(c) for c in top_customers]
    return {"explanations": explanations}
