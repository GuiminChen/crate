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
