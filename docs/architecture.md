# Architecture & Workflow Documentation

This document explains every module, every API endpoint, the execution
flow, and the agent's reasoning process in detail.

## 1. High-Level Flow

```
1. Analyst uploads a CSV            -> POST /upload
2. Analyst types a question         -> POST /chat  {query, dataset_id}
3. agent/planner.py builds a plan   -> {intent, tools, filters, customer_id, reasoning}
4. tools/executor.py resolves deps  -> expands plan into a valid run order
5. Only the required tools run      -> results merged into one dict
6. FastAPI returns JSON             -> Streamlit renders it
```

## 2. Module-by-Module Explanation

### `utils/llm_client.py`
Wraps whichever LLM provider is configured. Every other module calls
`get_llm_client().complete(prompt, system=..., json_mode=...)` and never
imports `openai` directly — swapping providers means editing only this
file (implement a new `BaseLLMClient` subclass, update `get_llm_client()`).
Exposes an `available` flag so callers (the planner) can proactively skip
straight to a deterministic fallback instead of making a network call that
is guaranteed to fail.

### `utils/data_loader.py`
Validates and normalizes an uploaded CSV (column names lower-cased,
`timestamp` parsed to datetime, `amount` coerced to numeric, invalid rows
dropped). Stores DataFrames in an in-memory dict keyed by a short
`dataset_id`. Swap `DATASETS` for Redis/Postgres for a production
deployment; the interface (`register_dataset`, `get_dataset`) stays the
same.

### `agent/intent_rules.py`
A deterministic, regex/keyword-based intent matcher. This is the safety
net: if the LLM is missing, mis-configured, or returns malformed JSON, the
system falls back to this matcher so the demo never fully breaks. It also
extracts simple entities (`country`, `customer_id`) via regex.

### `agent/planner.py`
**The single planning agent.** Responsibilities:
1. Build a system prompt describing the six available tools and give the
   LLM few-shot examples of query → tool-list mappings.
2. Call the LLM in JSON mode, requesting `{intent, tools, filters,
   customer_id, reasoning}`.
3. Validate the returned tool names against `VALID_TOOLS`, dropping any
   hallucinated tool.
4. On any parsing failure, or if the LLM client reports `available =
   False`, delegate to `agent/intent_rules.match_intent()` instead.

The planner returns an `ExecutionPlan` dataclass, never raw dicts, so the
FastAPI layer and executor have a typed contract.

### `tools/executor.py`
Owns the **dependency graph** between tools:

```python
DEPENDENCIES = {
    "eda": [],
    "features": [],
    "rules": ["features"],
    "ml": ["features"],
    "risk_score": ["rules", "ml"],
    "explanation": ["risk_score"],
}
```

`resolve_order()` performs a simple DFS-based topological expansion so that
even if the planner only asked for `["risk_score"]`, the executor correctly
runs `features → rules → ml → risk_score` in order, without ever running
`explanation` unless it (or something depending on it) was actually
requested. This is the mechanism that makes the system "agentic" rather
than a fixed sequential pipeline — **the set of tools that runs is a
function of the question**, not a hardcoded sequence.

### `tools/eda_tool.py`
Pure pandas/numpy descriptive statistics: missing-value report,
transaction statistics (count, sum, mean, median, std, min, max), per
customer statistics, and Plotly-ready histogram/timeline data. Shares a
single `apply_filters()` helper (country, channel, customer_id, amount
range, date range) with every other tool that accepts filters.

### `tools/feature_engineering.py`
Builds one row per `customer_id` with the AML-relevant features every
downstream tool needs: `txn_count`, `total_amount`, `avg_amount`,
`std_amount`, `unique_beneficiaries`, `daily_txn_count_max`,
`hourly_txn_count_max`, `velocity_score` (max transactions in any rolling
1-hour window), `small_txn_ratio` (fraction under the structuring
threshold), `rolling_sum_7d_max`, `rolling_avg_7d_max`, and
`dormant_then_active` (boolean). Computed **once** and reused by both the
Rule Engine and the ML tool — no duplicated aggregation logic.

### `tools/rule_engine.py`
Nine independent, explainable rule functions (see README for the full
table). Each returns `{customer_id, rule, score, reason}` hits; `run()`
aggregates all hits per customer into a single `rule_score` (capped at 1.0)
plus the list of individual hits (used later for explanations). Circular
transfers use `networkx.simple_cycles()` over a directed graph built from
every `customer_id -> beneficiary_id` edge.

### `tools/ml_tool.py`
Fits a `sklearn.ensemble.IsolationForest` (200 trees, configurable
contamination) on the standardized feature table. `decision_function`
output (higher = more normal) is inverted and min-max scaled to
`ml_score ∈ [0, 1]`. Requires at least 3 customers to fit meaningfully.

### `tools/risk_scoring.py`
Merges rule and ML output per customer:
`final_score = 0.6 * rule_score + 0.4 * ml_score`, then labels `High` (≥
0.65), `Medium` (0.35–0.64), or `Low` (< 0.35). Weights and thresholds are
named constants at the top of the file.

### `tools/explanation_tool.py`
For the top-N riskiest customers, builds a plain-language explanation +
recommendation. Prefers the LLM (concise, 2–4 sentence, no hallucinated
facts — the prompt explicitly constrains it to the given structured data);
falls back to a deterministic string-template when no LLM is configured.

### `backend/main.py`
FastAPI app wiring everything together. See the README's API Reference
table for the endpoint list. Notably, `/chat` is the only endpoint that
goes through the planner — `/eda` and `/risk-report` are direct
tool-executor calls for dashboard widgets that always need the same data.

### `frontend/app.py`
Streamlit multi-page dashboard (`Dashboard`, `Upload Dataset`, `Chat`,
`Suspicious Transactions`, `Customer Details`, `Network Graph`,
`Analytics`, `Settings`). Pure HTTP client over the FastAPI backend — no
business logic lives in the frontend.

## 3. Agent Reasoning Example

**Query:** *"Find suspicious customers."*

1. Planner LLM call returns:
   ```json
   {
     "intent": "find_suspicious",
     "tools": ["features", "rules", "ml", "risk_score", "explanation"],
     "filters": {},
     "customer_id": null,
     "reasoning": "Suspicious-customer detection requires the full rule + ML + risk pipeline with explanations."
   }
   ```
2. Executor resolves order (already minimal here): `features -> rules ->
   ml -> risk_score -> explanation`.
3. Each tool runs once, in order, passing its output to the next.
4. Response includes `plan` (for transparency/debugging in the UI) and
   `results` (the actual tool outputs).

**Query:** *"Average transaction amount."*

1. Planner returns `{"tools": ["eda"], ...}`.
2. Executor resolves order: `["eda"]` — no other tool runs.
3. Response is near-instant since no ML/rule computation happens at all.

This asymmetry (cheap questions run cheap tools, complex questions run the
full chain) is the core "agentic" behavior demonstrated by this project.
