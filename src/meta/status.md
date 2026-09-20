# Project Status

> Status snapshot: 2026-09-19 (research branch @ `506338b`+) — validation passing, plus an independent deep review and fix pass (see "Deep review & fix pass" below).

## Current status

**Research branch complete, independently reviewed, and repaired.** The `research`
branch is **93 commits ahead of `main`** (a strict superset: 0 commits and 0 files
exist on `main` but not here), adding **692 new markdown files**. The repository
contains **2,809 content pages** under `src/` (+`SUMMARY.md`), all reachable from
`SUMMARY.md` with 0 duplicate destinations.

A full external review on 2026-09-19 re-ran every validator from scratch, added a
real `mermaid@11` parse, probed all ~6,500 external URLs, resolved every DOI, and
read high-value pages by hand. It found and fixed: a code-fence corruption class
that rendered prose as code, wrong worked-example mathematics, a MathJax/link
collision, 48 site-root-absolute links, malformed URLs, conflicting kernel sizes,
stale counts in this file, and missing CI. See "Deep review & fix pass".

| Area | Status | Evidence |
|---|---|---|
| Git safety | ✅ Complete | Active development on `research`; `main` (== `dev`, `6f7e79b`) untouched by research commits; research is a clean 93-commit superset. |
| Content inventory | ✅ Expanded | **2,809** content markdown pages under `src/` (up from 2,117 at the 2026-08-16 snapshot). |
| Navigation | ✅ Passing | All 2,809 content pages reachable from `SUMMARY.md` (1 excluded: `SUMMARY.md` itself); 0 duplicate destinations. |
| Internal links | ✅ Passing | 0 broken links / anchors (24,754 links), including site-root-absolute and non-`.md` targets. |
| Mermaid | ✅ Passing | 4,889 of 4,889 diagrams across 1,328 files (100%) — verified with the real `mermaid@11` parser, not only the heuristic. |
| MathJax | ✅ Passing | 0 issues across all 128 math-bearing pages, including 0 math spans containing a literal `](` (which renders as a link). |
| Fence integrity | ✅ New | 0 malformed or nested code fences (33,152 blocks scanned by `scripts/check-fences.py`). |
| Advanced topics | ⚠️ Partially verified | All 1,374 `src/index.md` bullets covered. The earlier "all 1,528 `prompt.md` topics" claim could not be reproduced — **no `prompt.md` exists in the repository**, so that figure is unverifiable and is no longer asserted. |
| Build-it-yourself | ✅ Complete | 34 implementation projects across 5 domains. |
| Benchmarking | ✅ Complete | Methodology, pitfalls, statistics, tool comparison. |
| Research batches | ✅ Complete | 93 research commits (2026-08-02 → 2026-09-05), 66+ "batch" deep-dive pages with Crossref-verified DOIs, RFC-cited networking pages, and byte-exact demo QA. |

## Validation commands

The validation suite re-run on the `research` tree during the 2026-09-19 review:

- `scripts/check-summary.py` → 2,809/2,809 reachable, 0 duplicate destinations
- `scripts/check-links.py` → 0 broken links/anchors (24,754 links)
- `scripts/check-fences.py` → 0 problems across 33,152 fenced blocks
- `scripts/check-mathjax.py` → balanced across 128 math pages, 0 link-in-math hazards
- `scripts/validate-mermaid-heuristic.mjs` → 4,889/4,889 pass (100%)
- real `mermaid@11` parse → 4,889/4,889 pass (100%)
- `scripts/check-doi.py` → 491/491 DOIs resolve

> **External URLs are not fully clean.** A **full-repo sweep of all 8,662
> external links** (2,067 hosts) found **5,872 live** and **761 dead**
> (HTTP 404/410); the remainder returned 403/429/bot-challenge and are counted
> unverifiable, not dead. Three repair passes have fixed **251** dead links —
> each fetched and title-checked first — including **all 471 kernel.org links,
> now 100% live**. Of the rest, **25 are intentional `example.com`
> placeholders** and **522 are genuine broken links** catalogued by host in
> `scripts/dead-links-report.txt`; a further **68 404ing URLs live only inside
> fenced code blocks** (code samples and namespace identifiers, correct as
> written). What remains is overwhelmingly pages deleted upstream — source-tree
> citations whose files exist at no path, retired doc trees, removed vendor
> posts and dead DOIs — so each needs a human substitution decision (re-point,
> replace, or drop) rather than a code fix.
>
> The full mdBook build peaks above the memory limit of the environment used for
> this review, so the review ran a 47-chapter subset build of every changed file
> (clean, zero warnings). Run the full build locally before release.
>
> **Validation is a local/agent step, not a CI step.** CI in this repository is
> reserved for builds and deploys (`.github/workflows/deploy.yml`); adding
> validation jobs would consume hosted minutes on every push. The scripts under
> `scripts/` are meant to be run by a human or an agent in a dev environment.

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

## Deep review & fix pass — 2026-09-19

An independent review of the whole tree (own tooling, real Mermaid parser, live
HTTP probing, DOI resolution, manual page reads) produced the following fixes.
Each is verified, not asserted.

### Correctness

