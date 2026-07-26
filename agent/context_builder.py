"""
context_builder.py
--------------------
Sits architecturally BETWEEN the Planner and the Executor:

    Planner -> Context Builder -> Executor

Takes the raw plan output (filters, customer_id) plus the full dataset
and:
  - resolves/validates the customer_id (does it actually exist in this
    dataset? tools no longer each need to check this themselves)
  - applies filters ONCE to produce a scoped view for filter-aware tools
    (currently: EDA)
  - deliberately leaves population-level tools (features / rules / ml /
    graph) pointed at the FULL dataset, since AML detection needs the
    whole customer population as a statistical baseline — filtering it
    per-query would silently break z-score and percentile-based rules.

Centralizing this here means individual tools stay simple (just "give me
a dataframe") and adding a new tool later doesn't require re-implementing
filter/customer-resolution logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pandas as pd

from tools.eda_tool import apply_filters


@dataclass
class ExecutionContext:
    full_df: pd.DataFrame
    scoped_df: pd.DataFrame                 # filters already applied — used by EDA-style tools
    filters: Dict[str, Any] = field(default_factory=dict)
    customer_id: Optional[str] = None
    customer_exists: bool = True
    dataset_id: Optional[str] = None


def build_context(df: pd.DataFrame, filters: Optional[Dict[str, Any]] = None,
                   customer_id: Optional[str] = None, dataset_id: Optional[str] = None) -> ExecutionContext:
    filters = filters or {}
    scoped_df = apply_filters(df, filters)

    customer_exists = True
    if customer_id is not None:
        customer_exists = bool((df["customer_id"].astype(str) == str(customer_id)).any())

    return ExecutionContext(
        full_df=df,
        scoped_df=scoped_df,
        filters=filters,
        customer_id=customer_id,
        customer_exists=customer_exists,
        dataset_id=dataset_id,
    )
