"""Tests for compile POC (mocked LLM)."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from crate.compile_run import (
    CompileResult,
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

    result = run_compile(ctx, client_factory=factory)
    assert isinstance(result, CompileResult)
    assert not result.skipped
    assert result.output_path is not None
    assert result.output_path.is_file()
    text = result.output_path.read_text(encoding="utf-8")
    assert "compile_run" in text
    assert "Synth" in text
    client.chat.completions.create.assert_called_once()


def test_run_compile_incremental_skips_second_run(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    note = tmp_path / "raw" / "papers" / "x.md"
    note.write_text("# X\n", encoding="utf-8")

    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="## Once"))]
    )

    def factory() -> tuple[MagicMock, str]:
        return client, "fake-model"

    r1 = run_compile(ctx, client_factory=factory)
    assert not r1.skipped
    assert r1.output_path is not None
    client.chat.completions.create.assert_called_once()

    r2 = run_compile(ctx, client_factory=factory)
    assert r2.skipped
    assert r2.output_path is None
    client.chat.completions.create.assert_called_once()


def test_run_compile_only_paths_bypasses_incremental_skip(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    a = tmp_path / "raw" / "a.md"
    b = tmp_path / "raw" / "b.md"
    a.write_text("# A\n", encoding="utf-8")
    b.write_text("# B\n", encoding="utf-8")

    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="## Body"))]
    )

    def factory() -> tuple[MagicMock, str]:
        return client, "fake-model"

    run_compile(ctx, client_factory=factory)
    assert client.chat.completions.create.call_count == 1
    run_compile(ctx, client_factory=factory)
    assert client.chat.completions.create.call_count == 1
    run_compile(ctx, only_paths=[a], client_factory=factory)
    assert client.chat.completions.create.call_count == 2


def test_run_compile_full_after_skip_calls_again(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "raw" / "papers" / "x.md").write_text("# X\n", encoding="utf-8")

    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="## Body"))]
    )

    def factory() -> tuple[MagicMock, str]:
        return client, "fake-model"

    run_compile(ctx, client_factory=factory)
    assert client.chat.completions.create.call_count == 1

    run_compile(ctx, client_factory=factory)
    assert client.chat.completions.create.call_count == 1

    run_compile(ctx, full=True, client_factory=factory)
    assert client.chat.completions.create.call_count == 2


def test_legacy_v1_compile_state_upgrades_to_v2(tmp_path: Path) -> None:
    """Old mtime/size fingerprints are ignored until a successful v2 save."""
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    note = tmp_path / "raw" / "papers" / "x.md"
    note.write_text("# X\n", encoding="utf-8")
    legacy = {
        "version": 1,
        "raw_fingerprints": {
            "raw/papers/x.md": {"mtime_ns": 0, "size": 999},
        },
    }
    (tmp_path / "meta" / "compile_state.json").write_text(
        json.dumps(legacy),
        encoding="utf-8",
    )

    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="## Upgraded"))]
    )

    def factory() -> tuple[MagicMock, str]:
        return client, "fake-model"

    run_compile(ctx, client_factory=factory)
    assert client.chat.completions.create.call_count == 1

    data = json.loads((tmp_path / "meta" / "compile_state.json").read_text())
    assert data["version"] == 2
    assert "sha256" in data["raw_fingerprints"]["raw/papers/x.md"]

    run_compile(ctx, client_factory=factory)
    assert client.chat.completions.create.call_count == 1


def test_run_compile_incremental_on_edit(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    note = tmp_path / "raw" / "papers" / "x.md"
    note.write_text("# X\n", encoding="utf-8")

    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="## A"))]
    )

    def factory() -> tuple[MagicMock, str]:
        return client, "fake-model"

    run_compile(ctx, client_factory=factory)
    assert client.chat.completions.create.call_count == 1

    note.write_text("# X\nmore\n", encoding="utf-8")
    run_compile(ctx, client_factory=factory)
    assert client.chat.completions.create.call_count == 2


def test_load_deepseek_config_requires_key(monkeypatch: "pytest.MonkeyPatch") -> None:
    for name in (
        "CRATE_LLM_PROVIDER",
        "CRATE_DEEPSEEK_API_KEY",
        "DEEPSEEK_API_KEY",
        "CRATE_CHAT_API_KEY",
        "OPENAI_API_KEY",
        "CRATE_OPENAI_API_KEY",
        "CRATE_DASHSCOPE_API_KEY",
        "DASHSCOPE_API_KEY",
        "CRATE_ARK_API_KEY",
        "ARK_API_KEY",
        "CRATE_HUNYUAN_API_KEY",
        "HUNYUAN_API_KEY",
        "CRATE_OPENROUTER_API_KEY",
        "OPENROUTER_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "CRATE_AZURE_OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="No chat API key"):
        load_deepseek_config()


def test_load_deepseek_config_openai_auto(monkeypatch: "pytest.MonkeyPatch") -> None:
    for name in (
        "CRATE_DEEPSEEK_API_KEY",
        "DEEPSEEK_API_KEY",
        "CRATE_LLM_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
    cfg = load_deepseek_config()
    assert "api.openai.com" in cfg.base_url
    assert cfg.model


def test_load_deepseek_config_unknown_provider(
    monkeypatch: "pytest.MonkeyPatch",
) -> None:
    monkeypatch.setenv("CRATE_LLM_PROVIDER", "not-a-real-provider")
    monkeypatch.setenv("CRATE_DEEPSEEK_API_KEY", "x")
    with pytest.raises(ValueError, match="Unknown CRATE_LLM_PROVIDER"):
        load_deepseek_config()
