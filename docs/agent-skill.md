# 通用 Agent Skill（CRATE vault）

仓库内 **唯一真源**：[agent-skills/crate-vault/SKILL.md](../agent-skills/crate-vault/SKILL.md)。内容为 **YAML frontmatter + Markdown**，与 IDE 无关；各宿主通过「复制文件」或「指向路径」加载。

## Cursor

1. 将 **`agent-skills/crate-vault/`** 整个目录复制到项目 **`.cursor/skills/crate-vault/`**，或复制到用户目录 **`~/.cursor/skills/crate-vault/`**。
2. **不要**写入 `~/.cursor/skills-cursor/`（系统保留）。

## Claude Code

- 将同一目录纳入 Git，或在 **`AGENTS.md`** 中增加一节：「CRATE：遵循 `agent-skills/crate-vault/SKILL.md`」。
- 或在对话中用 **`@agent-skills/crate-vault/SKILL.md`**（若客户端支持文件引用）。

## OpenClaw / 其它 CLI 或自托管 Agent

- 在配置里将 **instructions / skills / rules** 指向仓库内该 **`SKILL.md`** 的绝对路径；或启动参数中附加该文件（具体键名以各产品文档为准）。
- 无专用目录时：把 **`SKILL.md`** 全文粘贴为系统提示附件即可。

## 其它编辑器 / 自定义流程

- 作为「用户规则」「项目指令」或团队模板中的 **单文件** 使用；更新时以仓库内 `agent-skills/crate-vault/SKILL.md` 为准。
