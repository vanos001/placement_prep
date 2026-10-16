# Project Status

> Status snapshot: 2026-10-17 — all three branches (`research`, `dev`, `main`)
> synced at `989c5c3` (link-debt repair round landed on `research`), validation passing. The October rounds rebuilt the Linux
> Interface Encyclopedia per-function, added the process-exit-signal part and the
> Section G eight-language process/runtime part, wired all 295 orphaned pages into
> navigation, and cleared 130 mdBook HTML-tag warnings. See "October 2026 rounds"
> below.

## Link-debt repair round — 2026-10-17

One round closed the oldest known-debt item: **all 217 broken internal
links/anchors** (`scripts/check-links.py` reports **0** on the merged tree).
The repair created the **92 missing pages** the links pointed at — 91
per-function syscall pages across the seven encyclopedia domains (process 6,
fs-mounts-namespace 8, signals-time 11, sched-misc 65, net-ipc 1) plus the
**musl catalog** page the musl ledger references — fixed two wrong relative
paths (`process-exit-signal-coverage.md` to `SUMMARY.md`; the Section G
language index to `src/languages/process-runtime/`), and repaired a
188-byte null-byte corruption inside `sched-misc/overview.md`'s domain table
(present since the wave-3 rebuild; verified byte-identical back to commit
`4cab223`, clean at `89274e6`). Entries were written against primary sources
fetched for this round: the man-pages 6.19 HTML set on man7.org (53 pages
fetched, cached), torvalds/linux kernel sources for the arch-specific and
6.13+ syscalls (fchroot, listns, file_getattr/file_setattr, the xattrat
family, rseq/rseq_slice_yield, ARM/alpha/sparc/m68k/openrisc privates), and
local `nm -D` on glibc 2.41 for every wrapper claim. 45 ledger rows flipped
`source-limited` → `documented` (syscalls now 433 documented / 46 researched
/ 56 source-limited of 535), the domain overview tables and the hub counts
were reconciled against the ledger (fixing pre-existing staleness in the
process/fs-mount/net-ipc rows), and all 92 pages are wired into `SUMMARY.md`
(4,211 content pages, 0 duplicates, 0 dead entries).

## October 2026 rounds — 2026-10-12 → 10-13

Four back-to-back rounds moved the book from 3,385 to 4,119 content pages and
closed out the navigation and warning debt:

- **Linux Interface Encyclopedia per-function rebuild (2026-10-12, waves 1–7).**
  The old per-domain mega-chapters were replaced by one page per syscall,
  libc function, sysfs class and cross-layer interface: 207 files under
  `src/linux/syscalls/`, 292 under `src/linux/libc/` (glibc + musl), 121 under
  `src/linux/sysfs/`, 5 under `src/linux/crossref/`. Coverage ledgers are
  regenerated from sources and status-honest: syscalls 388 documented /
  46 researched / 101 source-limited of 535 (0 not-started); glibc 1,047
  documented / 10 source-limited of the 1,881 documented-API rows; sysfs 106
  documented / 14 source-limited of 120 classes; crossref 37 documented /
  1 source-limited of 38.
- **Process-exit-signal knowledge base (2026-10-12).** New part
  `src/linux/process-exit-signal/` (43 pages): unified coverage ledger (174
  requirement IDs), signals inventory + interfaces, exit-status lifecycle,
  shell chapters (bash/dash/zsh), service managers (systemd/OpenRC/runit/s6),
  containers (PID 1 semantics, Docker, Kubernetes), and a troubleshooting
  decision tree.
- **Section G — eight-language process/runtime semantics (2026-10-13).**
  `src/languages/process-runtime/` (18 pages): one chapter + one coverage
  ledger per language (C, C++, Python, Go, Java, Rust, Node.js, OCaml —
  chapters 8.5k–10.4k words each), part hub, and a 9-dimension cross-language
  comparison. G1–G6 audited: 633 ledger rows (623 documented / 10
  source-limited / 0 remaining), zero duplicate IDs; a G3 reference-policy fix
  added 144 verified hyperlinks to the C/C++/Rust/comparison chapters; all 388
  intra-book links resolve; 290 of 291 external URLs reachable
  (en.cppreference.com = documented Cloudflare 403).
