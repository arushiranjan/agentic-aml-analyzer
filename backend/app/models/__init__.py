"""SQLAlchemy ORM models — one class per table in docs/database.md's ERD.

Phase 1 only actively writes to `simulations`, `optimization_metrics`, and
`llm_reasoning` (via the mock simulation/agent-cycle endpoints). All 8
tables are declared now so the schema matches the spec exactly and later
phases (real EnergyPlus, real agents) need no schema changes.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="pending")  # pending | running | completed | failed
    idf_path = Column(String, nullable=True)
    epw_path = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    output_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    is_baseline = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    sensor_readings = relationship("SensorReading", back_populates="simulation")
    optimization_metrics = relationship("OptimizationMetric", back_populates="simulation")
    llm_reasoning = relationship("LLMReasoning", back_populates="simulation")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=utcnow, index=True)
    zone_name = Column(String, index=True)
    indoor_temp_c = Column(Float)
    outdoor_temp_c = Column(Float)
    humidity_pct = Column(Float)
    co2_ppm = Column(Float)
    illuminance_lux = Column(Float)
    occupancy_count = Column(Integer)
    created_at = Column(DateTime, default=utcnow)

    simulation = relationship("Simulation", back_populates="sensor_readings")


class Weather(Base):
    __tablename__ = "weather"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=utcnow, index=True)
    dry_bulb_temp_c = Column(Float)
    wet_bulb_temp_c = Column(Float)
    rel_humidity_pct = Column(Float)
    wind_speed_ms = Column(Float)
    wind_direction_deg = Column(Float)
    solar_radiation_wm2 = Column(Float)
    cloud_cover = Column(String)
    created_at = Column(DateTime, default=utcnow)


class HVACAction(Base):
    __tablename__ = "hvac_actions"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=utcnow, index=True)
    action_type = Column(String)  # setpoint_change | mode_change | schedule_update
    zone_name = Column(String)
    cooling_setpoint_c = Column(Float, nullable=True)
    heating_setpoint_c = Column(Float, nullable=True)
    fan_speed_pct = Column(Float, nullable=True)
    mode = Column(String, nullable=True)  # cooling | heating | auto | off
    initiated_by = Column(String)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class OptimizationMetric(Base):
    __tablename__ = "optimization_metrics"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=utcnow)
    total_energy_kwh = Column(Float)
    hvac_energy_kwh = Column(Float)
    lighting_energy_kwh = Column(Float)
    cooling_energy_kwh = Column(Float)
    heating_energy_kwh = Column(Float)
    peak_demand_kw = Column(Float)
    cost_usd = Column(Float)
    carbon_kg = Column(Float)
    comfort_pmv = Column(Float)
    comfort_ppd = Column(Float)
    created_at = Column(DateTime, default=utcnow)

    simulation = relationship("Simulation", back_populates="optimization_metrics")


class BaselineMetric(Base):
    __tablename__ = "baseline_metrics"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=True, index=True)
    total_energy_kwh = Column(Float)
    hvac_energy_kwh = Column(Float)
    lighting_energy_kwh = Column(Float)
    cost_usd = Column(Float)
    carbon_kg = Column(Float)
    comfort_pmv = Column(Float)
    created_at = Column(DateTime, default=utcnow)


class LLMReasoning(Base):
    __tablename__ = "llm_reasoning"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=True, index=True)
    cycle_id = Column(Integer, ForeignKey("agent_cycles.id"), nullable=True, index=True)
    timestamp = Column(DateTime, default=utcnow, index=True)
    agent_name = Column(String, index=True)
    input_state = Column(Text, nullable=True)
    reasoning = Column(Text)
    planned_actions = Column(Text, nullable=True)
    tool_calls = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=True)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    simulation = relationship("Simulation", back_populates="llm_reasoning")
    cycle = relationship("AgentCycle", back_populates="steps")


class AgentCycle(Base):
    """One full Observe→Analyze→Plan→Execute→Validate→Report pass. Each of
    the per-agent steps in `run_mock_cycle()` is persisted as a linked
    `LLMReasoning` row (via `cycle_id`) so /api/v1/agents/history can return
    the cycle-level summary plus its full step-by-step trace."""

    __tablename__ = "agent_cycles"

    id = Column(Integer, primary_key=True, index=True)
    cycle_id = Column(String, unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, default=utcnow, index=True)
    status = Column(String)  # completed | reverted
    decision = Column(Text)
    confidence = Column(Float)
    duration_ms = Column(Float)
    tools_used = Column(Text, nullable=True)  # JSON list[str]
    generated_actions = Column(Text, nullable=True)  # JSON list[dict]
    validation_result = Column(Text, nullable=True)  # JSON dict
    created_at = Column(DateTime, default=utcnow)

    steps = relationship("LLMReasoning", back_populates="cycle", order_by="LLMReasoning.id")


class BuildingTick(Base):
    """One 15-minute step of the persistent building simulation (Phase 1
    Part 2). Unlike `SensorReading`/`Weather` (per-EnergyPlus-run snapshots),
    this table is the continuously-evolving mock building state — each row
    depends on the previous one so the frontend can chart a coherent
    simulation timeline instead of independent random samples."""

    __tablename__ = "building_ticks"

    id = Column(Integer, primary_key=True, index=True)
    sim_time = Column(DateTime, index=True)
    real_time = Column(DateTime, default=utcnow, index=True)
    occupancy = Column(Integer)
    outdoor_temp_c = Column(Float)
    indoor_temp_c = Column(Float)
    humidity_pct = Column(Float)
    weather_condition = Column(String)
    solar_radiation_wm2 = Column(Float)
    hvac_mode = Column(String)  # heating | cooling | idle
    hvac_status = Column(String)  # running | idle | cycling
    hvac_load_kw = Column(Float)
    lighting_load_kw = Column(Float)
    equipment_load_kw = Column(Float)
    total_energy_kw = Column(Float)
    comfort_score = Column(Float)
    carbon_kg = Column(Float)
    created_at = Column(DateTime, default=utcnow)


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow)
    report_type = Column(String)  # optimization | daily | alert | comparison
    summary = Column(Text)
    recommendations = Column(Text, nullable=True)
    energy_savings_pct = Column(Float, nullable=True)
    cost_savings_pct = Column(Float, nullable=True)
    carbon_reduction_pct = Column(Float, nullable=True)
    comfort_score = Column(Float, nullable=True)
