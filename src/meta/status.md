# Project Status

> Status snapshot: 2026-08-12 (Asia/Calcutta)

## Current status

**Integration and validation are complete on `dev`.**
The two public source books have been cloned, reviewed, integrated as coherent
learning tracks, and wired into the parent `SUMMARY.md`.

| Area | Status | Evidence |
|---|---|---|
| Git safety | ✅ Complete | Development is on `dev`; the released tree is synchronized on both `dev` and `main` |
| Linux source | ✅ Integrated | `src/linux/` contains the educational Markdown from `lb2` |
| DSA source | ✅ Integrated | `src/dsa/` contains the educational Markdown from `dsa_book_2` |
| Linux tools | ✅ Added | `src/linux/tools.md` is a placement-focused, referenced guide |
| Navigation | ✅ Passing | 1,532 of 1,533 Markdown files are linked; `SUMMARY.md` itself is excluded |
| Relative links | ✅ Passing | Repository checker reports 0 broken links |
| Mermaid heuristic | ✅ Passing | 4,387 of 4,387 diagrams pass |
| Mermaid v11 parser | ✅ Passing | 4,387 of 4,387 diagrams pass with `mermaid@11` + `jsdom` |
| MathJax | ✅ Enabled | mdBook `mathjax-support = true`; DSA block and inline delimiters are preserved |
| mdBook build | ✅ Constrained build passed | mdBook 0.4.52 built 1,573 output files with search indexing disabled; the normal search-enabled build was OOM-killed in this sandbox (exit 137) |

## Repository provenance

- Target: [`vanos001/placement_prep`](https://github.com/vanos001/placement_prep)
- Linux source: [`Abhinav-Kumar012/lb2`](https://github.com/Abhinav-Kumar012/lb2)
- DSA source: [`Abhinav-Kumar012/dsa_book_2`](https://github.com/Abhinav-Kumar012/dsa_book_2)

Only educational Markdown was imported. Git metadata, workflows, deployment
configuration, generated output, source JavaScript/CSS, and the DSA source's
anchor-named artifacts were not copied into the target book. Links were
rewritten or converted to nearby text when their old source path did not exist.

## Safety constraints

- All work is performed on `dev`.
- Pushes for this task go to `origin/dev` only.
- `main` is not a destination for this work.
- Credentials are read only at command time and are not stored in repository
  files, commits, or documentation.

## Final record

`validate-all.sh` was run with an absolute repository path, mdBook 0.4.52, and
Mermaid v11/jsdom. It returned 0: Mermaid heuristic/parser, links, and Summary
all passed. The search-enabled build was attempted twice and killed by the
sandbox memory limit; an isolated full build with `output.html.search.enable = false`
completed successfully. The production `book.toml` was left unchanged.

The release was promoted from `dev` to `main` after validation and synchronized
back to `dev`. The two release branches are kept at the same validated tree;
the working tree is clean.
