"""Poll ``raw/`` and run ``compile`` after a debounced quiet period."""

from __future__ import annotations

import sys
import threading
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
    from crate.compile_run import collect_raw_sources
    from crate.compile_state import fingerprints_for_paths

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
    native_watch: bool = False,
    run_compile_fn: Callable[..., CompileResult] | None = None,
) -> None:
    """Block until Ctrl+C; after ``raw/`` changes, debounce then compile.

    Uses polling by default. With ``native_watch=True`` and **watchdog** installed,
    filesystem events wake the loop early (``pip install crate[watch]`` or
    ``pip install watchdog``).
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

    wake = threading.Event()
    observer = None
    if native_watch:
        try:
            from watchdog.events import FileSystemEventHandler
            from watchdog.observers import Observer

            class _RawHandler(FileSystemEventHandler):
                def on_any_event(self, event: object) -> None:
                    if getattr(event, "is_directory", False):
                        return
                    wake.set()

            raw_dir = ctx.raw_dir()
            if raw_dir.is_dir():
                observer = Observer()
                observer.schedule(_RawHandler(), str(raw_dir), recursive=True)
                observer.start()
                print(
                    "watch: using filesystem events (watchdog).",
                    file=sys.stderr,
                )
        except ImportError:
            print(
                "watch: watchdog not installed; use pip install watchdog "
                "or pip install 'crate[watch]'. Falling back to polling.",
                file=sys.stderr,
            )

    print(
        f"Watching raw/ under {ctx.root} (debounce={debounce_seconds}s). "
        "Ctrl+C to stop.",
        file=sys.stderr,
    )

    try:
        while True:
            if observer is not None:
                wake.wait(timeout=poll_interval)
                wake.clear()
            else:
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
    finally:
        if observer is not None:
            observer.stop()
            observer.join(timeout=3.0)
