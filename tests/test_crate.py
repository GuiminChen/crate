"""Smoke tests for the crate package."""

import crate


def test_version() -> None:
    """Package exposes a semver string."""
    assert crate.__version__ == "0.1.0"
