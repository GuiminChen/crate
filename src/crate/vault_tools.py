"""Executable tools for the Q&A agent (read, search, write outputs only)."""

from __future__ import annotations

import json
from typing import Any

from crate.vault_paths import VaultContext, VaultPathError

__all__ = ["VaultTools", "TOOL_SPECS"]

_MAX_READ_BYTES = 200_000
_MAX_SEARCH_HITS = 30
_OUTPUT_PREFIX = "wiki/outputs/"


def TOOL_SPECS() -> list[dict[str, Any]]:
    """OpenAI-compatible tool definitions for chat completions."""
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
                "name": "vault_write_output",
                "description": (
                    "Write final answer markdown under wiki/outputs/ only. "
                    "Path must start with wiki/outputs/."
                ),
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

    def __init__(self, ctx: VaultContext) -> None:
        """Bind tools to ``ctx``."""
        self._ctx = ctx

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
        cap = min(max_hits or 20, _MAX_SEARCH_HITS)
        q = query.strip()
        if not q:
            return "[]"
        hits: list[dict[str, Any]] = []
        for base_name in ("wiki", "raw"):
            base = self._ctx.root / base_name
            if not base.is_dir():
                continue
            for md in sorted(base.rglob("*.md")):
                if len(hits) >= cap:
                    break
                try:
                    self._ctx.validate_under_vault(md)
                except VaultPathError:
                    continue
                try:
                    lines = md.read_text(
                        encoding="utf-8", errors="replace"
                    ).splitlines()
                except OSError:
                    continue
                for i, line in enumerate(lines, start=1):
                    if len(hits) >= cap:
                        break
                    if q.lower() in line.lower():
                        snippet = line.strip()[:500]
                        hits.append(
                            {
                                "path": md.relative_to(self._ctx.root).as_posix(),
                                "line": i,
                                "snippet": snippet,
                            }
                        )
        return json.dumps(hits, ensure_ascii=False)

    def vault_write_output(self, path: str, content: str) -> str:
        """Write markdown under wiki/outputs/ only."""
        rel = path.strip().lstrip("/").replace("\\", "/")
        if not rel.startswith(_OUTPUT_PREFIX):
            return "Error: path must start with wiki/outputs/"
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
        if name == "vault_write_output":
            return self.vault_write_output(
                str(args.get("path", "")),
                str(args.get("content", "")),
            )
        return f"Error: unknown tool {name}"
