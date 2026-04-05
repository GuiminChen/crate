"""Extended machine index: wiki/notes pages (disk scan, no LLM)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crate.vault_paths import VaultContext, VaultPathError

WIKI_INDEX_EXTENDED_FILENAME = "wiki_index_extended.json"

__all__ = [
    "WIKI_INDEX_EXTENDED_FILENAME",
    "build_wiki_index_extended",
    "write_wiki_index_extended",
]


def _strip_front_matter(text: str) -> str:
    if not text.startswith("---"):
        return text
    lines = text.splitlines()
    if len(lines) < 2 or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1 :])
    return text


def _first_paragraph_excerpt(path: Path, *, max_chars: int = 220) -> str:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "_(unreadable)_"
    body = _strip_front_matter(raw).strip()
    if not body:
        return "_(empty body)_"
    para = body.split("\n\n", 1)[0].replace("\n", " ").strip()
    if len(para) > max_chars:
        return para[: max_chars - 1] + "…"
    return para


def _title_from_front_matter(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    if len(lines) < 2 or lines[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None
    fm = "\n".join(lines[1:end])
    for line in fm.splitlines():
        if line.strip().lower().startswith("title:"):
            rest = line.split(":", 1)[1].strip()
            return rest.strip().strip('"').strip("'") or None
    return None


def build_wiki_index_extended(ctx: VaultContext) -> dict[str, Any]:
    """List ``wiki/notes/**/*.md`` with title + excerpt."""
    notes = ctx.wiki_dir() / "notes"
    pages: list[dict[str, Any]] = []
    if notes.is_dir():
        for path in sorted(notes.rglob("*.md")):
            if not path.is_file():
                continue
            try:
                ctx.validate_under_vault(path)
            except VaultPathError:
                continue
            rel = path.relative_to(ctx.root).as_posix()
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            title = _title_from_front_matter(raw) or path.stem
            pages.append(
                {
                    "path": rel,
                    "title": title,
                    "excerpt": _first_paragraph_excerpt(path),
                }
            )
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "version": 1,
        "generated_at": stamp,
        "kind": "wiki_notes_index",
        "pages": pages,
    }


def write_wiki_index_extended(ctx: VaultContext) -> Path:
    """Write ``meta/wiki_index_extended.json``."""
    payload = build_wiki_index_extended(ctx)
    meta = ctx.meta_dir()
    meta.mkdir(parents=True, exist_ok=True)
    path = meta / WIKI_INDEX_EXTENDED_FILENAME
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return path
