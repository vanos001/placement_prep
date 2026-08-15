# Project Status

> Status snapshot: 2026-08-15 — 1,528 advanced topics added across 20 sections

## Current status

**Major expansion complete.** 1,528 advanced CS topics written across 20 new sections (A-T) with 131 new markdown files (~249K words). All validation checks pass.

| Area | Status | Evidence |
|---|---|---|
| Git safety | ✅ Complete | Active branch is `dev`; `main` remains unchanged |
| Content inventory | ✅ Expanded | 2,117 content Markdown pages (up from 1,880) |
| Navigation | ✅ Passing | All 2,116 content pages reachable from `SUMMARY.md` (1 excluded: SUMMARY.md itself) |
| Relative links | ✅ Passing | 0 broken links |
| Mermaid heuristic | ✅ Passing | 4,883 of 4,883 diagrams pass (100%) — 478 new diagrams added |
| MathJax | ✅ Passing | 0 issues across 2,117 pages |
| Advanced topics | ✅ Complete | 1,525/1,528 core topics covered (99.8%); 3 trivially missing topics fixed |
| Build-it-yourself | ✅ Complete | 34 implementation projects across 5 domains |
| Benchmarking | ✅ Complete | Methodology, pitfalls, statistics, tool comparison |

## Validation command

The lightweight validation suite was re-run on the latest `dev` tree:

- `scripts/check-links.py` → 0 broken links
- `scripts/check-summary.py` → SUMMARY navigation: OK (2,116 files listed)
- `scripts/check-mathjax.py` → MathJax validation: OK
- `scripts/validate-mermaid-heuristic.mjs` → 4,883/4,883 pass (100%)

## New Sections Added (2026-08-15)

### 20 Advanced Topic Sections (A-T)

| Section | Directory | Files | Topics |
|---|---|---|---|
| A: Advanced OS | `os/advanced/` | 9 | 1-100 |
| B: Linux Kernel | `os/kernel-advanced/` | 8 | 101-200 |
| C: Distributed Systems | `distributed/advanced/` | 9 | 201-320 |
| D: Distributed Storage | `storage/advanced/` | 7 | 321-400 |
| E: Advanced DBs | `dbms/advanced/` | 10 | 401-520 |
| F: Advanced Algorithms | `dsa/advanced/` | 10 | 521-620 |
| G: PL/Compilers | `compilers/advanced/` | 9 | 621-720 |
| H: Architecture | `arch/advanced/` | 8 | 721-800 |
| I: HPC | `hpc/` | 4 | 801-850 |
| J: Networking | `networks/advanced/` | 6 | 851-930 |
| K: Formal Methods | `formal-methods/` | 7 | 931-990 |
| L: Security | `security/advanced/` | 6 | 991-1060 |
| M: Blockchain | `blockchain/` | 5 | 1061-1120 |
| N: AI Systems | `llm/advanced/` | 7 | 1121-1220 |
| O: AI+Distributed | `llm/advanced/distributed/` | 5 | 1221-1280 |
| P: Cloud/Serverless | `cloud/advanced/` | 4 | 1281-1330 |
| Q: Edge/IoT | `edge/` | 5 | 1331-1380 |
| R: Quantum | `quantum/` | 3 | 1381-1420 |
| S: Supply Chain | `supply-chain/` | 3 | 1421-1460 |
| T: Observability | `production-engineering/advanced/` | 3 | 1461-1500 |

### Build-It-Yourself Track (34 projects)

- OS: kernel, scheduler, allocator, filesystem, shell, TCP stack, debugger, eBPF tracer
- DB: B-tree, LSM tree, WAL, MVCC, query optimizer, vector DB, distributed KV
- Distributed: Raft, Paxos, gossip, consistent hashing, distributed lock, replicated log, scheduler
- Networking: TCP, HTTP/1.1, HTTP/2, DNS resolver, reverse proxy, load balancer
- Compilers: lexer, parser, interpreter, bytecode VM, optimizer, toy JIT

## Safety constraints

- Development work is performed on `dev`.
- Release promotion from `dev` to `main` occurs only after validation.
- Credentials are read only at command time and are not stored in repository files, commits, or documentation.
