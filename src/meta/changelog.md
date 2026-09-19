# Changelog

This file records meaningful content and validation changes to the placement
preparation book. Dates use the project timezone, Asia/Calcutta.

## 2026-09-19 — Independent review and fix pass

Full audit of the `research` tree, then repair of every defect it found. Net result:
the book's own validators are now stronger than the ones that missed these bugs.

- **Code fences (11 lines / 7 files)** — fences abbreviated to a bare double backtick, and the mangled
  double-backtick-plus-`n` form
  left an orphaned closer that *opened* a runaway code block, so following prose,
  headings and tables rendered as code. Repaired in `cloud-scheduling`,
  `hpc-infra`, `trigonometry`, `approximate-privacy`, `applied-systems`,
  `reliability-patterns`, `monotonic-queue-dp`; a stray mangled fence token deleted from
  `approximate-privacy.md:75`. Verified over all 33,152 fenced blocks.
- **`documentation.md` nested fences (4 blocks)** — ```` ```markdown ```` templates
  containing ```` ```bash ```` samples were invalid CommonMark; the inner fence closed
  the outer block, producing 25 phantom code blocks and swallowing the section's
  headings. Outer fences widened to 4 backticks and verified with a real mdBook build.
- **`profit-loss.md`** — replaced two wrong same-selling-price formulas (one
  contradicts its own proof) with the exact `Loss% = x²/100` result and the general
  `Net% = (100y − 100x + 2xy)/(200 + x − y)`; brute-force verified over 36 pairs.
  The vacuous "Trick 4" became a derived breakeven `y = 100x/(100 + 2x)`.
- **`time-work.md`** — worked example rewritten so its premise, arithmetic and
  conclusion agree, with an explicit consistency check.
- **`ppo.md` MathJax/link collision** — `H[\pi_\theta](s)` inside display math was
  parsed as a Markdown link, rendering `H<a href="s">…</a>`. Rewritten with
  `\lbrack`/`\rbrack`; render-verified.
- **48 site-root-absolute links** — `[x](/a/b)` never resolves in an mdBook and was
  invisible to `check-links.py`. Repointed or removed.
- **URL repairs** — `docs.yugabyte.compreview/...` ×3, a dead Cloudflare
  consistent-hashing blog, a URL containing a literal space (X100/MonetDB), and a
  duplicated "Linux Unplugged" entry that actually pointed at Late Night Linux.
- **Stale/incorrect counts** — kernel size unified on ~40M lines (Linux 6.14) across
  the 7 pages that disagreed; page/diagram/math counts refreshed in README, `status`,
  `progress`, `coverage_dashboard` and the cross-reference graph.
- **"prompt.md" claim retracted** — `meta/status.md` asserted full coverage of 1,528
  `prompt.md` topics, but no `prompt.md` exists in the repository.
- **Structure** — `page-rejection.md` → `page-replacement-overview.md`; two
  `SUMMARY.md` indentation jumps fixed; collision labels disambiguated for the three
  page-replacement and two query-optimization pages; `mobile/README.md` expanded
  into a landing page.
- **Tooling** — new `scripts/check-fences.py` (wired in as validate step 2/7);
  `check-links.py` now catches site-root-absolute and non-`.md` targets and no longer
  mistakes C++/Go samples such as `Sum[int](myInts)` for links; `check-mathjax.py`
  detects `](` inside math spans and drops an always-true condition.
- **CI deliberately left build-only** — the README badge, CONTRIBUTING and
  `scripts/README.md` claimed validation ran in CI "and weekly", but the only
  workflow is the `main`-only Pages build+deploy, so `research` had never been
  built by CI. Validation is a local/agent step in this repository to avoid
  burning hosted minutes; the documents and the badge were corrected to say so
  instead of adding validation jobs.
- **Known backlog** — 758 dead external URLs (647 × HTTP 404, mostly invalid
  `docs.kernel.org` deep paths), catalogued in `scripts/dead-links-report.txt`.
  Internal links, anchors, SUMMARY, Mermaid, MathJax, fences and all 491 DOIs are clean.

## 2026-08-13 — Software Engineering: dedicated Testing, DevOps, and Contributing pages

- Added `software-engineering/testing.md` (levels, types, TDD/BDD, strategy),
  `software-engineering/devops.md` (CI/CD, deployment strategies, IaC), and
  `software-engineering/CONTRIBUTING.md` (contribution guide).
- Registered all three in `SUMMARY.md`; re-pointed the Software Engineering
  README and `documentation.md` links to the new local pages (previously routed
  to `../testing/README.md`, `../cloud/cicd/README.md`, and a GitHub URL).
- Validation after change: 0 broken links, Summary navigation OK, MathJax OK,
  Mermaid heuristic 4,405/4,405.
- Committed on `dev` as `6318d8b` and pushed to `origin/dev`; `main` unchanged.

## 2026-08-13 — Pull and topic-completeness audit

