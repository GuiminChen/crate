"""OpenAI-compatible embedding API configuration (separate from chat LLM)."""

from __future__ import annotations

import os
from dataclasses import dataclass

__all__ = ["EmbeddingConfig", "load_embedding_config"]

_DEFAULT_BASE = "https://api.openai.com/v1"
_DEFAULT_MODEL = "text-embedding-3-small"
# DashScope / Aliyun compatible-mode embeddings allow at most 10 inputs per request.
_DEFAULT_EMBED_BATCH = 10


def _parse_embedding_batch_size() -> int:
    raw = os.environ.get("CRATE_EMBEDDING_BATCH_SIZE", "").strip()
    if raw:
        try:
            n = int(raw)
            return max(1, min(n, 2048))
        except ValueError:
            pass
    return _DEFAULT_EMBED_BATCH


@dataclass(frozen=True)
class EmbeddingConfig:
    """Runtime embedding settings from environment."""

    api_key: str
    base_url: str
    model: str
    embedding_batch_size: int = _DEFAULT_EMBED_BATCH


def load_embedding_config() -> EmbeddingConfig | None:
    """
    Load embedding config if ``CRATE_EMBEDDING_API_KEY`` or ``OPENAI_API_KEY`` is set.

    Returns ``None`` if no key (semantic index disabled).
    """
    key = (
        os.environ.get("CRATE_EMBEDDING_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
    )
    if not key:
        return None
    base = os.environ.get("CRATE_EMBEDDING_BASE_URL", _DEFAULT_BASE).strip().rstrip("/")
    model = os.environ.get("CRATE_EMBEDDING_MODEL", _DEFAULT_MODEL).strip()
    batch = _parse_embedding_batch_size()
    return EmbeddingConfig(
        api_key=key,
        base_url=base,
        model=model,
        embedding_batch_size=batch,
    )
