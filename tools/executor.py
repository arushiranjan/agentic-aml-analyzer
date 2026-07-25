"""
executor.py
-----------
Runs ONLY the tools that the AI Planner decided are needed, in the
correct dependency order, and merges their outputs into one response.

Dependency rules:
  - rules, ml need -> features
  - risk_score needs -> rules + ml
  - explanation needs -> risk_score

The executor auto-adds prerequisite tools even if the planner forgot
them, so a plan like ["risk_score"] still works correctly.
"""

from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd

from tools import eda_tool, feature_engineering, rule_engine, ml_tool, risk_scoring, explanation_tool

# Declares what each tool needs before it can run
DEPENDENCIES = {
    "eda": [],
    "features": [],
    "rules": ["features"],
    "ml": ["features"],
    "risk_score": ["rules", "ml"],
    "explanation": ["risk_score"],
}


def resolve_order(requested_tools: List[str]) -> List[str]:
    """Topologically expand the requested tool list with prerequisites, preserving a valid run order."""
    resolved: List[str] = []

    def add(tool: str):
        if tool in resolved:
            return
        for dep in DEPENDENCIES.get(tool, []):
            add(dep)
        resolved.append(tool)

    for t in requested_tools:
        add(t)
    return resolved


def execute(df: pd.DataFrame, tools: List[str], filters: Dict[str, Any] = None,
            customer_id: str = None) -> Dict[str, Any]:
    """
    Runs the resolved tool chain and returns a merged results dict.
    Only tools that were actually requested (or required as a dependency)
    execute — this is what makes the agent "dynamic" rather than a fixed
    sequential pipeline.
    """
    filters = filters or {}
    order = resolve_order(tools)
    results: Dict[str, Any] = {"tools_executed": order}

    features_df = None

    for tool in order:
        if tool == "eda":
            results["eda"] = eda_tool.run(df, filters)

        elif tool == "features":
            out = feature_engineering.run(df)
            features_df = out.pop("_df")
            results["features"] = out

        elif tool == "rules":
            rule_out = rule_engine.run(df, features_df)
            results["rules"] = rule_out

        elif tool == "ml":
            ml_out = ml_tool.run(features_df)
            results["ml"] = ml_out

        elif tool == "risk_score":
            risk_out = risk_scoring.run(
                results.get("rules", {}).get("rule_results", []),
                results.get("ml", {}).get("ml_results", []),
            )
            results["risk_score"] = risk_out

        elif tool == "explanation":
            exp_out = explanation_tool.run(results.get("risk_score", {}).get("risk_report", []))
            results["explanation"] = exp_out

    # Optional: scope the final risk_score / explanation to one customer for "Explain customer X"
    if customer_id and "risk_score" in results:
        report = results["risk_score"].get("risk_report", [])
        scoped = [r for r in report if str(r["customer_id"]) == str(customer_id)]
        results["risk_score"]["risk_report"] = scoped
        if "explanation" in results:
            results["explanation"]["explanations"] = [
                e for e in results["explanation"]["explanations"] if str(e["customer_id"]) == str(customer_id)
            ]

    return results
