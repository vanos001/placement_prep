# Mermaid Validation Report

Validated with the real Mermaid v11 parser (`mermaid.parse`) on the `dev2` branch.

- **Files with diagrams:** 696
- **Total diagrams:** 2475
- **Passed:** 2475
- **Failed:** 0
- **Pass rate:** 100.0%

## Fix summary (2026-08-08)

- **120 diagrams in 93 files** previously failed real-parser validation while the
  heuristic validator reported 100% — the heuristic checks were too shallow.
- Common root causes fixed:
  - Unquoted node/edge labels containing `()`, `|`, `{}`, `[brackets]`, or unicode
    math glyphs → wrapped in double quotes (verified break-set for Mermaid v11:
    `( ) { } |`).
  - Nested/unbalanced quotes inside quoted labels → replaced with the `#quot;`
    HTML entity (Mermaid v11 does not support `\"` escaping reliably).
  - `Note over ...` (sequence-diagram syntax) inside `graph`/`flowchart` blocks →
    converted to standalone annotation nodes.
  - `;` inside `sequenceDiagram` message text and `Note` text → replaced with the
    `#59;` entity (raw semicolons break the sequence-diagram lexer).
  - Multiple node definitions on a single line → one statement per line.
  - `subgraph` titles with spaces/`=` without explicit IDs → `subgraph ID["Title"]`.
  - Malformed edge labels (`-->|No G[...]` → `-->|No| G[...]`), single-arrow `->`
    in flowcharts → `-->`, bare `...` lines in sequence diagrams → `Note`, and
    bare text lines in sequence diagrams → `Note over`.
- **Validator upgrade**: `validate-mermaid.mjs` now catches these real break
  patterns (was reporting 100% while 120 diagrams failed). All new diagrams are
  validated with both the heuristic and the real parser.
