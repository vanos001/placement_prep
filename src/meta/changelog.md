# Changelog

This file records meaningful content and validation changes to the placement
preparation book. Dates use the project timezone, Asia/Calcutta.

## 2026-08-12 — Add MathJax validation tooling

- Added `scripts/check-mathjax.py` to verify `mathjax-support = true`, balanced
  escaped inline/block delimiters, no legacy `$$` delimiters outside code, and
  no unclosed Markdown fences.
- Added optional `--book-dir` checking for the generated MathJax runtime.
- Added the MathJax check as step 6 in `scripts/validate-all.sh` and documented
  standalone usage in `scripts/README.md`.

## 2026-08-12 — Research and validation audit

### Fixed

- Converted legacy `$$...$$` display equations in 61 Markdown pages to the
  mdBook-compatible escaped block delimiters used by MathJax.
- Closed malformed code fences in DSA advanced segment trees, Linux firewall
  maps, and ML optimizer examples.
- Repaired nine stale internal heading fragments and four escaped `Ctrl+` code
  examples discovered by the audit.
- Corrected the retired `ebpf.io/docs` URL to the maintained `docs.ebpf.io`
  documentation site.

### Audit result

- Broken relative links: **0**.
- SUMMARY reachability: **1,533 of 1,533 content pages linked**.
- Mermaid heuristic/parser: **4,387 / 4,387 passed**.
- Math delimiter counts are balanced outside fenced code and inline code spans.
- No exact duplicate Markdown bodies were found.
- 73 URL-bearing pages without a References-style heading and 112 pages with
  no content cross-links remain as research-review candidates; they are not
  navigation failures because Summary reachability is complete.

## 2026-08-12 — Enable MathJax and automatic cross-reference graph

- Enabled mdBook’s built-in MathJax support with
  `output.html.mathjax-support = true`.
- Added `scripts/generate-cross-reference-graph.py` and a Meta navigation page;
  the GitHub Pages workflow now generates the interactive graph automatically
  after every successful mdBook build.
- Added the `Cross-Reference Graph` Meta page; the generated view is output-only and is not committed as a large artifact.
- Confirmed the integrated DSA source uses mdBook-compatible escaped inline
  mdBook-compatible inline and block delimiters.
- The generated DSA math page now includes the MathJax runtime instead of
  leaving formulas as raw delimiter text.

## 2026-08-12 — Linux and DSA book integration

### Added

- Integrated the educational Markdown from [`lb2`](https://github.com/Abhinav-Kumar012/lb2)
  into the navigable [`src/linux/`](../linux/README.md) Linux deep-dive track.
- Integrated the educational Markdown from [`dsa_book_2`](https://github.com/Abhinav-Kumar012/dsa_book_2)
  into the navigable [`src/dsa/`](../dsa/README.md) DSA track.
- Added a referenced [Linux Tools for Placement Preparation](../linux/tools.md)
  chapter covering file/text, process, storage, networking, debugging, and
  developer-workflow tools.
- Added explicit project status, progress, backlog, coverage, and knowledge
  graph tracking for this batch.

### Fixed

- Rewrote imported relative Markdown links for their final locations and
  removed stale source-only targets rather than leaving broken navigation.
- Repaired 34 imported Mermaid diagrams identified by the repository heuristic
  validator, including unsafe labels, malformed subgraphs, sequence syntax,
  and a corrupted routing diagram.
- Repaired 15 parser-only Mermaid failures found by Mermaid v11, including
  nested quotes, multiline labels, invalid state transitions, inline comments,
  reserved node IDs, and source-file line-join corruption.
- Added five Linux build chapters that were initially hidden by the target
  repository's generic `build/` ignore rule.

### Validation

- Link checker: **0 broken links**.
- SUMMARY checker: **OK** for 1,534 Markdown files (1,533 linked chapters).
- Mermaid heuristic: **4,387 / 4,387 passed**.
- Mermaid v11 parser: **4,387 / 4,387 passed**.
- `validate-all.sh`: **exit 0 / ALL VALIDATION PASSED** when called with an
  absolute repository path.
- mdBook 0.4.52: a full search-disabled build produced 1,575 output files
  successfully; the normal search-enabled build was killed by the sandbox
  memory limit with exit 137. The production configuration remains unchanged.

### Git

- Integration commits `42c4e57` and `5f986da`, followed by metadata/validation
  commit `79145d7`, were made on `dev` and pushed to `origin/dev`.
- The validated tree was promoted from `dev` to `main` and synchronized back to
  `dev`; both release branches are kept aligned.
- The working tree was clean after promotion.

## Earlier history

See the preceding commits for the existing autonomous content-expansion
batches. This changelog intentionally records the current integration batch
without rewriting that history.
