"""Deterministic wiki checks: local markdown links must resolve under the vault."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from crate.vault_paths import VaultContext, VaultPathError

__all__ = ["LintIssue", "lint_markdown_links"]


@dataclass(frozen=True)
class LintIssue:
    """One broken reference."""

    file: str
    line: int
    kind: str
    target: str
    message: str


# [text](path)  — path not starting with http(s): mailto: # anchor-only
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


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


def lint_markdown_links(ctx: VaultContext) -> list[LintIssue]:
    """Scan ``wiki/**/*.md`` and report missing relative link targets."""
    wiki = ctx.wiki_dir()
    issues: list[LintIssue] = []
    if not wiki.is_dir():
        return issues
    for path in sorted(wiki.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            ctx.validate_under_vault(path)
        except VaultPathError:
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines, start=1):
            for m in _MD_LINK_RE.finditer(line):
                href = m.group(1).strip()
                resolved = _resolve_link_target(path, href, ctx)
                if resolved is None:
                    continue
                if not resolved.exists():
                    issues.append(
                        LintIssue(
                            file=path.relative_to(ctx.root).as_posix(),
                            line=i,
                            kind="broken_link",
                            target=href,
                            message=f"Missing target: {href}",
                        )
                    )
    return issues
