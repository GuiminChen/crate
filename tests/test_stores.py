"""Tests for multi-tenant blob + wiki DB stores."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from crate.stores.raw_blob import (
    FilesystemRawBlobStore,
    RawBlobBackend,
    build_raw_blob_store,
)
from crate.stores.wiki_database import SqliteWikiDatabase, WikiPageRecord, build_wiki_database


def test_filesystem_blob_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        fs = FilesystemRawBlobStore(Path(tmp))
        fs.put("t1", "raw/a.md", b"hello")
        assert fs.get("t1", "raw/a.md") == b"hello"
        assert "raw/a.md" in fs.list_keys("t1")


def test_build_raw_blob_local() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        b = build_raw_blob_store(RawBlobBackend.local, base_path=Path(tmp))
        b.put("x", "k.txt", b"x")
        assert b.exists("x", "k.txt")


def test_sqlite_wiki_tenant_isolation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "w.sqlite"
        db = SqliteWikiDatabase(path)
        now = "2020-01-01T00:00:00+00:00"
        db.upsert_page(
            WikiPageRecord(
                tenant_id="a",
                logical_path="p1",
                body_md="alpha wolf",
                content_sha256="x",
                updated_at=now,
            )
        )
        db.upsert_page(
            WikiPageRecord(
                tenant_id="b",
                logical_path="p1",
                body_md="beta wolf",
                content_sha256="y",
                updated_at=now,
            )
        )
        hits_a = db.search_literals("a", "wolf", limit=5)
        assert len(hits_a) == 1 and hits_a[0].tenant_id == "a"
        hits_b = db.search_literals("b", "wolf", limit=5)
        assert hits_b[0].body_md == "beta wolf"


def test_build_wiki_database_sqlite() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "x.sqlite"
        wdb = build_wiki_database("sqlite", sqlite_path=p)
        assert isinstance(wdb, SqliteWikiDatabase)
