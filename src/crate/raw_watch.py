"""Poll ``raw/`` and run ``compile`` after a debounced quiet period."""

from __future__ import annotations

import sys
import time
from typing import Callable

from crate.compile_run import CompileResult, run_compile
from crate.vault_paths import VaultContext
from crate.vault_stats import (
    GateConfig,
    collect_vault_stats,
    evaluate_gates,
    gate_message,
)

__all__ = ["run_watch_loop", "snapshot_raw_fingerprints"]


def snapshot_raw_fingerprints(ctx: VaultContext) -> dict[str, dict[str, str]]:
    """SHA-256 map for all files under ``raw/`` (same basis as compile state)."""
    from crate.compile_state import fingerprints_for_paths
    from crate.compile_run import collect_raw_sources

    paths = collect_raw_sources(ctx)
    return fingerprints_for_paths(paths, ctx.root)


def _maybe_print_gate(ctx: VaultContext, quiet: bool) -> None:
    if quiet:
        return
    stats = collect_vault_stats(ctx)
    reasons = evaluate_gates(stats, GateConfig.from_environ())
    if reasons:
        print(gate_message(reasons), file=sys.stderr)


def run_watch_loop(
    ctx: VaultContext,
    *,
    debounce_seconds: float = 3.0,
    poll_interval: float = 0.5,
    quiet_gate: bool = False,
    wiki_graph: bool = False,
    run_compile_fn: Callable[..., CompileResult] | None = None,
) -> None:
    """Block until Ctrl+C; after ``raw/`` changes, debounce then compile.

    Uses polling (no extra dependencies). ``run_compile_fn`` defaults to
    :func:`run_compile` and is injectable for tests.

    When ``wiki_graph`` is true (and no custom ``run_compile_fn``), calls
    ``run_compile(..., wiki_graph=True)`` for multi-page wiki output.
    """
    if run_compile_fn is not None:
        compile_fn = run_compile_fn
    elif wiki_graph:

        def compile_fn(c: VaultContext) -> CompileResult:
            return run_compile(c, wiki_graph=True)

    else:
        compile_fn = run_compile
    debounce_seconds = max(0.5, float(debounce_seconds))
    poll_interval = max(0.1, float(poll_interval))

    last_snapshot = snapshot_raw_fingerprints(ctx)
    last_compiled: dict[str, dict[str, str]] | None = None
    pending_since: float | None = None

    print(
        f"Watching raw/ under {ctx.root} (debounce={debounce_seconds}s). "
        "Ctrl+C to stop.",
        file=sys.stderr,
    )

    try:
        while True:
            time.sleep(poll_interval)
            snap = snapshot_raw_fingerprints(ctx)
            if snap != last_snapshot:
                last_snapshot = snap
                pending_since = time.time()
                continue
            if pending_since is None:
                continue
            if time.time() - pending_since < debounce_seconds:
                continue
            if snap == last_compiled:
                pending_since = None
                continue

            _maybe_print_gate(ctx, quiet_gate)
            try:
                result = compile_fn(ctx)
            except Exception as exc:  # noqa: BLE001
                print(f"watch: compile failed: {exc}", file=sys.stderr)
                pending_since = time.time()
                continue

            if result.skipped:
                print(
                    "watch: compile skipped (no effective raw change).",
                    file=sys.stderr,
                )
            else:
                assert result.output_path is not None
                print(
                    f"watch: compiled -> {result.output_path.relative_to(ctx.root)}",
                    file=sys.stderr,
                )
            last_compiled = snap
            pending_since = None
    except KeyboardInterrupt:
        print("watch: stopped.", file=sys.stderr)
