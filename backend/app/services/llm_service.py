"""LLM integration — Ollama-backed reasoning service.

Two implementations behind one `LLMServiceBase` interface (`complete`,
`status`):

- `MockLLMService` — zero-setup, deterministic-ish canned reasoning text.
  Default. Proves the agent/API contract without any local model.
- `RealLLMService` — calls a locally-running Ollama server over its HTTP
  API (`OLLAMA_BASE_URL`) using the official `ollama` Python client, and
  runs inference with `MODEL_NAME`/`LLM_MODEL`.

Switching to real Ollama:
  1. Install Ollama: https://ollama.com/download
  2. Pull a model, e.g. `ollama pull qwen3:8b`.
  3. Set OLLAMA_BASE_URL and LLM_MODEL in .env (see .env.example).
  4. Set USE_MOCK_LLM=false in .env.

Callers (`app/agents/graph.py`, `app/api/routes/system.py`,
`app/mcp/tools.py`) never see which implementation is active — same
method name/signature, same return shape — so switching is a pure
config change, no code changes required.

Like `RealEnergyPlusService`, if USE_MOCK_LLM=false but Ollama can't be
reached (or the model isn't pulled) at startup, `get_llm_service()` logs
a warning and falls back to `MockLLMService` so the app never fails to
boot on a missing/unreachable local model.
"""
import logging
import random
import time
from abc import ABC, abstractmethod

from app.config import get_settings

logger = logging.getLogger("app.llm")

_REASONS = [
    "Zone {zone} is running {delta}°C below setpoint during low occupancy; "
    "raising the cooling setpoint by 0.5°C should cut HVAC load without "
    "affecting comfort (PMV stays within ±0.5).",
    "Outdoor temperature has dropped; pre-cooling is no longer required. "
    "Reducing fan speed will lower energy use while occupancy is at {occ} people.",
    "Occupancy in {zone} is trending down for the next interval; scheduling "
    "a setback now will not impact comfort category A.",
    "Solar gain on the west facade is increasing indoor temperature; "
    "recommend adjusting the cooling setpoint proactively before it drifts.",
]

DEFAULT_SYSTEM_PROMPT = (
    "You are a building energy optimization assistant. Given the current "
    "building state and a candidate action, respond with a single short "
    "paragraph (2-3 sentences) explaining whether the action is a good idea "
    "and why, in plain, specific, technical language. Do not use markdown."
)


class LLMServiceBase(ABC):
    @abstractmethod
    def complete(self, prompt: str, system: str | None = None) -> dict:
        ...

    @abstractmethod
    def status(self) -> dict:
        ...


