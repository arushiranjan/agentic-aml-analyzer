"""Quantitative Savings comparison workflow (baseline vs AI-optimized).

Implements the hackathon requirement: run a baseline EnergyPlus simulation,
run the existing AI agent cycle (unchanged — app.agents.graph.run_mock_cycle),
run EnergyPlus again with the AI's changes applied, then compute + persist
the percentage comparison between the two runs.

Reuses everything that already exists:
- app.mcp.tools.get_mcp_client()        (same MCP client the API/agents use)
- app.agents.graph.run_mock_cycle()     (the real LangGraph agent cycle)
- app.models.Simulation / BaselineMetric / OptimizationMetric / Report
  (all already had every column this needs — no schema/migration changes)

No new database columns were required: the extra comparison fields
(hvac/cooling/heating saved %, temp/PMV/PPD diff, comfort_maintained) are
stored as a JSON blob in Report.recommendations (previously unused free-text
column), alongside Report's existing plain percentage columns.
"""
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.graph import run_mock_cycle
from app.mcp.tools import get_mcp_client
from app.models import AgentCycle, BaselineMetric, BuildingTick, LLMReasoning, OptimizationMetric, Report, Simulation

# Acceptable thermal-comfort boundaries used for the "comfort maintained" check.
COMFORT_TEMP_MIN_C = 20.0
COMFORT_TEMP_MAX_C = 26.0
COMFORT_PMV_MAX_ABS = 0.5
COMFORT_PPD_MAX = 15.0


