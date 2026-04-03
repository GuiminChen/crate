# Bug fixes and lessons learned

## When you fix a bug

1. **Document the incident** in [docs/lessons-learned.md](../../docs/lessons-learned.md) **in the same change set** as the fix when practical (same branch / PR).
2. Each entry should be concise but actionable — use the template in that file’s header.
3. **Close the loop**: add or adjust a **unit test** that would have caught the bug (see [testing.md](testing.md)). The lesson entry should mention which test now guards against recurrence.
4. If the bug reveals a **recurring pattern** (e.g. path traversal, encoding, async races), add a one-line **“watch for”** note under a shared section in `docs/lessons-learned.md` so future work scans it.

## Goals

- Turn one-off fixes into **searchable history** and **automation** (tests), not just chat memory.
- Reduce repeat mistakes by making the **root cause** and **prevention** explicit.
