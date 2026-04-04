# CRATE 与 Obsidian 搭配使用

Obsidian 是**本地 Markdown 库**；CRATE 是**在同一套文件上跑编译、问答、检索**的 CLI。二者搭配的核心是：**Obsidian 打开的「库」根目录 = CRATE 的 vault 根目录**（或对其使用 `crate --vault`）。

更通用的 CLI 与目录说明见 [usage.md](usage.md)。

---

## 1. 关系一句话

| 工具 | 做什么 |
|------|--------|
| **Obsidian** | 浏览、编辑、双链、图谱、搜索界面；你主要在这里**读** `wiki/`、**写** `raw/` 或随手记。 |
| **CRATE** | 在终端里对**同一文件夹**执行 `compile` / `ask` / `index` / `search`；产出落在 `wiki/`、`meta/`。 |

CRATE **不替代** Obsidian；它负责「把 raw 材料编译进 wiki、可脚本化检索」这一层。

---

## 2. 推荐目录布局（与 CRATE 一致）

在 vault 根目录（即 Obsidian 库根）保持 CRATE 约定即可，例如：

```
你的-Obsidian-库/
├── .obsidian/              # Obsidian 配置（主题、插件等）
├── .env                    # 本机密钥（勿提交 Git）
├── raw/                    # 原始材料：剪藏、论文、随手 md/pdf
├── wiki/                   # 编译与问答产出
│   ├── notes/              # compile 生成的笔记
│   ├── outputs/            # ask 默认产出
│   ├── _index/             # TOPICS、RECENT 等
│   └── …
├── meta/                   # compile 状态、embeddings.sqlite 等
├── VAULT.md
└── AGENTS.md
```

首次可在该根目录执行：

```bash
cd /path/to/你的-Obsidian-库
crate init
```

若库已存在、只想补目录，同样可用 `crate init`（已有文件默认不覆盖，除非 `--force`）。

---

## 3. 在 Obsidian 里打开

1. Obsidian：**「打开本地库」**，选择上述 **vault 根文件夹**（包含 `raw/`、`wiki/` 的那一层）。
2. 之后你在 Obsidian 里新建/编辑的 `.md`，只要落在 `raw/` 或 `wiki/` 下，CRATE 就能按规则索引或编译。

**库根不要选错成**「只含笔记子文件夹」若你希望 `crate` 默认在库根运行；若项目结构较深，始终在终端用 `crate --vault /绝对路径/到/库根` 即可。

---

## 4. 日常协作流程（简版）

1. **采集**：在 Obsidian 或外部工具把材料放进 `raw/`（如 `raw/web-clips/xxx.md`、`raw/papers/foo.pdf`）。
2. **编译**：在终端（库根或任意目录加 `--vault`）：
   ```bash
   crate compile
   ```
   阅读 **`wiki/notes/`** 下新生成的编译笔记；可在 Obsidian 图谱里打开相关文件。
3. **问答**：  
   ```bash
   crate ask 根据 raw 里关于 X 的材料，总结三个要点
   ```
   产出一般在 **`wiki/outputs/`**，在 Obsidian 中直接打开该 md。
4. **语义检索（可选）**：配置嵌入 API 后：
   ```bash
   crate index
   ```
   再用 `crate search --semantic "…"`；索引文件在 **`meta/embeddings.sqlite`**。

在 Obsidian 里可固定收藏 **`wiki/_index/TOPICS.md`**、**`RECENT.md`**（若使用默认回流）作为入口。

---

## 5. 链接：Wiki 链接 vs 相对路径

- Obsidian 常用 **`[[双链]]`**（wikilink），CRATE 的 **`crate lint`** 主要检查 **Markdown 标准相对路径**（如 `[text](wiki/concepts/foo.md)`）。  
- 若你**大量使用** `[[...]]` 而不写相对路径，**lint 报断链的情况可能变少或语义不同**——这是预期差异；需要「可脚本校验的链接」时，在关键导航页可兼用相对路径。

---

## 6. Git 与忽略项

若用 Git 管理库：

- **务必忽略** `.env`（密钥）。
- 常见可选忽略：`meta/embeddings.sqlite`（可重建）、`.obsidian/workspace` 等（团队若需统一工作区再议）。
- `wiki/notes/`、`wiki/outputs/` 是否纳入版本库：按你是否希望「编译结果」可回溯、可 diff 决定。

---

## 7. 与 CRATE 代码仓库分开放（推荐）

- **CRATE 项目克隆**（本 GitHub 仓库）与**个人知识库文件夹**可以是两个目录。
- 日常在**知识库目录**打开 Obsidian；在终端 `cd` 到该目录执行 `crate`，或：
  ```bash
  crate --vault ~/知识库/MyVault compile
  ```
- 这样 Obsidian 里不会出现大量 Python 源码，结构更清晰。

---

## 8. 常见问题

- **Obsidian 里改了文件，compile 会用新版本吗？**  
  会。`compile` 每次读取磁盘上当前 `raw/**/*.md` 与 `**/*.pdf`。

- **能在 Obsidian 移动端用 CRATE 吗？**  
  CRATE 在电脑终端运行；移动端仍可用 Obsidian 读已同步过来的 `wiki/`。编译需在装有 Python/`crate` 的环境执行。

- **图谱很乱？**  
  可把入口收窄到 `wiki/` 与 `raw/`，少用根目录散落 md；或用 Obsidian 的「排除文件夹」类插件隐藏 `meta/`（若不需要看）。

---

## 9. 相关文档

| 文档 | 内容 |
|------|------|
| [usage.md](usage.md) | 环境变量、全部子命令、FAQ |
| [technical-design.md](technical-design.md) | vault 架构与数据流 |
