"""
tests/test_pipeline.py
-----------------------
Basic pytest suite. Run with:  pytest tests/ -v

Uses the generated sample_data/transactions.csv so it also acts as a
regression check on the injected suspicious patterns.
"""

import os
import sys
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_loader import normalize_columns
from tools import feature_engineering, rule_engine, ml_tool, risk_scoring
from tools.executor import execute, resolve_order
from agent.intent_rules import match_intent

SAMPLE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "sample_data", "transactions.csv")


@pytest.fixture(scope="module")
def df():
    raw = pd.read_csv(SAMPLE_PATH)
    return normalize_columns(raw)


def test_normalize_columns_required(df):
    for col in ["transaction_id", "customer_id", "timestamp", "amount", "beneficiary_id"]:
        assert col in df.columns


def test_feature_engineering_no_nan(df):
    features = feature_engineering.build_features(df)
    assert not features.isna().any().any(), "Features must not contain NaN (breaks JSON serialization)"
    assert "C901" in features["customer_id"].values


def test_structuring_rule_detects_injected_pattern(df):
    features = feature_engineering.build_features(df)
    hits = rule_engine.rule_structuring(features)
    flagged = {h["customer_id"] for h in hits}
    assert "C901" in flagged
    assert "C902" in flagged


def test_circular_transfer_detection(df):
    hits = rule_engine.rule_circular_transfers(df)
    flagged = {h["customer_id"] for h in hits}
    assert {"C910", "C911", "C912"}.issubset(flagged)


def test_ml_tool_runs_and_scores_are_bounded(df):
    features = feature_engineering.build_features(df)
    out = ml_tool.run(features)
    for r in out["ml_results"]:
        assert 0.0 <= r["ml_score"] <= 1.0


def test_risk_scoring_labels(df):
    features = feature_engineering.build_features(df)
    rule_out = rule_engine.run(df, features)
    ml_out = ml_tool.run(features)
    risk_out = risk_scoring.run(rule_out["rule_results"], ml_out["ml_results"])
    for r in risk_out["risk_report"]:
        assert r["risk_level"] in {"Low", "Medium", "High"}


def test_executor_dependency_resolution():
    order = resolve_order(["risk_score"])
    assert order.index("features") < order.index("rules")
    assert order.index("rules") < order.index("risk_score")
    assert order.index("ml") < order.index("risk_score")


def test_executor_runs_only_requested_tools_and_deps(df):
    results = execute(df, tools=["eda"])
    assert results["tools_executed"] == ["eda"]
    assert "rules" not in results


def test_keyword_fallback_intent_matching():
    plan = match_intent("Find suspicious customers")
    assert "rules" in plan["tools"]
    plan2 = match_intent("average transaction amount")
    assert plan2["tools"] == ["eda"]


def test_full_pipeline_end_to_end(df):
    results = execute(df, tools=["features", "rules", "ml", "risk_score", "explanation"])
    assert "explanation" in results
    top = results["risk_score"]["risk_report"][0]
    assert top["risk_level"] == "High"
