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
      "conflicts_with_slugs": ["slug-that-contradicts"],
      "supersedes_slugs": ["older-slug"],
      "sources": ["raw/papers/example.md"]
    }
  ]
}
```

Optional fields:

- `conflicts_with_slugs`: other concept slugs whose claims conflict with this page (best-effort; only when supported by excerpts).
- `supersedes_slugs`: other concept slugs this page replaces or subsumes (best-effort).

Rules:

- `slug`: only `a-z`, `0-9`, `-`; ASCII; no `..` or `/`.
- `sources`: list vault-relative paths that appear in the input; may be empty.
- `concepts`: at least one entry when material exists; each `body` should be self-contained.
- Do not invent facts not supported by the excerpts.
- If excerpts are empty, use `"concepts": []` and a brief `synthesis_note` explaining no sources.
