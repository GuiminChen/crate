# CRATE 使用说明

面向 **已克隆仓库并完成安装** 的用户：如何初始化 vault、调用 CLI、配置密钥，以及理解各命令的输入与产出。架构与里程碑见 [technical-design.md](technical-design.md)、[PRD.md](PRD.md)。

与 [Andrej Karpathy](https://x.com/karpathy) 在 X 上讨论的「个人知识库 / 互联 wiki」思路的对照，见下文 **[Karpathy-style comparison](#karpathy-style-comparison)**（§7.5）。

---

## 1. 安装与运行环境

- **推荐**：按根目录 [README.md](../README.md) 使用 Conda（`environment.yml`）或 `venv`，并以可编辑方式安装：`pip install -e ".[dev]"`。
- 安装后可在终端使用 **`crate`** 命令（由 `pyproject.toml` 的 `[project.scripts]` 注册）。
- **Python**：3.9+（开发/CI 常用 3.11）。

**Cursor / VS Code**：若使用仓库内 [`.vscode/settings.json`](../.vscode/settings.json)，默认解释器可指向 Conda 环境 `crate`（路径因本机安装而异）。

---

## 2. 什么是 Vault

**Vault** 是 CRATE 工作的根目录：包含 `raw/`（原始材料）、`wiki/`（编译与问答产出）、`meta/`（可选状态）等。
**默认 vault = 当前工作目录**；若你的知识库在别的路径，对每个子命令使用 **`--vault /绝对或相对路径`** 指向该根目录。

不要在仓库内混放大量私人笔记时，可把 vault 放在任意独立文件夹，仅通过 `--vault` 指向即可。

若使用 **Obsidian**，把「库」根目录设为上述 vault 根即可与 CRATE 共用同一套 `raw/`、`wiki/`；步骤与注意见 [obsidian.md](obsidian.md)。

---

## 3. 环境变量与密钥（LLM）

`compile` 与 `ask` 通过 **OpenAI 兼容客户端** 调用 **DeepSeek**（默认 `https://api.deepseek.com`，模型 `deepseek-chat`）。

| 变量 | 含义 |
|------|------|
| `CRATE_DEEPSEEK_API_KEY` 或 `DEEPSEEK_API_KEY` | **必填**（二选一）。用于编译与问答，**勿写入代码或提交到 Git**。 |
| `CRATE_DEEPSEEK_BASE_URL` | 可选。覆盖 API 基址（默认见上）。 |
| `CRATE_DEEPSEEK_MODEL` | 可选。默认模型名（默认 `deepseek-chat`）。 |
| `CRATE_MODEL_COMPILE` | 可选。仅 **`crate compile`**（含 **`--wiki-graph`**）使用；若设置则覆盖 `CRATE_DEEPSEEK_MODEL`。 |
| `CRATE_MODEL_QA` | 可选。仅 **`crate ask`** 使用；若设置则覆盖 `CRATE_DEEPSEEK_MODEL`。 |
| `CRATE_MODEL_LINT` | 可选。用于 **`crate wiki-check`**（语义巡检）；若设置则覆盖 `CRATE_DEEPSEEK_MODEL`。 |
| `CRATE_MAX_OUTPUT_TOKENS` | 可选。聊天补全的 **`max_tokens`** 全局上限（若未设置 purpose 专用变量则不用）。 |
| `CRATE_MAX_OUTPUT_TOKENS_COMPILE` | 可选。覆盖全局，仅用于 **`compile`** / **`compile --wiki-graph`**。 |
| `CRATE_MAX_OUTPUT_TOKENS_QA` | 可选。覆盖全局，仅用于 **`crate ask`** / **`ask-multi`**。 |
| `CRATE_MAX_OUTPUT_TOKENS_LINT` | 可选。覆盖全局，仅用于 **`wiki-check`**。 |
| `CRATE_MAX_INPUT_CHARS` | 可选。发给模型的**用户/拼接提示**硬截断上限（字符数）；与下述 purpose 专用变量二选一链式生效。 |
| `CRATE_MAX_INPUT_CHARS_COMPILE` | 可选。仅 **`compile`** / **`compile --wiki-graph`** 的输入侧截断（优先于全局）。 |
| `CRATE_MAX_INPUT_CHARS_QA` | 可选。仅 **`ask`** / **`ask-multi`**。 |
| `CRATE_MAX_INPUT_CHARS_LINT` | 可选。仅 **`wiki-check`**。 |
| `CRATE_SEMANTIC_CHECK_MAX_PAGES` | 可选。语义巡检时从索引中抽样的概念页数量，默认 **8**。 |
| `CRATE_SEMANTIC_CHECK_EXCERPT_CHARS` | 可选。每页摘录最大字符，默认 **1500**。 |
| `CRATE_MARP_CMD` | 可选。调用 Marp 的前缀命令（shell 分词），默认 **`npx --yes @marp-team/marp-cli`**；需本机有 **Node/npm** 或已安装 **`marp` CLI**。 |
| `CRATE_MULTI_AGENT_MAX_ROUNDS` | 可选。**`ask-multi`** 第二阶段交给工具循环的最大轮数，默认 **16**。 |
| `CRATE_MULTI_AGENT_BUDGET_CHARS` | 可选。规划阶段与问题拼接的总字符预算，默认 **500000**。 |
| `CRATE_EMBEDDING_API_KEY` 或 `OPENAI_API_KEY` | 可选。用于 **`crate index`** / **`crate search --semantic`**（与聊天模型可分开）。 |
| `CRATE_EMBEDDING_BASE_URL` / `CRATE_EMBEDDING_MODEL` | 可选。默认 OpenAI 兼容嵌入端点与 `text-embedding-3-small`。**须与密钥同属一家服务商**（勿把 DeepSeek 聊天 Key 配到阿里云/OpenAI 等嵌入地址）。 |
| `CRATE_EMBEDDING_BATCH_SIZE` | 可选。每次嵌入 API 请求的文本条数上限，默认 **10**（阿里云 DashScope 单请求最多 10 条）。使用 OpenAI 等可承受更大批次时可设为 **64** 等以加快索引。 |
| `CRATE_GATE_WIKI_WORDS` 等 | 可选。规模门闸阈值（见 `crate stats`）。 |
| `CRATE_COMPILE_MAX_CHARS_PER_FILE` | 可选。`crate compile` 每个 raw 文件读入提示的**最大字符数**（覆盖默认 8000）。 |

CLI 会 **`load_dotenv()`**：可在 vault 或项目根目录放置 **`.env`**（且将 `.env` 保持在本机/`.gitignore` 中），避免在 shell 里反复 `export`。

---

## 4. 命令一览

| 命令 | 作用 |
|------|------|
| `crate init [--vault PATH] [--force]` | 创建标准目录与占位文件（`raw/`、`wiki/`、`meta/` 等）。 |
| `crate compile [--vault PATH] [--full] [--no-incremental] [--wiki-graph] [--quiet-gate]` | 读取 `raw/**/*.md` 与 **`raw/**/*.pdf`**，默认单条 `wiki/notes/`；**`--wiki-graph`** 时多页 JSON → `wiki/concepts/`、`meta/wiki_index.json`、`meta/compile_wiki_last.json`、**`wiki/_index/INDEX.md`**（导航 hub）、可选 **`BACKLINKS.md`** / **`TOPICS.md`**（见 §5.2）；默认增量；**`--full`** 全量。 |
| `crate watch [--vault PATH] [--debounce-seconds SEC] [--poll-interval SEC] [--wiki-graph] [--quiet-gate]` | **轮询** `raw/`，防抖后自动 **`compile`**；**`--wiki-graph`** 时等价于多次执行 **`compile --wiki-graph`**（需 API key）；Ctrl+C 结束。 |
| `crate serve-search [--vault PATH] [--host HOST] [--port N]` | 本机只读 **HTTP**：`GET /search`（字面量 / **`semantic=1`**）；**`GET /health`** 返回 **`vault`** 路径、**`embedding_configured`** / **`semantic_index_ready`** / **`semantic_ready`**、**`multi_page_wiki_index`**（是否存在 **`meta/wiki_index.json`**）；默认 `127.0.0.1:8765`。 |
| `crate ask [--vault PATH] [--no-feedback] [--session ID] <问题…>` | 工具型问答；**`--session`** 配合 **`ephemeral init`** 可写 `_ephemeral/`。 |
| `crate lint … [--raw]` | 默认检查 **`wiki/**/*.md`**；**`--raw`** 同时检查 **`raw/**/*.md`**（相对 **`[](path)`** / **`![](path)`**、可选 **`[[wikilink]]`**、重复标题，规则与 wiki 相同）；**`--no-duplicate-headings`** 等选项对两处同时生效；默认跳过 **`wiki/_ephemeral/`**（除非 **`--include-ephemeral`**）。 |
| `crate search [--vault PATH] [--json] [--semantic] <词…>` | 字面量子串搜索；**`--semantic`** 需先 **`crate index`** 与嵌入 API。 |
| `crate stats [--vault PATH] [--json] [--gates-json] [--strict]` | 统计词数/文件数；**`--json`** 含 **`readiness`**（与 **`serve-search`** 的 **`GET /health`** 相同字段：vault、**`semantic_ready`**、**`multi_page_wiki_index`** 等）；**`--gates-json`** 只打印门闸对象。 |
| `crate doctor [--vault PATH] [--json] [--strict]` | 无 LLM：**`crate_version`**、**`dirs`**、编译/巡检/向量库文件标记、**`readiness`**；详见 §5.5a。 |
| `crate index [--vault PATH] [--reset]` | 为 `raw`/`wiki` 下 Markdown 分块建 **`meta/embeddings.sqlite`**。 |
| `crate ephemeral init|finalize|clean` | 短命维基目录 **`wiki/_ephemeral/<id>/`** 的创建、打包到 `wiki/outputs/FINAL_*.md`、按 TTL 清理。 |
| `crate wiki-check [--no-write] [--json-full]` | **LLM 语义巡检**：读取 **`meta/wiki_index.json`**（需先 **`compile --wiki-graph`**）与若干概念页摘录，输出 JSON 报告；默认写入 **`meta/semantic_wiki_report.json`**。 |
| `crate wiki normalize --to-md-links \| --to-wikilinks` | 批量把 **`[[wikilinks]]`** 与 **`[text](path.md)`** 互转（仅 `wiki/**/*.md`）。 |
| `crate wiki figures-init` | 创建 **`wiki/outputs/figures/`**，便于存放 matplotlib 等脚本生成的图（由用户本地执行脚本）。 |
| `crate marp [PATH…] [--no-pdf]` | 调用本机 **Marp CLI** 渲染幻灯；未指定路径时在 **`wiki/`** 下查找 front matter 含 **`marp: true`** 的 `.md`；PDF 默认输出到 **`wiki/outputs/marp-pdf/`**。 |
| `crate ask-multi …` | **两阶段问答**：先做一次规划 JSON，再与 **`crate ask`** 相同的工具循环；参数与 **`ask`** 类似（**`--session`** 等）。 |

全局参数：**`--vault`** — 指定 vault 根路径；省略则为当前目录。

---

## 5. 各命令说明

### 5.1 `crate init`

- 创建目录（示例）：`raw/papers`、`raw/web-clips`、`raw/assets/images`、`wiki/_index`、`wiki/concepts`、`wiki/notes`、`wiki/outputs`、`meta`。
- 写入占位文件：`wiki/_index/TOPICS.md`、`wiki/_index/RECENT.md`、`wiki/_index/INDEX.md`、`VAULT.md`，以及 `AGENTS.md`、`meta/compile_state.json` 等。
- **`--force`**：若目标文件已存在，仍覆盖更新（慎用）。
- 成功时向 stderr 打印 vault 路径，stdout 列出相对路径。

### 5.2 `crate compile`

- **增量（默认）**：若 `meta/compile_state.json` 中已有 **v2** 成功编译记录，则仅在 **raw 文件新增、修改或删除**时调用模型；无变更时**不写**新笔记并提示跳过（退出码 0）。指纹为各文件内容的 **SHA-256**（旧版 `mtime`+`size` 会在下次成功编译时自动升级为 v2）。
- **`--full` / `--no-incremental`**：同义；忽略变更检测，始终用当前 **全部** raw 调用模型并刷新状态。
- 递归收集 **`raw/` 下所有 `.md` 与 `.pdf`**（增量模式下仅为本轮选中的子集，删除 raw 时见 [roadmap.md](roadmap.md) 说明）。Markdown 直接读入；PDF 仅抽取**可选中文本层**（扫描版/纯图 PDF 可能几乎无字，编译提示里会说明）。
- 按文件拼接为提示内容（**每个文件**有长度上限，超出会截断并标注）。
- 若无任何 `raw/**/*.md` 或 `**/*.pdf`，仍会生成笔记，但内容会提示先添加源文件。
- 产出：写入 **`wiki/notes/compile-<UTC时间戳>-<slug>.md`**，带 YAML front matter（`kind: compile_run`、`sources`、`model`、`created` 等）。
- **`--wiki-graph`**（多页互联 wiki）：使用 [`prompts/wiki_multi.md`](../prompts/wiki_multi.md) 要求模型返回 **JSON**（`version: 1`、`concepts[]`，可含 `related_slugs` 等）。成功时写入：
  - **`wiki/concepts/<slug>.md`**：概念页（front matter 含 `title`、`sources`、可选 **`related_slugs`**、`updated` 等）；
  - **`meta/wiki_index.json`**：机器可读索引（`touched_slugs`、`raw_sources`、`concepts[]` 含 `related_slugs`），供脚本或 Agent 使用；
  - **`meta/compile_wiki_last.json`**：最近一次多页编译的 **`touched_slugs`** 与时间戳（便于脚本与增量策略）；
  - 若有至少一个概念页：生成 **`wiki/_index/BACKLINKS.md`**（由 `related_slugs` 推导 **Outgoing / Incoming**）；
  - 每次成功多页编译：更新 **`wiki/_index/INDEX.md`**（导航：TOPICS、RECENT、BACKLINKS（若有概念）、`meta/wiki_index.json` 链接、概念列表、本轮 raw 列表）；
  - 若 JSON 中含 `topics_markdown`：覆盖/更新 **`wiki/_index/TOPICS.md`**（带自动生成说明行）；
  - 若含 `synthesis_note`：额外写入 **`wiki/notes/compile-<stamp>-wiki.md`** 综述笔记。
  - 若 JSON **无法解析**或 schema 不符：stderr 提示，并**回退**为单条 `wiki/notes/compile-*.md`（front matter 含 `wiki_graph_fallback: true`），不中断退出码。
- 需要有效的 DeepSeek API 密钥（见第 3 节）。

**使用示例（增量 / 全量）：**

```bash
# 首次或尚无 v2 状态：会编译当前全部 raw，并写入 meta/compile_state.json（SHA-256）
crate compile

# 未改任何 raw 时再执行：不向模型请求，stderr 提示跳过（仍退出 0）
crate compile

# 多页 wiki（概念页 + meta/wiki_index.json）
crate compile --wiki-graph

# 强制按「当前全部 raw」再编一版（忽略变更检测，刷新指纹）
crate compile --full
# 与上一行等价：
crate compile --no-incremental

# 指定 vault 根目录时同样适用
crate --vault /path/to/my-vault compile
crate --vault /path/to/my-vault compile --full
```

**`crate watch`（自动编译）示例：**

```bash
# 在 vault 根目录：监听 raw/，停止改动约 3 秒后自动 crate compile（可改 --debounce-seconds）
export CRATE_DEEPSEEK_API_KEY="********"
crate watch

# 更密的轮询 / 更长防抖
crate watch --poll-interval 0.3 --debounce-seconds 5

# 监听 raw/ 并在防抖后做多页 wiki 编译（与 compile --wiki-graph 一致）
crate watch --wiki-graph
```

**`crate serve-search`（HTTP 搜索）示例：**

```bash
# 终端 A：启动（默认 127.0.0.1:8765）
crate serve-search

# 终端 B：字面搜索，JSON（响应含 mode: literal）
curl -s 'http://127.0.0.1:8765/search?q=attention&max=10' | head
# 语义搜索（需先 crate index，且配置 CRATE_EMBEDDING_*）
curl -s 'http://127.0.0.1:8765/search?q=attention&semantic=1&max=10' | head
curl -s http://127.0.0.1:8765/health   # JSON: ok, vault, semantic_ready, …
```

### 5.2a `crate watch`

- **轮询** `raw/` 文件内容的 SHA-256（与增量编译状态同源）；有变化则重置防抖计时，仅在指纹连续 **`--debounce-seconds`**（默认 3）内不变时调用 **`compile`**。
- **`--wiki-graph`**：每次触发的编译与 **`crate compile --wiki-graph`** 相同（多页 **`wiki/concepts/`**、`meta/wiki_index.json` 等）；成本与 token 通常高于默认单条 compile 笔记。
- 不依赖 `watchdog` 等第三方库；需 **`CRATE_DEEPSEEK_API_KEY`**（与 `compile` 相同）。**Ctrl+C** 退出。

### 5.2b `crate serve-search`

- 只读、默认 **`127.0.0.1`**；**勿**将端口暴露到不可信网络。
- **`GET /health`**：返回 JSON，至少含 **`ok`**、**`vault`**（绝对路径）、**`embedding_configured`**（是否配置了嵌入密钥）、**`semantic_index_ready`**（**`meta/embeddings.sqlite`** 是否已有向量块）、**`semantic_ready`**（二者同时满足时 **`GET /search?semantic=1`** 才可能直接返回命中）、**`multi_page_wiki_index`**（**`meta/wiki_index.json`** 是否存在，用于判断多页 wiki 是否已编译）。便于脚本与 Agent 在调用搜索前做就绪探测。
- **`GET /search?q=...&max=N`** 返回 JSON，含 **`mode`**：**`literal`**（默认）或 **`semantic`**（`semantic=1` / `true` / `yes` / `on`）。
- **字面量**：**`hits`** 与 CLI **`crate search`** 相同；字段 **`path` / `line` / `snippet`**。
- **语义**：需 **`crate index`** 且配置嵌入 API（与 **`search --semantic`** 相同）。未配置密钥或无索引时 **`hits`** 为空，并带 **`detail`** 说明原因；嵌入调用失败时也会在 **`detail`** 中给出错误信息（仍 **HTTP 200**，便于 Agent 解析）。

### 5.3 `crate ask`

- 将 **`question` 多个词拼接成一句**（与 shell 引号配合即可）。
- 代理通过工具访问 vault：**`vault_read`**、**`vault_search`**、**`vault_search_semantic`**（需已建索引）、**`vault_write_output`**。
- 默认仅允许写入 **`wiki/outputs/**`**；若使用 **`--session <id>`**（先 **`crate ephemeral init`**），还可写入 **`wiki/_ephemeral/<id>/**`**。
- 运行结束后在 stdout 打印**产出文件相对 vault 的路径**（通常为 `wiki/outputs/` 下某文件）。
- **`--no-feedback`**：不向 **`wiki/_index/RECENT.md`** 追加链接行；默认会追加一行（时间戳 + 问题摘要 + 指向该产出）。
- **`--quiet-gate`**：不打印规模门闸提示（与 **`compile`** 相同）。

空问题会返回退出码 **2**。

### 5.4 `crate search` / `crate index`

- **`search`**：在 `raw/**/*.md` 与 `wiki/**/*.md` 中做**字面量**子串匹配（有 `rg` 时优先用 ripgrep）。**`--semantic`** 使用嵌入向量与 **`meta/embeddings.sqlite`**（需先 **`crate index`** 并配置嵌入 API）。
- **`index`**：对可索引 Markdown 分块并调用嵌入 API，写入 **`meta/embeddings.sqlite`**；**`--reset`** 清空旧块。

### 5.5 `crate stats`

- 输出 `wiki` / `raw` 的 `.md` 词数与文件数（可选 **`--exclude-outputs`** 排除 `wiki/outputs`）。**`--strict`** 在超过 **`CRATE_GATE_*`** 门闸时返回退出码 **1**。
- **`--json`**：输出完整 JSON，除 **`wiki`** / **`raw`** / **`gates`** 外，还有 **`readiness`** 对象，字段与 **`serve-search`** 的 **`GET /health`** 一致（**`vault`**、**`embedding_configured`**、**`semantic_index_ready`**、**`semantic_ready`**、**`multi_page_wiki_index`**），便于在不启 HTTP 时用脚本探测语义检索与多页 wiki 是否就绪。
- **`--gates-json`**：只输出 JSON 里的 **`gates`** 对象（含 `triggered`、`reasons`、`thresholds`），**不含** **`readiness`**，便于脚本判断门闸，**不必安装 jq**。若仍想用管道，可执行 `crate stats --json | jq .gates`（需本机已安装 **jq**；未安装时请用 **`--gates-json`**）。

### 5.5a `crate doctor`

- **不调用** LLM、**不**起 HTTP；用于快速确认 vault 目录是否齐全、增量编译状态文件是否存在、语义索引与多页 wiki 索引是否就绪。
- 人类可读输出多行：首行 **`crate_version`**，随后 **`vault`**、**`dirs`**、**`compile_state_present`**、**`compile_wiki_last_present`**、**`semantic_wiki_report_present`**、**`embeddings_sqlite_present`**（**`meta/embeddings.sqlite`** 是否存在；与 **`semantic_index_ready`** 不同：空库或 **`crate index --reset`** 后可能仅有文件无向量块），以及 **`embedding_configured`**、**`semantic_index_ready`**、**`semantic_ready`**、**`multi_page_wiki_index`**（后四项与 **`serve-search`** 的 **`GET /health`** 相同）。
- **`--json`**：输出一个 JSON 对象（上述字段全集），另含 **`crate_version`**（已安装的 **`crate`** 包版本，来自 **PyPI/可编辑安装**；若仅用 **`PYTHONPATH`** 指向源码而未安装，则为 **`unknown`**），便于 CI 或 Ansible 等解析。
- **`--strict`**：若 **`raw/`**、**`wiki/`**、**`meta/`** 三者缺一，向 stderr 打印错误并返回退出码 **1**（未跑过 **`crate init`** 的常见情况）；**`--json`** 时仍先打印完整 JSON 再按同一规则决定退出码。

### 5.6 `crate ephemeral`

- **`init`**：创建 **`wiki/_ephemeral/<新 id>/`**，stdout 打印 **session id**。
- **`finalize <session_id>`**：将该目录下各 `.md` 拼入 **`wiki/outputs/FINAL_<id>.md`**；**`--delete`** 在成功后删除 ephemeral 目录。
- **`clean --older-than DAYS`**：按目录 mtime 删除过期 ephemeral 子目录。

### 5.7 `crate lint`

- 默认扫描 **`wiki/**/*.md`**；**`--raw`** 时**额外**扫描 **`raw/**/*.md`**，规则相同（便于校验剪藏/论文笔记里的相对附件链接是否落在 vault 内）。
- 扫描范围内 Markdown 的 **`[text](path)`** 与 **`![alt](path)`**（相对路径、非 `http(s):`）：目标须在 vault 内且文件存在；图片引用缺失时问题类型为 **`broken_image`**，普通链接为 **`broken_link`**。
- **重复 ATX 标题**（默认开启）：同一 `.md` 内若两段 **`#`…`######` 标题**在去掉 `#` 并折叠空白后**文案相同**，则报告 **`duplicate_heading`**（Markdown 代码围栏内的行不计入）。不同级别但同名（如 `# Foo` 与 `## Foo`）也会视为重复。
- **`--no-duplicate-headings`**：关闭上述检查（仅关心链接时可用）。
- **`--wikilinks`**：额外检查 `[[Page]]`、`[[path/to.md]]`、`[[alias|display]]` 等形式；在 `wiki/`、`wiki/concepts/`、`wiki/notes/`、`wiki/_index/` 下按页面名或路径解析（跳过 `![[嵌入]]`）；与 **`--raw`** 合用时，**`raw/`** 下 `.md` 内的 wikilink 亦按同一规则解析。
- 默认**不**检查 **`wiki/_ephemeral/**`**；需要时用 **`--include-ephemeral`**。
- 默认人类可读输出：`文件:行: 信息`。
- **`--json`**：以 JSON 数组输出结构化问题列表，便于脚本集成。
- 无问题时退出码 **0**；有问题为 **1**。

### 5.8 `crate wiki-check`

- **前提**：存在 **`meta/wiki_index.json`**（先执行 **`crate compile --wiki-graph`**）。
- 将索引 JSON 与若干概念页正文摘录发给模型，要求返回结构化 JSON（孤立 raw、重复概念、证据薄弱等），**默认不写回 wiki**。
- **`--no-write`**：不写入 **`meta/semantic_wiki_report.json`**，仅 stdout 打印 JSON。
- **`--json-full`**：stdout 包含外层信封（`generated`、`model`、`report`）；否则只打印 **`report`** 对象。
- 模型与 token 上限见第 3 节 **`CRATE_MODEL_LINT`**、**`CRATE_MAX_OUTPUT_TOKENS_LINT`**、**`CRATE_MAX_INPUT_CHARS_LINT`**。

### 5.9 `crate wiki normalize` / `crate wiki figures-init`

- **`normalize`**：在 **`wiki/**/*.md`** 内批量转换链接风格，需**二选一**：**`--to-md-links`**（`[[slug]]` → `[text](相对路径.md)`）或 **`--to-wikilinks`**（本地 `[text](href)` → `[[stem]]`）。跳过 front matter 外的行级处理规则与 **`crate lint --wikilinks`** 的解析方向一致。
- **`--include-ephemeral`**：同时处理 **`wiki/_ephemeral/**`**。
- **`figures-init`**：创建 **`wiki/outputs/figures/`**，用于放置 Agent 或你本人编写的 **Python/matplotlib 源码**；**不在此执行**任意代码（安全上由你在本机运行脚本）。

### 5.10 `crate marp`

- **可选依赖**：本机需能运行 **`CRATE_MARP_CMD`**（默认通过 **`npx`** 拉取 **`@marp-team/marp-cli`**）。
- 未传 **`PATH`** 时，在 **`wiki/`** 下查找 YAML front matter 中含 **`marp: true`** 的 Markdown。
- 默认生成 **PDF** 到 **`wiki/outputs/marp-pdf/<stem>.pdf`**；**`--no-pdf`** 则只把文件交给 Marp 的默认行为（便于预览 HTML 等，视 CLI 版本而定）。
- 子进程失败时，对应文件一行会含 **`exit`** 或 **`os error`**，命令整体退出码 **1**。

### 5.11 `crate ask-multi`

- 第一阶段：无工具、仅 **JSON 规划**（子问题列表等）；第二阶段：与 **`crate ask`** 相同的 **工具循环**（读/搜/写输出）。
- 适用：问题较长、希望先「拆步」再检索时；成本与延迟通常高于单次 **`ask`**。
- 环境变量 **`CRATE_MULTI_AGENT_*`** 见第 3 节；**`--session`** 与 **`ask`** 含义相同。

---

## 6. 目录与文件约定（摘要）

| 路径 | 说明 |
|------|------|
| `raw/` | 原始采集；**编译器不应覆盖**其中的源文件。 |
| `wiki/notes/` | `compile` 生成的笔记。 |
| `wiki/outputs/` | `ask` 默认最终产出。 |
| `wiki/_ephemeral/<id>/` | 短命草稿（**`ephemeral init`** + **`ask --session`**）。 |
| `meta/embeddings.sqlite` | 语义索引（**`crate index`**）。 |
| `wiki/_index/INDEX.md`、`TOPICS.md`、`BACKLINKS.md`、`RECENT.md` | **`INDEX.md`** 为人类可读入口（**`compile --wiki-graph`** 更新）；**`BACKLINKS`** 由 `related_slugs` 生成；`RECENT` 可被问答回流更新。 |
| `meta/` | `compile_state.json`、`wiki_index.json`、`compile_wiki_last.json`（**`--wiki-graph`**）、`semantic_wiki_report.json`（**`wiki-check`**）、嵌入库等。 |
| `wiki/outputs/marp-pdf/` | **`crate marp`** 默认 PDF 输出目录。 |
| `wiki/outputs/figures/` | **`crate wiki figures-init`** 创建的图脚本目录。 |
| `VAULT.md` | vault 内简短说明。 |

更完整的布局与流程见 [technical-design.md](technical-design.md)。

---

## 7. 典型工作流示例

### 7.1 基础：初始化、编译、问答

```bash
cd /path/to/my-vault
crate init
# 将笔记放入 raw/，例如 raw/papers/note.md
export CRATE_DEEPSEEK_API_KEY="********"   # 或使用 .env
crate compile
crate lint              # wiki/
crate lint --raw        # 含 raw/ 内相对链接与图片
crate ask 这篇 raw 笔记的核心概念是什么？
```

在**另一目录**打开终端时：

```bash
crate --vault /path/to/my-vault compile
crate --vault /path/to/my-vault ask 列出 wiki 里最近关于 X 的片段
```

### 7.1b 增量编译（默认）与全量重编

在已有 **`crate compile` 成功记录**后，只有 **`raw/` 下 .md / .pdf** 增删改才会再次调用模型；否则第二次起会跳过并提示（节省 API 调用）。

```bash
cd /path/to/my-vault
export CRATE_DEEPSEEK_API_KEY="********"   # 或 .env

# 第一次：生成 wiki/notes/compile-*.md，并记录各 raw 文件内容 SHA-256
crate compile

# 未修改 raw 时：stderr 出现跳过提示，不写新笔记
crate compile

# 编辑或新增 raw 后再编（只把变更相关逻辑交给模型；删除 raw 时见 roadmap）
vim raw/papers/note.md
crate compile

# 需要「无论是否变更都对全部 raw 做一次综述」时用全量
crate compile --full
```

### 7.2 M2：字面搜索、规模统计、语义索引

**在 vault 根目录下全文搜一句子串（输出 路径:行: 片段）：**

```bash
cd /path/to/my-vault
crate search Attention
crate search --max-hits 50 "self-attention"
crate search --json "TOPICS" > /tmp/hits.json
```

**查看 wiki/raw 体量与是否触发门闸（人类可读）：**

```bash
crate stats
crate stats --exclude-outputs          # wiki 统计不含 wiki/outputs
crate stats --json | head            # 含 readiness（同 /health）
crate stats --gates-json             # 仅输出 gates 对象（无需 jq）
```

**CI 中若超阈值则失败退出：**

```bash
crate stats --strict || echo "scale gate triggered"
```

**语义检索（需先配置嵌入 API，与 DeepSeek 可分开）：**

```bash
# .env 示例：CRATE_EMBEDDING_API_KEY=... 或 OPENAI_API_KEY=...
crate index                    # 生成 meta/embeddings.sqlite
crate index --reset            # 清空后全量重建
crate search --semantic "transformer 与 RNN 的区别"
crate search --semantic --json --max-hits 5 "evaluation metrics"
```

**抑制 compile/ask 时的门闸提示（脚本流水线）：**

```bash
crate compile --quiet-gate
crate ask --quiet-gate 简述 TOPICS 里列了什么主题？
```

### 7.3 M3：短命维基会话（草稿 → 打包）

```bash
cd /path/to/my-vault
SID=$(crate ephemeral init)              # stdout 仅一行 session id
echo "SID=$SID"

# 仅在该会话目录写草稿（需配合 ask --session）
crate ask --session "$SID" --no-feedback 先列 raw 里与主题相关的文件名

# 打包 wiki/_ephemeral/<SID> 下所有 .md 到 wiki/outputs/FINAL_<SID>.md
crate ephemeral finalize "$SID"

# 打包并删除 ephemeral 目录
crate ephemeral finalize "$SID" --delete

# 清理 30 天未改动的过期会话目录
crate ephemeral clean --older-than 30
```

**跨目录指定 vault：**

```bash
crate --vault /path/to/my-vault ephemeral init
crate --vault /path/to/my-vault ephemeral finalize 20260404-abc12def --delete
```

### 7.4 组合：先搜再答

```bash
crate search "[[concept"
crate ask 根据搜索结果，总结 concept 相关链接指向哪些文件？
```

### 7.5 与 Karpathy 式知识流的对比

#### Karpathy-style comparison

[Karpathy 在 X 上的讨论](https://x.com/karpathy/status/2039805659525644595)（及后续帖）强调一种**个人知识库**形态：材料先进 **`raw/` 式沉淀**，再经编译成**可互联的 wiki**，问答与回流形成闭环。下表说明 **CRATE 当前实现**与这种愿景的对应关系（非一一产品对标，而是能力映射）。

| 愿景环节 | Karpathy 式描述（概括） | CRATE 中的对应 |
|----------|-------------------------|----------------|
| 材料入轨 | 论文、网页、剪藏进入「收件箱」 | **`raw/`** 支持 **`.md`** 与 **`.pdf`**（文本层抽取；扫描版/OCR 自理）；无专用剪藏 App，由你自选工具 |
| 自动监视 | 新文件触发整理/编译 | **`crate watch`**：轮询 `raw/` + 防抖后 **`compile`**；可加 **`--wiki-graph`** 做多页编译（非 inotify） |
| 互联 wiki | 多页、概念、链接、可浏览 | **`crate compile --wiki-graph`** → **`wiki/_index/INDEX.md`**（hub）+ 概念页 + **`meta/wiki_index.json`** + **`BACKLINKS.md`** + 可选 **`TOPICS.md`**；正文内 **`[[wikilink]]`** 与 Obsidian 全量互操作仍可增强 |
| 人类入口 | 从一页跳进主题/概念 | **`wiki/_index/INDEX.md`**（Obsidian / 浏览器打开即可跳转） |
| 问答 | 基于库的 Agent 问答 | **`crate ask`**（工具读/搜/写）；**`crate ask-multi`** 为「规划 + 问答」两阶段 |
| 检索 | 关键词 + 语义 | **`crate search`** / **`crate index`** + **`search --semantic`**；**`serve-search`**：**`/search`**（字面量或 **`?semantic=1`**）、**`/health`**（vault 与 **`semantic_ready`** 等，便于自动化探测） |
| 编译策略 | 增量 vs 全库 | 默认**增量**（变更 raw）；**`--full`** / **`--no-incremental`** 全量；**`watch`** 防抖触发与 **`compile`** 相同选项 |
| 健康度 | 断链、重复标题、语义一致性 | **`crate lint`**：**`wiki/`** 与可选 **`--raw`** 的 **`raw/`** 中断链/图链（**`broken_*`**）、**`duplicate_heading`**；**`crate wiki-check`**：LLM 结构化报告（**不写回** wiki） |
| 图片与附件 | 笔记内相对图片不 404 | **`crate lint`** 校验 **`![](相对路径)`**（与 Markdown 链接同一套解析）；大图/OCR 等仍由你自管 |
| 回流 | 输出回到笔记网络 | 默认写入 **`wiki/outputs/`**；**`RECENT.md`** 可选追加；**`ephemeral finalize`** 打包草稿 |
| 草稿隔离 | 实验性写作不污染主 wiki | **`crate ephemeral init`** + **`ask --session`** 写入 **`wiki/_ephemeral/<id>/`**；**`finalize`** 拼入 **`wiki/outputs/FINAL_*.md`** |
| 幻灯 / 可视化 | 演示稿、图 | **`crate marp`**（本机 Marp）；**`wiki/outputs/figures/`** 放脚本，**本地执行**出图 |
| 规模与成本 | 大库要控 token / 模型 | **`CRATE_MAX_INPUT_CHARS*`**、**`CRATE_MAX_OUTPUT_TOKENS*`**；**`CRATE_MODEL_COMPILE`** / **`CRATE_MODEL_QA`** / **`CRATE_MODEL_LINT`** 分任务路由；**`crate stats`** 门闸；**`stats --json`** / **`doctor`** 的 **`readiness`** 与 **`serve-search /health`** 对齐，便于 CI |
| 自检 | 一眼确认库是否「接好线」 | **`crate doctor`**：**`crate_version`**、**`dirs`**、**`compile_state`**、**`compile_wiki_last`**、**`semantic_wiki_report`**、**`embeddings_sqlite`**、**`readiness`**；**`doctor --strict`** 校验 **`init`**；无需 **`serve-search`** |
| 端到端闭环（概括） | raw → 互联 wiki → 工具问答 → 写回笔记 | **`watch`** / **`compile`**（含 **`--wiki-graph`**）→ **`INDEX.md`** / concepts / **`wiki_index.json`** → **`ask`** / **`ask-multi`** → **`wiki/outputs/`**、**`RECENT.md`**、**`ephemeral finalize`**；语义检索需 **`index`**；健康度见 **`lint`** / **`wiki-check`** |

**不在 CRATE 范围内的 Karpathy 延伸话题**：例如用合成数据做**微调**、多模型深度编排等，见 [roadmap.md](roadmap.md)。

### 7.6 多页 wiki + 语义巡检（示例）

```bash
export CRATE_DEEPSEEK_API_KEY="********"
crate doctor --json | head          # 看 multi_page_wiki_index、compile_wiki_last_present 等
crate compile --wiki-graph
crate doctor --json | jq .compile_wiki_last_present  # 成功多页编译后为 true（需 jq）
crate wiki-check                    # stdout JSON；默认写入 meta/semantic_wiki_report.json
crate wiki-check --no-write | jq .  # 仅打印，不写文件（需安装 jq 时）
```

---


## 8. 常见问题

- **提示未设置 API Key**：设置 `CRATE_DEEPSEEK_API_KEY` 或 `DEEPSEEK_API_KEY`，或配置 `.env` 后在同一工作目录运行。
- **`ModuleNotFoundError: No module named 'pypdf'`**：在项目环境中执行 `pip install -e .` 或 `pip install pypdf`，确保与 `crate` 命令使用同一 Python 环境。
- **compile 结果为空或很短**：检查 `raw/` 是否确有 `.md`/`.pdf`；模型是否返回异常可查看生成文件内容。
- **PDF 似乎没被“读到”**：确认文件在 `raw/` 下且扩展名为 `.pdf`；若为扫描件，需先 OCR 成文本或转为 Markdown 再放入 `raw/`。
- **`crate search --semantic` 无结果或报错**：先执行 **`crate index`**；并设置 **`CRATE_EMBEDDING_API_KEY`** 或 **`OPENAI_API_KEY`**；索引文件应在 **`meta/embeddings.sqlite`**。
- **`vault_search_semantic` 提示无索引**：同上，完成 `crate index` 后再问答或语义搜索。
- **`crate index` 报 401 / invalid API key**：嵌入接口与聊天接口密钥一般不同；为 **`CRATE_EMBEDDING_BASE_URL`** 配置**对应平台**的 Key（如阿里云百炼/Model Studio 的 API Key），并设置该平台支持的 **`CRATE_EMBEDDING_MODEL`**，勿复用 **`CRATE_DEEPSEEK_API_KEY`**。
- **lint 失败**：根据输出修正断链或合并重复标题；若暂时只需检查链接可加 **`--no-duplicate-headings`**；或使用 **`--json`** 交给脚本处理；草稿在 `_ephemeral` 时默认不 lint，需要时加 **`--include-ephemeral`**。
- **`wiki-check` 报缺少 wiki_index.json**：先执行 **`crate compile --wiki-graph`** 生成 **`meta/wiki_index.json`**。
- **`marp` 报 exit / npx 失败**：安装 **Node.js**，或全局安装 **Marp CLI** 后设置 **`CRATE_MARP_CMD`** 指向可执行文件。
- **密钥泄露**：若曾误提交密钥，应**轮换** DeepSeek 侧 Key，并清理 Git 历史（必要时）。
- **增量编译和「全库综述」不一致**：默认只把本轮变更的 raw 发给模型；删除 raw、全量对齐等语义见 [roadmap.md](roadmap.md) §7。

---

## 9. 相关文档

| 文档 | 内容 |
|------|------|
| [README.md](../README.md) | 仓库说明、安装、CLI 速览、路线图 |
| [obsidian.md](obsidian.md) | 与 Obsidian 共用 vault 的简要教程 |
| [technical-design.md](technical-design.md) | 架构与 vault 设计 |
| [roadmap.md](roadmap.md) | 待实现项与增量编译语义 |
| [PRD.md](PRD.md) | 需求与里程碑 |
| [lessons-learned.md](lessons-learned.md) | 缺陷与预防记录 |
