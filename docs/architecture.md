# System Architecture — Eco-Loop Building Agents

## Overview

Eco-Loop Building Agents is an autonomous closed-loop building optimization system that combines EnergyPlus energy simulation with AI-driven reasoning to minimize energy consumption while maintaining occupant comfort. The system uses a multi-agent architecture orchestrated by LangGraph, with tools exposed via the Model Context Protocol (MCP) using FastMCP, and powered by the Qwen3 8B Instruct open-source LLM running locally through Ollama.

---

## High-Level Architecture

```mermaid
graph TB
    subgraph "Frontend — Next.js"
        UI["Dashboard UI<br/>React + TypeScript"]
        Charts["Recharts<br/>Visualizations"]
        WS["WebSocket Client"]
    end

    subgraph "Backend — FastAPI"
        API["REST API<br/>FastAPI"]
        WSS["WebSocket Server"]
        
        subgraph "Agent Layer — LangGraph"
            AG["Agent Graph<br/>Multi-Agent Orchestration"]
            SA["Sensor Agent"]
            WA["Weather Agent"]
            BSA["Building State Agent"]
            RA["Reasoning Agent"]
            PA["Planner Agent"]
            CA["Control Agent"]
            VA["Validation Agent"]
            REP["Reporting Agent"]
        end
        
        subgraph "MCP Layer — FastMCP"
            MCP["MCP Server"]
            T1["read_building_state"]
            T2["read_weather"]
            T3["run_simulation"]
            T4["update_hvac"]
            T5["update_lighting"]
            T6["update_setpoints"]
            T7["analyze_comfort"]
            T8["generate_report"]
            T9["get_historical_metrics"]
        end
        
        subgraph "Service Layer"
            ES["EnergyPlus Service"]
            SS["Simulation Service"]
            WS2["Weather Service"]
            BS["Building Service"]
        end
        
        subgraph "Data Layer"
            DB["SQLite + SQLAlchemy"]
            ALB["Alembic Migrations"]
        end
    end

    subgraph "External Systems"
        EP["EnergyPlus 24.1<br/>Building Simulation"]
        OL["Ollama<br/>Qwen3 8B Instruct"]
        IDF["IDF Building Model"]
        EPW["EPW Weather File"]
    end

    UI --> API
    Charts --> API
    WS --> WSS

    API --> AG
    AG --> SA & WA & BSA & RA & PA & CA & VA & REP
    CA --> MCP
    MCP --> T1 & T2 & T3 & T4 & T5 & T6 & T7 & T8 & T9
    T3 --> ES
    T4 & T5 & T6 --> ES
    ES --> EP
    EP --> IDF & EPW
    AG --> OL
    
    T1 & T2 & T7 & T8 & T9 --> SS & WS2 & BS
    SS & WS2 & BS --> DB
    ES --> DB

    style UI fill:#22d3ee,color:#000
    style AG fill:#8b5cf6,color:#fff
    style MCP fill:#f59e0b,color:#000
    style DB fill:#10b981,color:#fff
    style EP fill:#ef4444,color:#fff
    style OL fill:#6366f1,color:#fff
```

---

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant D as Dashboard
    participant A as FastAPI
    participant AG as Agent Graph
    participant LLM as Qwen3 8B
    participant MCP as FastMCP
    participant EP as EnergyPlus
    participant DB as SQLite

    D->>A: POST /agents/run-cycle
    A->>AG: Start optimization cycle
    
    AG->>MCP: read_building_state()
    MCP->>DB: Query latest sensor data
    DB-->>MCP: Sensor readings
    MCP-->>AG: BuildingState

    AG->>MCP: read_weather()
    MCP-->>AG: WeatherData

    AG->>LLM: Analyze state + weather
    LLM-->>AG: Reasoning + planned actions

    AG->>MCP: update_hvac(setpoints)
    MCP->>EP: Modify IDF parameters
    
    AG->>MCP: run_simulation()
    MCP->>EP: Execute EnergyPlus
    EP-->>MCP: Simulation results
    MCP->>DB: Store metrics
    MCP-->>AG: SimulationResult

    AG->>MCP: analyze_comfort()
    MCP-->>AG: ComfortMetrics

    AG->>LLM: Validate results
    LLM-->>AG: Validation pass/fail

    AG->>MCP: generate_report()
    MCP->>DB: Store report
    MCP-->>AG: Report

    AG-->>A: Cycle complete
    A-->>D: Results via WebSocket
```

---

## Layer Responsibilities

### Frontend Layer
- **Purpose**: Real-time visualization and monitoring
- **Technology**: Next.js 14, React 18, TypeScript, TailwindCSS, shadcn/ui, Recharts, Framer Motion
- **Communication**: REST API for data queries, WebSocket for live updates
- **Key Feature**: Enterprise-grade dashboard with glassmorphism dark theme

### API Layer
- **Purpose**: HTTP and WebSocket gateway
- **Technology**: FastAPI with Pydantic validation
- **Features**: Auto-generated OpenAPI docs, CORS, request validation, error handling
- **Endpoints**: 22 REST endpoints + 1 WebSocket endpoint

### Agent Layer
- **Purpose**: Multi-agent AI orchestration
- **Technology**: LangGraph state machines
- **Features**: 9 specialized agents, shared state, conditional routing, memory
- **LLM**: Qwen3 8B Instruct via Ollama (ChatOllama wrapper)

### MCP Layer
- **Purpose**: Standardized tool interface for AI agents
- **Technology**: FastMCP (Python MCP server)
- **Features**: 9 tools with auto-generated JSON schemas, stdio transport
- **Bridge**: langchain-mcp-adapters for LangGraph integration

### Service Layer
- **Purpose**: Business logic and external system integration
- **Features**: EnergyPlus simulation management, weather data processing, building state aggregation

### Data Layer
- **Purpose**: Persistent storage
- **Technology**: SQLite + SQLAlchemy ORM + Alembic migrations
- **Tables**: 8 tables covering simulations, sensors, weather, HVAC, optimization, baseline, reasoning, reports

---

## Deployment Architecture

```mermaid
graph LR
    subgraph "Docker Compose"
        B["Backend Container<br/>Python 3.11<br/>FastAPI + EnergyPlus"]
        F["Frontend Container<br/>Node 20<br/>Next.js"]
    end
    
    subgraph "Host Machine"
        O["Ollama Server<br/>Qwen3 8B"]
        V["SQLite Volume"]
    end
    
    F -->|"port 3000"| B
    B -->|"port 8000"| O
    B --> V

    style B fill:#10b981,color:#fff
    style F fill:#22d3ee,color:#000
    style O fill:#8b5cf6,color:#fff
```

- **Backend**: Docker container with Python 3.11, FastAPI, EnergyPlus 24.1 installed
- **Frontend**: Docker container with Node.js 20, Next.js 14
- **Ollama**: Runs on host machine (GPU passthrough), accessed via HTTP on port 11434
- **Database**: SQLite file mounted as Docker volume for persistence

---

## Security & Configuration

- **Environment Variables**: All config via `.env` file (no hardcoded secrets)
- **CORS**: Configured for frontend origin only
- **No External APIs**: Fully offline operation (except optional weather API)
- **Local LLM**: No data leaves the machine — Ollama runs locally
