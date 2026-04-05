"""Append-only activity timeline at ``wiki/_index/LOG.md``."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from crate.vault_paths import VaultContext

__all__ = ["ACTIVITY_LOG_REL", "append_activity_log", "activity_log_enabled"]

ACTIVITY_LOG_REL = "wiki/_index/LOG.md"


def activity_log_enabled() -> bool:
    """Return False when ``CRATE_NO_ACTIVITY_LOG`` is set (skip all LOG hooks)."""
    v = os.environ.get("CRATE_NO_ACTIVITY_LOG", "").strip().lower()
    return v not in ("1", "true", "yes", "on")


def _markdown_heading_format() -> bool:
    """When set, use ``## [YYYY-MM-DD]`` lines (see llm-wiki.md grep tip)."""
    v = os.environ.get("CRATE_LOG_MARKDOWN_HEADINGS", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def append_activity_log(ctx: VaultContext, kind: str, detail: str) -> Path | None:
    """
    Append one line to ``wiki/_index/LOG.md`` (creates file with header if missing).

    Line format: bullet ``- UTC | kind | detail``, or ``## [YYYY-MM-DD] kind | detail``
    when ``CRATE_LOG_MARKDOWN_HEADINGS=1``.
    """
    if not activity_log_enabled():
        return None
    path = ctx.wiki_dir() / "_index" / "LOG.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_kind = kind.replace("|", "/").strip() or "event"
    safe_detail = detail.replace("\n", " ").replace("|", "/").strip()[:500]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _markdown_heading_format():
        line = f"## [{day}] {safe_kind} | {safe_detail}\n\n"
    else:
        line = f"- {ts} | {safe_kind} | {safe_detail}\n"
    if not path.exists():
        path.write_text(
            "# Activity log\n\n"
            "_Append-only timeline of `crate` events (UTC). "
            "Disable with `CRATE_NO_ACTIVITY_LOG=1`. "
            "See CRATE project `docs/usage.md` (§5.2, §7)._\n\n",
            encoding="utf-8",
        )
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
    return path
