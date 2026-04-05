"""LLM-based semantic health check for wiki (reads ``meta/wiki_index.json``)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI

from crate.compile_wiki import extract_json_object
from crate.llm import (
    DeepSeekConfig,
    build_openai_client,
    chat_extra_kwargs_for_purpose,
    load_deepseek_config,
    truncate_prompt_for_purpose,
)
from crate.vault_paths import VaultContext, VaultPathError

WIKI_INDEX_NAME = "wiki_index.json"

__all__ = ["run_semantic_wiki_check"]


def _strip_front_matter(text: str) -> str:
    if not text.startswith("---"):
        return text
    lines = text.splitlines()
    if len(lines) < 2 or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1 :])
    return text


def _excerpt_for_path(ctx: VaultContext, rel: str, max_chars: int) -> str:
    try:
        p = ctx.validate_under_vault(ctx.root / rel)
    except VaultPathError:
        return f"(invalid path: {rel})"
    if not p.is_file():
        return f"(missing file: {rel})"
    raw = p.read_text(encoding="utf-8", errors="replace")
    body = _strip_front_matter(raw).strip()
    if len(body) > max_chars:
        body = body[:max_chars] + "\n…(truncated)…"
    return body


def run_semantic_wiki_check(
    ctx: VaultContext,
    *,
    client: OpenAI | None = None,
    model: str | None = None,
    config: DeepSeekConfig | None = None,
    client_factory: Callable[[], tuple[OpenAI, str]] | None = None,
    max_pages: int | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    """
    Call LLM with wiki index + sampled pages; return parsed JSON report.

    Does not modify wiki pages. Optionally writes ``meta/semantic_wiki_report.json``.
    """
    idx_path = ctx.meta_dir() / WIKI_INDEX_NAME
    if not idx_path.is_file():
        raise FileNotFoundError(
            f"Missing {idx_path.relative_to(ctx.root)}; "
            "run `crate compile --wiki-graph` first."
        )
    index_data = json.loads(idx_path.read_text(encoding="utf-8"))
    concepts = index_data.get("concepts")
    if not isinstance(concepts, list):
        concepts = []

    if max_pages is None:
        raw = os.environ.get("CRATE_SEMANTIC_CHECK_MAX_PAGES", "").strip()
        max_pages_eff = int(raw) if raw else 8
    else:
        max_pages_eff = max_pages

    ex_max = 1500
    raw_ex = os.environ.get("CRATE_SEMANTIC_CHECK_EXCERPT_CHARS", "").strip()
    if raw_ex:
        try:
            ex_max = max(200, int(raw_ex))
        except ValueError:
            pass

    parts: list[str] = []
    for c in concepts[:max_pages_eff]:
        if not isinstance(c, dict):
            continue
        rel = str(c.get("path", "")).strip()
        if not rel.endswith(".md"):
            continue
        title = str(c.get("title", rel))
        body = _excerpt_for_path(ctx, rel, ex_max)
        parts.append(f"## {title}\npath: {rel}\n\n{body}\n")

    prompt_path = (
        Path(__file__).resolve().parent.parent.parent
        / "prompts"
        / "semantic_wiki_check.md"
    )
    try:
        instructions = prompt_path.read_text(encoding="utf-8")
    except OSError:
        instructions = "Return JSON only with version, summary, issues, orphan_raw."

    user_content = (
        "## wiki_index.json\n\n```json\n"
        + json.dumps(index_data, ensure_ascii=False, indent=2)
        + "\n```\n\n## Page excerpts\n\n"
        + ("\n".join(parts) if parts else "(no concept pages sampled)\n")
    )
    user_content = truncate_prompt_for_purpose(user_content, "lint")

    system = (
        "You are a careful wiki auditor. Follow the instructions exactly. "
        "Output valid JSON only.\n\n"
        + instructions
    )

    if client_factory is not None:
        client_used, model_name = client_factory()
    elif client is not None:
        if model is None:
            raise ValueError("model is required when client is passed")
        client_used = client
        model_name = model
    else:
        cfg = config or load_deepseek_config(purpose="lint")
        client_used, model_name = build_openai_client(cfg)

    resp = client_used.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        **chat_extra_kwargs_for_purpose("lint"),
    )
    raw_text = (resp.choices[0].message.content or "").strip()
    try:
        report = extract_json_object(raw_text)
    except (json.JSONDecodeError, ValueError) as exc:
        report = {
            "version": 1,
            "parse_error": str(exc),
            "raw_model_output": raw_text[:8000],
        }

    envelope: dict[str, Any] = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "report": report,
    }
    if write_report:
        ctx.meta_dir().mkdir(parents=True, exist_ok=True)
        out = ctx.meta_dir() / "semantic_wiki_report.json"
        out.write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return envelope
