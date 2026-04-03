# Wiki compile prompts (CRATE)

## Incremental compile plan

You are the **compile planner** for a CRATE vault.

**Given**

- `delta_raw_paths`: list of paths under `raw/` that changed.
- Excerpt of `wiki/_index/TOPICS.md` and titles of nearby concept pages.
- Policy: max `{max_new_pages}` new wiki files, max `{max_tokens}` output tokens, do not edit `raw/**`.

**Output JSON only**

```json
{
  "compile_run_id": "cr-YYYYMMDD-shortid",
  "touch_wiki_paths": ["wiki/concepts/foo.md", "..."],
  "read_raw_paths": ["raw/papers/bar.md"],
  "rationale": "short string"
}
```

Rules:

- Every new or heavily edited wiki page must cite `sources` pointing into `raw/` or URLs.
- Prefer updating existing `.md` over creating duplicate concept slugs.
- No writes outside `wiki/**` except allowed `meta/` reports if specified.

## Wikilink normalization

Given a markdown body that mixes `[[Concept Name]]` and `[Concept](wiki/concepts/foo.md)`, produce:

1. A single preferred style per project config (`wikilink` vs `markdown`).
2. A list of renamed links that would break, if any.
3. A minimal diff plan (file → change summary).

## Lint triage

Given a lint report (broken links, orphan pages), propose an ordered fix list:

- Deterministic fixes first (dead links, missing files).
- Then optional LLM passes for summary/raw alignment (flag high-cost items).

Do not execute shell commands; output instructions only.
