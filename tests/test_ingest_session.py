"""ingest session parsing."""

from crate.ingest_session import parse_ingest_session_text


def test_parse_ingest_session_text() -> None:
    text = """
# comment
raw/a.md

raw/b.pdf
"""
    assert parse_ingest_session_text(text) == ["raw/a.md", "raw/b.pdf"]
