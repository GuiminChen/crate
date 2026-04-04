"""Vault size statistics and scale gate thresholds."""

from __future__ import annotations

import os
from dataclasses import dataclass

from crate.vault_paths import VaultContext, VaultPathError

__all__ = [
    "VaultStats",
    "GateConfig",
    "collect_vault_stats",
    "evaluate_gates",
    "gate_message",
]


def _word_count(text: str) -> int:
    return len(text.split())


@dataclass(frozen=True)
class GateConfig:
    """Thresholds from environment (with documented defaults)."""

    max_wiki_words: int
    max_wiki_files: int
    max_raw_words: int
    max_raw_files: int

    @classmethod
    def from_environ(cls) -> "GateConfig":
        """Construct from ``CRATE_GATE_*`` environment variables."""
        return cls(
            max_wiki_words=int(os.environ.get("CRATE_GATE_WIKI_WORDS", "400000")),
            max_wiki_files=int(os.environ.get("CRATE_GATE_WIKI_FILES", "500")),
            max_raw_words=int(os.environ.get("CRATE_GATE_RAW_WORDS", "800000")),
            max_raw_files=int(os.environ.get("CRATE_GATE_RAW_FILES", "1000")),
        )


@dataclass(frozen=True)
class VaultStats:
    """Aggregated counts for ``wiki/`` and ``raw/``."""

    wiki_word_count: int
    wiki_md_files: int
    raw_word_count: int
    raw_md_files: int
    wiki_pdf_files: int
    raw_pdf_files: int


def collect_vault_stats(
    ctx: VaultContext,
    *,
    include_outputs: bool = True,
    include_ephemeral: bool = False,
) -> VaultStats:
    """Sum words (whitespace-split) and file counts for markdown under wiki and raw."""
    wiki_words = 0
    wiki_md = 0
    wiki_pdf = 0
    raw_words = 0
    raw_md = 0
    raw_pdf = 0

    wiki = ctx.wiki_dir()
    if wiki.is_dir():
        for p in sorted(wiki.rglob("*")):
            if not p.is_file():
                continue
            try:
                ctx.validate_under_vault(p)
            except VaultPathError:
                continue
            rel = p.relative_to(ctx.root).parts
            if not include_outputs and len(rel) >= 2 and rel[1] == "outputs":
                continue
            if not include_ephemeral and "_ephemeral" in rel:
                continue
            suf = p.suffix.lower()
            if suf == ".md":
                wiki_md += 1
                try:
                    wiki_words += _word_count(
                        p.read_text(encoding="utf-8", errors="replace")
                    )
                except OSError:
                    pass
            elif suf == ".pdf":
                wiki_pdf += 1

    raw = ctx.raw_dir()
    if raw.is_dir():
        for p in sorted(raw.rglob("*")):
            if not p.is_file():
                continue
            try:
                ctx.validate_under_vault(p)
            except VaultPathError:
                continue
            suf = p.suffix.lower()
            if suf == ".md":
                raw_md += 1
                try:
                    raw_words += _word_count(
                        p.read_text(encoding="utf-8", errors="replace")
                    )
                except OSError:
                    pass
            elif suf == ".pdf":
                raw_pdf += 1

    return VaultStats(
        wiki_word_count=wiki_words,
        wiki_md_files=wiki_md,
        raw_word_count=raw_words,
        raw_md_files=raw_md,
        wiki_pdf_files=wiki_pdf,
        raw_pdf_files=raw_pdf,
    )


def evaluate_gates(stats: VaultStats, cfg: GateConfig) -> list[str]:
    """Return human-readable reasons when any threshold is exceeded."""
    reasons: list[str] = []
    if stats.wiki_word_count > cfg.max_wiki_words:
        reasons.append(
            f"wiki word count {stats.wiki_word_count} > {cfg.max_wiki_words} "
            "(CRATE_GATE_WIKI_WORDS)"
        )
    if stats.wiki_md_files > cfg.max_wiki_files:
        reasons.append(
            f"wiki .md files {stats.wiki_md_files} > {cfg.max_wiki_files} "
            "(CRATE_GATE_WIKI_FILES)"
        )
    if stats.raw_word_count > cfg.max_raw_words:
        reasons.append(
            f"raw word count {stats.raw_word_count} > {cfg.max_raw_words} "
            "(CRATE_GATE_RAW_WORDS)"
        )
    if stats.raw_md_files > cfg.max_raw_files:
        reasons.append(
            f"raw .md files {stats.raw_md_files} > {cfg.max_raw_files} "
            "(CRATE_GATE_RAW_FILES)"
        )
    return reasons


def gate_message(reasons: list[str]) -> str:
    """Single stderr line for gate hints."""
    if not reasons:
        return ""
    return "CRATE scale gate: " + "; ".join(reasons) + ". Consider semantic search."
