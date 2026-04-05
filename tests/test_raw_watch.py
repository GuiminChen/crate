"""Tests for raw/ watch (fingerprints)."""

from crate.init_vault import init_vault
from crate.raw_watch import snapshot_raw_fingerprints
from crate.vault_paths import VaultContext


def test_snapshot_raw_fingerprints_changes_with_content(tmp_path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    p = tmp_path / "raw" / "papers" / "a.md"
    p.write_text("one\n", encoding="utf-8")
    s1 = snapshot_raw_fingerprints(ctx)
    p.write_text("two\n", encoding="utf-8")
    s2 = snapshot_raw_fingerprints(ctx)
    assert s1 != s2
    assert "raw/papers/a.md" in s1
