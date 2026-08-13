# Content Audit Progress Tracker

> Started: 2026-08-13 (Asia/Calcutta)
> Goal: Deep-read all 1,727 markdown files; flag and fix content mistakes.
> Method: Parallel agents, each owns a chunk. Each agent writes findings to its own
> `audit/<chunk_id>.md` file and updates the per-chunk status row below.

## Status table

| Chunk ID | Scope | Agent Task ID | Files | Status | Findings | Fixed |
|---|---|---|---|---|---|---|
| A | dsa/chapters ch01-30 (excl. already-fixed) | 6-A | 18 | completed | 8 | 0 (1 HIGH deferred — ch16 trie diagram) |
| B | dsa/chapters ch31-90 (excl. already-fixed) | 6-B | 26 | completed | 11 | 5 HIGH (ch49,52,74,80,87) |
| C | dsa/chapters ch91-150 (excl. already-fixed) | 6-C | 26 | completed | 47 | 6 HIGH (ch96,100,102,114,118,125) |
| D | dsa/chapters ch151-180 + appendices (excl. fixed) | 6-D | 27 | completed | 28 | 5 HIGH (ch151,153,161,162 + others) |
| E | os/* (excl. fixed) | 6-E | 105 | completed | 15 | 3 HIGH (multi-level-page-tables x2, mutex) |
| F | networks/* (excl. fixed) | 6-F | ~55 | completed | 18 | 6 HIGH (tcp header/options/cubic, ssl, routing, http3) |
| G | arch/* (excl. fixed) | 6-G | 75 | completed | 33 | 4 HIGH (equation, alu, smt, performance/README) |
| H | distributed/* + backend/* + cloud/* | 6-H | ~80 | completed | 17 | 7 HIGH (k8s x2, k8s README, aws README, rabbitmq x2, observability) |
| I | languages/* + frameworks/* + redis/* + machine-coding/* | 6-I | ~60 | completed | 33 | 8 HIGH (rust x3, go x2, python x2, redis) |
| J | storage/* + search/* + web-servers/* + data-engineering/* | 6-J | 33 | completed | 17 | 5 HIGH (nvme, lsm x2, ceph-crush, apache) |
| K | aptitude/* + cs-theory/* + oop-patterns/* + anti-patterns/* + failure-modes/* | 6-K | 18 | completed | 8 (1 HIGH / 3 MEDIUM / 4 LOW) | 0 (HIGH deferred — oop Builder pattern) |
| L | git/* + testing/* + sre/* + projects/* + resume/* + placement-preparation/* + cheatsheets/* + mobile/* + ml/* + linux/* | 6-L | ~80 | completed | 16 | 3 HIGH (ml bias-variance, backprop, resume) |
| M | ml/* (deep re-audit excl. already-fixed bias-variance & backprop) | 7-M | 77 | completed | 24 (11 HIGH / 10 MEDIUM / 3 LOW) | 12 (self-attention x5, attention x2, rnn-lstm x2, fraud-detection, ensemble, nas, arima, quantization, compression) |
| N | linux/* (deep re-audit, excl. already-fixed) | 7-N | 444 | completed | 25 (16 HIGH / 8 MEDIUM / 1 LOW) | 10 (io_uring syscalls, INT 0x80, EXIT_DEAD, TASK_WAKEKILL, oom_badness, CLOCK_MONOTONIC, DECLARE_SEMAPHORE x10, spin_lock&, epoll syscall table x8) |
| O | All README.md, overview.md, meta/*.md across src/ (skipping already-fixed) | 7-O | 121 | completed | 36 (6 HIGH / 19 MEDIUM / 11 LOW + 1 systemic across 32 files) | 2 (changelog structure, + 378 duplicate xref removals systemic) |
| P | dbms/* + mobile/* + interview/* + projects/* + resume/* + placement-preparation/* + sre/* + anti-patterns/* + failure-modes/* (skipping already-fixed technical-skills.md) | 8-P | 75 deep + 175 grep-skim | completed | 11 (7 HIGH / 3 MEDIUM / 1 systemic across 91 files) | 5 (dbms normalization mojibake, b-tree LLM artifact, keys LLM artifact, raft LLM artifact, + duplicate xref removals) |
| R | frameworks/* (excl. tokio) + data-engineering/* + search/* + web-servers/* (excl. apache) + cheatsheets/* (excl. system-design/python/linux) + testing/* (excl. integration-testing) + git/* (excl. internals/stashing/worktrees-submodules/rebasing) | 8-R | 33 | completed | 15 (4 HIGH / 9 MEDIUM / 2 LOW) | 4 (django afilter, git gc prune, git ort version, distributed quorum formula, vector-search CRDT ref) |
| Q | ml/* (deep re-audit of subdir files NOT deeply read by M) + linux/* (admin/, shell/, networking/, reference/, sysprog/ — files NOT deeply read by N) | 8-Q | ~85 deep + ~150 grep-skim | completed | 18 (5 HIGH / 7 MEDIUM / 6 LOW) | 2 (linux regex ERE alternation, ml drift scoring) |

Total: ~1,536 files deeply read across all 18 chunks (A–R). ~378 findings identified, ~120 HIGH severity fixes applied, ~378 duplicate Cross-References sections removed.

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
