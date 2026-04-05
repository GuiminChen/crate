"""Persistent state for incremental ``crate compile`` (raw file fingerprints)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from crate.vault_paths import VaultContext

# v1 used mtime_ns+size; v2 uses SHA-256 of raw file bytes (stable across checkout).
COMPILE_STATE_VERSION = 2


def compile_state_path(ctx: VaultContext) -> Path:
    """Return ``meta/compile_state.json`` under the vault."""
    return ctx.meta_dir() / "compile_state.json"


def load_compile_state_dict(ctx: VaultContext) -> dict[str, Any]:
    """Load JSON object from compile state file, or return ``{}`` if missing."""
    path = compile_state_path(ctx)
    if not path.is_file():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw) if raw.strip() else {}
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def has_valid_incremental_state(data: dict[str, Any]) -> bool:
    """Return whether ``data`` has v2 SHA-256 fingerprints from a prior compile."""
    if data.get("version") != COMPILE_STATE_VERSION:
        return False
    fp = data.get("raw_fingerprints")
    if not isinstance(fp, dict):
        return False
    for _rel, entry in fp.items():
        if not _fingerprint_is_sha256(entry):
            return False
    return True


def _fingerprint_is_sha256(entry: Any) -> bool:
    return (
        isinstance(entry, dict)
        and isinstance(entry.get("sha256"), str)
        and len(entry["sha256"]) == 64
    )


def fingerprints_for_paths(paths: list[Path], root: Path) -> dict[str, dict[str, str]]:
    """Map vault-relative paths to SHA-256 hex digests of raw file bytes."""
    out: dict[str, dict[str, str]] = {}
    for p in paths:
        rel = p.relative_to(root).as_posix()
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        out[rel] = {"sha256": digest}
    return out


def select_paths_for_compile(
    root: Path,
    current: list[Path],
    stored_fp: dict[str, Any],
    *,
    full: bool,
    has_valid_state: bool,
) -> tuple[list[Path] | None, bool]:
    """
    Choose which raw files to send to the model.

    Returns ``(paths_for_prompt, skipped)``. If ``skipped`` is True,
    ``paths_for_prompt`` is None (no LLM call, no new note).
    """
    if full or not has_valid_state:
        return (current, False)

    if not isinstance(stored_fp, dict):
        stored_fp = {}

    current_fp = fingerprints_for_paths(current, root)
    rels_current = {p.relative_to(root).as_posix() for p in current}
    rels_stored = set(stored_fp.keys())

    removed = rels_stored - rels_current
    added = rels_current - rels_stored

    modified: list[str] = []
    for rel in rels_current & rels_stored:
        cur = current_fp.get(rel)
        old = stored_fp.get(rel)
        if not isinstance(old, dict) or cur != old:
            modified.append(rel)

    if not removed and not added and not modified:
        return (None, True)

    if removed:
        return (current, False)

    rel_to_path = {p.relative_to(root).as_posix(): p for p in current}
    to_rels = set(added) | set(modified)
    ordered = sorted(to_rels)
    return ([rel_to_path[r] for r in ordered], False)


def merge_save_raw_fingerprints(
    ctx: VaultContext,
    raw_fingerprints: dict[str, dict[str, str]],
) -> None:
    """Merge fingerprints into compile state; keep other JSON top-level keys."""
    path = compile_state_path(ctx)
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if path.is_file():
        try:
            raw = path.read_text(encoding="utf-8")
            loaded = json.loads(raw) if raw.strip() else {}
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, json.JSONDecodeError):
            data = {}
    data["version"] = COMPILE_STATE_VERSION
    data["raw_fingerprints"] = raw_fingerprints
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
