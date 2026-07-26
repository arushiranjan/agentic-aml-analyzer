"""Eco-Loop Building Agents — FastAPI entrypoint.

Phase 1: mock services only. See docs/ for the full architecture spec and
each service module's docstring for exactly how it upgrades to the real
integration in later phases.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import building, dashboard, optimization, system, telemetry
from app.config import get_settings
from app.core.exceptions import EcoLoopException, ecoloop_exception_handler
from app.core.logging import setup_logging
from app.database import init_db

settings = get_settings()
setup_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Autonomous closed-loop building optimization system (Phase 1 — mock services).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(EcoLoopException, ecoloop_exception_handler)

app.include_router(system.router)
app.include_router(building.router)
app.include_router(dashboard.router)
app.include_router(optimization.router)
app.include_router(telemetry.router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "phase": "1 — mock services",
    }
