"""Persistent building simulation engine — Phase 1 Part 2.

`MockEnergyPlusService` (energyplus_service.py) still answers the explicit
"Run Simulation" button with an independent one-shot EnergyPlus-style run.
This module is different: it is a continuously-evolving mock building whose
state at tick N is always derived from tick N-1 (simulation clock, weather,
occupancy, indoor temperature, HVAC, energy, comfort, carbon), so the
Live Building / Energy / Carbon pages and the agent's "Observe" step see a
physically-plausible, coherent timeline instead of independent random
samples.

Real EnergyPlus (a later phase) will eventually replace `_advance_one_tick`'s
simplified physics with actual IDF/EPW-driven output while keeping the same
`BuildingSimulatorState` shape, so callers do not change.

Design notes:
  - One in-process singleton (`get_building_simulator()`) holds the current
    state. Callers that want history persist a snapshot to the
    `BuildingTick` table themselves (see api/routes/telemetry.py) — this
    module has no DB dependency, matching the existing service pattern.
  - `advance_if_due()` performs a lazy "auto-tick": each real-world
    `SECONDS_PER_TICK` that passes, the simulated clock moves forward one
    15-minute step, so the dashboard visibly progresses just from polling
    without needing a background scheduler/Celery/etc. (out of scope for
    Phase 1). `force_tick()` is used when the AI agent cycle or the explicit
    simulation-run endpoint wants to advance deliberately.
"""
import math
import random
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone

SECONDS_PER_TICK = 15  # 1 wall-clock cycle of this many seconds == 15 sim-minutes
TICK_MINUTES = 15
COMFORT_TARGET_C = 22.0
CARBON_INTENSITY_KG_PER_KWH = 0.42  # grid average, mock constant
MIN_TARGET_C = 18.0
MAX_TARGET_C = 28.0


def _round(x: float, n: int = 2) -> float:
    return round(x, n)


@dataclass
class BuildingSimulatorState:
    sim_time: datetime
    occupancy: int
    outdoor_temp_c: float
    indoor_temp_c: float
    humidity_pct: float
    weather_condition: str
    solar_radiation_wm2: float
    hvac_mode: str
    hvac_status: str
    hvac_load_kw: float
    lighting_load_kw: float
    equipment_load_kw: float
    total_energy_kw: float
    comfort_score: float
    carbon_kg: float
    daily_carbon_kg: float = 0.0

    def as_dict(self) -> dict:
        d = asdict(self)
        d["sim_time"] = self.sim_time.isoformat()
        return d


