"""Promote a wiki/outputs (or vault) markdown file into wiki/concepts/."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from crate.compile_wiki import sanitize_slug
from crate.vault_paths import VaultContext

__all__ = ["promote_markdown_to_concept"]


def _strip_front_matter(text: str) -> str:
    if not text.startswith("---"):
        return text
    idx = text.find("\n---\n", 3)
    if idx == -1:
        return text
    return text[idx + 5 :]


def _title_from_front_or_body(text: str) -> str:
    if text.startswith("---"):
        idx = text.find("\n---\n", 3)
        if idx != -1:
            fm = text[3:idx]
            for line in fm.splitlines():
                m = re.match(r'^title:\s*"(.*)"\s*$', line.strip())
                if m:
                    return m.group(1)
                m2 = re.match(r"^title:\s*(.+)\s*$", line.strip())
                if m2 and not m2.group(1).startswith('"'):
                    return m2.group(1).strip()
    body = _strip_front_matter(text).strip()
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return re.sub(r"^#+\s*", "", s).strip() or "concept"
    return "concept"


def promote_markdown_to_concept(
    ctx: VaultContext,
    source_rel: str,
    *,
    slug: str | None = None,
    model_name: str = "promoted",
) -> Path:
    """Write ``wiki/concepts/<slug>.md`` from a vault markdown file."""
    src = ctx.root / source_rel.replace("\\", "/")
    src = ctx.validate_under_vault(src)
    if not src.is_file():
        raise FileNotFoundError(str(src))
    text = src.read_text(encoding="utf-8", errors="replace")
    title = _title_from_front_or_body(text)
    if slug is None:
        slug = sanitize_slug(title)
    else:
        slug = sanitize_slug(slug)
    body = _strip_front_matter(text).strip() or "(empty)\n"

    stamp = datetime.now(timezone.utc).isoformat()
    front = f"""---
title: {json.dumps(title)}
kind: concept
crate_kind: concept
slug: {json.dumps(slug)}
tags:
  - crate/concept
promoted_from: {json.dumps(source_rel.replace(chr(92), "/"))}
model: {model_name!r}
updated: {stamp}
---

"""
    out = ctx.wiki_dir() / "concepts" / f"{slug}.md"
    out = ctx.validate_under_vault(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(front + body + "\n", encoding="utf-8")
    os.replace(tmp, out)
    return out
