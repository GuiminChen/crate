"""crate doctor command."""

import json

import pytest

from crate.cli import main
from crate.doctor import vault_doctor_report, vault_standard_dirs_ok
from crate.init_vault import init_vault
from crate.vault_paths import VaultContext


def test_vault_doctor_report_after_init(tmp_path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    r = vault_doctor_report(ctx)
    assert "crate_version" in r
    assert r["vault"] == str(tmp_path.resolve())
    assert r["dirs"] == {"raw": True, "wiki": True, "meta": True}
    assert r["compile_state_present"] is True
    assert r["compile_wiki_last_present"] is False
    assert r["semantic_wiki_report_present"] is False
    assert r["embeddings_sqlite_present"] is False
    assert r["ok"] is True


def test_cli_doctor_json(capsys: pytest.CaptureFixture[str], tmp_path) -> None:
    init_vault(VaultContext(root=tmp_path))
    rc = main(["--vault", str(tmp_path), "doctor", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert data["dirs"]["wiki"] is True
    assert "crate_version" in data
    assert "semantic_ready" in data
    assert vault_standard_dirs_ok(data) is True


def test_doctor_strict_fails_without_standard_dirs(tmp_path) -> None:
    empty = tmp_path / "bare"
    empty.mkdir()
    assert main(["--vault", str(empty), "doctor", "--strict"]) == 1


def test_doctor_strict_ok_after_init(tmp_path) -> None:
    init_vault(VaultContext(root=tmp_path))
    assert main(["--vault", str(tmp_path), "doctor", "--strict"]) == 0
