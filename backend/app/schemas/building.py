from pydantic import BaseModel


class ZoneState(BaseModel):
    name: str
    temperature_c: float
    humidity_pct: float
    co2_ppm: float
    illuminance_lux: float
    occupancy: int
    status: str


class BuildingStateResponse(BaseModel):
    timestamp: str
    zones: list[ZoneState]
    overall_health_score: int
