# CRATE 路线图与待实现项

本文档汇总 [PRD.md](PRD.md)、[technical-design.md](technical-design.md) 与产品愿景中**尚未完成或仅部分实现**的能力，便于排期与对齐（例如与 [Karpathy 知识库串](https://x.com/karpathy/status/2039805659525644595) 描述的「raw → 互联 wiki → 问答 → 回流」相比）。

状态说明：**未开始** | **部分**（有 CLI/雏形） | **已有**

---

## 1. 数据入轨与监视

| 项 | PRD / 设计 | 状态 | 说明 |
|----|-------------|------|------|
| Raw 入轨（拖入/剪藏约定） | FR-02 | 部分 | 用户自管 `raw/`；无专用剪藏工具 |
| 入轨监视（`raw/` 变更防抖触发编译） | V1 自动编译 | **部分** | **`crate watch`**（可选 **`--wiki-graph`**）：轮询 + 防抖后调 `compile`；非 OS 级 inotify |
| 图片与相对路径规范校验 | FR-02 | **部分** | **`crate lint`** / **`lint --raw`**：**`![](path)`** 缺失时 **`broken_image`**；**`crate doctor`** 快速看目录与索引就绪 |

---

## 2. 编译形态（wiki）

| 项 | PRD / 设计 | 状态 | 说明 |
|----|-------------|------|------|
| 增量编译（仅变更 raw） | FR-03 | **部分** | `crate compile` 默认增量；`--full` / `--no-incremental` 全量；指纹为 **SHA-256**（`meta/compile_state.json` v2） |
| 互联 wiki：概念页、backlinks、主题分层 | MVP 编译 | **部分** | **`crate compile --wiki-graph`**：`wiki/concepts/` + `meta/wiki_index.json` + **`wiki/_index/BACKLINKS.md`**（`related_slugs`）+ **`meta/compile_wiki_last.json`**；正文内全量 wikilink 图谱仍可增强 |
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
| 环境自检（无 LLM） | — | **已有** | **`crate doctor`**：**`crate_version`**、**`dirs`**、**`compile_state` / `compile_wiki_last`**、**`semantic_wiki_report`**、**`embeddings_sqlite`**、**`readiness`**；**`--strict`** 缺标准目录时退出 **1** |

---

## 4. Lint 与健康检查

| 项 | PRD / 设计 | 状态 | 说明 |
|----|-------------|------|------|
| 断链检查 | FR-08 | **部分** | **`crate lint`**：**`wiki/`**；**`--raw`** 时含 **`raw/`**；相对 **`[](path)`** / **`![](path)`**；**`--wikilinks`**；**`duplicate_heading`**（可 **`--no-duplicate-headings`**）；raw↔wiki 语义对齐仍靠编译与 **`wiki-check`** |
| LLM 语义巡检、孤立 raw、摘要冲突 | FR-08 | **部分** | **`crate wiki-check`**：读 `wiki_index.json` + 抽样页，结构化 JSON 报告（**不写回**）；**`--apply`** 类自动修复未做 |
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
| 回流与 front-matter | FR-07 | 部分 | `RECENT.md` 等 |
| Token 预算 / 模型路由 | FR-11 | **部分** | **`CRATE_COMPILE_MAX_CHARS_PER_FILE`**；**`CRATE_MODEL_*`** 分任务；**`CRATE_MAX_OUTPUT_TOKENS*`**；**`CRATE_MAX_INPUT_CHARS*`** 输入硬截断 |
| 短命 wiki 编排、多 Agent | V2 / Karpathy 二推 | **部分** | **`ephemeral` + `ask --session`**；**`crate ask-multi`**（规划 JSON + `ask` 工具循环）；深度多角色编排仍可增强 |
| 合成数据 + 微调 | Karpathy 展望 | 未开始 | 非本期 |

---

## 7. 已知语义边界（增量编译）

- 默认仅把**本轮判定为变更的** raw 发给模型；**不**保证与「全库一次性综述」等价。
- 删除 raw 文件时，当前实现会**用剩余全部 raw** 作为编译输入以刷新综述（见实现说明）。
- 需要与 Karpathy 式「全库互联 wiki」对齐时，仍依赖后续 **多页 wiki 维护**与 **`--full` / `--no-incremental`** 等组合策略。

更多操作说明见 [usage.md](usage.md)。
