"""Tests for vault statistics and gates."""

from pathlib import Path

import pytest

from crate.init_vault import init_vault
from crate.vault_paths import VaultContext
from crate.vault_stats import (
    GateConfig,
    collect_vault_stats,
    evaluate_gates,
    gate_message,
)


def test_collect_vault_stats_counts_md(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    w = tmp_path / "wiki" / "notes" / "a.md"
    w.write_text("one two three\n", encoding="utf-8")
    (tmp_path / "raw" / "papers" / "b.md").write_text("four five\n", encoding="utf-8")
    s = collect_vault_stats(ctx)
    assert s.wiki_md_files >= 1
    assert s.wiki_word_count >= 3
    assert s.raw_md_files >= 1
    assert s.raw_word_count >= 2


def test_gate_evaluate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRATE_GATE_WIKI_WORDS", "10")
    cfg = GateConfig.from_environ()
    from crate.vault_stats import VaultStats

    s = VaultStats(
        wiki_word_count=100,
        wiki_md_files=1,
        raw_word_count=0,
        raw_md_files=0,
        wiki_pdf_files=0,
        raw_pdf_files=0,
    )
    reasons = evaluate_gates(s, cfg)
    assert reasons


def test_gate_message_empty() -> None:
    assert gate_message([]) == ""
