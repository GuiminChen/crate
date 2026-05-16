"""Sync raw blob objects into a vault ``raw/`` tree for legacy compile paths."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from crate.stores.raw_blob import RawBlobStore
from crate.vault_paths import VaultContext, VaultPathError

__all__ = ["materialize_raw_blobs_to_vault"]


def materialize_raw_blobs_to_vault(
    blobs: RawBlobStore,
    tenant_id: str,
    keys: Iterable[str],
    ctx: VaultContext,
) -> List[Path]:
    """Write each blob into ``ctx.raw_dir()`` preserving relative paths.

    Returns absolute paths under the vault that were written.
    """

    raw_base = ctx.raw_dir()
    raw_base.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for key in keys:
        data = blobs.get(tenant_id, key)
        if data is None:
            continue
        dest = raw_base / Path(key)
        try:
            ctx.validate_under_vault(dest)
        except VaultPathError:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(dest)
        written.append(dest)
    return written
