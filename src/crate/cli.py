"""CRATE CLI: ``init``, ``compile``, ``ask``, ``lint``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from crate.compile_run import run_compile
from crate.init_vault import init_vault
from crate.lint_wiki import lint_markdown_links
from crate.qa_agent import run_qa
from crate.vault_paths import VaultContext, resolve_vault_root


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


def _cmd_compile(args: argparse.Namespace) -> int:
    ctx = _ctx_from_args(args)
    path = run_compile(ctx)
    print(path.relative_to(ctx.root))
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    ctx = _ctx_from_args(args)
    q = " ".join(args.question).strip()
    if not q:
        print("Error: empty question", file=sys.stderr)
        return 2
    path = run_qa(
        ctx,
        q,
        feedback=not args.no_feedback,
    )
    print(path.relative_to(ctx.root))
    return 0


def _cmd_lint(args: argparse.Namespace) -> int:
    ctx = _ctx_from_args(args)
    issues = lint_markdown_links(ctx)
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
    p_ask.set_defaults(func=_cmd_ask)

    p_lint = sub.add_parser(
        "lint",
        help="Verify wiki relative markdown links resolve to files",
    )
    p_lint.add_argument(
        "--json",
        action="store_true",
        help="Emit issues as JSON",
    )
    p_lint.set_defaults(func=_cmd_lint)

    return p


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args, run the selected subcommand, return exit code."""
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
