"""Tests for wiki promote."""

from pathlib import Path

from crate.init_vault import init_vault
from crate.vault_paths import VaultContext
from crate.wiki_promote import promote_markdown_to_concept


def test_promote_output_to_concept(tmp_path: Path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    out = tmp_path / "wiki" / "outputs" / "q.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        '---\ntitle: "My Topic"\nkind: qa_output\n---\n\nHello\n',
        encoding="utf-8",
    )
    p = promote_markdown_to_concept(ctx, "wiki/outputs/q.md", slug="my-topic")
    assert p.name == "my-topic.md"
    t = p.read_text(encoding="utf-8")
    assert "kind: concept" in t
    assert "promoted_from" in t
    assert "Hello" in t
