"""Stable entrypoints for hosts (Agentium) importing ``crate`` as a library."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional, Sequence

import structlog
from openai import OpenAI
from pathlib import Path

from crate.embedding_config import EmbeddingConfig, load_embedding_config
from crate.stores.raw_blob import RawBlobStore
from crate.stores.sync_vault import materialize_raw_blobs_to_vault
from crate.stores.wiki_database import WikiDatabase, WikiPageRecord, WikiPageSummary
from crate.stores.wiki_paths import session_path_prefix
from crate.vector_index import chunk_markdown, embed_openai_batch
from crate.vault_paths import VaultContext, resolve_vault_root

_LOGGER = structlog.get_logger(__name__)

__all__ = [
    "HostWikiConfig",
    "LlmWikiHost",
    "embedding_rows_from_markdown",
]


def _pack_f32(vec: List[float]) -> tuple[bytes, int]:
    import numpy as np

    arr = np.array(vec, dtype=np.float32)
    return arr.tobytes(), int(arr.shape[0])


class HostWikiConfig:
    """Embedding client wiring for semantic search (optional)."""

    def __init__(self, embedding: Optional[EmbeddingConfig] = None) -> None:
        self.embedding = embedding


def embedding_rows_from_markdown(
    page_path: str,
    markdown: str,
    client: OpenAI,
    model: str,
) -> List[tuple[str, int, str, str, bytes, int]]:
    """Chunk markdown and produce DB rows for :meth:`WikiDatabase.replace_page_chunks`."""

    parts: List[tuple[str, int, str]] = []
    for line_start, chunk in chunk_markdown(markdown):
        parts.append((page_path, line_start, chunk))
    if not parts:
        return []
    texts = [c for _, _, c in parts]
    vectors = embed_openai_batch(client, model, texts)
    out: List[tuple[str, int, str, str, bytes, int]] = []
    for (path, line_start, chunk_text), vec in zip(parts, vectors):
        blob, dim = _pack_f32(list(vec))
        sha = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
        out.append((path, line_start, chunk_text, sha, blob, dim))
    return out


class LlmWikiHost:
    """Facade: blob sync + wiki DB persistence and search."""

    def __init__(
        self,
        *,
        wiki_db: WikiDatabase,
        blobs: Optional[RawBlobStore] = None,
        host_wiki_config: Optional[HostWikiConfig] = None,
    ) -> None:
        self._wiki = wiki_db
        self._blobs = blobs
        self._cfg = host_wiki_config or HostWikiConfig()

    @property
    def wiki_db(self) -> WikiDatabase:
        return self._wiki

    @property
    def blobs(self) -> Optional[RawBlobStore]:
        return self._blobs

    def materialize_to_vault(
        self,
        tenant_id: str,
        blob_keys: Sequence[str],
        vault_root: Path,
    ) -> List[Path]:
        """Copy listed blob keys into ``vault_root/raw/``."""

        if self._blobs is None:
            raise RuntimeError("RawBlobStore not configured on LlmWikiHost")
        ctx = VaultContext(Path(resolve_vault_root(Path.cwd(), str(vault_root))))
        return materialize_raw_blobs_to_vault(self._blobs, tenant_id, blob_keys, ctx)

    def upsert_markdown_page(
        self,
        *,
        tenant_id: str,
        logical_path: str,
        body_md: str,
    ) -> WikiPageRecord:
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        sha = hashlib.sha256(body_md.encode("utf-8")).hexdigest()
        rec = WikiPageRecord(
            tenant_id=tenant_id,
            logical_path=logical_path,
            body_md=body_md,
            content_sha256=sha,
            updated_at=now,
        )
        self._wiki.upsert_page(rec)
        _LOGGER.info(
            "wiki_page_upserted",
            tenant_id=tenant_id,
            logical_path=logical_path,
        )
        return rec

    def list_page_summaries(
        self,
        tenant_id: str,
        *,
        path_prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WikiPageSummary]:
        """List wiki paths for vault UI (summary rows, no bulk body fetch)."""

        return self._wiki.list_page_summaries(
            tenant_id.strip(),
            path_prefix=path_prefix,
            limit=limit,
            offset=offset,
        )

    def get_page(self, tenant_id: str, logical_path: str) -> Optional[WikiPageRecord]:
        """Return full page row or ``None`` if absent / after validation."""

        return self._wiki.get_page(tenant_id.strip(), logical_path)

    def reindex_page_embeddings(
        self,
        *,
        tenant_id: str,
        page_path: str,
        markdown: str,
        client_factory: Optional[Callable[[EmbeddingConfig], OpenAI]] = None,
    ) -> int:
        """Rebuild vectors for one page via replace_page_chunks."""

        cfg = self._cfg.embedding or load_embedding_config()
        if cfg is None:
            _LOGGER.warning("embedding_disabled_skip_reindex")
            return 0
        if client_factory is not None:
            client = client_factory(cfg)
        else:
            client = OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
        rows = embedding_rows_from_markdown(page_path, markdown, client, cfg.model)
        if not rows:
            return self._wiki.replace_page_chunks(tenant_id, page_path, [])
        return self._wiki.replace_page_chunks(tenant_id, page_path, rows)

    def search(
        self,
        tenant_id: str,
        query: str,
        *,
        literal: bool = True,
        semantic: bool = False,
        limit: int = 10,
        query_embedding: Optional[Sequence[float]] = None,
        scope: str = "session",
        chat_session_id: str = "",
    ) -> dict[str, Any]:
        """Search wiki pages; ``scope`` is ``session`` (chat uploads) or ``tenant`` (full library)."""

        scope_norm = (scope or "session").strip().lower()
        if scope_norm not in ("session", "tenant"):
            scope_norm = "session"
        path_prefix: Optional[str] = None
        if scope_norm == "session":
            sid = (chat_session_id or "").strip()
            if not sid:
                return {
                    "literals": [],
                    "semantic": [],
                    "search_meta": {
                        "scope": scope_norm,
                        "path_prefix": None,
                        "hint": "session_scope_requires_session_id",
                    },
                }
            path_prefix = session_path_prefix(sid)
        meta = {
            "scope": scope_norm,
            "path_prefix": path_prefix,
        }
        out: dict[str, Any] = {"literals": [], "semantic": [], "search_meta": meta}
        if literal:
            pages = self._wiki.search_literals(
                tenant_id, query, limit=limit, path_prefix=path_prefix
            )
            out["literals"] = [p.__dict__ for p in pages]
        if semantic:
            if query_embedding is None:
                _LOGGER.warning("semantic_search_missing_embedding")
            else:
                hits = self._wiki.semantic_search_hits(
                    tenant_id,
                    list(query_embedding),
                    limit=limit,
                    path_prefix=path_prefix,
                )
                out["semantic"] = [h.__dict__ for h in hits]
        return out
