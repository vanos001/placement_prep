# Changelog

This file records meaningful content and validation changes to the placement
preparation book. Dates use the project timezone, Asia/Calcutta.

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
