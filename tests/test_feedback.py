"""Tests for RECENT.md feedback."""

from pathlib import Path

from crate.feedback import append_output_to_recent
from crate.init_vault import init_vault
from crate.vault_paths import VaultContext


def test_append_creates_and_appends(tmp_path: Path) -> None:
    """append_output_to_recent adds a bullet with link."""
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    append_output_to_recent(
        ctx,
        "wiki/outputs/q.md",
        question_preview="What is X?",
    )
    text = (tmp_path / "wiki" / "_index" / "RECENT.md").read_text(encoding="utf-8")
    assert "wiki/outputs/q.md" in text
    assert "What is X" in text
