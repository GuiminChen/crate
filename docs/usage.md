# CRATE 使用说明

面向 **已克隆仓库并完成安装** 的用户：如何初始化 vault、调用 CLI、配置密钥，以及理解各命令的输入与产出。架构与里程碑见 [technical-design.md](technical-design.md)、[PRD.md](PRD.md)。

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
| `CRATE_DEEPSEEK_MODEL` | 可选。覆盖模型名（默认 `deepseek-chat`）。 |
| `CRATE_EMBEDDING_API_KEY` 或 `OPENAI_API_KEY` | 可选。用于 **`crate index`** / **`crate search --semantic`**（与聊天模型可分开）。 |
| `CRATE_EMBEDDING_BASE_URL` / `CRATE_EMBEDDING_MODEL` | 可选。默认 OpenAI 兼容嵌入端点与 `text-embedding-3-small`。**须与密钥同属一家服务商**（勿把 DeepSeek 聊天 Key 配到阿里云/OpenAI 等嵌入地址）。 |
| `CRATE_EMBEDDING_BATCH_SIZE` | 可选。每次嵌入 API 请求的文本条数上限，默认 **10**（阿里云 DashScope 单请求最多 10 条）。使用 OpenAI 等可承受更大批次时可设为 **64** 等以加快索引。 |
| `CRATE_GATE_WIKI_WORDS` 等 | 可选。规模门闸阈值（见 `crate stats`）。 |

CLI 会 **`load_dotenv()`**：可在 vault 或项目根目录放置 **`.env`**（且将 `.env` 保持在本机/`.gitignore` 中），避免在 shell 里反复 `export`。

---

## 4. 命令一览

| 命令 | 作用 |
|------|------|
| `crate init [--vault PATH] [--force]` | 创建标准目录与占位文件（`raw/`、`wiki/`、`meta/` 等）。 |
| `crate compile [--vault PATH] [--quiet-gate]` | 读取 `raw/**/*.md` 与 **`raw/**/*.pdf`**，生成 `wiki/notes/` 编译笔记；可选抑制门闸提示。 |
| `crate ask [--vault PATH] [--no-feedback] [--session ID] <问题…>` | 工具型问答；**`--session`** 配合 **`ephemeral init`** 可写 `_ephemeral/`。 |
| `crate lint [--vault PATH] [--json] [--include-ephemeral]` | 检查 `wiki/` 下 Markdown **相对链接**；默认跳过 `_ephemeral/`。 |
| `crate search [--vault PATH] [--json] [--semantic] <词…>` | 字面量子串搜索；**`--semantic`** 需先 **`crate index`** 与嵌入 API。 |
| `crate stats [--vault PATH] [--json] [--gates-json] [--strict]` | 统计词数/文件数；**`--gates-json`** 只打印门闸 JSON（无需 **jq**）。 |
| `crate index [--vault PATH] [--reset]` | 为 `raw`/`wiki` 下 Markdown 分块建 **`meta/embeddings.sqlite`**。 |
| `crate ephemeral init|finalize|clean` | 短命维基目录 **`wiki/_ephemeral/<id>/`** 的创建、打包到 `wiki/outputs/FINAL_*.md`、按 TTL 清理。 |

全局参数：**`--vault`** — 指定 vault 根路径；省略则为当前目录。

---

## 5. 各命令说明

### 5.1 `crate init`

- 创建目录（示例）：`raw/papers`、`raw/web-clips`、`raw/assets/images`、`wiki/_index`、`wiki/concepts`、`wiki/notes`、`wiki/outputs`、`meta`。
- 写入占位文件：`wiki/_index/TOPICS.md`、`wiki/_index/RECENT.md`、`VAULT.md`，以及 `AGENTS.md`、`meta/compile_state.json` 等。
- **`--force`**：若目标文件已存在，仍覆盖更新（慎用）。
- 成功时向 stderr 打印 vault 路径，stdout 列出相对路径。

### 5.2 `crate compile`

- 递归收集 **`raw/` 下所有 `.md` 与 `.pdf`**。Markdown 直接读入；PDF 仅抽取**可选中文本层**（扫描版/纯图 PDF 可能几乎无字，编译提示里会说明）。
- 按文件拼接为提示内容（**每个文件**有长度上限，超出会截断并标注）。
- 若无任何 `raw/**/*.md` 或 `**/*.pdf`，仍会生成笔记，但内容会提示先添加源文件。
- 产出：写入 **`wiki/notes/compile-<UTC时间戳>-<slug>.md`**，带 YAML front matter（`kind: compile_run`、`sources`、`model`、`created` 等）。
- 需要有效的 DeepSeek API 密钥（见第 3 节）。

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
- **`--gates-json`**：只输出 JSON 里的 **`gates`** 对象（含 `triggered`、`reasons`、`thresholds`），便于脚本判断，**不必安装 jq**。若仍想用管道，可执行 `crate stats --json | jq .gates`（需本机已安装 **jq**；未安装时请用 **`--gates-json`**）。