| Defect | Fix |
|---|---|
| 11 fence lines written as `` `` `` / `` ``n `` , whose orphaned closers **opened** runaway code blocks that swallowed prose, headings and tables as code | Restored to well-formed fences in `cloud-scheduling`, `hpc-infra`, `trigonometry`, `approximate-privacy`, `applied-systems`, `reliability-patterns`, `monotonic-queue-dp` |
| `documentation.md`: 4 ` ```markdown ` templates containing ` ```bash ` samples were invalid CommonMark — inner fences closed the outer block, so `### README Best Practices` and friends rendered as code (25 phantom code blocks) | Outer fences widened to ` ````markdown `; verified with a real mdBook build (25 → 19 blocks, headings now `<h3>`) |
| `profit-loss.md`: two wrong formulas for same-SP/different-% (`(x−y)²/(200+x−y)` gives 0 when x=y) plus a proof that contradicted its own conclusion | Corrected to `(100y − 100x + 2xy)/(200 + x − y)`; verified against brute force over 36 (x, y) pairs (max deviation 1.4e-14); proof rewritten to the exact `x²/100` result |
| `time-work.md`: worked example whose premise and arithmetic disagreed, followed by a non-sequitur | Made self-consistent and replaced the trailing paragraph with a real consistency check |
| `ppo.md`: `H[\pi_\theta](s)` inside `\\[...\\]` — Markdown parsed it as a link, so mdBook emitted `H<a href="s">\pi_\theta</a>` and broke the equation | Rewritten with `\lbrack`/`\rbrack`; verified by rendering before/after |
| Linux kernel size given as 28M / 30M / 40M across 7 pages | Unified on ~40M lines (Linux 6.14, 2025) with the measurement scope stated |
| 5 empty `## Interview Frequency` sections (heading immediately followed by a heading) | Converted the stray heading into prose in the book's canonical style |

### Links

| Defect | Fix |
|---|---|
| 48 site-root-absolute links (`[Namespaces](/containers/namespaces)`) — always 404 on the published site, and invisible to `check-links.py` | Repointed to real relative targets; 29 that had no existing target were unlinked or redirected to the correct page |
| `https://docs.yugabyte.compreview/preview/...` ×3, `blog.cloudflare.com/common-hash-conflcit-...`, a URL with a literal space (`~kapil sigmod/x100.pdf`) | Fixed; replacements probed live (all 200) |
| `linux/reference/further-reading.md` listed "Linux Unplugged" twice, the second pointing at Late Night Linux | Second entry corrected to *Late Night Linux* |

### Structure

- Renamed `os/virtual-memory/page-rejection.md` → `page-replacement-overview.md`
  (the filename was a typo for "replacement" and the SUMMARY label hid it).
- Fixed both `SUMMARY.md` indentation jumps (4-space children among 2-space
  siblings) that mis-nested the page-replacement and query-processing groups.
- Disambiguated the three page-replacement pages and the two query-optimization
  pages with distinct nav labels and mutual cross-links; retitled the thin page
  `Page Replacement: Interview Guide` since its H1 collided with the deep dive.
- Expanded `mobile/README.md` from 373 bytes to a full section landing page.

### Tooling & process

- **New `scripts/check-fences.py`** — catches malformed openers, unclosed fences
  and nested fences with CommonMark-correct length rules. Wired into
  `validate-all.sh` as step 2/7. Positive controls confirm it rejects all three
  bug classes and accepts 4-backtick nesting.
- **Hardened `scripts/check-links.py`** — now flags site-root-absolute links and
  non-`.md` relative targets, and strips inline code so C++/Go samples like
  `Sum[int](myInts)` are not misread as links. Explicit allowlist for the
  CI-generated `cross-reference-graph-view.html`.
- **Hardened `scripts/check-mathjax.py`** — detects `](` inside math spans (the
  `ppo.md` bug class), and its always-true `if dollars == line.count("$$")`
  condition is gone (deduplication already happens downstream).
- **CI claims corrected, CI left build-only** — the README badge, CONTRIBUTING and
  `scripts/README.md` variously implied that links/SUMMARY/MathJax/Mermaid were
  validated in CI "and weekly", while the repository's only workflow is the
  `main`-only Pages build+deploy. Rather than adding validation jobs (which would
  bill hosted minutes on every push), the documents now state plainly that the
  suite is run locally by a human or an agent, and the badge says so too.
- `book.toml` edit links now point at `research` (a strict superset of `main`), so
  they resolve for research-only pages instead of 404ing.
- `.gitignore` no longer hides `package.json`/`Cargo.toml`, which had made the
  Mermaid-parser toolchain unreproducible from a fresh clone; added the real-parser
  report path.
- `scripts/dead-links-report.txt` — the 758 dead external URLs grouped by file, as
  an actionable backlog.

### Deliberately not changed

- The 74 colliding-topic page groups (`backend/` vs `distributed/`, `os/` vs
  `concurrency/`, …). Spot-checks showed the duplicates **agree** in substance, so
  merging them is an editorial decision, not a correctness fix.
- `IEEE TBD, 2021` in `vector-databases.md` and `rag-advanced.md` is **not** a
  placeholder: TBD = *IEEE Transactions on Big Data*.
- The `####` sub-headings under `##` sections in `linux/reference/further-reading.md`
  are a consistent file-local style (all 79 entries), not a stray level skip.
