from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from sagetrade.utils.config import get_settings
from sagetrade.utils.logging import get_logger


logger = get_logger(__name__)


class LLMClientBase(ABC):
    """Abstract LLM client for AI features."""

    @abstractmethod
    def complete(self, prompt: str, *, max_tokens: Optional[int] = None, temperature: float = 0.5) -> str:
        ...


class MockLLMClient(LLMClientBase):
    """Returns canned responses; safe fallback when AI is disabled or mock provider is set."""

    def complete(self, prompt: str, *, max_tokens: Optional[int] = None, temperature: float = 0.5) -> str:
        return "AI mock response: no live LLM configured."


class EnvLLMClient(LLMClientBase):
    """Placeholder for a real LLM client (e.g., OpenAI) driven by env + settings."""

    def __init__(self, model: str, api_key_env: str) -> None:
        self.model = model
        self.api_key_env = api_key_env
        # Real implementation would read env and init SDK.

    def complete(self, prompt: str, *, max_tokens: Optional[int] = None, temperature: float = 0.5) -> str:
        raise NotImplementedError("EnvLLMClient is a stub; configure a real provider.")


def build_llm_client() -> LLMClientBase:
    """Factory based on config/settings.yaml -> ai section."""
    settings = get_settings()
    ai_cfg = getattr(settings, "ai", None)
    provider = getattr(ai_cfg, "provider", "mock") if ai_cfg else "mock"

    if provider == "mock" or not getattr(ai_cfg, "enabled", False):
        return MockLLMClient()

    model = getattr(ai_cfg, "model", "gpt-4.1")
    api_key_env = getattr(ai_cfg, "api_key_env", "OPENAI_API_KEY")

    logger.info("llm_client_initialized event=llm_client_initialized provider=%s model=%s", provider, model)
    return EnvLLMClient(model=model, api_key_env=api_key_env)


__all__ = ["LLMClientBase", "MockLLMClient", "EnvLLMClient", "build_llm_client"]

