# CRATE 路线图与待实现项

本文档汇总 [PRD.md](PRD.md)、[technical-design.md](technical-design.md) 与产品愿景中**尚未完成或仅部分实现**的能力，便于排期与对齐（例如与 Karpathy [LLM Wiki（Gist）](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 及 [X 知识库串](https://x.com/karpathy/status/2039805659525644595) 描述的「raw → 互联 wiki → 问答 → 回流」相比）。模式说明正文以 Gist 为准；仓库副本见 [llm-wiki.md](llm-wiki.md)；**与 CRATE 的逐条差距**见 PRD **§12**。

状态说明：**未开始** | **部分**（有 CLI/雏形） | **已有**

---

## 1. 数据入轨与监视

| 项 | PRD / 设计 | 状态 | 说明 |
|----|-------------|------|------|
| Raw 入轨（拖入/剪藏约定） | FR-02 | 部分 | 用户自管 `raw/`；无专用剪藏工具 |
| 入轨监视（`raw/` 变更防抖触发编译） | V1 自动编译 | **部分** | **`crate watch`**（可选 **`--wiki-graph`**）：默认轮询 + 防抖；安装 **`watchdog`** 时可用 **`--native`**（FSEvents/inotify 类） |
| 图片与相对路径规范校验 | FR-02 | **部分** | **`crate lint`** / **`lint --raw`**：**`![](path)`** 缺失时 **`broken_image`**；**`crate doctor`** 快速看目录与索引就绪 |

---

## 2. 编译形态（wiki）

| 项 | PRD / 设计 | 状态 | 说明 |
|----|-------------|------|------|
| 增量编译（仅变更 raw） | FR-03 | **部分** | `crate compile` 默认增量；`--full` / `--no-incremental` 全量；指纹为 **SHA-256**（`meta/compile_state.json` v2） |
| 互联 wiki：概念页、backlinks、主题分层 | MVP 编译 | **部分** | **`crate compile --wiki-graph`**：概念 YAML 含 **`related_slugs`**、可选 **`conflicts_with_slugs`** / **`supersedes_slugs`**；**`BACKLINKS.md`**、**`CATALOG.md`**；正文链接图：**`crate wiki graph`** → **`meta/wiki_body_graph.json`** / 可选 **`BODYGRAPH.md`**（与 BACKLINKS 的 YAML 边互补） |
| 全库索引页（`INDEX.md` / TOPICS 机器可依赖） | FR-04 | **已有** | **`wiki/_index/INDEX.md`**（**`compile --wiki-graph`** 更新）；**`meta/wiki_index.json`**；**`TOPICS.md`** 可由 **`topics_markdown`** 同步；分层主题树仍可由你手工维护 |
| 编译幂等、原子写 | technical-design | **已有** | 主要 Markdown 产出（**`compile`**、**`compile --wiki-graph`**、**`wiki normalize`** 等）先写 **`*.md.tmp`** 再 **`os.replace`** |

---

## 3. 问答与检索

| 项 | PRD / 设计 | 状态 | 说明 |
|----|-------------|------|------|
| Agent 问答 + 工具读/搜/写 | FR-05, FR-06 | 已有 | `crate ask` |
| 朴素搜索 CLI | FR-09 | 已有 | `crate search` |
| 向量 / 语义检索 | V1 检索分层 | 已有 | `crate index` + `search --semantic` |
| 朴素搜索 HTTP 服务 | V1 | **已有** | **`crate serve-search`**：**`/search`**（字面量 / **`semantic=1`**）；**`/health`** 返回 **vault**、**`semantic_ready`**、**`multi_page_wiki_index`** 等 |
| 规模门闸 | FR-10 | 已有 | **`crate stats`** / **`--strict`** / **`--gates-json`**；**`--json`** 另含 **`readiness`**（与 **`serve-search`** **`/health`** 同字段，便于无 HTTP 探测） |
| 环境自检（无 LLM） | — | **已有** | **`crate doctor`**：**`crate_version`**、**`dirs`**、**`compile_state` / `compile_wiki_last`**、**`semantic_wiki_report`**、**`embeddings_sqlite`**、**`wiki_body_graph` / `raw_wiki_coverage` / `wiki_index_extended`** 文件标记、**`readiness`**；**`--strict`** 缺标准目录时退出 **1** |

---

## 4. Lint 与健康检查

| 项 | PRD / 设计 | 状态 | 说明 |
|----|-------------|------|------|
| 断链检查 | FR-08 | **部分** | **`crate lint`**：**`wiki/`**；**`--raw`** 时含 **`raw/`**；相对 **`[](path)`** / **`![](path)`**；**`--wikilinks`**；**`--orphans`**（入链图上的 **wiki 孤立页**）；**`--http-external`**（外链 HTTP 抽检；**`SKIP_HTTP_LINT`**）；**`duplicate_heading`**（可 **`--no-duplicate-headings`**）；raw↔wiki 语义对齐仍靠编译、**`report raw-wiki`** 与 **`wiki-check`** |
| LLM 语义巡检、孤立 raw、摘要冲突 | FR-08 | **部分** | **`crate wiki-check`**：JSON 报告；可选 **`--apply-dry-run`** / **`--apply`**（**仅白名单**合并 `wiki/concepts/*.md` 内 `related_slugs` / `conflicts_with_slugs`）；复杂语义仍靠人工 |
| Obsidian wikilink 与标准链接互转 | PRD 6.5 | **部分** | **`crate lint --wikilinks`** 校验；**`crate wiki normalize`** 批量 **`--to-md-links` / `--to-wikilinks`** |

---

## 5. 产出形态

| 项 | PRD / 设计 | 状态 | 说明 |
|----|-------------|------|------|
| Markdown 输出 | FR-06 | 已有 | `wiki/outputs/` 等 |
| Marp / 幻灯 | V1 可视化 | **部分** | **`crate marp`**：本机 Marp CLI；PDF 默认 **`wiki/outputs/marp-pdf/`** |
| matplotlib 等图 | 愿景 | **部分** | **`crate wiki figures-init`** → **`wiki/outputs/figures/`**，脚本由用户本地执行 |

---

## 6. 工程化与其它

| 项 | PRD / 设计 | 状态 | 说明 |
|----|-------------|------|------|
| 回流与 front-matter | FR-07 | **部分** | **`RECENT.md`**、**`LOG.md`**（可选标题行格式 **`CRATE_LOG_MARKDOWN_HEADINGS`**）；**`crate wiki promote`** 将 **`wiki/outputs/`** 显式提升为 **`wiki/concepts/`**；详见 [usage.md](usage.md) |
| Token 预算 / 模型路由 | FR-11 | **部分** | [usage.md](usage.md) **§3.1** 矩阵；**`CRATE_COMPILE_MAX_CHARS_PER_FILE`**；**`CRATE_MODEL_*`**；**`CRATE_MAX_OUTPUT_TOKENS*`**；**`CRATE_MAX_INPUT_CHARS*`** |
| 短命 wiki 编排、多 Agent | V2 / Karpathy 二推 | **部分** | **`ephemeral` + `ask --session`**；**`crate ask-multi`**（规划 JSON + `ask` 工具循环）；深度多角色编排仍可增强 |
| 显式 ingest、CI、Agent Skill、Obsidian 插件 | — | **部分** | **`crate ingest`**（**`.crate/ingest_session.md`**）；[ci.md](ci.md) workflow 模板；[agent-skills/crate-vault/SKILL.md](../agent-skills/crate-vault/SKILL.md)；[obsidian-plugin/](../obsidian-plugin/crate/) |
| 合成数据 + 微调 | Karpathy 展望 | 未开始 | 非本期 |

---

## 7. 已知语义边界（增量编译）

- 默认仅把**本轮判定为变更的** raw 发给模型；**不**保证与「全库一次性综述」等价。
- 删除 raw 文件时，当前实现会**用剩余全部 raw** 作为编译输入以刷新综述（见实现说明）。
- 需要与 Karpathy 式「全库互联 wiki」对齐时，仍依赖后续 **多页 wiki 维护**与 **`--full` / `--no-incremental`** 等组合策略。

更多操作说明见 [usage.md](usage.md)。

---

## 8. 社区实践参考（Karpathy [LLM Wiki Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 讨论）

以下为 Gist **评论区**中多次出现的实践总结，供产品/文档对照；**不是** Karpathy 正文承诺，也**不**表示 CRATE 已完整实现。

| 实践要点 | 社区在说什么 | 与 CRATE 的关系 |
|----------|----------------|-----------------|
| **先分类再抽取** | 报告 / 信函 / 转录等类型不同，抽取与摘要策略宜分类型，避免「一刀切」浅摘要 | **未内置**文档类型路由；可在 **`raw/`** 下用子目录与提示词自行区分；若需可列为后续「ingest 策略」 |
| **索引分档（token 预算）** | 从项目上下文 → 索引 → 检索结果 → 全文，逐级展开，避免一上来读满全文 | 与 **`crate stats`** 门闸、**`ask`** 工具读页、语义检索分层**方向一致**；**未**内置固定 L0–L3 档位 |
| **实体分模板** | 人物页 / 事件页 / 文献摘要等区块结构不同，在 schema 里约定 | 概念页 **YAML** 可扩展；**未**强制「每类实体」模板；可由 **`AGENTS.md`** / 提示词约定 |
| **双产出** | 每次任务：用户要的答案 + 同步更新相关 wiki 页，避免知识蒸发在聊天里 | **`ask`** 落盘 **`wiki/outputs/`**；**`crate wiki promote`** 可进 **`wiki/concepts/`**；**`RECENT.md` / `LOG.md`** 记录活动；**不**自动合并进概念网（需显式） |
| **跨域标签** | 多项目 / 多客户共库时，front matter 尽早加 **domain** 等域标签 | 可用 **`tags`**、自定义 YAML 字段；**未**内置专用 domain 字段 |
| **人做主编** | 高风险场景：LLM 可能合成而不引用——人负责抽查与引用规范 | 与 PRD **§1.2**、**`sources`** 与 **`wiki-check`** 思路一致；**usage** 可强调「验证责任在用户」 |
| **反方与缺口（Divergence）** | 更新概念页时增加「反方论据 / 数据缺口」类区块，减轻确认偏误 | **未**内置；**`wiki-check`** / 多页 prompt 中可**增强**；属可选演进 |
| **结构化存储 + 渲染 MD** | 有人用事务日志 + SQLite + 渲染为 Markdown，与「纯文件 wiki」路线不同 | CRATE 明确 **文件优先**；**不**替代 Binder 类产品；若需可文档中一句话对比 |

若你希望把某一行提升为 **PRD / usage 正式条款**，可在 Issue 中拆任务并改 `PRD.md` / `usage.md` 对应小节。
