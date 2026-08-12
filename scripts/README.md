# Validation Scripts

Reusable tooling for the Placement Prep mdBook repo. These scripts validate
**Mermaid diagrams**, **Markdown links**, and **SUMMARY navigation** so every
change is verified before commit.

## Requirements

| Tool | Needed by | Install |
|---|---|---|
| mdBook (0.4.x) | `validate-all.sh` | `curl -sL https://github.com/rust-lang/mdBook/releases/download/v0.4.40/mdbook-v0.4.40-x86_64-unknown-linux-gnu.tar.gz -o mdbook.tar.gz && tar xzf mdbook.tar.gz` |
| Node.js ≥ 18 + npm | `validate-mermaid.mjs` (real parser) | — |
| Python 3 | `check-links.py`, `check-summary.py` | — |

For the **real Mermaid parser** validator, install once:

```bash
npm install mermaid@11 jsdom   # in a scratch dir, NOT committed
```

> `node_modules` is git-ignored — install in a local scratch folder
> (e.g. `/tmp/mermaid-validate`) and pass the repo path as an argument.

## Quick Start

```bash
./scripts/validate-all.sh /path/to/repo          # everything, best-effort
./scripts/validate-mermaid-heuristic.mjs         # fast heuristic checks (run from repo root)
node /tmp/mermaid-validate/validate.mjs /path/to/repo/src   # real Mermaid v11 parser
./scripts/check-links.py /path/to/repo           # broken relative links
./scripts/check-summary.py /path/to/repo/src     # SUMMARY completeness
python3 scripts/generate-cross-reference-graph.py \
  --output book/meta/cross-reference-graph-view.html # generated graph after mdBook build
```

## Scripts

### `validate-all.sh` — one-shot full check

Runs, in order, skipping anything whose dependencies are missing:

1. `mdbook build` (if mdbook is on PATH or `$MDBOOK`)
2. heuristic Mermaid checks (`validate-mermaid-heuristic.mjs`)
3. real Mermaid parser (`validate-mermaid.mjs` via `node`, if a copy exists)
4. link check (`check-links.py`)
5. SUMMARY check (`check-summary.py`)

Exits non-zero if any *available* check fails.

Notes:
- Set `MDBOOK=/path/to/mdbook` if mdbook is not on PATH.
- The build step is **best-effort** by default: in memory-constrained sandboxes
  mdbook (peak ~1 GB RSS) can be OOM-killed even when healthy. Set `STRICT=1`
  to make a build failure fatal, or just run `mdbook build` yourself to verify.
- `MERMAID_DIR=/path/to/scratch` points at a scratch dir holding
  `node_modules/{mermaid,jsdom}` plus a copy of `scripts/validate-mermaid.mjs`
  (the parser check is skipped if it can't find these).

### `validate-mermaid.mjs` — real Mermaid v11 parser (authoritative)

Parses every ```mermaid block with the actual Mermaid library. This is the
check that catches what heuristics miss. Usage:

```bash
node validate-mermaid.mjs /path/to/repo/src
```

Requires `mermaid@11` + `jsdom` installed in the same directory (git-ignored).
Prints per-file failures and writes `report.json`. Exit code 1 if any diagram
fails.

### `validate-mermaid-heuristic.mjs` — fast heuristic checks

No dependencies. Catches the common v11 break patterns:

- unquoted labels containing `( ) { } |`
- escaped `\"` quotes in labels (use `#quot;`)
- `Note over` (sequence syntax) inside flowcharts
- multiple node definitions on one line
- `+` between node statements (block-beta syntax in a flowchart)
- single `->` arrows in flowcharts (use `-->`)
- raw `;` in sequenceDiagram text (use `#59;`)
- bare `...` lines and unrecognized prose in sequence diagrams
- unquoted subgraph titles with `=` or `(`

Run from the **repo root** (it scans `src/` by default):

```bash
./scripts/validate-mermaid-heuristic.mjs
```

### `check-links.py` — broken link finder

Walks all `.md` files and verifies every relative link resolves (files AND
directory links). Usage:

```bash
python3 scripts/check-links.py /path/to/repo
```

Prints broken links grouped by file; total count at the end.

### `check-summary.py` — navigation completeness

Verifies every `.md` file under `src/` is reachable from `SUMMARY.md` and that
every SUMMARY link points to an existing file. Usage:

```bash
python3 scripts/check-summary.py /path/to/repo/src
```

## Mermaid gotchas (what the validators look for)

| Problem | Fix |
|---|---|
| Unquoted label with `( ) { } \|` | Quote it: `ID["text"]` |
| Escaped quote in label | Use HTML entity: `#quot;` |
| `Note over` inside a flowchart | Use a standalone node: `NOTE1["..."]` |
| `;` in a sequenceDiagram message/note | Use `#59;` |
| Multiple node defs on one line | One statement per line |
| `subgraph Title = ...` | `subgraph ID["Title = ..."]` |
