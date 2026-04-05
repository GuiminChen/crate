"""Planner + Q&A orchestration: one planning completion, then ``run_qa`` tool loop."""

from __future__ import annotations

import json
import os
from typing import Callable

from openai import OpenAI

from crate.compile_wiki import extract_json_object
from crate.ephemeral import validate_session_id
from crate.llm import (
    DeepSeekConfig,
    build_openai_client,
    chat_extra_kwargs_for_purpose,
    load_deepseek_config,
    truncate_prompt_for_purpose,
)
from crate.qa_agent import run_qa
from crate.vault_paths import VaultContext

__all__ = ["run_multi_agent_qa"]


def run_multi_agent_qa(
    ctx: VaultContext,
    question: str,
    *,
    session_id: str | None = None,
    max_rounds: int | None = None,
    budget_chars: int | None = None,
    client: OpenAI | None = None,
    model: str | None = None,
    config: DeepSeekConfig | None = None,
    client_factory: Callable[[], tuple[OpenAI, str]] | None = None,
    feedback: bool = True,
) -> Path:
    """
    Run a lightweight JSON planning call, then delegate to :func:`run_qa`.

    Uses ``CRATE_MULTI_AGENT_MAX_ROUNDS`` (default 16) and
    ``CRATE_MULTI_AGENT_BUDGET_CHARS`` (default 500000) when args are omitted.
    """
    if max_rounds is None:
        raw = os.environ.get("CRATE_MULTI_AGENT_MAX_ROUNDS", "").strip()
        max_rounds_eff = int(raw) if raw else 16
    else:
        max_rounds_eff = max_rounds

    if budget_chars is None:
        raw_b = os.environ.get("CRATE_MULTI_AGENT_BUDGET_CHARS", "").strip()
        budget_eff = int(raw_b) if raw_b else 500_000
    else:
        budget_eff = budget_chars

    sid: str | None = None
    if session_id is not None:
        sid = validate_session_id(session_id)

    if client_factory is not None:
        client_used, model_name = client_factory()
    elif client is not None:
        if model is None:
            raise ValueError("model is required when client is passed")
        client_used = client
        model_name = model
    else:
        cfg = config or load_deepseek_config(purpose="qa")
        client_used, model_name = build_openai_client(cfg)

    plan_prompt = (
        "You are a research planner for a local markdown vault. "
        "Reply with JSON only:\n"
        '{"sub_questions": ["short item", ...], '
        '"focus_paths": ["optional/wiki/path.md"]}\n'
        "Use at most 5 sub_questions."
    )
    user_plan = truncate_prompt_for_purpose(question, "qa")
    r1 = client_used.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": plan_prompt},
            {"role": "user", "content": user_plan},
        ],
        temperature=0.2,
        **chat_extra_kwargs_for_purpose("qa"),
    )
    plan_text = (r1.choices[0].message.content or "").strip()
    try:
        plan_obj = extract_json_object(plan_text)
    except (json.JSONDecodeError, ValueError, TypeError):
        plan_obj = {"sub_questions": [], "parse_error": True, "raw": plan_text[:2000]}

    sub = plan_obj.get("sub_questions") if isinstance(plan_obj, dict) else None
    if not isinstance(sub, list):
        sub = []
    sub_str = "\n".join(f"- {s}" for s in sub[:8] if isinstance(s, str))
    combined = (
        "--- Planner JSON ---\n"
        + json.dumps(plan_obj, ensure_ascii=False)[: budget_eff // 2]
        + "\n\n--- Sub-questions ---\n"
        + sub_str
        + "\n\n--- User question ---\n"
        + question
    )
    if len(combined) > budget_eff:
        combined = (
            combined[:budget_eff] + "\n…(truncated: CRATE_MULTI_AGENT_BUDGET_CHARS)…"
        )

    return run_qa(
        ctx,
        combined,
        client=client_used,
        model=model_name,
        feedback=feedback,
        max_rounds=max_rounds_eff,
        session_id=sid,
    )
