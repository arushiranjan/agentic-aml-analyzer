# AI-Powered Suspicious Activity Detection Agent (AML)

An **agentic AI** system for Anti-Money-Laundering (AML) suspicious activity
detection. Upload a banking transaction CSV, then ask natural-language
questions — a single planning agent decides which analysis tools are
actually needed for each question and runs only those, instead of a fixed
sequential pipeline.

> Built for a hackathon. Runs fully offline (rule-engine + keyword-fallback
> mode) with zero API key, and upgrades to full LLM-powered planning and
> explanations the moment you add an `OPENAI_API_KEY`.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Folder Structure](#folder-structure)
4. [Setup & Installation](#setup--installation)
5. [Environment Variables](#environment-variables)
6. [How to Obtain an OpenAI API Key](#how-to-obtain-an-openai-api-key)
7. [Running the Backend](#running-the-backend)
8. [Running the Frontend](#running-the-frontend)
9. [Running with the Sample Dataset](#running-with-the-sample-dataset)
10. [How the Agent Works](#how-the-agent-works)
11. [How the Rules Work](#how-the-rules-work)
12. [How the ML Model Works](#how-the-ml-model-works)
13. [How Risk Scoring Works](#how-risk-scoring-works)
14. [API Reference](#api-reference)
15. [Screenshots](#screenshots)
16. [Future Improvements](#future-improvements)

---

## Project Overview

Banks generate millions of transactions. Compliance analysts need to ask
ad-hoc questions like *"find suspicious customers"* or *"show me
structuring patterns"* without waiting for a data scientist to write a new
script every time.

This project is **one intelligent planning agent** sitting in front of six
specialized tools (EDA, Feature Engineering, Rule Engine, ML Anomaly
Detection, Risk Scoring, Explanation Generator). The agent reads the
question, decides which tools are relevant, executes only those, and
returns an explainable answer — not a canned report.

## Architecture

```
User
  │
  ▼
Streamlit Dashboard  (frontend/app.py)
  │  HTTP
  ▼
FastAPI              (backend/main.py)
  │
  ▼
AI Planner Agent     (agent/planner.py)   -- decides WHICH tools to run
  │
  ▼
Tool Executor        (tools/executor.py) -- runs ONLY those tools, in dependency order
  │
  ├── EDA Tool                 (tools/eda_tool.py)
  ├── Feature Engineering Tool (tools/feature_engineering.py)
  ├── Rule Engine              (tools/rule_engine.py)
  ├── ML Anomaly Detection     (tools/ml_tool.py)
  ├── Risk Scoring             (tools/risk_scoring.py)
  └── Explanation Generator    (tools/explanation_tool.py)
  │
  ▼
Response (JSON) → rendered by Streamlit
```

Full technical write-up: [`docs/architecture.md`](docs/architecture.md).

## Folder Structure

```
project/
├── README.md
├── requirements.txt
├── .env.example
├── backend/
│   ├── __init__.py
│   └── main.py                  # FastAPI app + endpoints
├── frontend/
│   └── app.py                   # Streamlit multi-page dashboard
├── agent/
│   ├── __init__.py
│   ├── planner.py                # THE planning agent (LLM + JSON plan)
│   └── intent_rules.py           # Keyword fallback when LLM is unavailable
├── tools/
│   ├── __init__.py
│   ├── executor.py                # Runs only the requested tools, in order
│   ├── eda_tool.py
│   ├── feature_engineering.py
│   ├── rule_engine.py
│   ├── ml_tool.py
│   ├── risk_scoring.py
│   └── explanation_tool.py
├── utils/
│   ├── __init__.py
│   ├── llm_client.py             # Swappable LLM provider wrapper
│   └── data_loader.py            # CSV validation + in-memory dataset store
├── data/                          # (scratch space for cached artifacts)
├── models/                        # (scratch space for persisted models, if added)
├── docs/
│   └── architecture.md
├── sample_data/
│   ├── generate_sample_data.py    # Regenerates the synthetic dataset
│   └── transactions.csv           # Ready-to-use sample dataset
└── tests/
    ├── __init__.py
    └── test_pipeline.py
```

## Setup & Installation

**Requirements:** Python 3.11+

```bash
# 1. Clone / unzip the project, then cd into it
cd aml-agent

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# then open .env and paste your OpenAI key (optional — see below)
```

## Environment Variables

| Variable          | Required | Default                | Description                                   |
|--------------------|----------|-------------------------|------------------------------------------------|
| `OPENAI_API_KEY`   | No       | (empty)                | Enables LLM-powered planning + explanations.   |
| `OPENAI_MODEL`     | No       | `gpt-4.1`               | Any chat-completion capable OpenAI model.      |
| `BACKEND_URL`      | No       | `http://localhost:8000`| Used by the Streamlit frontend to reach the API.|

**Without `OPENAI_API_KEY`**, the system still works end-to-end: the planner
falls back to deterministic keyword matching (`agent/intent_rules.py`) and
the explanation tool falls back to a template-based summary
(`tools/explanation_tool.py`). This is intentional so the project is always
demoable, even with no internet access to OpenAI.

## How to Obtain an OpenAI API Key

1. Go to <https://platform.openai.com/signup> and create an account (or log in).
2. Navigate to <https://platform.openai.com/api-keys>.
3. Click **"Create new secret key"**, name it (e.g. `aml-hackathon`), and copy it immediately — it's shown only once.
4. Add billing details under **Settings → Billing** if you haven't already (a few dollars of credit is enough for a hackathon demo).
5. Paste the key into your `.env` file as `OPENAI_API_KEY=sk-...`.

## Running the Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API docs (Swagger UI): <http://localhost:8000/docs>
- Health check: `GET http://localhost:8000/health`

## Running the Frontend

In a second terminal (with the same virtual environment activated):

```bash
cd frontend
streamlit run app.py
```

This opens the dashboard at <http://localhost:8501>. Make sure the backend
is running first — the sidebar's **Settings → Check backend health** button
confirms connectivity.

## Running with the Sample Dataset

A ready-made synthetic dataset with **deliberately injected suspicious
patterns** (structuring, layering, circular transfers, dormant-then-active,
high velocity, large-amount anomalies, unusual recipient counts) lives at
`sample_data/transactions.csv`. Regenerate it anytime with:

```bash
python sample_data/generate_sample_data.py
```

To demo:
1. Start backend + frontend as above.
2. On the **Upload Dataset** page, upload `sample_data/transactions.csv`.
3. Go to **Dashboard** → click **Run Full Risk Pipeline**.
4. Try the **Chat** page with: *"find suspicious customers"*, *"show
   structuring"*, *"explain customer C901"*, *"average transaction amount"*.
5. On **Network Graph**, look up `C910` with 2 hops to see the injected
   circular-transfer ring (`C910 → C911 → C912 → C910`).

## How the Agent Works

`agent/planner.py` is the **single** planning agent in this system (by
design — no multi-agent orchestration). For every user query it:

1. Sends the query + a tool catalogue to the LLM in JSON mode.
2. Parses the returned plan: `intent`, `tools`, `filters`, `customer_id`, `reasoning`.
3. Validates that every tool name is real (drops hallucinated tool names).
4. If the LLM is unavailable or returns invalid JSON, falls back to
   `agent/intent_rules.py`, a deterministic keyword matcher, so the agent
   never fully breaks.

`tools/executor.py` then expands the plan with any missing prerequisite
tools (e.g. `risk_score` requires `rules` + `ml`, which require `features`)
and executes **only** that resolved chain — this is what makes the system
dynamic rather than a fixed sequential pipeline. Asking *"average
transaction amount"* runs only the EDA tool; asking *"find suspicious
customers"* runs the full features → rules → ML → risk → explanation chain.

## How the Rules Work

`tools/rule_engine.py` implements nine deterministic, explainable AML
rules, each returning a `(customer_id, score, reason)` hit:

| Rule | Signal |
|---|---|
| Structuring | Many transactions just under a reporting threshold (₹10,000) |
| Many small transfers | High count of low-value transfers |
| High velocity | Too many transactions within any 1-hour window |
| Rapid P2P | Multiple distinct recipients within a 30-minute window (sliding window) |
| Layering | Incoming funds forwarded onward within 2 hours to a different party |
| Dormant → active | ≥30 day gap in activity followed by a burst |
| Circular transfers | Graph cycles (A→B→...→A) detected with NetworkX `simple_cycles` |
| Large amount anomaly | A transaction far above the customer's own historical average (z-score) |
| Unusual recipient count | Beneficiary count far above the typical customer |

All thresholds are named constants at the top of `rule_engine.py` for easy
tuning per jurisdiction.

## How the ML Model Works

`tools/ml_tool.py` fits a scikit-learn **Isolation Forest** over the
per-customer feature table produced by `tools/feature_engineering.py`
(transaction frequency, rolling sums/averages, velocity, unique
beneficiaries, structuring ratio, etc). The model's `decision_function`
output is inverted and min-max normalized to a `ml_score` in `[0, 1]`
(1 = most anomalous), catching patterns that don't match any hand-written
rule.

## How Risk Scoring Works

`tools/risk_scoring.py` combines both signals per customer:

```
final_score = 0.6 * rule_score + 0.4 * ml_score
```

| final_score | Label |
|---|---|
| ≥ 0.65 | **High** |
| 0.35 – 0.64 | **Medium** |
| < 0.35 | **Low** |

`tools/explanation_tool.py` then turns the top flagged customers' rule hits
and score into a plain-language explanation + recommendation (LLM-generated
when available, template-based otherwise).

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET`  | `/health` | Health check |
| `POST` | `/upload` | Upload a transaction CSV (multipart form, field `file`) |
| `POST` | `/chat` | `{query, dataset_id}` → agent plan + tool results |
| `POST` | `/eda` | Direct EDA-only call, bypassing the planner |
| `POST` | `/risk-report` | Runs the full features→rules→ml→risk→explanation pipeline |
| `GET`  | `/customer/{customer_id}` | Full drill-down for one customer |
| `GET`  | `/graph/{customer_id}` | Transaction graph (nodes/edges) around one customer |

Full interactive docs at `/docs` once the backend is running.

## Screenshots

> _Add screenshots here after running the app locally:_
> - `docs/screenshots/dashboard.png`
> - `docs/screenshots/chat.png`
> - `docs/screenshots/network_graph.png`
> - `docs/screenshots/customer_details.png`

## Future Improvements

- Persist datasets and risk reports to a real database (Postgres) instead of in-memory storage.
- Add authentication/authorization for compliance analysts.
- Support streaming LLM responses in the Chat page.
- Add a supervised model trained on labeled SAR (Suspicious Activity Report) outcomes to complement the unsupervised Isolation Forest.
- Add configurable rule thresholds via the Settings page instead of source constants.
- Batch/async processing for very large transaction volumes (Dask/Spark backend for `pandas`).
- Multi-currency normalization for the structuring threshold.
