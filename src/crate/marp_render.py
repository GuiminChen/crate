"""Invoke local Marp CLI on markdown files (optional dependency)."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

from crate.vault_paths import VaultContext, VaultPathError

__all__ = ["find_marp_files", "run_marp", "ensure_figures_dir"]


def _has_marp_front_matter(text: str) -> bool:
    if not text.startswith("---"):
        return False
    end = text.find("\n---", 3)
    if end == -1:
        return False
    block = text[3:end]
    pat = r"^marp\s*:\s*true\s*$"
    return re.search(pat, block, re.MULTILINE | re.IGNORECASE) is not None


def ensure_figures_dir(ctx: VaultContext) -> Path:
    """Ensure ``wiki/outputs/figures/`` exists for generated plot scripts."""
    d = ctx.wiki_dir() / "outputs" / "figures"
    d.mkdir(parents=True, exist_ok=True)
    return d


def find_marp_files(ctx: VaultContext, root_sub: str = "wiki") -> list[Path]:
    """List ``*.md`` under ``wiki/`` whose body or front matter enables Marp."""
    base = ctx.root / root_sub
    if not base.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(base.rglob("*.md")):
        if not p.is_file():
            continue
        try:
            ctx.validate_under_vault(p)
        except VaultPathError:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if _has_marp_front_matter(text):
            out.append(p)
    return out


def run_marp(
    ctx: VaultContext,
    paths: list[Path] | None = None,
    *,
    to_pdf: bool = True,
    out_dir: Path | None = None,
) -> list[tuple[Path, str]]:
    """
    Run Marp on each path; return list of (source, stdout_or_error).

    Command from ``CRATE_MARP_CMD`` (default: ``npx --yes @marp-team/marp-cli``)
    plus file args. Uses subprocess; raises on missing command only when
    subprocess fails with ENOENT.
    """
    cmd_base = os.environ.get("CRATE_MARP_CMD", "").strip()
    if not cmd_base:
        cmd_base = "npx --yes @marp-team/marp-cli"
    parts = shlex.split(cmd_base)

    targets = paths or find_marp_files(ctx)
    if not targets:
        return []

    out_dir = out_dir or (ctx.wiki_dir() / "outputs" / "marp-pdf")
    if to_pdf:
        out_dir.mkdir(parents=True, exist_ok=True)

    results: list[tuple[Path, str]] = []
    for src in targets:
        src = ctx.validate_under_vault(src)
        args = list(parts) + [str(src)]
        if to_pdf:
            stem = src.stem + ".pdf"
            dest = out_dir / stem
            args.extend(["--pdf", "-o", str(dest)])
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
        except OSError as exc:
            results.append((src, f"os error: {exc}"))
            continue
        except subprocess.TimeoutExpired:
            results.append((src, "timeout after 600s"))
            continue
        msg = proc.stdout or ""
        if proc.stderr:
            msg += "\n" + proc.stderr
        if proc.returncode != 0:
            msg = f"exit {proc.returncode}\n{msg}"
        results.append((src, msg.strip() or "ok"))
    return results
