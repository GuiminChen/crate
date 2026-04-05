"""raw -> wiki coverage report."""

from crate.init_vault import init_vault
from crate.raw_wiki_coverage import build_raw_wiki_coverage
from crate.vault_paths import VaultContext


def test_raw_wiki_coverage_referenced(tmp_path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    raw_f = tmp_path / "raw" / "note.md"
    raw_f.write_text("src\n", encoding="utf-8")
    wiki_f = tmp_path / "wiki" / "ref.md"
    wiki_f.write_text("See [x](../raw/note.md)\n", encoding="utf-8")
    cov = build_raw_wiki_coverage(ctx)
    srcs = {s["path"]: s for s in cov["sources"]}
    assert srcs["raw/note.md"]["status"] == "referenced"
    assert "wiki/ref.md" in srcs["raw/note.md"]["referenced_by"]


def test_raw_wiki_coverage_unreferenced(tmp_path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    (tmp_path / "raw" / "orphan.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "wiki" / "other.md").write_text("no link\n", encoding="utf-8")
    cov = build_raw_wiki_coverage(ctx)
    srcs = {s["path"]: s for s in cov["sources"]}
    assert srcs["raw/orphan.md"]["status"] == "unreferenced"
