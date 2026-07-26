"""
rule_engine.py
--------------
Deterministic, explainable AML rules. Each rule returns a list of
(customer_id, score 0-1, reason string) hits. Hits are combined in
run() using PER-RULE IMPORTANCE WEIGHTS from config.py (not flat/equal
weighting — see config.py for the rationale) alongside the ML anomaly
score from risk_scoring.py.

Rules implemented:
  1. Structuring            - many transactions just under a reporting threshold
  2. Layering                - rapid multi-hop transfers through many beneficiaries
  3. High velocity           - too many transactions in a short window
  4. Many small transfers    - high count of low-value transfers
  5. Rapid P2P transfers     - fast back-to-back transfers to persons
  6. Dormant account active  - long inactivity followed by a burst
  7. Circular transfers      - A->B->C->A cycles via NetworkX
  8. Large amount anomaly    - transaction far above the customer's own norm
  9. Unusual recipient count - beneficiary count far above peer norm
  10. Transaction burst      - many transactions inside a tight 5-minute window
  11. Geo anomaly            - transactions spanning several countries in 2 hours
  12. Device anomaly         - many distinct devices used (if device_id column present)
  13. Merchant anomaly       - many distinct merchant categories (if column present)

Plus graph-based hits (hub_account, bridge_node, money_mule) computed in
tools/graph_intelligence.py can be merged in via the `extra_hits` param of
run() — they use the same {customer_id, rule, score, reason} shape.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np
import networkx as nx

from config import (
    STRUCTURING_THRESHOLD, RULE_IMPORTANCE, DEFAULT_RULE_IMPORTANCE,
    BURST_WINDOW_MINUTES, BURST_MIN_COUNT,
    GEO_ANOMALY_WINDOW_HOURS, GEO_ANOMALY_MIN_COUNTRIES,
)

VELOCITY_LIMIT_PER_HOUR = 5
SMALL_TXN_RATIO_LIMIT = 0.6
LARGE_AMOUNT_Z_SCORE = 3.0
UNUSUAL_BENEFICIARY_COUNT = 8


def rule_structuring(features: pd.DataFrame) -> List[Dict]:
    hits = []
    for _, row in features.iterrows():
        if row["small_txn_ratio"] >= SMALL_TXN_RATIO_LIMIT and row["txn_count"] >= 5:
            hits.append({
                "customer_id": row["customer_id"], "rule": "structuring",
                "score": min(1.0, row["small_txn_ratio"]),
                "reason": (f"{row['txn_count']} transactions, "
                           f"{row['small_txn_ratio']*100:.0f}% under the "
                           f"₹{STRUCTURING_THRESHOLD:,.0f} reporting threshold.")
            })
    return hits


def rule_high_velocity(features: pd.DataFrame) -> List[Dict]:
    hits = []
    for _, row in features.iterrows():
        if row["velocity_score"] >= VELOCITY_LIMIT_PER_HOUR:
            hits.append({
                "customer_id": row["customer_id"], "rule": "high_velocity",
                "score": min(1.0, row["velocity_score"] / (VELOCITY_LIMIT_PER_HOUR * 3)),
                "reason": f"Up to {row['velocity_score']} transactions within a single hour."
            })
    return hits


def rule_many_small_transfers(features: pd.DataFrame) -> List[Dict]:
    hits = []
    for _, row in features.iterrows():
        if row["small_txn_ratio"] >= 0.8 and row["txn_count"] >= 10:
            hits.append({
                "customer_id": row["customer_id"], "rule": "many_small_transfers",
                "score": 0.7,
                "reason": f"{row['txn_count']} transactions, majority below the threshold."
            })
    return hits


def rule_dormant_then_active(features: pd.DataFrame) -> List[Dict]:
    hits = []
    for _, row in features.iterrows():
        if row["dormant_then_active"]:
            hits.append({
                "customer_id": row["customer_id"], "rule": "dormant_then_active",
                "score": 0.6,
                "reason": "Long dormant period followed by a sudden burst of activity."
            })
    return hits


def rule_large_amount_anomaly(df: pd.DataFrame, features: pd.DataFrame) -> List[Dict]:
    hits = []
    feat_idx = features.set_index("customer_id")
    for cust_id, grp in df.groupby("customer_id"):
        if cust_id not in feat_idx.index:
            continue
        mean = feat_idx.loc[cust_id, "avg_amount"]
        std = feat_idx.loc[cust_id, "std_amount"] or 1.0
        z_scores = (grp["amount"] - mean) / (std if std > 0 else 1.0)
        max_z = z_scores.max()
        if max_z >= LARGE_AMOUNT_Z_SCORE:
            hits.append({
                "customer_id": cust_id, "rule": "large_amount_anomaly",
                "score": min(1.0, max_z / (LARGE_AMOUNT_Z_SCORE * 2)),
                "reason": f"A transaction was {max_z:.1f} standard deviations above this customer's own average."
            })
    return hits


def rule_unusual_recipient_count(features: pd.DataFrame) -> List[Dict]:
    hits = []
    for _, row in features.iterrows():
        if row["unique_beneficiaries"] >= UNUSUAL_BENEFICIARY_COUNT:
            hits.append({
                "customer_id": row["customer_id"], "rule": "unusual_recipient_count",
                "score": min(1.0, row["unique_beneficiaries"] / (UNUSUAL_BENEFICIARY_COUNT * 2)),
                "reason": f"Sent money to {row['unique_beneficiaries']} distinct beneficiaries."
            })
    return hits


def rule_rapid_p2p(df: pd.DataFrame) -> List[Dict]:
    """Flags customers sending multiple transfers to distinct beneficiaries within a short window.

    Implemented as a manual sliding window (two-pointer) rather than
    pandas' `.rolling()`, since rolling cannot aggregate a non-numeric
    (beneficiary_id) column directly.
    """
    hits = []
    for cust_id, grp in df.groupby("customer_id"):
        grp = grp.sort_values("timestamp").reset_index(drop=True)
        if len(grp) < 3:
            continue
        timestamps = grp["timestamp"].tolist()
        beneficiaries = grp["beneficiary_id"].tolist()
        max_unique = 0
        left = 0
        for right in range(len(grp)):
            while timestamps[right] - timestamps[left] > pd.Timedelta(minutes=30):
                left += 1
            unique_in_window = len(set(beneficiaries[left:right + 1]))
            max_unique = max(max_unique, unique_in_window)
        if max_unique >= 3:
            hits.append({
                "customer_id": cust_id, "rule": "rapid_p2p",
                "score": min(1.0, max_unique / 6),
                "reason": f"Sent to {max_unique} distinct recipients within a 30-minute window."
            })
    return hits


def rule_layering(df: pd.DataFrame) -> List[Dict]:
    """
    Layering heuristic: customer receives funds and quickly forwards them
    onward to a different beneficiary (in -> out inside a short window),
    a classic layering signature.
    """
    hits = []
    for cust_id, out_grp in df.groupby("customer_id"):
        in_grp = df[df["beneficiary_id"] == cust_id]
        if in_grp.empty or out_grp.empty:
            continue
        matches = 0
        for _, in_txn in in_grp.iterrows():
            follow_on = out_grp[
                (out_grp["timestamp"] > in_txn["timestamp"]) &
                (out_grp["timestamp"] <= in_txn["timestamp"] + pd.Timedelta(hours=2)) &
                (out_grp["beneficiary_id"] != in_txn["customer_id"])
            ]
            matches += len(follow_on)
        if matches >= 2:
            hits.append({
                "customer_id": cust_id, "rule": "layering",
                "score": min(1.0, matches / 5),
                "reason": f"Received funds and forwarded them onward {matches} time(s) within 2 hours, consistent with layering."
            })
    return hits


def rule_circular_transfers(df: pd.DataFrame) -> List[Dict]:
    """Builds a directed graph of customer -> beneficiary transfers and finds cycles."""
    hits = []
    G = nx.DiGraph()
    for _, row in df.iterrows():
        G.add_edge(str(row["customer_id"]), str(row["beneficiary_id"]))

    try:
        cycles = list(nx.simple_cycles(G))
    except Exception:
        cycles = []

    involved: Dict[str, int] = {}
    for cycle in cycles:
        if 2 <= len(cycle) <= 6:
            for node in cycle:
                involved[node] = involved.get(node, 0) + 1

    for cust_id, cycle_count in involved.items():
        hits.append({
            "customer_id": cust_id, "rule": "circular_transfers",
            "score": min(1.0, 0.5 + 0.1 * cycle_count),
            "reason": f"Involved in {cycle_count} circular fund-transfer loop(s) (A→B→...→A)."
        })
    return hits


def rule_transaction_burst(df: pd.DataFrame) -> List[Dict]:
    """
    Modern AML technique: flags a tight burst of transactions (e.g. 45
    transfers in 5 minutes) regardless of recipient — distinct from
    rapid_p2p (which requires many DISTINCT recipients) and high_velocity
    (which looks at a 1-hour window). A burst at an unusual hour (23:00-05:00)
    scores higher.
    """
    hits = []
    window = pd.Timedelta(minutes=BURST_WINDOW_MINUTES)
    for cust_id, grp in df.groupby("customer_id"):
        grp = grp.sort_values("timestamp").reset_index(drop=True)
        timestamps = grp["timestamp"].tolist()
        if len(timestamps) < BURST_MIN_COUNT:
            continue
        left = 0
        max_count = 0
        burst_hour = None
        for right in range(len(timestamps)):
            while timestamps[right] - timestamps[left] > window:
                left += 1
            count = right - left + 1
            if count > max_count:
                max_count = count
                burst_hour = timestamps[right].hour
        if max_count >= BURST_MIN_COUNT:
            odd_hour = burst_hour is not None and (burst_hour < 5 or burst_hour >= 23)
            score = min(1.0, max_count / (BURST_MIN_COUNT * 2) + (0.2 if odd_hour else 0.0))
            hour_note = f" around {burst_hour:02d}:00" if odd_hour else ""
            hits.append({
                "customer_id": cust_id, "rule": "transaction_burst",
                "score": round(score, 3),
                "reason": f"{max_count} transactions within a {BURST_WINDOW_MINUTES}-minute window{hour_note}."
            })
    return hits


def rule_geo_anomaly(df: pd.DataFrame) -> List[Dict]:
    """
    Modern AML technique: flags impossible/implausible cross-border
    activity — e.g. transactions tagged with 3+ different countries
    within a short window, suggestive of layering across jurisdictions
    or a compromised/shared account.
    """
    hits = []
    window = pd.Timedelta(hours=GEO_ANOMALY_WINDOW_HOURS)
    for cust_id, grp in df.groupby("customer_id"):
        grp = grp.sort_values("timestamp").reset_index(drop=True)
        timestamps = grp["timestamp"].tolist()
        countries = grp["country"].tolist()
        if len(grp) < GEO_ANOMALY_MIN_COUNTRIES:
            continue
        left = 0
        max_unique = 0
        for right in range(len(grp)):
            while timestamps[right] - timestamps[left] > window:
                left += 1
            max_unique = max(max_unique, len(set(countries[left:right + 1])))
        if max_unique >= GEO_ANOMALY_MIN_COUNTRIES:
            hits.append({
                "customer_id": cust_id, "rule": "geo_anomaly",
                "score": round(min(1.0, max_unique / (GEO_ANOMALY_MIN_COUNTRIES * 2)), 3),
                "reason": f"Transactions spanned {max_unique} different countries within {GEO_ANOMALY_WINDOW_HOURS} hours."
            })
    return hits


def rule_device_anomaly(df: pd.DataFrame) -> List[Dict]:
    """Optional rule: only runs if the uploaded CSV includes a `device_id` column."""
    if "device_id" not in df.columns:
        return []
    hits = []
    for cust_id, grp in df.groupby("customer_id"):
        unique_devices = grp["device_id"].nunique()
        if unique_devices >= 4 and len(grp) >= 5:
            hits.append({
                "customer_id": cust_id, "rule": "device_anomaly",
                "score": round(min(1.0, unique_devices / 8), 3),
                "reason": f"Used {unique_devices} distinct devices to transact."
            })
    return hits


def rule_merchant_anomaly(df: pd.DataFrame) -> List[Dict]:
    """Optional rule: only runs if the uploaded CSV includes a `merchant_category` column."""
    if "merchant_category" not in df.columns:
        return []
    hits = []
    for cust_id, grp in df.groupby("customer_id"):
        unique_categories = grp["merchant_category"].nunique()
        if unique_categories >= 5:
            hits.append({
                "customer_id": cust_id, "rule": "merchant_anomaly",
                "score": round(min(1.0, unique_categories / 8), 3),
                "reason": f"Transacted across {unique_categories} unrelated merchant categories in a short period."
            })
    return hits


def run(df: pd.DataFrame, features_df: pd.DataFrame,
        extra_hits: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Entry point for the Tool Executor. Runs all rules, merges any
    `extra_hits` (e.g. graph-intelligence hub/mule/bridge hits from
    tools/graph_intelligence.py), and aggregates per customer using
    IMPORTANCE-WEIGHTED contributions rather than flat/equal weighting.
    """
    all_hits: List[Dict] = []
    all_hits += rule_structuring(features_df)
    all_hits += rule_high_velocity(features_df)
    all_hits += rule_many_small_transfers(features_df)
    all_hits += rule_dormant_then_active(features_df)
    all_hits += rule_large_amount_anomaly(df, features_df)
    all_hits += rule_unusual_recipient_count(features_df)
    all_hits += rule_rapid_p2p(df)
    all_hits += rule_layering(df)
    all_hits += rule_circular_transfers(df)
    all_hits += rule_transaction_burst(df)
    all_hits += rule_geo_anomaly(df)
    all_hits += rule_device_anomaly(df)
    all_hits += rule_merchant_anomaly(df)
    if extra_hits:
        all_hits += extra_hits

    per_customer: Dict[str, Dict[str, Any]] = {}
    for hit in all_hits:
        cid = str(hit["customer_id"])
        entry = per_customer.setdefault(cid, {"customer_id": cid, "rule_hits": [], "rule_score": 0.0})
        importance = RULE_IMPORTANCE.get(hit["rule"], DEFAULT_RULE_IMPORTANCE)
        contribution = hit["score"] * importance
        entry["rule_hits"].append({
            "rule": hit["rule"], "score": round(hit["score"], 3),
            "importance": importance, "reason": hit["reason"],
        })
        entry["rule_score"] = min(1.0, entry["rule_score"] + contribution)

    return {"rule_results": list(per_customer.values()), "raw_hits": all_hits}
