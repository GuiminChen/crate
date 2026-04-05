"""Tests for multi-agent Q&A orchestration."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from crate.init_vault import init_vault
from crate.multi_agent import run_multi_agent_qa
from crate.vault_paths import VaultContext


def test_multi_agent_planner_then_run_qa(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)

    out = ctx.wiki_dir() / "outputs" / "stub.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("---\ntitle: T\n---\n", encoding="utf-8")

    planner_client = MagicMock()
    planner_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(content='{"sub_questions": ["a"], "focus_paths": []}')
            )
        ]
    )

    def factory() -> tuple[MagicMock, str]:
        return planner_client, "fake"

    seen: dict[str, str] = {}

    def run_qa_capture(
        c: VaultContext, q: str, **kwargs: object
    ) -> Path:
        seen["q"] = q
        return out

    monkeypatch.setattr("crate.multi_agent.run_qa", run_qa_capture)

    result = run_multi_agent_qa(
        ctx,
        "What is X?",
        client_factory=factory,
        feedback=False,
    )
    assert result == out
    assert "What is X?" in seen["q"]
    assert "Planner" in seen["q"] or "sub_questions" in seen["q"]
