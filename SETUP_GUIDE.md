# Setup Guide

Everything below is optional — the app runs with **zero setup** using mock
services. This guide is only for switching on the real integrations.

Two files control everything: `backend/.env` (copy from `backend/.env.example`
if it doesn't exist) and, for the frontend, `frontend/.env.local` (copy from
`frontend/.env.local.example`).

---

## 1. Python environment (required)

| File to edit | — |
|---|---|
| Variable | N/A — this is a shell/venv step, not an env var |
| Example | `python3.11 -m venv backend/venv` |
| Why | The pinned dependency set in `backend/requirements.txt` (fastmcp, mcp, langgraph, langchain-core) is verified against **Python 3.11/3.12**. Python 3.13 is untested and may hit resolver or wheel-availability issues. |
| Verify | `source backend/venv/bin/activate && python --version` → should print `3.11.x` (or `3.12.x`). Then `pip install -r backend/requirements.txt` should finish with no `ResolutionImpossible` error. |

---

## 2. Real EnergyPlus (optional — default is a mock)

| Variable | `ENERGYPLUS_DIR` |
|---|---|
| File to edit | `backend/.env` |
| Example (Windows) | `E:/EnergyPlusV26-1-0` |
| Example (Linux) | `/usr/local/EnergyPlus-24-1-0` |
| Why | Points the app at the folder containing the `energyplus` / `energyplus.exe` binary, so `RealEnergyPlusService` can shell out to it. |
| Verify | Run `energyplus --version` from that directory. |

| Variable | `ENERGYPLUS_IDF` |
|---|---|
| File to edit | `backend/.env` |
| Example | `energyplus/models/SmallOffice.idf` |
| Why | The building model to simulate. Any valid EnergyPlus IDF works; the app parses whatever `Output:Variable`/`Output:Meter` objects it defines. |
| Verify | The path resolves to an existing `.idf` file on disk. |

| Variable | `ENERGYPLUS_EPW` |
|---|---|
| File to edit | `backend/.env` |
| Example | `energyplus/weather/USA_CA_San.Francisco.epw` |
| Why | Weather data for the simulation's location. |
| Verify | The path resolves to an existing `.epw` file on disk. |

| Variable | `USE_MOCK_ENERGYPLUS` |
|---|---|
| File to edit | `backend/.env` |
| Example | `false` |
| Why | Master switch. `true` (default) = zero-setup mock data. `false` = use the three paths above. |
| Verify | Restart the backend, call `GET /api/v1/system/status` → `energyplus.status` should read `"real"`. If it still says `"mock"`, the backend log will show why (missing binary, bad path, etc.) — it never fails to boot, it just falls back. |

---

## 3. Real Ollama / LLM (optional — default is a mock)

| Variable | `OLLAMA_BASE_URL` |
|---|---|
| File to edit | `backend/.env` |
| Example | `http://localhost:11434` |
| Why | Where the Ollama server is listening. Only change this if Ollama runs on another host/port (e.g. in Docker). |
| Verify | `curl http://localhost:11434/api/tags` returns a JSON list of pulled models. |

| Variable | `LLM_MODEL` |
|---|---|
| File to edit | `backend/.env` |
| Example | `qwen3:8b` |
| Why | Which pulled Ollama model `RealLLMService` calls for agent reasoning. |
| Verify | `ollama list` shows the model; `ollama pull qwen3:8b` if it doesn't. |

| Variable | `USE_MOCK_LLM` |
|---|---|
| File to edit | `backend/.env` |
| Example | `false` |
| Why | Master switch. `true` (default) = zero-setup canned reasoning text. `false` = call the real model via Ollama. |
| Verify | Restart the backend, call `GET /api/v1/system/status` → `ollama.status` should read `"real"`. If it still says `"mock"`, check the backend log (Ollama not running, or the model isn't pulled). |

---

## 4. FastMCP standalone server (optional)

Only needed if you want an external MCP client (Claude Desktop, `mcp inspect`)
to call the building tools directly. The backend's own REST API and
LangGraph agents already call the same tool functions in-process and do
**not** need this running.

| Variable | `MCP_PORT` |
|---|---|
| File to edit | `backend/.env` |
| Example | `8765` |
| Why | Port for the standalone MCP server when `MCP_TRANSPORT=sse` (network-accessible). Irrelevant for the default `stdio` transport. |
| Verify | `cd backend && python -m app.mcp.server`, then connect an MCP client to `http://MCP_HOST:MCP_PORT`. |

---

## 5. Database (usually no setup needed)

| Variable | `DATABASE_URL` |
|---|---|
| File to edit | `backend/.env` |
| Example | `sqlite:///./ecoloop.db` |
| Why | SQLite by default — the file is created automatically on first run, no setup required. Change only if you want Postgres/MySQL instead. |
| Verify | `GET /api/v1/system/status` → `database.status` should read `"online"`. |

---

## Quick end-to-end check

1. `cd backend && pip install -r requirements.txt`
2. `cp .env.example .env` (already done if `.env` exists) and edit as above.
3. `uvicorn app.main:app --reload`
4. `curl http://localhost:8000/api/v1/system/status` — confirms which
   services (database, energyplus, ollama, mcp) are running real vs. mock.
5. `cd frontend && npm install && npm run dev` — dashboard at
   `http://localhost:3000`.

No further code changes are required for either the mock or real paths —
everything above is environment configuration only.
