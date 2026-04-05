# CRATE

**Compile Raw Archives, Tracked in the vault, into Encyclopedic wiki.**

**Language:** **English** | [Chinese version](README.zh.md)

CRATE is a **file-first personal knowledge compiler**: ingest messy **raw** captures (notes, papers, clips, repos), keep provenance in your **vault**, and iteratively **compile** them into a navigable **wiki**—with lightweight retrieval, linting, and optional feedback loops back into compilation.

> 中文释义：**CRATE** = 把散落在各处的 **raw**，以 **vault** 为单一事实来源，**增量编译**成可互链的 **wiki**（百科全书式知识库）。

---

## Documentation

Linked docs below are **in Chinese** (for readability in this repo).

- **[docs/README.md](docs/README.md)** — documentation index
- **[docs/usage.md](docs/usage.md)** — CLI, vault layout, environment variables, workflows
- **[agent-skills/crate-vault/SKILL.md](agent-skills/crate-vault/SKILL.md)** — portable Agent Skill (Cursor, Claude Code, others); install paths in [docs/agent-skill.md](docs/agent-skill.md)
- **[docs/providers.md](docs/providers.md)** — multi-vendor LLM / embeddings (DeepSeek, OpenAI, Alibaba, Tencent, Volcengine, OpenRouter, Azure, etc.; `CRATE_LLM_PROVIDER`)
- **[docs/roadmap.md](docs/roadmap.md)** — roadmap and gaps (including incremental compile semantics)
- **[docs/obsidian.md](docs/obsidian.md)** — using Obsidian with the vault (vault root, day-to-day flow)
- **[docs/PRD.md](docs/PRD.md)** — product requirements and milestones
- **[docs/technical-design.md](docs/technical-design.md)** — architecture, vault layout, compile / Q&A / lint

---

## Why CRATE

- **Local-first**: Markdown trees, not a black-box SaaS library.
- **Incremental**: Short-lived wiki passes; re-run compilation as sources change.
- **Inspectable**: Diff-friendly outputs (wiki pages, slides, figures) you can review like code.
- **Agent-ready**: Room for a QA/RAG layer that reads *relevant pages* instead of dumping the whole corpus into context.

