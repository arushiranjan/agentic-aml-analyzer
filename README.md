# Sentinel AML — AI-Powered Suspicious Activity Detection Agent (v3)

An **agentic AI** system for Anti-Money-Laundering (AML) suspicious activity
detection, now with a modern **React + TypeScript** enterprise dashboard in
front of the same, unmodified AI pipeline: a single planning agent that
decides which analysis tools are actually needed for each question and
runs only those, instead of a fixed sequential pipeline.

> **v3 changelog:** the Streamlit frontend has been completely replaced
> with a React + Vite + TailwindCSS + shadcn-style + Framer Motion +
> Recharts dashboard (dark, professional, Sentinel/Palantir/Linear-style
> theme). The Python AI pipeline — planner, context builder, executor,
> rule engine, feature engineering, Isolation Forest, risk scoring,
> explanation engine — is **untouched**, other than three small, additive,
> read-only endpoints and two additive data fields added purely to feed
> the new dashboard (see [What Changed on the Backend](#what-changed-on-the-backend-v3)).
> Two real bugs from the old Streamlit UI are fixed in this rewrite — see
> [Bugs Fixed in v3](#bugs-fixed-in-v3).

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Frontend](#frontend)
4. [Backend](#backend)
5. [Bugs Fixed in v3](#bugs-fixed-in-v3)
6. [What Changed on the Backend (v3)](#what-changed-on-the-backend-v3)
7. [Folder Structure](#folder-structure)
8. [Setup & Installation](#setup--installation)
9. [Running the Backend](#running-the-backend)
10. [Running the Frontend](#running-the-frontend)
11. [Training Models](#training-models)
12. [Using Existing Models](#using-existing-models)
13. [API Endpoints](#api-endpoints)
14. [Screenshots](#screenshots)
15. [Future Improvements](#future-improvements)
16. [Dataset Citation](#dataset-citation)
17. [Hackathon Notes](#hackathon-notes)

---

## Project Overview

Banks generate millions of transactions. Compliance analysts need to ask
ad-hoc questions like *"find suspicious customers"* or *"show me
structuring patterns"* without waiting for a data scientist to write a new
script every time.

The system is **one intelligent planning agent** sitting in front of seven
specialized tools (EDA, Feature Engineering, Graph Intelligence, Rule
Engine, Isolation Forest anomaly detection, Risk Scoring, Explanation
Generator). The agent reads the question, plans which tools are relevant
**and why**, executes only those, and returns an explainable,
evidence-grounded answer — surfaced through a modern enterprise console
instead of a Streamlit script.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  React + TypeScript SPA (frontend/)                                 │
│  Dashboard · Investigation · Customers · Analytics · Models ·       │
│  Settings · 404 · Loading Screen                                    │
│  React Router · Context API (dataset state) · Axios · Recharts ·    │
│  Framer Motion · Tailwind + shadcn-style primitives                 │
└───────────────────────────────┬───────────────────────────────────┘
                                 │ HTTP (axios) — /api/* proxied to :8000 in dev
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FastAPI (backend/main.py)                                          │
│  /upload /chat /eda /risk-report /train /customer/{id} /timeline    │
│  /history/{id} /graph/{id}  +  v3-only: /dataset/summary            │
│  /system/status /model/status  (read-only, additive, see below)     │
└───────────────────────────────┬───────────────────────────────────┘
                                 ▼
                    AI Planner Agent  (agent/planner.py)         — decides WHICH tools + WHY
                                 │
                    Context Builder   (agent/context_builder.py) — resolves filters + customer_id
                                 │
                    Tool Executor     (tools/executor.py)        — runs ONLY the resolved tools
                                 │
        ┌────────────┬──────────┼───────────┬────────────┬─────────────┐
        ▼            ▼          ▼           ▼            ▼             ▼
      EDA Tool   Feature Eng  Graph Intel  Rule Engine  Isolation   Explanation
                                                          Forest ML    Engine
                                                        (cached per
                                                          dataset)
```

**Nothing in the box below the FastAPI line changed in v3.** The React
app is a pure HTTP client over the exact same AI pipeline documented in
[`docs/architecture.md`](docs/architecture.md).

## Frontend

- **Stack:** React 18 + TypeScript, Vite, TailwindCSS, hand-authored
  shadcn/ui-style primitives (`src/components/ui/*` — see note below),
  Framer Motion, Lucide icons, React Router, Axios, Recharts.
- **Why hand-authored shadcn-style primitives instead of the shadcn CLI:**
  the shadcn CLI fetches component source from `ui.shadcn.com` at
  install time, which isn't reachable from a locked-down build
  environment. The primitives in `src/components/ui/` (`Button`, `Card`,
  `Badge`, `Input`, `Progress`, `Separator`, `Tabs`, `Skeleton`) are
  written in the exact same style shadcn generates — plain Tailwind +
  `class-variance-authority` + the `cn()` merge helper — so swapping in
  real shadcn components later is a drop-in replacement if you have CLI
  access.
- **Theme:** dark, professional, restrained — a single blue accent, deep
  near-black surfaces, subtle borders over heavy shadows, light
  glassmorphism only on the topbar. Modeled on Microsoft Sentinel /
  Palantir / Datadog / Linear, not a SaaS marketing gradient.
- **Pages:** Dashboard, Investigation, Customers (Customer Details),
  Analytics, Models (Model Insights), Settings, 404, and a Suspense-driven
  Loading Screen shown while each route's code-split chunk loads.
- **State management:** React Context (`DatasetContext`) holds the active
  `dataset_id` app-wide (persisted to `sessionStorage`); no Redux needed
  for an app this size. `src/lib/investigationHistory.ts` persists full
  investigation results (see [Bugs Fixed](#bugs-fixed-in-v3)).
- **Type safety:** every backend JSON shape is mirrored in
  `src/types/index.ts`; `npm run build` runs a full `tsc -b` project
  build before bundling, so a backend field rename that isn't reflected
  in the types will fail the build loudly instead of breaking silently
  in the browser.

## Backend

**Fully preserved from v2** — planner, context builder, executor, rule
engine (16 importance-weighted rules), feature engineering, graph
intelligence (hub/mule/bridge detection), Isolation Forest (cached per
dataset, not retrained per request), risk scoring (confidence + evidence
panel), and the evidence-grounded explanation engine all behave
identically to before. See [`docs/architecture.md`](docs/architecture.md)
for the full module-by-module writeup — none of it changed.

## Bugs Fixed in v3

Two concrete bugs reported against the old Streamlit frontend are fixed
by this rewrite (not patched around — actually fixed at the root cause):

1. **Dashboard crash on an empty/undefined risk table.** The old
   Streamlit code selected a fixed set of DataFrame columns
   (`df_risk.head(10)[["customer_id", ...]]`) which throws a `KeyError`
   when the risk report is empty (an empty list produces a DataFrame with
   *zero columns*, so none of the requested column names exist). The
   React Dashboard and Analytics pages never index into an assumed shape
   — every list render (`riskRows`, `explanations`, `graph_hits`, etc.) is
   guarded with `?? []` / length checks and renders an explicit `EmptyState`
   component instead of crashing.
2. **Previous chat/investigation answers disappearing.** The old
   Streamlit Chat page stored only a hardcoded placeholder string ("See
   results above.") in `st.session_state.chat_history` for the assistant
   turn, instead of the actual response — so re-rendering an earlier turn
   showed literally nothing useful (exactly the behavior in the reported
   screenshot). The new **Investigation** page's history
   (`src/lib/investigationHistory.ts`) stores the **entire** `ChatResponse`
   object per query — goal, plan steps, evidence, risk rows, explanations,
   everything — and every past investigation renders its own fully
   populated `RiskResultCard`s, permanently, not a summary placeholder.

## What Changed on the Backend (v3)

Per the instruction to preserve every backend behavior, changes were kept
to the **minimum required for React integration** — three new read-only
endpoints and two additive (backward-compatible) data fields. Nothing
existing was renamed, removed, or had its behavior altered; all 34
pre-existing backend tests still pass unmodified.

| Change | File | Why |
|---|---|---|
| `GET /dataset/summary` | `backend/main.py` | Dashboard stat cards (transaction/customer/beneficiary counts) — wraps existing `df` already loaded by `/upload`. |
| `GET /system/status` | `backend/main.py` | Dashboard "Planner Status" / "Rule Engine Status" cards — reads `agent.planner.VALID_TOOLS` and `config.RULE_IMPORTANCE`, which already existed. |
| `GET /model/status` | `backend/main.py` | Model Insights page — reads `utils/model_store.py`'s existing cache plus `ml_tool.FEATURE_COLUMNS`. |
| `trained_at` timestamp | `utils/model_store.py` | Added as a **separate** dict (`_TRAINED_AT`), so the existing `model, scaler, feature_columns = model_store.get(...)` unpacking used by `ml_tool.py` is untouched. |
| `hourly_txn_counts`, `channel_counts`, `country_counts` | `tools/eda_tool.py` `distribution_data()` | Additive keys only — `amount_histogram` and `daily_txn_counts` (used by v2) are unchanged. Powers the Analytics page's extra charts. |
| `rule_importance` field | `/system/status` response | Exposes the existing `config.RULE_IMPORTANCE` dict for the Model Insights page's rule-weight chart. |

## Folder Structure

```
project/
├── README.md
├── requirements.txt              # Python deps
├── .env.example                  # Backend env template
├── config.py                     # Rule/risk weights (unchanged from v2)
├── backend/
│   ├── main.py                   # FastAPI app (+3 new read-only endpoints)
│   └── __init__.py
├── frontend/                     # v3: React + TS + Vite (replaces Streamlit)
│   ├── package.json
│   ├── vite.config.ts            # Dev proxy: /api -> localhost:8000
│   ├── tailwind.config.js
│   ├── tsconfig*.json
│   ├── .env.example              # VITE_API_BASE_URL
│   ├── index.html
│   ├── public/shield.svg
│   └── src/
│       ├── main.tsx / App.tsx    # Router + providers
│       ├── index.css              # Dark theme CSS variables
│       ├── context/DatasetContext.tsx
│       ├── lib/
│       │   ├── api.ts             # Typed Axios wrapper over every endpoint
│       │   ├── utils.ts           # cn(), formatters
│       │   └── investigationHistory.ts  # Fixes the "lost answers" bug
│       ├── types/index.ts         # Mirrors every backend JSON shape
│       ├── components/
│       │   ├── ui/                # Hand-authored shadcn-style primitives
│       │   ├── layout/             # Sidebar, Topbar, AppLayout
│       │   ├── RiskBadge.tsx, StatCard.tsx, EvidenceList.tsx,
│       │   ├── ConfidenceGauge.tsx, PlanSteps.tsx, RiskResultCard.tsx,
│       │   └── LoadingScreen.tsx, EmptyState.tsx
│       └── pages/
│           ├── Dashboard.tsx, Investigation.tsx, CustomerDetails.tsx,
│           ├── Analytics.tsx, ModelInsights.tsx, Settings.tsx, NotFound.tsx
├── agent/                         # Unchanged: planner.py, context_builder.py, intent_rules.py
├── tools/                         # Unchanged except additive eda_tool.py fields
├── utils/                         # Unchanged except additive model_store.py timestamp
├── data/  models/                 # Scratch space
├── docs/architecture.md            # Full backend module-by-module writeup (still accurate)
├── sample_data/
│   ├── generate_sample_data.py     # 11 injected suspicious patterns
│   └── transactions.csv
└── tests/test_pipeline.py          # 34 tests — all still passing, unmodified pipeline
```

## Setup & Installation

**Requirements:** Python 3.11+, Node.js 18+ (tested on Node 22).

```bash
# Clone / unzip the project, then cd into it
cd aml-agent

# --- Backend ---
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # optional: add OPENAI_API_KEY

# --- Frontend ---
cd frontend
npm install
cp .env.example .env            # optional: override VITE_API_BASE_URL
```

## Running the Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
- Swagger docs: http://localhost:8000/docs
- Health check: `GET http://localhost:8000/health`

## Running the Frontend

In a second terminal:
```bash
cd frontend
npm run dev
```
Opens at **http://localhost:5173**. The dev server proxies `/api/*` to
`http://localhost:8000` automatically (see `vite.config.ts`) — the
browser only ever talks to one origin, so there's no CORS configuration
to worry about during development.

**Production build:**
```bash
npm run build      # outputs frontend/dist — tsc -b runs first, so type errors fail the build
npm run preview    # serve the production build locally
```
For a production deployment where the frontend and backend are on
different origins/hosts, set `VITE_API_BASE_URL` (in `frontend/.env`) to
the backend's full URL before building, e.g.
`VITE_API_BASE_URL=https://api.yourcompany.com`.

## Training Models

The Isolation Forest is trained **once per uploaded dataset** and cached
server-side (`utils/model_store.py`) — it is not refit on every query.
From the UI: **Dashboard → Upload Dataset → Train / Retrain Model**. From
the API directly:
```bash
curl -X POST "http://localhost:8000/train?dataset_id=<id>"
```

## Using Existing Models

Because the model cache is keyed by `dataset_id` and lives in the
backend process's memory, re-uploading the exact same CSV in the same
running backend session will re-register a **new** `dataset_id` (and
therefore require training again) — the cache is intentionally
per-upload, not per-file-hash, to keep the in-memory demo store simple.
Within a single dataset's session, every `/chat`, `/risk-report`, and
`/customer/{id}` call automatically reuses the cached model — check
`GET /model/status?dataset_id=<id>` any time to confirm
`"trained": true` and see `trained_at`.

## API Endpoints

| Method | Path | Added in | Description |
|---|---|---|---|
| `GET`  | `/health` | v1 | Health check |
| `POST` | `/upload` | v1 | Upload a transaction CSV |
| `POST` | `/chat` | v1 | Natural-language query → agent plan (goal+steps) → tool results |
| `POST` | `/eda` | v1 | Direct EDA-only call, bypassing the planner |
| `POST` | `/risk-report` | v1 | Full features→graph→rules→ml→risk→explanation pipeline |
| `POST` | `/train` | v2 | Explicitly (re)trains and caches the Isolation Forest |
| `GET`  | `/customer/{id}` | v1 | Full drill-down for one customer, incl. history delta |
| `GET`  | `/timeline/{id}` | v2 | Investigation Timeline (chronological events + caption) |
| `GET`  | `/history/{id}` | v2 | Past risk-score snapshots for one customer |
| `GET`  | `/graph/{id}` | v1 | Transaction graph (nodes/edges) around one customer |
| `GET`  | `/dataset/summary` | **v3** | Dataset-level counts for the Dashboard |
| `GET`  | `/system/status` | **v3** | Planner/rule-engine status + rule importance weights |
| `GET`  | `/model/status` | **v3** | Isolation Forest cache status + feature columns |

## Screenshots

> _Add screenshots here after running the app locally:_
> - `docs/screenshots/dashboard.png`
> - `docs/screenshots/investigation.png`
> - `docs/screenshots/customer_details.png`
> - `docs/screenshots/analytics.png`
> - `docs/screenshots/model_insights.png`

## Future Improvements

- Replace the in-memory dataset/model/history stores with Postgres + object storage for real persistence across backend restarts.
- Add authentication (the current build has no auth layer — add one before any real deployment).
- Server-Sent Events or WebSocket streaming for the Investigation page so long-running LLM calls show incremental progress.
- A dedicated `/customers` list endpoint (paginated) instead of deriving "top customers" from a full `/risk-report` call on the frontend.
- Real shadcn CLI components once network access to the component registry is available, as a drop-in replacement for the hand-authored primitives.
- E2E browser tests (Playwright) once a Chromium download path is available in the build environment — currently verified via `tsc -b`, `npm run build`, ESLint, and live HTTP round-trip tests against the running backend through the Vite dev proxy.

## Dataset Citation

`sample_data/transactions.csv` is **entirely synthetic**, generated by
`sample_data/generate_sample_data.py` specifically for this project — it
is not derived from any real bank, customer, or third-party dataset, and
requires no external citation. It contains ~2,200 transactions across 166
synthetic customers, with eleven deliberately injected suspicious
patterns (one per detection rule) so every rule in the pipeline has
something to find out of the box.

## Hackathon Notes

- The **entire AI pipeline is unchanged from the pre-frontend-rewrite
  version** — same planner, same 16 rules, same Isolation Forest, same
  risk scoring math. This rewrite is a frontend modernization only, as
  requested; nothing here should be read as an AI/ML capability claim
  beyond what was already implemented and tested (34 passing pytest
  cases) before this rewrite.
- The Model Insights page deliberately does **not** show a Random Forest,
  ROC curve, or confusion matrix, because this pipeline has no supervised
  labeled data and no Random Forest model — fabricating those charts
  would misrepresent the system. What's shown instead (Isolation Forest
  config, live anomaly-score distribution, rule importance weights, rule
  trigger frequency) is all real, computed from the actual loaded dataset.
- Runs fully offline: with no `OPENAI_API_KEY` set, the planner falls back
  to deterministic keyword matching and the explanation engine falls back
  to a template — the whole system, frontend included, remains fully
  functional and demoable without any external API access.
