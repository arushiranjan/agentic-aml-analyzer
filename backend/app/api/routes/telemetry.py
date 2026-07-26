"""Part 5 — new history/telemetry endpoints, all backed by the persistent
`BuildingSimulator` + the `BuildingTick`/`AgentCycle` tables so the frontend
gets a real, self-consistent timeline instead of independently-random mock
data.

- GET /api/v1/simulation/history   recent building-simulation ticks
- GET /api/v1/agents/history       agent cycles + their step-by-step trace
- GET /api/v1/weather              current weather + short forecast
- GET /api/v1/occupancy            current occupancy + today's profile
- GET /api/v1/energy/history       energy breakdown history + daily/weekly totals
- GET /api/v1/carbon/history       carbon history + daily total/rolling avg/score
- GET /api/v1/building/live        one-call snapshot for the Live Building page
"""
import json
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.mcp.tools import get_mcp_client
from app.models import AgentCycle, BuildingTick
from app.services.building_simulator import CARBON_INTENSITY_KG_PER_KWH, get_building_simulator

router = APIRouter(prefix="/api/v1", tags=["telemetry"])


def _tick_dict(t: BuildingTick) -> dict:
    return {
        "sim_time": t.sim_time.isoformat(),
        "occupancy": t.occupancy,
        "outdoor_temp_c": t.outdoor_temp_c,
        "indoor_temp_c": t.indoor_temp_c,
        "humidity_pct": t.humidity_pct,
        "weather_condition": t.weather_condition,
        "solar_radiation_wm2": t.solar_radiation_wm2,
        "hvac_mode": t.hvac_mode,
        "hvac_status": t.hvac_status,
        "hvac_load_kw": t.hvac_load_kw,
        "lighting_load_kw": t.lighting_load_kw,
        "equipment_load_kw": t.equipment_load_kw,
        "total_energy_kw": t.total_energy_kw,
        "comfort_score": t.comfort_score,
        "carbon_kg": t.carbon_kg,
    }


def _recent_ticks(db: Session, limit: int) -> list[BuildingTick]:
    rows = db.query(BuildingTick).order_by(BuildingTick.sim_time.desc()).limit(limit).all()
    return list(reversed(rows))


@router.get("/simulation/history")
def simulation_history(limit: int = Query(default=96, ge=1, le=1000), db: Session = Depends(get_db)) -> dict:
    """History of the persistent building simulation clock (not to be
    confused with the one-shot `/simulation/run` EnergyPlus mock runs)."""
    sim = get_building_simulator()
    sim.current()  # ensure the clock is caught up before reading history
    ticks = _recent_ticks(db, limit)
    return {
        "count": len(ticks),
        "ticks": [_tick_dict(t) for t in ticks],
    }


@router.get("/agents/history")
def agents_history(limit: int = Query(default=20, ge=1, le=200), db: Session = Depends(get_db)) -> dict:
    cycles = db.query(AgentCycle).order_by(AgentCycle.id.desc()).limit(limit).all()
    out = []
    for c in cycles:
        out.append({
            "cycle_id": c.cycle_id,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            "status": c.status,
            "decision": c.decision,
            "confidence": c.confidence,
            "duration_ms": c.duration_ms,
            "tools_used": json.loads(c.tools_used) if c.tools_used else [],
            "generated_actions": json.loads(c.generated_actions) if c.generated_actions else [],
            "validation_result": json.loads(c.validation_result) if c.validation_result else {},
            "steps": [
                {
                    "agent": s.agent_name,
                    "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                    "reasoning": s.reasoning,
                    "confidence": s.confidence,
                    "latency_ms": s.latency_ms,
                    "tool_calls": json.loads(s.tool_calls) if s.tool_calls else [],
                }
                for s in c.steps
            ],
        })
    return {"count": len(out), "cycles": out}


@router.get("/weather")
def weather() -> dict:
    sim = get_building_simulator()
    tick = sim.current()
    forecast = []
    t = tick.sim_time
    for _ in range(8):
        t = t + timedelta(minutes=15)
        w = sim.forecast_weather(t)
        forecast.append({"time": t.strftime("%H:%M"), "temp_c": w["temp_c"], "condition": w["condition"], "solar_wm2": w["solar_wm2"]})
    return {
        "sim_time": tick.sim_time.isoformat(),
        "outdoor_temp_c": tick.outdoor_temp_c,
        "condition": tick.weather_condition,
        "humidity_pct": tick.humidity_pct,
        "solar_radiation_wm2": tick.solar_radiation_wm2,
        "forecast": forecast,
    }


