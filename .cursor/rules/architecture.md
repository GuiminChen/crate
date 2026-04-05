# CRATE architecture rules

## Agreed implementation phases (current focus)

| Phase | Scope (confirmed) |
|-------|-------------------|
| **M0** | Vault 约定 + **手工触发**编译 POC + **最小** Lint（含 `compile` 增量、`lint`、`watch` 等） |
| **M1** | Agent 问答（`crate ask` + 工具读/搜/写 `wiki/outputs`）+ **回流**（默认追加 `RECENT.md`） |
| **M2** | `crate search` / `stats` / `doctor` / `serve-search`；`crate index` + 语义检索；规模门闸 |
| **M3** | `crate ephemeral` + `ask --session` + finalize/clean |

**跨阶段能力（CLI 已落地，与 PRD §12 一致）**：多页 wiki（**`compile --wiki-graph`**，`meta/wiki_index.json`）；正文链接图（**`crate wiki graph`** → `meta/wiki_body_graph.json`）；raw→wiki 覆盖（**`crate report raw-wiki`**）；**`crate wiki index-extend`**；显式子集编译（**`crate ingest`** + `.crate/ingest_session.md`）；**`lint --orphans`**（导航页含 `BODYGRAPH.md` 等排除）；可选 **`lint --http-external`**。聊天与嵌入：**OpenAI 兼容** HTTPS 客户端；多平台密钥与变量见 [docs/providers.md](../../docs/providers.md)。

**产品界面策略**：首期以 **CLI**（及可选 Cursor / 外部 Agent）为控制面；**阅读与导航**优先用 **Obsidian（或任意 Markdown 编辑器）** 打开 vault，**不**把 Web 前端作为核心交付。可选 Obsidian 插件见 `docs/obsidian-plugin.md`。若后续需要管理台，再单独立项。

## System components

| Component          | Responsibility |
|--------------------|----------------|
| **IngestWatcher**  | Optional: watch `raw/` changes (debounced), enqueue compile jobs. |
| **CompileWorker**  | Incremental compile: summaries, concept pages, wikilinks, topic indices under `wiki/`. |
| **QA Agent**       | Question answering with tools: read vault, search, write outputs under allowed paths. |
| **LintWorker**     | Deterministic checks (broken links, orphans, optional HTTP on external URLs); optional LLM semantic passes (`wiki-check`). |
| **Search CLI**     | ripgrep/BM25 wrapper + optional semantic layer (`crate index` → `search --semantic`); HTTP `serve-search` for agents. |

## Data flow principles

- **Vault is source of truth**: Git-versioned tree; compilers and agents read/write under explicit path ACLs.
- **Two zones**: `raw/**` is immutable by the LLM by default; `wiki/**` is LLM-owned compiled surface.
- **Progressive retrieval**: Prefer index + targeted full reads; escalate to search/vectors when thresholds hit.
- **Idempotent runs**: Re-running compile on the same raw revision should converge; cap new pages and tokens per policy.

## Layering (conceptual)

```
CLI（及 Agent 运行时）作为入口
        → orchestration (jobs, budgets, run_id)
        → workers (compile, lint, search)
        → vault I/O (path canonicalization, atomic writes)
```

## References

- README: [README.md](../../README.md)（English）· [README.zh.md](../../README.zh.md)（简体中文）
- Product scope: [docs/PRD.md](../../docs/PRD.md)
- Technical design: [docs/technical-design.md](../../docs/technical-design.md)
- LLM / embedding config: [docs/providers.md](../../docs/providers.md)
- Vault agent hints: [AGENTS.md](../../AGENTS.md)