class MockLLMService(LLMServiceBase):
    """Returns plausible reasoning text + confidence without calling any
    model — proves the agent/API contract before Ollama is installed."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def complete(self, prompt: str, system: str | None = None) -> dict:
        start = time.time()
        time.sleep(random.uniform(0.15, 0.4))  # simulate inference latency
        template = random.choice(_REASONS)
        text = template.format(
            zone=random.choice(["Core_ZN", "Perimeter_S_ZN", "Perimeter_W_ZN"]),
            delta=round(random.uniform(0.5, 2.0), 1),
            occ=random.randint(2, 15),
        )
        latency_ms = round((time.time() - start) * 1000, 1)
        return {
            "text": text,
            "confidence": round(random.uniform(0.72, 0.96), 2),
            "latency_ms": latency_ms,
            "token_count": len(text.split()) + len((prompt or "").split()),
        }

    def status(self) -> dict:
        return {
            "status": "mock",
            "model": f"{self.settings.llm_model} (mock)",
            "url": self.settings.ollama_base_url,
        }


class LLMConfigError(Exception):
    """Raised when USE_MOCK_LLM=false but Ollama / the configured model
    can't be reached or found. Caught by `get_llm_service()`, which logs a
    warning and falls back to the mock rather than crashing the app."""


class RealLLMService(LLMServiceBase):
    """Calls a locally-running Ollama server via the official `ollama`
    Python client (sync `Client`, same transport the `ollama` CLI uses).

    `complete()` sends a single-turn chat completion (optional system
    prompt + user prompt) and returns the same shape `MockLLMService`
    does, so `app/agents/graph.py` and the MCP tool layer are unaffected
    by which implementation is active:

        {"text": str, "confidence": float, "latency_ms": float, "token_count": int}

    Ollama's chat API does not return a calibrated confidence score, so
    `confidence` here is a heuristic derived from `done_reason` (a clean
    "stop" scores higher than a truncated "length"/other reason) — it is
    not a probability and should be treated as a rough signal only.
    """

    def __init__(self) -> None:
        try:
            import ollama  # noqa: F401  (import check only; used below)
        except ImportError as exc:  # pragma: no cover
            raise LLMConfigError(
                "The 'ollama' package is not installed. Run `pip install ollama` "
                "(see requirements.txt), then retry."
            ) from exc

        self.settings = get_settings()
        self._ollama = ollama
        self.client = ollama.Client(
            host=self.settings.ollama_base_url,
            timeout=self.settings.llm_timeout_seconds,
        )
        self._verify_server_and_model()
        logger.info(
            "RealLLMService ready: url=%s model=%s",
            self.settings.ollama_base_url,
            self.settings.llm_model,
        )

    # ------------------------------------------------------------------
    def _verify_server_and_model(self) -> None:
        """Fail fast (caught by get_llm_service()) if Ollama isn't running
        at OLLAMA_BASE_URL, or if MODEL_NAME/LLM_MODEL hasn't been pulled
        — rather than surfacing an opaque connection error on first use."""
        try:
            available = self.client.list()
        except Exception as exc:
            raise LLMConfigError(
                f"Could not reach Ollama at '{self.settings.ollama_base_url}' "
                f"({exc}). Is Ollama running? Start it with `ollama serve` "
                "or the Ollama desktop app."
            ) from exc

        model_names = {m.model for m in getattr(available, "models", [])}
        configured = self.settings.llm_model
        # Ollama tags are typically "name:tag" — also accept a bare name
        # match against the part before ':' so "qwen3" matches "qwen3:8b".
        if configured not in model_names and not any(
            name.split(":")[0] == configured.split(":")[0] for name in model_names
        ):
            raise LLMConfigError(
                f"Model '{configured}' is not pulled in Ollama at "
                f"'{self.settings.ollama_base_url}'. Run `ollama pull {configured}` "
                f"(available locally: {sorted(model_names) or 'none'})."
            )

    # ------------------------------------------------------------------
    def complete(self, prompt: str, system: str | None = None) -> dict:
        start = time.time()
        messages = [{"role": "system", "content": system or DEFAULT_SYSTEM_PROMPT}]
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat(
                model=self.settings.llm_model,
                messages=messages,
                options={
                    "temperature": self.settings.llm_temperature,
                    "num_ctx": self.settings.llm_num_ctx,
                },
                stream=False,
            )
        except Exception as exc:
            logger.error("Ollama completion failed: %s", exc)
            raise

        latency_ms = round((time.time() - start) * 1000, 1)
        text = (response.message.content or "").strip()
        done_reason = getattr(response, "done_reason", None)
        confidence = 0.9 if done_reason == "stop" else 0.6

        eval_count = getattr(response, "eval_count", None) or 0
        prompt_eval_count = getattr(response, "prompt_eval_count", None) or 0

        return {
            "text": text or "(model returned an empty response)",
            "confidence": confidence,
            "latency_ms": latency_ms,
            "token_count": eval_count + prompt_eval_count,
        }

    def status(self) -> dict:
        return {
            "status": "real",
            "model": self.settings.llm_model,
            "url": self.settings.ollama_base_url,
        }


_service_instance: LLMServiceBase | None = None


def get_llm_service() -> LLMServiceBase:
    global _service_instance
    if _service_instance is None:
        settings = get_settings()
        if settings.use_mock_llm:
            _service_instance = MockLLMService()
        else:
            try:
                _service_instance = RealLLMService()
            except Exception as exc:
                logger.warning(
                    "USE_MOCK_LLM=false but RealLLMService could not be initialized "
                    "(%s). Falling back to MockLLMService. See README 'Manual Steps "
                    "Required' to install Ollama and pull the configured model.",
                    exc,
                )
                _service_instance = MockLLMService()
    return _service_instance


def reset_llm_service() -> None:
    """Test/ops helper to force re-initialization (e.g. after changing .env)."""
    global _service_instance
    _service_instance = None
