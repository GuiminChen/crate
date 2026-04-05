"""OpenAI-compatible chat LLM configuration (DeepSeek, OpenAI, 阿里, 火山, etc.)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI

__all__ = [
    "ChatLLMConfig",
    "DeepSeekConfig",
    "LLM_PROVIDER_IDS",
    "load_deepseek_config",
    "build_openai_client",
    "chat_extra_kwargs_for_purpose",
    "truncate_prompt_for_purpose",
]

Purpose = Literal["compile", "qa", "lint"]


@dataclass(frozen=True)
class DeepSeekConfig:
    """Runtime chat LLM settings (OpenAI-compatible HTTP API)."""

    api_key: str
    base_url: str
    model: str


ChatLLMConfig = DeepSeekConfig


# Default DeepSeek (legacy)
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

# Preset id -> default base URL, default model, env vars to try for API key (order).
# base_url_env / model_env: optional provider-specific overrides (before CRATE_CHAT_*).
_CHAT_PRESETS: dict[str, dict[str, Any]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
        "key_envs": ("CRATE_DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY"),
        "base_url_env": "CRATE_DEEPSEEK_BASE_URL",
        "model_env": "CRATE_DEEPSEEK_MODEL",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "key_envs": ("CRATE_OPENAI_API_KEY", "OPENAI_API_KEY"),
        "base_url_env": "CRATE_OPENAI_BASE_URL",
        "model_env": "CRATE_OPENAI_MODEL",
    },
    "aliyun": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-turbo",
        "key_envs": (
            "CRATE_DASHSCOPE_API_KEY",
            "DASHSCOPE_API_KEY",
            "ALIBABA_CLOUD_API_KEY",
        ),
        "base_url_env": "CRATE_DASHSCOPE_BASE_URL",
        "model_env": "CRATE_DASHSCOPE_MODEL",
    },
    "volcengine": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "doubao-pro-32k",
        "key_envs": ("CRATE_ARK_API_KEY", "ARK_API_KEY"),
        "base_url_env": "CRATE_ARK_BASE_URL",
        "model_env": "CRATE_ARK_MODEL",
    },
    "tencent": {
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "default_model": "hunyuan-turbo",
        "key_envs": ("CRATE_HUNYUAN_API_KEY", "HUNYUAN_API_KEY"),
        "base_url_env": "CRATE_HUNYUAN_BASE_URL",
        "model_env": "CRATE_HUNYUAN_MODEL",
    },
    "bytedance": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "doubao-pro-32k",
        "key_envs": ("CRATE_ARK_API_KEY", "ARK_API_KEY"),
        "base_url_env": "CRATE_ARK_BASE_URL",
        "model_env": "CRATE_ARK_MODEL",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-4o-mini",
        "key_envs": ("CRATE_OPENROUTER_API_KEY", "OPENROUTER_API_KEY"),
        "base_url_env": "CRATE_OPENROUTER_BASE_URL",
        "model_env": "CRATE_OPENROUTER_MODEL",
    },
    "azure_openai": {
        "base_url": "",
        "default_model": "gpt-4o-mini",
        "key_envs": ("AZURE_OPENAI_API_KEY", "CRATE_AZURE_OPENAI_API_KEY"),
        "base_url_env": "",
        "model_env": "AZURE_OPENAI_DEPLOYMENT",
    },
    "custom": {
        "base_url": "",
        "default_model": "gpt-4o-mini",
        "key_envs": ("CRATE_CHAT_API_KEY",),
        "base_url_env": "",
        "model_env": "CRATE_CHAT_MODEL",
    },
}

LLM_PROVIDER_IDS = tuple(sorted(k for k in _CHAT_PRESETS if k != "custom")) + (
    "custom",
)


def _first_nonempty_env(names: tuple[str, ...]) -> str:
    for name in names:
        v = os.environ.get(name, "").strip()
        if v:
            return v
    return ""


def _resolve_chat_provider() -> str:
    """Pick preset id from CRATE_LLM_PROVIDER or key auto-detection."""
    raw = os.environ.get("CRATE_LLM_PROVIDER", "").strip().lower()
    if raw:
        if raw in _CHAT_PRESETS:
            return raw
        raise ValueError(
            f"Unknown CRATE_LLM_PROVIDER={raw!r}. "
            f"Use one of: {', '.join(LLM_PROVIDER_IDS)}."
        )
    if _first_nonempty_env(("CRATE_DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY")):
        return "deepseek"
    if _first_nonempty_env(
        ("CRATE_DASHSCOPE_API_KEY", "DASHSCOPE_API_KEY", "ALIBABA_CLOUD_API_KEY")
    ):
        return "aliyun"
    if _first_nonempty_env(("CRATE_ARK_API_KEY", "ARK_API_KEY")):
        return "volcengine"
    if _first_nonempty_env(("CRATE_HUNYUAN_API_KEY", "HUNYUAN_API_KEY")):
        return "tencent"
    if _first_nonempty_env(("CRATE_OPENROUTER_API_KEY", "OPENROUTER_API_KEY")):
        return "openrouter"
    if _first_nonempty_env(("CRATE_OPENAI_API_KEY", "OPENAI_API_KEY")):
        return "openai"
    if _first_nonempty_env(("AZURE_OPENAI_API_KEY", "CRATE_AZURE_OPENAI_API_KEY")):
        return "azure_openai"
    if _first_nonempty_env(("CRATE_CHAT_API_KEY",)):
        return "custom"
    return "deepseek"


def load_deepseek_config(purpose: Purpose | None = None) -> DeepSeekConfig:
    """
    Load OpenAI-compatible chat config from the environment.

    Set ``CRATE_LLM_PROVIDER`` to one of: ``deepseek``, ``openai``, ``aliyun``,
    ``volcengine``, ``tencent``, ``bytedance``, ``openrouter``, ``azure_openai``,
    ``custom``. If unset, the first matching API key among common env vars selects
    a provider (DeepSeek keys win over OpenAI when both are set).

    Universal overrides: ``CRATE_CHAT_API_KEY``, ``CRATE_CHAT_BASE_URL``,
    ``CRATE_CHAT_MODEL`` (applied after purpose-specific model overrides chain).

    Purpose-specific model overrides: ``CRATE_MODEL_COMPILE`` / ``CRATE_MODEL_QA`` /
    ``CRATE_MODEL_LINT`` take precedence over ``CRATE_CHAT_MODEL`` and preset
    defaults. Legacy ``CRATE_DEEPSEEK_MODEL`` still applies when the provider is
    ``deepseek`` or as a final fallback model name.
    """
    provider = _resolve_chat_provider()
    preset = _CHAT_PRESETS[provider]

    key = _first_nonempty_env(("CRATE_CHAT_API_KEY",) + tuple(preset["key_envs"]))
    if not key:
        raise ValueError(
            "No chat API key found. Set CRATE_CHAT_API_KEY or one of: "
            + ", ".join(preset["key_envs"])
            + f" (provider={provider}). See docs/providers.md."
        )

    base = ""
    if os.environ.get("CRATE_CHAT_BASE_URL", "").strip():
        base = os.environ["CRATE_CHAT_BASE_URL"].strip().rstrip("/")
    elif preset.get("base_url_env"):
        benv = str(preset["base_url_env"])
        base = os.environ.get(benv, "").strip().rstrip("/")
    if not base:
        base = str(preset.get("base_url") or "").strip().rstrip("/")
    if provider == "azure_openai" and not base:
        ep = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
        deploy = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip()
        if ep and deploy:
            base = f"{ep}/openai/deployments/{deploy}"
    if provider == "custom" and not base:
        raise ValueError(
            "CRATE_LLM_PROVIDER=custom requires CRATE_CHAT_BASE_URL "
            "(OpenAI-compatible base URL)."
        )
    if not base:
        raise ValueError(
            f"Missing base URL for provider {provider!r}. "
            "Set CRATE_CHAT_BASE_URL or the provider-specific base env "
            f"({preset.get('base_url_env') or 'see docs/providers.md'})."
        )

    base_model = ""
    if preset.get("model_env"):
        menv = str(preset["model_env"])
        base_model = os.environ.get(menv, "").strip()
    if not base_model:
        base_model = os.environ.get("CRATE_CHAT_MODEL", "").strip()
    if not base_model:
        base_model = os.environ.get("CRATE_DEEPSEEK_MODEL", "").strip()
    if not base_model:
        base_model = str(preset.get("default_model") or "gpt-4o-mini")

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
