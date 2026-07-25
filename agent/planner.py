"""
planner.py
----------
THE agent. There is deliberately only ONE planner agent in this system
(per project spec — no multi-agent orchestration).

Responsibilities:
  1. Understand the natural language query (via LLM, JSON mode).
  2. Extract intent, entities (customer_id, country, channel), and filters.
  3. Decide which of the available tools are actually required.
  4. Return a validated ExecutionPlan for tools/executor.py to run.

If the LLM is unavailable or returns malformed output, the planner
transparently falls back to agent/intent_rules.py so the system keeps
working end-to-end even with zero API key configured.
"""

from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils.llm_client import get_llm_client
from agent.intent_rules import match_intent

logger = logging.getLogger(__name__)

VALID_TOOLS = {"eda", "features", "rules", "ml", "risk_score", "explanation"}

PLANNER_SYSTEM_PROMPT = """You are the planning module of an AML (Anti-Money \
Laundering) suspicious-activity-detection agent.

Given a bank compliance analyst's natural language question, decide which \
of the following tools are needed to answer it. DO NOT select tools that \
are not needed - being efficient matters.

Available tools:
- "eda": descriptive statistics, distributions, missing values, averages, totals
- "features": builds per-customer AML features (velocity, structuring ratio, etc). \
Required before "rules" or "ml" can run.
- "rules": rule-based AML detection (structuring, layering, velocity, circular transfers, etc)
- "ml": Isolation Forest anomaly detection over customer features
- "risk_score": combines rule + ml scores into Low/Medium/High. Requires "rules" and "ml".
- "explanation": natural-language explanation + recommendation per flagged customer. Requires "risk_score".

Examples:
- "average transaction amount" -> tools: ["eda"]
- "show transaction distribution" -> tools: ["eda"]
- "find suspicious customers" -> tools: ["features", "rules", "ml", "risk_score", "explanation"]
- "find structuring" -> tools: ["features", "rules"]
- "which customers should be investigated" -> tools: ["features", "rules", "ml", "risk_score", "explanation"]
- "explain customer 123" -> tools: ["features", "risk_score", "explanation"], customer_id: "123"
- "show customers from India" -> tools: ["eda"], filters: {"country": "India"}

Respond ONLY with a JSON object, no markdown, no preamble, in this exact shape:
{
  "intent": "<short_snake_case_label>",
  "tools": ["<tool_name>", ...],
  "filters": {"country": null, "channel": null, "min_amount": null, "max_amount": null, "date_from": null, "date_to": null},
  "customer_id": null,
  "reasoning": "<one sentence on why these tools were chosen>"
}
"""


@dataclass
class ExecutionPlan:
    intent: str
    tools: List[str]
    filters: Dict[str, Any] = field(default_factory=dict)
    customer_id: Optional[str] = None
    reasoning: str = ""
    source: str = "llm"  # "llm" or "fallback"


def _validate_tools(tools: List[str]) -> List[str]:
    """Drop any tool name the LLM hallucinated that isn't in VALID_TOOLS."""
    cleaned = [t for t in tools if t in VALID_TOOLS]
    return cleaned or ["eda"]


def build_plan(query: str) -> ExecutionPlan:
    """
    Main entry point. Tries the LLM first, validates the JSON, and falls
    back to the deterministic keyword matcher on any failure.
    """
    llm = get_llm_client()

    if not getattr(llm, "available", True):
        fb = match_intent(query)
        return ExecutionPlan(
            intent=fb["intent"], tools=_validate_tools(fb["tools"]),
            filters=fb["filters"], customer_id=fb.get("customer_id"),
            reasoning=fb["reasoning"], source="fallback",
        )

    raw = llm.complete(query, system=PLANNER_SYSTEM_PROMPT, json_mode=True, temperature=0.1)

    try:
        parsed = json.loads(raw)
        tools = _validate_tools(parsed.get("tools", []))
        filters = {k: v for k, v in (parsed.get("filters") or {}).items() if v not in (None, "")}
        return ExecutionPlan(
            intent=parsed.get("intent", "unknown"),
            tools=tools,
            filters=filters,
            customer_id=parsed.get("customer_id"),
            reasoning=parsed.get("reasoning", ""),
            source="llm",
        )
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        logger.warning(f"Planner LLM output invalid ({e}), using keyword fallback.")
        fb = match_intent(query)
        return ExecutionPlan(
            intent=fb["intent"], tools=_validate_tools(fb["tools"]),
            filters=fb["filters"], customer_id=fb.get("customer_id"),
            reasoning=fb["reasoning"], source="fallback",
        )
