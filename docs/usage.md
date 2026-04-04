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

---

## 3. 环境变量与密钥（LLM）

`compile` 与 `ask` 通过 **OpenAI 兼容客户端** 调用 **DeepSeek**（默认 `https://api.deepseek.com`，模型 `deepseek-chat`）。

| 变量 | 含义 |
|------|------|
| `CRATE_DEEPSEEK_API_KEY` 或 `DEEPSEEK_API_KEY` | **必填**（二选一）。用于编译与问答，**勿写入代码或提交到 Git**。 |
| `CRATE_DEEPSEEK_BASE_URL` | 可选。覆盖 API 基址（默认见上）。 |
| `CRATE_DEEPSEEK_MODEL` | 可选。覆盖模型名（默认 `deepseek-chat`）。 |

CLI 会 **`load_dotenv()`**：可在 vault 或项目根目录放置 **`.env`**（且将 `.env` 保持在本机/`.gitignore` 中），避免在 shell 里反复 `export`。

---

## 4. 命令一览

| 命令 | 作用 |
|------|------|
| `crate init [--vault PATH] [--force]` | 创建标准目录与占位文件（`raw/`、`wiki/`、`meta/` 等）。 |
| `crate compile [--vault PATH]` | 读取 `raw/**/*.md` 与 **`raw/**/*.pdf`**（PDF 用 [pypdf](https://pypi.org/project/pypdf/) 抽正文），调用模型生成一篇编译笔记到 `wiki/notes/`。 |
| `crate ask [--vault PATH] [--no-feedback] <问题…>` | 工具型问答：读 vault、可写 `wiki/outputs/`，默认回流一行到 `wiki/_index/RECENT.md`。 |
| `crate lint [--vault PATH] [--json]` | 检查 `wiki/` 下 Markdown **相对链接**是否解析到存在的文件；有问题时退出码为 **1**。 |

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
- 代理通过工具访问 vault：**`vault_read`**、**`vault_search`**、**`vault_write_output`**（**仅允许写入 `wiki/outputs/**`**）。
- 运行结束后在 stdout 打印**产出文件相对 vault 的路径**（通常为 `wiki/outputs/` 下某文件）。
- **`--no-feedback`**：不向 **`wiki/_index/RECENT.md`** 追加链接行；默认会追加一行（时间戳 + 问题摘要 + 指向该产出）。

空问题会返回退出码 **2**。

### 5.4 `crate lint`

- 扫描 wiki 下 Markdown 的相对链接，检查目标文件是否存在（实现以当前代码为准）。
- 默认人类可读输出：`文件:行: 信息`。
- **`--json`**：以 JSON 数组输出结构化问题列表，便于脚本集成。
- 无问题时退出码 **0**；有问题为 **1**。

---

## 6. 目录与文件约定（摘要）

| 路径 | 说明 |
|------|------|
| `raw/` | 原始采集；**编译器不应覆盖**其中的源文件。 |
| `wiki/notes/` | `compile` 生成的笔记。 |
| `wiki/outputs/` | `ask` 代理**唯一允许写入**的产出区（工具约束）。 |
| `wiki/_index/TOPICS.md`、`RECENT.md` | 主题索引与最近变更；`RECENT` 可被问答回流更新。 |
| `meta/` | 如 `compile_state.json` 等构建状态。 |
| `VAULT.md` | vault 内简短说明。 |

更完整的布局与流程见 [technical-design.md](technical-design.md)。

---

## 7. 典型工作流示例

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

---

## 8. 常见问题

- **提示未设置 API Key**：设置 `CRATE_DEEPSEEK_API_KEY` 或 `DEEPSEEK_API_KEY`，或配置 `.env` 后在同一工作目录运行。
- **compile 结果为空或很短**：检查 `raw/` 是否确有 `.md`/`.pdf`；模型是否返回异常可查看生成文件内容。
- **PDF 似乎没被“读到”**：确认文件在 `raw/` 下且扩展名为 `.pdf`；若为扫描件，需先 OCR 成文本或转为 Markdown 再放入 `raw/`。
- **lint 失败**：根据输出修正断链，或使用 `--json` 交给脚本处理。
- **密钥泄露**：若曾误提交密钥，应**轮换** DeepSeek 侧 Key，并清理 Git 历史（必要时）。

---

## 9. 相关文档

| 文档 | 内容 |
|------|------|
| [README.md](../README.md) | 仓库说明、安装、CLI 速览、路线图 |
| [technical-design.md](technical-design.md) | 架构与 vault 设计 |
| [PRD.md](PRD.md) | 需求与里程碑 |
| [lessons-learned.md](lessons-learned.md) | 缺陷与预防记录 |
