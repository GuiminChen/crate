"""CRATE CLI: ``init``, ``compile``, ``ask``, ``lint``."""

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
from crate.vault_paths import VaultContext, resolve_vault_root
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
    path = run_compile(ctx)
    print(path.relative_to(ctx.root))
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


def _cmd_lint(args: argparse.Namespace) -> int:
    ctx = _ctx_from_args(args)
    issues = lint_markdown_links(ctx, include_ephemeral=args.include_ephemeral)
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
        "--quiet-gate",
        action="store_true",
        help="Do not print scale gate hints to stderr",
    )
    p_compile.set_defaults(func=_cmd_compile)

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
        help="Verify wiki relative markdown links resolve to files",
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
    p_lint.set_defaults(func=_cmd_lint)

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
