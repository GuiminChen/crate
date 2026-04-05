"""CLI smoke tests."""

from pathlib import Path

from crate.cli import build_parser, main


def test_cli_init_and_lint(tmp_path: Path) -> None:
    assert main(["--vault", str(tmp_path), "init"]) == 0
    assert main(["--vault", str(tmp_path), "lint"]) == 0


def test_cli_wiki_graph_and_report_raw_wiki(tmp_path: Path) -> None:
    assert main(["--vault", str(tmp_path), "init"]) == 0
    assert main(["--vault", str(tmp_path), "wiki", "graph"]) == 0
    assert (tmp_path / "meta" / "wiki_body_graph.json").is_file()
    assert main(["--vault", str(tmp_path), "report", "raw-wiki"]) == 0
    assert main(["--vault", str(tmp_path), "wiki", "index-extend"]) == 0
    assert (tmp_path / "meta" / "wiki_index_extended.json").is_file()


def test_parse_watch_wiki_graph() -> None:
    p = build_parser()
    a = p.parse_args(["watch", "--wiki-graph"])
    assert a.wiki_graph is True


def test_parse_compile_no_incremental_same_as_full() -> None:
    p = build_parser()
    a = p.parse_args(["compile", "--no-incremental"])
    assert a.full is True
    b = p.parse_args(["compile", "--full"])
    assert b.full is True


def test_cli_lint_fails_on_broken_link(tmp_path: Path) -> None:
    main(["--vault", str(tmp_path), "init"])
    bad = tmp_path / "wiki" / "notes" / "bad.md"
    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("[m](nope.md)", encoding="utf-8")
    assert main(["--vault", str(tmp_path), "lint", "--json"]) == 1
