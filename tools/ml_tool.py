"""
ml_tool.py
----------
Unsupervised anomaly detection over the engineered feature table using
Isolation Forest. Complements the rule engine by catching anomalies that
don't match any hand-written rule.

IMPORTANT: the model is trained ONCE per dataset and cached in
utils/model_store.py, keyed by dataset_id. Every subsequent query against
the same dataset (e.g. "explain customer 15" run ten times) REUSES the
cached model + scaler instead of re-fitting Isolation Forest from
scratch — this matters once datasets get large. Pass force_retrain=True
(e.g. from the /train endpoint) to explicitly refit.
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from utils import model_store

FEATURE_COLUMNS = [
    "txn_count", "total_amount", "avg_amount", "std_amount",
    "unique_beneficiaries", "daily_txn_count_max", "hourly_txn_count_max",
    "velocity_score", "small_txn_ratio", "rolling_sum_7d_max", "rolling_avg_7d_max",
]


def _fit_new_model(X: pd.DataFrame, contamination: float):
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = IsolationForest(n_estimators=200, contamination=contamination, random_state=42)
    model.fit(X_scaled)
    return model, scaler, X_scaled


def run(features_df: pd.DataFrame, dataset_id: Optional[str] = None,
        contamination: float = 0.1, force_retrain: bool = False) -> Dict[str, Any]:
    """
    Fits (or reuses a cached) Isolation Forest on the customer feature
    table and returns a normalized anomaly score in [0, 1] per customer
    (1 = most anomalous).
    """
    if features_df.empty or len(features_df) < 3:
        return {"ml_results": [], "model_status": "skipped",
                "message": "Not enough customers to run anomaly detection (need >= 3)."}

    X = features_df[FEATURE_COLUMNS].fillna(0).astype(float)

    cached = model_store.get(dataset_id) if dataset_id else None
    if cached and not force_retrain:
        model, scaler, feature_columns = cached
        X_scaled = scaler.transform(X[feature_columns])
        model_status = "reused_cached_model"
    else:
        model, scaler, X_scaled = _fit_new_model(X, contamination)
        if dataset_id:
            model_store.set(dataset_id, model, scaler, FEATURE_COLUMNS)
        model_status = "trained_new_model" if not cached else "retrained_model"

    raw_scores = model.decision_function(X_scaled)  # higher = more normal
    normalized = (raw_scores.max() - raw_scores) / (raw_scores.max() - raw_scores.min() + 1e-9)
    predictions = model.predict(X_scaled)  # -1 = anomaly, 1 = normal

    results = []
    for i, row in features_df.reset_index(drop=True).iterrows():
        results.append({
            "customer_id": row["customer_id"],
            "ml_score": round(float(normalized[i]), 3),
            "is_anomaly": bool(predictions[i] == -1),
        })

    results.sort(key=lambda r: r["ml_score"], reverse=True)
    return {"ml_results": results, "model_status": model_status}
