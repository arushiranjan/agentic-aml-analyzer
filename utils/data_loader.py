"""
data_loader.py
--------------
Loads the uploaded transaction CSV into a normalized pandas DataFrame
and holds it in a simple in-memory store keyed by dataset_id.

For a hackathon-scale project an in-memory dict is intentional —
swap `DATASETS` for Redis/Postgres in a real deployment.
"""

from __future__ import annotations
import uuid
from typing import Dict, Optional
import pandas as pd

# In-memory dataset registry: dataset_id -> DataFrame
DATASETS: Dict[str, pd.DataFrame] = {}

REQUIRED_COLUMNS = [
    "transaction_id", "customer_id", "timestamp", "amount",
    "beneficiary_id", "country", "channel",
]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case + strip column names, coerce dtypes, sort by time."""
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Uploaded CSV is missing required columns: {missing}. "
            f"Required columns are: {REQUIRED_COLUMNS}"
        )

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df = df.dropna(subset=["timestamp", "amount"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def register_dataset(df: pd.DataFrame) -> str:
    """Normalize + store a dataframe, returning a dataset_id."""
    clean = normalize_columns(df)
    dataset_id = str(uuid.uuid4())[:8]
    DATASETS[dataset_id] = clean
    return dataset_id


def get_dataset(dataset_id: str) -> Optional[pd.DataFrame]:
    return DATASETS.get(dataset_id)


def latest_dataset_id() -> Optional[str]:
    """Convenience helper for the Streamlit demo (single active dataset)."""
    if not DATASETS:
        return None
    return list(DATASETS.keys())[-1]
