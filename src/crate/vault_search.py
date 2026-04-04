"""Shared markdown search: ripgrep when available, else Python substring scan."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from crate.vault_paths import VaultContext, VaultPathError

__all__ = ["search_markdown_hits", "MAX_SEARCH_HITS_CAP"]

MAX_SEARCH_HITS_CAP = 100


def search_markdown_hits(
    ctx: VaultContext,
    query: str,
    *,
    max_hits: int = 20,
) -> list[dict[str, Any]]:
    """
    Search for a literal substring in ``*.md`` under ``wiki/`` and ``raw/``.

    Returns ``[{path, line, snippet}, ...]`` with paths relative to vault root.
    """
    cap = max(0, min(max_hits, MAX_SEARCH_HITS_CAP))
    q = query.strip()
    if not q or cap == 0:
        return []
    rg_hits = _search_rg(ctx, q, cap)
    if rg_hits is not None:
        return rg_hits
    return _search_python(ctx, q, cap)


def _search_python(
    ctx: VaultContext, query: str, max_hits: int
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    q_lower = query.lower()
    for base_name in ("wiki", "raw"):
        base = ctx.root / base_name
        if not base.is_dir():
            continue
        for md in sorted(base.rglob("*.md")):
            if len(hits) >= max_hits:
                break
            try:
                ctx.validate_under_vault(md)
            except VaultPathError:
                continue
            try:
                lines = md.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, start=1):
                if len(hits) >= max_hits:
                    break
                if q_lower in line.lower():
                    hits.append(
                        {
                            "path": md.relative_to(ctx.root).as_posix(),
                            "line": i,
                            "snippet": line.strip()[:500],
                        }
                    )
    return hits


def _search_rg(
    ctx: VaultContext, query: str, max_hits: int
) -> list[dict[str, Any]] | None:
    rg = shutil.which("rg")
    if not rg:
        return None
    wiki = ctx.wiki_dir()
    raw = ctx.raw_dir()
    paths: list[str] = []
    if wiki.is_dir():
        paths.append(str(wiki.resolve()))
    if raw.is_dir():
        paths.append(str(raw.resolve()))
    if not paths:
        return []
    cmd = [
        rg,
        "--json",
        "-F",
        "--glob",
        "*.md",
        "--",
        query,
        *paths,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode not in (0, 1):
        return None
    hits: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        if len(hits) >= max_hits:
            break
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "match":
            continue
        data = obj.get("data") or {}
        path_obj = data.get("path") or {}
        path_text = path_obj.get("text")
        if not path_text:
            continue
        abs_path = Path(path_text)
        if not abs_path.is_absolute():
            abs_path = (ctx.root / abs_path).resolve()
        else:
            abs_path = abs_path.resolve()
        try:
            canon = ctx.validate_under_vault(abs_path)
            rel = canon.relative_to(ctx.root).as_posix()
        except VaultPathError:
            continue
        lines_obj = data.get("lines") or {}
        text = (lines_obj.get("text") or "").rstrip("\n")
        line_no = int(data.get("line_number", 0))
        snippet = text.strip()[:500]
        hits.append({"path": rel, "line": line_no, "snippet": snippet})
    return hits
