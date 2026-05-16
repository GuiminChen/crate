"""Logical paths for hosted wiki uploads (tenant-unified DB, session namespaces)."""

from __future__ import annotations


def wiki_logical_path_for_blob(*, blob_key: str, session_id: str = "") -> str:
    """Return stable wiki page path under one tenant DB.

    When ``session_id`` is non-empty, pages live under ``sessions/<id>/raw/...``
    so retrieval can default to session scope without a schema migration.

    Args:
        blob_key: Relative path inside blob store / vault raw (posix, no leading slash).
        session_id: Chat session id when uploads should stay session-scoped.

    Returns:
        Logical path key matching ``wiki_pages.logical_path``.
    """

    key = (blob_key or "").strip().replace("\\", "/").lstrip("/")
    if not key:
        raise ValueError("blob_key required")
    if ".." in key.split("/"):
        raise ValueError("invalid blob_key")
    sid = (session_id or "").strip()
    if sid:
        if "/" in sid or sid == "..":
            raise ValueError("invalid session_id")
        return f"sessions/{sid}/raw/{key}"
    return f"raw/{key}"


def session_path_prefix(session_id: str) -> str | None:
    """Return LIKE prefix for rows belonging to one chat session, or ``None`` for full tenant."""

    sid = (session_id or "").strip()
    if not sid:
        return None
    if "/" in sid or sid == "..":
        raise ValueError("invalid session_id")
    return f"sessions/{sid}/"
