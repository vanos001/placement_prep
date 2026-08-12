# Contributing to placement_prep

Thank you for contributing! This book is a community-maintained knowledge base for
software-engineering and placement preparation. This guide explains how to add and
improve content.

## Repository Overview

| Item | Description |
|---|---|
| `src/` | All book content (Markdown) |
| `src/SUMMARY.md` | The table of contents — every chapter must be listed here |
| `book.toml` | mdBook configuration |
| `scripts/` | Validation tooling (links, SUMMARY, MathJax, Mermaid) |
| `custom.css`, `mermaid-init.js` | Styling and diagram rendering |

The book is built with [mdBook](https://rust-lang.github.io/mdBook/).

## Getting Started

```bash
git clone https://github.com/vanos001/placement_prep.git
cd placement_prep
git checkout dev            # work on the dev branch
```

> Never push directly to `main`. All content work happens on `dev`.

## How to Add a Chapter

1. **Check for duplicates first** — search `src/`, filenames, and `SUMMARY.md` for
   the topic. Prefer deepening an existing page over creating a duplicate.
2. **Create the Markdown file** under the appropriate section, e.g.:

   ```text
   src/networks/tcp/congestion-control.md
   ```

3. **Register it in `src/SUMMARY.md`** so it is discoverable, e.g. a line of the form
   `- [Congestion Control] → ./networks/tcp/congestion-control.md`.

4. **Write real content** — no placeholder pages. Aim for definition, intuition,
   examples, trade-offs, and (where useful) interview questions.

## Content Guidelines

- **Follow existing structure** — do not invent a new hierarchy when one already works.
- **Prefer primary sources** — official documentation, RFCs, standards, man pages.
- **Add references** — and never invent them.
- **Use diagrams sparingly** — Mermaid where they genuinely aid understanding.
- **Keep pages focused** — one excellent 2,000-word page beats ten shallow ones.
- **Style:** technically rigorous, beginner-friendly, interview-oriented, no filler.

## Validation

Before committing, run the repo's checks (lightweight, no full build required):

```bash
python3 scripts/check-links.py .           # broken relative links
python3 scripts/check-summary.py src       # SUMMARY completeness
python3 scripts/check-mathjax.py .         # MathJax delimiter balance
node scripts/validate-mermaid-heuristic.mjs
```

## Commit Conventions

Use conventional, scoped messages:

```text
feat(networking): add TCP congestion control
feat(dsa): add advanced graph algorithms
docs(interview): add OS interview questions
fix(summary): repair broken links
```

## License & Code of Conduct

- Be respectful and constructive in all interactions.
- Only submit content you have the right to share.
- Do not commit secrets, credentials, or large binaries.
