"""Append Q&A output links to RECENT.md (optional feedback loop)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from crate.vault_paths import VaultContext

__all__ = ["append_output_to_recent"]


def append_output_to_recent(
    ctx: VaultContext,
    output_rel: str,
    *,
    question_preview: str,
) -> Path:
    """Append a bullet line to ``wiki/_index/RECENT.md`` with link to output."""
    recent = ctx.wiki_dir() / "_index" / "RECENT.md"
    recent.parent.mkdir(parents=True, exist_ok=True)
    if not recent.exists():
        recent.write_text("# 最近变更\n\n", encoding="utf-8")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    preview = question_preview.replace("\n", " ").strip()[:120]
    line = f"- {ts} — [{preview}]({output_rel})\n"
    with recent.open("a", encoding="utf-8") as f:
        f.write(line)
    return recent
