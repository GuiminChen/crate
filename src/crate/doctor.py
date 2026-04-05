"""One-shot vault diagnostics (dirs, compile state, search readiness)."""

from __future__ import annotations

from typing import Any

from crate.search_http import health_payload
from crate.vault_paths import VaultContext

# Keep in sync with ``crate.vector_index.INDEX_FILENAME`` (avoid importing numpy here).
_EMBEDDINGS_SQLITE = "embeddings.sqlite"

__all__ = ["vault_doctor_report", "vault_standard_dirs_ok"]


def _crate_cli_version() -> str:
    """Installed ``crate`` distribution version, or ``unknown`` if not installed."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("crate")
    except PackageNotFoundError:
        return "unknown"


def vault_standard_dirs_ok(report: dict[str, Any]) -> bool:
    """Return True if ``raw/``, ``wiki/``, and ``meta/`` all exist."""
    d = report.get("dirs")
    if not isinstance(d, dict):
        return False
    return bool(d.get("raw") and d.get("wiki") and d.get("meta"))


def vault_doctor_report(ctx: VaultContext) -> dict[str, Any]:
    """
    Structured status for ``crate doctor``: readiness plus layout hints.

    ``readiness`` matches :func:`crate.search_http.health_payload`; other keys
    help spot uninitialized or half-initialized vaults.
    """
    meta = ctx.meta_dir()
    compile_state = meta / "compile_state.json"
    compile_wiki_last = meta / "compile_wiki_last.json"
    semantic_wiki_report = meta / "semantic_wiki_report.json"
    embeddings_db = meta / _EMBEDDINGS_SQLITE
    wiki_body_graph = meta / "wiki_body_graph.json"
    raw_wiki_coverage = meta / "raw_wiki_coverage.json"
    wiki_index_extended = meta / "wiki_index_extended.json"
    base = health_payload(ctx)
    return {
        **base,
        "crate_version": _crate_cli_version(),
        "dirs": {
            "raw": ctx.raw_dir().is_dir(),
            "wiki": ctx.wiki_dir().is_dir(),
            "meta": meta.is_dir(),
        },
        "compile_state_present": compile_state.is_file(),
        "compile_wiki_last_present": compile_wiki_last.is_file(),
        "semantic_wiki_report_present": semantic_wiki_report.is_file(),
        "embeddings_sqlite_present": embeddings_db.is_file(),
        "wiki_body_graph_present": wiki_body_graph.is_file(),
        "raw_wiki_coverage_present": raw_wiki_coverage.is_file(),
        "wiki_index_extended_present": wiki_index_extended.is_file(),
    }
