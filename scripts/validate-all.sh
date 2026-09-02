#!/usr/bin/env bash
# One-shot validation for the Placement Prep mdBook repo.
# Runs every check whose dependencies are available; exits non-zero if any
# available check fails.
#
# Usage: ./scripts/validate-all.sh [repo-path]
set -u

REPO="${1:-$(pwd)}"
cd "$REPO" || { echo "ERROR: cannot cd to $REPO"; exit 1; }

MDBOOK="${MDBOOK:-mdbook}"
fail=0

echo "=== [1/8] mdBook build ==="
if command -v "$MDBOOK" >/dev/null 2>&1 || [ -x "$MDBOOK" ]; then
    if ! "$MDBOOK" build; then
        echo "  build failed (mdbook can peak >1 GB; constrained sandboxes may OOM-kill it) — retrying once..."
        sleep 2
        if ! "$MDBOOK" build; then
            if [ "${STRICT:-0}" = "1" ]; then
                echo "FAIL: mdbook build"
                fail=1
            else
                echo "WARN: mdbook build failed in this environment. Verify with: $MDBOOK build"
                echo "      (set STRICT=1 to treat a build failure as fatal)"
            fi
        fi
    fi
else
    echo "SKIP: mdbook not found (set MDBOOK=/path/to/mdbook)"
fi

echo
echo "=== [2/8] Mermaid heuristic checks ==="
node scripts/validate-mermaid-heuristic.mjs || { echo "FAIL: heuristic mermaid"; fail=1; }

echo
echo "=== [3/8] Mermaid real parser (needs mermaid@11 + jsdom in node_modules) ==="
PARSER_OK=0
# Try MERMAID_DIR (a scratch dir holding node_modules + a copy of validate-mermaid.mjs),
# then scripts/ directory.
for base in "${MERMAID_DIR:-}" "$(pwd)/scripts"; do
    [ -n "$base" ] || continue
    if [ -d "$base/node_modules/mermaid" ] && [ -d "$base/node_modules/jsdom" ] && [ -f "$base/validate-mermaid.mjs" ]; then
        (cd "$base" && node validate-mermaid.mjs "$REPO/src") || { echo "FAIL: parser mermaid"; fail=1; }
        PARSER_OK=1
        break
    fi
done
if [ "$PARSER_OK" -eq 0 ]; then
    if [ "${STRICT:-0}" = "1" ]; then
        echo "FAIL: real mermaid parser step skipped (mermaid@11/jsdom not installed)."
        echo "  In STRICT mode a skipped parser is a hard failure — the heuristics cannot"
        echo "  see whole bug classes (review §V.2). Install deps first:"
        echo "    (cd scripts && npm i mermaid@11 jsdom)"
        fail=1
    else
        echo "SKIP: mermaid@11/jsdom not installed. To enable:"
        echo "  mkdir -p /tmp/mv && cd /tmp/mv && npm i mermaid@11 jsdom && cp $REPO/scripts/validate-mermaid.mjs . && node validate-mermaid.mjs $REPO/src"
        echo "  (or run with STRICT=1 to make a skipped parser step fatal — CI does)"
    fi
fi

echo
echo "=== [4/8] Broken link check (internal links + anchors) ==="
python3 scripts/check-links.py "$REPO/src" || { echo "FAIL: links"; fail=1; }

echo
echo "=== [5/8] SUMMARY completeness + duplicate destinations ==="
python3 scripts/check-summary.py "$REPO/src" || { echo "FAIL: summary"; fail=1; }

echo
echo "=== [6/8] MathJax source checks ==="
python3 scripts/check-mathjax.py "$REPO" || { echo "FAIL: MathJax"; fail=1; }

if [ "${EXTERNAL:-0}" = "1" ]; then
    echo
    echo "=== [7/8] DOI resolution (doi.org Handle API; needs network) ==="
    python3 scripts/check-doi.py "$REPO/src" || { echo "FAIL: DOIs"; fail=1; }

    echo
    echo "=== [8/8] External URL probe (needs network) ==="
    python3 scripts/check-links.py --external "$REPO/src" || { echo "FAIL: external URLs"; fail=1; }
else
    echo
    echo "(external steps 7-8 skipped: set EXTERNAL=1 to probe DOIs + external URLs)"
fi

echo
if [ "$fail" -eq 0 ]; then
    echo "ALL VALIDATION PASSED ✅"
else
    echo "VALIDATION FAILED ❌"
fi
exit "$fail"
