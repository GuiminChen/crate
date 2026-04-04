"""Tests for vault_tools."""

from pathlib import Path

from crate.init_vault import init_vault
from crate.vault_paths import VaultContext
from crate.vault_tools import VaultTools


def test_vault_read_under_raw(tmp_path: Path) -> None:
    """vault_read returns file contents for paths under raw/."""
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    p = tmp_path / "raw" / "papers" / "x.md"
    p.write_text("hello", encoding="utf-8")
    vt = VaultTools(ctx)
    assert "hello" in vt.vault_read("raw/papers/x.md")


def test_vault_read_rejects_escape(tmp_path: Path) -> None:
    """Paths outside vault return an error string."""
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    vt = VaultTools(ctx)
    out = vt.vault_read("../../etc/passwd")
    assert "Error" in out


def test_vault_write_output_only_outputs(tmp_path: Path) -> None:
    """Writes are limited to wiki/outputs/."""
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    vt = VaultTools(ctx)
    assert "Error" in vt.vault_write_output("wiki/notes/bad.md", "x")


def test_vault_search_semantic_no_index(tmp_path: Path) -> None:
    """vault_search_semantic returns error when index is missing."""
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    vt = VaultTools(ctx)
    out = vt.vault_search_semantic("anything")
    assert "Error" in out


def test_vault_write_ephemeral_session(tmp_path: Path) -> None:
    """With session_id, writes under wiki/_ephemeral/<id>/ are allowed."""
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    sid = "test-sess-1"
    d = tmp_path / "wiki" / "_ephemeral" / sid
    d.mkdir(parents=True)
    vt = VaultTools(ctx, session_id=sid)
    rel = f"wiki/_ephemeral/{sid}/draft.md"
    res = vt.vault_write_output(rel, "# Draft\n")
    assert "Wrote" in res


def test_vault_search_finds_line(tmp_path: Path) -> None:
    """vault_search returns JSON hits."""
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "wiki" / "notes" / "n.md").write_text(
        "alpha uniquetoken beta", encoding="utf-8"
    )
    vt = VaultTools(ctx)
    raw = vt.vault_search("uniquetoken")
    assert "uniquetoken" in raw
    assert "wiki/notes/n.md" in raw
