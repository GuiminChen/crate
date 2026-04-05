# Multi-page wiki compile (JSON output)

You receive excerpts from `raw/` (markdown and PDF text). Respond with **only** a single JSON object (no markdown outside JSON). Schema:

```json
{
  "version": 1,
  "synthesis_note": "optional short markdown overview for a compile run note",
  "topics_markdown": "markdown bullet list of main themes for TOPICS.md",
  "concepts": [
    {
      "slug": "lowercase-kebab-case",
      "title": "Human Title",
      "body": "markdown body with ## headings and optional [[other-slug]] links",
      "related_slugs": ["other-slug"],
      "sources": ["raw/papers/example.md"]
    }
  ]
}
```

Rules:

- `slug`: only `a-z`, `0-9`, `-`; ASCII; no `..` or `/`.
- `sources`: list vault-relative paths that appear in the input; may be empty.
- `concepts`: at least one entry when material exists; each `body` should be self-contained.
- Do not invent facts not supported by the excerpts.
- If excerpts are empty, use `"concepts": []` and a brief `synthesis_note` explaining no sources.
