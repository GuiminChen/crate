"""Convert between Obsidian wikilinks and standard Markdown links under ``wiki/``."""

from __future__ import annotations

import os
import re
from pathlib import Path

from crate.lint_wiki import (
    _resolve_link_target,
    resolve_wikilink_first_existing,
)
from crate.vault_paths import VaultContext, VaultPathError

__all__ = ["normalize_wiki_markdown"]

_WIKI_RE = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")
_MD_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")


def _split_front_matter(text: str) -> tuple[str, str]:
    if not text.startswith("---"):
        return "", text
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return "", text
    i = 1
    while i < len(lines):
        if lines[i].strip() == "---":
            fm = "".join(lines[: i + 1])
            rest = "".join(lines[i + 1 :])
            return fm, rest
        i += 1
    return "", text


def _display_from_inner(inner: str) -> str:
    part = inner.split("|", 1)[0].strip()
    return part.split("#", 1)[0].strip() or "link"


def _to_md_links_line(ctx: VaultContext, md_file: Path, line: str) -> str:
    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        target = resolve_wikilink_first_existing(ctx, inner)
        if target is None:
            return m.group(0)
        rel = os.path.relpath(target, md_file.parent).replace(os.sep, "/")
        disp = _display_from_inner(inner)
        if "|" in inner:
            disp = inner.split("|", 1)[1].strip() or disp
        return f"[{disp}]({rel})"

    return _WIKI_RE.sub(repl, line)


def _to_wikilinks_line(ctx: VaultContext, md_file: Path, line: str) -> str:
    def repl(m: re.Match[str]) -> str:
        text = m.group(1)
        href = m.group(2).strip()
        if not href or href.startswith("#"):
            return m.group(0)
        lower = href.split("?", 1)[0].split("#", 1)[0].lower()
        if lower.startswith(("http://", "https://", "mailto:")):
            return m.group(0)
        resolved = _resolve_link_target(md_file, href, ctx)
        if resolved is None or not resolved.exists():
            return m.group(0)
        stem = resolved.stem
        if text.strip() and text.strip() != stem:
            return f"[[{stem}|{text}]]"
        return f"[[{stem}]]"

    return _MD_LINK_RE.sub(repl, line)


def normalize_wiki_markdown(
    ctx: VaultContext,
    *,
    to_md_links: bool = False,
    to_wikilinks: bool = False,
    include_ephemeral: bool = False,
) -> tuple[int, list[str]]:
    """
    Walk ``wiki/**/*.md`` and rewrite links in place (atomic tmp + replace).

    Exactly one of ``to_md_links`` or ``to_wikilinks`` must be true.

    Returns ``(files_changed, relative_paths)``.
    """
    if to_md_links == to_wikilinks:
        raise ValueError("Set exactly one of to_md_links= or to_wikilinks=")

    wiki = ctx.wiki_dir()
    changed: list[str] = []
    n = 0
    for path in sorted(wiki.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            ctx.validate_under_vault(path)
        except VaultPathError:
            continue
        if not include_ephemeral and "_ephemeral" in path.relative_to(ctx.root).parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fm, body = _split_front_matter(text)
        out_lines: list[str] = []
        for line in body.splitlines(keepends=True):
            if to_md_links:
                out_lines.append(_to_md_links_line(ctx, path, line))
            else:
                out_lines.append(_to_wikilinks_line(ctx, path, line))
        new_body = "".join(out_lines)
        new_text = fm + new_body if fm else new_body
        if new_text != text:
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text(new_text, encoding="utf-8")
            os.replace(tmp, path)
            n += 1
            changed.append(path.relative_to(ctx.root).as_posix())
    return n, changed
