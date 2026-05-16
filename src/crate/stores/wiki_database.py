"""Wiki page + embedding chunk storage (SQLite or PostgreSQL, multi-tenant)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional, Protocol, Sequence, Tuple, Union, runtime_checkable

import numpy as np

__all__ = [
    "WikiDbBackend",
    "WikiDatabase",
    "WikiPageRecord",
    "WikiPageSummary",
    "SemanticHit",
    "SqliteWikiDatabase",
    "PostgresWikiDatabase",
    "build_wiki_database",
]


@dataclass(frozen=True)
class WikiPageRecord:
    """One wiki page row."""

    tenant_id: str
    logical_path: str
    body_md: str
    content_sha256: str
    updated_at: str


@dataclass(frozen=True)
class WikiPageSummary:
    """Lightweight wiki page row without ``body_md`` (vault listing)."""

    tenant_id: str
    logical_path: str
    content_sha256: str
    updated_at: str


@dataclass(frozen=True)
class SemanticHit:
    """Chunk hit with cosine similarity score."""

    path: str
    line_start: int
    text: str
    score: float


def normalize_wiki_prefix_for_like(prefix: Optional[str]) -> str:
    """Return prefix used as ``LIKE prefix%``. Empty string selects all tenant rows."""

    raw = (prefix or "").strip().replace("\\", "/").lstrip("/")
    if raw and ".." in raw.split("/"):
        raise ValueError("invalid path prefix")
    return raw


def normalize_wiki_logical_path_key(path: str) -> str:
    """Normalize and validate wiki primary key segment (reject ``..``)."""

    raw = (path or "").strip().replace("\\", "/").lstrip("/")
    if not raw:
        raise ValueError("logical_path required")
    if ".." in raw.split("/"):
        raise ValueError("invalid logical_path")
    return raw


@runtime_checkable
class WikiDatabase(Protocol):
    """Canonical wiki text + chunk embeddings for a single deployment."""

    def upsert_page(self, record: WikiPageRecord) -> None:
        ...

    def delete_pages_with_prefix(self, tenant_id: str, path_prefix: str) -> None:
        ...

    def list_page_summaries(
        self,
        tenant_id: str,
        *,
        path_prefix: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WikiPageSummary]:
        ...

    def get_page(self, tenant_id: str, logical_path: str) -> Optional[WikiPageRecord]:
        """Return exact page row or ``None`` if missing."""

        ...

    def search_literals(
        self,
        tenant_id: str,
        query: str,
        *,
        limit: int = 20,
        path_prefix: Optional[str] = None,
    ) -> List[WikiPageRecord]:
        ...

    def replace_chunks(
        self,
        tenant_id: str,
        rows: Sequence[Tuple[str, int, str, str, bytes, int]],
    ) -> int:
        """Replace **all** chunks for ``tenant_id``."""

    def replace_page_chunks(
        self,
        tenant_id: str,
        page_path: str,
        rows: Sequence[Tuple[str, int, str, str, bytes, int]],
    ) -> int:
        """Replace chunks for a single ``page_path`` (delete path rows, then insert)."""

    def semantic_search_hits(
        self,
        tenant_id: str,
        query_embedding: Sequence[float],
        *,
        limit: int = 10,
        path_prefix: Optional[str] = None,
    ) -> List[SemanticHit]:
        ...


class WikiDbBackend(str, Enum):
    sqlite = "sqlite"
    postgresql = "postgresql"


_SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS wiki_pages (
    tenant_id TEXT NOT NULL,
    logical_path TEXT NOT NULL,
    body_md TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, logical_path)
);

CREATE TABLE IF NOT EXISTS wiki_chunks (
    tenant_id TEXT NOT NULL,
    path TEXT NOT NULL,
    line_start INTEGER NOT NULL,
    text TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    emb BLOB NOT NULL,
    dim INTEGER NOT NULL,
    PRIMARY KEY (tenant_id, path, line_start)
);
CREATE INDEX IF NOT EXISTS idx_wiki_pages_tenant ON wiki_pages (tenant_id);
CREATE INDEX IF NOT EXISTS idx_wiki_chunks_tenant ON wiki_chunks (tenant_id);
"""

_SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS wiki_pages (
    tenant_id TEXT NOT NULL,
    logical_path TEXT NOT NULL,
    body_md TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, logical_path)
);

CREATE TABLE IF NOT EXISTS wiki_chunks (
    tenant_id TEXT NOT NULL,
    path TEXT NOT NULL,
    line_start INTEGER NOT NULL,
    text TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    emb BYTEA NOT NULL,
    dim INTEGER NOT NULL,
    PRIMARY KEY (tenant_id, path, line_start)
);
CREATE INDEX IF NOT EXISTS idx_wiki_pages_tenant ON wiki_pages (tenant_id);
CREATE INDEX IF NOT EXISTS idx_wiki_chunks_tenant ON wiki_chunks (tenant_id);
"""


def _pack_f32(vec: Sequence[float]) -> bytes:
    arr = np.array(list(vec), dtype=np.float32)
    return arr.tobytes()


def _unpack_f32(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


class SqliteWikiDatabase:
    """SQLite file with ``tenant_id`` on all rows."""

    def __init__(self, sqlite_path: Path) -> None:
        self._path = Path(sqlite_path).expanduser().resolve()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._path))
        try:
            conn.executescript(_SCHEMA_SQLITE)
            conn.commit()
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._path))

    def upsert_page(self, record: WikiPageRecord) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO wiki_pages (tenant_id, logical_path, body_md, content_sha256, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, logical_path) DO UPDATE SET
                  body_md=excluded.body_md,
                  content_sha256=excluded.content_sha256,
                  updated_at=excluded.updated_at
                """,
                (
                    record.tenant_id,
                    record.logical_path,
                    record.body_md,
                    record.content_sha256,
                    record.updated_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_pages_with_prefix(self, tenant_id: str, path_prefix: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM wiki_pages WHERE tenant_id = ? AND logical_path LIKE ?",
                (tenant_id, path_prefix + "%"),
            )
            conn.commit()
        finally:
            conn.close()

    def list_page_summaries(
        self,
        tenant_id: str,
        *,
        path_prefix: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WikiPageSummary]:
        pref = normalize_wiki_prefix_for_like(path_prefix)
        lim = max(0, min(2000, int(limit)))
        off = max(0, int(offset))
        tid = tenant_id.strip()
        conn = self._connect()
        try:
            if pref:
                cur = conn.execute(
                    """
                    SELECT tenant_id, logical_path, content_sha256, updated_at
                    FROM wiki_pages
                    WHERE tenant_id = ? AND logical_path LIKE ?
                    ORDER BY logical_path ASC
                    LIMIT ? OFFSET ?
                    """,
                    (tid, f"{pref}%", lim, off),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT tenant_id, logical_path, content_sha256, updated_at
                    FROM wiki_pages
                    WHERE tenant_id = ?
                    ORDER BY logical_path ASC
                    LIMIT ? OFFSET ?
                    """,
                    (tid, lim, off),
                )
            rows = cur.fetchall()
        finally:
            conn.close()
        return [
            WikiPageSummary(
                tenant_id=str(r[0]),
                logical_path=str(r[1]),
                content_sha256=str(r[2]),
                updated_at=str(r[3]),
            )
            for r in rows
        ]

    def get_page(self, tenant_id: str, logical_path: str) -> Optional[WikiPageRecord]:
        lp = normalize_wiki_logical_path_key(logical_path)
        conn = self._connect()
        try:
            cur = conn.execute(
                """
                SELECT tenant_id, logical_path, body_md, content_sha256, updated_at
                FROM wiki_pages
                WHERE tenant_id = ? AND logical_path = ?
                """,
                (tenant_id.strip(), lp),
            )
            row = cur.fetchone()
        finally:
            conn.close()
        if row is None:
            return None
        return WikiPageRecord(
            tenant_id=str(row[0]),
            logical_path=str(row[1]),
            body_md=str(row[2]),
            content_sha256=str(row[3]),
            updated_at=str(row[4]),
        )

    def search_literals(
        self,
        tenant_id: str,
        query: str,
        *,
        limit: int = 20,
        path_prefix: Optional[str] = None,
    ) -> List[WikiPageRecord]:
        if not query.strip():
            return []
        conn = self._connect()
        try:
            pf = (path_prefix or "").strip()
            if pf:
                cur = conn.execute(
                    """
                    SELECT tenant_id, logical_path, body_md, content_sha256, updated_at
                    FROM wiki_pages
                    WHERE tenant_id = ? AND logical_path LIKE ? AND body_md LIKE ?
                    LIMIT ?
                    """,
                    (tenant_id, f"{pf}%", f"%{query}%", limit),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT tenant_id, logical_path, body_md, content_sha256, updated_at
                    FROM wiki_pages
                    WHERE tenant_id = ? AND body_md LIKE ?
                    LIMIT ?
                    """,
                    (tenant_id, f"%{query}%", limit),
                )
            rows = cur.fetchall()
        finally:
            conn.close()
        return [
            WikiPageRecord(
                tenant_id=r[0],
                logical_path=r[1],
                body_md=r[2],
                content_sha256=r[3],
                updated_at=r[4],
            )
            for r in rows
        ]

    def replace_chunks(
        self,
        tenant_id: str,
        rows: Sequence[Tuple[str, int, str, str, bytes, int]],
    ) -> int:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM wiki_chunks WHERE tenant_id = ?", (tenant_id,))
            total = 0
            for path, line_start, text, sha256, emb, dim in rows:
                conn.execute(
                    """
                    INSERT INTO wiki_chunks
                    (tenant_id, path, line_start, text, content_sha256, emb, dim)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tenant_id, path, line_start, text, sha256, emb, dim),
                )
                total += 1
            conn.commit()
            return total
        finally:
            conn.close()

    def replace_page_chunks(
        self,
        tenant_id: str,
        page_path: str,
        rows: Sequence[Tuple[str, int, str, str, bytes, int]],
    ) -> int:
        conn = self._connect()
        try:
            conn.execute(
                "DELETE FROM wiki_chunks WHERE tenant_id = ? AND path = ?",
                (tenant_id, page_path),
            )
            total = 0
            for path, line_start, text, sha256, emb, dim in rows:
                conn.execute(
                    """
                    INSERT INTO wiki_chunks
                    (tenant_id, path, line_start, text, content_sha256, emb, dim)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tenant_id, path, line_start, text, sha256, emb, dim),
                )
                total += 1
            conn.commit()
            return total
        finally:
            conn.close()

    def semantic_search_hits(
        self,
        tenant_id: str,
        query_embedding: Sequence[float],
        *,
        limit: int = 10,
        path_prefix: Optional[str] = None,
    ) -> List[SemanticHit]:
        q = _unpack_f32(_pack_f32(query_embedding))
        conn = self._connect()
        try:
            pf = (path_prefix or "").strip()
            if pf:
                cur = conn.execute(
                    """
                    SELECT path, line_start, text, emb FROM wiki_chunks
                    WHERE tenant_id = ? AND path LIKE ?
                    """,
                    (tenant_id, f"{pf}%"),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT path, line_start, text, emb FROM wiki_chunks
                    WHERE tenant_id = ?
                    """,
                    (tenant_id,),
                )
            scored: List[SemanticHit] = []
            for path, line_start, text, emb_blob in cur:
                vec = _unpack_f32(emb_blob)
                scored.append(
                    SemanticHit(
                        path=str(path),
                        line_start=int(line_start),
                        text=str(text),
                        score=_cosine(q, vec),
                    )
                )
        finally:
            conn.close()
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:limit]


class PostgresWikiDatabase:
    """PostgreSQL backend using psycopg3 when available."""

    def __init__(self, conninfo: str) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "PostgresWikiDatabase requires psycopg (pip install 'psycopg[binary]')"
            ) from exc
        self._psycopg = psycopg
        self._conninfo = conninfo
        with psycopg.connect(conninfo) as conn:
            for raw_stmt in _SCHEMA_PG.split(";"):
                stmt = raw_stmt.strip()
                if stmt:
                    conn.execute(stmt)
            conn.commit()

    def upsert_page(self, record: WikiPageRecord) -> None:
        with self._psycopg.connect(self._conninfo) as conn:
            conn.execute(
                """
                INSERT INTO wiki_pages
                  (tenant_id, logical_path, body_md, content_sha256, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (tenant_id, logical_path) DO UPDATE SET
                  body_md = EXCLUDED.body_md,
                  content_sha256 = EXCLUDED.content_sha256,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    record.tenant_id,
                    record.logical_path,
                    record.body_md,
                    record.content_sha256,
                    record.updated_at,
                ),
            )
            conn.commit()

    def delete_pages_with_prefix(self, tenant_id: str, path_prefix: str) -> None:
        with self._psycopg.connect(self._conninfo) as conn:
            conn.execute(
                "DELETE FROM wiki_pages WHERE tenant_id = %s AND logical_path LIKE %s",
                (tenant_id, path_prefix + "%"),
            )
            conn.commit()

    def list_page_summaries(
        self,
        tenant_id: str,
        *,
        path_prefix: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WikiPageSummary]:
        pref = normalize_wiki_prefix_for_like(path_prefix)
        lim = max(0, min(2000, int(limit)))
        off = max(0, int(offset))
        tid = tenant_id.strip()
        with self._psycopg.connect(self._conninfo) as conn:
            if pref:
                cur = conn.execute(
                    """
                    SELECT tenant_id, logical_path, content_sha256, updated_at
                    FROM wiki_pages
                    WHERE tenant_id = %s AND logical_path LIKE %s
                    ORDER BY logical_path ASC
                    LIMIT %s OFFSET %s
                    """,
                    (tid, f"{pref}%", lim, off),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT tenant_id, logical_path, content_sha256, updated_at
                    FROM wiki_pages
                    WHERE tenant_id = %s
                    ORDER BY logical_path ASC
                    LIMIT %s OFFSET %s
                    """,
                    (tid, lim, off),
                )
            rows = cur.fetchall()
        return [
            WikiPageSummary(
                tenant_id=str(r[0]),
                logical_path=str(r[1]),
                content_sha256=str(r[2]),
                updated_at=str(r[3]),
            )
            for r in rows
        ]

    def get_page(self, tenant_id: str, logical_path: str) -> Optional[WikiPageRecord]:
        lp = normalize_wiki_logical_path_key(logical_path)
        with self._psycopg.connect(self._conninfo) as conn:
            cur = conn.execute(
                """
                SELECT tenant_id, logical_path, body_md, content_sha256, updated_at
                FROM wiki_pages
                WHERE tenant_id = %s AND logical_path = %s
                """,
                (tenant_id.strip(), lp),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return WikiPageRecord(
            tenant_id=str(row[0]),
            logical_path=str(row[1]),
            body_md=str(row[2]),
            content_sha256=str(row[3]),
            updated_at=str(row[4]),
        )

    def search_literals(
        self,
        tenant_id: str,
        query: str,
        *,
        limit: int = 20,
        path_prefix: Optional[str] = None,
    ) -> List[WikiPageRecord]:
        if not query.strip():
            return []
        pf = (path_prefix or "").strip()
        with self._psycopg.connect(self._conninfo) as conn:
            if pf:
                cur = conn.execute(
                    """
                    SELECT tenant_id, logical_path, body_md, content_sha256, updated_at
                    FROM wiki_pages
                    WHERE tenant_id = %s AND logical_path LIKE %s AND body_md ILIKE %s
                    LIMIT %s
                    """,
                    (tenant_id, f"{pf}%", f"%{query}%", limit),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT tenant_id, logical_path, body_md, content_sha256, updated_at
                    FROM wiki_pages
                    WHERE tenant_id = %s AND body_md ILIKE %s
                    LIMIT %s
                    """,
                    (tenant_id, f"%{query}%", limit),
                )
            rows = cur.fetchall()
        return [
            WikiPageRecord(
                tenant_id=r[0],
                logical_path=r[1],
                body_md=r[2],
                content_sha256=r[3],
                updated_at=r[4],
            )
            for r in rows
        ]

    def replace_chunks(
        self,
        tenant_id: str,
        rows: Sequence[Tuple[str, int, str, str, bytes, int]],
    ) -> int:
        with self._psycopg.connect(self._conninfo) as conn:
            conn.execute("DELETE FROM wiki_chunks WHERE tenant_id = %s", (tenant_id,))
            total = 0
            for path, line_start, text, sha256, emb, dim in rows:
                conn.execute(
                    """
                    INSERT INTO wiki_chunks
                    (tenant_id, path, line_start, text, content_sha256, emb, dim)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (tenant_id, path, line_start, text, sha256, emb, dim),
                )
                total += 1
            conn.commit()
        return total

    def replace_page_chunks(
        self,
        tenant_id: str,
        page_path: str,
        rows: Sequence[Tuple[str, int, str, str, bytes, int]],
    ) -> int:
        with self._psycopg.connect(self._conninfo) as conn:
            conn.execute(
                "DELETE FROM wiki_chunks WHERE tenant_id = %s AND path = %s",
                (tenant_id, page_path),
            )
            total = 0
            for path, line_start, text, sha256, emb, dim in rows:
                conn.execute(
                    """
                    INSERT INTO wiki_chunks
                    (tenant_id, path, line_start, text, content_sha256, emb, dim)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (tenant_id, path, line_start, text, sha256, emb, dim),
                )
                total += 1
            conn.commit()
        return total

    def semantic_search_hits(
        self,
        tenant_id: str,
        query_embedding: Sequence[float],
        *,
        limit: int = 10,
        path_prefix: Optional[str] = None,
    ) -> List[SemanticHit]:
        q = _unpack_f32(_pack_f32(query_embedding))
        pf = (path_prefix or "").strip()
        with self._psycopg.connect(self._conninfo) as conn:
            if pf:
                cur = conn.execute(
                    """
                    SELECT path, line_start, text, emb FROM wiki_chunks
                    WHERE tenant_id = %s AND path LIKE %s
                    """,
                    (tenant_id, f"{pf}%"),
                )
            else:
                cur = conn.execute(
                    "SELECT path, line_start, text, emb FROM wiki_chunks WHERE tenant_id = %s",
                    (tenant_id,),
                )
            rows = cur.fetchall()
        scored = [
            SemanticHit(
                path=str(r[0]),
                line_start=int(r[1]),
                text=str(r[2]),
                score=_cosine(q, _unpack_f32(bytes(r[3]))),
            )
            for r in rows
        ]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:limit]


def build_wiki_database(
    backend: Union[WikiDbBackend, str],
    *,
    sqlite_path: Optional[Path] = None,
    postgresql_conninfo: Optional[str] = None,
) -> WikiDatabase:
    """Construct a :class:`WikiDatabase` for the given backend."""

    be = WikiDbBackend(backend) if isinstance(backend, str) else backend
    if be == WikiDbBackend.sqlite:
        if sqlite_path is None:
            raise ValueError("sqlite_path required for sqlite wiki db")
        return SqliteWikiDatabase(Path(sqlite_path))
    if be == WikiDbBackend.postgresql:
        if not postgresql_conninfo or not str(postgresql_conninfo).strip():
            raise ValueError("postgresql_conninfo required for postgresql wiki db")
        return PostgresWikiDatabase(str(postgresql_conninfo).strip())
    raise ValueError(f"unsupported wiki db backend: {be}")
