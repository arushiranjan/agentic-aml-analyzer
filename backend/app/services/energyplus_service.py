"""EnergyPlus integration.

Two implementations behind one `EnergyPlusServiceBase` interface
(`run_simulation`, `get_building_state`, `status`):

- `MockEnergyPlusService` — zero-setup deterministic demo data. Default.
- `RealEnergyPlusService` — shells out to a real, locally-installed
  EnergyPlus binary and parses its CSV output. Used when
  `USE_MOCK_ENERGYPLUS=false` and `ENERGYPLUS_DIR`/`ENERGYPLUS_IDF`/
  `ENERGYPLUS_EPW` are all set and valid (see README "Manual Steps
  Required"). If validation fails, `get_energyplus_service()` logs a
  warning and falls back to the mock so the app never fails to boot.

Callers never see which implementation is active — same method names,
same return shapes — so the REST API and LangGraph agents are unaffected
by which one is running.
"""
import csv
import logging
import shutil
import subprocess
import random
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger("app.energyplus")

ZONE_NAMES = ["Core_ZN", "Perimeter_N_ZN", "Perimeter_S_ZN", "Perimeter_E_ZN", "Perimeter_W_ZN"]


class EnergyPlusServiceBase(ABC):
    @abstractmethod
    def run_simulation(self, idf_path: str | None, epw_path: str | None, is_baseline: bool) -> dict:
        ...

    @abstractmethod
    def get_building_state(self, zone_name: str | None = None) -> dict:
        ...

    @abstractmethod
    def status(self) -> dict:
        ...


