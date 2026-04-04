"""Short-lived wiki under wiki/_ephemeral/{session_id}/ (M3)."""

from __future__ import annotations

import re
import shutil
import time
import uuid
from pathlib import Path

from crate.vault_paths import VaultContext, VaultPathError

__all__ = [
    "SESSION_ID_RE",
    "validate_session_id",
    "ephemeral_dir",
    "init_ephemeral_session",
    "finalize_ephemeral_session",
    "clean_old_ephemeral",
]

SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9._-]{1,256}$")


def validate_session_id(session_id: str) -> str:
    """Return stripped id or raise ``ValueError``."""
    s = session_id.strip()
    if not s or ".." in s or "/" in s or "\\" in s:
        raise ValueError("invalid session id")
    if not SESSION_ID_RE.match(s):
        raise ValueError("invalid session id")
    return s


def ephemeral_dir(ctx: VaultContext, session_id: str) -> Path:
    """Return resolved ``wiki/_ephemeral/<session_id>`` under the vault."""
    sid = validate_session_id(session_id)
    p = (ctx.wiki_dir() / "_ephemeral" / sid).resolve()
    ctx.validate_under_vault(p)
    return p


def init_ephemeral_session(ctx: VaultContext) -> str:
    """Create ``wiki/_ephemeral/<id>/`` with README; return new session id."""
    ctx.wiki_dir().mkdir(parents=True, exist_ok=True)
    ephem = ctx.wiki_dir() / "_ephemeral"
    ephem.mkdir(parents=True, exist_ok=True)
    sid = f"{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
    d = ephem / sid
    d.mkdir(parents=True, exist_ok=True)
    readme = d / "README.md"
    readme.write_text(
        f"# Ephemeral session `{sid}`\n\n"
        "Draft notes for this question run. "
        "Use `crate ephemeral finalize` to pack into wiki/outputs/.\n",
        encoding="utf-8",
    )
    ctx.validate_under_vault(d)
    return sid


def finalize_ephemeral_session(
    ctx: VaultContext,
    session_id: str,
    *,
    delete: bool = False,
) -> Path:
    """
    Concatenate markdown under the session dir into ``wiki/outputs/FINAL_<sid>.md``.

    Returns path to the output file.
    """
    root = ephemeral_dir(ctx, session_id)
    if not root.is_dir():
        raise FileNotFoundError(f"session not found: {session_id}")
    parts: list[str] = []
    for p in sorted(root.rglob("*.md")):
        if not p.is_file():
            continue
        try:
            ctx.validate_under_vault(p)
        except VaultPathError:
            continue
        rel = p.relative_to(ctx.root).as_posix()
        body = p.read_text(encoding="utf-8", errors="replace")
        parts.append(f"## Source: {rel}\n\n{body}\n\n---\n\n")
    out_dir = ctx.wiki_dir() / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe = validate_session_id(session_id).replace("/", "-")
    out = out_dir / f"FINAL_{safe}.md"
    out = ctx.validate_under_vault(out.resolve())
    header = (
        f"---\n"
        f'title: "Ephemeral finalize {session_id}"\n'
        f"kind: ephemeral_finalize\n"
        f"session_id: {session_id!r}\n"
        f"---\n\n"
    )
    body = "\n".join(parts) if parts else "(empty)\n"
    out.write_text(header + body, encoding="utf-8")
    if delete:
        shutil.rmtree(root)
    return out


def clean_old_ephemeral(ctx: VaultContext, *, older_than_days: int) -> list[str]:
    """Delete old ``wiki/_ephemeral/<id>/`` dirs; return removed directory names."""
    if older_than_days < 1:
        raise ValueError("older_than_days must be >= 1")
    base = ctx.wiki_dir() / "_ephemeral"
    if not base.is_dir():
        return []
    cutoff = time.time() - older_than_days * 86400
    removed: list[str] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        try:
            ctx.validate_under_vault(child.resolve())
        except VaultPathError:
            continue
        try:
            mtime = child.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            name = child.name
            shutil.rmtree(child)
            removed.append(name)
    return removed
