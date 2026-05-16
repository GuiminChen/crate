# CRATE 文档索引

| 文档 | 说明 |
|------|------|
| [usage.md](usage.md) | **使用说明**：安装、vault、`crate` 子命令（含 **`wiki graph`** / **`report raw-wiki`** / **`ingest`** / **`wiki index-extend`**）、环境变量、[providers.md](providers.md) 多平台模型、目录约定、示例、**[Karpathy 对照（§7.5）](usage.md#karpathy-style-comparison)**、常见问题。 |
| [roadmap.md](roadmap.md) | **路线图**：相对 PRD 的待实现项、当前状态与增量编译语义（含 `watch` / `serve-search`）；**§8** 为 Karpathy Gist **评论区实践摘要**与 CRATE 对照。 |
| [obsidian.md](obsidian.md) | **与 Obsidian 搭配**：库根即 vault、日常流程、链接与 Git 注意。 |
| [PRD.md](PRD.md) | 产品需求：愿景、用户故事、MVP/V1/V2、功能与非功能需求、风险、里程碑；**§12** 与 [llm-wiki.md](llm-wiki.md) 的逐条对照与差距。 |
| [llm-wiki.md](llm-wiki.md) | Karpathy《**LLM Wiki**》模式说明（英文；**权威正文**见 [Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)）；文末有指向本仓库 PRD/usage 的中文对照说明。 |
| [technical-design.md](technical-design.md) | 技术方案：架构、`vault` 布局、编译 / 问答 / Lint 流程、检索门闸、安全与可观测性。 |
| [providers.md](providers.md) | **多平台模型**：DeepSeek / OpenAI / 阿里 / 火山 / 腾讯 / OpenRouter / Azure、嵌入与 `CRATE_LLM_PROVIDER`。 |
| [ci.md](ci.md) | CI：`crate doctor` / `lint` 示例 workflow、vault 仓库模板。 |
| [agent-skill.md](agent-skill.md) | 通用 Agent Skill（[agent-skills/crate-vault/SKILL.md](../agent-skills/crate-vault/SKILL.md)）在各宿主的挂载方式。 |
| [obsidian-plugin.md](obsidian-plugin.md) | 可选 Obsidian 插件（打开 INDEX / `wiki_index.json`、运行 `crate doctor`）。 |
| [lessons-learned.md](lessons-learned.md) | 缺陷复盘与预防（与测试、变更同步维护）。 |

**CRATE**（**C**ompile **R**aw **A**rchives，**T**racked in the **vault**，into **E**ncyclopedic **wiki**）是一条 **本地优先、文件优先** 的流水线：从 `raw/` 采集到由 LLM 参与维护的互联 `wiki/`。仓库定位与快速入口见根目录 [README.md](../README.md)（英文）或 [README.zh.md](../README.zh.md)（简体中文）。

## 外部参考（灵感来源）

- [LLM Wiki（Karpathy，GitHub Gist 正文）](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — 权威出处
- [Andrej Karpathy 关于 LLM 知识库的帖文（X）](https://x.com/karpathy/status/2039805659525644595)
- [Thread Reader 同串整理](https://threadreaderapp.com/thread/2039805659525644595.html)
- [LLM Wiki（本仓库副本，便于离线 / 给 Agent）](llm-wiki.md)

以上链接用于问题陈述的启发；**CRATE 为独立产品化抽象**，并非任何第三方工作流的官方实现。
