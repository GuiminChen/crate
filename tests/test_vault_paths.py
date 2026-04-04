"""Tests for vault path resolution and containment checks."""

from pathlib import Path

import pytest

from crate.vault_paths import VaultContext, VaultPathError, resolve_vault_root


def test_resolve_vault_root_default_cwd(tmp_path: Path) -> None:
    """Without vault_arg, base is cwd."""
    expected = (tmp_path / "inside").resolve()
    expected.mkdir()
    got = resolve_vault_root(expected, None)
    assert got == expected


def test_resolve_vault_relative_to_cwd(tmp_path: Path) -> None:
    sub = tmp_path / "vault"
    sub.mkdir()
    got = resolve_vault_root(tmp_path, "vault")
    assert got == sub.resolve()


def test_validate_under_vault_relative(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    inner = tmp_path / "wiki" / "a.md"
    inner.parent.mkdir(parents=True)
    inner.write_text("x", encoding="utf-8")
    assert ctx.validate_under_vault(Path("wiki/a.md")) == inner.resolve()


def test_validate_rejects_escape(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    outside = tmp_path.parent / "evil.md"
    with pytest.raises(VaultPathError):
        ctx.validate_under_vault(outside)
