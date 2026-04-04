"""DeepSeek / OpenAI-compatible client configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI

__all__ = [
    "DeepSeekConfig",
    "load_deepseek_config",
    "build_openai_client",
]


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


@dataclass(frozen=True)
class DeepSeekConfig:
    """Runtime LLM settings from environment."""

    api_key: str
    base_url: str
    model: str


def load_deepseek_config() -> DeepSeekConfig:
    """Read API key from ``CRATE_DEEPSEEK_API_KEY`` or ``DEEPSEEK_API_KEY``."""
    key = os.environ.get("CRATE_DEEPSEEK_API_KEY") or os.environ.get(
        "DEEPSEEK_API_KEY", ""
    ).strip()
    if not key:
        raise ValueError(
            "Set CRATE_DEEPSEEK_API_KEY or DEEPSEEK_API_KEY for compile (not hardcoded)."
        )
    base = (
        os.environ.get("CRATE_DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    )
    model = os.environ.get("CRATE_DEEPSEEK_MODEL", DEFAULT_MODEL).strip()
    return DeepSeekConfig(api_key=key, base_url=base, model=model)


def build_openai_client(cfg: DeepSeekConfig | None = None) -> tuple[OpenAI, str]:
    """Return a synchronous OpenAI-compatible client and model name."""
    c = cfg or load_deepseek_config()
    client = OpenAI(api_key=c.api_key, base_url=c.base_url)
    return client, c.model
