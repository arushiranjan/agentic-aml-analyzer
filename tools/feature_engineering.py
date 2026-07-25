"""
feature_engineering.py
-----------------------
Builds a per-customer feature table used by both the Rule Engine and the
ML Anomaly Detection tool. Kept as a separate module so the planner can
invoke it once and reuse the output for multiple downstream tools
(single source of truth, no duplicated aggregation logic).
"""

from __future__ import annotations
import pandas as pd
import numpy as np


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per customer_id with columns:

    txn_count, total_amount, avg_amount, std_amount,
    unique_beneficiaries, daily_txn_count_max, hourly_txn_count_max,
    velocity_score (txns per hour, max over any rolling 1h window),
    small_txn_ratio (fraction of txns under a "structuring" threshold),
    dormant_then_active (bool), rolling_sum_7d_max, rolling_avg_7d_max
    """
    data = df.copy()
    data["date"] = data["timestamp"].dt.date
    data["hour_bucket"] = data["timestamp"].dt.floor("h")

    STRUCTURING_THRESHOLD = 10000  # currency-agnostic threshold used across rules

    rows = []
    for cust_id, grp in data.groupby("customer_id"):
        grp = grp.sort_values("timestamp")
        txn_count = len(grp)
        total_amount = grp["amount"].sum()
        avg_amount = grp["amount"].mean()
        std_amount = grp["amount"].std()
        std_amount = 0.0 if pd.isna(std_amount) else std_amount
        unique_beneficiaries = grp["beneficiary_id"].nunique()

        daily_counts = grp.groupby("date").size()
        hourly_counts = grp.groupby("hour_bucket").size()

        # Velocity: max transactions inside any 1-hour sliding window
        velocity_score = _max_rolling_count(grp["timestamp"], window="1h")

        small_txn_ratio = float((grp["amount"] < STRUCTURING_THRESHOLD).mean())

        # Rolling 7-day sum/avg (per calendar day, then rolling)
        daily_sum = grp.set_index("timestamp")["amount"].resample("D").sum()
        rolling_sum_7d = daily_sum.rolling(7, min_periods=1).sum()
        rolling_avg_7d = daily_sum.rolling(7, min_periods=1).mean()

        # Dormant-then-active: >=30 day gap followed by a burst of activity
        gaps = grp["timestamp"].diff().dt.days.fillna(0)
        dormant_then_active = bool((gaps >= 30).any() and txn_count >= 3)

        rows.append({
            "customer_id": cust_id,
            "txn_count": txn_count,
            "total_amount": round(float(total_amount), 2),
            "avg_amount": round(float(avg_amount), 2),
            "std_amount": round(float(std_amount), 2),
            "unique_beneficiaries": int(unique_beneficiaries),
            "daily_txn_count_max": int(daily_counts.max() if len(daily_counts) else 0),
            "hourly_txn_count_max": int(hourly_counts.max() if len(hourly_counts) else 0),
            "velocity_score": int(velocity_score),
            "small_txn_ratio": round(small_txn_ratio, 3),
            "rolling_sum_7d_max": round(float(rolling_sum_7d.max() if len(rolling_sum_7d) else 0), 2),
            "rolling_avg_7d_max": round(float(rolling_avg_7d.max() if len(rolling_avg_7d) else 0), 2),
            "dormant_then_active": dormant_then_active,
        })

    return pd.DataFrame(rows)


def _max_rolling_count(timestamps: pd.Series, window: str = "1h") -> int:
    """Max number of events inside any sliding window of the given size."""
    if len(timestamps) == 0:
        return 0
    s = pd.Series(1, index=pd.DatetimeIndex(timestamps.values)).sort_index()
    counts = s.rolling(window).sum()
    return int(counts.max())


def run(df: pd.DataFrame) -> dict:
    """Entry point for the Tool Executor."""
    features_df = build_features(df)
    return {"features": features_df.to_dict(orient="records"), "_df": features_df}
