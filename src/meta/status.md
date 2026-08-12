# Project Status

> Status snapshot: 2026-08-13 (Asia/Calcutta)

## Current status

**Link repair and Software Engineering pages complete.** The Software Engineering
section now has dedicated pages for Testing, DevOps & CI/CD, and Contributing,
registered in `SUMMARY.md` and linked from the section README. All relative
links, navigation, MathJax, and Mermaid checks pass on `dev`.

| Area | Status | Evidence |
|---|---|---|
| Git safety | ✅ Complete | Active branch is `dev`; `main` remains unchanged |
| Content inventory | ✅ Audited | 1,726 content Markdown pages plus `SUMMARY.md` |
| Navigation | ✅ Passing | 1,726 of 1,726 content pages are reachable from `SUMMARY.md` |
| Relative links | ✅ Passing | Checker reports 0 broken links |
| Mermaid heuristic | ✅ Passing | 4,405 of 4,405 diagrams pass |
| Mermaid v11 parser | ✅ Passing | 4,405 of 4,405 diagrams pass (previous run) |
| MathJax | ✅ Passing | 396 block pairs, 610 inline pairs, no legacy `$$` delimiters |
| Cross-reference graph | ✅ Generated | 1,723 nodes and 7,405 internal links (pre-SE-pages run) |
| Software Engineering | ✅ Expanded | 14 pages, incl. new Testing, DevOps & CI/CD, Contributing |

## Validation command

The lightweight validation suite was re-run on the latest `dev` tree:

- `scripts/check-links.py` → 0 broken links
- `scripts/check-summary.py` → SUMMARY navigation: OK
- `scripts/check-mathjax.py` → MathJax validation: OK
- `scripts/validate-mermaid-heuristic.mjs` → 4,405/4,405 pass

A full `mdbook build` is not run in this sandbox: it peaks >1 GB RSS and is
OOM-killed under the ~2 GB memory limit (documented in `validate-all.sh`).

## Repository provenance

- Target: [`vanos001/placement_prep`](https://github.com/vanos001/placement_prep)
- Linux source: [`Abhinav-Kumar012/lb2`](https://github.com/Abhinav-Kumar012/lb2)
- DSA source: [`Abhinav-Kumar012/dsa_book_2`](https://github.com/Abhinav-Kumar012/dsa_book_2)

Only educational Markdown was imported. Git metadata, workflows, deployment
configuration, generated output, source JavaScript/CSS, and the DSA source's
anchor-named artifacts were not copied into the target book. Links were
rewritten or converted to nearby text when their old source path did not exist.

## Safety constraints

- Development work is performed on `dev`.
- Release promotion from `dev` to `main` occurs only after validation.
- Credentials are read only at command time and are not stored in repository
  files, commits, or documentation.
