# Changelog

This file records meaningful content and validation changes to the placement
preparation book. Dates use the project timezone, Asia/Calcutta.

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
- SUMMARY checker: **OK** for 1,533 Markdown files (1,532 linked chapters).
- Mermaid heuristic: **4,387 / 4,387 passed**.
- Mermaid v11 parser: **4,387 / 4,387 passed**.
- `validate-all.sh`: **exit 0 / ALL VALIDATION PASSED** when called with an
  absolute repository path.
- mdBook 0.4.52: a full search-disabled build produced 1,573 output files
  successfully; the normal search-enabled build was killed by the sandbox
  memory limit with exit 137. The production configuration remains unchanged.

### Git

- Integration commits `42c4e57` and `5f986da`, followed by metadata/validation
  commit `79145d7`, were made on `dev` and pushed to `origin/dev`.
- Local `dev` and remote `origin/dev` resolve to `79145d7`; the working tree is
  clean.
- `main` was not modified.

## Earlier history

See the preceding commits for the existing autonomous content-expansion
batches. This changelog intentionally records the current integration batch
without rewriting that history.
