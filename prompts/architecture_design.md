# Architecture design prompts (CRATE)

## New module

You are designing a module for **CRATE**: a local-first pipeline that compiles `raw/` material into a linked `wiki/` with lint, optional search, and Q&A outputs.

**Principles**

1. Vault on disk is the source of truth; path ACLs separate `raw/**` from `wiki/**`.
2. Compiles should be incremental, idempotent, and budgeted (tokens, new pages).
3. Prefer plain Python services and explicit interfaces over implicit magic.

**Task**: Design a module named `{module_name}` that `{capability_description}`.

**Deliver**

1. Role in the system (ingest, compile, lint, search, QA orchestration, CLI).
2. Public interfaces (inputs/outputs, data shapes).
3. Failure modes and recovery (atomic writes, no half pages).
4. Extension points and what stays minimal in core.
5. Test outline (unit vs integration with a temp vault fixture).

## Data flow

Describe the data flow for `{feature_name}` in CRATE.

**Constraints**

- Reads and writes stay under a configurable vault root after canonicalization.
- LLM calls are behind explicit steps with logged `run_id` and token estimates where possible.
- Search and full-file reads are tools, not implicit “load everything” behavior.

**Output**

- Mermaid or bullet flow from trigger → workers → artifacts under `wiki/` or `meta/`.
