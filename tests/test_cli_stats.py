"""CLI stats subcommand."""

import json

import pytest

from crate.cli import main
from crate.init_vault import init_vault
from crate.vault_paths import VaultContext


def test_stats_gates_json(capsys: pytest.CaptureFixture[str], tmp_path) -> None:
    """--gates-json prints only the gates object."""
    init_vault(VaultContext(root=tmp_path))
    rc = main(["--vault", str(tmp_path), "stats", "--gates-json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "triggered" in data
    assert "reasons" in data
    assert "thresholds" in data
    assert "readiness" not in data


def test_stats_json_includes_readiness(capsys: pytest.CaptureFixture[str], tmp_path) -> None:
    init_vault(VaultContext(root=tmp_path))
    rc = main(["--vault", str(tmp_path), "stats", "--json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    r = data["readiness"]
    assert r["vault"] == str(tmp_path.resolve())
    assert r["multi_page_wiki_index"] is False
    assert r["semantic_ready"] == (
        r["embedding_configured"] and r["semantic_index_ready"]
    )
