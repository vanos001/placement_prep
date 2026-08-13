# Content Audit Progress Tracker

> Started: 2026-08-13 (Asia/Calcutta)
> Goal: Deep-read all 1,727 markdown files; flag and fix content mistakes.
> Method: Parallel agents, each owns a chunk. Each agent writes findings to its own
> `audit/<chunk_id>.md` file and updates the per-chunk status row below.

## Status table

| Chunk ID | Scope | Agent Task ID | Files | Status | Findings | Fixed |
|---|---|---|---|---|---|---|
| A | dsa/chapters ch01-30 (excl. already-fixed) | 6-A | 18 | completed | 8 | - |
| B | dsa/chapters ch31-90 (excl. already-fixed) | 6-B | 26 | completed | 11 | - |
| C | dsa/chapters ch91-150 (excl. already-fixed) | 6-C | 26 | completed | 47 | - |
| D | dsa/chapters ch151-180 + appendices (excl. fixed) | 6-D | 27 | completed | 28 | - |
| E | os/* (excl. fixed) | 6-E | 105 | completed | 15 | - |
| F | networks/* (excl. fixed) | 6-F | ~55 | completed | 18 | - |
| G | arch/* (excl. fixed) | 6-G | 75 | completed | 33 | - |
| H | distributed/* + backend/* + cloud/* | 6-H | ~80 | completed | 17 | - |
| I | languages/* + frameworks/* + redis/* + machine-coding/* | 6-I | ~60 | completed | 33 | - |
| J | storage/* + search/* + web-servers/* + data-engineering/* | 6-J | 33 | completed | 17 | - |
| K | aptitude/* + cs-theory/* + oop-patterns/* + anti-patterns/* + failure-modes/* | 6-K | 18 | completed | 8 (1 HIGH / 3 MEDIUM / 4 LOW) | - |
| L | git/* + testing/* + sre/* + projects/* + resume/* + placement-preparation/* + cheatsheets/* + mobile/* + ml/* + linux/* | 6-L | ~80 | completed | 16 | - |

Total: ~537 files in this round (the remaining ~1190 are mostly appendix/index/README
files that are short and will be batched in a final pass after these chunks complete).

## Already-fixed files (DO NOT re-audit)

See `audit/already_fixed.md` for the list of files fixed in prior commits. Agents
should skip these.

## Per-chunk file format

Each agent writes `audit/<chunk_id>.md` with:
1. Header with scope and file count
2. Per-file findings (file:line, severity, wrong text, correct text, verification method)
3. Summary at the end with counts

## Workflow

1. Agent reads `audit/already_fixed.md` to know what to skip
2. Agent deep-reads each file in its chunk (verify arithmetic with Python, verify
   technical claims with web search where needed)
3. Agent writes findings to `audit/<chunk_id>.md`
4. Agent updates its row in this table (Status → completed, Findings count → N)
5. Parent (main agent) reads the chunk audit file, applies fixes, commits, pushes
6. Parent updates Fixed column

## Conventions

- Severity: HIGH (teaches wrong answer) / MEDIUM (misleading) / LOW (cosmetic)
- Always quote the exact wrong text
- Always provide the correct text with justification
- For arithmetic: verify with Python and include the verification command
- For technical claims: cite source (RFC, official docs, textbook)
