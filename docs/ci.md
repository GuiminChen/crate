# CI：CRATE 源码仓库与个人 vault 仓库

## 本仓库（crate CLI）

默认使用根目录 [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)：`pre-commit`、`pytest`、覆盖率。

[`.github/workflows/crate-vault.yml`](../.github/workflows/crate-vault.yml) 在临时目录执行 `crate init`、`crate doctor --strict`、`crate lint`，作为 **无密钥** 的 CLI 冒烟（不调用 `compile`）。

## 个人 vault 仓库（仅 Markdown 树 + 可选 crate）

在 **vault 根目录** 已有 `raw/`、`wiki/`、`meta/`（例如已运行过 `crate init`）时，可在该仓库添加 workflow，在 PR 上跑确定性检查。

### 环境变量与密钥

- **`compile` / `ask` / `wiki-check`** 需要 LLM 与（可选）嵌入 API，**不要**把 `.env` 提交进 Git；在 CI 中若只做 **lint / doctor / report**，无需这些密钥。
- 若将来在 CI 中跑 `compile`，使用 GitHub **Secrets** 注入 `OPENAI_API_KEY` 或项目文档中的 `CRATE_*` 变量（自行评估风险）。

### 示例 workflow（复制到 vault 仓库 `.github/workflows/crate.yml`）

将下面 `pip install` 一行改为你的安装方式（例如从 PyPI、私有 wheel，或 `git+https://github.com/<org>/<crate-fork>.git`）。

```yaml
name: vault-crate-check

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install crate CLI
        run: pip install "crate @ git+https://github.com/OWNER/crate.git"

      - name: Layout
        run: crate doctor --strict

      - name: Lint
        run: crate lint --wikilinks --strict-concepts
```

按需删除 `--strict-concepts`（无 `meta/wiki_index.json` 时可能不适用）。外链 HTTP 检查可加 `crate lint --http-external`（依赖网络，易抖；可设 `SKIP_HTTP_LINT=1` 跳过）。

### 参考命令（本地与 CI 对齐）

```bash
crate doctor --strict
crate lint --wikilinks --orphans
crate wiki graph
crate report raw-wiki --write
```
