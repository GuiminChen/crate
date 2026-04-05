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


def test_lint_reports_missing_image_target(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    bad = tmp_path / "wiki" / "notes" / "img.md"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("![](assets/missing.png)", encoding="utf-8")
    issues = lint_markdown_links(ctx)
    assert len(issues) == 1
    assert issues[0].kind == "broken_image"
    assert "missing.png" in issues[0].target


def test_lint_skips_http_links(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    page = tmp_path / "wiki" / "notes" / "ext.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("[u](https://example.com/x)", encoding="utf-8")
    assert lint_markdown_links(ctx) == []


def test_lint_wikilink_missing_without_flag_ok(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    page = tmp_path / "wiki" / "notes" / "p.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("[[GhostPage]]", encoding="utf-8")
    assert lint_markdown_links(ctx) == []


def test_lint_wikilink_reports_when_enabled(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    page = tmp_path / "wiki" / "notes" / "p.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text("[[GhostPage]]", encoding="utf-8")
    issues = lint_markdown_links(ctx, include_wikilinks=True)
    assert len(issues) == 1
    assert issues[0].kind == "broken_wikilink"


def test_lint_wikilink_ok_when_file_exists(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "wiki" / "notes" / "target.md").write_text("x", encoding="utf-8")
    page = tmp_path / "wiki" / "notes" / "p.md"
    page.write_text("[[target]]", encoding="utf-8")
    assert lint_markdown_links(ctx, include_wikilinks=True) == []


def test_lint_reports_duplicate_atx_headings(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    page = tmp_path / "wiki" / "notes" / "dup.md"
    page.write_text(
        "# Same\n\nbody\n\n## Same\n\n```\n# Same\n```\n\n# Same\n",
        encoding="utf-8",
    )
    issues = lint_markdown_links(ctx)
    dups = [i for i in issues if i.kind == "duplicate_heading"]
    assert len(dups) == 2
    assert {i.line for i in dups} == {5, 11}


def test_lint_duplicate_headings_can_be_disabled(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    page = tmp_path / "wiki" / "notes" / "dup.md"
    page.write_text("# X\n\n# X\n", encoding="utf-8")
    assert lint_markdown_links(ctx, include_duplicate_headings=False) == []


def test_lint_orphans_disabled_by_default(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "wiki" / "concepts" / "only.md").write_text("solo\n", encoding="utf-8")
    assert lint_markdown_links(ctx) == []


def test_lint_orphans_reports_page_with_no_inbound(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "wiki" / "concepts" / "a.md").write_text("A\n", encoding="utf-8")
    (tmp_path / "wiki" / "concepts" / "b.md").write_text("B\n[[a]]\n", encoding="utf-8")
    issues = lint_markdown_links(ctx, include_wikilinks=True, include_orphans=True)
    orphans = [i for i in issues if i.kind == "orphan_page"]
    assert len(orphans) == 1
    assert orphans[0].file.replace("\\", "/").endswith("wiki/concepts/b.md")


def test_lint_orphans_resolved_when_linked(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "wiki" / "concepts" / "a.md").write_text("A\n[[b]]\n", encoding="utf-8")
    (tmp_path / "wiki" / "concepts" / "b.md").write_text("B\n[[a]]\n", encoding="utf-8")
    assert lint_markdown_links(ctx, include_wikilinks=True, include_orphans=True) == []


def test_lint_strict_concepts_bad_slug_ref(tmp_path: Path) -> None:
    import json

    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "meta").mkdir(parents=True, exist_ok=True)
    idx = {
        "version": 1,
        "concepts": [
            {
                "slug": "a",
                "path": "wiki/concepts/a.md",
                "title": "A",
                "related_slugs": ["missing-slug"],
            }
        ],
    }
    (tmp_path / "meta" / "wiki_index.json").write_text(
        json.dumps(idx), encoding="utf-8"
    )
    (tmp_path / "wiki" / "concepts" / "a.md").write_text("# A\n", encoding="utf-8")
    issues = lint_markdown_links(ctx, include_strict_concepts=True)
    kinds = [i.kind for i in issues]
    assert "bad_slug_ref" in kinds


def test_lint_raw_reports_broken_relative_link(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    r = tmp_path / "raw" / "papers" / "note.md"
    r.parent.mkdir(parents=True, exist_ok=True)
    r.write_text("See [bad](../assets/missing.md)", encoding="utf-8")
    assert lint_markdown_links(ctx) == []
    issues = lint_markdown_links(ctx, include_raw=True)
    assert len(issues) == 1
    assert issues[0].kind == "broken_link"
    assert "raw/papers/note.md" in issues[0].file.replace("\\", "/")
