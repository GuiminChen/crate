# Code generation prompts (CRATE)

## New class

Create a Python class `{class_name}` for CRATE.

**Responsibility**: `{responsibility}`

**Requirements**

- Python 3.11+ with full type annotations.
- Pydantic v2 where structured data crosses boundaries.
- Async for I/O-bound work; structured logging via `structlog`.
- Google-style docstrings for public methods.
- No secrets in code or logs; vault paths validated against root.

**Style**: black / isort (line length 88), tests with pytest.

**Skeleton**

```python
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class {class_name}(BaseModel):
    """TODO: one-line summary."""

    id: str = Field(..., description="Stable identifier")

    async def primary_method(self) -> None:
        """TODO: describe behavior and raises."""
        logger.info("{class_name}_start", id=self.id)
```

## New tests

Generate pytest tests for:

```python
{paste_code}
```

Cover success and failure cases; mock LLM and filesystem where needed; keep tests fast.
