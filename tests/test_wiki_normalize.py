"""Tests for wikilink ↔ markdown normalization."""

from pathlib import Path

import pytest

from crate.init_vault import init_vault
from crate.llm import truncate_prompt_for_purpose
from crate.vault_paths import VaultContext
from crate.wiki_normalize import normalize_wiki_markdown


def test_normalize_to_md_links(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    target = tmp_path / "wiki" / "concepts" / "alpha.md"
    target.write_text("---\ntitle: A\n---\n# A\n", encoding="utf-8")
    src = tmp_path / "wiki" / "notes" / "n.md"
    src.write_text("See [[alpha]] for more.\n", encoding="utf-8")

    n, changed = normalize_wiki_markdown(ctx, to_md_links=True)
    assert n == 1
    text = src.read_text(encoding="utf-8")
    assert "[[alpha]]" not in text
    assert "](" in text
    assert "concepts/alpha.md" in text.replace("\\", "/")


def test_truncate_prompt_for_compile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRATE_MAX_INPUT_CHARS_COMPILE", "10")
    out = truncate_prompt_for_purpose("hello world here", "compile")
    assert "truncated" in out.lower()
