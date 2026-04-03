# 缺陷复盘与经验（Lessons learned）

本文件记录 **已修复缺陷的简要复盘**，用于避免重复踩坑。Cursor / 协作者在处理 bugfix 时应按 [`.cursor/rules/lessons_from_bugs.md`](../.cursor/rules/lessons_from_bugs.md) 补充条目，并补上能防止回归的测试。

## 如何写一条记录

对每条 bugfix，复制下面模板，按日期倒序放在最上方新起一节：

```markdown
### YYYY-MM-DD — 简短标题

- **现象**：
- **根因**：
- **修复要点**：
- **预防 / 测试**：哪条用例或哪类检查现在覆盖此问题？
```

---

（尚无记录时保留本段；第一条复盘起可删除此行。）
