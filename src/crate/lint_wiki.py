"""Deterministic wiki checks: local ``[text](url)`` and ``![alt](url)`` must resolve."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from crate.vault_paths import VaultContext, VaultPathError

__all__ = [
    "LintIssue",
    "WikiOutgoingEdge",
    "iter_wiki_outgoing_edges",
    "lint_markdown_links",
    "resolve_wikilink_first_existing",
    "lint_wiki_orphans",
    "lint_concept_slug_refs",
]

# Orphan lint: skip nav stubs (often only linked outside the wiki graph / Obsidian).
_ORPHAN_EXCLUDE_EXACT = frozenset(
    {
        "wiki/_index/INDEX.md",
        "wiki/_index/TOPICS.md",
        "wiki/_index/RECENT.md",
        "wiki/_index/BACKLINKS.md",
        "wiki/_index/BODYGRAPH.md",
    }
)


@dataclass(frozen=True)
class LintIssue:
    """One broken reference."""

    file: str
    line: int
    kind: str
    target: str
    message: str


@dataclass(frozen=True)
class WikiOutgoingEdge:
    """One resolved wiki-to-wiki link from prose (fenced code skipped)."""

    line: int
    kind: str  # "md_link" | "wikilink"
    target_rel: str  # vault-relative posix path under wiki/


# [text](path)  — path not starting with http(s): mailto: # anchor-only
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
_WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _wikilink_inner_to_target(raw: str) -> str:
    """Obsidian-style inner: ``Page|alias`` or ``path#heading`` -> file stem/path."""
    part = raw.split("|", 1)[0].strip()
    return part.split("#", 1)[0].strip()


