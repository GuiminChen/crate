"""DeepSeek / OpenAI-compatible client configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI

__all__ = [
    "DeepSeekConfig",
    "load_deepseek_config",
    "build_openai_client",
    "chat_extra_kwargs_for_purpose",
    "truncate_prompt_for_purpose",
]

Purpose = Literal["compile", "qa", "lint"]


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


@dataclass(frozen=True)
class DeepSeekConfig:
    """Runtime LLM settings from environment."""

    api_key: str
    base_url: str
    model: str


def load_deepseek_config(purpose: Purpose | None = None) -> DeepSeekConfig:
    """
    Read API key from ``CRATE_DEEPSEEK_API_KEY`` or ``DEEPSEEK_API_KEY``.

    When ``purpose`` is set, ``CRATE_MODEL_COMPILE`` / ``CRATE_MODEL_QA`` /
    ``CRATE_MODEL_LINT`` (respectively) override ``CRATE_DEEPSEEK_MODEL`` if set.
    """
    key = (
        os.environ.get("CRATE_DEEPSEEK_API_KEY")
        or os.environ.get("DEEPSEEK_API_KEY", "").strip()
    )
    if not key:
        raise ValueError(
            "Set CRATE_DEEPSEEK_API_KEY or DEEPSEEK_API_KEY for compile "
            "(do not hardcode secrets)."
        )
    base = (
        os.environ.get("CRATE_DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
    )
    base_model = os.environ.get("CRATE_DEEPSEEK_MODEL", DEFAULT_MODEL).strip()
    override = ""
    if purpose == "compile":
        override = os.environ.get("CRATE_MODEL_COMPILE", "").strip()
    elif purpose == "qa":
        override = os.environ.get("CRATE_MODEL_QA", "").strip()
    elif purpose == "lint":
        override = os.environ.get("CRATE_MODEL_LINT", "").strip()
    model = override or base_model
    return DeepSeekConfig(api_key=key, base_url=base, model=model)


def chat_extra_kwargs_for_purpose(purpose: Purpose) -> dict[str, Any]:
    """Return optional ``max_tokens`` for chat completions from environment.

    Purpose-specific keys (e.g. ``CRATE_MAX_OUTPUT_TOKENS_COMPILE``) take
    precedence over ``CRATE_MAX_OUTPUT_TOKENS`` (global cap).
    """
    keys: list[str]
    if purpose == "compile":
        keys = ["CRATE_MAX_OUTPUT_TOKENS_COMPILE", "CRATE_MAX_OUTPUT_TOKENS"]
    elif purpose == "qa":
        keys = ["CRATE_MAX_OUTPUT_TOKENS_QA", "CRATE_MAX_OUTPUT_TOKENS"]
    elif purpose == "lint":
        keys = ["CRATE_MAX_OUTPUT_TOKENS_LINT", "CRATE_MAX_OUTPUT_TOKENS"]
    for key in keys:
        raw = os.environ.get(key, "").strip()
        if raw:
            try:
                return {"max_tokens": int(raw)}
            except ValueError:
                continue
    return {}


def build_openai_client(cfg: DeepSeekConfig | None = None) -> tuple[OpenAI, str]:
    """Return a synchronous OpenAI-compatible client and model name."""
    c = cfg or load_deepseek_config()
    client = OpenAI(api_key=c.api_key, base_url=c.base_url)
    return client, c.model


def _max_input_chars_for_purpose(purpose: Purpose) -> int | None:
    """Upper bound on user/prompt text from env (hard truncation)."""
    keys: list[str]
    if purpose == "compile":
        keys = ["CRATE_MAX_INPUT_CHARS_COMPILE", "CRATE_MAX_INPUT_CHARS"]
    elif purpose == "qa":
        keys = ["CRATE_MAX_INPUT_CHARS_QA", "CRATE_MAX_INPUT_CHARS"]
    elif purpose == "lint":
        keys = ["CRATE_MAX_INPUT_CHARS_LINT", "CRATE_MAX_INPUT_CHARS"]
    for key in keys:
        raw = os.environ.get(key, "").strip()
        if raw:
            try:
                return max(1, int(raw))
            except ValueError:
                continue
    return None


def truncate_prompt_for_purpose(text: str, purpose: Purpose) -> str:
    """Truncate prompt text when ``CRATE_MAX_INPUT_CHARS*`` is set."""
    limit = _max_input_chars_for_purpose(purpose)
    if limit is None or len(text) <= limit:
        return text
    return text[:limit] + "\n\n…(truncated: CRATE_MAX_INPUT_CHARS*)…"