@router.get("/occupancy")
def occupancy() -> dict:
    sim = get_building_simulator()
    tick = sim.current()
    profile = []
    day_start = tick.sim_time.replace(hour=0, minute=0)
    prev = 0
    for i in range(96):  # full day at 15-min resolution
        t = day_start + timedelta(minutes=15 * i)
        occ = sim.forecast_occupancy(t, previous=prev if i else None)
        prev = occ
        profile.append({"time": t.strftime("%H:%M"), "occupancy": occ})
    return {
        "sim_time": tick.sim_time.isoformat(),
        "current": tick.occupancy,
        "today_profile": profile,
    }


@router.get("/energy/history")
def energy_history(limit: int = Query(default=96, ge=1, le=1000), db: Session = Depends(get_db)) -> dict:
    sim = get_building_simulator()
    sim.current()
    ticks = _recent_ticks(db, limit)

    series = [{
        "time": t.sim_time.strftime("%H:%M"),
        "hvac": t.hvac_load_kw,
        "lighting": t.lighting_load_kw,
        "plug": t.equipment_load_kw,
        "total": t.total_energy_kw,
    } for t in ticks]

    peak_demand = max((t.total_energy_kw for t in ticks), default=0.0)

    by_day: dict[str, float] = {}
    for t in ticks:
        key = t.sim_time.strftime("%Y-%m-%d")
        by_day[key] = round(by_day.get(key, 0.0) + t.total_energy_kw * 0.25, 2)  # kW * 0.25h = kWh
    daily = [{"date": d, "kwh": v} for d, v in sorted(by_day.items())]
    weekly_total = round(sum(by_day.values()), 2)

    return {
        "series": series,
        "peak_demand_kw": round(peak_demand, 2),
        "daily_consumption_kwh": daily,
        "weekly_consumption_kwh": weekly_total,
    }


@router.get("/carbon/history")
def carbon_history(limit: int = Query(default=96, ge=1, le=1000), db: Session = Depends(get_db)) -> dict:
    sim = get_building_simulator()
    tick = sim.current()
    ticks = _recent_ticks(db, limit)

    series = [{"time": t.sim_time.strftime("%H:%M"), "carbon_kg": t.carbon_kg} for t in ticks]
    rolling_avg = round(sum(t.carbon_kg for t in ticks) / len(ticks), 3) if ticks else 0.0

    baseline_daily_kg = 45.0  # mock reference baseline for an unoptimized building
    savings_pct = max(0.0, round((1 - (tick.daily_carbon_kg / baseline_daily_kg)) * 100, 1)) if baseline_daily_kg else 0.0
    sustainability_score = max(0, min(100, round(100 - (tick.daily_carbon_kg / baseline_daily_kg) * 60)))

    return {
        "today_carbon_kg": tick.daily_carbon_kg,
        "current_carbon_kg": tick.carbon_kg,
        "carbon_intensity_kg_per_kwh": CARBON_INTENSITY_KG_PER_KWH,
        "rolling_average_kg": rolling_avg,
        "estimated_savings_pct": savings_pct,
        "sustainability_score": sustainability_score,
        "series": series,
    }


@router.get("/building/live")
def building_live(db: Session = Depends(get_db)) -> dict:
    """One-call snapshot for the Live Building page: simulator state plus
    the per-zone floor summary from the mock EnergyPlus building state."""
    sim = get_building_simulator()
    tick = sim.current()
    zones = get_mcp_client().read_building_state()

    return {
        "sim_time": tick.sim_time.isoformat(),
        "indoor_temp_c": tick.indoor_temp_c,
        "outdoor_temp_c": tick.outdoor_temp_c,
        "humidity_pct": tick.humidity_pct,
        "occupancy": tick.occupancy,
        "hvac_status": tick.hvac_status,
        "hvac_mode": tick.hvac_mode,
        "lighting_load_kw": tick.lighting_load_kw,
        "equipment_load_kw": tick.equipment_load_kw,
        "weather_condition": tick.weather_condition,
        "solar_radiation_wm2": tick.solar_radiation_wm2,
        "floor_summary": zones["zones"],
        "overall_health_score": zones["overall_health_score"],
    }
