# Obsidian 插件（可选）

源码位于仓库 **[obsidian-plugin/crate/](../obsidian-plugin/crate/)**：在 Obsidian 中快速打开 CRATE 导航页，并在**桌面端**调用本机 **`crate doctor`**。

## 功能（MVP）

- **命令面板**：「Open wiki/_index/INDEX.md」「Open meta/wiki_index.json」「Run crate doctor」。
- **设置**：**crate executable** — `crate` 命令或绝对路径（需已安装 Python 包 `crate` 且可在 shell 中运行）。

## 从文件夹安装

1. 在本仓库 **`obsidian-plugin/crate/`** 目录执行 **`npm install`**（可选）与 **`npm run build`**；若已包含预生成的 **`main.js`**，可直接下一步。
2. 将整个 **`crate`** 文件夹复制到 vault 的 **`.obsidian/plugins/crate/`**（文件夹名须与 **`manifest.json`** 的 **`id`** 字段一致）。
3. 重启 Obsidian 或刷新插件列表，在 **第三方插件** 中启用 **CRATE**。

## BRAT

在 [BRAT](https://github.com/TfTHacker/obsidian42-brat) 中可使用本 Git 仓库 URL 与子路径 **`obsidian-plugin/crate`**（具体以 BRAT 版本说明为准）。

## 限制

- 仅 **桌面端**（需 `child_process` 与本地 vault 路径）；不提供同步/协同。
- 不内置运行 **`compile`** / **`ask`**（避免在笔记应用内隐式消耗 API）。
