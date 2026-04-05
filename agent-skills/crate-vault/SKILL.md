---
name: crate-vault
description: >-
  Operate a CRATE knowledge vault: raw/, wiki/, meta/, compile, ask, lint,
  wiki-graph, reports, and safe wiki-check apply. Use when editing or
  automating a CRATE vault, running crate CLI, or interpreting meta/*.json.
---

# CRATE vault agent skill

## What CRATE is

CRATE is a **local-first** toolchain: **`raw/`** holds sources; **`wiki/`** holds compiled Markdown; **`meta/`** holds fingerprints, embeddings DB, and JSON indexes. The CLI is `crate` (see repo `docs/usage.md`).

## Read first

- **`AGENTS.md`** at vault root (if present): project-specific rules.
- **`docs/usage.md`** in the crate repo: full command reference.
- **`docs/providers.md`**: multi-vendor LLM + embedding (`CRATE_LLM_PROVIDER`, OpenAI-compatible APIs).
- **`meta/wiki_index.json`**: multi-page wiki graph from `crate compile --wiki-graph`.
- **`meta/wiki_body_graph.json`**: prose link graph from `crate wiki graph`.
- **`meta/raw_wiki_coverage.json`**: optional; from `crate report raw-wiki --write`.

## Safe defaults

- Do **not** bulk-overwrite user wiki pages unless the user asked.
- **`crate wiki-check --apply`** only merges **whitelist** fields on concept pages (`related_slugs` / `conflicts_with_slugs` per server implementation); never treat model output as permission to erase bodies.
- Prefer **`crate wiki promote`** to move a vetted answer from **`wiki/outputs/`** into **`wiki/concepts/`**.

## Command map

| Goal | Command |
|------|---------|
| Compile raw → wiki note or multi-page wiki | `crate compile` / `crate compile --wiki-graph` |
| Watch `raw/` | `crate watch` (optional `--native` with watchdog) |
| Q&A | `crate ask` / `crate ask-multi` |
| Deterministic link checks | `crate lint` (add `--wikilinks`, `--orphans`, `--strict-concepts` as needed) |
| Prose link graph JSON | `crate wiki graph` (`--md` for `wiki/_index/BODYGRAPH.md`) |
| Raw coverage report | `crate report raw-wiki` (`--write` for JSON under `meta/`) |
| Session-scoped compile | List paths in `.crate/ingest_session.md` then `crate ingest` |
| Extended notes index | `crate wiki index-extend` → `meta/wiki_index_extended.json` |
| Semantic wiki audit | `crate wiki-check` (optional `--apply-dry-run` / `--apply`) |
| HTTP URL check (opt-in) | `crate lint --http-external` (set `SKIP_HTTP_LINT=1` to skip) |
| Diagnostics | `crate doctor` |

## Install locations (any agent host)

See **`docs/agent-skill.md`** in the crate repository for Cursor, Claude Code, OpenClaw, and generic “paste this file into instructions” workflows.
