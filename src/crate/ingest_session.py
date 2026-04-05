"""Parse ``.crate/ingest_session.md`` for explicit raw paths (thin ingest wrapper)."""

from __future__ import annotations

from pathlib import Path

from crate.vault_paths import VaultContext

DEFAULT_SESSION_REL = ".crate/ingest_session.md"

__all__ = [
    "DEFAULT_SESSION_REL",
    "parse_ingest_session_text",
    "default_session_path",
]


def default_session_path(ctx: VaultContext) -> Path:
    """``$VAULT/.crate/ingest_session.md``."""
    return ctx.root / DEFAULT_SESSION_REL


def parse_ingest_session_text(text: str) -> list[str]:
    """
    Non-comment non-empty lines as vault-relative ``raw/...`` paths.

    Lines starting with ``#`` are skipped. Whitespace stripped.
    """
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        s = s.replace("\\", "/")
        if s.startswith("raw/"):
            out.append(s)
    return out
