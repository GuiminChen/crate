"""Chunk markdown, embed via OpenAI-compatible API.

Stored under ``meta/embeddings.sqlite``.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
from openai import OpenAI

from crate.embedding_config import EmbeddingConfig, load_embedding_config
from crate.vault_paths import VaultContext, VaultPathError

EmbeddingClientFactory = Callable[[EmbeddingConfig], OpenAI]


def _embedding_api_user_message(exc: BaseException) -> str:
    """Turn SDK/network errors into an actionable message for CLI users."""
    detail = str(exc).strip()
    name = type(exc).__name__
    auth_like = (
        "401" in detail
        or name in ("AuthenticationError", "PermissionDeniedError")
        or "invalid_api_key" in detail
        or "Incorrect API key" in detail
    )
    if auth_like:
        return (
            "Embedding API rejected the credentials (HTTP 401 / invalid key). "
            "Use a key that matches CRATE_EMBEDDING_BASE_URL — do not reuse "
            "chat-only keys for Aliyun, OpenAI, or other embedding hosts. "
            "Set CRATE_EMBEDDING_API_KEY (or OPENAI_API_KEY) and "
            "CRATE_EMBEDDING_MODEL to values valid for that provider. "
            f"Original error: {detail}"
        )
    return f"Embedding API request failed: {detail}"


__all__ = [
    "INDEX_FILENAME",
    "chunk_markdown",
    "embed_openai_batch",
    "build_vector_index",
    "semantic_search_hits",
    "index_database_path",
    "index_exists",
]

INDEX_FILENAME = "embeddings.sqlite"
_MAX_CHUNK_CHARS = 1500


def index_database_path(ctx: VaultContext) -> Path:
    """Return the SQLite path under ``meta/``."""
    return ctx.meta_dir() / INDEX_FILENAME


def chunk_markdown(
    text: str, *, max_chars: int = _MAX_CHUNK_CHARS
) -> list[tuple[int, str]]:
    """Split into ``(start_line_1based, chunk_text)`` segments."""
    lines = text.splitlines()
    chunks: list[tuple[int, str]] = []
    cur: list[str] = []
    cur_start = 1
    cur_len = 0
    for i, line in enumerate(lines, start=1):
        add = len(line) + (1 if cur else 0)
        if cur and cur_len + add > max_chars:
            chunks.append((cur_start, "\n".join(cur)))
            cur = [line]
            cur_start = i
            cur_len = len(line)
        else:
            if not cur:
                cur_start = i
            cur.append(line)
            cur_len += add
    if cur:
        chunks.append((cur_start, "\n".join(cur)))
    return chunks


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            path TEXT NOT NULL,
            line_start INTEGER NOT NULL,
            text TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            emb BLOB NOT NULL,
            dim INTEGER NOT NULL,
            PRIMARY KEY (path, line_start)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL)
        """
    )


def _iter_md_paths(ctx: VaultContext) -> Iterable[Path]:
    for base_name in ("raw", "wiki"):
        base = ctx.root / base_name
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*.md")):
            if not p.is_file():
                continue
            try:
                ctx.validate_under_vault(p)
            except VaultPathError:
                continue
            rel = p.relative_to(ctx.root).parts
            if len(rel) >= 2 and rel[0] == "wiki" and rel[1] == "outputs":
                continue
            if "_ephemeral" in rel:
                continue
            yield p


def _embed_batch(
    client: OpenAI,
    model: str,
    texts: list[str],
) -> list[list[float]]:
    if not texts:
        return []
    try:
        resp = client.embeddings.create(model=model, input=texts)
    except Exception as exc:
        raise ValueError(_embedding_api_user_message(exc)) from exc
    out: list[list[float]] = []
    for item in sorted(resp.data, key=lambda x: x.index):
        out.append(list(item.embedding))
    return out


def embed_openai_batch(
    client: OpenAI,
    model: str,
    texts: list[str],
) -> list[list[float]]:
    """Embed multiple strings via the OpenAI-compatible embeddings API."""

    return _embed_batch(client, model, texts)


def _pack_embedding(vec: list[float]) -> tuple[bytes, int]:
    arr = np.array(vec, dtype=np.float32)
    return arr.tobytes(), arr.shape[0]


