# Testing requirements

## Mandatory for implementation work

1. **Every feature or meaningful code change** must include updates to **unit tests** under `tests/` (new `test_*.py` or extending existing tests).
2. **Cover behavior, not only happy path** where risk warrants: edge cases, error paths, and regressions for fixed bugs.
3. **Representative data**: use small fixtures, tmp paths, or factory helpers in `tests/` when behavior depends on vault layout or file content (keep samples minimal and documented).
4. **Before claiming work is complete** (or opening a PR): run **`pytest`** on the affected suite at minimum, ideally the full project **`pytest -q`** (or `pytest tests/`), and ensure it **passes**. Do not finish with failing or skipped tests without explicit agreement.
5. **CLI / integration** logic that is hard to unit-test in isolation should still have: thin unit tests for pure functions, and/or focused tests using `tmp_path` / subprocess with a tiny vault fixture.

## Workflow

- Prefer writing or updating the test that demonstrates the bug or new contract **before or alongside** the implementation change.
- After refactors, run the full test suite to catch accidental breakage.

## References

- Project pytest config: [pyproject.toml](../../pyproject.toml) (`[tool.pytest.ini_options]`)