- Fast-forwarded local `dev` to remote commit `61ac3ce`.
- Found ten Summary entries whose target files were absent and added concise,
  referenced pages for data formats, data quality, search fundamentals, vector
  search, technical interviews, group discussions, SQL window functions,
  joins, DBMS concurrency scenarios, and testing interview questions.
- Repaired four stale links in Software Engineering and testing documentation.
- Validation after repair: 0 broken links, complete Summary reachability,
  MathJax OK, Mermaid 4,405/4,405, and Mermaid v11 parser 4,405/4,405.
- Work remains on `dev`; `main` was not modified.


## 2026-08-13 — Massive content expansion (parallel agents)

Six parallel agents are creating comprehensive new sections:

### Git Section (15 files)
- `src/git/README.md` — Overview and chapter outline
- `src/git/internals.md` — Objects (blob, tree, commit, tag), refs, HEAD, index, packfiles, SHA-1
- `src/git/fundamentals.md` — Setup, config, staging, committing, diffing, undoing
- `src/git/branching.md` — Branches, fast-forward, three-way merge, conflicts, octopus merge
- `src/git/rebasing.md` — Rebase, interactive rebase, --onto, autosquash, rerere
- `src/git/stashing.md` — Stash operations, partial stashing, branch from stash
- `src/git/advanced.md` — cherry-pick, revert, reset, reflog, bisect, worktree, submodule, blame, grep
- `src/git/remotes.md` — fetch, pull, push, force-with-lease, multiple remotes
- `src/git/tags.md` — Lightweight vs annotated, semver, GPG signing
- `src/git/hooks.md` — Client-side (pre-commit, commit-msg, pre-push), server-side (pre-receive, update)
- `src/git/workflows.md` — Trunk-based, GitFlow, GitHub Flow, GitLab Flow, forking
- `src/git/github.md` — PRs, code review, branch protection, CODEOWNERS, GitHub Actions
- `src/git/interview-questions.md` — 25+ questions from beginner to advanced + scenarios
- `src/git/cheat-sheet.md` — Quick reference for all commands

### Software Engineering Section (10 files)
- SDLC models, Agile/Scrum, requirements engineering, software design (SOLID)
- Code quality, documentation, project management, metrics, team dynamics
- Interview questions covering all SE topics

### Programming Fundamentals Section (10 files)
- Variables/types, scope/lifetime, functions (closures, HOFs, generators)
- Error handling, type systems, memory model, I/O/serialization
- Modules/packages, interview questions

### Aptitude & Placement Preparation (17 files)
- Quantitative: percentages, ratios, averages, profit/loss, time/work, speed/distance
- Logical: probability, number systems, logical reasoning, data interpretation
- Placement: campus process, online assessment, technical/HR interview, group discussion

### Resume, Behavioral, Communication (15 files)
- Resume: structure, bullet writing, projects, technical skills, ATS optimization
- Behavioral: STAR method, 30+ common questions, company fit, scenarios
- Communication: technical, interview, written

### Machine Coding & Practical Problems (22 files)
- Machine coding: parking lot, elevator, library, splitwise, rate limiter, LRU cache, task scheduler
- Practical problems: parsers, CLI tools, file processing, concurrent problems, system utilities
- DBMS interview problems: classic SQL, window functions, joins, optimization, concurrency

### Security, Data Engineering, Search (18 files)
- Security: authentication (OAuth/OIDC/JWT), authorization (RBAC/ABAC), web security (OWASP Top 10)
- Cryptography: AES/RSA/ECC, TLS, password hashing, certificates, PKI
- Data engineering: Spark, Kafka, Airflow, Parquet/Avro/ORC, data quality
- Search: inverted indexes, TF-IDF/BM25, Elasticsearch, vector search

## 2026-08-12 — Research loop batch 4

- Added `backend/api/graphql-federation.md` with entities, composition,
  directives, query planning, schema governance, and failure modes.
- Added `distributed/fundamentals/distributed-locks.md` with lease races,
  fencing tokens, Redis/Redlock, ZooKeeper, etcd, and lock alternatives.
- Added `storage/tiered-storage.md` with hot/warm/cold policies, RocksDB
  tiering, object lifecycle, caching, cost, latency, and recovery trade-offs.
- Added navigation, cross-reference edges, backlog markers, and coverage data
  for the research batch.

## 2026-08-12 — Research loop batch 3

- Added `networks/ebpf-networking.md` using Linux kernel networking/BPF docs,
  AF_XDP, XSKMAP, SOCKMAP, BPF maps, Cilium, and eBPF Docs references.
- Added `languages/rust/async-runtimes.md` using the Rust Async Book, Tokio,
  smol, async-std, Glommio, Monoio, and Embassy documentation.
- Added `backend/observability/opentelemetry.md` using OpenTelemetry signal,
  propagation, semantic-convention, sampling, and specification docs.
- Added Summary links, graph edges, backlog markers, and coverage updates.

## 2026-08-12 — Research loop batch 2

