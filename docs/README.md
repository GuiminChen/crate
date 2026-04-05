# CRATE 文档索引

| 文档 | 说明 |
|------|------|
| [usage.md](usage.md) | **使用说明**：安装、vault、`crate` 子命令、环境变量、目录约定、示例、**[Karpathy 对照（§7.5）](usage.md#karpathy-style-comparison)**、常见问题。 |
| [roadmap.md](roadmap.md) | **路线图**：相对 PRD 的待实现项、当前状态与增量编译语义说明（含 `watch` / `serve-search` 进展）。 |
| [obsidian.md](obsidian.md) | **与 Obsidian 搭配**：库根即 vault、日常流程、链接与 Git 注意。 |
| [PRD.md](PRD.md) | 产品需求：愿景、用户故事、MVP/V1/V2、功能与非功能需求、风险、里程碑。 |
| [technical-design.md](technical-design.md) | 技术方案：架构、`vault` 布局、编译 / 问答 / Lint 流程、检索门闸、安全与可观测性。 |
| [lessons-learned.md](lessons-learned.md) | 缺陷复盘与预防（与测试、变更同步维护）。 |

**CRATE**（**C**ompile **R**aw **A**rchives，**T**racked in the **vault**，into **E**ncyclopedic **wiki**）是一条 **本地优先、文件优先** 的流水线：从 `raw/` 采集到由 LLM 参与维护的互联 `wiki/`。仓库定位与快速入口见根目录 [README.md](../README.md)。

## 外部参考（灵感来源）

- [Andrej Karpathy 关于 LLM 知识库的帖文（X）](https://x.com/karpathy/status/2039805659525644595)
- [Thread Reader 同串整理](https://threadreaderapp.com/thread/2039805659525644595.html)

以上链接用于问题陈述的启发；**CRATE 为独立产品化抽象**，并非任何第三方工作流的官方实现。
