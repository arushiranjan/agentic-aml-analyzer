
% One-Page Architecture & Run Guide

## One-Page Architecture (Mermaid)

```mermaid
flowchart LR
  User[User\n(Analyst)]
  Frontend[Streamlit UI\nfrontend/app.py]
  Backend[FastAPI API\nbackend/main.py]
  Planner[Planner Agent\nagent/planner.py]
  Executor[Tool Executor\ntools/executor.py]
  EDA[EDA\ntools/eda_tool.py]
  Features[Feature Eng\ntools/feature_engineering.py]
  Rules[Rule Engine\ntools/rule_engine.py]
  ML[ML Anomaly\ntools/ml_tool.py]
  Risk[Risk Scoring\ntools/risk_scoring.py]
  Explanation[Explanation\ntools/explanation_tool.py]
  DataLoader[Data Loader\nutils/data_loader.py]
  LLMClient[LLM Client\nutils/llm_client.py]
  SampleData[(sample_data/transactions.csv)]

  User --> Frontend
  Frontend -->|HTTP| Backend
  Backend --> Planner
  Planner --> LLMClient
  Backend --> DataLoader
  Backend --> SampleData

  Backend --> Executor
  Executor --> EDA
  Executor --> Features
  Features --> Rules
  Features --> ML
  Rules --> Risk
  ML --> Risk
  Risk --> Explanation

  classDef infra fill:#f9f,stroke:#333,stroke-width:1px;
  class Backend,Planner,Executor infra;

  %% Notes: executor runs only requested tools; planner decides which tools to run
```

## Summary (short)
- Single planning agent (`agent/planner.py`) interprets user queries (LLM first, deterministic fallback via `agent/intent_rules.py`).
- Planner returns an `ExecutionPlan` listing required tools and filters.
- Executor (`tools/executor.py`) topologically resolves tool dependencies and runs only that subset (e.g., `features` → `rules` & `ml` → `risk_score` → `explanation`).
- Frontend is a thin Streamlit UI (`frontend/app.py`) that calls the FastAPI backend (`backend/main.py`).
- System supports offline demo mode: `utils/llm_client.py` returns an offline JSON plan when no API key is present; explanation tool and planner fall back to templates/keywords.

---

## Short Developer Guide — Run Locally (Windows / PowerShell)

1) Create and activate a virtual environment

```powershell
# From project root (aml-agent)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks execution, run (once) as administrator to allow scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

2) Install dependencies

```powershell
pip install -r requirements.txt
```

3) Configure environment (optional LLM)

Create a `.env` file in the project root or set environment variables in PowerShell:

```powershell
# Optional: enable OpenAI LLM features
$env:OPENAI_API_KEY = 'sk-...'
$env:OPENAI_MODEL = 'gpt-4.1'

# Backend URL used by the frontend (default shown)
$env:BACKEND_URL = 'http://localhost:8000'
```

4) Run the backend (FastAPI / Uvicorn)

```powershell
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

5) Run the frontend (Streamlit)

```powershell
# in a separate terminal (same venv)
cd frontend
streamlit run app.py
```

Frontend UI opens at http://localhost:8501. Use the **Upload Dataset** page to upload `sample_data/transactions.csv`.

6) Quick API examples (curl / PowerShell)

Upload dataset via HTTP POST (multipart):

```powershell
curl -X POST "http://localhost:8000/upload" -F "file=@..\sample_data\transactions.csv"
```

Chat example (planner + executor):

```powershell
curl -X POST "http://localhost:8000/chat" -H "Content-Type: application/json" -d "{\"query\": \"Find suspicious customers\"}"
```

Health check:

```powershell
curl http://localhost:8000/health
```

7) Run tests

```powershell
# From project root
pytest tests/ -v
```

8) Where to change behaviour

- Planner prompt & JSON schema: `agent/planner.py`
- Offline / provider swap: `utils/llm_client.py`
- Rule thresholds and signals: `tools/rule_engine.py`
- Executor orchestration: `tools/executor.py`
- Streamlit UI widgets: `frontend/app.py`

---

If you'd like, I can also: produce a PNG of the Mermaid diagram, add this file to the README, or run the test suite now and report results.
