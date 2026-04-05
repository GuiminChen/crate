"""Tests for incremental compile raw selection (``select_paths_for_compile``)."""

from pathlib import Path

from crate.compile_state import select_paths_for_compile


def _paths(root: Path, *rels: str) -> list[Path]:
    return [root / r for r in rels]


def test_full_always_returns_all_current(tmp_path: Path) -> None:
    root = tmp_path
    a = root / "raw" / "a.md"
    a.parent.mkdir(parents=True)
    a.write_text("x", encoding="utf-8")
    current = _paths(root, "raw/a.md")
    stored = {}
    paths, skipped = select_paths_for_compile(
        root, current, stored, full=True, has_valid_state=True
    )
    assert skipped is False
    assert paths is not None and len(paths) == 1


def test_no_change_skips(tmp_path: Path) -> None:
    root = tmp_path
    p = root / "raw" / "a.md"
    p.parent.mkdir(parents=True)
    p.write_text("same", encoding="utf-8")
    from crate.compile_state import fingerprints_for_paths

    current = [p]
    stored = fingerprints_for_paths(current, root)
    paths, skipped = select_paths_for_compile(
        root, current, stored, full=False, has_valid_state=True
    )
    assert skipped is True
    assert paths is None


def test_removed_raw_triggers_full_current_set(tmp_path: Path) -> None:
    """Deleting tracked raw forces compile with all remaining files (roadmap §7)."""
    root = tmp_path
    raw = root / "raw"
    raw.mkdir(parents=True)
    a = raw / "a.md"
    b = raw / "b.md"
    a.write_text("a", encoding="utf-8")
    b.write_text("b", encoding="utf-8")
    from crate.compile_state import fingerprints_for_paths

    both = [a, b]
    stored = fingerprints_for_paths(both, root)
    only_a = [a]
    paths, skipped = select_paths_for_compile(
        root, only_a, stored, full=False, has_valid_state=True
    )
    assert skipped is False
    assert paths is not None
    assert len(paths) == 1
    assert paths[0].name == "a.md"


def test_added_file_subset_only_new(tmp_path: Path) -> None:
    root = tmp_path
    raw = root / "raw"
    raw.mkdir(parents=True)
    a = raw / "a.md"
    a.write_text("a", encoding="utf-8")
    from crate.compile_state import fingerprints_for_paths

    stored = fingerprints_for_paths([a], root)
    b = raw / "b.md"
    b.write_text("b", encoding="utf-8")
    current = [a, b]
    paths, skipped = select_paths_for_compile(
        root, current, stored, full=False, has_valid_state=True
    )
    assert skipped is False
    assert paths is not None
    assert len(paths) == 1
    assert paths[0].name == "b.md"
