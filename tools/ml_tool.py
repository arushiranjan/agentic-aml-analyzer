"""
ml_tool.py
----------
Unsupervised anomaly detection over the engineered feature table using
Isolation Forest. Complements the rule engine by catching anomalies that
don't match any hand-written rule.
"""

from __future__ import annotations
from typing import Any, Dict
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = [
    "txn_count", "total_amount", "avg_amount", "std_amount",
    "unique_beneficiaries", "daily_txn_count_max", "hourly_txn_count_max",
    "velocity_score", "small_txn_ratio", "rolling_sum_7d_max", "rolling_avg_7d_max",
]


def run(features_df: pd.DataFrame, contamination: float = 0.1) -> Dict[str, Any]:
    """
    Fits Isolation Forest on the customer feature table and returns a
    normalized anomaly score in [0, 1] per customer (1 = most anomalous).
    """
    if features_df.empty or len(features_df) < 3:
        return {"ml_results": [], "message": "Not enough customers to run anomaly detection (need >= 3)."}

    X = features_df[FEATURE_COLUMNS].fillna(0).astype(float)
    X_scaled = StandardScaler().fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )
    model.fit(X_scaled)

    # decision_function: higher = more normal. Invert + normalize to [0, 1].
    raw_scores = model.decision_function(X_scaled)
    normalized = (raw_scores.max() - raw_scores) / (raw_scores.max() - raw_scores.min() + 1e-9)
    predictions = model.predict(X_scaled)  # -1 = anomaly, 1 = normal

    results = []
    for i, row in features_df.iterrows():
        results.append({
            "customer_id": row["customer_id"],
            "ml_score": round(float(normalized[i]), 3),
            "is_anomaly": bool(predictions[i] == -1),
        })

    results.sort(key=lambda r: r["ml_score"], reverse=True)
    return {"ml_results": results}
