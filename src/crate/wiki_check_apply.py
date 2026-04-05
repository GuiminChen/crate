"""Whitelist application of ``wiki-check`` JSON ``fixes`` to concept front matter."""

from __future__ import annotations

import os
from typing import Any

import yaml

from crate.vault_paths import VaultContext, VaultPathError

__all__ = ["apply_wiki_check_fixes", "ALLOWED_FIX_ACTIONS"]

ALLOWED_FIX_ACTIONS = frozenset(
    {
        "merge_related_slugs",
        "merge_conflicts_with_slugs",
    }
)


def _split_front_matter(text: str) -> tuple[dict[str, Any], str] | None:
    if not text.startswith("---"):
        return None
    idx = text.find("\n---\n", 3)
    if idx == -1:
        return None
    fm_raw = text[3:idx]
    body = text[idx + 5 :]
    try:
        data = yaml.safe_load(fm_raw)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        data = {}
    return data, body


def _merge_slug_field(
    data: dict[str, Any], key: str, slugs: list[str]
) -> None:
    cur = data.get(key)
    if not isinstance(cur, list):
        cur = []
    seen = {str(x) for x in cur if x is not None}
    for s in slugs:
        s = str(s).strip()
        if s and s not in seen:
            cur.append(s)
            seen.add(s)
    data[key] = cur


def _dump_md(data: dict[str, Any], body: str) -> str:
    fm = yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).rstrip()
    return f"---\n{fm}\n---\n{body}"


def apply_wiki_check_fixes(
    ctx: VaultContext,
    fixes: list[dict[str, Any]],
    *,
    dry_run: bool = True,
) -> list[dict[str, Any]]:
    """
    Apply whitelist fixes to ``wiki/concepts/*.md`` only.

    Each fix: ``action``, ``path`` (vault-relative), ``slugs`` (list of str).
    Returns a list of result dicts (applied or skipped with reason).
    """
    results: list[dict[str, Any]] = []
    concepts_root = ctx.wiki_dir() / "concepts"

    for raw in fixes:
        if not isinstance(raw, dict):
            results.append({"ok": False, "error": "fix is not an object"})
            continue
        action = str(raw.get("action", "")).strip()
        rel = str(raw.get("path", "")).strip().replace("\\", "/")
        slugs_raw = raw.get("slugs")
        if action not in ALLOWED_FIX_ACTIONS:
            results.append(
                {"ok": False, "action": action, "error": "action not whitelisted"}
            )
            continue
        if not rel.startswith("wiki/concepts/") or ".." in rel:
            results.append(
                {
                    "ok": False,
                    "path": rel,
                    "error": "path not under wiki/concepts/",
                }
            )
            continue
        if not isinstance(slugs_raw, list):
            results.append({"ok": False, "path": rel, "error": "slugs must be a list"})
            continue
        slugs = [str(x).strip() for x in slugs_raw if str(x).strip()]
        if not slugs:
            results.append({"ok": False, "path": rel, "error": "empty slugs"})
            continue

        try:
            path = ctx.validate_under_vault(ctx.root / rel)
        except VaultPathError as e:
            results.append({"ok": False, "path": rel, "error": str(e)})
            continue

        if not path.is_file() or path.suffix.lower() != ".md":
            results.append({"ok": False, "path": rel, "error": "not a markdown file"})
            continue
        try:
            path.resolve().relative_to(concepts_root.resolve())
        except ValueError:
            results.append(
                {"ok": False, "path": rel, "error": "outside wiki/concepts/"}
            )
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        parsed = _split_front_matter(text)
        if parsed is None:
            results.append({"ok": False, "path": rel, "error": "no YAML front matter"})
            continue
        data, body = parsed

        key = (
            "related_slugs"
            if action == "merge_related_slugs"
            else "conflicts_with_slugs"
        )
        before = yaml.safe_dump(
            {key: data.get(key)},
            allow_unicode=True,
            sort_keys=False,
        ).strip()
        _merge_slug_field(data, key, slugs)
        after = yaml.safe_dump(
            {key: data.get(key)},
            allow_unicode=True,
            sort_keys=False,
        ).strip()
        new_text = _dump_md(data, body)

        entry: dict[str, Any] = {
            "ok": True,
            "path": rel,
            "action": action,
            "dry_run": dry_run,
            "before": before,
            "after": after,
        }
        if dry_run:
            results.append(entry)
            continue

        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(new_text, encoding="utf-8")
        os.replace(tmp, path)
        results.append(entry)

    return results