- Added `storage/nvmeof.md` using current NVM Express TCP/RDMA transport
  specifications and Linux NVMe documentation.
- Added `distributed/fundamentals/crdts.md` using CRDT.tech, the CRDT papers
  bibliography, the original CRDT literature, and Ink & Switch local-first and
  Peritext research.
- Added `backend/patterns/cdc-outbox.md` using current Debezium connector,
  Outbox Event Router, PostgreSQL logical decoding, and Microservices.io
  transaction-log-tailing documentation.
- Added Summary links, cross-reference edges, backlog completion markers, and
  coverage updates for all three topics.

## 2026-08-12 — Research: ABA and safe memory reclamation

- Added `src/concurrency/aba-problem.md` covering ABA interleavings, tagged
  pointers, hazard pointers, epoch-based reclamation, RCU, reference counting,
  memory ordering, implementation choices, and interview questions.
- Cross-linked the chapter to lock-free structures, the memory model, Linux
  RCU, OS memory barriers, C++, Rust/Crossbeam, and DSA hardware context.
- Researched against [Linux RCU Concepts](https://docs.kernel.org/RCU/rcu.html),
  [WG21 P2530R3](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2023/p2530r3.pdf),
  [WG21 P2545R4](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2023/p2545r4.pdf),
  the [current C++ working draft](https://eel.is/c++draft/thread#saferecl),
  IBM's hazard-pointer paper, Boost.Lockfree, Folly Hazptr, and Crossbeam Epoch.

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

## 2026-08-15 — Massive advanced topics expansion (1,500+ topics across 20 sections)

Two commits pushed to `origin/dev`:

1. `docs: add 1,500+ advanced topics across 20 sections (A-T)` (`fa3dc05`) —
   131 new markdown files across 20 directories covering topics 1-1500 from
   the master specification. ~249K words total. Sections: Advanced OS,
   Linux Kernel, Distributed Systems, Distributed Storage, Advanced DBs,
   Advanced Algorithms, PL/Compilers, Computer Architecture, HPC,
   Networking Research, Formal Methods, Security Research, Blockchain,
   AI Systems, AI+Distributed, Cloud/Serverless, Edge/IoT, Quantum
   Computing, Supply Chain/Build Systems, Observability.
2. `fix: resolve all validation errors and add gap content` (`3c41f0b`) —
   Added Build-It-Yourself track (34 implementation projects across 5 domains),
   Advanced Benchmarking section (methodology, pitfalls, statistics, tools,
   flame graphs), fixed 3 missing topics (hugetlbfs, TCP autotuning, zk-rollups),
   fixed 3 missing SUMMARY entries, 11 broken links, 13 mermaid errors, 3
   legacy MathJax delimiters, 6 unclosed code fences, 26 single-backslash
   delimiters.

### Validation after expansion

- Link checker: **0 broken links**
- SUMMARY checker: **OK** (2,117 content files, all reachable at that snapshot; now 2,809)
- Mermaid heuristic: **4,883 / 4,883 passed (100%)** — 478 new diagrams (now 4,889 / 4,889)
- MathJax: **OK** (0 legacy delimiters, 0 unclosed fences, 0 unbalanced)

Every commit was preceded by a clean validation run. `main` unchanged;
all work on `dev`.

## 2026-08-15 — OpenClaw expansion batch

Five focused commits pushed to `origin/dev`:

1. `docs(index): add master topic index as authoritative roadmap` —
   `src/index.md` (1 660 lines, 50 topic sections) added; wired into
   `SUMMARY.md` top nav and Meta section.
2. `docs(java): expand virtual-threads page with depth` —
   `src/languages/java/virtual-threads.md` 139 → 261 lines. JEP timeline,
   continuation-on-heap internals, structured-concurrency API churn,
   migration playbook, comparison vs goroutines / Kotlin coroutines /
   Reactor.
3. `docs(python): expand free-threaded page with depth` —
   `src/languages/python/free-threaded.md` 148 → 235 lines. PEP 779,
   biased-locking internals, immortal objects, Py_BEGIN_CRITICAL_SECTION,
   Cython freethreading directive, runtime introspection, comparison vs
   Java Loom / Go / Ruby Ractor.
4. `docs(storage): expand Ceph CRUSH/RADOS deep dive` —
   `src/storage/ceph-crush.md` 181 → 340 lines. Straw2 algorithm,
   CRUSH rules, upmap balancer, PG peering state machine, Bluestore
   internals, replication vs EC table, upper-layer services.
5. `docs(cs-theory): add formal methods page` — new
   `src/cs-theory/formal-methods.md` (282 lines). TLA+, Alloy, Coq,
   Lean, Isabelle/HOL, Dafny, model checking, symbolic execution,
   abstract interpretation, distributed-systems verification, 8
   interview questions.

Every commit was preceded by a clean `mdbook build`; no warnings
introduced. `token.txt` is in `.gitignore` and was never staged.
