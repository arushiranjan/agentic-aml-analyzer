"""
explanation_tool.py
--------------------
Turns a customer's rule_hits + risk score into a natural-language
explanation and a recommendation, e.g.:

  "Customer performed 18 transactions below ₹10,000 within 20 minutes to
   7 beneficiaries. Pattern resembles structuring. Recommendation: Flag
   for manual review."

Uses the LLM for fluent phrasing when available, and falls back to a
deterministic template (no API key required) so the demo always works.
"""

from __future__ import annotations
from typing import Any, Dict, List
from utils.llm_client import get_llm_client

SYSTEM_PROMPT = (
    "You are an AML compliance analyst assistant. Given structured rule hits "
    "and a risk score for one customer, write a concise (2-4 sentence) "
    "explanation of why the customer was flagged, in plain business language, "
    "ending with a clear recommendation (Flag for manual review / Monitor / No action needed). "
    "Do not invent facts beyond what is given."
)


def _template_explanation(customer_risk: Dict[str, Any]) -> str:
    """Deterministic fallback used when no LLM is configured."""
    hits = customer_risk.get("rule_hits", [])
    level = customer_risk.get("risk_level", "Low")
    cid = customer_risk.get("customer_id")

    if not hits:
        return (f"Customer {cid} shows a final risk score of "
                f"{customer_risk.get('final_score', 0)} ({level}) driven mainly by "
                f"the ML anomaly model, with no specific rule matches. "
                f"Recommendation: {'Flag for manual review' if level == 'High' else 'Monitor'}.")

    reasons = "; ".join(h["reason"] for h in hits[:3])
    recommendation = {
        "High": "Flag for manual review.",
        "Medium": "Monitor closely over the next reporting cycle.",
        "Low": "No immediate action needed.",
    }[level]
    return (f"Customer {cid} was flagged {level.lower()} risk (score {customer_risk.get('final_score')}). "
            f"{reasons}. Recommendation: {recommendation}")


def explain_customer(customer_risk: Dict[str, Any]) -> str:
    """Generate one explanation, preferring the LLM, falling back to template."""
    llm = get_llm_client()
    prompt = (
        f"Customer ID: {customer_risk.get('customer_id')}\n"
        f"Final risk score: {customer_risk.get('final_score')} ({customer_risk.get('risk_level')})\n"
        f"Rule score: {customer_risk.get('rule_score')} | ML anomaly score: {customer_risk.get('ml_score')}\n"
        f"Rule hits: {customer_risk.get('rule_hits')}\n\n"
        "Write the explanation now."
    )
    result = llm.complete(prompt, system=SYSTEM_PROMPT, temperature=0.3)

    # If offline fallback returned raw JSON (no real LLM configured), use the template instead.
    if result.strip().startswith("{"):
        return _template_explanation(customer_risk)
    return result.strip()


def run(risk_report: List[Dict[str, Any]], top_n: int = 10) -> Dict[str, Any]:
    """Entry point for the Tool Executor. Explains the top-N riskiest customers."""
    top_customers = risk_report[:top_n]
    explanations = [
        {"customer_id": c["customer_id"], "risk_level": c["risk_level"],
         "final_score": c["final_score"], "explanation": explain_customer(c)}
        for c in top_customers
    ]
    return {"explanations": explanations}
