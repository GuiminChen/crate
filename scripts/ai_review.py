#!/usr/bin/env python3
"""Optional OpenAI-based PR review; loads CRATE rules from .cursorrules and .cursor/rules."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

RULES_PATHS = (
    ".cursorrules",
    ".cursor/rules/architecture.md",
    ".cursor/rules/vault_and_markdown.md",
    ".cursor/rules/python_coding.md",
    ".cursor/rules/testing.md",
    ".cursor/rules/lessons_from_bugs.md",
)


def load_project_rules() -> str:
    """Load markdown/text rules from the repository root."""
    root = Path.cwd()
    chunks: list[str] = []
    for rel in RULES_PATHS:
        path = root / rel
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            chunks.append(f"=== {rel} ===\n{text}")
    return "\n\n".join(chunks) if chunks else "(no rule files found)"


def git_changed_py_paths(base: str) -> list[Path]:
    """Paths to changed Python files under src/ or tests/."""
    try:
        out = subprocess.check_output(
            [
                "git",
                "diff",
                "--name-only",
                "--diff-filter=ACM",
                f"{base}...HEAD",
            ],
            text=True,
            cwd=Path.cwd(),
        )
    except subprocess.CalledProcessError:
        return []
    result: list[Path] = []
    for line in out.splitlines():
        raw = line.strip()
        if not raw.endswith(".py"):
            continue
        path = Path(raw)
        top = path.parts[0] if path.parts else ""
        if top in ("src", "tests") and path.is_file():
            result.append(path)
    return result


def git_path_diff(path: Path, base: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "diff", f"{base}...HEAD", "--", str(path)],
            text=True,
            cwd=Path.cwd(),
        )
    except subprocess.CalledProcessError:
        return "(diff unavailable)"


@dataclass
class CodeFile:
    path: Path
    content: str
    changes: str


class AIReviewer:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.project_rules = load_project_rules()

    async def review_file(self, code_file: CodeFile) -> dict[str, Any]:
        prompt = (
            "You are a senior Python engineer reviewing code for **CRATE**, "
            "a local-first vault/wiki compiler (raw → wiki, lint, optional Q&A).\n\n"
            "## Project rules\n"
            f"{self.project_rules}\n\n"
            "## File\n"
            f"Path: {code_file.path}\n\n"
            "## Full file\n```python\n"
            f"{code_file.content}\n```\n\n"
            "## Diff\n```\n"
            f"{code_file.changes}\n```\n\n"
            "Review: (1) architecture vs CRATE vault/compile/lint boundaries, "
            "(2) code quality, (3) security, (4) performance, (5) testability, "
            "(6) documentation.\n"
            "Return JSON only with keys file, issues (type, description, "
            "severity high|medium|low, suggestion, example), overall_score (0-100), "
            "summary."
        )
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Lead reviewer for the CRATE repository.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            return {
                "file": str(code_file.path),
                "issues": [
                    {
                        "type": "system_error",
                        "description": f"Review failed: {exc!s}",
                        "severity": "high",
                        "suggestion": "Please review manually.",
                        "example": "",
                    }
                ],
                "overall_score": 0,
                "summary": "Error during AI review.",
            }

    async def generate_summary(self, reviews: list[dict[str, Any]]) -> str:
        body = json.dumps(reviews, indent=2, ensure_ascii=False)
        prompt = (
            "Summarize these per-file reviews for a GitHub PR comment using "
            f"Markdown.\n\n{body}\n\n"
            "Include overall assessment, any high-severity findings, and "
            "whether to merge (yes / no / conditional)."
        )
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You write concise PR summaries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or "_Empty summary._"


async def async_main(base: str, max_files: int) -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("OPENAI_API_KEY not set; exiting without summary.", file=sys.stderr)
        sys.exit(0)
    model = os.environ.get("OPENAI_REVIEW_MODEL", "gpt-4o-mini")
    reviewer = AIReviewer(api_key=api_key, model=model)
    paths = git_changed_py_paths(base)[:max_files]
    if not paths:
        note = (
            f"_No Python changes under `src/` or `tests/` vs `{base}`; "
            "skipping per-file review._"
        )
        Path("ai_review_summary.md").write_text(note, encoding="utf-8")
        return
    reviews: list[dict[str, Any]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        diff = git_path_diff(path, base) or "(no diff)"
        reviews.append(await reviewer.review_file(CodeFile(path, text, diff)))
    summary = await reviewer.generate_summary(reviews)
    Path("ai_review_summary.md").write_text(summary, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="CRATE optional AI PR review.")
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--repo", type=str, required=True)
    parser.add_argument("--author", type=str, required=True)
    parser.add_argument(
        "--base",
        type=str,
        default=(
            os.environ.get("CRATE_REVIEW_BASE")
            or os.environ.get("GITHUB_BASE_REF")
            or "origin/main"
        ),
        help="Git base (SHA or ref) for comparison; CI sets CRATE_REVIEW_BASE.",
    )
    parser.add_argument("--max-files", type=int, default=8)
    args = parser.parse_args()
    # Reserved for future GitHub API use; avoids unused-arg lint in callers.
    _ = (args.pr_number, args.repo, args.author)
    asyncio.run(async_main(args.base, args.max_files))


if __name__ == "__main__":
    main()
