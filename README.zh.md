# CRATE

**Compile Raw Archives, Tracked in the vault, into Encyclopedic wiki.**

**语言 / Language：** [English](README.md) | **中文（本文）**

CRATE 是一套**以文件为中心的个人知识「编译器」**：把杂乱的 **raw** 素材（笔记、论文、剪藏、仓库片段）纳入 **vault** 统一溯源，再迭代**编译**成可导航的 **wiki**，并辅以轻量检索、Lint，以及可选的回流再编译。

> **中文释义：** **CRATE** = 把散落在各处的 **raw**，以 **vault** 为单一事实来源，**增量编译**成可互链的 **wiki**（百科全书式知识库）。

---

## 文档

下列设计类文档正文为**中文**。

- **[docs/README.md](docs/README.md)** — 文档索引
- **[docs/usage.md](docs/usage.md)** — 使用说明（CLI、vault、环境变量、工作流）
- **[agent-skills/crate-vault/SKILL.md](agent-skills/crate-vault/SKILL.md)** — 通用 Agent Skill（Cursor / Claude Code / 其它）；安装说明见 [docs/agent-skill.md](docs/agent-skill.md)
- **[docs/providers.md](docs/providers.md)** — 多平台 LLM / 嵌入（DeepSeek、OpenAI、阿里、腾讯、火山、OpenRouter、Azure 等，`CRATE_LLM_PROVIDER`）
- **[docs/roadmap.md](docs/roadmap.md)** — 路线图与待实现项（含增量编译语义）
- **[docs/obsidian.md](docs/obsidian.md)** — 与 Obsidian 搭配（库根即 vault、日常流程）
- **[docs/PRD.md](docs/PRD.md)** — 产品需求与里程碑
- **[docs/technical-design.md](docs/technical-design.md)** — 架构、vault 布局、编译 / 问答 / Lint

---

## 为什么选择 CRATE

- **本地优先**：Markdown 目录树，而非黑盒云端文库。
- **增量编译**：随素材变化反复跑编译，而非一次性生成。
- **可审阅**：wiki 页、幻灯、图表等产出可 diff、可当代码审。
- **Agent 友好**：为问答 / RAG 预留读**相关页面**的路径，而非整库塞进上下文。

