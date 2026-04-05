"""Manual compile POC: summarize raw markdown via DeepSeek, write wiki note."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from openai import OpenAI

from crate.compile_state import (
    fingerprints_for_paths,
    has_valid_incremental_state,
    load_compile_state_dict,
    merge_save_raw_fingerprints,
    select_paths_for_compile,
)
from crate.llm import (
    DeepSeekConfig,
    build_openai_client,
    chat_extra_kwargs_for_purpose,
    load_deepseek_config,
    truncate_prompt_for_purpose,
)
from crate.vault_paths import VaultContext, VaultPathError

__all__ = [
    "CompileResult",
    "collect_raw_markdown",
    "collect_raw_sources",
    "extract_pdf_text",
    "run_compile",
    "build_compile_prompt",
]


@dataclass(frozen=True)
class CompileResult:
    """Outcome of ``run_compile``."""

    output_path: Path | None
    skipped: bool


def collect_raw_sources(ctx: VaultContext) -> list[Path]:
    """List ``*.md`` and ``*.pdf`` under ``raw/`` (recursive), sorted."""
    raw = ctx.raw_dir()
    if not raw.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(raw.rglob("*")):
        if not p.is_file():
            continue
        suf = p.suffix.lower()
        if suf not in {".md", ".pdf"}:
            continue
        try:
            out.append(ctx.validate_under_vault(p))
        except VaultPathError:
            continue
    return out


def collect_raw_markdown(ctx: VaultContext) -> list[Path]:
    """List ``*.md`` files under ``raw/`` (recursive), sorted."""
    return [p for p in collect_raw_sources(ctx) if p.suffix.lower() == ".md"]


def extract_pdf_text(path: Path) -> str:
    """
    Extract plain text from a PDF using pypdf.

    Returns a short diagnostic string if the file cannot be read or has no text.
    """
    from pypdf import PdfReader

    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001 — surface to compiler prompt
        return f"(Could not open PDF: {exc})"

    parts: list[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text()
        except Exception as exc:  # noqa: BLE001
            parts.append(f"\n[page extract error: {exc}]\n")
            continue
        if t:
            parts.append(t)
    out = "\n".join(parts).strip()
    if not out:
        return "(No extractable text from PDF; it may be image-only or need OCR.)"
    return out


def _read_source_text(path: Path, *, max_chars: int) -> str:
    """Load markdown or extracted PDF text."""
    if path.suffix.lower() == ".md":
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        text = extract_pdf_text(path)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n…(truncated)…"
    return text


def build_compile_prompt(
    ctx: VaultContext, paths: list[Path], max_chars_per_file: int = 8000
) -> str:
    """Assemble user message with raw excerpts for the model."""
    chunks: list[str] = []
    for p in paths:
        rel = p.relative_to(ctx.root).as_posix()
        body = _read_source_text(p, max_chars=max_chars_per_file)
        if p.suffix.lower() == ".pdf":
            chunks.append(f"## File: {rel}\n\n_(text extracted from PDF)_\n\n{body}\n")
        else:
            chunks.append(f"## File: {rel}\n\n{body}\n")
    if not chunks:
        return (
            "No markdown or PDF files under raw/. "
            "Add sources to raw/ then run compile again."
        )
    return "\n".join(chunks)


def run_compile(
    ctx: VaultContext,
    *,
    full: bool = False,
    wiki_graph: bool = False,
    client: OpenAI | None = None,
    model: str | None = None,
    config: DeepSeekConfig | None = None,
    client_factory: Callable[[], tuple[OpenAI, str]] | None = None,
    max_chars_per_file: int = 8000,
) -> CompileResult:
    """
    Read raw markdown and PDF text, call chat completion, write a wiki note.

    Output path: ``wiki/notes/compile-*.md`` (unless incremental skip).

    Incremental mode (default): uses ``meta/compile_state.json`` fingerprints;
    when nothing changed since last successful compile, returns
    ``CompileResult(None, skipped=True)`` without calling the model.

    If ``client`` is provided, ``model`` must be provided too. Otherwise uses
    ``client_factory`` (for tests) or ``build_openai_client``.
    """
    ctx.meta_dir().mkdir(parents=True, exist_ok=True)
    state_data = load_compile_state_dict(ctx)
    has_state = has_valid_incremental_state(state_data)
    stored_fp = state_data.get("raw_fingerprints", {})
    if not isinstance(stored_fp, dict):
        stored_fp = {}

    current_all = collect_raw_sources(ctx)
    paths, skipped = select_paths_for_compile(
        ctx.root,
        current_all,
        stored_fp,
        full=full,
        has_valid_state=has_state,
    )
    if skipped:
        return CompileResult(output_path=None, skipped=True)

    assert paths is not None
    eff_max_chars = max_chars_per_file
    _m = os.environ.get("CRATE_COMPILE_MAX_CHARS_PER_FILE", "").strip()
    if _m:
        try:
            eff_max_chars = max(1, int(_m))
        except ValueError:
            pass
    if wiki_graph:
        from crate.compile_wiki import run_wiki_graph_compile

        return run_wiki_graph_compile(
            ctx,
            paths,
            current_all,
            eff_max_chars=eff_max_chars,
            client=client,
            model=model,
            config=config,
            client_factory=client_factory,
        )

    user_content = build_compile_prompt(
        ctx, paths, max_chars_per_file=eff_max_chars
    )
    user_content = truncate_prompt_for_purpose(user_content, "compile")
    system = (
        "You are a CRATE wiki compiler. Given raw markdown and (where provided) "
        "plain text extracted from PDFs in a personal vault, produce a concise "
        "synthesis: overview, key entities, and suggested wiki structure. Use "
        "Markdown with ## headings. Do not claim unavailable facts."
    )
    if client_factory is not None:
        client_used, model_name = client_factory()
    elif client is not None:
        if model is None:
            raise ValueError("model is required when client is passed")
        client_used = client
        model_name = model
    else:
        cfg = config or load_deepseek_config(purpose="compile")
        client_used, model_name = build_openai_client(cfg)

    resp = client_used.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        **chat_extra_kwargs_for_purpose("compile"),
    )
    text = (resp.choices[0].message.content or "").strip()
    if not text:
        text = "(empty model response)"

    wiki_notes = ctx.wiki_dir() / "notes"
    wiki_notes.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if len(paths) == 1:
        slug = re.sub(
            r"[^a-zA-Z0-9._-]+",
            "-",
            paths[0].relative_to(ctx.root).as_posix(),
        )[:40]
    else:
        slug = "multi"
    out = wiki_notes / f"compile-{stamp}-{slug}.md"
    out = ctx.validate_under_vault(out)

    source_lines = (
        "\n".join(f"  - path: {p.relative_to(ctx.root).as_posix()!r}" for p in paths)
        if paths
        else "  []"
    )
    front = f"""---
title: "Compile run {stamp}"
kind: compile_run
sources:
{source_lines}
model: {model_name!r}
created: {datetime.now(timezone.utc).isoformat()}
---

"""
    full_body = front + text + "\n"
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(full_body, encoding="utf-8")
    os.replace(tmp, out)

    merge_save_raw_fingerprints(
        ctx, fingerprints_for_paths(current_all, ctx.root)
    )
    return CompileResult(output_path=out, skipped=False)
