"""Tests for vector index (mocked embeddings)."""

from pathlib import Path
from unittest.mock import MagicMock

from crate.embedding_config import EmbeddingConfig
from crate.init_vault import init_vault
from crate.vault_paths import VaultContext
from crate.vector_index import build_vector_index, chunk_markdown, semantic_search_hits


def test_chunk_markdown_splits() -> None:
    lines = "\n".join([f"line {i}" for i in range(100)])
    chunks = chunk_markdown(lines, max_chars=50)
    assert len(chunks) >= 2


def test_build_vector_index_mocked(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    note = tmp_path / "raw" / "papers" / "a.md"
    note.write_text("# Hi\n\nbody\n", encoding="utf-8")

    cfg = EmbeddingConfig(
        api_key="k",
        base_url="https://api.openai.com/v1",
        model="text-embedding-3-small",
    )

    def factory(_c: EmbeddingConfig) -> MagicMock:
        client = MagicMock()

        def emb_create(**kwargs: object) -> MagicMock:
            texts = kwargs.get("input")
            if isinstance(texts, str):
                texts = [texts]
            n = len(texts)
            r = MagicMock()
            r.data = [
                MagicMock(
                    index=i,
                    embedding=[0.0] * 8,
                )
                for i in range(n)
            ]
            return r

        client.embeddings.create = emb_create
        return client

    n = build_vector_index(ctx, reset=True, config=cfg, client_factory=factory)
    assert n >= 1

    hits = semantic_search_hits(
        ctx,
        "body",
        max_hits=3,
        config=cfg,
        client_factory=factory,
    )
    assert isinstance(hits, list)


def test_build_vector_index_batches_at_most_n(tmp_path: Path) -> None:
    """Ensure embedding batches respect per-request caps (e.g. DashScope at 10)."""
    ctx = VaultContext(root=tmp_path)
    (tmp_path / "raw" / "papers").mkdir(parents=True)
    for i in range(25):
        p = tmp_path / "raw" / "papers" / f"c{i}.md"
        p.write_text(f"# chunk\n\nline {i}\n", encoding="utf-8")

    cfg = EmbeddingConfig(
        api_key="k",
        base_url="https://api.openai.com/v1",
        model="text-embedding-3-small",
        embedding_batch_size=10,
    )
    batch_lens: list[int] = []

    def factory(_c: EmbeddingConfig) -> MagicMock:
        client = MagicMock()

        def emb_create(**kwargs: object) -> MagicMock:
            texts = kwargs.get("input")
            if isinstance(texts, str):
                texts = [texts]
            batch_lens.append(len(texts))
            n = len(texts)
            r = MagicMock()
            r.data = [MagicMock(index=i, embedding=[0.0] * 8) for i in range(n)]
            return r

        client.embeddings.create = emb_create
        return client

    n = build_vector_index(ctx, reset=True, config=cfg, client_factory=factory)
    assert n == 25
    assert batch_lens == [10, 10, 5]
    assert max(batch_lens) <= 10