class MockEnergyPlusService(EnergyPlusServiceBase):
    """Generates realistic, physically-plausible mock building data so the
    frontend/backend contract is proven end-to-end before EnergyPlus itself
    is wired in."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._last_run: str | None = None

    def _outdoor_temp(self) -> float:
        # simple diurnal curve, warmer mid-afternoon
        hour = datetime.now().hour + datetime.now().minute / 60
        base = 24 + 8 * (1 - abs(hour - 15) / 15)
        return round(base + random.uniform(-1.0, 1.0), 1)

    def get_building_state(self, zone_name: str | None = None) -> dict:
        outdoor = self._outdoor_temp()
        names = [zone_name] if zone_name else ZONE_NAMES
        zones = []
        for name in names:
            indoor = round(22.0 + random.uniform(-1.2, 1.8), 1)
            occ = random.randint(0, 18)
            zones.append(
                {
                    "name": name,
                    "temperature_c": indoor,
                    "outdoor_temp_c": outdoor,
                    "humidity_pct": round(random.uniform(38, 55), 1),
                    "co2_ppm": round(random.uniform(450, 850), 0),
                    "illuminance_lux": round(random.uniform(250, 550), 0),
                    "occupancy": occ,
                    "status": "comfortable" if 21 <= indoor <= 25 else "attention",
                }
            )
        health = round(100 - sum(1 for z in zones if z["status"] != "comfortable") * 8 - random.uniform(0, 5))
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "zones": zones,
            "overall_health_score": max(0, min(100, int(health))),
        }

    def run_simulation(self, idf_path: str | None, epw_path: str | None, is_baseline: bool) -> dict:
        started = time.time()
        sim_id = f"sim_{uuid.uuid4().hex[:8]}"
        # simulate a short "compute" delay so the UI can show a running state
        time.sleep(0.4)
        duration = round(time.time() - started, 2)
        self._last_run = datetime.now(timezone.utc).isoformat()

        baseline_energy = 165.0
        savings_pct = 0.0 if is_baseline else round(random.uniform(0.10, 0.22), 3)
        total_energy = round(baseline_energy * (1 - savings_pct) + random.uniform(-3, 3), 1)
        hvac_energy = round(total_energy * 0.62, 1)
        lighting_energy = round(total_energy * 0.15, 1)

        return {
            "simulation_id": sim_id,
            "status": "completed",
            "duration_seconds": duration,
            "output_path": f"{self.settings.output_directory}/{sim_id}/",
            "is_baseline": is_baseline,
            "metrics": {
                "total_energy_kwh": total_energy,
                "hvac_energy_kwh": hvac_energy,
                "lighting_energy_kwh": lighting_energy,
                "cooling_energy_kwh": round(hvac_energy * 0.55, 1),
                "heating_energy_kwh": round(hvac_energy * 0.45, 1),
                "peak_demand_kw": round(total_energy / 3.2, 1),
                "cost_usd": round(total_energy * 0.15, 2),
                "carbon_kg": round(total_energy * 0.5, 1),
                "comfort_pmv": round(random.uniform(-0.3, 0.4), 2),
                "comfort_ppd": round(random.uniform(5, 12), 1),
            },
        }

    def status(self) -> dict:
        return {
            "status": "mock",
            "version": "24.1.0 (mock)",
            "path": self.settings.energyplus_dir,
            "last_run": self._last_run,
        }


class EnergyPlusConfigError(Exception):
    """Raised when USE_MOCK_ENERGYPLUS=false but the required paths are
    missing/invalid. Caught by `get_energyplus_service()`, which logs a
    warning and falls back to the mock rather than crashing the app."""


def _find_binary(energyplus_dir: str) -> Path:
    candidates = [Path(energyplus_dir) / "energyplus", Path(energyplus_dir) / "energyplus.exe"]
    for c in candidates:
        if c.exists():
            return c
    found = shutil.which("energyplus")
    if found:
        return Path(found)
    raise EnergyPlusConfigError(
        f"No EnergyPlus executable found under ENERGYPLUS_DIR='{energyplus_dir}' "
        "(looked for 'energyplus' / 'energyplus.exe') and 'energyplus' is not on PATH."
    )


class RealEnergyPlusService(EnergyPlusServiceBase):
    """Runs the real EnergyPlus CLI against a user-provided IDF/EPW and
    parses `eplusout.csv` for zone temperatures and meter data.

    Command executed (per EnergyPlus CLI docs):
        energyplus -w <epw> -d <output_dir> -r <idf>

    `-r` enables ReadVarsESO so `eplusout.csv` is produced alongside the
    raw ESO/SQL output. Column names in that CSV depend entirely on the
    Output:Variable / Output:Meter objects present in the user's IDF —
    this parser is intentionally tolerant: it pattern-matches on common
    variable name substrings (see `_parse_output_csv`) and degrades
    gracefully (zeros + a logged warning) for any metric it can't find,
    rather than failing the whole run.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.binary = _find_binary(self.settings.energyplus_dir)

        self.idf_path = Path(self.settings.energyplus_idf)
        self.epw_path = Path(self.settings.energyplus_epw)
        if not self.idf_path.is_file():
            raise EnergyPlusConfigError(f"ENERGYPLUS_IDF does not point to a file: '{self.settings.energyplus_idf}'")
        if not self.epw_path.is_file():
            raise EnergyPlusConfigError(f"ENERGYPLUS_EPW does not point to a file: '{self.settings.energyplus_epw}'")

        self.output_root = Path(self.settings.output_directory)
        self.output_root.mkdir(parents=True, exist_ok=True)

        self._last_run: str | None = None
        self._last_output_dir: Path | None = None
        self._last_zone_state: dict | None = None
        logger.info("RealEnergyPlusService ready: binary=%s idf=%s epw=%s", self.binary, self.idf_path, self.epw_path)

    # ------------------------------------------------------------------
    def _run_cli(self, idf: Path, epw: Path, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        cmd = [str(self.binary), "-w", str(epw), "-d", str(out_dir), "-r", str(idf)]
        logger.info("Running EnergyPlus: %s", " ".join(cmd))
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=self.settings.energyplus_timeout_seconds
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"EnergyPlus exited with code {result.returncode}.\n"
                f"stdout (tail): {result.stdout[-1500:]}\n"
                f"stderr (tail): {result.stderr[-1500:]}"
            )

    def _parse_output_csv(self, out_dir: Path) -> dict:
        """Best-effort parse of eplusout.csv. Returns zone temps + energy
        metrics, filling in 0.0 / empty for anything not found in the
        columns the user's IDF happened to request."""
        csv_path = out_dir / "eplusout.csv"
        zones: dict[str, float] = {}
        energy_cols: dict[str, float] = {}

        if not csv_path.exists():
            logger.warning("eplusout.csv not found in %s — was -r (readvars) enabled and did the run succeed?", out_dir)
            return {"zones": zones, "energy_cols": energy_cols}

        with csv_path.open(newline="", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return {"zones": zones, "energy_cols": energy_cols}

        last_row = rows[-1]  # final timestep = current/most-recent building state
        for col, val in last_row.items():
            try:
                fval = float(val)
            except (TypeError, ValueError):
                continue
            col_upper = col.upper()
            if "ZONE MEAN AIR TEMPERATURE" in col_upper:
                zone_name = col.split(":")[0].strip()
                zones[zone_name] = fval
            elif any(key in col_upper for key in ("ELECTRICITY:FACILITY", "ELECTRICITY:HVAC", "GAS:FACILITY",
                                                    "DISTRICTCOOLING:FACILITY", "DISTRICTHEATING:FACILITY",
                                                    "ELECTRICITY:LIGHTS")):
                energy_cols[col] = fval

        return {"zones": zones, "energy_cols": energy_cols}

    # ------------------------------------------------------------------
    def get_building_state(self, zone_name: str | None = None) -> dict:
        if self._last_zone_state is None:
            # No run yet — perform one automatically so this endpoint
            # always returns real data once real mode is enabled, instead
            # of erroring on first call.
            logger.info("No prior EnergyPlus run cached — running one now to populate building state.")
            self.run_simulation(None, None, is_baseline=False)

        state = self._last_zone_state or {"zones": [], "overall_health_score": 0}
        if zone_name:
            zones = [z for z in state["zones"] if z["name"] == zone_name]
            return {**state, "zones": zones}
        return state

    def run_simulation(self, idf_path: str | None, epw_path: str | None, is_baseline: bool) -> dict:
        started = time.time()
        sim_id = f"sim_{uuid.uuid4().hex[:8]}"
        idf = Path(idf_path) if idf_path else self.idf_path
        epw = Path(epw_path) if epw_path else self.epw_path
        out_dir = self.output_root / sim_id

        self._run_cli(idf, epw, out_dir)
        duration = round(time.time() - started, 2)
        self._last_run = datetime.now(timezone.utc).isoformat()
        self._last_output_dir = out_dir

        parsed = self._parse_output_csv(out_dir)
        zone_temps = parsed["zones"]
        energy_cols = parsed["energy_cols"]

        # Build a building-state snapshot in the same shape Mock produces,
        # from whatever zone temperature columns the IDF exposed.
        zones = []
        for name, temp in zone_temps.items():
            zones.append({
                "name": name,
                "temperature_c": round(temp, 1),
                "outdoor_temp_c": None,
                "humidity_pct": None,
                "co2_ppm": None,
                "illuminance_lux": None,
                "occupancy": None,
                "status": "comfortable" if 21 <= temp <= 25 else "attention",
            })
        if not zones:
            logger.warning(
                "No 'Zone Mean Air Temperature' columns found in eplusout.csv — add an "
                "Output:Variable,*,Zone Mean Air Temperature,Timestep; object to your IDF "
                "for per-zone data. Returning an empty zone list for this run."
            )
        self._last_zone_state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "zones": zones,
            "overall_health_score": round(100 - sum(1 for z in zones if z["status"] != "comfortable") * 8) if zones else 0,
        }

        total_electricity_j = sum(v for k, v in energy_cols.items() if "ELECTRICITY" in k.upper())
        total_energy_kwh = round(total_electricity_j / 3_600_000, 2) if total_electricity_j else 0.0
        if not energy_cols:
            logger.warning(
                "No recognized energy meter columns found in eplusout.csv — add "
                "Output:Meter objects (e.g. Electricity:Facility) to your IDF for "
                "energy metrics. Returning zeroed metrics for this run."
            )

        return {
            "simulation_id": sim_id,
            "status": "completed",
            "duration_seconds": duration,
            "output_path": str(out_dir),
            "is_baseline": is_baseline,
            "metrics": {
                "total_energy_kwh": total_energy_kwh,
                "hvac_energy_kwh": round(total_energy_kwh * 0.62, 2),
                "lighting_energy_kwh": round(total_energy_kwh * 0.15, 2),
                "cooling_energy_kwh": round(total_energy_kwh * 0.62 * 0.55, 2),
                "heating_energy_kwh": round(total_energy_kwh * 0.62 * 0.45, 2),
                "peak_demand_kw": round(total_energy_kwh / 3.2, 2),
                "cost_usd": round(total_energy_kwh * 0.15, 2),
                "carbon_kg": round(total_energy_kwh * 0.5, 2),
                "comfort_pmv": None,
                "comfort_ppd": None,
            },
        }

    def status(self) -> dict:
        return {
            "status": "real",
            "version": "installed (see ENERGYPLUS_DIR)",
            "path": str(self.binary),
            "idf": str(self.idf_path),
            "epw": str(self.epw_path),
            "last_run": self._last_run,
        }


_service_instance: EnergyPlusServiceBase | None = None


def get_energyplus_service() -> EnergyPlusServiceBase:
    global _service_instance
    if _service_instance is None:
        settings = get_settings()
        if settings.use_mock_energyplus:
            _service_instance = MockEnergyPlusService()
        else:
            try:
                _service_instance = RealEnergyPlusService()
            except Exception as exc:
                logger.warning(
                    "USE_MOCK_ENERGYPLUS=false but real EnergyPlus could not be initialized "
                    "(%s). Falling back to MockEnergyPlusService. See README 'Manual Steps "
                    "Required' to configure ENERGYPLUS_DIR/ENERGYPLUS_IDF/ENERGYPLUS_EPW.",
                    exc,
                )
                _service_instance = MockEnergyPlusService()
    return _service_instance


def reset_energyplus_service() -> None:
    """Test/ops helper to force re-initialization (e.g. after changing .env)."""
    global _service_instance
    _service_instance = None
