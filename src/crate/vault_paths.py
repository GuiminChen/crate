"""Resolve and validate vault root paths (no traversal outside the vault)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

__all__ = ["VaultContext", "VaultPathError", "resolve_vault_root"]


class VaultPathError(ValueError):
    """Raised when a path escapes the vault or is invalid."""


def resolve_vault_root(cwd: Path, vault_arg: str | None) -> Path:
    """Return absolute, resolved vault root. ``vault_arg`` is relative to ``cwd`` if not absolute."""
    base = Path(vault_arg).expanduser() if vault_arg else cwd
    if not base.is_absolute():
        base = (cwd / base).resolve()
    else:
        base = base.resolve()
    return base


@dataclass(frozen=True)
class VaultContext:
    """All filesystem operations for one vault should use this root."""

    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root).resolve())

    def validate_under_vault(self, path: Path) -> Path:
        """Return resolved ``path`` if it lies under ``root``, else raise."""
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = (self.root / p).resolve()
        else:
            p = p.resolve()
        try:
            p.relative_to(self.root)
        except ValueError as e:
            raise VaultPathError(f"Path escapes vault: {path}") from e
        return p

    def raw_dir(self) -> Path:
        return self.root / "raw"

    def wiki_dir(self) -> Path:
        return self.root / "wiki"

    def meta_dir(self) -> Path:
        return self.root / "meta"


_DEFAULT_SENTINEL: Final[object] = object()


def default_cwd() -> Path:
    """Current working directory as an absolute path."""
    return Path(os.getcwd()).resolve()