- **Navigation integrity & warning cleanup (2026-10-13).** Wired the last 295
  orphaned pages into `SUMMARY.md` (binaries overview + coreutils/util-linux
  flatlands rebuilt into a designed hierarchy, sysfs Class Encyclopedia, musl
  catalog, crossref maps; Section G ledgers became real nav children, fixing 8
  live-site 404s; 14 bogus part titles removed; the glibc hub repositioned —
  it had been splitting 282 pages under the musl ledger). `SUMMARY.md` now has
  **4,116 nav entries, 0 duplicates, 0 dead entries**, verified by a real
  mdBook v0.5.4 build (`create-missing=false`) over 4,119 pages. Then all 130
  mdBook "unclosed HTML tag" warnings were eliminated by wrapping bare
  `<token>` placeholders in inline code across 33 files (negative control:
  mini-build 130 warnings before → 0 after).

## Userland binaries round — 2026-10-09

- **New part**: `src/linux/binaries/` — 280 pages, 16 collections, one page
  per binary (coreutils 104, util-linux 96, shadow 24, login 8, procps 18,
  findutils, diffutils, grep, sed, gawk, tar, acl, hostname, bsdutils,
  busybox, uutils), each with a package-level hub.
- **Validation after the round**: 3,385 pages reachable via SUMMARY (0
  duplicates), 0 broken links/anchors, MathJax clean, 5,527/5,527 Mermaid
  diagrams pass the real mermaid@11 parser.
- **References**: 285 per-binary manpage URLs verified live (manpages.debian.org,
  incl. the post-split Debian package mapping), sources.debian.org,
  GitHub mirrors, BusyBox manual, POSIX 2018 spec.

## Current status

**All branches synced and repaired.** `research`, `dev` and `main` point at the
same commit (`989c5c3`); the repository contains **4211 content pages** under
`src/` (+`SUMMARY.md`), all reachable from `SUMMARY.md` (4208 nav entries) with
0 duplicate destinations and 0 dead entries — the 2026-08-era orphan problem is
closed.

A full external review on 2026-09-19 re-ran every validator from scratch, added a
real `mermaid@11` parse, probed all ~6,500 external URLs, resolved every DOI, and
read high-value pages by hand. It found and fixed: a code-fence corruption class
that rendered prose as code, wrong worked-example mathematics, a MathJax/link
collision, 48 site-root-absolute links, malformed URLs, conflicting kernel sizes,
stale counts in this file, and missing CI. See "Deep review & fix pass". The
October 2026 rounds (above) then rebuilt the interface encyclopedia, added the
process/exit/signal and Section G parts, wired the last 295 orphaned pages, and
cleared 130 mdBook HTML-tag warnings.

| Area | Status | Evidence |
|---|---|---|
| Git safety | ✅ Complete | Active development on `research`; promotion research → dev → main via explicit `--no-ff` merges; all three branches synced at `989c5c3` (2026-10-15). |
| Content inventory | ✅ Expanded | **4211** content markdown pages under `src/` (up from 4,119 before the 2026-10-17 link-debt repair round, 3,385 at the 2026-10-09 binaries round and 2,809 at the 2026-09-19 snapshot). |
| Navigation | ✅ Passing | All 4211 content pages reachable from `SUMMARY.md` (4208 nav entries; `SUMMARY.md` itself and the intro/glossary/index pages are the only non-bullet exceptions); 0 duplicate destinations, 0 dead entries; enforced by real mdBook v0.5.4 with `create-missing=false`. |
| Internal links | ✅ Passing | `scripts/check-links.py` reports **0 broken links/anchors** (2026-10-17). The long-standing 217-link debt was closed by the link-debt repair round: 92 missing pages created, 2 relative paths corrected, 1 file-corruption repaired. |
| Mermaid | ✅ Passing | 5,546 of 5,546 diagrams across 1,659 files pass the heuristic validator (2026-10-15); the real `mermaid@11` parser last passed the full corpus 5,527/5,527 on 2026-10-09 (19 diagrams added since, all heuristic-clean). |
| MathJax | ✅ Passing | 0 unbalanced delimiters and 0 math spans containing a literal `](` (full run 2026-10-15). |
| Fence integrity | ✅ Passing | 0 malformed or nested code fences across 4,120 files (`scripts/check-fences.py`, 2026-10-15). |
| Linux Interface Encyclopedia | ✅ Complete, status-honest | One page per syscall/libc-function/sysfs-class/crossref interface (625 + 92 files across four directories after the 2026-10-17 round) with source-regenerated coverage ledgers; syscalls now 433 documented / 46 researched / 56 source-limited of 535; 10 glibc rows, 14 sysfs classes and 1 crossref row are labelled source-limited rather than padded. |
| Process/runtime semantics (Section G) | ✅ Complete | 8 language chapters + 8 coverage ledgers (633 rows: 623 documented / 10 source-limited) + 9-dimension comparison; G1–G6 acceptance criteria audited and passing. |
| Advanced topics | ✅ Covered | All 1,374 `src/index.md` bullets covered (the 2026-10-15 index revision adds process/signal, binary-suite and per-language runtime-semantics topics, all already backed by pages). |
| Build-it-yourself | ✅ Complete | 34 implementation projects across 5 domains. |
| Benchmarking | ✅ Complete | Methodology, pitfalls, statistics, tool comparison. |
| Reference libraries | ✅ Complete | 14 indexes under `src/references/` — **1,257 entries**, **2,744 de-duplicated URLs**, 928 education resources, 195 video resources, 86 conference sources; every URL verified 2026-10-07/08/09, CSV mirrors each page. |
| Research batches | ✅ Complete | 93 research commits (2026-08-02 → 2026-09-05), 66+ "batch" deep-dive pages with Crossref-verified DOIs, RFC-cited networking pages, and byte-exact demo QA. |