Design inspiration comes from the idea of treating an LLM as a **compiler** over your own materials—not a one-shot chat endpoint. Karpathy’s **LLM Wiki** pattern is published as a [GitHub Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f); an [X thread](https://x.com/karpathy/status/2039805659525644595) discussed the same ideas earlier. A **feature-by-feature mapping** to that workflow is in [docs/usage.md §7.5 Karpathy-style comparison](docs/usage.md#karpathy-style-comparison); a repo copy of the article is [docs/llm-wiki.md](docs/llm-wiki.md).

---

## What’s in scope

| Stage        | Intent |
|-------------|--------|
| **Raw ingest** | Web clipper, repo snapshots, PDFs, images—anything that enters the pipeline. |
| **Vault**      | Versioned, observable store: raw + compiled artifacts share one traceable home. |
| **Wiki compile** | LLM-driven structuring: summaries, concepts, backlinks, directory tree. |
| **Outputs**    | Markdown, optional Marp/deck exports, small charts—whatever you treat as “release artifacts”. |
| **Health / lint** | Consistency checks, gaps, new terms, optional “wiki checkup” passes. |
| **Enrich loop** | Feed outputs or lint findings back into the compiler for the next pass. |

## Non-goals (for now)

- Replacing a full-featured PKM app (e.g. calendar, tasks, spaced repetition).
- A hosted multi-tenant cloud—CRATE is oriented around **your** vault and **your** toolchain.

---

## Repository layout

```
crate/
├── README.md
├── README.zh.md          # Chinese README
├── pyproject.toml
├── environment.yml        # optional Conda env (Anaconda / Miniconda)
├── docs/                  # PRD, technical design (see docs/README.md)
├── prompts/               # Prompt templates for compile / architecture / codegen
├── scripts/               # Automation (e.g. optional AI PR review)
├── src/crate/             # Python package
├── tests/
├── .cursor/rules/         # Cursor agent guidance
├── .vscode/               # optional Conda path & interpreter hints
├── .devcontainer/         # Optional VS Code Dev Container
└── .github/               # CI, issue/PR templates, optional AI review workflow
```

Example **vault** trees (user data, often outside this repo) are described in [docs/technical-design.md](docs/technical-design.md).

---

## Getting started

### Conda (default Anaconda install path)

If you use Anaconda and `conda` lives at `/opt/anaconda3/condabin/conda`, you can create a **`crate`** environment from [`environment.yml`](environment.yml) (Python 3.11, editable `[dev]` install):

```bash
git clone https://github.com/GuiminChen/crate.git
cd crate
/opt/anaconda3/condabin/conda env create -f environment.yml   # first time
# or refresh deps later: /opt/anaconda3/condabin/conda env update -f environment.yml

conda activate crate
pre-commit install
pytest -q
```

[`.vscode/settings.json`](.vscode/settings.json) in this repo is set to that `conda` binary and interpreter `/opt/anaconda3/envs/crate/bin/python` so Cursor/VS Code match the activated env. If your paths differ, edit them locally or pick the interpreter in the command palette.

### venv / system Python (3.9+; Dev Container uses 3.11)

```bash
git clone https://github.com/GuiminChen/crate.git
cd crate
python3 -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
pre-commit install
pytest -q
```

### Dev Container

Open the repo in VS Code and select “Reopen in Container” to use [`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json) (Python 3.11, editable install, pre-commit).

### CLI (M0)

After `pip install -e ".[dev]"`, the `crate` command is available:

```bash
crate init [--vault PATH]           # create raw/wiki/meta tree (default vault = cwd)
crate compile [--vault PATH] [--full|--no-incremental] [--wiki-graph]  # raw/**/*.md + **/*.pdf; default incremental
crate ingest [--vault PATH]         # .crate/ingest_session.md → explicit raw subset compile (bypasses incremental skip)
crate watch [--vault PATH] [--debounce-seconds SEC] [--wiki-graph]   # poll raw/; auto compile after quiet period
crate serve-search [--vault PATH] [--port N]              # HTTP GET /search?q=... (JSON; &semantic=1 after crate index)
crate lint [--vault PATH] [--json] [--wikilinks] [--raw] [--http-external]  # wiki/; optional HTTP reachability for external URLs
crate wiki graph [--vault PATH]     # meta/wiki_body_graph.json + optional wiki/_index/BODYGRAPH.md
crate report raw-wiki [--vault PATH]   # meta/raw_wiki_coverage.json (raw → wiki coverage heuristic)
crate wiki index-extend [--vault PATH] # meta/wiki_index_extended.json (wiki/notes/ titles)
```

`compile`, `ask`, and `wiki-check` use an **OpenAI-compatible** chat client. Default provider is still **DeepSeek** when its key is set; switch platforms with `CRATE_LLM_PROVIDER` and the per-vendor variables in **[docs/providers.md](docs/providers.md)**.

**M1 — Q&A and feedback**

```bash
crate ask [--vault PATH] [--no-feedback] What is in TOPICS?
```

`ask` runs a tool loop (`vault_read`, `vault_search`, `vault_search_semantic`, `vault_write_output`) using the **same chat API configuration** as `compile`, writes the answer under `wiki/outputs/`, and by default appends one line to `wiki/_index/RECENT.md` (disable with `--no-feedback`). Use `--session <id>` after `crate ephemeral init` to allow drafts under `wiki/_ephemeral/<id>/`.

**M2 — Search, stats, semantic index**

```bash
crate search [--vault PATH] [--json] [--max-hits N] [--semantic] <words...>
crate stats [--vault PATH] [--json] [--strict] [--exclude-outputs]   # --json includes readiness (like serve-search /health)
crate doctor [--vault PATH] [--json] [--strict]   # crate_version, dirs, meta artifacts, readiness
crate index [--vault PATH] [--reset]   # needs CRATE_EMBEDDING_API_KEY or OPENAI_API_KEY
```

`compile` / `ask` print scale-gate hints to stderr unless `--quiet-gate`. Semantic search needs `crate index` first.

**M3 — Ephemeral question wiki**

```bash
crate ephemeral init [--vault PATH]                    # prints new session id
crate ask [--session ID] ...                           # can write under wiki/_ephemeral/ID/
crate ephemeral finalize <session_id> [--vault PATH] [--delete]
crate ephemeral clean [--vault PATH] --older-than DAYS
```

### Optional AI PR review

The workflow [`.github/workflows/ai-code-review.yml`](.github/workflows/ai-code-review.yml) runs only when repository secret `OPENAI_API_KEY` is set. Override model with `OPENAI_REVIEW_MODEL` if needed.

---

## Roadmap (aligned with docs/PRD.md)

| Phase | Focus |
|-------|--------|
| **M0** | Vault contract + manual compile proof-of-concept + minimal lint |
| **M1** | Q&A agent + file outputs + feedback (`crate ask`, `wiki/outputs`, `RECENT.md`) |
| **M2** | `crate search`, `stats`, `index`, semantic tool + env-gated embeddings |
| **M3** | `crate ephemeral` + `ask --session` + finalize/clean |

Adjust priorities via Issues.

---

## Contributing

Open a PR using the template, or start with an Issue describing:

- Use case (what raw → what wiki shape you want),
- Constraint (local-only, model X, vault tool Y),
- Acceptance idea (how you’d know the compile pass succeeded).

---

## License

**Apache-2.0**.

---

## Etymology

The name **CRATE** expands to:

- **C**ompile
- **R**aw
- **A**rchives
- **T**racked in the **vault**
- **E**ncyclopedic wiki

This matches the tagline at the top: *Compile Raw Archives, Tracked in the vault, into Encyclopedic wiki.*
