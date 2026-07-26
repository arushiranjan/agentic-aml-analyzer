"""
planner.py
----------
THE agent. There is deliberately only ONE planner agent in this system
(per project spec — no multi-agent orchestration).

Responsibilities:
  1. Understand the natural language query (via LLM, JSON mode).
  2. Extract a GOAL and a sequence of STEPS, each naming a tool AND WHY
     it's needed — this is genuine planning/reasoning output, not just a
     flat tool-selection list, so the "why" is visible to the analyst
     (surfaced in the Streamlit Chat page) and auditable.
  3. Extract entities (customer_id, country, channel) and filters.
  4. Return a validated ExecutionPlan for agent/context_builder.py and
     tools/executor.py to run.

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

VALID_TOOLS = {"eda", "features", "graph", "rules", "ml", "risk_score", "explanation"}

TOOL_CATALOGUE = """Available tools:
- "eda": descriptive statistics, distributions, missing values, averages, totals
- "features": builds per-customer AML features (velocity, structuring ratio, etc). \
Required before "rules" or "ml" can run.
- "graph": NetworkX centrality analysis (hub accounts, bridge/intermediary nodes, \
money-mule pass-through detection). Feeds into "rules".
- "rules": rule-based AML detection (structuring, layering, velocity, circular transfers, \
transaction bursts, geo anomalies, etc), merged with "graph" hits.
- "ml": Isolation Forest anomaly detection over customer features (trained once per \
dataset and cached, not refit per query)
- "risk_score": combines rule + ml scores into Low/Medium/High with a confidence score. \
Requires "rules" and "ml".
- "explanation": natural-language explanation + recommendation per flagged customer, \
grounded in a structured evidence bundle. Requires "risk_score"."""

PLANNER_SYSTEM_PROMPT = f"""You are the planning module of an AML (Anti-Money \
Laundering) suspicious-activity-detection agent.

Given a bank compliance analyst's natural language question, produce a PLAN: a \
goal statement plus an ordered list of steps, each naming exactly one tool AND a \
short reason why that tool is needed for this specific question. DO NOT include \
steps that are not needed - being efficient matters, and a stronger plan explains \
its own reasoning rather than just listing tool names.

{TOOL_CATALOGUE}

Examples:
- "average transaction amount" -> goal: "Compute average transaction amount", \
steps: [{{"tool":"eda","why":"Simple descriptive statistic, no rules or ML needed"}}]
- "find suspicious customers" -> goal: "Identify and explain suspicious customers", \
steps: [{{"tool":"features","why":"Need customer-level aggregates"}}, \
{{"tool":"graph","why":"Detect hub/mule/bridge network patterns"}}, \
{{"tool":"rules","why":"Check known AML typologies"}}, \
{{"tool":"ml","why":"Catch anomalies no rule covers"}}, \
{{"tool":"risk_score","why":"Combine both signals into one verdict"}}, \
{{"tool":"explanation","why":"Produce an analyst-readable explanation"}}]
- "find structuring" -> steps: [{{"tool":"features","why":"..."}}, {{"tool":"rules","why":"..."}}]
- "explain customer 123" -> steps: [{{"tool":"features","why":"..."}}, {{"tool":"rules","why":"..."}}, \
{{"tool":"ml","why":"..."}}, {{"tool":"risk_score","why":"..."}}, {{"tool":"explanation","why":"..."}}], \
customer_id: "123"
- "find hub accounts" or "find money mules" -> steps: [{{"tool":"features","why":"..."}}, \
{{"tool":"graph","why":"..."}}, {{"tool":"rules","why":"..."}}]
- "show customers from India" -> steps: [{{"tool":"eda","why":"..."}}], filters: {{"country": "India"}}

Respond ONLY with a JSON object, no markdown, no preamble, in this exact shape:
{{
  "goal": "<one sentence describing what the analyst wants>",
  "steps": [{{"tool": "<tool_name>", "why": "<one short reason>"}}, ...],
  "filters": {{"country": null, "channel": null, "min_amount": null, "max_amount": null, "date_from": null, "date_to": null}},
  "customer_id": null
}}
"""


@dataclass
class ExecutionPlan:
    goal: str
    steps: List[Dict[str, str]]
    tools: List[str] = field(default_factory=list)  # flattened, deduped, order-preserving
    filters: Dict[str, Any] = field(default_factory=dict)
    customer_id: Optional[str] = None
    source: str = "llm"  # "llm" or "fallback"

    @property
    def reasoning(self) -> str:
        """Human-readable summary of the plan's steps, for logging/UI display."""
        return " → ".join(f"{s['tool']} ({s['why']})" for s in self.steps) or "no tools required"


def _validate_steps(steps: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Drop any step whose tool name the LLM hallucinated; ensure each step has a 'why'."""
    cleaned = []
    for step in steps:
        tool = step.get("tool")
        if tool in VALID_TOOLS:
            cleaned.append({"tool": tool, "why": step.get("why", "")})
    return cleaned or [{"tool": "eda", "why": "Default fallback: no specific tool identified."}]


def _tools_from_steps(steps: List[Dict[str, str]]) -> List[str]:
    """Flatten steps into a deduped, order-preserving tool list for the executor."""
    seen = []
    for s in steps:
        if s["tool"] not in seen:
            seen.append(s["tool"])
    return seen


def _fallback_plan(query: str) -> ExecutionPlan:
    fb = match_intent(query)
    return ExecutionPlan(
        goal=fb["goal"], steps=fb["steps"], tools=_tools_from_steps(fb["steps"]),
        filters=fb["filters"], customer_id=fb.get("customer_id"), source="fallback",
    )


def build_plan(query: str) -> ExecutionPlan:
    """
    Main entry point. Tries the LLM first, validates the JSON, and falls
    back to the deterministic keyword matcher on any failure or when the
    LLM client reports itself unavailable (no API key configured).
    """
    llm = get_llm_client()

    if not getattr(llm, "available", True):
        return _fallback_plan(query)

    raw = llm.complete(query, system=PLANNER_SYSTEM_PROMPT, json_mode=True, temperature=0.1)

    try:
        parsed = json.loads(raw)
        steps = _validate_steps(parsed.get("steps", []))
        filters = {k: v for k, v in (parsed.get("filters") or {}).items() if v not in (None, "")}
        return ExecutionPlan(
            goal=parsed.get("goal", "Answer the analyst's question"),
            steps=steps,
            tools=_tools_from_steps(steps),
            filters=filters,
            customer_id=parsed.get("customer_id"),
            source="llm",
        )
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        logger.warning(f"Planner LLM output invalid ({e}), using keyword fallback.")
        return _fallback_plan(query)
