"""
intent_rules.py
----------------
Deterministic keyword-based intent matcher. Used as a fallback whenever
the LLM is unavailable (no API key, network failure, offline demo) so
the agent NEVER fully breaks. Also used to sanity-check/repair whatever
the LLM returns.
"""

from __future__ import annotations
import re
from typing import Any, Dict

PATTERNS = [
    (r"\b(explain|details? (of|for|about)|tell me about) customer\b", "explain_customer", ["features", "risk_score", "explanation"]),
    (r"\b(structuring)\b", "find_structuring", ["features", "rules"]),
    (r"\b(layering)\b", "find_layering", ["features", "rules"]),
    (r"\b(circular)\b", "find_circular", ["features", "rules"]),
    (r"\b(velocity)\b", "find_velocity", ["features", "rules"]),
    (r"\b(suspicious|investigat|risk|flag)\b", "find_suspicious", ["features", "rules", "ml", "risk_score", "explanation"]),
    (r"\b(distribution|histogram|chart|plot|trend|timeline)\b", "show_distribution", ["eda"]),
    (r"\b(average|mean|median|std|statistic|total)\b", "get_statistics", ["eda"]),
    (r"\b(missing)\b", "missing_values", ["eda"]),
    (r"\b(network|graph|connections?)\b", "show_network", ["features", "rules"]),
    (r"\b(anomaly|anomalies|outlier)\b", "find_anomalies", ["features", "ml"]),
]

COUNTRY_RE = re.compile(r"from ([a-zA-Z ]+)$", re.IGNORECASE)
CUSTOMER_ID_RE = re.compile(r"customer\s+([a-zA-Z0-9_-]+)", re.IGNORECASE)


def match_intent(query: str) -> Dict[str, Any]:
    """Best-effort keyword match. Always returns a usable plan."""
    q = query.lower().strip()

    intent, tools = "eda_summary", ["eda"]
    for pattern, name, tool_list in PATTERNS:
        if re.search(pattern, q):
            intent, tools = name, tool_list
            break

    filters: Dict[str, Any] = {}
    country_match = COUNTRY_RE.search(q)
    if country_match:
        filters["country"] = country_match.group(1).strip()

    customer_id = None
    cust_match = CUSTOMER_ID_RE.search(q)
    if cust_match:
        customer_id = cust_match.group(1)

    return {
        "intent": intent,
        "tools": tools,
        "filters": filters,
        "customer_id": customer_id,
        "reasoning": f"Keyword fallback matched intent '{intent}'.",
    }
