"""Raw material storage: local filesystem, shared mount, or COS-compatible stub."""

from __future__ import annotations

import hashlib
import os
from enum import Enum
from pathlib import Path
from typing import Any, List, Protocol, runtime_checkable

__all__ = [
    "RawBlobBackend",
    "RawBlobStore",
    "FilesystemRawBlobStore",
    "CosStubRawBlobStore",
    "CodStubRawBlobStore",
    "build_raw_blob_store",
]


def _norm_key(key: str) -> str:
    k = (key or "").strip().replace("\\", "/").lstrip("/")
    if ".." in k.split("/"):
        raise ValueError("invalid blob key")
    return k


@runtime_checkable
class RawBlobStore(Protocol):
    """Store arbitrary bytes under ``(tenant_id, logical_key)``."""

    def put(self, tenant_id: str, key: str, data: bytes) -> str:
        """Write bytes; return content digest for etag-style stamping."""

    def get(self, tenant_id: str, key: str) -> bytes | None:
        ...

    def exists(self, tenant_id: str, key: str) -> bool:
        ...

    def delete(self, tenant_id: str, key: str) -> None:
        """Remove object if present (no error if missing)."""

    def list_keys(self, tenant_id: str, prefix: str = "") -> List[str]:
        """Return logical keys under tenant, optional key prefix (posix path)."""


class RawBlobBackend(str, Enum):
    local = "local"
    shared_mount = "shared_mount"
    tencent_cos = "tencent_cos"


class FilesystemRawBlobStore:
    """Local or NFS-style mount: ``root / tenant_id / key`` on disk."""

    def __init__(self, root: Path, *, backend_tag: str = "local") -> None:
        self._root = Path(root).expanduser().resolve()
        self.backend_tag = backend_tag

    @property
    def root(self) -> Path:
        return self._root

    def _abs(self, tenant_id: str, key: str) -> Path:
        tid = (tenant_id or "").strip()
        if not tid:
            raise ValueError("tenant_id required")
        rel = Path(_norm_key(key))
        path = (self._root / tid / rel).resolve()
        try:
            path.relative_to(self._root)
        except ValueError as e:
            raise ValueError("path escapes blob root") from e
        return path

    def put(self, tenant_id: str, key: str, data: bytes) -> str:
        path = self._abs(tenant_id, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
        return hashlib.sha256(data).hexdigest()

    def get(self, tenant_id: str, key: str) -> bytes | None:
        path = self._abs(tenant_id, key)
        if not path.is_file():
            return None
        return path.read_bytes()

    def exists(self, tenant_id: str, key: str) -> bool:
        return self._abs(tenant_id, key).is_file()

    def delete(self, tenant_id: str, key: str) -> None:
        path = self._abs(tenant_id, key)
        try:
            path.unlink(missing_ok=True)
        except TypeError:
            if path.is_file():
                path.unlink()

    def list_keys(self, tenant_id: str, prefix: str = "") -> List[str]:
        tid = (tenant_id or "").strip()
        base = self._root / tid
        pref = _norm_key(prefix) if prefix else ""
        if not base.is_dir():
            return []
        out: List[str] = []
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(base).as_posix()
            if pref and not rel.startswith(pref):
                continue
            out.append(rel)
        return out


class CosStubRawBlobStore:
    """Tencent COS placeholder: persists under *staging* for dev/tests.

    Production can swap for ``qcloud_cos`` without changing the protocol.
    """

    def __init__(self, staging_root: Path) -> None:
        self._fs = FilesystemRawBlobStore(
            Path(staging_root).resolve(), backend_tag="tencent_cos_stub"
        )

    def put(self, tenant_id: str, key: str, data: bytes) -> str:
        return self._fs.put(tenant_id, key, data)

    def get(self, tenant_id: str, key: str) -> bytes | None:
        return self._fs.get(tenant_id, key)

    def exists(self, tenant_id: str, key: str) -> bool:
        return self._fs.exists(tenant_id, key)

    def delete(self, tenant_id: str, key: str) -> None:
        self._fs.delete(tenant_id, key)

    def list_keys(self, tenant_id: str, prefix: str = "") -> List[str]:
        return self._fs.list_keys(tenant_id, prefix=prefix)


CodStubRawBlobStore = CosStubRawBlobStore


def build_raw_blob_store(
    backend: RawBlobBackend | str,
    *,
    base_path: Path | None = None,
    cos_staging_path: Path | None = None,
    **_: Any,
) -> RawBlobStore:
    """Factory for :class:`RawBlobStore` implementations."""

    be = RawBlobBackend(backend) if isinstance(backend, str) else backend
    if be in (RawBlobBackend.local, RawBlobBackend.shared_mount):
        if base_path is None:
            raise ValueError("base_path required for local/shared_mount blob backend")
        tag = "local" if be == RawBlobBackend.local else "shared_mount"
        return FilesystemRawBlobStore(Path(base_path), backend_tag=tag)
    if be == RawBlobBackend.tencent_cos:
        if cos_staging_path is None:
            raise ValueError("cos_staging_path required for tencent_cos stub backend")
        return CosStubRawBlobStore(Path(cos_staging_path))
    raise ValueError(f"unsupported blob backend: {be}")
