"""Tests for ``init_vault`` scaffolding."""

from pathlib import Path

from crate.init_vault import init_vault
from crate.vault_paths import VaultContext


def test_init_creates_expected_tree(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    created = init_vault(ctx)
    assert (tmp_path / "raw" / "papers").is_dir()
    assert (tmp_path / "wiki" / "_index" / "TOPICS.md").is_file()
    assert (tmp_path / "meta" / "compile_state.json").is_file()
    assert len(created) > 0


def test_init_idempotent_without_force(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    first_top = (tmp_path / "wiki" / "_index" / "TOPICS.md").read_text(encoding="utf-8")
    init_vault(ctx)
    second_top = (tmp_path / "wiki" / "_index" / "TOPICS.md").read_text(
        encoding="utf-8"
    )
    assert first_top == second_top
