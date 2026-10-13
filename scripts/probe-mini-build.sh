#!/usr/bin/env bash
# Build a minimal mdBook containing ONLY the files named in an mdBook
# warnings log (or a default file list), so we can prove the "unclosed
# HTML tag" warnings are gone without OOM-killing on the full 4,000+ page
# tree.
#
# Usage:   scripts/probe-mini-build.sh [mdbook-build.log]
#          (log lines look like: WARN unclosed HTML tag `<x>` found in `path` ...)
# Env:     REPO   - repo root          (default: repo containing this script)
#          MDBOOK - mdbook binary      (default: mdbook on PATH)
#          WORK   - scratch build dir  (default: /tmp/mdbook-mini)
set -euo pipefail

REPO="${REPO:-$(cd "$(dirname "$0")/.." && pwd)}"
MDBOOK="${MDBOOK:-mdbook}"
WORK="${WORK:-/tmp/mdbook-mini}"
LOG="${1:-}"

# --- collect the files to probe -------------------------------------------
# Historical default: the 9 files fixed at b82a2cb.
DEFAULT_FILES=(
  "linux/binaries/util-linux/prlimit.md"
  "linux/binaries/util-linux/nsenter.md"
  "linux/binaries/util-linux/mkfs.md"
  "linux/binaries/shadow/newgidmap.md"
  "linux/binaries/shadow/newuidmap.md"
  "linux/init-systems/openrc/init-scripts.md"
  "linux/init-systems/sysvinit/configuration.md"
  "linux/init-systems/sysvinit/getty-terminals.md"
  "linux/init-systems/sysvinit/init-scripts.md"
)

if [ -n "$LOG" ]; then
  FILES=($(python3 - "$LOG" <<'PY'
import re, sys
pat = re.compile(r"WARN unclosed HTML tag `<[^`<>]+>` found in `([^`]+)`")
seen = []
for ln in open(sys.argv[1], encoding="utf-8"):
    m = pat.search(ln)
    if m and m.group(1) not in seen:
        seen.append(m.group(1))
print("\n".join(seen))
PY
))
else
  FILES=("${DEFAULT_FILES[@]}")
fi

echo "probing ${#FILES[@]} file(s)"

# --- scratch book -----------------------------------------------------------
rm -rf "$WORK"
mkdir -p "$WORK/src"

cat > "$WORK/book.toml" <<'TOML'
[book]
title = "Mini HTML-tag warning probe"
language = "en"
src = "src"

[build]
build-dir = "book"
create-missing = false

[output.html]
TOML

for f in "${FILES[@]}"; do
  mkdir -p "$WORK/src/$(dirname "$f")"
  cp "$REPO/src/$f" "$WORK/src/$f"
done

# Minimal SUMMARY wiring every file as a top-level entry, titled from its H1.
python3 - "$WORK" "${FILES[@]}" <<'PY' > "$WORK/src/SUMMARY.md"
import pathlib, sys
work = sys.argv[1]
files = sys.argv[2:]
print("# Summary\n")
for f in files:
    text = pathlib.Path(work, "src", f).read_text(encoding="utf-8")
    title = next((l[2:].strip() for l in text.splitlines()
                  if l.startswith("# ")), pathlib.Path(f).stem)
    title = title.replace("]", "\\]")
    print(f"- [{title}]({f})")
PY

echo "=== Running mdbook build ==="
cd "$WORK"
"$MDBOOK" build 2>&1 | tee "$WORK/build.log"

warn_count=$(grep -c '^ WARN' "$WORK/build.log" || true)
unclosed_count=$(grep -ci 'unclosed html tag' "$WORK/build.log" || true)
err_count=$(grep -c '^ERROR' "$WORK/build.log" || true)
built_html=$(find "$WORK/book" -name '*.html' 2>/dev/null | wc -l)

echo
echo "=== Result ==="
echo "WARN lines:                 $warn_count"
echo "Unclosed-HTML-tag warnings: $unclosed_count"
echo "ERROR lines:                $err_count"
echo "Built HTML pages:           $built_html"

if [ "$unclosed_count" -eq 0 ] && [ "$err_count" -eq 0 ] && [ "$built_html" -gt 0 ]; then
  echo
  echo "PASS: build clean, no unclosed-HTML-tag warnings, all pages rendered."
  exit 0
else
  echo
  echo "FAIL"
  exit 1
fi
