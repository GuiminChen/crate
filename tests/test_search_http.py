"""Tests for local HTTP search server."""

import json
import threading
import urllib.error
import urllib.request
from http.server import HTTPServer

from crate.init_vault import init_vault
from crate.search_http import health_payload, make_search_handler_class
from crate.vault_paths import VaultContext


def test_search_http_search_and_health(tmp_path) -> None:
    ctx = VaultContext(root=tmp_path)
    init_vault(ctx)
    note = tmp_path / "raw" / "papers" / "a.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("# hello world\n", encoding="utf-8")

    handler = make_search_handler_class(ctx)
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    try:
        h = urllib.request.urlopen(f"http://127.0.0.1:{port}/health")
        health = json.loads(h.read().decode())
        assert health["ok"] is True
        assert health["vault"] == tmp_path.resolve().as_posix()
        assert isinstance(health["embedding_configured"], bool)
        assert isinstance(health["semantic_index_ready"], bool)
        assert health["semantic_ready"] == (
            health["embedding_configured"] and health["semantic_index_ready"]
        )
        assert health["multi_page_wiki_index"] is False
        direct = health_payload(ctx)
        assert direct == health

        r = urllib.request.urlopen(f"http://127.0.0.1:{port}/search?q=hello&max=5")
        data = json.loads(r.read().decode())
        assert data["query"] == "hello"
        assert data.get("mode") == "literal"
        assert len(data["hits"]) >= 1
        assert any("hello" in hit["snippet"].lower() for hit in data["hits"])

        r2 = urllib.request.urlopen(
            f"http://127.0.0.1:{port}/search?q=hello&semantic=1&max=5"
        )
        sem = json.loads(r2.read().decode())
        assert sem["mode"] == "semantic"
        assert sem["hits"] == []
        detail = (sem.get("detail") or "").lower()
        assert detail and (
            "embedding" in detail or "index" in detail
        ), f"unexpected detail: {sem.get('detail')!r}"

        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/nope")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        httpd.shutdown()
        thread.join(timeout=3.0)
