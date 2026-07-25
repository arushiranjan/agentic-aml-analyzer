"""
rule_engine.py
--------------
Deterministic, explainable AML rules. Each rule returns a list of
(customer_id, score 0-1, reason string) hits. Scores are combined in
risk_scoring.py alongside the ML anomaly score.

Rules implemented:
  1. Structuring          - many transactions just under a reporting threshold
  2. Layering              - rapid multi-hop transfers through many beneficiaries
  3. High velocity         - too many transactions in a short window
  4. Many small transfers  - high count of low-value transfers
  5. Rapid P2P transfers   - fast back-to-back transfers to persons
  6. Dormant -> active     - long inactivity followed by a burst
  7. Circular transfers    - A->B->C->A cycles via NetworkX
  8. Large amount anomaly  - transaction far above the customer's own norm
  9. Unusual recipient count - beneficiary count far above peer norm
"""

from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd
import numpy as np
import networkx as nx

STRUCTURING_THRESHOLD = 10000
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
                           f"₹{STRUCTURING_THRESHOLD:,} reporting threshold.")
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
    incoming = df.rename(columns={"customer_id": "receiver", "beneficiary_id": "sender"})
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


def run(df: pd.DataFrame, features_df: pd.DataFrame) -> Dict[str, Any]:
    """Entry point for the Tool Executor. Runs all rules and aggregates per customer."""
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

    per_customer: Dict[str, Dict[str, Any]] = {}
    for hit in all_hits:
        cid = str(hit["customer_id"])
        entry = per_customer.setdefault(cid, {"customer_id": cid, "rule_hits": [], "rule_score": 0.0})
        entry["rule_hits"].append({"rule": hit["rule"], "score": round(hit["score"], 3), "reason": hit["reason"]})
        entry["rule_score"] = min(1.0, entry["rule_score"] + hit["score"] * 0.4)

    return {"rule_results": list(per_customer.values()), "raw_hits": all_hits}
