"""Initialize a new CRATE vault directory tree."""

from __future__ import annotations

from pathlib import Path

from crate.vault_paths import VaultContext

__all__ = ["init_vault", "VAULT_README", "PLACEHOLDER_TOPICS", "PLACEHOLDER_RECENT"]

VAULT_README = """# CRATE vault

- `raw/` — 原始材料（勿由编译器覆盖源文件）
- `wiki/` — LLM 编译区（摘要、概念、索引、问答产出）
- `meta/` — 构建状态与报告（可选）

详见项目文档 `docs/technical-design.md`。
"""

PLACEHOLDER_TOPICS = """# 主题索引

由 `crate compile` incremental 维护。首次初始化占位。
"""

PLACEHOLDER_RECENT = """# 最近变更

由 `crate compile` / 回流 更新。
"""

DIRS: tuple[str, ...] = (
    "raw/papers",
    "raw/web-clips",
    "raw/assets/images",
    "wiki/_index",
    "wiki/concepts",
    "wiki/notes",
    "wiki/outputs",
    "meta",
)

FILES: tuple[tuple[str, str], ...] = (
    ("wiki/_index/TOPICS.md", PLACEHOLDER_TOPICS),
    ("wiki/_index/RECENT.md", PLACEHOLDER_RECENT),
    ("VAULT.md", VAULT_README),
)


def init_vault(ctx: VaultContext, *, force: bool = False) -> list[Path]:
    """
    Create standard dirs and starter files. Missing parents are created.

    If a file already exists, it is not overwritten unless ``force`` is True.
    Returns list of paths created or updated.
    """
    created: list[Path] = []
    root = ctx.root
    root.mkdir(parents=True, exist_ok=True)
    for rel in DIRS:
        d = (root / rel).resolve()
        d.relative_to(ctx.root)
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)
    for rel, content in FILES:
        path = (root / rel).resolve()
        path.relative_to(ctx.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not force:
            continue
        path.write_text(content.strip() + "\n", encoding="utf-8")
        created.append(path)
    agents = root / "AGENTS.md"
    if not agents.exists() or force:
        agents.write_text(
            _default_agents_md().strip() + "\n",
            encoding="utf-8",
        )
        created.append(agents)
    state = root / "meta" / "compile_state.json"
    if not state.exists() or force:
        state.write_text("{}\n", encoding="utf-8")
        created.append(state)
    return created


def _default_agents_md() -> str:
    return """# Vault agent hints

- 编译写入仅限 `wiki/**`；不要覆盖 `raw/**` 中的源文件。
- 遵守 `VAULT.md` 与项目 `docs/technical-design.md` 中的 front-matter 约定。
"""
