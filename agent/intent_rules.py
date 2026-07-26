"""
intent_rules.py
----------------
Deterministic keyword-based intent matcher. Used as a fallback whenever
the LLM is unavailable (no API key, network failure, offline demo) so
the agent NEVER fully breaks. Produces the same {goal, steps, filters,
customer_id} shape agent/planner.py expects from the LLM, so downstream
code doesn't need to special-case the fallback source.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List

WHY = {
    "eda": "Descriptive statistic — no rules or ML needed for this question.",
    "features": "Need customer-level aggregates before running rules or ML.",
    "graph": "Detect network-level patterns (hub accounts, money mules, bridge nodes).",
    "rules": "Check known AML typologies against the engineered features.",
    "ml": "Catch anomalies that don't match any hand-written rule.",
    "risk_score": "Combine rule and ML signals into one Low/Medium/High verdict.",
    "explanation": "Produce an analyst-readable, evidence-grounded explanation.",
}


def _steps(tool_names: List[str]) -> List[Dict[str, str]]:
    return [{"tool": t, "why": WHY.get(t, "")} for t in tool_names]


PATTERNS = [
    (r"\b(explain|details? (of|for|about)|tell me about) customer\b",
     "Explain a specific customer's risk profile", ["features", "rules", "ml", "risk_score", "explanation"]),
    (r"\b(hub|mule|money mule|bridge|centrality|intermediar)\b",
     "Find hub accounts, money mules, or bridge nodes", ["features", "graph", "rules"]),
    (r"\b(structuring)\b", "Find structuring patterns", ["features", "rules"]),
    (r"\b(layering)\b", "Find layering patterns", ["features", "rules"]),
    (r"\b(circular)\b", "Find circular transfer loops", ["features", "rules"]),
    (r"\b(burst)\b", "Find transaction bursts", ["features", "rules"]),
    (r"\b(geo|cross[- ]?border|countr(y|ies))\b", "Find geographic/cross-border anomalies", ["features", "rules"]),
    (r"\b(velocity)\b", "Find high-velocity accounts", ["features", "rules"]),
    (r"\b(suspicious|investigat|risk|flag)\b",
     "Identify and explain suspicious customers", ["features", "graph", "rules", "ml", "risk_score", "explanation"]),
    (r"\b(distribution|histogram|chart|plot|trend|timeline)\b",
     "Show transaction distribution/trend", ["eda"]),
    (r"\b(average|mean|median|std|statistic|total)\b",
     "Compute descriptive transaction statistics", ["eda"]),
    (r"\b(missing)\b", "Check for missing values", ["eda"]),
    (r"\b(network|graph|connections?)\b", "Analyze the transaction network", ["features", "graph", "rules"]),
    (r"\b(anomaly|anomalies|outlier)\b", "Find statistical anomalies", ["features", "ml"]),
]

COUNTRY_RE = re.compile(r"from ([a-zA-Z ]+)$", re.IGNORECASE)
CUSTOMER_ID_RE = re.compile(r"customer\s+([a-zA-Z0-9_-]+)", re.IGNORECASE)


def match_intent(query: str) -> Dict[str, Any]:
    """Best-effort keyword match. Always returns a usable plan."""
    q = query.lower().strip()

    goal, tools = "Summarize the transaction data", ["eda"]
    for pattern, goal_text, tool_list in PATTERNS:
        if re.search(pattern, q):
            goal, tools = goal_text, tool_list
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
        "goal": goal,
        "steps": _steps(tools),
        "filters": filters,
        "customer_id": customer_id,
    }
