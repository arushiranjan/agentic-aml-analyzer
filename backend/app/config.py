"""Application configuration loaded from environment variables (.env).

Part 4 (Configuration): every machine-specific value is a placeholder here
and in `.env` / `.env.example`. Nothing under EnergyPlus/Ollama/MCP is
hardcoded to any particular OS or install location — see the "Manual Steps
Required" section of README.md for exactly what to fill in and why.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Eco-Loop Building Agents"
    app_version: str = "0.2.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = "sqlite:///./ecoloop.db"

    # ------------------------------------------------------------------
    # EnergyPlus — ALL machine-specific. Left blank by default; the app
    # runs on MockEnergyPlusService until these are filled in AND
    # use_mock_energyplus is set to false. See README "Manual Steps
    # Required" for exact values to use.
    # ------------------------------------------------------------------
    energyplus_dir: str = ""      # e.g. C:/EnergyPlusV24-1-0 or /usr/local/EnergyPlus-24-1-0
    energyplus_idf: str = ""      # absolute or repo-relative path to your .idf model
    energyplus_epw: str = ""      # absolute or repo-relative path to your .epw weather file
    output_directory: str = "energyplus/output"  # where each run's output subfolder is written
    energyplus_timeout_seconds: int = 600
    # Master switch. true = MockEnergyPlusService (default, zero setup).
    # false = RealEnergyPlusService (requires energyplus_dir/idf/epw above).
    # If false but the real install can't be found/validated at startup,
    # the app logs a warning and automatically falls back to the mock so
    # it never fails to boot.
    use_mock_energyplus: bool = True

    # ------------------------------------------------------------------
    # Ollama / LLM — machine-specific only if you change the default
    # localhost URL (e.g. Ollama running in Docker or on another host).
    # ------------------------------------------------------------------
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:8b"
    llm_temperature: float = 0.1
    llm_num_ctx: int = 8192
    llm_timeout_seconds: int = 60
    # true = MockLLMService (default, zero setup). false = RealLLMService
    # (requires Ollama running + model pulled). Same auto-fallback pattern
    # as EnergyPlus: if Ollama isn't reachable at startup, falls back to
    # mock with a warning instead of failing to boot.
    use_mock_llm: bool = True

    # ------------------------------------------------------------------
    # FastMCP server — only needed if you run `python -m app.mcp.server`
    # standalone (e.g. for Claude Desktop or `mcp inspect`). The REST API
    # and LangGraph agents call the same tool functions in-process and do
    # not need this server running.
    # ------------------------------------------------------------------
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8765
    mcp_transport: str = "stdio"  # stdio | sse

    # ------------------------------------------------------------------
    # Optimization cycle / LangGraph
    # ------------------------------------------------------------------
    cycle_interval_minutes: int = 15
    dashboard_polling_interval_seconds: int = 5
    max_retries: int = 3
    max_actions_per_cycle: int = 5
    comfort_priority: float = 0.6
    min_savings_threshold: float = 0.01

    log_level: str = "INFO"
    log_file: str = "logs/ecoloop.log"

    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
