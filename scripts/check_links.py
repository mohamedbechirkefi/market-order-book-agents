# SPDX-License-Identifier: LicenseRef-MARKET-NC-Research-1.0
"""Check that every relative link and image in the tracked Markdown files resolves (M6).

A link ``[text](target)`` or image ``![alt](target)`` whose target is not a URL (http, https,
mailto) must point to an existing file or folder, relative to the Markdown file. A ``#anchor``
(alone or after a Markdown path) must match a heading of the target file, using GitHub's slug
rule (lower case, punctuation removed, spaces to hyphens). Links inside fenced code blocks and
inline code are ignored.

Usage: .venv/bin/python scripts/check_links.py   (exit 0 and "LINK-CHECK PASS" when all resolve)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
FENCE = re.compile(r"^(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")


def markdown_files(root: Path = ROOT) -> list[Path]:
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=root, capture_output=True, text=True, check=True).stdout
    return [root / line for line in out.splitlines() if line and "node_modules/" not in line]


def slug(heading: str) -> str:
    s = heading.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    seen: dict[str, int] = {}
    out = set()
    in_code = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
        if m:
            base = slug(m.group(1))
            n = seen.get(base, 0)
            out.add(base if n == 0 else f"{base}-{n}")
            seen[base] = n + 1
    return out


def links(path: Path) -> list[tuple[int, str]]:
    out = []
    in_code = False
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE.match(line.lstrip()):
            in_code = not in_code
            continue
        if in_code:
            continue
        for m in LINK.finditer(INLINE_CODE.sub("", line)):
            out.append((i, m.group(1)))
    return out


def check(root: Path = ROOT) -> tuple[int, list[str]]:
    errors = []
    n = 0
    for md in markdown_files(root):
        for line, target in links(md):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                continue  # URL (http, https, mailto, ...)
            n += 1
            path_part, _, anchor = target.partition("#")
            dest = (md.parent / path_part).resolve() if path_part else md
            rel = md.relative_to(root)
            if not dest.exists():
                errors.append(f"{rel}:{line}: missing target {target}")
                continue
            if anchor and dest.is_file() and dest.suffix == ".md" and anchor not in anchors(dest):
                errors.append(f"{rel}:{line}: missing anchor {target}")
    return n, errors


def main() -> int:
    n, errors = check()
    for e in errors:
        print(e)
    files = len(markdown_files())
    if errors:
        print(f"LINK-CHECK FAIL: {len(errors)} of {n} relative links in {files} Markdown files do not resolve")
        return 1
    print(f"LINK-CHECK PASS: {n} relative links in {files} Markdown files resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
