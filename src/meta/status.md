# Project Status

> Status snapshot: 2026-09-02 (research branch @ `9c249de`) — all validation passing, meta refreshed to include research-branch deep-dive batches.

## Current status

**Research branch complete and audited.** The `research` branch is **75 commits ahead of `main`**, adding **660 new markdown files** (~174K lines) on top of the major expansion that landed on `dev`/`main` in mid-August. The repository now contains **2,777 markdown pages** under `src/`, all reachable from `SUMMARY.md`. All validation checks pass on `research`.

| Area | Status | Evidence |
|---|---|---|
| Git safety | ✅ Complete | Active development on `research`; `main` (== `dev`, `6f7e79b`) untouched by research commits; research is a clean 75-commit superset. |
| Content inventory | ✅ Expanded | **2,777** content markdown pages under `src/` (up from 2,117 at the 2026-08-16 snapshot). |
| Navigation | ✅ Passing | All 2,776 of 2,777 content pages reachable from `SUMMARY.md` (1 excluded: `SUMMARY.md` itself); 0 duplicate destinations. |
| Relative links | ✅ Passing | 0 broken links / anchors. |
| Mermaid heuristic | ✅ Passing | 4,873 of 4,873 diagrams across 1,317 files (100%). |
| MathJax | ✅ Passing | 0 issues across all 128 math-bearing pages. |
| Advanced topics | ✅ Complete | All 1,528 prompt.md topics (A–T) and all 1,374 index.md bullets covered (verified by deep-read audit on 2026-09-02). |
| Build-it-yourself | ✅ Complete | 34 implementation projects across 5 domains. |
| Benchmarking | ✅ Complete | Methodology, pitfalls, statistics, tool comparison. |
| Research batches | ✅ Complete | 75 research commits (2026-08-02 → 2026-09-02), 66+ "batch" deep-dive pages with Crossref-verified DOIs, RFC-cited networking pages, and byte-exact demo QA. |

## Validation commands

The lightweight validation suite re-run on the `research` tree (2026-09-02):

- `scripts/check-summary.py` → 2,776/2,777 reachable, 0 duplicate destinations
- `scripts/check-links.py` → 0 broken links/anchors
- `scripts/check-mathjax.py` → balanced across 128 math pages
- `scripts/validate-mermaid-heuristic.mjs` → 4,873/4,873 pass (100%)

> mdBook build and real-Mermaid (mermaid@11 + jsdom) parse were not re-run in the audit sandbox (binaries not installed); both are expected to be exercised in CI.

## Research-branch additions (2026-08-02 → 2026-09-02)

The research branch added 75 commits and 660 new files. Highlights:

- **Batch-style deep-dives** (batches 1–66): each batch produced 3–4 high-quality, heavily-cited pages on topics spanning scheduler internals (EEVDF, CFS, EASY/FCFS backfilling), RCU torture testing, transient-execution attacks, Zobrist hashing, pdqsort, NVIDIA MIG, QUIC congestion control, Haystack/SeaweedFS, LMAX Disruptor, GPU warp scheduling, CUDA Graphs, Intel RDT/resctrl, and many more.
- **Citation discipline**: Crossref-verified DOIs (e.g. Spectre 10.1109/SP.2019.00002, Mu'alem-Feitelson TPDS'01 10.1109/71.932708, Musser SPE 1997, Lindholm IEEE Micro 10.1109/MM.2008.31), RFC-verbatim QUIC frame types and header-protection sample sizes, and Slurm `bf_*` parameter names quoted verbatim from `sched_config.html`.
- **Demo QA**: every CLI / code demo is byte-exact against an instrumented reference run; batch commit messages record the byte-identical stdout.

## Original major expansion (2026-08-15)

### 20 Advanced Topic Sections (A–T)

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

- Development work is performed on `research` (and `dev` before promotion).
- Release promotion to `main` occurs only after validation.
- Credentials are read only at command time and are not stored in repository files, commits, or documentation.
