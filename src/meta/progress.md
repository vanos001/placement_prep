# Integration Progress

> Work log for 2026-08-02 to 2026-10-13. All counts are from the working tree after each change.

## Research Projects expansion round — 2026-10-17 (Round 16)

43 new pages added to `src/research-projects/` (follow-up tree +8 chains,
assumptions hunt +7 audits, connection atlas +7 connections, why-not handbook
+7 comparisons, failure casebook +6 incident case histories, misconceptions
+8 audited claims), taking the part to 95 pages / ~220K words. New casebook
incidents (Ariane 5, Heartbleed, GitLab 2017, CrowdStrike 2024, Fastly 2021,
AWS us-east-1 2021) each reconstructed from primary sources with CONFIRMED vs
INTERPRETATION separation. Part description line removed from SUMMARY.md per
user feedback. Scoped validation: 0 broken links, 0 fence problems, Mermaid
5,563/5,563 pass, SUMMARY navigation OK (4,306/4,307, only SUMMARY itself
unreferenced). Per-project Coverage Ledgers updated with sources and gaps.

## Research Projects round — 2026-10-17

52 new pages under `src/research-projects/` (hub + six collections: follow-up
tree 7, assumptions hunt 8, connection atlas 10, why-not handbook 8, failure
casebook 7, misconceptions 11), wired as the new top-level SUMMARY part
"Research Projects" (6 sub-sections, 52 entries). ~109K words, 10 Mermaid
diagrams. Wired into `src/SUMMARY.md`; per-project Coverage Ledgers live in
each collection's index. Scoped validation: 0 broken links/anchors across all
52 files, 0 fence problems, Mermaid heuristic 100% pass repo-wide (5,556).
Failure Casebook incidents sourced to primary postmortems/orders (SEC 3-15570,
AWS/Cloudflare/GitHub/Meta first-party reports, Leveson-Turner IEEE 1993).

## Linux userland binaries round — 2026-10-09

280 new pages under `src/linux/binaries/` (one page per binary across 16
collections, hubs included), wired as the new top-level SUMMARY part
"Linux Userland Binaries". Page counts: 3,105 → 3,385 content pages.
Words ~7.09M → ~7.73M. Unique external URLs 12,035 → 12,370. Mermaid
diagrams unchanged at 5,527 (new pages favor house-style ASCII diagrams);
all pass the real mermaid@11 parser. Validation: 0 broken links, 0
duplicate SUMMARY destinations, MathJax clean. Reference URLs verified
live the day of writing (285 per-binary manpages + source browsers).

## Research branch — 2026-08-02 to 2026-09-02

The `research` branch (75 commits ahead of `main`) landed 660 new markdown files (~174K lines) and 66 batch-style deep-dive pages. All counts below are from the `research` tree @ `9c249de`.

