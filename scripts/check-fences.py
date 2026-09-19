#!/usr/bin/env python3
"""Verify Markdown code-fence integrity across the book.

Written after the research-branch review found two fence bug classes that every
existing validator missed (fence *parity* was even in both cases, so a naive
count passed while the rendered page was badly corrupted):

  1. Malformed openers. A `\\n` escape that leaked into the source as a literal
     `n`, plus a lost backtick, produced lines like ``n  or  ``  instead of
     ```. The author's *intended* closer then became an opener, and everything
     between the two swallowed 100+ lines of prose, headings and tables into a
     code block.

  2. Nested fences. A ```markdown template containing example ```bash blocks is
     invalid CommonMark: the inner fence closes the outer block early. The whole
     template must use a longer outer fence (````markdown ... ````).

Detection is CommonMark-correct: an opening fence is 0-3 spaces followed by 3+
backticks and an info string that contains no backticks; the matching closer is
a line of backticks at least as long as the opener carrying nothing else.

Usage: python3 scripts/check-fences.py [src-dir]
Exit status: 0 = clean, 1 = problems found.
"""
from __future__ import annotations

import os
import re
import sys

OPEN_FENCE = re.compile(r"^ {0,3}(`{3,})([^`]*)$")

# An opener written as two backticks (with an optional stray `n`) instead of
# three, optionally with the intended closer glued onto the same line.
MANGLED_OPENERS = [
    (re.compile(r"^\s*``\s*$"), "lone '``' where a fence opener was intended"),
    (re.compile(r"^\s*``n(?=[A-Za-z_])"), "mangled fence opener '``n'"),
    (re.compile(r"^\s*``n\s*$"), "mangled fence opener '``n'"),
    (re.compile(r"^\s*``n[^\n]*```\s*$"), "mangled opener and closer on one line"),
    (re.compile(r"^\s*``(?=[^`])[^\n]*```\s*$"), "spliced fence opener/closer on one line"),
]


def analyse(path: str) -> list[str]:
    """Return a list of human-readable problems for one file."""
    problems: list[str] = []
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")

    # --- class 1: malformed openers ---
    for i, line in enumerate(lines, 1):
        for pattern, why in MANGLED_OPENERS:
            if pattern.match(line):
                problems.append(f"line {i}: {why} -> {line.strip()[:70]!r}")
                break

    # --- CommonMark-correct fence walk ---
    in_fence = False
    opener_line = 0
    opener_len = 0
    opener_info = ""
    for i, line in enumerate(lines, 1):
        if not in_fence:
            m = OPEN_FENCE.match(line)
            if m:
                in_fence = True
                opener_line = i
                opener_len = len(m.group(1))
                opener_info = m.group(2).strip()
            continue

        stripped = line.strip()
        if re.fullmatch(r"`+", stripped) and len(stripped) >= opener_len:
            # A valid closer. Cross-check: if this "closer" carries an info
            # string it means the previous opener was closed too early — the
            # classic nested-fence signature.
            in_fence = False
            continue

    if in_fence:
        problems.append(
            f"line {opener_line}: unclosed code fence (opened with "
            f"{'`' * opener_len}{opener_info or ''}, never closed)"
        )

    # --- class 2: nested fences ---
    # A fenced block may contain inner fences ONLY if the inner fence is shorter
    # than the outer one (````markdown ... ```bash ... ``` ... ````). If an inner
    # opener is at least as long as the outer fence, its matching closer will
    # terminate the outer block instead, so the rest of the intended block leaks
    # out as prose.
    in_fence = False
    opener_line = 0
    opener_len = 0
    opener_info = ""
    for i, line in enumerate(lines, 1):
        if not in_fence:
            m = OPEN_FENCE.match(line)
            if m:
                in_fence = True
                opener_line = i
                opener_len = len(m.group(1))
                opener_info = m.group(2).strip()
            continue

        stripped = line.strip()
        if re.fullmatch(r"`+", stripped) and len(stripped) >= opener_len:
            in_fence = False
            continue

        inner = OPEN_FENCE.match(line)
        if inner and len(inner.group(1)) >= opener_len:
            problems.append(
                f"lines {opener_line}-{i}: fence opened as "
                f"{'`' * opener_len}{opener_info or ''} contains a nested "
                f"fence opener {inner.group(0).strip()!r} of equal-or-greater "
                f"length — its closer will terminate the outer block; widen the "
                f"outer fence (e.g. '````markdown') so the inner fence stays literal"
            )
            break

    return problems


def main() -> int:
    src = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "src")
    if not os.path.isdir(src):
        print(f"ERROR: {src} is not a directory")
        return 1

    files = []
    for dirpath, _dirs, names in os.walk(src):
        for name in names:
            if name.endswith(".md"):
                files.append(os.path.join(dirpath, name))
    files.sort()

    total = 0
    for path in files:
        problems = analyse(path)
        if problems:
            rel = os.path.relpath(path, src)
            print(f"{rel}")
            for p in problems:
                print(f"    {p}")
                total += 1

    print(f"\nFiles scanned: {len(files)}")
    print(f"Fence problems: {total}")
    if total:
        print("Fence integrity: FAIL")
        return 1
    print("Fence integrity: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
