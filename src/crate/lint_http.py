"""Optional HTTP checks for ``https?://`` targets in markdown links."""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from crate.lint_wiki import LintIssue
from crate.vault_paths import VaultContext, VaultPathError

_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

__all__ = ["lint_http_external_links"]


def _http_check_one(url: str, timeout: float) -> tuple[bool, str]:
    """Return (ok, detail). Uses HEAD, falls back to GET on HTTP 405."""
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    req = Request(
        url,
        headers={"User-Agent": "crate-lint/1.0 (+https://github.com/GuiminChen/crate)"},
        method="HEAD",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            code = getattr(resp, "status", resp.getcode())
            if 200 <= int(code) < 400:
                return True, ""
            return False, f"HTTP {code}"
    except HTTPError as e:
        if e.code == 405:
            req_g = Request(
                url,
                headers={
                    "User-Agent": "crate-lint/1.0 (+https://github.com/GuiminChen/crate)"
                },
                method="GET",
            )
            try:
                with urlopen(req_g, timeout=timeout) as resp:
                    code = getattr(resp, "status", resp.getcode())
                    if 200 <= int(code) < 400:
                        return True, ""
                    return False, f"HTTP {code}"
            except OSError as e2:
                return False, str(e2)
        return False, f"HTTP {e.code}"
    except URLError as e:
        return False, str(e.reason if hasattr(e, "reason") else e)
    except OSError as e:
        return False, str(e)


def _iter_http_link_occurrences(path: str, lines: list[str]) -> list[tuple[int, str]]:
    """(line, url) for http(s) in ``[text](url)`` in prose (fences skipped)."""
    out: list[tuple[int, str]] = []
    in_fence = False
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in _MD_LINK_RE.finditer(line):
            href = m.group(1).strip()
            low = href.split("?", 1)[0].split("#", 1)[0].lower()
            if not (low.startswith("http://") or low.startswith("https://")):
                continue
            out.append((i, href))
    return out


def lint_http_external_links(
    ctx: VaultContext,
    *,
    include_ephemeral: bool = False,
    timeout: float = 10.0,
    concurrency: int = 1,
) -> list[LintIssue]:
    """
    Check external ``http(s)`` URLs in wiki ``[text](url)`` links.

    Set ``SKIP_HTTP_LINT=1`` to skip (e.g. flaky CI).
    """
    skip = os.environ.get("SKIP_HTTP_LINT", "").strip().lower()
    if skip in ("1", "true", "yes", "on"):
        return []

    wiki = ctx.wiki_dir()
    if not wiki.is_dir():
        return []

    occurrences: list[tuple[str, int, str]] = []
    for path in sorted(wiki.rglob("*.md")):
        if not path.is_file():
            continue
        try:
            ctx.validate_under_vault(path)
        except VaultPathError:
            continue
        rel_parts = path.relative_to(ctx.root).parts
        if not include_ephemeral and "_ephemeral" in rel_parts:
            continue
        rel = path.relative_to(ctx.root).as_posix()
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, url in _iter_http_link_occurrences(rel, lines):
            occurrences.append((rel, line_no, url))

    if not occurrences:
        return []

    unique_urls = sorted({u for _, _, u in occurrences})
    results: dict[str, tuple[bool, str]] = {}
    conc = max(1, int(concurrency))

    def _check(u: str) -> tuple[str, tuple[bool, str]]:
        return u, _http_check_one(u, timeout)

    if conc == 1:
        for u in unique_urls:
            results[u] = _http_check_one(u, timeout)
    else:
        with ThreadPoolExecutor(max_workers=conc) as ex:
            futs = {ex.submit(_http_check_one, u, timeout): u for u in unique_urls}
            for fut in as_completed(futs):
                u = futs[fut]
                try:
                    ok, detail = fut.result()
                    results[u] = (ok, detail)
                except Exception as exc:  # noqa: BLE001
                    results[u] = (False, str(exc))

    issues: list[LintIssue] = []
    for rel, line_no, url in occurrences:
        ok, detail = results.get(url, (False, "missing check"))
        if ok:
            continue
        issues.append(
            LintIssue(
                file=rel,
                line=line_no,
                kind="http_check_failed",
                target=url,
                message=f"HTTP check failed: {detail or url}",
            )
        )
    return issues
