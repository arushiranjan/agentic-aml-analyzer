"""System routes: /api/v1/system/health, /api/v1/system/status."""
import time
from fastapi import APIRouter, Depends
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import engine, get_db
from app.mcp.tools import TOOL_NAMES
from app.services.energyplus_service import get_energyplus_service
from app.services.llm_service import get_llm_service

router = APIRouter(prefix="/api/v1/system", tags=["system"])
_START_TIME = time.time()


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    uptime_seconds = int(time.time() - _START_TIME)
    return {
        "status": "healthy",
        "uptime": f"{uptime_seconds}s",
        "version": settings.app_version,
    }


@router.get("/status")
def status(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    inspector = inspect(engine)
    table_count = len(inspector.get_table_names())

    ep = get_energyplus_service()
    llm = get_llm_service()

    return {
        "database": {"status": "online", "tables": table_count, "url": settings.database_url},
        "energyplus": ep.status(),
        "ollama": llm.status(),
        "mcp": {"status": "ready", "tools": len(TOOL_NAMES), "tool_names": TOOL_NAMES},
        "simulation": {"status": "idle", "last_run": ep.status().get("last_run")},
    }


@router.get("/settings")
def settings_view() -> dict:
    """Read-only view of the running configuration for the Settings page.
    Per the Phase 1 spec, settings are read-only here; write support (with
    validation + hot-reload) is a later phase."""
    settings = get_settings()
    return {
        "simulation": {
            "polling_interval_seconds": settings.dashboard_polling_interval_seconds,
            "simulation_tick_minutes": 15,
        },
        "optimization": {
            "comfort_priority": settings.comfort_priority,
            "max_retries": settings.max_retries,
            "max_actions_per_cycle": settings.max_actions_per_cycle,
            "cycle_interval_minutes": settings.cycle_interval_minutes,
            "min_savings_threshold": settings.min_savings_threshold,
            "optimization_mode": "balanced",
        },
        "llm": {
            "model": settings.llm_model,
            "mode": "mock" if settings.use_mock_llm else "real",
            "temperature": settings.llm_temperature,
            "context_window": settings.llm_num_ctx,
        },
        "energyplus": {
            "mode": "mock" if settings.use_mock_energyplus else "real",
            "idf_path": settings.idf_path,
            "epw_path": settings.epw_path,
        },
        "read_only": True,
    }