设计理念来自把 LLM 当作对自己材料的**编译器**，而非一次性聊天接口。Karpathy 的 **LLM Wiki** 正文见 [GitHub Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)；更早的 [X 帖串](https://x.com/karpathy/status/2039805659525644595)亦讨论同一思路。与该工作流的**逐项对照**见 [docs/usage.md §7.5](docs/usage.md#karpathy-style-comparison)；仓库内副本为 [docs/llm-wiki.md](docs/llm-wiki.md)。

---

## 能力范围

| 阶段 | 意图 |
|------|------|
| **Raw 入轨** | 网页剪藏、仓库快照、PDF、图片等进入流水线的素材 |
| **Vault** | 可版本化、可观测的存储：raw 与编译产物同处一处、可追溯 |
| **Wiki 编译** | 由 LLM 结构化：摘要、概念、反向链接、目录树 |
| **产出物** | Markdown，可选 Marp 幻灯、小图表等你视为「发布物」的内容 |
| **健康 / Lint** | 一致性检查、缺口、新术语、可选「wiki 体检」 |
| **富化闭环** | 将问答产出或 Lint 结果再喂回下一轮编译 |

## 非目标（现阶段）

- 替代功能齐全的 PKM 应用（如日历、任务、间隔重复）。
- 托管多租户云端服务——CRATE 面向**你的** vault 与**你的**工具链。

---

## 仓库结构

```
crate/
├── README.md
├── README.zh.md         # 本文件（纯中文说明）
├── pyproject.toml
├── environment.yml        # Conda 环境（可选，与 Anaconda/Miniconda 配合）
├── docs/                  # PRD、技术方案等（见 docs/README.md）
├── prompts/               # 编译 / 架构 / 代码生成等提示模板
├── scripts/               # 自动化（如可选的 AI PR 审查）
├── src/crate/             # Python 包
├── tests/
├── .cursor/rules/         # Cursor Agent 约定
├── .vscode/               # Conda 路径与本机解释器（可选）
├── .devcontainer/         # 可选：VS Code Dev Container
└── .github/               # CI、Issue/PR 模板、可选 AI 审查 workflow
```

用户数据侧的 **vault** 目录树（常在本仓库之外）见 [docs/technical-design.md](docs/technical-design.md)。

---

## 快速开始

### Conda（Anaconda 默认安装路径）

若本机使用 Anaconda 且 `conda` 位于 `/opt/anaconda3/condabin/conda`，可用仓库中的 [`environment.yml`](environment.yml) 一键创建名为 **`crate`** 的环境（Python 3.11，并以可编辑方式安装 `[dev]` 依赖）：

```bash
git clone https://github.com/GuiminChen/crate.git
cd crate
/opt/anaconda3/condabin/conda env create -f environment.yml   # 首次
# 或已创建后更新依赖：/opt/anaconda3/condabin/conda env update -f environment.yml

conda activate crate
pre-commit install
pytest -q
```

已将 [`.vscode/settings.json`](.vscode/settings.json) 配置为使用上述 `conda` 可执行文件，并将默认解释器指向 `/opt/anaconda3/envs/crate/bin/python`（激活环境与 Cursor/VS Code 打开仓库后即可一致）。若你的安装路径不同，请在本机改掉这两项，或在命令面板中选择正确的 Python 解释器。

### venv / 裸 Python（3.9+；Dev Container 为 3.11）

```bash
git clone https://github.com/GuiminChen/crate.git
cd crate
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
pytest -q
```

### Dev Container

在 VS Code 中打开本仓库并选择「在容器中重新打开」，将使用 [`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json)（Python 3.11、可编辑安装、pre-commit）。

### CLI（M0）

执行 `pip install -e ".[dev]"` 后，可使用 `crate` 命令：

```bash
crate init [--vault PATH]           # 创建 raw/wiki/meta 树（默认 vault = 当前目录）
crate compile [--vault PATH] [--full|--no-incremental] [--wiki-graph]  # raw 下 .md/.pdf；默认增量
crate ingest [--vault PATH]         # .crate/ingest_session.md → 显式 raw 子集编译（绕过增量跳过）
crate watch [--vault PATH] [--debounce-seconds SEC] [--wiki-graph]   # 轮询 raw/，静默后自动 compile
crate serve-search [--vault PATH] [--port N]              # HTTP GET /search?q=...（JSON；crate index 后可 &semantic=1）
crate lint [--vault PATH] [--json] [--wikilinks] [--raw] [--http-external]  # wiki/；可选外链 HTTP 抽检
crate wiki graph [--vault PATH]     # meta/wiki_body_graph.json + 可选 wiki/_index/BODYGRAPH.md
crate report raw-wiki [--vault PATH]   # meta/raw_wiki_coverage.json（raw→wiki 覆盖启发式）
crate wiki index-extend [--vault PATH] # meta/wiki_index_extended.json（wiki/notes/ 标题）
```

`compile`、`ask`、`wiki-check` 使用 **OpenAI 兼容**的聊天客户端。若已配置 DeepSeek 密钥，默认仍可选用 DeepSeek；切换平台请使用 `CRATE_LLM_PROVIDER` 及各云变量，详见 **[docs/providers.md](docs/providers.md)**。

**M1 — 问答与回流**

```bash
crate ask [--vault PATH] [--no-feedback] TOPICS 里写了什么？
```

`ask` 通过工具循环（`vault_read`、`vault_search`、`vault_search_semantic`、`vault_write_output`）调用与 `compile` **相同的聊天 API 配置**，将答案写入 `wiki/outputs/`，默认在 `wiki/_index/RECENT.md` 追加一行（可用 `--no-feedback` 关闭）。先执行 `crate ephemeral init` 后可用 `--session <id>`，允许在 `wiki/_ephemeral/<id>/` 下写草稿。

**M2 — 搜索、统计、语义索引**

```bash
crate search [--vault PATH] [--json] [--max-hits N] [--semantic] <词...>
crate stats [--vault PATH] [--json] [--strict] [--exclude-outputs]   # --json 含 readiness（同 serve-search /health）
crate doctor [--vault PATH] [--json] [--strict]   # 版本、目录、meta 产物、readiness
crate index [--vault PATH] [--reset]   # 需 CRATE_EMBEDDING_API_KEY 或 OPENAI_API_KEY 等
```

`compile` / `ask` 会向 stderr 打印规模门闸提示，除非加 `--quiet-gate`。语义搜索需先执行 `crate index`。

**M3 — 短命问题 wiki**

```bash
crate ephemeral init [--vault PATH]                    # 打印新会话 id
crate ask [--session ID] ...                           # 可写入 wiki/_ephemeral/ID/
crate ephemeral finalize <session_id> [--vault PATH] [--delete]
crate ephemeral clean [--vault PATH] --older-than DAYS
```

### 可选：AI PR 审查

工作流 [`.github/workflows/ai-code-review.yml`](.github/workflows/ai-code-review.yml) 仅在仓库已设置密钥 `OPENAI_API_KEY` 时运行。如需可设置 `OPENAI_REVIEW_MODEL` 覆盖模型。

---

## 路线图（与 docs/PRD.md 对齐）

| 阶段 | 重点 |
|------|------|
| **M0** | Vault 约定 + 手工触发编译 POC + 最小 Lint |
| **M1** | Agent 问答 + 文件化输出 + 回流（`crate ask`、`wiki/outputs`、`RECENT.md`） |
| **M2** | `crate search`、`stats`、`index`、语义工具 + 依赖环境的嵌入 |
| **M3** | `crate ephemeral` + `ask --session` + finalize/clean |

排期可通过 Issues 调整。

---

## 贡献

欢迎按模板提交 PR，或先开 Issue，说明：

- 使用场景（希望 raw 变成什么样的 wiki），
- 约束（仅本地、模型 X、vault 工具 Y），
- 可接受的验收方式（如何判断编译成功）。

---

## 许可证

**Apache-2.0**。

---

## 名称由来

**CRATE** 展开为：

- **C**ompile
- **R**aw
- **A**rchives
- **T**racked in the **vault**
- **E**ncyclopedic wiki

与文首标语一致：*Compile Raw Archives, Tracked in the vault, into Encyclopedic wiki.*
