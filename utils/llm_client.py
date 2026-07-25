"""
llm_client.py
--------------
Thin wrapper around the LLM provider (OpenAI by default).

Design goal: swap providers by editing ONLY this file.
Every other module calls `get_llm_client().complete(prompt, system=...)`
and never imports `openai` directly.

To switch to Anthropic / local models / Azure OpenAI:
  1. Implement a new class with the same `.complete()` signature.
  2. Change `get_llm_client()` at the bottom to return your class.
"""

from __future__ import annotations
import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class BaseLLMClient:
    """Interface every LLM backend must implement."""

    available: bool = True  # False signals callers to prefer a deterministic fallback

    def complete(self, prompt: str, system: Optional[str] = None,
                 json_mode: bool = False, temperature: float = 0.2) -> str:
        raise NotImplementedError


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT-4.1 / GPT-5 backend."""

    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1")
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        self.available = False
        if not api_key:
            logger.warning("OPENAI_API_KEY not set. Agent will run in RULE-ONLY fallback mode.")
        else:
            try:
                from openai import OpenAI  # imported lazily so app can boot w/o the package too
                self.client = OpenAI(api_key=api_key)
                self.available = True
            except ImportError:
                logger.warning("openai package not installed. Falling back to offline mode.")

    def complete(self, prompt: str, system: Optional[str] = None,
                 json_mode: bool = False, temperature: float = 0.2) -> str:
        if self.client is None:
            return self._offline_fallback(prompt)

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        kwargs = dict(model=self.model, messages=messages, temperature=temperature)
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            resp = self.client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._offline_fallback(prompt)

    @staticmethod
    def _offline_fallback(prompt: str) -> str:
        """
        Used when no API key is present, the `openai` package is missing,
        or the API call fails. Returns a minimal valid JSON plan so the
        agent keeps working via keyword-based intent matching
        (see agent/intent_rules.py) instead of crashing the demo.
        """
        return json.dumps({
            "intent": "unknown",
            "tools": ["eda"],
            "filters": {},
            "reasoning": "Offline fallback: no LLM available, defaulting to EDA summary."
        })


_client_instance: Optional[BaseLLMClient] = None


def get_llm_client() -> BaseLLMClient:
    """Factory. Swap the returned class to change providers everywhere."""
    global _client_instance
    if _client_instance is None:
        _client_instance = OpenAIClient()
    return _client_instance
