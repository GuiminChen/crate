# CRATE architecture rules

## Agreed implementation phases (current focus)

| Phase | Scope (confirmed) |
|-------|-------------------|
| **M0** | Vault 约定 + **手工触发**编译 POC + **最小** Lint |
| **M1** | Agent 问答（`crate ask` + 工具读/搜/写 `wiki/outputs`）+ **回流**（默认追加 `RECENT.md`） — **已实现初版** |

**产品界面策略**：首期以 **CLI**（及可选 Cursor / 外部 Agent）为控制面；**阅读与导航**优先用 **Obsidian（或任意 Markdown 编辑器）** 打开 vault，**不**把 Web 前端作为 M0/M1 的必要交付。若后续需要管理台，再单独立项。

## System components

| Component          | Responsibility |
|--------------------|----------------|
| **IngestWatcher**  | Optional: watch `raw/` changes (debounced), enqueue compile jobs. |
| **CompileWorker**  | Incremental compile: summaries, concept pages, wikilinks, topic indices under `wiki/`. |
| **QA Agent**       | Question answering with tools: read vault, search, write outputs under allowed paths. |
| **LintWorker**     | Deterministic checks (broken links, orphans); optional LLM semantic passes. |
| **Search CLI**     | Optional: ripgrep/BM25 wrapper returning path, line, snippet as structured JSON. |

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

- Product scope: [docs/PRD.md](../../docs/PRD.md)
- Technical design: [docs/technical-design.md](../../docs/technical-design.md)
