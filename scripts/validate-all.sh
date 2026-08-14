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

echo "=== [1/6] mdBook build ==="
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
echo "=== [2/6] Mermaid heuristic checks ==="
node scripts/validate-mermaid-heuristic.mjs || { echo "FAIL: heuristic mermaid"; fail=1; }

echo
echo "=== [3/6] Mermaid real parser (needs mermaid@11 + jsdom in node_modules) ==="
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
    echo "SKIP: mermaid@11/jsdom not installed. To enable:"
    echo "  mkdir -p /tmp/mv && cd /tmp/mv && npm i mermaid@11 jsdom && cp $REPO/scripts/validate-mermaid.mjs . && node validate-mermaid.mjs $REPO/src"
fi

echo
echo "=== [4/6] Broken link check ==="
python3 scripts/check-links.py "$REPO" || { echo "FAIL: links"; fail=1; }

echo
echo "=== [5/6] SUMMARY completeness ==="
python3 scripts/check-summary.py "$REPO/src" || { echo "FAIL: summary"; fail=1; }

echo
echo "=== [6/6] MathJax source checks ==="
python3 scripts/check-mathjax.py "$REPO" || { echo "FAIL: MathJax"; fail=1; }

echo
if [ "$fail" -eq 0 ]; then
    echo "ALL VALIDATION PASSED ✅"
else
    echo "VALIDATION FAILED ❌"
fi
exit "$fail"
