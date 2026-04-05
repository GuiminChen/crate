"""Tests for multi-page wiki compile (mocked LLM JSON)."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from crate.compile_run import run_compile
from crate.compile_wiki import (
    COMPILE_WIKI_LAST_FILENAME,
    WIKI_INDEX_FILENAME,
    extract_json_object,
    sanitize_slug,
)
from crate.init_vault import init_vault
from crate.vault_paths import VaultContext


def test_sanitize_slug() -> None:
    assert sanitize_slug("Foo Bar!") == "foo-bar"
    assert sanitize_slug("  ") == "concept"


def test_extract_json_object_fenced() -> None:
    text = '```json\n{"version": 1, "concepts": []}\n```'
    assert extract_json_object(text) == {"version": 1, "concepts": []}


def test_run_wiki_graph_writes_index_and_concepts(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "raw" / "papers" / "x.md").write_text("# X\n", encoding="utf-8")

    payload = {
        "version": 1,
        "concepts": [
            {
                "slug": "alpha-topic",
                "title": "Alpha",
                "body": "## Hi\n",
                "sources": ["raw/papers/x.md"],
            }
        ],
        "topics_markdown": "- Theme A",
        "synthesis_note": "## Overview\nok",
    }
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps(payload)))]
    )

    def factory() -> tuple[MagicMock, str]:
        return client, "fake-model"

    result = run_compile(ctx, wiki_graph=True, client_factory=factory)
    assert not result.skipped
    assert result.output_path is not None

    idx = tmp_path / "meta" / WIKI_INDEX_FILENAME
    assert idx.is_file()
    data = json.loads(idx.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert len(data["concepts"]) == 1
    assert data["concepts"][0]["slug"] == "alpha-topic"
    assert data.get("touched_slugs") == ["alpha-topic"]

    last = tmp_path / "meta" / COMPILE_WIKI_LAST_FILENAME
    assert last.is_file()
    last_data = json.loads(last.read_text(encoding="utf-8"))
    assert last_data["touched_slugs"] == ["alpha-topic"]

    concept = tmp_path / "wiki" / "concepts" / "alpha-topic.md"
    assert concept.is_file()
    assert "kind: concept" in concept.read_text(encoding="utf-8")

    topics = tmp_path / "wiki" / "_index" / "TOPICS.md"
    assert topics.is_file()
    assert "Theme A" in topics.read_text(encoding="utf-8")

    hub = tmp_path / "wiki" / "_index" / "INDEX.md"
    assert hub.is_file()
    hub_text = hub.read_text(encoding="utf-8")
    assert "alpha-topic" in hub_text
    assert "meta/wiki_index.json" in hub_text

    catalog = tmp_path / "wiki" / "_index" / "CATALOG.md"
    assert catalog.is_file()
    cat_text = catalog.read_text(encoding="utf-8")
    assert "alpha-topic" in cat_text
    assert "|" in cat_text

    syn = list((tmp_path / "wiki" / "notes").glob("compile-*-wiki.md"))
    assert len(syn) == 1
    assert "Overview" in syn[0].read_text(encoding="utf-8")


def test_run_wiki_graph_related_slugs_and_backlinks(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "raw" / "papers" / "x.md").write_text("# X\n", encoding="utf-8")

    payload = {
        "version": 1,
        "concepts": [
            {
                "slug": "alpha-topic",
                "title": "Alpha",
                "body": "## A\n",
                "related_slugs": ["beta-topic"],
                "sources": ["raw/papers/x.md"],
            },
            {
                "slug": "beta-topic",
                "title": "Beta",
                "body": "## B\n",
                "related_slugs": [],
                "sources": ["raw/papers/x.md"],
            },
        ],
    }
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=json.dumps(payload)))]
    )

    def factory() -> tuple[MagicMock, str]:
        return client, "fake-model"

    run_compile(ctx, wiki_graph=True, client_factory=factory)
    bl = tmp_path / "wiki" / "_index" / "BACKLINKS.md"
    assert bl.is_file()
    text = bl.read_text(encoding="utf-8")
    assert "beta-topic" in text
    assert "Incoming" in text
    alpha = (tmp_path / "wiki" / "concepts" / "alpha-topic.md").read_text(
        encoding="utf-8"
    )
    assert "related_slugs:" in alpha


def test_wiki_graph_fallback_on_bad_json(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "raw" / "papers" / "x.md").write_text("# X\n", encoding="utf-8")

    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="not json at all"))]
    )

    def factory() -> tuple[MagicMock, str]:
        return client, "fake-model"

    result = run_compile(ctx, wiki_graph=True, client_factory=factory)
    assert not result.skipped
    assert result.output_path is not None
    text = result.output_path.read_text(encoding="utf-8")
    assert "wiki_graph_fallback" in text
    assert "not json" in text


def test_load_deepseek_config_model_compile_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from crate.llm import load_deepseek_config

    monkeypatch.setenv("CRATE_DEEPSEEK_API_KEY", "k")
    monkeypatch.setenv("CRATE_DEEPSEEK_MODEL", "base-model")
    monkeypatch.setenv("CRATE_MODEL_COMPILE", "compile-only")
    cfg = load_deepseek_config(purpose="compile")
    assert cfg.model == "compile-only"
    cfg2 = load_deepseek_config(purpose="qa")
    assert cfg2.model == "base-model"
