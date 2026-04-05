"""Read-only HTTP server exposing vault literal search (JSON)."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from crate.embedding_config import load_embedding_config
from crate.vault_paths import VaultContext
from crate.vault_search import MAX_SEARCH_HITS_CAP, search_markdown_hits
from crate.vector_index import index_exists, semantic_search_hits

__all__ = ["serve_search_http", "make_search_handler_class", "health_payload"]


def _truthy_semantic_flag(raw: str | None) -> bool:
    if raw is None:
        return False
    return raw.strip().lower() in ("1", "true", "yes", "on")


def health_payload(ctx: VaultContext) -> dict[str, object]:
    """
    JSON object for ``GET /health``: vault path and whether semantic search can run.

    ``semantic_ready`` is true when embedding env is set **and** ``crate index`` has
    been built (same conditions as ``GET /search?semantic=1`` without ``detail``).
    """
    embedding_configured = load_embedding_config() is not None
    semantic_index_ready = index_exists(ctx)
    wiki_index_path = ctx.meta_dir() / "wiki_index.json"
    return {
        "ok": True,
        "vault": ctx.root.as_posix(),
        "embedding_configured": embedding_configured,
        "semantic_index_ready": semantic_index_ready,
        "semantic_ready": embedding_configured and semantic_index_ready,
        "multi_page_wiki_index": wiki_index_path.is_file(),
    }


def make_search_handler_class(ctx: VaultContext) -> type[BaseHTTPRequestHandler]:
    """Build a request handler that searches ``ctx`` (closure over vault)."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            if path == "/health":
                body = (
                    json.dumps(health_payload(ctx), ensure_ascii=False) + "\n"
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/search":
                qs = parse_qs(parsed.query)
                q = (qs.get("q") or [""])[0].strip()
                try:
                    max_hits = int((qs.get("max") or ["20"])[0])
                except ValueError:
                    max_hits = 20
                max_hits = max(0, min(max_hits, MAX_SEARCH_HITS_CAP))
                semantic = _truthy_semantic_flag((qs.get("semantic") or [None])[0])
                if semantic:
                    body_obj: dict = {"query": q, "mode": "semantic", "hits": []}
                    cfg = load_embedding_config()
                    if cfg is None:
                        body_obj["detail"] = (
                            "embedding API not configured "
                            "(set CRATE_EMBEDDING_API_KEY or OPENAI_API_KEY)"
                        )
                    elif not index_exists(ctx):
                        body_obj["detail"] = (
                            "no vector index (run `crate index` in this vault first)"
                        )
                    else:
                        try:
                            body_obj["hits"] = semantic_search_hits(
                                ctx, q, max_hits=max_hits
                            )
                        except Exception as exc:  # noqa: BLE001
                            # Embedding/network errors become JSON for agent clients.
                            body_obj["detail"] = str(exc).strip() or repr(exc)
                else:
                    hits = search_markdown_hits(ctx, q, max_hits=max_hits)
                    body_obj = {"query": q, "mode": "literal", "hits": hits}
                payload = json.dumps(body_obj, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            msg = b'{"error":"not found"}\n'
            self.send_response(404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    return Handler


def serve_search_http(ctx: VaultContext, *, host: str, port: int) -> None:
    """Listen until ``KeyboardInterrupt`` (local read-only search API)."""
    import sys

    handler = make_search_handler_class(ctx)
    server = HTTPServer((host, port), handler)
    addr = server.server_address
    host_s = str(addr[0])
    port_s = int(addr[1])
    print(
        f"Search HTTP http://{host_s}:{port_s}/search?q=... "
        f"(add &semantic=1 for vector search after `crate index`; "
        f"health: /health). Ctrl+C to stop.",
        file=sys.stderr,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("serve-search: stopped.", file=sys.stderr)
    finally:
        server.server_close()