| Step | Result |
|---|---|
| Batches 1 → 66 | Each batch produced 3–4 heavily-cited pages (Crossref DOIs, RFC verbatim, source-code-verified constants). Topics span schedulers (EEVDF, EASY/FCFS backfilling), RCU torture testing, transient-execution attacks, Zobrist hashing, pdqsort, NVIDIA MIG, QUIC congestion control, Haystack/SeaweedFS, LMAX Disruptor, GPU warp scheduling, CUDA Graphs, Intel RDT/resctrl, and more. |
| Summary navigation | `SUMMARY.md` grew from ~2,116 refs (2026-08-16) → **2,776 refs** at `9c249de` (0 broken, 0 duplicate destinations). |
| Mermaid diagrams | 4,889 diagrams across 1,328 files, 100% passing the real `mermaid@11` parser (not only the heuristic). |
| MathJax | balanced across 128 math pages. |
| Demo QA | every CLI / code demo byte-exact against an instrumented reference run; commit messages record the byte-identical stdout. |
| Citation discipline | Crossref-verified DOIs (Spectre 10.1109/SP.2019.00002, Mu'alem-Feitelson 10.1109/71.932708, Musser SPE 1997, Lindholm 10.1109/MM.2008.31), RFC-verbatim QUIC frame types and header-protection sample sizes, Slurm `bf_*` parameter names from `sched_config.html`. |
| Audit & QA fixes | Deep-read audit (2026-09-02) confirmed 100% coverage of all 1,528 prompt.md topics and all 1,374 index.md bullets. Audit-driven fixes: Meltdown CVE corrected to CVE-2017-5754, GrapheneOS→Graphene/Gramine libOS clarification, GPT-4 175B→GPT-3 175B, mirror-clock formula corrected to `11:60 − H:M`, four aptitude worked examples rewritten without leaked AI monologue (calendar, mirror, boat, escalator, ages), four DSA worked examples repaired (ch36 diff-array reconstruction, ch178 Burnside cube, ch121 Lyndon minimal rotation, ch169 min-cost-max-flow), EEVDF benchmark block labelled illustrative, and meta/* refreshed. |

## Advanced Topics Expansion — 2026-08-15

| Step | Result |
|---|---|
| Wrote 1,528 advanced topics across 20 sections (A-T) | 131 new markdown files, ~249K words in 19 new directories |
| Sections covered | A: Advanced OS, B: Linux Kernel, C: Distributed Systems, D: Distributed Storage, E: Advanced DBs, F: Advanced Algorithms, G: PL/Compilers, H: Computer Architecture, I: HPC, J: Networking Research, K: Formal Methods, L: Security Research, M: Blockchain, N: AI Systems, O: AI+Distributed, P: Cloud/Serverless, Q: Edge/IoT, R: Quantum, S: Supply Chain, T: Observability |
| Added Build-It-Yourself track | 5 project pages covering OS, DB, distributed, networking, and compiler projects (34 total project ideas) |
| Added Advanced Benchmarking section | Methodology, pitfalls, statistics, tool comparison, perf, flame graphs |
| Fixed 3 missing topics | hugetlbfs, TCP autotuning, zk-rollups appended to existing files |
| Updated SUMMARY.md | 22 new sections + build-it-yourself + benchmarking added |
| Topic coverage | 1,525/1,528 core topics (99.8%) |

## Validation & Cleanup — 2026-08-15

| Action | Result |
|---|---|
| check-summary.py | Fixed 3 missing SUMMARY entries (btrees.md, bitcask.md, page-replacement.md) |
| check-links.py | Fixed 11 broken links in new files (wrong relative paths) |
| validate-mermaid-heuristic.mjs | Fixed 13 mermaid errors (unquoted labels, unmatched quotes, escaped quotes, markdown in blocks) |
| check-mathjax.py | Fixed 3 legacy \$ delimiters, 6 unclosed code fences, 26 single-backslash delimiters |
| Final validation | SUMMARY OK (2,809/2,809 reachable, 0 duplicates), 0 broken internal links/anchors, 4,889/4,889 mermaid pass, MathJax OK, 33,152 fences clean. External URLs: 758 dead — see `scripts/dead-links-report.txt`. |

## Previous Sessions

### Validation & cleanup — 2026-08-15 (earlier)

| Action | Result |
|---|---|
| Ran full validation suite | 7 mermaid errors, 39 broken links, 63 missing SUMMARY entries, 2 unclosed code fences, 2 MathJax delimiter issues |
| Fixed all issues | All validators passing |

### Software Engineering section completion — 2026-08-13

| Step | Result |
|---|---|
| Added testing, devops, CONTRIBUTING pages | Testing levels, CI/CD, contribution guide |
| Registered in SUMMARY.md | All listed under Software Engineering |
| Re-ran validation | 0 broken links, SUMMARY OK, MathJax OK, Mermaid 4,405/4,405 |

### Integration — 2026-08-12 to 2026-08-13

| Step | Result |
|---|---|
| Integrated Linux book (lb2) | 444 pages under src/linux/ |
| Integrated DSA book (dsa_book_2) | 193 pages under src/dsa/ |
| Fixed navigation and links | 0 broken links, all SUMMARY-reachable |
| Mermaid repair | 4,387/4,387 pass |

### Research batches — 2026-08-08 to 2026-08-13

- Added 20+ pages across kernel, networks, backend, languages, storage, concurrency, and interview sections
- All with Mermaid diagrams, interview questions, and real-world references

## Reference library expansion — 2026-10-09

| Step | Result |
|---|---|
| New fourteenth index | `references/dsa-competitive-programming.md` — 170 entries, 72 education resources (37 basic / 35 advanced), 30 research sources, 402 verified URLs, wired into `SUMMARY.md` and `references/README.md`. |
| Video sections | 195 resources across the fourteen indexes (channels, conference recordings and lecture playlists), every channel and playlist fetched and title-checked. |
| Conference sections | 86 sources across the fourteen indexes: conference channels and video archives (USENIX, FOSDEM `video.fosdem.org`, `media.ccc.de`, Linux Plumbers, netdev, LCA, PyCon US, LLVM dev meetings) plus proceedings and note archives (SIGCOMM, SIGPLAN, SIGMOD, VLDB, NeurIPS, ICLR, ICML, CVF, EuroSys, IEEE S&P, SNIA, `;login:`). |
| Rejected rather than guessed | ~35 bad YouTube handles (wrong identity or 404), 4 dead hosts, 2 playlist IDs that resolved to "undefined"; 3 bot-blocked sites kept and flagged. |
| CSVs | `data/*.csv` extended to one row per resource — entries, education, video, conference — including education rows for the four indexes that were entry-only. |
| Documentation | `references/README.md` (Video + Conference columns, recomputed URL counts, corrected totals), root `README.md` (What's Inside, repository structure, stats), `meta/status.md`, `meta/progress.md`, `meta/coverage_dashboard.md`, `meta/knowledge_graph.md`. |



## Linux Interface Encyclopedia - per-function rebuild - 2026-10-12

| Part | Result |
|---|---|
| Structure | One page per syscall/function/class (no per-domain mega-chapters); man-page families share pages per the source-derived `.so` alias map |
| Ledgers | syscalls 535, glibc 1881+3470+1953 rows, musl 1482, sysfs 120, crossref 38 - regenerated from sources, statuses restored from surviving reports |
| Documentation | 194 syscall pages, 122 glibc pages, 6 musl pages, 42 sysfs class pages, 3 crossref maps (367 content pages) |
| Honest gaps | 101 syscall rows source-limited (named), 10 not-started, 12 crossref rows source-limited, glibc 1377 documented-API rows still `researched` |

## Linux Interface Encyclopedia - wave 7 (push to research) - 2026-10-13

| Part | Result |
|---|---|
| Syscalls | 10 not-started rows closed (rlimit family, getrusage, execv, personality, chown32 trio): 388 documented / 46 researched / 101 source-limited of 535; 0 not-started |
| glibc | 157 per-function pages across 6 new dirs (math, threads, termios, users, vm, misc) plus fs/stdio/strings/net additions; ledger 1047 documented / 10 source-limited / 0 researched of the 1881 documented-API rows |
| sysfs | all 77 remaining `researched` classes -> per-class pages (65 documented, 13 honest source-limited stubs): 106 documented / 14 source-limited of 120 |
| crossref | 11 of 12 `source-limited` rows upgraded with fetched upstream docs (NetworkManager, thermald, UPower, libinput, libdrm, rdma-core, ndctl, procps, dmidecode) plus local NSS/kernel sources; XR-112 stays source-limited (msr-tools docs unreachable) |
| Validation | every new page ASCII-only, balanced fences, relative links resolve; statuses/notes flipped in all four ledgers; SUMMARY wired (282 glibc entries, 119 class entries) |

## Section G - eight-language process/runtime semantics - 2026-10-13

| Step | Result |
|---|---|
| Part built | `src/languages/process-runtime/` (18 pages): 8 chapters (C, C++, Python, Go, Java, Rust, Node.js, OCaml; 8.5k-10.4k words each) + 8 G4 coverage ledgers + part hub + 9-dimension comparison (562 lines, 11 tables) |
| Ledger audit | 633 rows inventoried: 623 documented / 10 source-limited / 0 remaining; zero duplicate IDs; rollup numbers match ledger contents exactly |
| G3 reference policy | C/C++/Rust/comparison chapters cited sources by name only (Rust had zero URLs); 209 URLs live-verified, 144 hyperlinks added -> all chapters carry direct source links |
| Link & URL audit | 388 intra-book links resolve; 290/291 external URLs reachable (en.cppreference.com = documented Cloudflare 403 to bots) |
| Acceptance | G1-G6 verified, including equal-rigor OCaml chapter (source-transcribed signatures, verified-absent API list, layer labels) |

## Navigation integrity & warning cleanup - 2026-10-13

| Step | Result |
|---|---|
| Orphan wiring | 295 authored-but-unwired pages joined `SUMMARY.md`: binaries flatlands rebuilt (overview -> 16 collection hubs -> pages), sysfs Class Encyclopedia + crossref maps added, glibc hub moved to block top (it split 282 pages under the musl ledger), 14 pseudo-part titles promoted, Section G ledgers became real nav children (fixing 8 live-site 404s) |
| Summary state | 4,116 nav entries, 0 duplicate destinations, 0 dead entries; real mdBook v0.5.4 stub build with `create-missing=false` exits 0 and renders all 4,119 pages |
| CI fix | duplicate `languages/comparison.md` entry that broke the deploy replaced with a real language-chapters hub page |
| Warning cleanup | 130 mdBook "unclosed HTML tag" warnings eliminated: bare `<token>` placeholders (`ttyS<x>`, `SIG<NAME>`, `<PCI BDF>`) wrapped in inline code across 33 files; negative control mini-build 130 -> 0 warnings, 0 errors |
| Link check | `check-links.py` reports 217 broken links/anchors before AND after (pre-existing repo-wide debt, none in touched files; stash-baseline verified) |
| Fence check | `check-fences.py` clean across 4,120 files |
| Branch sync | research -> dev -> main via explicit `--no-ff` merges, then all three branches fast-forwarded to the same commit (`989c5c3`) |


## Research Projects round 17 — 2026-10-18

| Item | Result |
|------|--------|
| Scope | 41 new chapters across the six research collections (expansion round 17) |
| Follow-up Tree | +7 chains: DNS resolution, TLS handshake, message queues, Kubernetes pod lifecycle, connection pooling, consensus/Raft, regex engines |
| Hidden Assumptions Hunt | +7 audits: clocks and time, text and encoding, containers and resources, DNS, ordering and pagination, randomness and IDs, serialization compatibility |
| Concept Connection Atlas | +7 maps: DNS/CDN edge routing, containers-cgroups-namespaces, auth-identity-session, load balancing-partitioning, JIT-to-silicon, search inverted index, observability pipeline |
| Why-Not Handbook | +7 comparisons: REST vs gRPC, ORM vs raw SQL, TCP vs UDP, sync vs async I/O, ID generation (auto-increment/UUID/Snowflake), row vs column stores, password hashing choices |
| Failure Casebook | +6 verified cases: Cloudflare control plane (Nov 2025), AWS DynamoDB us-east-1 (2015), Mars Climate Orbiter (1999), Toyota unintended acceleration (2009-2011), UK Post Office Horizon (1999-2025), Boeing 737 MAX MCAS (2018-2020) |
| Misconception Elimination | +7 audits: async-await parallelism, encryption-vs-authentication, UDP reliability, checksum equality, single-threaded parallelism, immutability thread-safety, average latency |
| Collection totals | 129 chapters + 7 index pages (~330K words): 21 chains, 21 audits, 23 connections, 21 comparisons, 18 case histories, 25 misconceptions |
| Primary sources | Cloudflare first-party RCA; AWS DynamoDB statement; NASA MCO mishap report; NHTSA/NASA assessment + court materials; UK Horizon Inquiry report + two High Court judgments; NTSB ASR-19/01 |
| QA | Scoped validation: 0 broken links, 0 fence problems, Mermaid 100% pass; SUMMARY.md +41 bare entries; per-project ledgers extended |
