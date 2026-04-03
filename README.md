# CRATE

**Compile Raw Archives, Tracked in the vault, into Encyclopedic wiki.**

CRATE is a **file-first personal knowledge compiler**: ingest messy **raw** captures (notes, papers, clips, repos), keep provenance in your **vault**, and iteratively **compile** them into a navigable **wiki**—with lightweight retrieval, linting, and optional feedback loops back into compilation.

> 中文释义：**CRATE** = 把散落在各处的 **raw**，以 **vault** 为单一事实来源，**增量编译**成可互链的 **wiki**（百科全书式知识库）。

---

## Documentation

Design docs below are **in Chinese** (中文).

- **[docs/README.md](docs/README.md)** — 文档索引
- **[docs/PRD.md](docs/PRD.md)** — 产品需求与里程碑
- **[docs/technical-design.md](docs/technical-design.md)** — 架构、vault 布局、编译 / 问答 / Lint

---

## Why CRATE

- **Local-first**: Markdown trees, not a black-box SaaS library.
- **Incremental**: Short-lived wiki passes; re-run compilation as sources change.
- **Inspectable**: Diff-friendly outputs (wiki pages, slides, figures) you can review like code.
- **Agent-ready**: Room for a QA/RAG layer that reads *relevant pages* instead of dumping the whole corpus into context.

Design inspiration comes from the idea of treating an LLM as a **compiler** over your own materials—not a one-shot chat endpoint. (See [Andrej Karpathy’s thread on LLM knowledge bases](https://x.com/karpathy/status/2039805659525644595).)

---

## What’s in scope

| Stage        | Intent |
|-------------|--------|
| **Raw ingest** | Web clipper, repo snapshots, PDFs, images—anything that enters the pipeline. |
| **Vault**      | Versioned, observable store: raw + compiled artifacts share one traceable home. |
| **Wiki compile** | LLM-driven structuring: summaries, concepts, backlinks, directory tree. |
| **Outputs**    | Markdown, optional Marp/deck exports, small charts—whatever you treat as “release artifacts”. |
| **Health / lint** | Consistency checks, gaps, new terms, optional “wiki checkup” passes. |
| **Enrich loop** | Feed outputs or lint findings back into the compiler for the next pass. |

## Non-goals (for now)

- Replacing a full-featured PKM app (e.g. calendar, tasks, spaced repetition).
- A hosted multi-tenant cloud—CRATE is oriented around **your** vault and **your** toolchain.

---

## Repository layout

```
crate/
├── README.md
├── pyproject.toml
├── environment.yml        # Conda 环境（可选，与 Anaconda/Miniconda 配合）
├── docs/                  # PRD, technical design (see docs/README.md)
├── prompts/               # Prompt templates for compile / architecture / codegen
├── scripts/               # Automation (e.g. optional AI PR review)
├── src/crate/             # Python package
├── tests/
├── .cursor/rules/         # Cursor agent guidance
├── .vscode/               # Conda 路径与本机解释器（可选）
├── .devcontainer/         # Optional VS Code Dev Container
└── .github/               # CI, issue/PR templates, optional AI review workflow
```

Example **vault** trees (user data, often outside this repo) are described in [docs/technical-design.md](docs/technical-design.md).

---

## Getting started

### Conda（Anaconda 默认安装路径）

若本机使用 Anaconda 且 `conda` 位于 `/opt/anaconda3/condabin/conda`，可用仓库中的 [`environment.yml`](environment.yml) 一键创建名为 **`crate`** 的环境（Python 3.11，并以可编辑方式安装 `[dev]` 依赖）：

```bash
git clone https://github.com/<you>/crate.git
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
git clone https://github.com/<you>/crate.git
cd crate
python3 -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
pre-commit install
pytest -q
```

### Dev Container

Open the repo in VS Code and select “Reopen in Container” to use [`.devcontainer/devcontainer.json`](.devcontainer/devcontainer.json) (Python 3.11, editable install, pre-commit).

### Optional AI PR review

The workflow [`.github/workflows/ai-code-review.yml`](.github/workflows/ai-code-review.yml) runs only when repository secret `OPENAI_API_KEY` is set. Override model with `OPENAI_REVIEW_MODEL` if needed.

---

## Roadmap (aligned with docs/PRD.md)

| Phase | Focus |
|-------|--------|
| **M0** | Vault contract + manual compile proof-of-concept + minimal lint |
| **M1** | Q&A agent + file outputs + feedback into the wiki |
| **M2** | Search CLI + scale gates + optional vectors |
| **M3** | Ephemeral “question wiki” orchestration (advanced) |

Adjust priorities via Issues.

---

## Contributing

Open a PR using the template, or start with an Issue describing:

- Use case (what raw → what wiki shape you want),
- Constraint (local-only, model X, vault tool Y),
- Acceptance idea (how you’d know the compile pass succeeded).

---

## License

**Apache-2.0**.

---

## Etymology

The name **CRATE** expands to:

- **C**ompile
- **R**aw
- **A**rchives
- **T**racked in the **vault**
- **E**ncyclopedic wiki

This matches the tagline at the top: *Compile Raw Archives, Tracked in the vault, into Encyclopedic wiki.*
