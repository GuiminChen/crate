"""Tests for compile POC (mocked LLM)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from crate.compile_run import (
    build_compile_prompt,
    collect_raw_markdown,
    collect_raw_sources,
    run_compile,
)
from crate.init_vault import init_vault
from crate.llm import load_deepseek_config
from crate.vault_paths import VaultContext


def test_collect_raw_empty_without_raw(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    assert collect_raw_markdown(ctx) == []


def test_collect_raw_finds_markdown(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    note = tmp_path / "raw" / "papers" / "a.md"
    note.write_text("# Hello", encoding="utf-8")
    paths = collect_raw_markdown(ctx)
    assert len(paths) == 1
    assert paths[0].name == "a.md"


def test_collect_raw_sources_includes_pdf(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "raw" / "papers" / "a.pdf").write_bytes(b"%PDF-1.4\n")
    (tmp_path / "raw" / "papers" / "b.md").write_text("# B", encoding="utf-8")
    paths = collect_raw_sources(ctx)
    assert {p.name for p in paths} == {"a.pdf", "b.md"}


def test_build_compile_prompt_includes_pdf_extract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "raw" / "papers" / "paper.pdf").write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(
        "crate.compile_run.extract_pdf_text",
        lambda _p: "Abstract: hello from PDF.",
    )
    paths = collect_raw_sources(ctx)
    msg = build_compile_prompt(ctx, paths)
    assert "raw/papers/paper.pdf" in msg
    assert "extracted from PDF" in msg
    assert "hello from PDF" in msg


def test_build_compile_prompt_includes_relative_paths(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    note = tmp_path / "raw" / "papers" / "a.md"
    note.write_text("# Title\nbody", encoding="utf-8")
    paths = collect_raw_markdown(ctx)
    msg = build_compile_prompt(ctx, paths)
    assert "raw/papers/a.md" in msg
    assert "Title" in msg


def test_run_compile_writes_wiki_note(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "raw" / "papers" / "x.md").write_text("# X\n", encoding="utf-8")

    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="## Synth\nok"))]
    )

    def factory() -> tuple[MagicMock, str]:
        return client, "fake-model"

    out = run_compile(ctx, client_factory=factory)
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "compile_run" in text
    assert "Synth" in text
    client.chat.completions.create.assert_called_once()


def test_load_deepseek_config_requires_key(monkeypatch: "pytest.MonkeyPatch") -> None:
    monkeypatch.delenv("CRATE_DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(ValueError, match="CRATE_DEEPSEEK_API_KEY"):
        load_deepseek_config()
