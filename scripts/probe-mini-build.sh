#!/usr/bin/env bash
# Build a minimal mdBook containing ONLY the 9 fixed files (+ a SUMMARY),
# so we can prove the "unclosed HTML tag" warnings are gone without
# OOM-killing on the full 3,432-page tree.
set -euo pipefail

REPO=/home/z/my-project/placement_prep
WORK=/tmp/mdbook-mini
MDBOOK=/tmp/mdbook

rm -rf "$WORK"
mkdir -p "$WORK/src/linux/binaries/util-linux" \
         "$WORK/src/linux/binaries/shadow" \
         "$WORK/src/linux/init-systems/openrc" \
         "$WORK/src/linux/init-systems/sysvinit"

# Minimal book.toml — no mermaid, no MathJax, no custom CSS. Pure mdBook.
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

# Files relative to src/ in the mini book.
declare -a FILES=(
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

for f in "${FILES[@]}"; do
  cp "$REPO/src/$f" "$WORK/src/$f"
done

# Minimal SUMMARY.md wiring every file as a top-level entry.
# Use python to read H1 safely (avoids sed/backtick issues).
python3 - <<'PY' > "$WORK/src/SUMMARY.md"
import pathlib
files = [
    "linux/binaries/util-linux/prlimit.md",
    "linux/binaries/util-linux/nsenter.md",
    "linux/binaries/util-linux/mkfs.md",
    "linux/binaries/shadow/newgidmap.md",
    "linux/binaries/shadow/newuidmap.md",
    "linux/init-systems/openrc/init-scripts.md",
    "linux/init-systems/sysvinit/configuration.md",
    "linux/init-systems/sysvinit/getty-terminals.md",
    "linux/init-systems/sysvinit/init-scripts.md",
]
print("# Summary\n")
for f in files:
    text = pathlib.Path(f"/tmp/mdbook-mini/src/{f}").read_text(encoding="utf-8")
    title = ""
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    if not title:
        title = pathlib.Path(f).stem
    # Escape any `]` in the title so the SUMMARY link doesn't break.
    title = title.replace("]", "\\]")
    print(f"- [{title}]({f})")
PY

echo "=== Mini SUMMARY.md ==="
cat "$WORK/src/SUMMARY.md"
echo
echo "=== Running mdbook build ==="
cd "$WORK"
"$MDBOOK" build 2>&1 | tee "$WORK/build.log"
echo
warn_count=$(rg -c '^ WARN' "$WORK/build.log" || echo 0)
unclosed_count=$(rg -ic 'unclosed html tag' "$WORK/build.log" || echo 0)
err_count=$(rg -c '^ERROR' "$WORK/build.log" || echo 0)
built_html=$(find "$WORK/book" -name '*.html' 2>/dev/null | wc -l)

echo "=== Result ==="
echo "WARN lines:                 $warn_count"
echo "Unclosed-HTML-tag warnings: $unclosed_count"
echo "ERROR lines:                $err_count"
echo "Built HTML pages:           $built_html"
echo
echo "=== Probe a fixed heading in the rendered HTML ==="
# The prlimit page should now contain the heading text intact, with the
# <pid> rendered as inline code (i.e. <code>&lt;pid&gt;</code>), not dropped.
rg -c 'read-only mirror' "$WORK/book/linux/binaries/util-linux/prlimit.html" || true
rg -o '<code>&lt;pid&gt;</code>' "$WORK/book/linux/binaries/util-linux/prlimit.html" | head -2 || true

if [ "$unclosed_count" -eq 0 ] && [ "$err_count" -eq 0 ] && [ "$built_html" -gt 0 ]; then
  echo
  echo "PASS: build clean, no unclosed-HTML-tag warnings, all pages rendered."
  exit 0
else
  echo
  echo "FAIL"
  exit 1
fi