### 5.6 `crate ephemeral`

- **`init`**：创建 **`wiki/_ephemeral/<新 id>/`**，stdout 打印 **session id**。
- **`finalize <session_id>`**：将该目录下各 `.md` 拼入 **`wiki/outputs/FINAL_<id>.md`**；**`--delete`** 在成功后删除 ephemeral 目录。
- **`clean --older-than DAYS`**：按目录 mtime 删除过期 ephemeral 子目录。

### 5.7 `crate lint`

- 扫描 wiki 下 Markdown 的相对链接，检查目标文件是否存在（实现以当前代码为准）。
- 默认**不**检查 **`wiki/_ephemeral/**`**；需要时用 **`--include-ephemeral`**。
- 默认人类可读输出：`文件:行: 信息`。
- **`--json`**：以 JSON 数组输出结构化问题列表，便于脚本集成。
- 无问题时退出码 **0**；有问题为 **1**。

---

## 6. 目录与文件约定（摘要）

| 路径 | 说明 |
|------|------|
| `raw/` | 原始采集；**编译器不应覆盖**其中的源文件。 |
| `wiki/notes/` | `compile` 生成的笔记。 |
| `wiki/outputs/` | `ask` 默认最终产出。 |
| `wiki/_ephemeral/<id>/` | 短命草稿（**`ephemeral init`** + **`ask --session`**）。 |
| `meta/embeddings.sqlite` | 语义索引（**`crate index`**）。 |
| `wiki/_index/TOPICS.md`、`RECENT.md` | 主题索引与最近变更；`RECENT` 可被问答回流更新。 |
| `meta/` | 如 `compile_state.json` 等构建状态。 |
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
crate lint
crate ask 这篇 raw 笔记的核心概念是什么？
```

在**另一目录**打开终端时：

```bash
crate --vault /path/to/my-vault compile
crate --vault /path/to/my-vault ask 列出 wiki 里最近关于 X 的片段
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

---


## 8. 常见问题

- **提示未设置 API Key**：设置 `CRATE_DEEPSEEK_API_KEY` 或 `DEEPSEEK_API_KEY`，或配置 `.env` 后在同一工作目录运行。
- **`ModuleNotFoundError: No module named 'pypdf'`**：在项目环境中执行 `pip install -e .` 或 `pip install pypdf`，确保与 `crate` 命令使用同一 Python 环境。
- **compile 结果为空或很短**：检查 `raw/` 是否确有 `.md`/`.pdf`；模型是否返回异常可查看生成文件内容。
- **PDF 似乎没被“读到”**：确认文件在 `raw/` 下且扩展名为 `.pdf`；若为扫描件，需先 OCR 成文本或转为 Markdown 再放入 `raw/`。
- **`crate search --semantic` 无结果或报错**：先执行 **`crate index`**；并设置 **`CRATE_EMBEDDING_API_KEY`** 或 **`OPENAI_API_KEY`**；索引文件应在 **`meta/embeddings.sqlite`**。
- **`vault_search_semantic` 提示无索引**：同上，完成 `crate index` 后再问答或语义搜索。
- **`crate index` 报 401 / invalid API key**：嵌入接口与聊天接口密钥一般不同；为 **`CRATE_EMBEDDING_BASE_URL`** 配置**对应平台**的 Key（如阿里云百炼/Model Studio 的 API Key），并设置该平台支持的 **`CRATE_EMBEDDING_MODEL`**，勿复用 **`CRATE_DEEPSEEK_API_KEY`**。
- **lint 失败**：根据输出修正断链，或使用 `--json` 交给脚本处理；草稿在 `_ephemeral` 时默认不 lint，需要时加 **`--include-ephemeral`**。
- **密钥泄露**：若曾误提交密钥，应**轮换** DeepSeek 侧 Key，并清理 Git 历史（必要时）。

---

## 9. 相关文档

| 文档 | 内容 |
|------|------|
| [README.md](../README.md) | 仓库说明、安装、CLI 速览、路线图 |
| [obsidian.md](obsidian.md) | 与 Obsidian 共用 vault 的简要教程 |
| [technical-design.md](technical-design.md) | 架构与 vault 设计 |
| [PRD.md](PRD.md) | 需求与里程碑 |
| [lessons-learned.md](lessons-learned.md) | 缺陷与预防记录 |
