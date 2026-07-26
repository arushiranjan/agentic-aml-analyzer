"""
tests/test_pipeline.py
-----------------------
Pytest suite covering the core pipeline, the v2 features (weighted rules,
graph intelligence, model caching, confidence scoring, context builder,
planner reasoning steps, timeline, and history tracking).

Run with:  pytest tests/ -v

Uses the generated sample_data/transactions.csv, which has ELEVEN
dedicated injected patterns (see sample_data/generate_sample_data.py),
so this suite also acts as a regression check on every rule.
"""

import os
import sys
import time
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_loader import normalize_columns
from utils import model_store, history_store
from tools import feature_engineering, rule_engine, ml_tool, risk_scoring, graph_intelligence, timeline_tool
from tools.executor import execute, resolve_order
from agent.context_builder import build_context
from agent.intent_rules import match_intent
from agent.planner import build_plan

SAMPLE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "sample_data", "transactions.csv")


@pytest.fixture(scope="module")
def df():
    raw = pd.read_csv(SAMPLE_PATH)
    return normalize_columns(raw)


@pytest.fixture(scope="module")
def features(df):
    return feature_engineering.build_features(df)


# ---------------------------------------------------------------- basic sanity
def test_normalize_columns_required(df):
    for col in ["transaction_id", "customer_id", "timestamp", "amount", "beneficiary_id"]:
        assert col in df.columns


def test_optional_columns_present(df):
    """Sample data includes optional device_id/merchant_category to exercise those rules."""
    assert "device_id" in df.columns
    assert "merchant_category" in df.columns


def test_feature_engineering_no_nan(df, features):
    assert not features.isna().any().any(), "Features must not contain NaN (breaks JSON serialization)"
    assert "C901" in features["customer_id"].values


# ---------------------------------------------------------------- rule engine (11 injected patterns)
@pytest.mark.parametrize("customer_id,expected_rule", [
    ("C901", "structuring"),
    ("C903", "high_velocity"),
    ("C904", "layering"),
    ("C920", "dormant_then_active"),
    ("C930", "large_amount_anomaly"),
    ("C940", "unusual_recipient_count"),
    ("C950", "transaction_burst"),
    ("C960", "geo_anomaly"),
    ("C970", "device_anomaly"),
    ("C980", "merchant_anomaly"),
])
def test_rule_detects_injected_pattern(df, features, customer_id, expected_rule):
    graph_out = graph_intelligence.run(df)
    rule_out = rule_engine.run(df, features, extra_hits=graph_out["graph_hits"])
    entry = next((r for r in rule_out["rule_results"] if r["customer_id"] == customer_id), None)
    assert entry is not None, f"{customer_id} was not flagged by any rule at all"
    flagged_rules = {h["rule"] for h in entry["rule_hits"]}
    assert expected_rule in flagged_rules


def test_circular_transfer_detection(df):
    hits = rule_engine.rule_circular_transfers(df)
    flagged = {h["customer_id"] for h in hits}
    assert {"C910", "C911", "C912"}.issubset(flagged)


def test_rule_importance_weighting_differentiates_severity(df, features):
    """Structuring (importance 0.40) should contribute more than dormant_then_active (0.10)
    for an equivalent hit score, proving rules are NOT weighted equally."""
    from config import RULE_IMPORTANCE
    assert RULE_IMPORTANCE["structuring"] > RULE_IMPORTANCE["dormant_then_active"]
    assert RULE_IMPORTANCE["layering"] > RULE_IMPORTANCE["dormant_then_active"]


# ---------------------------------------------------------------- graph intelligence
def test_graph_intelligence_detects_money_mule(df):
    out = graph_intelligence.run(df)
    flagged = {h["customer_id"] for h in out["graph_hits"] if h["rule"] == "money_mule"}
    # C904/C905 forward almost all received funds onward (layering scenario)
    assert flagged & {"C904", "C905"}


def test_graph_intelligence_centrality_table_shape(df):
    out = graph_intelligence.run(df)
    assert len(out["centrality"]) > 0
    row = out["centrality"][0]
    assert {"customer_id", "degree", "pagerank", "betweenness"}.issubset(row.keys())


# ---------------------------------------------------------------- ML + model caching
def test_ml_tool_runs_and_scores_are_bounded(features):
    out = ml_tool.run(features)
    for r in out["ml_results"]:
        assert 0.0 <= r["ml_score"] <= 1.0


def test_ml_model_is_cached_between_calls(features):
    model_store.invalidate("pytest_cache_ds")
    out1 = ml_tool.run(features, dataset_id="pytest_cache_ds")
    assert out1["model_status"] == "trained_new_model"
    out2 = ml_tool.run(features, dataset_id="pytest_cache_ds")
    assert out2["model_status"] == "reused_cached_model"


def test_force_retrain_overrides_cache(features):
    ml_tool.run(features, dataset_id="pytest_retrain_ds")
    out = ml_tool.run(features, dataset_id="pytest_retrain_ds", force_retrain=True)
    assert out["model_status"] == "retrained_model"


