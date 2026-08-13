#!/usr/bin/env python3
"""Verify mdBook MathJax configuration and Markdown math delimiters.

Usage:
    python3 scripts/check-mathjax.py [repo-path]
    python3 scripts/check-mathjax.py [repo-path] --book-dir book

The source check ignores fenced code blocks and inline-code spans. mdBook's
MathJax support expects escaped delimiters in Markdown source:
    inline: \\( ... \\)
    block:  \\[ ... \\]
Legacy $$...$$ display delimiters are rejected outside code because mdBook's
built-in MathJax support does not reliably recognize them.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BLOCK_OPEN = "\\\\["   # two backslashes followed by [ in source
BLOCK_CLOSE = "\\\\]"
INLINE_OPEN = "\\\\("
INLINE_CLOSE = "\\\\)"

# A single backslash delimiter is not the mdBook-compatible escaped form.
SINGLE_BLOCK_OPEN = re.compile(r"(?<!\\)\\\[")
SINGLE_BLOCK_CLOSE = re.compile(r"(?<!\\)\\\]")
SINGLE_INLINE_OPEN = re.compile(r"(?<!\\)\\\(")
SINGLE_INLINE_CLOSE = re.compile(r"(?<!\\)\\\)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", default=None, help="repository root; defaults to the parent of this script")
    parser.add_argument(
        "--book-dir",
        default=None,
        help="optional generated mdBook directory; checks that generated HTML includes MathJax",
    )
    return parser.parse_args()


def strip_inline_code(line: str) -> str:
    """Remove inline-code spans before checking math delimiters."""
    return re.sub(r"`+[^`]*?`+", "", line)


def source_check(repo: Path) -> tuple[dict, list[str]]:
    src = repo / "src"
    files = sorted(p for p in src.rglob("*.md") if p.name != "SUMMARY.md")
    errors: list[str] = []
    pages_with_math = 0
    block_open = block_close = inline_open = inline_close = 0
    legacy_dollar = 0
    raw_single = 0
    unclosed_fences: list[str] = []
    imbalanced: list[str] = []

    for path in files:
        rel = path.relative_to(repo).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        in_fence = False
        bo = bc = io = ic = dollars = singles = 0

        for line_number, raw_line in enumerate(text.splitlines(), 1):
            stripped = raw_line.lstrip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue

            line = strip_inline_code(raw_line)
            bo += line.count(BLOCK_OPEN)
            bc += line.count(BLOCK_CLOSE)
            io += line.count(INLINE_OPEN)
            ic += line.count(INLINE_CLOSE)
            dollars += line.count("$$")
            singles += sum(
                len(pattern.findall(line))
                for pattern in (
                    SINGLE_BLOCK_OPEN,
                    SINGLE_BLOCK_CLOSE,
                    SINGLE_INLINE_OPEN,
                    SINGLE_INLINE_CLOSE,
                )
            )

            if dollars:
                # Keep the location of the first legacy delimiter for a useful error.
                if dollars == line.count("$$"):
                    errors.append(f"{rel}:{line_number}: legacy $$ delimiter; use escaped \\\\[ ... \\\"]")

        if in_fence:
            unclosed_fences.append(rel)
        if bo or bc or io or ic:
            pages_with_math += 1
        block_open += bo
        block_close += bc
        inline_open += io
        inline_close += ic
        legacy_dollar += dollars
        raw_single += singles
        if bo != bc or io != ic:
            imbalanced.append(f"{rel}: block {bo}/{bc}, inline {io}/{ic}")

    # Remove duplicate line-level legacy errors while retaining source locations.
    errors = list(dict.fromkeys(errors))
    if not (repo / "book.toml").exists():
        errors.append("book.toml: file not found")
    else:
        book_toml = (repo / "book.toml").read_text(encoding="utf-8", errors="replace")
        if not re.search(r"^\s*mathjax-support\s*=\s*true\s*$", book_toml, re.MULTILINE):
            errors.append("book.toml: [output.html] mathjax-support = true is missing")

    if unclosed_fences:
        errors.extend(f"{p}: unclosed Markdown code fence" for p in unclosed_fences)
    if imbalanced:
        errors.extend(f"{p}: unbalanced MathJax delimiters" for p in imbalanced)
    if raw_single:
        errors.append(f"{raw_single} single-backslash math delimiter(s) found outside code; mdBook needs escaped delimiters")

    stats = {
        "files": len(files),
        "pages_with_math": pages_with_math,
        "block_open": block_open,
        "block_close": block_close,
        "inline_open": inline_open,
        "inline_close": inline_close,
        "legacy_dollar": legacy_dollar,
        "raw_single": raw_single,
        "unclosed_fences": len(unclosed_fences),
        "imbalanced_pages": len(imbalanced),
    }
    return stats, errors


def generated_check(repo: Path, book_dir_arg: str | None, errors: list[str]) -> dict:
    if not book_dir_arg:
        return {"checked": False, "html_files": 0, "mathjax_html_files": 0}
    book_dir = Path(book_dir_arg)
    if not book_dir.is_absolute():
        book_dir = repo / book_dir
    if not book_dir.exists():
        errors.append(f"generated book directory not found: {book_dir}")
        return {"checked": True, "html_files": 0, "mathjax_html_files": 0}
    html_files = sorted(book_dir.rglob("*.html"))
    mathjax_files = [
        p for p in html_files
        if "MathJax.js" in p.read_text(encoding="utf-8", errors="ignore")
        or "mathjax" in p.read_text(encoding="utf-8", errors="ignore").lower()
    ]
    if not html_files:
        errors.append(f"generated book directory contains no HTML: {book_dir}")
    elif not mathjax_files:
        errors.append("generated HTML contains no MathJax runtime reference")
    return {"checked": True, "html_files": len(html_files), "mathjax_html_files": len(mathjax_files)}


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[1]
    stats, errors = source_check(repo)
    generated = generated_check(repo, args.book_dir, errors)

    print("=== MathJax Validation ===")
    print(f"Repository: {repo}")
    print(f"Markdown pages scanned: {stats['files']}")
    print(f"Pages containing math: {stats['pages_with_math']}")
    print(f"Block delimiters: {stats['block_open']} open / {stats['block_close']} close")
    print(f"Inline delimiters: {stats['inline_open']} open / {stats['inline_close']} close")
    print(f"Legacy $$ delimiters outside code: {stats['legacy_dollar']}")
    print(f"Single-backslash delimiters outside code: {stats['raw_single']}")
    print(f"Unclosed code fences: {stats['unclosed_fences']}")
    print(f"Pages with unbalanced delimiters: {stats['imbalanced_pages']}")
    if generated["checked"]:
        print(f"Generated HTML files: {generated['html_files']}")
        print(f"HTML files with MathJax runtime: {generated['mathjax_html_files']}")

    if errors:
        print("\nFAILURES:")
        for error in errors[:200]:
            print(f"  - {error}")
        if len(errors) > 200:
            print(f"  ... and {len(errors) - 200} more")
        return 1

    print("MathJax validation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
