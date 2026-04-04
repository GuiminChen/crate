"""Executable tools for the Q&A agent (read, search, write outputs only)."""

from __future__ import annotations

import json
from typing import Any

from crate.vault_paths import VaultContext, VaultPathError
from crate.vault_search import MAX_SEARCH_HITS_CAP, search_markdown_hits

__all__ = ["VaultTools", "TOOL_SPECS"]

_MAX_READ_BYTES = 200_000
_MAX_SEARCH_HITS = 30  # capped by MAX_SEARCH_HITS_CAP in search_markdown_hits
_OUTPUT_PREFIX = "wiki/outputs/"


def TOOL_SPECS(*, session_id: str | None = None) -> list[dict[str, Any]]:
    """OpenAI-compatible tool definitions for chat completions."""
    write_desc = (
        "Write final answer markdown under wiki/outputs/ only. "
        "Path must start with wiki/outputs/."
    )
    if session_id:
        write_desc = (
            f"Write markdown under wiki/outputs/ or wiki/_ephemeral/{session_id}/ "
            "(session drafts). Path must use one of these prefixes."
        )
    return [
        {
            "type": "function",
            "function": {
                "name": "vault_read",
                "description": (
                    "Read text from a file under raw/ or wiki/. "
                    "Path is relative to vault root (e.g. TOPICS.md)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path, e.g. wiki/_index/TOPICS.md",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "vault_search",
                "description": (
                    "Search for a plain-text substring in *.md under wiki/ and raw/. "
                    "Returns JSON lines: path, line_number, snippet."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_hits": {
                            "type": "integer",
                            "description": "Cap results (default 20)",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "vault_search_semantic",
                "description": (
                    "Semantic search over indexed chunks (requires `crate index` and "
                    "embedding API env). Returns JSON: path, line, score, snippet. "
                    "Prefer this when the vault is large."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_hits": {
                            "type": "integer",
                            "description": "Cap results (default 10)",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "vault_write_output",
                "description": write_desc,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "e.g. wiki/outputs/answer-2026.md",
                        },
                        "content": {
                            "type": "string",
                            "description": "Markdown body (front matter optional).",
                        },
                    },
                    "required": ["path", "content"],
                },
            },
        },
    ]


class VaultTools:
    """Side-effecting helpers bound to a vault."""

    def __init__(self, ctx: VaultContext, *, session_id: str | None = None) -> None:
        """Bind tools to ``ctx``; ``session_id`` enables ``wiki/_ephemeral/`` writes."""
        self._ctx = ctx
        self._session_id = session_id.strip() if session_id else None

    def vault_read(self, path: str) -> str:
        """Read and return UTF-8 text or an error string."""
        rel = path.strip().lstrip("/")
        p = (self._ctx.root / rel).resolve()
        try:
            canon = self._ctx.validate_under_vault(p)
        except VaultPathError as e:
            return f"Error: {e}"
        parts = canon.relative_to(self._ctx.root).parts
        if parts[0] not in ("raw", "wiki"):
            return "Error: path must be under raw/ or wiki/"
        if not canon.is_file():
            return f"Error: not a file: {path}"
        data = canon.read_bytes()
        if len(data) > _MAX_READ_BYTES:
            data = data[:_MAX_READ_BYTES]
            text = data.decode("utf-8", errors="replace") + "\n…(truncated)…"
        else:
            text = canon.read_text(encoding="utf-8", errors="replace")
        return text

    def vault_search(self, query: str, max_hits: int | None = None) -> str:
        """Return JSON array of {path, line, snippet}."""
        cap = min(max_hits or 20, _MAX_SEARCH_HITS, MAX_SEARCH_HITS_CAP)
        hits = search_markdown_hits(self._ctx, query, max_hits=cap)
        return json.dumps(hits, ensure_ascii=False)

    def vault_search_semantic(self, query: str, max_hits: int | None = None) -> str:
        """Return JSON array of semantic hits or an error string."""
        from crate.vector_index import index_exists, semantic_search_hits

        if not index_exists(self._ctx):
            return (
                "Error: no vector index. Run `crate index` after setting an "
                "embedding API key (CRATE_EMBEDDING_API_KEY or OPENAI_API_KEY)."
            )
        cap = min(max_hits or 10, 50)
        try:
            hits = semantic_search_hits(self._ctx, query, max_hits=cap)
        except ValueError as e:
            return f"Error: {e}"
        return json.dumps(hits, ensure_ascii=False)

    def vault_write_output(self, path: str, content: str) -> str:
        """Write markdown under wiki/outputs/ or session ephemeral subtree."""
        rel = path.strip().lstrip("/").replace("\\", "/")
        ok = rel.startswith(_OUTPUT_PREFIX)
        if not ok and self._session_id:
            prefix = f"wiki/_ephemeral/{self._session_id}/"
            if rel.startswith(prefix):
                ok = True
        if not ok:
            return (
                "Error: path must start with wiki/outputs/ or "
                "wiki/_ephemeral/<session>/"
            )
        p = (self._ctx.root / rel).resolve()
        try:
            canon = self._ctx.validate_under_vault(p)
        except VaultPathError as e:
            return f"Error: {e}"
        canon.parent.mkdir(parents=True, exist_ok=True)
        canon.write_text(content, encoding="utf-8")
        return f"Wrote {canon.relative_to(self._ctx.root).as_posix()}"

    def dispatch(self, name: str, arguments_json: str) -> str:
        """Run tool by name with JSON arguments from the model."""
        try:
            args = json.loads(arguments_json) if arguments_json.strip() else {}
        except json.JSONDecodeError as e:
            return f"Error: invalid JSON arguments: {e}"
        if name == "vault_read":
            return self.vault_read(str(args.get("path", "")))
        if name == "vault_search":
            return self.vault_search(
                str(args.get("query", "")),
                max_hits=args.get("max_hits"),
            )
        if name == "vault_search_semantic":
            return self.vault_search_semantic(
                str(args.get("query", "")),
                max_hits=args.get("max_hits"),
            )
        if name == "vault_write_output":
            return self.vault_write_output(
                str(args.get("path", "")),
                str(args.get("content", "")),
            )
        return f"Error: unknown tool {name}"
