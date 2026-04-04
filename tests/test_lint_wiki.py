"""Tests for wiki markdown link lint."""

from pathlib import Path

from crate.init_vault import init_vault
from crate.lint_wiki import lint_markdown_links
from crate.vault_paths import VaultContext


def test_lint_clean_when_no_broken_links(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    assert lint_markdown_links(ctx) == []


def test_lint_reports_missing_relative_target(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    bad = tmp_path / "wiki" / "notes" / "bad.md"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("See [x](missing.md)", encoding="utf-8")
    issues = lint_markdown_links(ctx)
    assert len(issues) == 1
    assert issues[0].kind == "broken_link"
    assert "missing.md" in issues[0].target


def test_lint_skips_http_links(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    page = tmp_path / "wiki" / "notes" / "ext.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("[u](https://example.com/x)", encoding="utf-8")
    assert lint_markdown_links(ctx) == []
