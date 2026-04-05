"""OpenAI-compatible embedding API configuration (separate from chat LLM)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

__all__ = [
    "EmbeddingConfig",
    "EMBEDDING_PROVIDER_IDS",
    "load_embedding_config",
]

_DEFAULT_BASE = "https://api.openai.com/v1"
_DEFAULT_MODEL = "text-embedding-3-small"
_DEFAULT_EMBED_BATCH = 10

_EMBED_PRESETS: dict[str, dict[str, Any]] = {
    "openai": {
        "base_url": _DEFAULT_BASE,
        "default_model": _DEFAULT_MODEL,
        "key_envs": (
            "CRATE_EMBEDDING_API_KEY",
            "OPENAI_API_KEY",
            "CRATE_OPENAI_API_KEY",
        ),
        "base_url_env": "CRATE_EMBEDDING_BASE_URL",
        "model_env": "CRATE_EMBEDDING_MODEL",
    },
    "aliyun": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "text-embedding-v3",
        "key_envs": (
            "CRATE_EMBEDDING_API_KEY",
            "CRATE_DASHSCOPE_API_KEY",
            "DASHSCOPE_API_KEY",
        ),
        "base_url_env": "CRATE_EMBEDDING_BASE_URL",
        "model_env": "CRATE_EMBEDDING_MODEL",
    },
    "volcengine": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "default_model": "doubao-embedding",
        "key_envs": (
            "CRATE_EMBEDDING_API_KEY",
            "CRATE_ARK_API_KEY",
            "ARK_API_KEY",
        ),
        "base_url_env": "CRATE_EMBEDDING_BASE_URL",
        "model_env": "CRATE_EMBEDDING_MODEL",
    },
    "tencent": {
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "default_model": "hunyuan-embedding",
        "key_envs": ("CRATE_EMBEDDING_API_KEY", "CRATE_HUNYUAN_API_KEY"),
        "base_url_env": "CRATE_EMBEDDING_BASE_URL",
        "model_env": "CRATE_EMBEDDING_MODEL",
    },
}

EMBEDDING_PROVIDER_IDS = tuple(sorted(_EMBED_PRESETS.keys()))


def _parse_embedding_batch_size() -> int:
    raw = os.environ.get("CRATE_EMBEDDING_BATCH_SIZE", "").strip()
    if raw:
        try:
            n = int(raw)
            return max(1, min(n, 2048))
        except ValueError:
            pass
    return _DEFAULT_EMBED_BATCH


def _first_nonempty_env(names: tuple[str, ...]) -> str:
    for name in names:
        v = os.environ.get(name, "").strip()
        if v:
            return v
    return ""


def _resolve_embed_provider() -> str:
    explicit = os.environ.get("CRATE_EMBEDDING_PROVIDER", "").strip().lower()
    if explicit:
        if explicit in _EMBED_PRESETS:
            return explicit
        raise ValueError(
            f"Unknown CRATE_EMBEDDING_PROVIDER={explicit!r}. "
            f"Use one of: {', '.join(EMBEDDING_PROVIDER_IDS)}."
        )
    eb = os.environ.get("CRATE_EMBEDDING_BASE_URL", "").strip().lower()
    if "dashscope" in eb or "aliyuncs" in eb:
        return "aliyun"
    if "volces" in eb or "ark.cn" in eb:
        return "volcengine"
    if "tencent" in eb or "hunyuan" in eb:
        return "tencent"
    if _first_nonempty_env(("CRATE_EMBEDDING_API_KEY",)):
        return "openai"
    if _first_nonempty_env(("CRATE_DASHSCOPE_API_KEY", "DASHSCOPE_API_KEY")):
        return "aliyun"
    if _first_nonempty_env(("CRATE_ARK_API_KEY", "ARK_API_KEY")):
        return "volcengine"
    if _first_nonempty_env(("OPENAI_API_KEY", "CRATE_OPENAI_API_KEY")):
        return "openai"
    return "openai"


@dataclass(frozen=True)
class EmbeddingConfig:
    """Runtime embedding settings from environment."""

    api_key: str
    base_url: str
    model: str
    embedding_batch_size: int = _DEFAULT_EMBED_BATCH


def load_embedding_config() -> EmbeddingConfig | None:
    """
    Load embedding config if a matching API key exists.

    Use ``CRATE_EMBEDDING_PROVIDER`` (``openai`` | ``aliyun`` | ``volcengine`` |
    ``tencent``) to force defaults; otherwise infer from ``CRATE_EMBEDDING_BASE_URL``
    or key env vars. See docs/providers.md.
    """
    provider = _resolve_embed_provider()
    preset = _EMBED_PRESETS[provider]
    key = _first_nonempty_env(tuple(preset["key_envs"]))
    if not key:
        return None

    base = ""
    if os.environ.get("CRATE_EMBEDDING_BASE_URL", "").strip():
        base = os.environ["CRATE_EMBEDDING_BASE_URL"].strip().rstrip("/")
    elif preset.get("base_url_env"):
        benv = str(preset["base_url_env"])
        base = os.environ.get(benv, "").strip().rstrip("/")
    if not base:
        base = str(preset.get("base_url") or "").strip().rstrip("/")

    model = ""
    if preset.get("model_env"):
        menv = str(preset["model_env"])
        model = os.environ.get(menv, "").strip()
    if not model:
        model = str(preset.get("default_model") or _DEFAULT_MODEL)

    batch = _parse_embedding_batch_size()
    return EmbeddingConfig(
        api_key=key,
        base_url=base,
        model=model,
        embedding_batch_size=batch,
    )
