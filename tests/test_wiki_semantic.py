"""Tests for semantic wiki check (mocked LLM)."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from crate.init_vault import init_vault
from crate.vault_paths import VaultContext
from crate.wiki_semantic import run_semantic_wiki_check


def test_semantic_wiki_check_writes_report(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "meta").mkdir(parents=True, exist_ok=True)
    idx = {
        "version": 1,
        "raw_sources": ["raw/a.md"],
        "concepts": [{"slug": "x", "path": "wiki/concepts/x.md", "title": "X", "sources": []}],
    }
    (tmp_path / "meta" / "wiki_index.json").write_text(
        json.dumps(idx), encoding="utf-8"
    )
    (tmp_path / "wiki" / "concepts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "wiki" / "concepts" / "x.md").write_text(
        "---\ntitle: X\n---\nbody\n", encoding="utf-8"
    )

    report_json = {
        "version": 1,
        "summary": "ok",
        "issues": [],
        "orphan_raw": [],
    }
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps(report_json)))]
    )

    def factory() -> tuple[MagicMock, str]:
        return client, "m"

    env = run_semantic_wiki_check(ctx, client_factory=factory, write_report=True)
    assert "report" in env
    out = tmp_path / "meta" / "semantic_wiki_report.json"
    assert out.is_file()
