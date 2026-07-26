"""
graph_intelligence.py
-----------------------
Goes beyond simple cycle detection (rule_engine.rule_circular_transfers)
to compute NetworkX centrality measures over the full transaction graph
and flag three additional network-level AML signals:

  - hub_account : unusually high degree (connected to many counterparties)
  - bridge_node : high betweenness centrality (sits on many shortest paths
                  between otherwise-separate clusters — a classic
                  intermediary/broker position)
  - money_mule  : high pass-through ratio (forwards nearly all received
                  funds onward — receives money and moves it out again
                  rather than accumulating or spending it)

Output hits use the SAME shape as rule_engine hits ({customer_id, rule,
score, reason}) so tools/executor.py can merge them straight into the
rule-scoring aggregation in rule_engine.run(..., extra_hits=...).
"""

from __future__ import annotations
from typing import Any, Dict, List
import numpy as np
import pandas as pd
import networkx as nx

from config import (
    HUB_DEGREE_PERCENTILE, BRIDGE_BETWEENNESS_PERCENTILE, MULE_PASSTHROUGH_RATIO,
)

MIN_DEGREE_FOR_HUB = 5


def build_graph(df: pd.DataFrame) -> nx.DiGraph:
    """Directed, weighted (amount) multigraph collapsed to single edges with summed weight/count."""
    G = nx.DiGraph()
    for _, row in df.iterrows():
        s, t, amt = str(row["customer_id"]), str(row["beneficiary_id"]), float(row["amount"])
        if G.has_edge(s, t):
            G[s][t]["weight"] += amt
            G[s][t]["count"] += 1
        else:
            G.add_edge(s, t, weight=amt, count=1)
    return G


def run(df: pd.DataFrame) -> Dict[str, Any]:
    G = build_graph(df)
    if G.number_of_nodes() < 3:
        return {"graph_hits": [], "centrality": [], "message": "Graph too small for centrality analysis."}

    degree = dict(G.degree())
    pagerank = nx.pagerank(G, weight="weight")
    # Unweighted betweenness for speed on larger graphs; still surfaces structural bridges.
    betweenness = nx.betweenness_centrality(G, weight=None)

    deg_values = np.array(list(degree.values()), dtype=float)
    deg_threshold = float(np.quantile(deg_values, HUB_DEGREE_PERCENTILE)) if len(deg_values) else 0.0
    bet_values = np.array(list(betweenness.values()), dtype=float)
    bet_threshold = float(np.quantile(bet_values, BRIDGE_BETWEENNESS_PERCENTILE)) if len(bet_values) else 0.0

    hits: List[Dict[str, Any]] = []
    centrality_table = []

    for node in G.nodes():
        in_amt = sum(d["weight"] for _, _, d in G.in_edges(node, data=True))
        out_amt = sum(d["weight"] for _, _, d in G.out_edges(node, data=True))
        passthrough_ratio = (min(in_amt, out_amt) / max(in_amt, out_amt)) if in_amt > 0 and out_amt > 0 else 0.0

        centrality_table.append({
            "customer_id": node, "degree": degree[node],
            "pagerank": round(pagerank[node], 4), "betweenness": round(betweenness[node], 4),
            "passthrough_ratio": round(passthrough_ratio, 3),
        })

        if degree[node] >= max(deg_threshold, MIN_DEGREE_FOR_HUB):
            hits.append({
                "customer_id": node, "rule": "hub_account",
                "score": round(min(1.0, degree[node] / (deg_threshold * 2 + 1e-9)), 3),
                "reason": f"High-degree hub account connected to {degree[node]} distinct counterparties.",
            })

        if bet_threshold > 0 and betweenness[node] >= bet_threshold:
            hits.append({
                "customer_id": node, "rule": "bridge_node",
                "score": round(min(1.0, betweenness[node] / (bet_threshold * 2 + 1e-9)), 3),
                "reason": "Sits on many shortest paths between otherwise unconnected counterparties (potential intermediary).",
            })

        if in_amt > 0 and out_amt > 0 and passthrough_ratio >= MULE_PASSTHROUGH_RATIO:
            hits.append({
                "customer_id": node, "rule": "money_mule",
                "score": round(passthrough_ratio, 3),
                "reason": f"Forwarded {passthrough_ratio*100:.0f}% of received funds onward almost immediately, consistent with a money-mule account.",
            })

    return {"graph_hits": hits, "centrality": sorted(centrality_table, key=lambda r: r["degree"], reverse=True)}
