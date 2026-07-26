from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    uptime: str
    version: str


class ComponentStatus(BaseModel):
    status: str
    detail: str = ""


class SystemStatusResponse(BaseModel):
    database: dict
    energyplus: dict
    ollama: dict
    mcp: dict
    simulation: dict
