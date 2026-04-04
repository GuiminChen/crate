"""Tests for Q&A agent (mocked LLM)."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from crate.init_vault import init_vault
from crate.qa_agent import run_qa
from crate.vault_paths import VaultContext


def test_run_qa_tool_write_roundtrip(tmp_path: Path) -> None:
    """Two-step mock: model calls vault_write_output then stops."""
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "wiki" / "_index" / "TOPICS.md").write_text("# T\n", encoding="utf-8")

    calls: list[int] = [0]

    def fake_create(**kwargs: object) -> MagicMock:
        calls[0] += 1
        resp = MagicMock()
        msg = MagicMock()
        if calls[0] == 1:
            tc = MagicMock()
            tc.id = "c1"
            tc.function.name = "vault_write_output"
            tc.function.arguments = json.dumps(
                {
                    "path": "wiki/outputs/qa-test.md",
                    "content": "## Answer\n\nok",
                }
            )
            msg.content = ""
            msg.tool_calls = [tc]
        else:
            msg.content = "done"
            msg.tool_calls = []
        resp.choices = [MagicMock(message=msg)]
        return resp

    client = MagicMock()
    client.chat.completions.create = fake_create

    def factory() -> tuple[MagicMock, str]:
        return client, "fake-model"

    out = run_qa(ctx, "hello?", client_factory=factory, feedback=False)
    assert out.name == "qa-test.md"
    assert "Answer" in out.read_text(encoding="utf-8")


def test_run_qa_fallback_without_write(tmp_path: Path) -> None:
    """If model never calls write, fallback file is created."""
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)

    def fake_create(**kwargs: object) -> MagicMock:
        resp = MagicMock()
        msg = MagicMock()
        msg.content = "only text"
        msg.tool_calls = []
        resp.choices = [MagicMock(message=msg)]
        return resp

    client = MagicMock()
    client.chat.completions.create = fake_create

    out = run_qa(
        ctx,
        "q?",
        client_factory=lambda: (client, "m"),
        feedback=False,
    )
    assert "qa-fallback" in out.name or out.name.endswith(".md")
    assert out.read_text(encoding="utf-8")
