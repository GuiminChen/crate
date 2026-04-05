"""Report which raw/ sources are referenced from wiki/ (deterministic heuristics)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crate.compile_run import collect_raw_sources
from crate.lint_wiki import _MD_LINK_RE, _resolve_link_target
from crate.vault_paths import VaultContext, VaultPathError

RAW_WIKI_COVERAGE_FILENAME = "raw_wiki_coverage.json"

__all__ = [
    "RAW_WIKI_COVERAGE_FILENAME",
    "build_raw_wiki_coverage",
    "write_raw_wiki_coverage",
]


def _list_wiki_files_for_scan(
    ctx: VaultContext,
    *,
    include_ephemeral: bool,
) -> list[Path]:
    wiki = ctx.wiki_dir()
    if not wiki.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(wiki.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            ctx.validate_under_vault(path)
        except VaultPathError:
            continue
        rel_parts = path.relative_to(ctx.root).parts
        if not include_ephemeral and "_ephemeral" in rel_parts:
            continue
        out.append(path)
    return out


def _scan_wiki_for_raw_ref(
    wiki_path: Path,
    raw_rel: str,
    ctx: VaultContext,
) -> bool:
    """Return True if this wiki file references the raw path."""
    try:
        text = wiki_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if raw_rel in text:
        return True
    lines = text.splitlines()
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in _MD_LINK_RE.finditer(line):
            href = m.group(1).strip()
            resolved = _resolve_link_target(wiki_path, href, ctx)
            if resolved is None:
                continue
            try:
                rel = resolved.relative_to(ctx.root).as_posix()
            except ValueError:
                continue
            if rel == raw_rel:
                return True
    return False


def build_raw_wiki_coverage(
    ctx: VaultContext,
    *,
    include_ephemeral: bool = False,
) -> dict[str, Any]:
    """Map each raw source to referencing wiki pages (posix paths)."""
    raw_paths = collect_raw_sources(ctx)
    wiki_files = _list_wiki_files_for_scan(ctx, include_ephemeral=include_ephemeral)
    entries: list[dict[str, Any]] = []
    for rp in raw_paths:
        raw_rel = rp.relative_to(ctx.root).as_posix()
        refs: list[str] = []
        for wp in wiki_files:
            wrel = wp.relative_to(ctx.root).as_posix()
            if _scan_wiki_for_raw_ref(wp, raw_rel, ctx):
                refs.append(wrel)
        entries.append(
            {
                "path": raw_rel,
                "status": "referenced" if refs else "unreferenced",
                "referenced_by": sorted(set(refs)),
            }
        )
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "version": 1,
        "generated_at": stamp,
        "sources": entries,
    }


def write_raw_wiki_coverage(
    ctx: VaultContext,
    *,
    include_ephemeral: bool = False,
) -> Path:
    """Write ``meta/raw_wiki_coverage.json``."""
    payload = build_raw_wiki_coverage(ctx, include_ephemeral=include_ephemeral)
    meta = ctx.meta_dir()
    meta.mkdir(parents=True, exist_ok=True)
    path = meta / RAW_WIKI_COVERAGE_FILENAME
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return path
