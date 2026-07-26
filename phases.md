# Eco-Loop Building Agents - Development Phases

## General Rules

The project MUST always remain in a runnable state.

At the end of every phase:

- Project should compile successfully.
- Existing functionality must not break.
- Update README.md.
- Update architecture diagrams if required.
- Add installation steps for any new dependency.
- Add screenshots/placeholders if UI changes.
- Provide a Git commit message.
- Stop after completing the phase.

---

# Phase 0 — Architecture & Project Planning

## Goal

Finalize the entire architecture before writing implementation code.

## Tasks

- Decide complete technology stack with justification.
- Explain why every technology was selected.
- Decide folder structure.
- Design complete system architecture.
- Design agent architecture.
- Design MCP architecture.
- Design closed-loop architecture.
- Design database schema.
- Design backend API structure.
- Design frontend architecture.
- Design dashboard layout.
- Create Mermaid diagrams.
- Create project roadmap.

## Important Decisions

### EnergyPlus

Decide:

- EnergyPlus version
- Why this version
- Installation steps

### Building Model

Choose one publicly available EnergyPlus example building.

Document:

- Source
- Building type
- Why selected

Store inside

energyplus/models/

### Weather

Choose one EPW weather file.

Document:

- Source
- Why selected
- How user can change weather

Store inside

energyplus/weather/

### FMU

Explicitly answer:

- Is FMU required?
- Why or why not?

If not required, explain why EnergyPlus Python API is sufficient.

### Open Source LLM

Use

Qwen3 8B Instruct

Explain

- Why Qwen
- Why not larger models
- Ollama installation
- Download command
- Resource requirements

### MCP

Use

FastMCP

Explain

- Why FastMCP
- Tool calling
- Tool discovery
- LangGraph integration

### Database

Design complete ER diagram.

Tables should include

- simulations
- sensor_readings
- weather
- hvac_actions
- optimization_metrics
- baseline_metrics
- llm_reasoning
- reports

### Dashboard

Design complete UI.

No coding.

Need wireframes.

Need color palette.

Need layout.

Need graphs.

---

Expected Output

- Complete architecture
- README (40%)
- Mermaid diagrams
- Development roadmap

Git Commit

docs: finalize architecture and implementation roadmap

---

# Phase 1 — Project Foundation

## Goal

Create complete project skeleton.

## Backend

- FastAPI
- Config management
- Logging
- Environment variables
- SQLite initialization
- SQLAlchemy
- Alembic

## Frontend

- Next.js
- TypeScript
- Tailwind
- shadcn/ui
- Theme setup

## Project

- Docker
- Docker Compose
- GitHub Actions
- requirements.txt
- package.json

## Dashboard

Landing dashboard.

Display

- System Status
- Database Status
- EnergyPlus Status
- LLM Status
- MCP Status

Everything should compile.

README updated.

Git Commit

feat: initialize project foundation

---

# Phase 2 — EnergyPlus Integration

## Goal

Integrate EnergyPlus simulation.

## Tasks

Install

- EnergyPlus
- pyenergyplus
- eppy

Add

- Building model (.idf)
- Weather (.epw)

Create

EnergyPlusService

Features

- Run simulation
- Read outputs
- Parse metrics
- Read sensor values

Generate

BuildingState object.

No AI yet.

Dashboard

Display

- Indoor temperature
- Outdoor temperature
- HVAC load
- Cooling
- Heating
- Occupancy
- Energy usage

README

Explain

- IDF
- EPW
- Why FMU isn't used
- How EnergyPlus works

Git Commit

feat: integrate EnergyPlus simulation engine

---

# Phase 3 — Backend APIs & Dashboard

## Goal

Create complete monitoring platform.

## Backend

Create APIs

- Current Building State
- Sensor History
- Simulation History
- Weather
- Energy Metrics
- Comfort Metrics

Store everything in SQLite.

## Dashboard

Implement professional dashboard.

Show

- Live metrics
- Energy graph
- Temperature graph
- HVAC graph
- Occupancy
- Weather
- Timeline
- Historical charts

No AI yet.

README updated.

Git Commit

feat: implement simulation monitoring dashboard

---

# Phase 4 — AI Agent + MCP Integration

## Goal

Integrate autonomous reasoning.

Install

- Ollama
- Qwen3 8B
- LangGraph
- FastMCP

Create MCP Tools

- Read Building State
- Read Weather
- Run Simulation
- Update HVAC
- Update Lighting
- Analyze Comfort
- Generate Report

Create Agents

- Sensor Agent
- Weather Agent
- Reasoning Agent
- Planner Agent
- Control Agent

Dashboard

Add

AI Reasoning panel

Display

- Thoughts
- Confidence
- Tool Calls
- Planned Actions

README

Document

- Ollama installation
- Model download
- MCP setup
- LangGraph architecture

Git Commit

feat: integrate AI reasoning with MCP tools

---

# Phase 5 — Closed Loop Optimization

## Goal

Implement autonomous optimization.

Implement

Observe

↓

Read sensors

↓

Reason

↓

Plan

↓

Execute MCP tools

↓

Run simulation

↓

Read new state

↓

Repeat

Add

Validation Agent

Safety checks

Baseline simulation

Optimized simulation

Database

Store every iteration.

Dashboard

Show

Baseline

vs

Optimized

Display

- Savings
- Comfort
- Carbon
- Cost
- HVAC runtime

Git Commit

feat: implement autonomous closed-loop optimization

---

# Phase 6 — Enterprise Dashboard

## Goal

Transform dashboard into professional control center.

Theme

Background

#0F172A

Accent

Emerald

Warnings

Amber

AI

Cyan

Critical

Orange

Glassmorphism

Animations

Framer Motion

Charts

- Energy timeline
- Carbon
- Comfort
- HVAC
- Occupancy
- Weather
- PMV
- Savings
- Baseline comparison
- Control timeline

Cards

- Current Energy
- Savings
- Cost
- Comfort
- Carbon
- AI Status
- Occupancy

Panels

- AI Thoughts
- Decision Timeline
- MCP Activity
- Building State
- Weather
- Historical Trends

README

Add screenshots.

Git Commit

feat: build enterprise energy intelligence dashboard

---

# Phase 7 — Finalization & Hackathon Submission

## Goal

Prepare final submission.

Complete

README

Architecture

Mermaid diagrams

ER Diagram

API Documentation

Deployment guide

Installation guide

Testing guide

Generate

Sample reports

Demo dataset

Presentation assets

Submission checklist

Ensure

Everything runs end-to-end.

Verify

- EnergyPlus
- Backend
- Frontend
- Database
- Ollama
- MCP
- LangGraph
- Dashboard

Git Commit

docs: finalize documentation and hackathon submission