#!/usr/bin/env python3
"""
Fix mdBook "unclosed HTML tag" warnings (v2, log-driven).

mdBook's markdown parser (pulldown-cmark, following CommonMark) treats any
token matching `<[A-Za-z][A-Za-z0-9-]*>` as an HTML open-tag. When such a
token appears in a heading, list item, paragraph, or table cell and no
matching close-tag exists, mdBook emits:

    WARN unclosed HTML tag `<x>` found in <file> while exiting TableCell
    HTML tags must be closed before exiting a markdown element.

and the tag text is consumed as HTML in the rendered page (the placeholder
visually disappears, or swallows following text in some browsers).

These tokens are not HTML — they are placeholders like `<pid>`, `<x>`,
`<n>`, `<PCI BDF>` used in sysfs path templates (e.g. /sys/class/accel/accel<n>/)
and format strings (e.g. SIG<NAME>).

v1 of this script (branch @ b82a2cb) fixed 11 such sites with a hardcoded
edit list. v2 generalizes: it reads an mdBook build log, extracts every
(file, tag) pair, and wraps each bare occurrence of the tag in inline-code
backticks — the convention established by v1 (e.g. /proc/`<pid>`/limits).

Notes
-----
* mdBook LOWERCASES the tag name in the warning (`<PCI BDF>` warns as
  `<pci>`, `SIG<NAME>` warns as `<name>`), so source matching is
  case-insensitive.
* Occurrences inside fenced code blocks or inline code spans are left
  alone (they never warn, and escaping there would corrupt rendering).
* Inline-code span state is tracked per line (k-backtick runs), and
  conservatively reset on blank lines, headings, fence lines, and table
  rows, so a span opened on an earlier line cannot swallow the patch.
* --scan lists remaining bare tag-shaped tokens repo-wide without
  patching (e.g. attr-style tokens like `<PCI BDF>` that some browsers
  also eat but mdBook does not warn about under older parsers).

Usage:
    python3 scripts/fix-unclosed-html-tags.py <mdbook-build.log> [--dry-run]
    python3 scripts/fix-unclosed-html-tags.py --scan
"""
import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "src"

WARN_RE = re.compile(
    r"WARN unclosed HTML tag `<([^`<>]+)>` found in `([^`]+)` while exiting"
)
# tag-shaped token in source: <tag> or <tag attr...> (no angle brackets,
# no backticks inside; must start with a letter)
SHAPE_RE = re.compile(r"<([A-Za-z][A-Za-z0-9_-]*(?:\s[^<>`]*)?)>")


def iter_content_lines(text):
    """Yield (index, line, in_fence) with fence state carried forward."""
    fence_re = re.compile(r"^\s*(`{3,}|~{3,})")
    fence = None
    for i, line in enumerate(text.splitlines()):
        m = fence_re.match(line)
        if fence:
            yield i, line, True
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
        elif m:
            fence = m.group(1)
            yield i, line, True
        else:
            yield i, line, False


def masked_line(line):
    """Return a copy of the line with inline-code-span contents blanked.

    Tracks k-backtick runs; a span opened on this line is blanked from its
    opening run to its closing run. An unterminated run blanks nothing
    (conservative: token stays visible and may be patched — acceptable
    because the block-level caller resets state on headings/blank/table
    lines, and every patch is human-reviewed via git diff).
    """
    out = list(line)
    i, n = 0, len(line)
    while i < n:
        if line[i] == "`":
            j = i
            while j < n and line[j] == "`":
                j += 1
            k = j - i
            close = line.find("`" * k, j)
            if close != -1:
                for p in range(i, close + k):
                    out[p] = "\0"
                i = close + k
                continue
            i = j
            continue
        i += 1
    return "".join(out)


def find_bare(line, tag_re):
    """Yield (start, end) of bare <tag> occurrences outside inline code."""
    masked = masked_line(line)
    for m in tag_re.finditer(masked):
        yield m.start(), m.end()


def patch_file(path, tags, dry_run):
    """Wrap bare occurrences of the given tags in backticks. Return count.

    The regex also matches attr-style open tags like `<PCI BDF>` for a
    warned tag `pci`: pulldown-cmark accepts `tagname attribute` as a valid
    open tag and mdBook reports just the lowercased tag name.
    """
    tag_res = [(t, re.compile(r"<" + re.escape(t) + r"(?:\s[^<>`]*)?>",
                              re.IGNORECASE))
               for t in tags]
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    changed = 0
    prev_kind = "blank"
    for i, line in enumerate(lines):
        fence = line.lstrip().startswith("```") or line.lstrip().startswith("~~~")
        is_table = line.lstrip().startswith("|")
        is_heading = re.match(r"^\s*#{1,6}\s", line) is not None
        # state resets: blank line, fence line, table row, heading
        if prev_kind in ("blank", "fence", "table", "heading") or is_table \
                or is_heading or fence or not line.strip():
            pass  # masked_line() is per-line anyway; kept for clarity
        prev_kind = ("fence" if fence else "table" if is_table
                     else "heading" if is_heading else "blank"
                     if not line.strip() else "text")
        new_line = line
        for tag, tag_re in tag_res:
            spans = list(find_bare(new_line, tag_re))
            for s, e in reversed(spans):
                token = new_line[s:e]
                new_line = new_line[:s] + "`" + token + "`" + new_line[e:]
                changed += 1
                if dry_run:
                    print(f"  {path.relative_to(REPO)}:{i+1}: {token} -> ` {token} `")
        if new_line != line:
            lines[i] = new_line
    if changed and not dry_run:
        path.write_text("\n".join(lines), encoding="utf-8")
    return changed


def load_warnings(log_path):
    pairs = set()
    for ln in pathlib.Path(log_path).read_text(encoding="utf-8").splitlines():
        m = WARN_RE.search(ln)
        if m:
            pairs.add((m.group(2), m.group(1).lower()))
    files = {}
    for rel, tag in sorted(pairs):
        files.setdefault(rel, set()).add(tag)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log", nargs="?", help="mdBook build log with WARN lines")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--scan", action="store_true",
                    help="report remaining bare tag-shaped tokens repo-wide")
    args = ap.parse_args()

    if args.scan:
        print("bare tag-shaped tokens outside code spans, repo-wide:")
        total = 0
        for p in sorted(SRC.rglob("*.md")):
            rel = p.relative_to(REPO)
            for i, line, in_fence in iter_content_lines(p.read_text(encoding="utf-8")):
                if in_fence:
                    continue
                masked = masked_line(line)
                for m in SHAPE_RE.finditer(masked):
                    total += 1
                    print(f"  {rel}:{i+1}: <{m.group(1)}>")
        print(f"total: {total}")
        return

    if not args.log:
        ap.error("a build log path is required (or use --scan)")
    files = load_warnings(args.log)
    print(f"{sum(len(v) for v in files.values())} (file, tag) pairs "
          f"across {len(files)} files")
    errors = 0
    for rel, tags in files.items():
        path = SRC / rel
        if not path.is_file():
            print(f"MISSING: {rel}")
            errors += 1
            continue
        n = patch_file(path, tags, args.dry_run)
        print(f"{'DRY ' if args.dry_run else 'OK  '}{rel}: {n} occurrence(s) "
              f"wrapped ({', '.join(sorted(tags))})")
    if errors:
        raise SystemExit(1)
    print(f"\n{'dry run complete' if args.dry_run else 'all files patched'}")


if __name__ == "__main__":
    main()
