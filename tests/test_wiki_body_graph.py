"""wiki body graph JSON + BODYGRAPH.md."""

from crate.init_vault import init_vault
from crate.vault_paths import VaultContext
from crate.wiki_body_graph import build_wiki_body_graph, write_wiki_body_graph


def test_build_wiki_body_graph_edges(tmp_path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    a = tmp_path / "wiki" / "a.md"
    b = tmp_path / "wiki" / "b.md"
    a.write_text("[l](b.md)\n", encoding="utf-8")
    b.write_text("x\n", encoding="utf-8")
    g = build_wiki_body_graph(ctx)
    assert g["version"] == 1
    assert any(e["from"] == "wiki/a.md" and e["to"] == "wiki/b.md" for e in g["edges"])


def test_write_wiki_body_graph_writes_json(tmp_path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "wiki" / "x.md").write_text("hi\n", encoding="utf-8")
    jp, mp = write_wiki_body_graph(ctx, write_md=False)
    assert jp.name == "wiki_body_graph.json"
    assert mp is None
    assert jp.is_file()