def _unpack_embedding(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def build_vector_index(
    ctx: VaultContext,
    *,
    reset: bool = False,
    config: EmbeddingConfig | None = None,
    client_factory: EmbeddingClientFactory | None = None,
) -> int:
    """
    Index all eligible ``*.md`` chunks; return number of chunks stored.

    Uses ``CRATE_EMBEDDING_*`` / ``OPENAI_API_KEY`` unless ``config`` is passed.
    """
    cfg = config or load_embedding_config()
    if cfg is None:
        raise ValueError(
            "Embedding API not configured. Set CRATE_EMBEDDING_API_KEY or "
            "OPENAI_API_KEY, optionally CRATE_EMBEDDING_BASE_URL and "
            "CRATE_EMBEDDING_MODEL."
        )
    ctx.meta_dir().mkdir(parents=True, exist_ok=True)
    db_path = index_database_path(ctx)
    conn = sqlite3.connect(str(db_path))
    try:
        _init_db(conn)
        if reset:
            conn.execute("DELETE FROM chunks")
            conn.commit()

        if client_factory is not None:
            client = client_factory(cfg)
        else:
            client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)

        rows: list[tuple[str, int, str]] = []
        for path in _iter_md_paths(ctx):
            try:
                body = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = path.relative_to(ctx.root).as_posix()
            for line_start, chunk in chunk_markdown(body):
                rows.append((rel, line_start, chunk))

        total = 0
        batch_size = cfg.embedding_batch_size
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            texts = [c for _, _, c in batch]
            vectors = _embed_batch(client, cfg.model, texts)
            for (rel, line_start, chunk), vec in zip(batch, vectors):
                blob, dim = _pack_embedding(vec)
                sha = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
                conn.execute(
                    """
                    INSERT OR REPLACE INTO chunks
                    (path, line_start, text, content_sha256, emb, dim)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (rel, line_start, chunk, sha, blob, dim),
                )
                total += 1
            conn.commit()

        conn.execute(
            "INSERT OR REPLACE INTO meta (k, v) VALUES (?, ?)",
            ("embedding_model", cfg.model),
        )
        conn.commit()
        return total
    finally:
        conn.close()


def semantic_search_hits(
    ctx: VaultContext,
    query: str,
    *,
    max_hits: int = 10,
    config: EmbeddingConfig | None = None,
    client_factory: EmbeddingClientFactory | None = None,
) -> list[dict[str, Any]]:
    """Return ``[{path, line, score, snippet}, ...]`` by cosine similarity."""
    cfg = config or load_embedding_config()
    if cfg is None:
        raise ValueError(
            "Embedding API not configured. Set CRATE_EMBEDDING_API_KEY or "
            "OPENAI_API_KEY."
        )
    db_path = index_database_path(ctx)
    if not db_path.is_file():
        return []

    if client_factory is not None:
        client = client_factory(cfg)
    else:
        client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)

    q_vecs = _embed_batch(client, cfg.model, [query.strip()])
    if not q_vecs:
        return []
    q = np.array(q_vecs[0], dtype=np.float32)

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute("SELECT path, line_start, text, emb FROM chunks")
        scored: list[tuple[float, str, int, str]] = []
        for path, line_start, text, emb_blob in cur.fetchall():
            v = _unpack_embedding(emb_blob)
            score = _cosine_sim(q, v)
            snippet = text.strip().replace("\n", " ")[:500]
            scored.append((score, path, int(line_start), snippet))
    finally:
        conn.close()

    scored.sort(key=lambda x: -x[0])
    out: list[dict[str, Any]] = []
    for score, path, line_start, snippet in scored[:max_hits]:
        out.append(
            {
                "path": path,
                "line": line_start,
                "score": round(score, 6),
                "snippet": snippet,
            }
        )
    return out


def index_exists(ctx: VaultContext) -> bool:
    """Whether ``meta/embeddings.sqlite`` exists and has at least one row."""
    p = index_database_path(ctx)
    if not p.is_file():
        return False
    conn = sqlite3.connect(str(p))
    try:
        _init_db(conn)
        n = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        return int(n) > 0
    finally:
        conn.close()
