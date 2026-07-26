"""
model_store.py
----------------
Caches the fitted Isolation Forest + its StandardScaler per dataset_id, so
tools/ml_tool.py trains ONCE per dataset instead of refitting on every
single chat query ("explain customer 15" no longer re-trains a model).

In-memory dict for the hackathon; swap for joblib-on-disk or a model
registry (MLflow, S3) in production — the get/set/invalidate interface
below stays the same.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_MODEL_CACHE: Dict[str, Tuple[Any, Any, List[str]]] = {}
# dataset_id -> (fitted_model, fitted_scaler, feature_column_order)

_TRAINED_AT: Dict[str, str] = {}
# dataset_id -> ISO timestamp of last training. Kept as a SEPARATE dict rather
# than extending the tuple above, so ml_tool.py's existing
# `model, scaler, feature_columns = model_store.get(dataset_id)` unpacking
# never breaks — this is a purely additive read for the React dashboard's
# "Last Training Time" card.


def get(dataset_id: Optional[str]) -> Optional[Tuple[Any, Any, List[str]]]:
    if not dataset_id:
        return None
    return _MODEL_CACHE.get(dataset_id)


def set(dataset_id: str, model: Any, scaler: Any, feature_columns: List[str]) -> None:
    _MODEL_CACHE[dataset_id] = (model, scaler, feature_columns)
    _TRAINED_AT[dataset_id] = datetime.now(timezone.utc).isoformat()


def invalidate(dataset_id: str) -> None:
    _MODEL_CACHE.pop(dataset_id, None)
    _TRAINED_AT.pop(dataset_id, None)


def is_trained(dataset_id: Optional[str]) -> bool:
    return dataset_id is not None and dataset_id in _MODEL_CACHE


def get_trained_at(dataset_id: Optional[str]) -> Optional[str]:
    """ISO timestamp of the last time this dataset's model was (re)trained, or None."""
    if not dataset_id:
        return None
    return _TRAINED_AT.get(dataset_id)
