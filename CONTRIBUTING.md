# Contributing to Placement Prep

Thanks for your interest in improving this knowledge base. Whether you're fixing a typo, adding a new topic, or creating diagrams — every contribution helps.

## Before You Start

1. **Read [`scripts/USEFUL_COMMANDS.md`](scripts/USEFUL_COMMANDS.md)** — essential workflow reference for both humans and AI agent sessions.
2. **Check existing content** — search before creating to avoid duplicates:
   ```bash
   rg -li "topic name" src --glob '*.md' | grep -v SUMMARY
   ```
3. **Understand the structure** — `src/SUMMARY.md` is the navigation. Every page must be listed there or it's unreachable.

## Content Guidelines

### Page Template

Every page should follow this structure:

```markdown
# Title

## Overview

Brief introduction (2-3 sentences) explaining what the topic is and why it matters.

## Core Content

... sections with explanations, tables, diagrams ...

## Interview Questions

1. **Question?** Concise answer demonstrating depth.

## Key Takeaways

- Bullet points summarizing the most important points.

## Cross-References

- [Related Topic](src/dsa/README.md) — Brief context.
```

### Style Rules

| Rule | Details |
|------|---------|
| **Start with `# Title`** | Followed by `## Overview`, then sections |
| **No filler** | Avoid "X is very important" — be direct and technical |
| **Use diagrams** | Mermaid diagrams for architectures, flows, state machines |
| **Use tables** | Comparison tables for trade-offs, protocol differences, feature matrices |
| **Cross-reference** | Link to related pages — no page should be an island |
| **Real references** | Official docs, RFCs, papers with accessible URLs. Never invent URLs |
| **Interview questions** | Include 3-5 questions with concise, insightful answers |
| **MathJax** | Use `\\(...)` for inline and `\\[...\\]` for block math (mdBook compatible) |

### Mermaid Diagrams

Diagrams use **Mermaid v11** (loaded from CDN). Common pitfalls:

| Problem | Fix |
|----------|-----|
| Unquoted label with `( ) { } \|` | Quote it: `ID["text"]` |
| Escaped quote inside label | Use HTML entity: `#quot;` |
| `Note over` inside a flowchart | Use standalone node: `NOTE1["..."]` |
| `;` in sequenceDiagram text | Use `#59;` |
| Multiple node defs on one line | One statement per line |

Always validate diagrams: `node scripts/validate-mermaid-heuristic.mjs`

## Adding a New Page

1. Create the `.md` file in the appropriate directory under `src/`
2. Add it to `src/SUMMARY.md` in the correct section
3. Run validation:
   ```bash
   ./scripts/validate-all.sh .
   ```
4. Fix any issues reported

## Commit Messages

Use [conventional commits](https://www.conventionalcommits.org/):

```
type(scope): summary
```

| Type | Example |
|------|---------|
| `docs` | `docs(dbms): add OLTP vs OLAP comparison page` |
| `fix` | `fix(mermaid): quote unquoted labels containing parens` |
| `feat` | `feat(system-design): add Netflix case study` |
| `chore` | `chore: clean up stale audit files` |

## Branch & PR Workflow

- Work on `dev` branch — never commit directly to `main`
- Make small, logical commits (one topic/type per commit)
- Run validation before every commit
- PRs merge `dev` → `main`

## Validation Suite

```bash
# Full suite (recommended before every commit)
./scripts/validate-all.sh .

# Individual checks
./scripts/validate-mermaid-heuristic.mjs    # Fast Mermaid checks (no deps)
python3 scripts/check-links.py .             # Broken links
python3 scripts/check-summary.py src          # SUMMARY completeness + duplicate destinations
python3 scripts/check-mathjax.py .            # MathJax validation

# Network-dependent checks (run in CI and weekly; opt-in locally)
python3 scripts/check-doi.py src              # Resolve every DOI via the doi.org Handle API
python3 scripts/check-links.py --external .   # Probe all external URLs (bot-blocker aware)

# Strict mode (CI): a skipped real-mermaid-parser step FAILS the build
STRICT=1 ./scripts/validate-all.sh .
```

See [`scripts/README.md`](scripts/README.md) for full documentation of all scripts.

## Finding Pages That Need Work

```bash
# Short pages (likely stubs or incomplete)
find src -name '*.md' -size -500c

# Pages with no diagrams (candidates for visual improvement)
rg -L src -g '*.md' | head -20

# Pages with no interview questions
rg -Ll '## Interview' src -g '*.md' | head -20
```

## Questions?

Open an issue on GitHub or check [`scripts/USEFUL_COMMANDS.md`](scripts/USEFUL_COMMANDS.md) for the full workflow reference.
