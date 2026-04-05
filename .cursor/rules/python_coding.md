# Python coding standards (CRATE)

## Import order

1. Standard library
2. Third-party packages
3. Local `crate` modules

Separate groups with one blank line.

## Type annotations

Use Python 3.11+ syntax; annotate all public functions and methods. Prefer explicit return types.

```python
def process_task(task: Task) -> ProcessResult:
    """Process a single compile or lint task."""
    ...
```

## Error handling

- Catch specific exceptions; log with context; re-raise or wrap with domain errors.
- Use timeouts on network I/O.
- Do not use bare `except:`.

## Logging

Use structured logging:

```python
import structlog

logger = structlog.get_logger(__name__)
logger.info("compile_started", run_id=run_id, paths=len(paths))
```

## Tests

- Framework: `pytest`, `pytest-asyncio` for async code.
- Files: `tests/test_<module>.py`; functions: `test_<behavior>`.
- Mock external I/O and LLM clients in unit tests.

## Configuration

- Prefer typed settings (e.g. Pydantic models) loaded from env with `.env` locally (never committed).
- Validate configuration at startup.
- Chat and embedding endpoints are **OpenAI-compatible**; env naming varies by vendor — follow [docs/providers.md](../../docs/providers.md) and existing `src/crate/llm.py` / `embedding_config.py` patterns instead of hard-coding one provider.
