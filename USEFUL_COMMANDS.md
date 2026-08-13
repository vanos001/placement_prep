# Useful Commands & Workflow Reference

Practical reference for maintaining the **Placement Prep** mdBook repo — for
humans and future agent sessions. Read this before making changes.

---

## Repo facts

| Item | Value |
|---|---|
| Book source | `src/` (Markdown), `src/SUMMARY.md` is the navigation |
| Build output | `book/` (git-ignored) |
| Mermaid rendering | Mermaid **v11** loaded from CDN in `mermaid-init.js` |
| Working branch | **`dev2`** (never commit directly to `main`) |
| Content count | ~870 Markdown files, ~2500 Mermaid diagrams |

---

## Git workflow

```bash
# Start a session: always on dev2, up to date
git checkout dev2 && git pull origin dev2

# Make changes, then validate (see below), then:
git add -A
git commit -m "type(scope): summary"
#   type: fix | docs | feat | refactor | chore | test
#   examples:
#     fix(mermaid): quote unquoted labels containing parens
#     docs(dbms): add OLTP vs OLAP page

# Push to dev2 ONLY
git branch --show-current        # must print: dev2
git push origin dev2
```

Rules:
- **Never push to `main`** unless the user explicitly asks for a merge.
- Commit in small logical batches (one topic/page/type per commit).
- Push frequently so work is never lost.
- Merge to `main` when asked: `git checkout main && git pull && git merge dev2 && git push origin main`.

## Authentication

The GitHub token lives in `token.txt` (git-ignored — **never** commit, print, or
log it). When pushing with the token:

```bash
TOKEN=$(cat token.txt)
git push "https://x-access-token:${TOKEN}@github.com/vanos001/placement_prep.git" dev2
```

Never put the token in the remote URL stored in `.git/config`; pass it inline
only. After cloning, reset the remote to the plain URL:
`git remote set-url origin https://github.com/vanos001/placement_prep.git`

---

## Build

```bash
# Install mdBook once (0.4.x)
curl -sL https://github.com/rust-lang/mdBook/releases/download/v0.4.40/mdbook-v0.4.40-x86_64-unknown-linux-gnu.tar.gz -o mdbook.tar.gz
tar xzf mdbook.tar.gz && mv mdbook ~/bin/   # or anywhere on PATH

# Build (outputs book/)
mdbook build

# Serve locally
mdbook serve --open          # http://localhost:3000
```

---

## Validation (run before every commit)

### One-shot suite (recommended)

```bash
./scripts/validate-all.sh .                 # from repo root
# options:
MDBOOK=/path/to/mdbook ./scripts/validate-all.sh .     # if mdbook not on PATH
MERMAID_DIR=/tmp/mv ./scripts/validate-all.sh .        # scratch dir with mermaid@11+jsdom
```

### Individual checks

```bash
# 1. Real Mermaid v11 parser (AUTHORITATIVE — catches what heuristics miss)
mkdir -p /tmp/mv && cd /tmp/mv && npm i mermaid@11 jsdom
cp <repo>/scripts/validate-mermaid.mjs . && node validate-mermaid.mjs <repo>/src
#    → must print: Passed: N, Failed: 0

# 2. Fast heuristic Mermaid checks (no deps) — run from repo root
node scripts/validate-mermaid-heuristic.mjs

# 3. Broken links (files + directory links)
python3 scripts/check-links.py .

# 4. SUMMARY completeness (every page reachable, no dead refs)
python3 scripts/check-summary.py src
```

The repo's own `validate-mermaid.mjs` (root) is the heuristic checker; the
authoritative parser lives in `scripts/validate-mermaid.mjs`.

---

## Mermaid v11 — things that break rendering

The book renders Mermaid **v11** (CDN). Verified break-set for **unquoted
labels**: `( ) { } |`. Rules of thumb:

| Symptom | Fix |
|---|---|
| Unquoted label with `( ) { } \|` | Quote it: `ID["text"]` |
| Escaped quote inside a label | Use HTML entity `#quot;` (backslash-escapes are unreliable in v11) |
| `Note over X: ...` inside a `graph`/`flowchart` | Sequence-only syntax — use a standalone node `NOTE1["..."]` |
| `;` in sequenceDiagram message/note text | Use `#59;` entity |
| Multiple node definitions on one line | One statement per line |
| `subgraph Title = ...` with spaces/`=` | `subgraph ID["Title = ..."]` |
| `A -->|No G[...]` (malformed edge label) | `A -->|No| G[...]` |
| Bare `...` or prose lines in a sequenceDiagram | Convert to `Note over` |
| Single `->` in a flowchart | Use `-->` (`-.->`, `==>` are fine) |

`graph TD` / `flowchart TD` are valid — do **not** "fix" them just for being
`graph TD`.

---

## Content conventions

- Every page: start with `# Title`, then `## Overview`, then sections.
- **Every substantial researched topic needs references** (official docs,
  RFCs, papers). Use real, accessible URLs; never invent them.
- Include **interview questions** and **tables/diagrams** where useful.
- Cross-reference related pages (avoid isolated wiki pages).
- Every new page must be added to `src/SUMMARY.md` or it is unreachable.
- Validate every new Mermaid diagram (real parser).
- Do NOT create duplicate topics — search first, expand or cross-reference
  instead.
- Keep pages focused and technical; no filler prose ("X is very important...").

## Common content searches

```bash
# Find pages mentioning a topic
grep -rli "consistent hashing" src --include='*.md' | grep -v SUMMARY

# Find stub/short pages (likely incomplete)
find src -name '*.md' -size -500c

# Count diagrams
grep -rc '```mermaid' src --include='*.md' | awk -F: '{s+=$2} END {print s}'

# Find a page's section headings
grep -n '^#' src/dbms/overview.md
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `mdbook build` killed (exit 137) in a sandbox | Memory pressure — mdbook peaks ~1 GB. Retry, or verify build separately; content validators still run |
| `node` says `Cannot find module 'mermaid'` | `npm i mermaid@11 jsdom` in a scratch dir (node_modules is git-ignored) |
| New page not in the book | Add it to `src/SUMMARY.md` |
| Diagram renders wrong in preview | Run the real parser validator; likely one of the gotchas above |
| Broken link after adding a page | `python3 scripts/check-links.py .` |
| `.git` missing after a session restart | Workspace snapshots exclude git metadata — re-clone with the token and re-apply any unpushed changes |
