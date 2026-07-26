You are the lead software architect and technical lead for this project.

We are building a complete end-to-end hackathon Proof-of-Concept for the following problem statement:

Eco-Loop Building Agents

The objective is to build an autonomous closed-loop building optimization system using EnergyPlus, an open-source LLM, MCP tool calling, and AI reasoning.

This project MUST satisfy every deliverable and evaluation criterion from the hackathon.

DO NOT attempt to build everything at once.

Instead, implement the project in carefully planned development phases.

Every phase MUST satisfy ALL of these requirements:

• Fully runnable
• Builds successfully
• Previous functionality must continue working
• Well documented
• Unit tested where reasonable
• GitHub ready
• Small enough for one Git commit
• Generates visible progress
• Updates README
• Updates architecture diagrams if needed

At the end of every phase, stop and wait.

Never continue to the next phase until I explicitly ask.

====================================================

GENERAL REQUIREMENTS

====================================================

Language

Backend: Python
Frontend: Next.js + React + TypeScript

Dashboard
TailwindCSS
shadcn/ui
Recharts

Backend: FastAPI
Database: SQLite
ORM: SQLAlchemy
Validation: Pydantic
Energy Simulation: EnergyPlus
EnergyPlus Python API: pyenergyplus
eppy
LLM Framework: LangGraph
MCP: FastMCP
Open Source LLM: Use Qwen3 8B Instruct.

Explain clearly WHY this model was selected.

Discuss: quality, latency, tool calling, memory, local inference, download size, license

Do NOT use OpenAI APIs.

The project must work completely offline except optional weather APIs.

Model should be downloaded locally using Ollama

Explain installation.

Prompt engineering must be documented.

====================================================

ENERGYPLUS

====================================================

Explain

What EnergyPlus is
How it works, How IDF files work, How EPW files work
How FMU differs from IDF
Whether FMU is required
Whether we will generate IDF automatically
Whether we will modify IDF
Whether we need FMU
How Python connects with EnergyPlus
How simulations are executed
How outputs are read
How controls are injected
Generate all documentation.

====================================================

DATABASE

====================================================

Design database.
Explain why SQLite is enough.
Generate migration scripts.
Create schema.
Store: Sensor history, Simulation history, Agent decisions, Weather, Optimization actions, Energy metrics, Comfort metrics, Reports, Alert history

Everything should automatically initialize when project starts.

====================================================

MCP

====================================================

Explain

What MCP is
Why MCP is required
Which implementation is selected
Why FastMCP was selected
How tool calling works
How the LLM discovers tools
Create tools including
Read Building State
Run Simulation
Read Weather
Update HVAC
Update Lighting
Update Setpoints
Retrieve Historical Metrics
Generate Report
Analyze Comfort
Everything documented.

====================================================

CLOSED LOOP

====================================================

Implement exactly the closed-loop described in the hackathon.

Observe

↓

Read sensors

↓

Reason

↓

Plan

↓

Call MCP tools

↓

Modify building

↓

Run EnergyPlus

↓

Collect metrics

↓

Compare

↓

Repeat

Every iteration must be logged.

====================================================

AGENTS

====================================================

Use LangGraph.
Create multiple agents:

Sensor Agent
Weather Agent
Building State Agent
Optimization Agent
Reasoning Agent
Planner Agent
Control Agent
Validation Agent
Reporting Agent

Each agent must have: prompt, responsibility, inputs, outputs, memory, tool access

====================================================

FRONTEND

====================================================

The dashboard must be elegant.

Use: Dark theme

Palette

Background: #0F172A

Success
Emerald

Warnings: Amber

AI Activity: Cyan

Critical: Orange

Glassmorphism
Rounded cards
Animated transitions
Professional typography
Monospace metric cards
No Streamlit.
Use Next.js.

Dashboard sections

Overview

Live Building

HVAC

Weather

Occupancy

Comfort

Energy

Carbon

Savings

Control Timeline

Agent Reasoning

Simulation Status

Sensor Table

Historical Trends

Baseline

Optimized

Savings

Reports

Settings

AI Thought Process

Every graph should update automatically.

====================================================

VISUAL REQUIREMENTS

====================================================

Design should resemble enterprise dashboards like

Datadog

Grafana

Azure Portal

Tesla Energy

Use

Tailwind

shadcn

Framer Motion

Recharts

Glass cards

Metric cards

Heatmaps

Gauge charts

Line charts

Area charts

Timeline

Decision log

====================================================

README

====================================================

Maintain an extensive README.

Update it every phase.

Must include

Overview

Problem Statement

Architecture

Folder Structure

Tech Stack

Installation

Running

Screenshots

EnergyPlus Setup

Ollama Setup

Model Download

Database

MCP

LangGraph

Dashboard

API

Folder Structure

Deployment

Future Work

Architecture diagrams

Mermaid diagrams

Sequence diagrams

Flow diagrams

Database ERD

Closed Loop Diagram

Agent Graph

Everything should be in Markdown.

====================================================

INSTALLATION

====================================================

Whenever a dependency is required

Explain

Why

How to install

Version

Commands

Expected output

Verification

Troubleshooting

Never assume software already exists.

====================================================

PROJECT STYLE

====================================================

Follow

Clean Architecture

SOLID

Modular

Typed Python

Reusable components

No giant files

Every module documented.

====================================================

IMPORTANT

The repository should look like a polished open-source GitHub repository.

Every phase must result in a working application.

The dashboard should progressively become more complete after every phase.

Never leave broken code.

Always leave the repository in a deployable state.

After every phase provide

1. Git commit message

2. Files created

3. Files modified

4. README changes

5. What can now be demonstrated

6. Next phase preview

Then STOP.