def persist_tick(db: Session, tick) -> BuildingTick:
    row = BuildingTick(
        sim_time=tick.sim_time,
        occupancy=tick.occupancy,
        outdoor_temp_c=tick.outdoor_temp_c,
        indoor_temp_c=tick.indoor_temp_c,
        humidity_pct=tick.humidity_pct,
        weather_condition=tick.weather_condition,
        solar_radiation_wm2=tick.solar_radiation_wm2,
        hvac_mode=tick.hvac_mode,
        hvac_status=tick.hvac_status,
        hvac_load_kw=tick.hvac_load_kw,
        lighting_load_kw=tick.lighting_load_kw,
        equipment_load_kw=tick.equipment_load_kw,
        total_energy_kw=tick.total_energy_kw,
        comfort_score=tick.comfort_score,
        carbon_kg=tick.carbon_kg,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def persist_agent_cycle(db: Session, result: dict) -> AgentCycle:
    """Persists one agent-cycle result (AgentCycle + its LLMReasoning steps
    + the building tick it advanced). Extracted from app/api/routes/dashboard.py
    so both the plain cycle and the new full comparison workflow share one
    persistence path instead of duplicating it."""
    building_tick = result.get("building_tick")
    if building_tick is not None:
        persist_tick(db, building_tick)

    cycle = AgentCycle(
        cycle_id=result["cycle_id"],
        timestamp=datetime.now(timezone.utc),
        status=result["status"],
        decision=result["decision"],
        confidence=result["confidence"],
        duration_ms=result["duration_ms"],
        tools_used=json.dumps(result.get("tools_used", [])),
        generated_actions=json.dumps(result.get("generated_actions", [])),
        validation_result=json.dumps(result.get("validation_result", {})),
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)

    for step in result.get("steps", []):
        db.add(LLMReasoning(
            cycle_id=cycle.id,
            agent_name=step["agent"],
            timestamp=datetime.now(timezone.utc),
            reasoning=step.get("detail", ""),
            planned_actions=json.dumps([step["action"]]),
            tool_calls=json.dumps([step["action"]]),
            confidence=step.get("confidence", result["confidence"]),
            latency_ms=step.get("latency_ms"),
        ))
    db.commit()
    return cycle


def _avg_indoor_temp(building_state: dict) -> float | None:
    zones = building_state.get("zones") or []
    temps = [z["temperature_c"] for z in zones if z.get("temperature_c") is not None]
    if not temps:
        return None
    return round(sum(temps) / len(temps), 2)


def _run_energyplus_snapshot(db: Session, is_baseline: bool) -> dict:
    """Runs one EnergyPlus pass (real or mock, whichever is configured),
    persists the Simulation row + its BaselineMetric/OptimizationMetric
    row, and returns everything compute_comparison() needs."""
    mcp = get_mcp_client()
    result = mcp.run_simulation(None, None, is_baseline)

    sim = Simulation(
        simulation_id=result["simulation_id"],
        status=result["status"],
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_seconds=result["duration_seconds"],
        output_path=result["output_path"],
        is_baseline=is_baseline,
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)

    building_state = mcp.read_building_state()
    avg_temp = _avg_indoor_temp(building_state)
    m = result["metrics"]

    if is_baseline:
        row = BaselineMetric(
            simulation_id=sim.id,
            total_energy_kwh=m["total_energy_kwh"],
            hvac_energy_kwh=m["hvac_energy_kwh"],
            lighting_energy_kwh=m["lighting_energy_kwh"],
            cost_usd=m["cost_usd"],
            carbon_kg=m["carbon_kg"],
            comfort_pmv=m["comfort_pmv"],
        )
    else:
        row = OptimizationMetric(
            simulation_id=sim.id,
            timestamp=datetime.now(timezone.utc),
            total_energy_kwh=m["total_energy_kwh"],
            hvac_energy_kwh=m["hvac_energy_kwh"],
            lighting_energy_kwh=m["lighting_energy_kwh"],
            cooling_energy_kwh=m["cooling_energy_kwh"],
            heating_energy_kwh=m["heating_energy_kwh"],
            peak_demand_kw=m["peak_demand_kw"],
            cost_usd=m["cost_usd"],
            carbon_kg=m["carbon_kg"],
            comfort_pmv=m["comfort_pmv"],
            comfort_ppd=m["comfort_ppd"],
        )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {"simulation": sim, "metrics": m, "avg_indoor_temp_c": avg_temp, "row": row}


def _pct_saved(baseline_val: float | None, optimized_val: float | None) -> float | None:
    if not baseline_val:
        return None
    return round((baseline_val - optimized_val) / baseline_val * 100, 2)


def compute_comparison(baseline: dict, optimized: dict) -> dict:
    """STEP 4: compute every percentage/diff the requirement asks for, plus
    the comfort-maintained boundary check."""
    bm, om = baseline["metrics"], optimized["metrics"]

    energy_saved_kwh = round(bm["total_energy_kwh"] - om["total_energy_kwh"], 2)
    energy_saved_percent = _pct_saved(bm["total_energy_kwh"], om["total_energy_kwh"])
    hvac_saved_percent = _pct_saved(bm["hvac_energy_kwh"], om["hvac_energy_kwh"])
    cooling_saved_percent = _pct_saved(bm.get("cooling_energy_kwh"), om.get("cooling_energy_kwh"))
    heating_saved_percent = _pct_saved(bm.get("heating_energy_kwh"), om.get("heating_energy_kwh"))
    carbon_reduction_percent = _pct_saved(bm["carbon_kg"], om["carbon_kg"])

    avg_temp_diff_c = None
    if baseline["avg_indoor_temp_c"] is not None and optimized["avg_indoor_temp_c"] is not None:
        avg_temp_diff_c = round(optimized["avg_indoor_temp_c"] - baseline["avg_indoor_temp_c"], 2)

    pmv_diff = None
    if bm.get("comfort_pmv") is not None and om.get("comfort_pmv") is not None:
        pmv_diff = round(om["comfort_pmv"] - bm["comfort_pmv"], 2)

    ppd_diff = None
    if bm.get("comfort_ppd") is not None and om.get("comfort_ppd") is not None:
        ppd_diff = round(om["comfort_ppd"] - bm["comfort_ppd"], 2)

    temp_ok = optimized["avg_indoor_temp_c"] is None or (
        COMFORT_TEMP_MIN_C <= optimized["avg_indoor_temp_c"] <= COMFORT_TEMP_MAX_C
    )
    pmv_ok = om.get("comfort_pmv") is None or abs(om["comfort_pmv"]) <= COMFORT_PMV_MAX_ABS
    ppd_ok = om.get("comfort_ppd") is None or om["comfort_ppd"] <= COMFORT_PPD_MAX
    comfort_maintained = bool(temp_ok and pmv_ok and ppd_ok)

    return {
        "energy_saved_kwh": energy_saved_kwh,
        "energy_saved_percent": energy_saved_percent,
        "hvac_saved_percent": hvac_saved_percent,
        "cooling_saved_percent": cooling_saved_percent,
        "heating_saved_percent": heating_saved_percent,
        "carbon_reduction_percent": carbon_reduction_percent,
        "avg_temp_diff_c": avg_temp_diff_c,
        "pmv_diff": pmv_diff,
        "ppd_diff": ppd_diff,
        "comfort_maintained": comfort_maintained,
        "comfort_bounds": {
            "temp_min_c": COMFORT_TEMP_MIN_C, "temp_max_c": COMFORT_TEMP_MAX_C,
            "pmv_max_abs": COMFORT_PMV_MAX_ABS, "ppd_max": COMFORT_PPD_MAX,
        },
    }


def _serialize(entry: dict) -> dict:
    m = dict(entry["metrics"])
    m["avg_indoor_temp_c"] = entry["avg_indoor_temp_c"]
    m["simulation_id"] = entry["simulation"].simulation_id
    row = entry["row"]
    m["timestamp"] = row.created_at.isoformat() if row.created_at else datetime.now(timezone.utc).isoformat()
    return m


def run_full_optimization_cycle(db: Session) -> dict:
    """STEP 1 -> 4 + 8: baseline sim, AI cycle, optimized sim, comparison,
    stored as a `Report(report_type="comparison")`. This is what
    POST /api/v1/agents/run-cycle now calls, so the full workflow runs
    automatically on every "Run AI Cycle" click with no extra user action.
    """
    baseline = _run_energyplus_snapshot(db, is_baseline=True)

    cycle_result = run_mock_cycle()
    persist_agent_cycle(db, cycle_result)

    optimized = _run_energyplus_snapshot(db, is_baseline=False)

    comparison = compute_comparison(baseline, optimized)
    baseline_payload = _serialize(baseline)
    optimized_payload = _serialize(optimized)

    report = Report(
        simulation_id=optimized["simulation"].id,
        report_type="comparison",
        summary=(
            f"AI cycle reduced total building energy by {comparison['energy_saved_percent']}% "
            f"({comparison['energy_saved_kwh']} kWh) while "
            f"{'maintaining' if comparison['comfort_maintained'] else 'NOT maintaining'} thermal comfort."
        ),
        recommendations=json.dumps({
            "baseline": baseline_payload, "optimized": optimized_payload, "comparison": comparison,
        }),
        energy_savings_pct=comparison["energy_saved_percent"],
        cost_savings_pct=_pct_saved(baseline_payload.get("cost_usd"), optimized_payload.get("cost_usd")),
        carbon_reduction_pct=comparison["carbon_reduction_percent"],
        comfort_score=optimized_payload.get("comfort_pmv"),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        **cycle_result,
        "baseline": baseline_payload,
        "optimized": optimized_payload,
        "comparison": comparison,
        "report_id": report.id,
    }


def get_latest_comparison(db: Session) -> dict | None:
    report = (
        db.query(Report)
        .filter(Report.report_type == "comparison")
        .order_by(Report.id.desc())
        .first()
    )
    if not report:
        return None
    payload = json.loads(report.recommendations)
    payload["report_id"] = report.id
    payload["created_at"] = report.created_at.isoformat() if report.created_at else None
    payload["summary"] = report.summary
    return payload


def get_comparison_history(db: Session, limit: int = 20) -> list[dict]:
    reports = (
        db.query(Report)
        .filter(Report.report_type == "comparison")
        .order_by(Report.id.desc())
        .limit(limit)
        .all()
    )
    out = []
    for report in reports:
        payload = json.loads(report.recommendations)
        out.append({
            "report_id": report.id,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "summary": report.summary,
            "comparison": payload.get("comparison", {}),
        })
    return out
