"""Q&A agent: DeepSeek tool loop, answer file under wiki/outputs/."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, cast

from openai import OpenAI

from crate.feedback import append_output_to_recent
from crate.llm import DeepSeekConfig, build_openai_client, load_deepseek_config
from crate.vault_paths import VaultContext
from crate.vault_tools import TOOL_SPECS, VaultTools

__all__ = ["run_qa", "build_system_prompt"]

_MAX_ROUNDS = 12


def build_system_prompt(ctx: VaultContext) -> str:
    """System prompt with vault rules and light index context."""
    topics = ctx.wiki_dir() / "_index" / "TOPICS.md"
    idx = ""
    if topics.is_file():
        try:
            t = topics.read_text(encoding="utf-8", errors="replace")
            idx = t[:6000]
            if len(t) > 6000:
                idx += "\n…(TOPICS truncated)…"
        except OSError:
            idx = "(could not read TOPICS.md)"
    return (
        "You are the CRATE vault Q&A assistant. Answer using the vault only; "
        "cite file paths when you use facts. Tools: vault_read, vault_search, "
        "vault_write_output. You MUST call vault_write_output exactly once at "
        "the end with the full markdown answer (with ## sections) and a path "
        "under wiki/outputs/ such as wiki/outputs/qa-YYYYMMDD.md. "
        "Do not invent files not in the vault. Be conservative if evidence is thin.\n\n"
        f"--- TOPICS excerpt ---\n{idx or '(empty)'}\n"
    )


def run_qa(
    ctx: VaultContext,
    question: str,
    *,
    client: OpenAI | None = None,
    model: str | None = None,
    config: DeepSeekConfig | None = None,
    client_factory: Callable[[], tuple[OpenAI, str]] | None = None,
    feedback: bool = True,
    max_rounds: int = _MAX_ROUNDS,
) -> Path:
    """
    Run a tool loop until the model finishes or max rounds.

    Returns path to the answer file under ``wiki/outputs/``.
    """
    tools = TOOL_SPECS()
    vt = VaultTools(ctx)
    system = build_system_prompt(ctx)

    if client_factory is not None:
        client_used, model_name = client_factory()
    elif client is not None:
        if model is None:
            raise ValueError("model is required when client is passed")
        client_used = client
        model_name = model
    else:
        cfg = config or load_deepseek_config()
        client_used, model_name = build_openai_client(cfg)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]

    last_output_rel: str | None = None
    last_assistant_text = ""
    rounds = 0
    while rounds < max_rounds:
        rounds += 1
        resp = client_used.chat.completions.create(
            model=model_name,
            messages=cast(Any, messages),
            tools=cast(Any, tools),
            tool_choice="auto",
            temperature=0.3,
        )
        msg = resp.choices[0].message
        last_assistant_text = (msg.content or "").strip()
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": msg.content or "",
        }
        tool_calls = getattr(msg, "tool_calls", None) or []
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "{}",
                    },
                }
                for tc in tool_calls
            ]
        messages.append(assistant_msg)

        if not tool_calls:
            break

        for tc in tool_calls:
            name = tc.function.name
            args = tc.function.arguments or "{}"
            result = vt.dispatch(name, args)
            if name == "vault_write_output" and result.startswith("Wrote "):
                try:
                    parsed = json.loads(args)
                    last_output_rel = str(parsed.get("path", "")).strip()
                except (json.JSONDecodeError, TypeError, KeyError):
                    pass
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    if last_output_rel is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        fallback = ctx.wiki_dir() / "outputs" / f"qa-fallback-{stamp}.md"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        body = (
            last_assistant_text or "(No vault_write_output call; model stopped early.)"
        )
        text = f"""---
title: "Q&A fallback"
kind: qa_output
source_query: {question!r}
created: {datetime.now(timezone.utc).isoformat()}
model: {model_name!r}
---

{body}
"""
        fb = ctx.validate_under_vault(fallback)
        fb.write_text(text, encoding="utf-8")
        rel = fb.relative_to(ctx.root).as_posix()
        if feedback:
            append_output_to_recent(ctx, rel, question_preview=question)
        return fb

    out_path = ctx.validate_under_vault(ctx.root / last_output_rel)
    if feedback:
        front = f"""---
title: "Q&A answer"
kind: qa_output
source_query: {question!r}
created: {datetime.now(timezone.utc).isoformat()}
model: {model_name!r}
---

"""
        existing = out_path.read_text(encoding="utf-8", errors="replace")
        if not existing.startswith("---"):
            out_path.write_text(front + existing, encoding="utf-8")
        append_output_to_recent(ctx, last_output_rel, question_preview=question)
    return out_path
