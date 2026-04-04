"""Tests for ephemeral sessions."""

from pathlib import Path

import pytest

from crate.ephemeral import (
    finalize_ephemeral_session,
    init_ephemeral_session,
    validate_session_id,
)
from crate.init_vault import init_vault
from crate.vault_paths import VaultContext


def test_validate_session_id_rejects_traversal() -> None:
    with pytest.raises(ValueError):
        validate_session_id("../x")


def test_init_and_finalize_ephemeral(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    sid = init_ephemeral_session(ctx)
    assert sid
    d = tmp_path / "wiki" / "_ephemeral" / sid
    assert d.is_dir()
    (d / "note.md").write_text("# N\n", encoding="utf-8")
    out = finalize_ephemeral_session(ctx, sid, delete=False)
    assert out.name.startswith("FINAL_")
    assert "Source:" in out.read_text(encoding="utf-8")