def iter_wiki_outgoing_edges(path: Path, ctx: VaultContext) -> list[WikiOutgoingEdge]:
    """Collect resolved wiki ``.md`` targets from prose (skips fenced code)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out: list[WikiOutgoingEdge] = []
    in_fence = False
    for i, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in _MD_LINK_RE.finditer(line):
            href = m.group(1).strip()
            resolved = _resolve_link_target(path, href, ctx)
            if resolved and resolved.exists() and resolved.suffix.lower() == ".md":
                try:
                    ctx.validate_under_vault(resolved)
                except VaultPathError:
                    continue
                rel = resolved.relative_to(ctx.root).as_posix()
                if rel.startswith("wiki/"):
                    out.append(
                        WikiOutgoingEdge(line=i, kind="md_link", target_rel=rel)
                    )
        for m in _WIKI_LINK_RE.finditer(line):
            if m.start() > 0 and line[m.start() - 1] == "!":
                continue
            inner = m.group(1)
            p = resolve_wikilink_first_existing(ctx, inner)
            if p and p.suffix.lower() == ".md":
                try:
                    rel = p.relative_to(ctx.root).as_posix()
                except ValueError:
                    continue
                if rel.startswith("wiki/"):
                    out.append(
                        WikiOutgoingEdge(line=i, kind="wikilink", target_rel=rel)
                    )
    return out


def _iter_wiki_outgoing_links(path: Path, ctx: VaultContext) -> set[str]:
    """Wiki `.md` targets linked from `path` (prose only; skips fenced code)."""
    return {e.target_rel for e in iter_wiki_outgoing_edges(path, ctx)}


def lint_wiki_orphans(
    ctx: VaultContext,
    *,
    include_ephemeral: bool = False,
    exclude_index_stubs: bool = True,
    exclude_outputs: bool = True,
) -> list[LintIssue]:
    """Wiki pages with no inbound links from other pages (deterministic graph).

    Md links + wikilinks in prose (skips fenced code). Self-link ≠ inbound.
    """
    wiki = ctx.wiki_dir()
    if not wiki.is_dir():
        return []

    wiki_files: list[str] = []
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
        rel = path.relative_to(ctx.root).as_posix()
        if exclude_outputs and rel.startswith("wiki/outputs/"):
            continue
        if exclude_index_stubs and rel in _ORPHAN_EXCLUDE_EXACT:
            continue
        wiki_files.append(rel)

    wiki_set = set(wiki_files)
    inbound: dict[str, set[str]] = {}

    for src in wiki_files:
        src_path = ctx.root / src
        for tgt in _iter_wiki_outgoing_links(src_path, ctx):
            if tgt not in wiki_set or tgt == src:
                continue
            inbound.setdefault(tgt, set()).add(src)

    issues: list[LintIssue] = []
    for rel in sorted(wiki_files):
        if rel not in inbound:
            issues.append(
                LintIssue(
                    file=rel,
                    line=1,
                    kind="orphan_page",
                    target="",
                    message="wiki page has no inbound links from other wiki pages",
                )
            )
    return issues


def resolve_wikilink_first_existing(ctx: VaultContext, inner: str) -> Path | None:
    """Return the first vault path that exists for an Obsidian ``[[inner]]`` link."""
    target = _wikilink_inner_to_target(inner)
    for p in _wikilink_candidate_paths(target, ctx):
        if p.exists():
            return p
    return None


def _wikilink_candidate_paths(target: str, ctx: VaultContext) -> list[Path]:
    """Possible vault paths for a wikilink target (existence checked by caller)."""
    t = target.strip()
    if not t:
        return []
    lower = t.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return []
    root = ctx.root
    out: list[Path] = []
    if "/" in t:
        try:
            p = ctx.validate_under_vault(root / t)
            out.append(p)
        except VaultPathError:
            pass
        return out
    stem = t[:-3] if t.endswith(".md") else t
    slug = stem.replace(" ", "-")
    names = (stem + ".md", slug + ".md") if stem != slug else (stem + ".md",)
    for sub in ("wiki", "wiki/concepts", "wiki/notes", "wiki/_index"):
        base = root / sub
        for name in names:
            try:
                out.append(ctx.validate_under_vault(base / name))
            except VaultPathError:
                continue
    return out


def _duplicate_heading_issues(rel_posix: str, lines: list[str]) -> list[LintIssue]:
    """Report duplicate ATX headings in one file (fenced code blocks skipped)."""
    in_fence = False
    seen: dict[str, int] = {}
    issues: list[LintIssue] = []
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _ATX_HEADING_RE.match(line.rstrip())
        if not m:
            continue
        raw_text = m.group(2).strip()
        norm = " ".join(raw_text.split())
        if not norm:
            continue
        if norm in seen:
            first = seen[norm]
            issues.append(
                LintIssue(
                    file=rel_posix,
                    line=i,
                    kind="duplicate_heading",
                    target=norm,
                    message=(
                        f"Duplicate heading {norm!r} "
                        f"(first ATX heading with same text at line {first})"
                    ),
                )
            )
        else:
            seen[norm] = i
    return issues


def _lint_one_markdown_file(
    path: Path,
    ctx: VaultContext,
    *,
    include_wikilinks: bool,
    include_duplicate_headings: bool,
) -> list[LintIssue]:
    """Check one ``.md``: links, images, optional wikilinks, duplicate headings."""
    issues: list[LintIssue] = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rel = path.relative_to(ctx.root).as_posix()
    for i, line in enumerate(lines, start=1):
        for m in _MD_LINK_RE.finditer(line):
            href = m.group(1).strip()
            resolved = _resolve_link_target(path, href, ctx)
            if resolved is None:
                continue
            if not resolved.exists():
                is_image = m.start() > 0 and line[m.start() - 1] == "!"
                kind = "broken_image" if is_image else "broken_link"
                label = "image" if is_image else "link"
                issues.append(
                    LintIssue(
                        file=rel,
                        line=i,
                        kind=kind,
                        target=href,
                        message=f"Missing {label} target: {href}",
                    )
                )
        if include_wikilinks:
            for m in _WIKI_LINK_RE.finditer(line):
                if m.start() > 0 and line[m.start() - 1] == "!":
                    continue
                inner = m.group(1)
                target = _wikilink_inner_to_target(inner)
                candidates = _wikilink_candidate_paths(target, ctx)
                if not candidates:
                    continue
                if any(p.exists() for p in candidates):
                    continue
                shown = ", ".join(
                    p.relative_to(ctx.root).as_posix() for p in candidates[:4]
                )
                issues.append(
                    LintIssue(
                        file=rel,
                        line=i,
                        kind="broken_wikilink",
                        target=inner,
                        message=f"Wikilink has no file (try e.g. {shown})",
                    )
                )
    if include_duplicate_headings:
        issues.extend(_duplicate_heading_issues(rel, lines))
    return issues


def _resolve_link_target(md_file: Path, href: str, ctx: VaultContext) -> Path | None:
    """Return resolved target path under vault if local file link; else None (skip)."""
    href = href.strip()
    if not href or href.startswith("#"):
        return None
    lower = href.split("?", 1)[0].split("#", 1)[0].lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return None
    if lower.startswith("mailto:"):
        return None
    target = (md_file.parent / href).resolve()
    try:
        return ctx.validate_under_vault(target)
    except VaultPathError:
        return None


def lint_concept_slug_refs(ctx: VaultContext) -> list[LintIssue]:
    """Flag slug refs in wiki_index graph fields when the target concept is missing."""
    idx_path = ctx.meta_dir() / "wiki_index.json"
    if not idx_path.is_file():
        return []
    try:
        raw = idx_path.read_text(encoding="utf-8")
        data = json.loads(raw) if raw.strip() else {}
    except (OSError, json.JSONDecodeError):
        return []
    concepts = data.get("concepts")
    if not isinstance(concepts, list):
        return []
    slug_set: set[str] = set()
    for c in concepts:
        if isinstance(c, dict) and isinstance(c.get("slug"), str):
            slug_set.add(c["slug"])
    cdir = ctx.wiki_dir() / "concepts"
    if cdir.is_dir():
        for p in cdir.glob("*.md"):
            if p.is_file():
                slug_set.add(p.stem)
    issues: list[LintIssue] = []
    fields = ("related_slugs", "conflicts_with_slugs", "supersedes_slugs")
    for c in concepts:
        if not isinstance(c, dict):
            continue
        src_rel = str(c.get("path", "")).strip() or "meta/wiki_index.json"
        for field in fields:
            for target in c.get(field) or []:
                if not isinstance(target, str) or not target:
                    continue
                if target not in slug_set:
                    issues.append(
                        LintIssue(
                            file=src_rel,
                            line=1,
                            kind="bad_slug_ref",
                            target=f"{field}:{target}",
                            message=(
                                f"slug reference {target!r} in {field} "
                                "has no matching concept page"
                            ),
                        )
                    )
    return issues


def lint_markdown_links(
    ctx: VaultContext,
    *,
    include_ephemeral: bool = False,
    include_wikilinks: bool = False,
    include_duplicate_headings: bool = True,
    include_raw: bool = False,
    include_orphans: bool = False,
    include_strict_concepts: bool = False,
) -> list[LintIssue]:
    """Scan ``wiki/**/*.md`` and optionally ``raw/**/*.md`` for broken refs."""
    issues: list[LintIssue] = []
    wiki = ctx.wiki_dir()
    if wiki.is_dir():
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
            issues.extend(
                _lint_one_markdown_file(
                    path,
                    ctx,
                    include_wikilinks=include_wikilinks,
                    include_duplicate_headings=include_duplicate_headings,
                )
            )
    if include_raw:
        raw = ctx.raw_dir()
        if raw.is_dir():
            for path in sorted(raw.rglob("*.md")):
                if not path.is_file():
                    continue
                try:
                    ctx.validate_under_vault(path)
                except VaultPathError:
                    continue
                issues.extend(
                    _lint_one_markdown_file(
                        path,
                        ctx,
                        include_wikilinks=include_wikilinks,
                        include_duplicate_headings=include_duplicate_headings,
                    )
                )
    if include_orphans:
        issues.extend(
            lint_wiki_orphans(
                ctx,
                include_ephemeral=include_ephemeral,
                exclude_index_stubs=True,
                exclude_outputs=True,
            )
        )
    if include_strict_concepts:
        issues.extend(lint_concept_slug_refs(ctx))
    return issues
