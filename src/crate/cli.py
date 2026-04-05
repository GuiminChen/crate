"""CRATE CLI: init, compile, watch, serve-search, doctor, ask, lint, and more."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from crate.compile_run import run_compile
from crate.ephemeral import (
    clean_old_ephemeral,
    finalize_ephemeral_session,
    init_ephemeral_session,
    validate_session_id,
)
from crate.init_vault import init_vault
from crate.lint_wiki import lint_markdown_links
from crate.qa_agent import run_qa
from crate.vault_paths import VaultContext, VaultPathError, resolve_vault_root
from crate.vault_search import search_markdown_hits
from crate.vault_stats import (
    GateConfig,
    collect_vault_stats,
    evaluate_gates,
    gate_message,
)


def _ctx_from_args(args: argparse.Namespace) -> VaultContext:
    cwd = Path.cwd().resolve()
    root = resolve_vault_root(cwd, args.vault)
    return VaultContext(root=root)


def _cmd_init(args: argparse.Namespace) -> int:
    ctx = _ctx_from_args(args)
    paths = init_vault(ctx, force=args.force)
    for p in paths:
        print(p.relative_to(ctx.root))
    print(f"Initialized vault at {ctx.root}", file=sys.stderr)
    return 0


def _maybe_print_gate(ctx: VaultContext, quiet: bool) -> None:
    if quiet:
        return
    stats = collect_vault_stats(ctx)
    reasons = evaluate_gates(stats, GateConfig.from_environ())
    if reasons:
        print(gate_message(reasons), file=sys.stderr)


def _cmd_compile(args: argparse.Namespace) -> int:
    ctx = _ctx_from_args(args)
    _maybe_print_gate(ctx, args.quiet_gate)
    result = run_compile(ctx, full=args.full, wiki_graph=args.wiki_graph)
    if result.skipped:
        print(
            "No raw changes since last compile; skipping "
            "(use --full or --no-incremental to rebuild).",
            file=sys.stderr,
        )
        return 0
    assert result.output_path is not None
    print(result.output_path.relative_to(ctx.root))
    return 0


def _cmd_watch(args: argparse.Namespace) -> int:
    from crate.raw_watch import run_watch_loop

    ctx = _ctx_from_args(args)
    run_watch_loop(
        ctx,
        debounce_seconds=args.debounce_seconds,
        poll_interval=args.poll_interval,
        quiet_gate=args.quiet_gate,
        wiki_graph=args.wiki_graph,
    )
    return 0


def _cmd_serve_search(args: argparse.Namespace) -> int:
    from crate.search_http import serve_search_http

    ctx = _ctx_from_args(args)
    serve_search_http(ctx, host=args.host, port=args.port)
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    ctx = _ctx_from_args(args)
    _maybe_print_gate(ctx, args.quiet_gate)
    q = " ".join(args.question).strip()
    if not q:
        print("Error: empty question", file=sys.stderr)
        return 2
    sid = None
    if getattr(args, "session", None):
        try:
            sid = validate_session_id(str(args.session))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
    path = run_qa(
        ctx,
        q,
        feedback=not args.no_feedback,
        session_id=sid,
    )
    print(path.relative_to(ctx.root))
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    from crate.search_http import health_payload

    ctx = _ctx_from_args(args)
    stats = collect_vault_stats(
        ctx,
        include_outputs=not args.exclude_outputs,
        include_ephemeral=args.include_ephemeral,
    )
    cfg = GateConfig.from_environ()
    reasons = evaluate_gates(stats, cfg)
    payload = {
        "wiki": {
            "md_files": stats.wiki_md_files,
            "word_count": stats.wiki_word_count,
            "pdf_files": stats.wiki_pdf_files,
        },
        "raw": {
            "md_files": stats.raw_md_files,
            "word_count": stats.raw_word_count,
            "pdf_files": stats.raw_pdf_files,
        },
        "gates": {
            "triggered": bool(reasons),
            "reasons": reasons,
            "thresholds": {
                "CRATE_GATE_WIKI_WORDS": cfg.max_wiki_words,
                "CRATE_GATE_WIKI_FILES": cfg.max_wiki_files,
                "CRATE_GATE_RAW_WORDS": cfg.max_raw_words,
                "CRATE_GATE_RAW_FILES": cfg.max_raw_files,
            },
        },
        "readiness": health_payload(ctx),
    }
    if getattr(args, "gates_json", False):
        print(
            json.dumps(payload["gates"], ensure_ascii=False, indent=2),
        )
    elif args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"wiki: {stats.wiki_md_files} md files, {stats.wiki_word_count} words")
        print(f"raw: {stats.raw_md_files} md files, {stats.raw_word_count} words")
        if reasons:
            print("GATE:", "; ".join(reasons), file=sys.stderr)
        else:
            print("gates: ok")
    if args.strict and reasons:
        return 1
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    from crate.doctor import vault_doctor_report, vault_standard_dirs_ok

    ctx = _ctx_from_args(args)
    report = vault_doctor_report(ctx)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        d = report["dirs"]
        print(f"crate_version: {report['crate_version']}")
        print(f"vault: {report['vault']}")
        print(f"dirs: raw={d['raw']} wiki={d['wiki']} meta={d['meta']}")
        print(f"compile_state: {report['compile_state_present']}")
        print(f"compile_wiki_last: {report['compile_wiki_last_present']}")
        print(f"semantic_wiki_report: {report['semantic_wiki_report_present']}")
        print(f"embeddings_sqlite: {report['embeddings_sqlite_present']}")
        print(f"embedding_configured: {report['embedding_configured']}")
        print(f"semantic_index_ready: {report['semantic_index_ready']}")
        print(f"semantic_ready: {report['semantic_ready']}")
        print(f"multi_page_wiki_index: {report['multi_page_wiki_index']}")
    if args.strict and not vault_standard_dirs_ok(report):
        print(
            "Error: missing raw/, wiki/, or meta/ (run `crate init` in this vault).",
            file=sys.stderr,
        )
        return 1
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    ctx = _ctx_from_args(args)
    q = " ".join(args.query).strip()
    if not q:
        print("Error: empty query", file=sys.stderr)
        return 2
    if args.semantic:
        from crate.vector_index import semantic_search_hits

        try:
            hits = semantic_search_hits(ctx, q, max_hits=args.max_hits)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
    else:
        hits = search_markdown_hits(ctx, q, max_hits=args.max_hits)
    if args.json:
        print(json.dumps(hits, ensure_ascii=False, indent=2))
    else:
        for h in hits:
            if args.semantic:
                sc = h.get("score", "")
                print(f"{h['path']}:{h['line']} ({sc}): {h['snippet']}")
            else:
                print(f"{h['path']}:{h['line']}: {h['snippet']}")
    return 0


def _cmd_index(args: argparse.Namespace) -> int:
    from crate.vector_index import build_vector_index

    ctx = _ctx_from_args(args)
    try:
        n = build_vector_index(ctx, reset=args.reset)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    print(n)
    return 0


def _cmd_ephemeral_init(args: argparse.Namespace) -> int:
    ctx = _ctx_from_args(args)
    sid = init_ephemeral_session(ctx)
    print(sid)
    return 0


def _cmd_ephemeral_finalize(args: argparse.Namespace) -> int:
    ctx = _ctx_from_args(args)
    try:
        sid = validate_session_id(args.session_id)
        out = finalize_ephemeral_session(ctx, sid, delete=args.delete)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    print(out.relative_to(ctx.root))
    return 0


def _cmd_ephemeral_clean(args: argparse.Namespace) -> int:
    ctx = _ctx_from_args(args)
    try:
        removed = clean_old_ephemeral(ctx, older_than_days=args.older_than)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    for name in removed:
        print(name)
    return 0


def _cmd_wiki_check(args: argparse.Namespace) -> int:
    from crate.wiki_semantic import run_semantic_wiki_check

    ctx = _ctx_from_args(args)
    try:
        env = run_semantic_wiki_check(ctx, write_report=not args.no_write)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2
    report = env.get("report", env)
    payload = env if args.json_full else report
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_wiki_figures_init(args: argparse.Namespace) -> int:
    from crate.marp_render import ensure_figures_dir

    ctx = _ctx_from_args(args)
    p = ensure_figures_dir(ctx)
    print(p.relative_to(ctx.root))
    return 0


def _cmd_wiki_normalize(args: argparse.Namespace) -> int:
    from crate.wiki_normalize import normalize_wiki_markdown

    ctx = _ctx_from_args(args)
    n, paths = normalize_wiki_markdown(
        ctx,
        to_md_links=args.to_md_links,
        to_wikilinks=args.to_wikilinks,
        include_ephemeral=args.include_ephemeral,
    )
    print(f"wiki normalize: updated {n} file(s)", file=sys.stderr)
    for rel in paths:
        print(rel)
    return 0


def _cmd_marp(args: argparse.Namespace) -> int:
    from crate.marp_render import run_marp

    ctx = _ctx_from_args(args)
    paths = None
    if args.paths:
        paths = []
        for s in args.paths:
            p = Path(s)
            if not p.is_absolute():
                p = (ctx.root / p).resolve()
            try:
                paths.append(ctx.validate_under_vault(p))
            except VaultPathError as e:
                print(f"Error: {e}", file=sys.stderr)
                return 2
    results = run_marp(ctx, paths=paths, to_pdf=not args.no_pdf)
    if not results:
        print("marp: no matching markdown files", file=sys.stderr)
        return 0
    bad = 0
    for src, msg in results:
        rel = src.relative_to(ctx.root).as_posix()
        print(f"{rel}: {msg}")
        if msg.startswith("exit ") or msg.startswith("os error"):
            bad += 1
    return 1 if bad else 0


def _cmd_ask_multi(args: argparse.Namespace) -> int:
    from crate.multi_agent import run_multi_agent_qa

    ctx = _ctx_from_args(args)
    _maybe_print_gate(ctx, args.quiet_gate)
    q = " ".join(args.question).strip()
    if not q:
        print("Error: empty question", file=sys.stderr)
        return 2
    sid = None
    if getattr(args, "session", None):
        try:
            sid = validate_session_id(str(args.session))
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 2
    path = run_multi_agent_qa(
        ctx,
        q,
        feedback=not args.no_feedback,
        session_id=sid,
    )
    print(path.relative_to(ctx.root))
    return 0


def _cmd_lint(args: argparse.Namespace) -> int:
    ctx = _ctx_from_args(args)
    issues = lint_markdown_links(
        ctx,
        include_ephemeral=args.include_ephemeral,
        include_wikilinks=args.wikilinks,
        include_duplicate_headings=not args.no_duplicate_headings,
        include_raw=args.raw,
    )
    if args.json:
        payload = [
            {
                "file": i.file,
                "line": i.line,
                "kind": i.kind,
                "target": i.target,
                "message": i.message,
            }
            for i in issues
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for i in issues:
            print(f"{i.file}:{i.line}: {i.message}")
    return 1 if issues else 0


def build_parser() -> argparse.ArgumentParser:
    """Construct the ``crate`` CLI argument parser."""
    p = argparse.ArgumentParser(
        prog="crate",
        description="CRATE vault compiler CLI",
    )
    p.add_argument(
        "--vault",
        metavar="PATH",
        default=None,
        help="Vault root (default: current directory)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Create raw/wiki/meta tree")
    p_init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite starter files if they exist",
    )
    p_init.set_defaults(func=_cmd_init)

    p_compile = sub.add_parser(
        "compile",
        help="POC: summarize raw/*.md via DeepSeek into wiki/notes",
    )
    p_compile.add_argument(
        "--full",
        "--no-incremental",
        action="store_true",
        help=(
            "Full rebuild: compile all raw sources and refresh fingerprints. "
            "Same as --no-incremental."
        ),
    )
    p_compile.add_argument(
        "--quiet-gate",
        action="store_true",
        help="Do not print scale gate hints to stderr",
    )
    p_compile.add_argument(
        "--wiki-graph",
        action="store_true",
        help=(
            "Multi-page wiki: LLM emits JSON; write wiki/concepts/*.md and "
            "meta/wiki_index.json (see docs/usage.md)"
        ),
    )
    p_compile.set_defaults(func=_cmd_compile)

    p_watch = sub.add_parser(
        "watch",
        help="Poll raw/ for changes and run compile after a quiet period",
    )
    p_watch.add_argument(
        "--debounce-seconds",
        type=float,
        default=3.0,
        metavar="SEC",
        help="Wait this long after raw/ stops changing before compiling (default 3)",
    )
    p_watch.add_argument(
        "--poll-interval",
        type=float,
        default=0.5,
        metavar="SEC",
        help="How often to scan raw/ fingerprints (default 0.5)",
    )
    p_watch.add_argument(
        "--quiet-gate",
        action="store_true",
        help="Do not print scale gate hints before compile",
    )
    p_watch.add_argument(
        "--wiki-graph",
        action="store_true",
        help="Run multi-page compile (same as compile --wiki-graph) after debounce",
    )
    p_watch.set_defaults(func=_cmd_watch)

    p_serve = sub.add_parser(
        "serve-search",
        help="Local read-only HTTP JSON search (/search?q=…&semantic=1, /health)",
    )
    p_serve.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default 127.0.0.1)",
    )
    p_serve.add_argument(
        "--port",
        type=int,
        default=8765,
        metavar="N",
        help="TCP port (default 8765)",
    )
    p_serve.set_defaults(func=_cmd_serve_search)

    p_ask = sub.add_parser(
        "ask",
        help="Q&A agent (DeepSeek tools): answer from vault, file under wiki/outputs/",
    )
    p_ask.add_argument(
        "question",
        nargs="+",
        help="Question text (words joined with spaces)",
    )
    p_ask.add_argument(
        "--no-feedback",
        action="store_true",
        help="Do not append a line to wiki/_index/RECENT.md",
    )
    p_ask.add_argument(
        "--quiet-gate",
        action="store_true",
        help="Do not print scale gate hints to stderr",
    )
    p_ask.add_argument(
        "--session",
        metavar="ID",
        default=None,
        help="Allow writes under wiki/_ephemeral/ID/ (use `crate ephemeral init`)",
    )
    p_ask.set_defaults(func=_cmd_ask)

    p_stats = sub.add_parser(
        "stats",
        help="Word and file counts for wiki/ and raw/; optional scale gate check",
    )
    p_stats.add_argument(
        "--json",
        action="store_true",
        help="Emit stats and gate info as JSON",
    )
    p_stats.add_argument(
        "--gates-json",
        action="store_true",
        help="Emit only the gates object as JSON (no jq needed; overrides --json)",
    )
    p_stats.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any gate threshold is exceeded",
    )
    p_stats.add_argument(
        "--exclude-outputs",
        action="store_true",
        help="Exclude wiki/outputs/** from wiki counts",
    )
    p_stats.add_argument(
        "--include-ephemeral",
        action="store_true",
        help="Include wiki/_ephemeral/** in wiki counts",
    )
    p_stats.set_defaults(func=_cmd_stats)

    p_doctor = sub.add_parser(
        "doctor",
        help="Vault layout + readiness (dirs, compile state, semantic/wiki graph)",
    )
    p_doctor.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON (extends serve-search /health with dirs, compile_state)",
    )
    p_doctor.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if raw/, wiki/, or meta/ is missing (CI guard)",
    )
    p_doctor.set_defaults(func=_cmd_doctor)

    p_search = sub.add_parser(
        "search",
        help="Literal substring search in raw/**/*.md and wiki/**/*.md",
    )
    p_search.add_argument(
        "query",
        nargs="+",
        help="Search text (words joined with spaces)",
    )
    p_search.add_argument(
        "--max-hits",
        type=int,
        default=20,
        metavar="N",
        help="Max results (default 20)",
    )
    p_search.add_argument(
        "--json",
        action="store_true",
        help="Emit hits as JSON",
    )
    p_search.add_argument(
        "--semantic",
        action="store_true",
        help="Semantic search (needs `crate index` + embedding API env)",
    )
    p_search.set_defaults(func=_cmd_search)

    p_index = sub.add_parser(
        "index",
        help=(
            "Build semantic embedding index "
            "(CRATE_EMBEDDING_API_KEY or OPENAI_API_KEY)"
        ),
    )
    p_index.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing chunks before reindexing",
    )
    p_index.set_defaults(func=_cmd_index)

    p_eph = sub.add_parser(
        "ephemeral",
        help="Short-lived wiki under wiki/_ephemeral/<session>/",
    )
    ep_sub = p_eph.add_subparsers(dest="eph_cmd", required=True)

    p_ein = ep_sub.add_parser("init", help="Create wiki/_ephemeral/<new-id>/")
    p_ein.set_defaults(func=_cmd_ephemeral_init)

    p_efin = ep_sub.add_parser(
        "finalize",
        help="Merge session markdown into wiki/outputs/FINAL_<id>.md",
    )
    p_efin.add_argument("session_id", help="Session id from ephemeral init")
    p_efin.add_argument(
        "--delete",
        action="store_true",
        help="Remove wiki/_ephemeral/<session_id>/ after packing",
    )
    p_efin.set_defaults(func=_cmd_ephemeral_finalize)

    p_ecln = ep_sub.add_parser("clean", help="Remove ephemeral dirs older than N days")
    p_ecln.add_argument(
        "--older-than",
        type=int,
        metavar="DAYS",
        required=True,
        help="Delete subdirs of wiki/_ephemeral/ older than this many days",
    )
    p_ecln.set_defaults(func=_cmd_ephemeral_clean)

    p_lint = sub.add_parser(
        "lint",
        help=(
            "Verify wiki/ (optional raw/) links, images, "
            "optional wikilinks & heading dupes"
        ),
    )
    p_lint.add_argument(
        "--json",
        action="store_true",
        help="Emit issues as JSON",
    )
    p_lint.add_argument(
        "--include-ephemeral",
        action="store_true",
        help="Also lint wiki/_ephemeral/**/*.md",
    )
    p_lint.add_argument(
        "--wikilinks",
        action="store_true",
        help="Also check Obsidian-style [[wikilinks]] resolve to a file",
    )
    p_lint.add_argument(
        "--no-duplicate-headings",
        action="store_true",
        help="Skip duplicate ATX (#) heading check within the same file",
    )
    p_lint.add_argument(
        "--raw",
        action="store_true",
        help="Also scan raw/**/*.md (same rules as wiki/)",
    )
    p_lint.set_defaults(func=_cmd_lint)

    p_wcheck = sub.add_parser(
        "wiki-check",
        help="LLM semantic health check (needs meta/wiki_index.json from --wiki-graph)",
    )
    p_wcheck.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write meta/semantic_wiki_report.json",
    )
    p_wcheck.add_argument(
        "--json-full",
        action="store_true",
        help="Include envelope (generated, model) in JSON output",
    )
    p_wcheck.set_defaults(func=_cmd_wiki_check)

    p_wiki = sub.add_parser(
        "wiki",
        help="Wiki utilities (link normalization)",
    )
    wiki_sub = p_wiki.add_subparsers(dest="wiki_cmd", required=True)

    p_wn = wiki_sub.add_parser(
        "normalize",
        help="Convert [[wikilinks]] to markdown links or the reverse",
    )
    wgrp = p_wn.add_mutually_exclusive_group(required=True)
    wgrp.add_argument(
        "--to-md-links",
        action="store_true",
        help="Replace [[links]] with [text](relative.md)",
    )
    wgrp.add_argument(
        "--to-wikilinks",
        action="store_true",
        help="Replace local [text](path) with [[stem]]",
    )
    p_wn.add_argument(
        "--include-ephemeral",
        action="store_true",
        help="Also process wiki/_ephemeral/**/*.md",
    )
    p_wn.set_defaults(func=_cmd_wiki_normalize)

    p_wfig = wiki_sub.add_parser(
        "figures-init",
        help="Create wiki/outputs/figures/ for matplotlib scripts",
    )
    p_wfig.set_defaults(func=_cmd_wiki_figures_init)

    p_marp = sub.add_parser(
        "marp",
        help="Run local Marp CLI on slides (marp: true in front matter)",
    )
    p_marp.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="Markdown files (default: scan wiki/ for marp: true)",
    )
    p_marp.add_argument(
        "--no-pdf",
        action="store_true",
        help="Do not pass --pdf (preview / default marp behavior only)",
    )
    p_marp.set_defaults(func=_cmd_marp)

    p_am = sub.add_parser(
        "ask-multi",
        help="Planner + Q&A agent (two-phase; same outputs as ask)",
    )
    p_am.add_argument(
        "question",
        nargs="+",
        help="Question text",
    )
    p_am.add_argument(
        "--no-feedback",
        action="store_true",
        help="Do not append a line to wiki/_index/RECENT.md",
    )
    p_am.add_argument(
        "--quiet-gate",
        action="store_true",
        help="Do not print scale gate hints to stderr",
    )
    p_am.add_argument(
        "--session",
        metavar="ID",
        default=None,
        help="Allow writes under wiki/_ephemeral/ID/",
    )
    p_am.set_defaults(func=_cmd_ask_multi)

    return p


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args, run the selected subcommand, return exit code."""
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