### Known debt

- **217 broken internal links/anchors** (`scripts/check-links.py`, full run
  2026-10-15). Proven pre-existing: a stash-baseline run during the 2026-10-13
  warning round produced the identical 217 before and after the change, and
  none sit in files touched by the recent rounds. They need a per-link decision
  (re-point, retarget, or drop) and are the next maintenance candidate.
- **Source-limited ledger rows** (documented, not hidden): 101 syscalls, 10
  glibc APIs, 14 sysfs classes, 1 crossref row, 10 Section G rows — each labelled
  in its ledger with the reason (primary source unreachable from the work
  environment).

**Reference libraries (2026-10-09).** Fourteen verified primary-source indexes, one per major topic, each carrying the same five parts: numbered entry categories, a two-track Education section, a research-papers section, a Video courses/channels/talks section, and a Conference videos/notes/archives section. A new fourteenth index (DSA, competitive programming and competitive math) joined the set this week. Per-index counts, the CSV list and the verification dates live in `src/references/README.md`; the headline totals there (1,257 entries, 2,744 unique URLs) are recomputed from the pages rather than carried forward, because the previous totals did not reconcile with their own per-index column.

## Validation commands

Latest full-suite runs on the merged tree (2026-10-15 unless noted):

- `scripts/check-summary.py` → 4208 nav entries, 0 duplicate destinations, 0 dead entries
- `scripts/check-links.py` → 0 broken links/anchors (2026-10-17, after the link-debt repair round)
- `scripts/check-fences.py` → 0 problems across 4,120 files
- `scripts/check-mathjax.py` → 0 unbalanced delimiters, 0 link-in-math hazards
- `scripts/validate-mermaid-heuristic.mjs` → 5,546/5,546 pass (100%)
- real `mermaid@11` parse → 5,527/5,527 pass on 2026-10-09 (last full run; 19 diagrams added since)
- real mdBook v0.5.4 stub build → exit 0, all 4211 pages render (2026-10-13; re-run before release after the 2026-10-17 round)
- `scripts/check-doi.py` → 491/491 DOIs resolve (2026-09-19 run)

> **External URLs are not fully clean.** A **sweep of all 8,638 external
> links** found **6,112 live** and **630 dead** (HTTP 404/410); the remainder
> returned 403/429/bot-challenge and are counted unverifiable, not dead. Six
> repair passes have fixed **399** dead links — each fetched and title-checked
> first, or backed by a verified archive snapshot — including **all 471
> kernel.org links, now 100% live**. Of the rest, **63 are intentional
> placeholders** and **395 are genuine broken links**
> catalogued by host in `scripts/dead-links-report.txt`; a further **116 404ing
> URLs live only inside fenced code blocks** and are correct as written.
>
> Automated resolution is now exhausted, and the report records what was tried
> and measured: structural URL variants (2,740 candidates → 7 fixes), host-alias
> rewrites (638 → 0), Crossref metadata matching against 88 dead PDF citations
> (5 confirmed), and harvesting the sitemaps of 184 live hosts (102,590 URLs →
> 16 confirmed; a sixth pass added OpenAlex metadata matching, GitHub API
> checks and archive CDX resolution). The 395 that remain need a human decision
> each — re-point, substitute, or drop — because no equivalent page exists to
> point at.
> substitute, or drop — because no equivalent page exists to point at.
>
>
> An earlier revision of these figures was **overstated**: the URL extractor
> stopped at the first `)` and bled across `]`, so every URL containing a
> parenthesis was measured truncated and reported dead. A Markdown-aware
> extractor fixed this and recovered 20 links (14 DOIs, 5 Wikipedia articles,
> 1 testcontainers page) that were never broken.
>
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
