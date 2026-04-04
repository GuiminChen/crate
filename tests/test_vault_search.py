"""Tests for shared vault markdown search."""

from pathlib import Path

from crate.init_vault import init_vault
from crate.vault_paths import VaultContext
from crate.vault_search import search_markdown_hits


def test_search_markdown_hits_empty_query(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    assert search_markdown_hits(ctx, "   ") == []


def test_search_markdown_hits_finds_substring(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    p = tmp_path / "wiki" / "notes" / "a.md"
    p.write_text("line one\nuniqueXYZ token\n", encoding="utf-8")
    hits = search_markdown_hits(ctx, "uniqueXYZ", max_hits=10)
    assert len(hits) == 1
    assert hits[0]["path"] == "wiki/notes/a.md"
    assert hits[0]["line"] == 2
    assert "uniqueXYZ" in hits[0]["snippet"]
