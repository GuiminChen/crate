"""Tests for wiki-check whitelist apply."""

from pathlib import Path

from crate.init_vault import init_vault
from crate.vault_paths import VaultContext
from crate.wiki_check_apply import apply_wiki_check_fixes


def test_apply_merge_related_slugs_dry_run(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    p = tmp_path / "wiki" / "concepts" / "a.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ntitle: A\nkind: concept\nrelated_slugs:\n  - b\n---\n\nbody\n",
        encoding="utf-8",
    )
    fixes = [
        {
            "action": "merge_related_slugs",
            "path": "wiki/concepts/a.md",
            "slugs": ["new-slug"],
        }
    ]
    r = apply_wiki_check_fixes(ctx, fixes, dry_run=True)
    assert len(r) == 1
    assert r[0].get("ok") is True
    assert r[0].get("dry_run") is True
    text = p.read_text(encoding="utf-8")
    assert "new-slug" not in text


def test_apply_merge_related_slugs_writes(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    p = tmp_path / "wiki" / "concepts" / "a.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "---\ntitle: A\nkind: concept\nrelated_slugs:\n  - b\n---\n\nbody\n",
        encoding="utf-8",
    )
    fixes = [
        {
            "action": "merge_related_slugs",
            "path": "wiki/concepts/a.md",
            "slugs": ["new-slug"],
        }
    ]
    r = apply_wiki_check_fixes(ctx, fixes, dry_run=False)
    assert r[0].get("ok") is True
    text = p.read_text(encoding="utf-8")
    assert "new-slug" in text


def test_apply_rejects_bad_path(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    fixes = [
        {
            "action": "merge_related_slugs",
            "path": "wiki/outputs/x.md",
            "slugs": ["a"],
        }
    ]
    r = apply_wiki_check_fixes(ctx, fixes, dry_run=False)
    assert r[0].get("ok") is False


def test_apply_rejects_unknown_action(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    r = apply_wiki_check_fixes(
        ctx,
        [{"action": "delete_all", "path": "wiki/concepts/a.md", "slugs": []}],
        dry_run=True,
    )
    assert r[0].get("ok") is False
