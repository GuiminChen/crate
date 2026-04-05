# Vault, markdown, and safety rules

## Directory contract

- **`raw/`**: Original captures (notes, papers, clips, images). Do not let the compile/QA pipeline overwrite source files unless an explicit, documented exception exists.
- **`wiki/`**: Compiled Markdown graph: concepts, notes, `_index` topic pages, `outputs/` for Q&A artifacts.
- **`meta/`** (optional): Build state and machine-readable artifacts (`compile_state.json`, `wiki_index.json`, `wiki_body_graph.json`, `raw_wiki_coverage.json`, `wiki_index_extended.json`, embeddings DB, lint reports, etc.); see [docs/usage.md](../../docs/usage.md).

## Front matter

- Wiki pages should declare provenance: `sources` pointing at paths under `raw/` or source URLs.
- Output pages should include `kind`, `source_query`, `created` (ISO 8601), and optional model metadata.
- Use YAML front matter consistent with [docs/technical-design.md](../../docs/technical-design.md).

## Links

- Support Obsidian wikilinks `[[...]]` and standard Markdown links; normalize in compile tasks (pick one style as primary per vault policy).
- Lint must validate targets exist where checkable.
- **`crate lint --orphans`** treats some index/navigation pages as non-orphans by default (e.g. `wiki/_index/INDEX.md`, `TOPICS.md`, `RECENT.md`, `BACKLINKS.md`, `BODYGRAPH.md`, and all of `wiki/outputs/`); see CLI docs — do not “fix” those as false orphan reports.

## Path and execution safety

- Resolve paths with `canonicalize` / equivalent; reject any path outside the vault root (traversal-safe).
- Prefer **no arbitrary shell** from agents; allow only whitelisted CLIs (e.g. search wrapper).
- Never commit API keys or `.env`; never write secrets into `wiki/`.

## Atomic writes

- Write to `*.tmp` then rename; avoid half-written pages on failure.
- On failure, retain previous `compile_run_id` / rollback via Git.