class BuildingSimulator:
    def __init__(self) -> None:
        self.target_temp_c = COMFORT_TARGET_C
        self.hvac_override: str | None = None  # None | "cooling" | "heating" | "off" — set via control_hvac
        self.last_control_action: dict | None = None
        now = datetime.now(timezone.utc)
        # align sim clock to the previous 15-minute mark
        sim_start = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
        outdoor = self.forecast_weather(sim_start)
        occupancy = self.forecast_occupancy(sim_start)
        self.state = BuildingSimulatorState(
            sim_time=sim_start,
            occupancy=occupancy,
            outdoor_temp_c=outdoor["temp_c"],
            indoor_temp_c=22.5,
            humidity_pct=45.0,
            weather_condition=outdoor["condition"],
            solar_radiation_wm2=outdoor["solar_wm2"],
            hvac_mode="idle",
            hvac_status="idle",
            hvac_load_kw=2.0,
            lighting_load_kw=1.5,
            equipment_load_kw=3.0,
            total_energy_kw=6.5,
            comfort_score=88.0,
            carbon_kg=0.0,
            daily_carbon_kg=0.0,
        )
        self._last_real_tick = time.time()
        self._day_start = self.state.sim_time.date()

    # ------------------------------------------------------------------
    # Environment models
    # ------------------------------------------------------------------
    def forecast_weather(self, sim_time: datetime) -> dict:
        """Diurnal curve: morning warming, afternoon peak (~15:00), evening
        cooling. Deterministic on hour-of-day plus small bounded noise."""
        hour = sim_time.hour + sim_time.minute / 60
        base = 21 + 7 * math.cos(math.pi * (hour - 15) / 12)
        temp = base + random.uniform(-0.4, 0.4)
        solar = max(0.0, 800 * math.cos(math.pi * (hour - 12.5) / 13)) if 6 <= hour <= 19 else 0.0
        condition = "clear" if solar > 500 else "partly_cloudy" if solar > 100 else "overcast" if hour < 6 or hour > 19 else "clear"
        return {"temp_c": _round(temp), "solar_wm2": _round(solar, 0), "condition": condition}

    def forecast_occupancy(self, sim_time: datetime, previous: int | None = None) -> int:
        """Typical weekday office profile: low overnight, ramp up 7-9,
        high 9-17, ramp down 17-19, low evening. Weekend scaled down.
        Moves toward the target occupancy rather than jumping, so it
        depends on the previous value for continuity."""
        hour = sim_time.hour + sim_time.minute / 60
        is_weekend = sim_time.weekday() >= 5
        peak = 8 if is_weekend else 32
        if hour < 7 or hour > 19:
            target = 0 if hour < 6 or hour > 20 else 2
        elif hour < 9:
            target = int(peak * (hour - 7) / 2)
        elif hour <= 17:
            target = peak + random.randint(-2, 2)
        else:
            target = int(peak * max(0, (19 - hour) / 2))
        target = max(0, target)
        if previous is None:
            return target
        # smooth toward target so occupancy evolves rather than jumping
        step = target - previous
        return max(0, previous + max(-6, min(6, step)))

    # ------------------------------------------------------------------
    # HVAC + comfort + carbon models
    # ------------------------------------------------------------------
    def _hvac(self, indoor: float, outdoor: float, occupancy: int) -> tuple[str, str, float]:
        if self.hvac_override == "off":
            return "idle", "idle", 0.2
        delta = indoor - self.target_temp_c
        if self.hvac_override == "cooling" or (self.hvac_override is None and delta > 0.6):
            mode, status = "cooling", "running"
            load = _round(1.2 + abs(delta) * 1.1 + 0.03 * outdoor)
        elif self.hvac_override == "heating" or (self.hvac_override is None and delta < -0.6):
            mode, status = "heating", "running"
            load = _round(1.2 + abs(delta) * 1.1 + 0.02 * max(0, 15 - outdoor))
        else:
            mode, status = "idle", "cycling" if occupancy > 0 else "idle"
            load = _round(0.8 + random.uniform(0, 0.4))
        return mode, status, max(0.3, load)

    def set_target_temperature(self, target_c: float, initiated_by: str = "api", reason: str | None = None) -> dict:
        """Real, effective HVAC control: bounds-checked setpoint change that
        actually shifts subsequent `_advance_one_tick()` physics (unlike a
        purely cosmetic "applied": true response)."""
        clamped = max(MIN_TARGET_C, min(MAX_TARGET_C, target_c))
        self.target_temp_c = clamped
        self.last_control_action = {
            "type": "setpoint_change", "target_temp_c": clamped, "initiated_by": initiated_by,
            "reason": reason, "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return {"applied": True, "target_temp_c": clamped}

    def set_hvac_mode(self, mode: str, initiated_by: str = "api", reason: str | None = None) -> dict:
        """mode: 'auto' clears the override (physics decides), or force
        'cooling' | 'heating' | 'off'."""
        self.hvac_override = None if mode == "auto" else mode
        self.last_control_action = {
            "type": "mode_change", "mode": mode, "initiated_by": initiated_by,
            "reason": reason, "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return {"applied": True, "mode": mode}

    def _next_indoor_temp(self, prev_indoor: float, outdoor: float, occupancy: int, mode: str, hvac_load: float) -> float:
        envelope_gain = 0.12 * (outdoor - prev_indoor)  # heat exchange w/ outside
        internal_gain = 0.015 * occupancy  # occupant body heat + equipment
        hvac_effect = -0.35 * hvac_load if mode == "cooling" else 0.35 * hvac_load if mode == "heating" else 0.0
        next_temp = prev_indoor + envelope_gain + internal_gain + hvac_effect
        return _round(next_temp)

    def _comfort_score(self, indoor: float, humidity: float, occupancy: int) -> float:
        temp_penalty = min(40, abs(indoor - self.target_temp_c) * 22)
        humidity_penalty = min(20, abs(humidity - 45) * 0.6)
        score = 100 - temp_penalty - humidity_penalty
        if occupancy == 0:
            score = max(score, 90)  # comfort is moot when nobody's there
        return _round(max(0.0, min(100.0, score)), 1)

    # ------------------------------------------------------------------
    # Tick loop
    # ------------------------------------------------------------------
    def _advance_one_tick(self) -> BuildingSimulatorState:
        prev = self.state
        sim_time = prev.sim_time + timedelta(minutes=TICK_MINUTES)
        weather = self.forecast_weather(sim_time)
        occupancy = self.forecast_occupancy(sim_time, previous=prev.occupancy)

        mode, status, hvac_load = self._hvac(prev.indoor_temp_c, weather["temp_c"], occupancy)
        indoor_temp = self._next_indoor_temp(prev.indoor_temp_c, weather["temp_c"], occupancy, mode, hvac_load)
        humidity = _round(max(30.0, min(65.0, prev.humidity_pct + random.uniform(-1.2, 1.2) + (0.4 if occupancy > 10 else -0.2))), 1)

        lighting_load = _round(0.4 + 0.06 * occupancy + (0.6 if weather["solar_wm2"] < 150 and occupancy > 0 else 0.0))
        equipment_load = _round(0.5 + 0.09 * occupancy)
        total_energy = _round(hvac_load + lighting_load + equipment_load)

        comfort = self._comfort_score(indoor_temp, humidity, occupancy)

        tick_kwh = total_energy * (TICK_MINUTES / 60)
        carbon_kg = _round(tick_kwh * CARBON_INTENSITY_KG_PER_KWH, 3)

        if sim_time.date() != self._day_start:
            self._day_start = sim_time.date()
            daily_carbon = carbon_kg
        else:
            daily_carbon = _round(prev.daily_carbon_kg + carbon_kg, 3)

        self.state = BuildingSimulatorState(
            sim_time=sim_time,
            occupancy=occupancy,
            outdoor_temp_c=weather["temp_c"],
            indoor_temp_c=indoor_temp,
            humidity_pct=humidity,
            weather_condition=weather["condition"],
            solar_radiation_wm2=weather["solar_wm2"],
            hvac_mode=mode,
            hvac_status=status,
            hvac_load_kw=hvac_load,
            lighting_load_kw=lighting_load,
            equipment_load_kw=equipment_load,
            total_energy_kw=total_energy,
            comfort_score=comfort,
            carbon_kg=carbon_kg,
            daily_carbon_kg=daily_carbon,
        )
        return self.state

    def advance_if_due(self, max_catchup_ticks: int = 8) -> BuildingSimulatorState:
        """Lazily advances the sim clock based on elapsed wall-clock time so
        polling the dashboard shows visible progress without a scheduler."""
        elapsed = time.time() - self._last_real_tick
        ticks_due = min(max_catchup_ticks, int(elapsed // SECONDS_PER_TICK))
        for _ in range(ticks_due):
            self._advance_one_tick()
            self._last_real_tick += SECONDS_PER_TICK
        if ticks_due == 0 and elapsed > SECONDS_PER_TICK * max_catchup_ticks:
            # avoid unbounded drift if the process was idle a long time
            self._last_real_tick = time.time()
        return self.state

    def force_tick(self) -> BuildingSimulatorState:
        """Advances exactly one tick regardless of elapsed wall-clock time —
        used when the AI agent runs a cycle or a simulation run is
        triggered, so the action is always reflected immediately."""
        state = self._advance_one_tick()
        self._last_real_tick = time.time()
        return state

    def current(self) -> BuildingSimulatorState:
        return self.advance_if_due()

    def forecast_ahead(self, steps: int = 8) -> list[dict]:
        """Side-effect-free projection of `steps` future ticks using the
        same physics as `_advance_one_tick`, seeded from the current state
        but WITHOUT mutating `self.state` — used by the `forecast_energy`
        MCP tool so callers can preview upcoming load without advancing
        the real simulation clock."""
        sim_time = self.state.sim_time
        indoor = self.state.indoor_temp_c
        humidity = self.state.humidity_pct
        occupancy = self.state.occupancy
        out = []
        for _ in range(steps):
            sim_time = sim_time + timedelta(minutes=TICK_MINUTES)
            weather = self.forecast_weather(sim_time)
            occupancy = self.forecast_occupancy(sim_time, previous=occupancy)
            mode, status, hvac_load = self._hvac(indoor, weather["temp_c"], occupancy)
            indoor = self._next_indoor_temp(indoor, weather["temp_c"], occupancy, mode, hvac_load)
            humidity = _round(max(30.0, min(65.0, humidity + (0.4 if occupancy > 10 else -0.2))), 1)
            lighting_load = _round(0.4 + 0.06 * occupancy + (0.6 if weather["solar_wm2"] < 150 and occupancy > 0 else 0.0))
            equipment_load = _round(0.5 + 0.09 * occupancy)
            total_energy = _round(hvac_load + lighting_load + equipment_load)
            out.append({
                "time": sim_time.strftime("%H:%M"),
                "occupancy": occupancy,
                "outdoor_temp_c": weather["temp_c"],
                "indoor_temp_c": indoor,
                "hvac_mode": mode,
                "hvac_load_kw": hvac_load,
                "lighting_load_kw": lighting_load,
                "equipment_load_kw": equipment_load,
                "total_energy_kw": total_energy,
            })
        return out


_simulator_instance: BuildingSimulator | None = None


def get_building_simulator() -> BuildingSimulator:
    global _simulator_instance
    if _simulator_instance is None:
        _simulator_instance = BuildingSimulator()
    return _simulator_instance
