# Semantic wiki health check (JSON only)

You receive:

1. A JSON blob `wiki_index` from `meta/wiki_index.json` (version, `raw_sources`, `concepts` with slug, path, title, sources).
2. Short excerpts from a few concept pages (path + first ~1500 chars of body text after front matter).

Respond with **only** one JSON object (no markdown outside JSON):

```json
{
  "version": 1,
  "summary": "one sentence overview",
  "issues": [
    {
      "kind": "duplicate_concept|thin_evidence|orphan_raw|terminology|other",
      "detail": "human-readable explanation",
      "paths": ["optional/wiki/paths.md"]
    }
  ],
  "orphan_raw": ["raw/paths/not_in_any_concept_sources.md"],
  "notes": "optional extra notes"
}
```

Rules:

- Compare `wiki_index.concepts[].sources` to `wiki_index.raw_sources` and listed raw files; flag **orphan_raw** when a raw path appears unused or obviously disconnected (best-effort).
- Flag **duplicate_concept** when titles/slugs suggest the same topic split across pages.
- Do not invent file paths; only reference paths present in the input.
- If excerpts are empty, still return valid JSON with brief `summary` and empty arrays.