# ---------------------------------------------------------------- risk scoring: confidence + evidence
def test_risk_scoring_labels_and_confidence(df, features):
    graph_out = graph_intelligence.run(df)
    rule_out = rule_engine.run(df, features, extra_hits=graph_out["graph_hits"])
    ml_out = ml_tool.run(features)
    risk_out = risk_scoring.run(rule_out["rule_results"], ml_out["ml_results"])
    for r in risk_out["risk_report"]:
        assert r["risk_level"] in {"Low", "Medium", "High"}
        assert 0.0 <= r["confidence"] <= 100.0
        assert "evidence" in r and isinstance(r["evidence"], list)
        assert r["weights_used"]["rule_weight"] + r["weights_used"]["ml_weight"] == pytest.approx(1.0)


def test_risk_scoring_configurable_weights(df, features):
    graph_out = graph_intelligence.run(df)
    rule_out = rule_engine.run(df, features, extra_hits=graph_out["graph_hits"])
    ml_out = ml_tool.run(features)
    default_out = risk_scoring.run(rule_out["rule_results"], ml_out["ml_results"])
    overridden_out = risk_scoring.run(rule_out["rule_results"], ml_out["ml_results"], rule_weight=0.9, ml_weight=0.1)
    default_map = {r["customer_id"]: r["final_score"] for r in default_out["risk_report"]}
    overridden_map = {r["customer_id"]: r["final_score"] for r in overridden_out["risk_report"]}
    assert default_map != overridden_map  # weights actually change the outcome


# ---------------------------------------------------------------- context builder
def test_context_builder_resolves_customer_existence(df):
    ctx_real = build_context(df, customer_id="C901")
    assert ctx_real.customer_exists is True
    ctx_fake = build_context(df, customer_id="NOT_A_REAL_CUSTOMER")
    assert ctx_fake.customer_exists is False


def test_context_builder_scopes_eda_but_not_population_tools(df):
    ctx = build_context(df, filters={"country": "India"})
    assert len(ctx.scoped_df) <= len(ctx.full_df)
    assert len(ctx.full_df) == len(df)  # population tools still see everything


# ---------------------------------------------------------------- executor / dependency graph
def test_executor_dependency_resolution_includes_graph():
    order = resolve_order(["risk_score"])
    assert order.index("features") < order.index("rules")
    assert order.index("graph") < order.index("rules")
    assert order.index("rules") < order.index("risk_score")
    assert order.index("ml") < order.index("risk_score")


def test_executor_runs_only_requested_tools_and_deps(df):
    ctx = build_context(df)
    results = execute(ctx, tools=["eda"])
    assert results["tools_executed"] == ["eda"]
    assert "rules" not in results


def test_executor_flags_nonexistent_customer(df):
    ctx = build_context(df, customer_id="GHOST_CUSTOMER")
    results = execute(ctx, tools=["eda"])
    assert "warning" in results


def test_full_pipeline_end_to_end(df):
    ctx = build_context(df, dataset_id="pytest_e2e_ds")
    results = execute(ctx, tools=["features", "graph", "rules", "ml", "risk_score", "explanation"])
    assert "explanation" in results
    top = results["risk_score"]["risk_report"][0]
    assert top["risk_level"] == "High"
    assert "evidence" in top


# ---------------------------------------------------------------- planner reasoning (goal + steps)
def test_keyword_fallback_produces_goal_and_steps():
    plan = match_intent("Find suspicious customers")
    assert "goal" in plan and "steps" in plan
    tool_names = {s["tool"] for s in plan["steps"]}
    assert "rules" in tool_names
    for step in plan["steps"]:
        assert step["why"]  # every step must justify itself, not just name a tool


def test_planner_falls_back_cleanly_without_api_key():
    plan = build_plan("average transaction amount")
    assert plan.tools == ["eda"]
    assert plan.source in {"llm", "fallback"}
    assert plan.goal


# ---------------------------------------------------------------- timeline
def test_timeline_flags_structuring_caption(df):
    result = timeline_tool.run(df, "C901")
    assert len(result["events"]) == 18
    assert "structuring" in result["caption"].lower()


def test_timeline_handles_unknown_customer(df):
    result = timeline_tool.run(df, "NO_SUCH_CUSTOMER")
    assert result["events"] == []


# ---------------------------------------------------------------- investigation history
def test_history_delta_tracks_score_change():
    history_store.record("pytest_hist_ds", "C1", 0.4, "Medium")
    delta = history_store.compute_delta("pytest_hist_ds", "C1", 0.8)
    assert delta["previous_score"] == 0.4
    assert delta["change"] == pytest.approx(0.4)


def test_history_delta_none_on_first_snapshot():
    delta = history_store.compute_delta("pytest_hist_ds_fresh", "C_NEW", 0.5)
    assert delta is None
