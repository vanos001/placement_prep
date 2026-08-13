# Chunk O Audit — READMEs and Short Files

**Scope:** All README.md, overview.md, and meta files across src/ (skipping already-fixed)
**Files audited:** 121 deeply read + structural grep across all 138 READMEs
**Files clean:** ~85 (no findings)
**Total findings:** 36 (6 HIGH / 19 MEDIUM / 11 LOW, plus 1 systemic structural issue across 32 READMEs)

Methodology: Deep-read each file in scope; verify internal links against the filesystem;
verify technical claims with web search where possible; cross-reference counts and dates
between meta files; flag duplicate "Cross-References" + "Cross References" section pairs
(via ripgrep).

## Findings

### HIGH severity

#### O-H1 · `meta/cross-reference-graph.md:25` — Bash code fence has wrong line continuation

**Wrong text:**
```bash
python3 scripts/generate-cross-reference-graph.py \\
  --output book/meta/cross-reference-graph-view.html
```

**Problem:** Verified via `od -c` that the file contains two literal backslash characters
(`\\`) at end of line. In bash, `\\` is an escaped backslash (literal `\`), NOT a line
continuation. The next line `--output book/meta/...` would therefore be executed as a
separate command, which would fail.

**Correct text:** Replace `\\` with a single `\`:
```bash
python3 scripts/generate-cross-reference-graph.py \
  --output book/meta/cross-reference-graph-view.html
```

**Verification:** `awk 'NR>=24 && NR<=30' meta/cross-reference-graph.md | od -c | head`
shows `\\` (two backslash bytes) at end of the python3 line.

---

#### O-H2 · `dbms/normalization/README.md:194` — Corrupted Unicode character in answer text

**Wrong text:** `If (R1 ∩ R2) → R1 or (R1 ∩ R� R2) → R2 (checked against the original FDs), the decomposition is lossless.`

**Problem:** The string `R�` contains a Unicode replacement character (U+FFFD) — visible
as `�`. Verified via `rg "R�"` returning only this match in the entire src/ tree. The
intended text was clearly `(R1 ∩ R2)`.

**Correct text:** `If (R1 ∩ R2) → R1 or (R1 ∩ R2) → R2 (checked against the original FDs), the decomposition is lossless.`

**Verification:** `rg -n "R�" dbms/normalization/README.md` → matches line 194 only.

---

#### O-H3 · `meta/changelog.md:27-29` — Stray descriptive text orphaned in middle of file

**Wrong text:**
```
## 2026-08-13 — Pull and topic-completeness audit
... (entries) ...

[blank line 27]
This file records meaningful content and validation changes to the placement
preparation book. Dates use the project timezone, Asia/Calcutta.
[blank line]

## 2026-08-13 — Massive content expansion (parallel agents)
```

**Problem:** The description text ("This file records meaningful content and validation
changes...") appears between two `##` section headings with no heading of its own. It
looks like it was originally meant to be at the top of the file as a description and got
displaced during edits. This is broken Markdown structure.

**Correct text:** Move the description to immediately under the `# Changelog` H1 at the
top of the file, or delete it (it duplicates the purpose of the changelog itself).

---

#### O-H4 · `meta/status.md:15-16` vs `meta/coverage_dashboard.md:42` vs `meta/progress.md:80` — Inconsistent file counts

**Wrong claims:**
- `meta/status.md:15` — "1,726 content Markdown pages plus `SUMMARY.md`" (i.e., 1,727 total)
- `meta/status.md:16` — "1,726 of 1,726 content pages are reachable from `SUMMARY.md`"
- `meta/coverage_dashboard.md:42` — "Total markdown files: 1,724 (1,723 content pages plus SUMMARY)"
- `meta/progress.md:80` — "Markdown files under `src/`: **1,724**"

**Actual count (verified):** `find src -name "*.md" -type f | wc -l` = **1,742** files
(1,741 content + 1 SUMMARY).

**Problem:** All three meta files disagree with each other AND with reality. status.md
overstates by 16, the others understate by 18. Since these are tracking files, they
should agree and be re-derived automatically.

**Correct text:** All three should be regenerated from the same source of truth (e.g., a
common count produced by the validation script) and read "1,742 markdown files (1,741
content pages + SUMMARY)" (or whatever the current count is when the fix is applied).

**Verification:** `find src -name '*.md' -type f | wc -l` returns 1742; `find src -name
'*.md' -type f -not -name 'SUMMARY.md' | wc -l` returns 1741.

---

#### O-H5 · `interview/behavioral/README.md:113-131` — Table claims 16 Amazon LPs but lists only 14

**Wrong text:** The section header (line 113) says "Amazon's behavioral interviews are
entirely structured around their 16 Leadership Principles" but the table (lines 116-131)
lists only 14 LPs.

**Problem:** Amazon added two new Leadership Principles in July 2021:
- "Strive to be Earth's Best Employer"
- "Success and Scale Bring Broad Responsibility"

These are missing from the table.

**Verification:** Web search confirms — `aboutamazon.com/news/company-news/two-new-leadership-principles`
(Jul 1, 2021) and `amazon.jobs/content/en/our-workplace/leadership-principles` both list
all 16 LPs including the two new ones.

**Correct text:** Add the two missing rows to the table:
```
| **Strive to be Earth's Best Employer** | "Describe a time you invested in your team's growth or safety" |
| **Success and Scale Bring Broad Responsibility** | "Tell me about a time your work had impact beyond your immediate team" |
```

---

#### O-H6 · `dbms/indexing/README.md:310` — Wrong link description

**Wrong text:** `[Query Optimization](../transactions/isolation-levels.md) — How optimizer uses indexes`

**Problem:** Link text says "Query Optimization" but the target file is
`dbms/transactions/isolation-levels.md` (about isolation levels, not query optimization).
Either the link text is wrong (should be "Isolation Levels") or the link target is wrong
(should point to `dbms/query-processing/optimization.md`).

**Correct text (option A — fix link text):**
`[Isolation Levels](../transactions/isolation-levels.md) — How isolation affects index usage`

**Correct text (option b — fix link target):**
`[Query Optimization](../query-processing/optimization.md) — How optimizer uses indexes`

**Verification:** `ls dbms/transactions/isolation-levels.md` exists; `ls
dbms/query-processing/optimization.md` also exists.

---

### MEDIUM / LOW severity

#### O-M1 · `os/scheduling/README.md:132, 215, 303` — CFS called "Linux default" but EEVDF replaced CFS in kernel 6.6

**Wrong text (line 132):** `[CFS](./linux-cfs.md) | Preemptive | No | Linux default | O(log n) | Linux default`
**Wrong text (line 215):** `Desktop | CFS (Linux), MLFQ (Windows) | Interactive > Background`
**Wrong text (line 303):** `Linux uses CFS (Completely Fair Scheduler) for normal processes.`

**Problem:** Linux 6.6 (released October 2023) replaced CFS with the EEVDF scheduler as
the default. The file `linux/kernel/overview.md:158` correctly notes "EEVDF scheduler
introduced in kernel 6.6 as the successor to CFS" — so the docs are internally
inconsistent.

**Correct text:** Mention "CFS (kernel < 6.6) / EEVDF (kernel 6.6+)" or simply
"CFS/EEVDF" as the linux/kernel overview does.

---

#### O-M2 · `glossary.md:39` — CFS called "Linux default process scheduler"

**Wrong text:** `| **CFS** | Completely Fair Scheduler — Linux default process scheduler |`

**Problem:** Same as O-M1. Linux 6.6+ uses EEVDF, not CFS.

**Correct text:** `| **CFS** | Completely Fair Scheduler — Linux process scheduler (replaced by EEVDF in kernel 6.6+, Oct 2023) |`

---

#### O-M3 · `meta/coverage_dashboard.md:23` — Linux Deep Dive page count inconsistent with changelog

**Wrong text:** `Linux Deep Dive (\`lb2\`) | 446 | — | 1,531 | Integrated`

**Problem:** `meta/changelog.md:24` says "444 educational Markdown files and 1,530
Mermaid blocks reviewed". `meta/progress.md:26` says "Integrated the Linux book ...
Completed under `src/linux/`". `meta/topic_backlog.md:21` says "integrated 444
educational pages". Only `coverage_dashboard.md` says 446.

**Correct text:** Should be 444 (matching the other two meta files), unless 2 README/overview pages were added later — in which case all meta files should be updated to reflect the same count.

---

#### O-M4 · `meta/topic_backlog.md:113-115` — Outdated planning guidance

**Wrong text:** `Storage (45%) and Concurrency (48%) still lowest → prioritize WAL, LSM
compaction (done), next SSTable, BlobDB, RCU (done), memory barriers, work-stealing.
After storage/concurrency reaches 60%, move to Frameworks (60%) and Distributed (55%)
and Cloud (60%)`

**Problem:** `coverage_dashboard.md` shows Storage at 60% and Concurrency at 58% — both
have already reached or exceeded the 60% target. The "next" items (SSTable, BlobDB, RCU,
work-stealing) are all marked "Done" later in the same topic_backlog file. This is stale
planning text that should be updated or moved to a "historical" section.

---

#### O-M5 · `meta/topic_backlog.md:91` — Ceph CRUSH/RADOS marked "still TODO" but file exists

**Wrong text:** `**Storage: Ceph CRUSH/RADOS Deep Dive** — CRUSH algorithm, placement groups, RADOS (still TODO)`

**Problem:** `storage/ceph.md` exists (verified). The topic is not "still TODO" — at
most, the existing ceph.md may not cover CRUSH/RADOS in depth, but the file is present.

**Correct text:** Update to reflect that `storage/ceph.md` exists; if CRUSH/RADOS coverage
is thin, say "expand `storage/ceph.md` with CRUSH/RADOS deep dive" rather than "still TODO".

---

#### O-M6 · `meta/coverage_dashboard.md:184-232` — "Priority Gaps Remaining" section is stale

**Problem:** Section header says "Updated 2026-08-12" but lists items like "Python GIL
3.13 free-threaded deep dive (`languages/python/free-threaded.md`)" and "Java Loom
Virtual Threads (`languages/java/virtual-threads.md`)" as "Remaining MEDIUM (Next Loop)"
without indicating completion. The same section also marks many items as "✅" completed
inconsistently.

**Correct text:** Either update the "Remaining MEDIUM" sub-section to remove completed
items, or convert the whole section to "Completed in 2026-08-12 batch" with a fresh
"Remaining" list.

---

#### O-M7 · `search/README.md` — Missing 2 of 5 content files in chapter listing

**Wrong text:** README lists only `[Elasticsearch](./elasticsearch.md)` and
`[Interview Questions](./interview-questions.md)`.

**Problem:** Directory has 5 content files: `elasticsearch.md`, `fundamentals.md`,
`vector-search.md`, `interview-questions.md`, plus README. README does not mention
`fundamentals.md` or `vector-search.md`.

**Verification:** `ls search/*.md` confirms 5 files.

**Correct text:** Add rows for `./fundamentals.md` (inverted index, TF-IDF, BM25) and
`./vector-search.md` (embeddings, HNSW, ANN).

---

#### O-M8 · `data-engineering/README.md` — Missing 2 of 6 content files in chapter listing

**Wrong text:** README lists 4 chapters: `fundamentals.md`, `batch-processing.md`,
`stream-processing.md`, `interview-questions.md`.

**Problem:** Directory has 7 files (6 content + README). Missing: `data-formats.md`
(Parquet/Avro/ORC) and `data-quality.md`.

**Verification:** `ls data-engineering/*.md` confirms 7 files.

---

#### O-M9 · `placement-preparation/README.md` — Missing 2 of 5 content files in chapter listing

**Wrong text:** README lists 3 chapters: `campus-placement.md`, `online-assessment.md`,
`hr-interview.md`.

**Problem:** Directory has 6 files (5 content + README). Missing: `group-discussion.md`
and `technical-interview.md`.

**Verification:** `ls placement-preparation/*.md` confirms 6 files.

---

#### O-M10 · `dbms/interview-problems/README.md` — Missing 3 of 5 content files in chapter listing

**Wrong text:** README lists 2 chapters: `classic-problems.md`, `optimization-problems.md`.

**Problem:** Directory has 6 files (5 content + README). Missing: `concurrency-scenarios.md`,
`join-problems.md`, `window-function-problems.md`.

**Verification:** `ls dbms/interview-problems/*.md` confirms 6 files.

---

#### O-M11 · `dbms/postgresql/README.md:18-19` — Lists "stats collector" as current background worker

**Wrong text:** Architecture diagram includes `└── stats collector` as one of the
"Background Workers".

**Problem:** PostgreSQL 15 (released October 2022) removed the stats collector process
and replaced it with in-memory shared statistics. This README's claim is outdated for
PostgreSQL 15+ (which is now the oldest supported version as of 2024).

**Verification:** Web search confirms — Percona blog (Aug 26, 2022): "Yes, the 'stats
collector' is missing, and it is gone for good" (referring to PG 15). PostgreSQL docs
confirm shared-memory cumulative statistics subsystem.

**Correct text:** Replace `stats collector` with `stats (shared memory, since PG 15)` or
note "pre-PG 15: stats collector process; PG 15+: in-memory shared stats".

---

#### O-M12 · `distributed/consensus/README.md:41, 45` — Mermaid edge labels use non-standard `#quot;`

**Wrong text:**
```
A1 -->|"Promise(#quot;n, prev_accepted#quot;)"| P1
P1 -->|"Accept(#quot;n, value#quot;)"| A1
```

**Problem:** The `#quot;` sequence is non-standard. Mermaid documentation recommends
either `&quot;` (HTML entity) or wrapping the entire label in double quotes. The
validator passes these (per changelog "Mermaid v11 parser 4,405/4,405 passed"), but the
rendering may show literal `#quot;` text instead of `"` in some Mermaid versions.

**Correct text:** Use `&quot;` or just remove the inner quotes:
```
A1 -->|"Promise(n, prev_accepted)"| P1
```

**Note:** This pattern (`#quot;`) also appears in many content files (paxos.md,
rabbitmq.md, etc.) — see Other notes below.

---

#### O-M13 · `linux/kernel/overview.md:558` — Outdated claim about odd/even versioning

**Wrong text:** `Odd minor numbers (e.g., 5.17-rc1) denote development kernels.`

**Problem:** The Linux kernel ended the odd/even versioning convention with the 2.6.0
release in December 2003. Modern Linux uses `-rc1`, `-rc2`, etc. tags for development
kernels; all mainline kernel releases are considered stable. This claim has been
incorrect for over 20 years.

**Verification:** Web search — Greg Kroah-Hartman's blog (Dec 9, 2025): "Once the 2.6.0
kernel was released, it was decided that the rule of kernel releases would be that every
release would be 'stable'." Also linux.com (Jun 11, 2005): "odd-numbered kernels are the
unstable series... even-numbered kernels are the stable branch" — describing the
historical (pre-2.6) convention.

**Correct text:** Either delete the sentence or replace with: "Before kernel 2.6 (2003),
odd minor versions denoted development kernels; this convention was abandoned with 2.6.0.
Modern kernels use -rcN tags for release candidates."

---

#### O-M14 · `linux/security/overview.md:226` — Misleading "starting with Linux 5.4+" for LSM stacking

**Wrong text:** `Only one **major LSM** can be active at a time (SELinux, AppArmor,
SMACK, or TOMOYO), but **minor LSMs** (Yama, LoadPin, Lockdown) can stack with a major
LSM starting with Linux 5.4+.`

**Problem:** LSM stacking (the ability for minor LSMs to stack with a major one) has
been supported since the LSM framework was introduced in Linux 2.6 (2003). The "5.4"
reference conflates the introduction of the Lockdown LSM (which was indeed merged in
5.4) with general stacking support. Yama has been around since 3.4 and LoadPin since
4.7 — both stackable.

**Verification:** LWN article (lwn.net/Articles/804906): "The idea of stacking (or
chaining) Linux security modules (LSMs) goes back 15 years (at least)." The SUSE docs
and kernel.org references confirm Lockdown was added in 5.4.

**Correct text:** `Only one **major LSM** can be active at a time (SELinux, AppArmor,
SMACK, or TOMOYO), but **minor LSMs** (Yama since 3.4, LoadPin since 4.7, Lockdown since
5.4) can stack with a major LSM.`

---

#### O-M15 · `linux/embedded/overview.md:35` — eMMC storage size range is wrong

**Wrong text:** `Storage | SSD/HDD, 100s GB | eMMC, NAND, 4-32 MB`

**Problem:** Modern eMMC storage is typically 4 GB to 128 GB+ (used in phones, tablets,
RPi). The "4-32 MB" range applies only to raw NOR/SPI flash, not eMMC. Conflating eMMC
with NAND under a single "4-32 MB" size is misleading.

**Correct text:** Either split into separate rows or clarify: `Storage | SSD/HDD, 100s
GB | eMMC 4-128 GB; raw NOR/SPI flash 4-32 MB; NAND 128 MB - 1 GB`.

---

#### O-M16 · `meta/coverage_dashboard.md:162` — Out-of-place "bluetooth + congestion-control README added" line in Batch 5

**Wrong text (Batch 5 section, line 162):** `**Meta fixes**: 14 mermaid regressions
after dev merge fixed (unquoted labels () {} |, Note over → NODE_FIX), 16 broken links
fixed, bluetooth + congestion-control README added`

**Problem:** This appears under "Batch 5 — Concurrency Advanced & BlobDB (3 files) —
Latest" but mentions "bluetooth + congestion-control README added", which has nothing to
do with Batch 5 (concurrency/storage). This looks like leftover text from another batch
that was pasted in the wrong section.

**Correct text:** Move the "bluetooth + congestion-control README added" mention to the
appropriate batch entry (likely the integration batch where these READMEs were actually
added).

---

#### O-L1 · `interview/system-design/lld/README.md:180-191` — Orphaned bullets after horizontal rule

**Wrong text:** Lines 180-186 contain the "Cross-References" heading with 4 bullet
items; line 187 is `---`; line 188 is blank; line 189 is an italic note; lines 190-191
contain two bullet items (`- [System Design Framework](../framework.md)` and `- [HLD
Overview](../hld/README.md)`) without a heading.

**Problem:** The bullets on lines 190-191 are orphaned — they appear after a horizontal
rule and italic note, with no `##` heading to introduce them. They look like leftovers.

**Correct text:** Either move lines 190-191 up into the "Cross-References" section, or
add a heading like `## Next Steps` above them.

---

#### O-L2 · `ml/overview.md:130` and `llm/llm-serving/README.md:135` — Misleading "Cloud GPU" link text

**Wrong text:** `[Cloud GPU](../cloud/virtualization/README.md)`

**Problem:** Link text says "Cloud GPU" but the target file is
`cloud/virtualization/README.md` — which is about virtualization broadly (VMs,
hypervisors, containers), not GPU-specific content.

**Correct text:** Either change link text to "Cloud Virtualization" or create a
GPU-specific page and link to that.

---

#### O-L3 · `llm/vision/README.md:121` — Misleading "Neural Networks" link text

**Wrong text:** `[Neural Networks](../../ml/transformers/README.md)`

**Problem:** Link text says "Neural Networks" but the target is `ml/transformers/README.md`
— which is about transformers specifically, not general neural networks. The very next
line has `[Transformers](../../ml/transformers/README.md)` pointing to the same file,
making the first link redundant and misleading.

**Correct text:** Either remove the "Neural Networks" link, or change it to point to a
general neural-networks page (e.g., `ml/deep-learning/README.md` if it covers NN
fundamentals).

---

#### O-L4 · `interview/coding/README.md:52` — Odd date range "2024-2026"

**Wrong text:** `Based on analysis of recent FAANG interviews (2024-2026):`

**Problem:** The file was created 2026-08-13. The range "2024-2026" is unusual — 2026 is
the current year and not yet complete. Reads as if it includes future data.

**Correct text:** Either "Based on analysis of recent FAANG interviews (2024-2025)" or
"(2024 through mid-2026)".

---

#### O-L5 · `meta/knowledge_graph.md:5` — "Last updated" date inconsistent with other meta files

**Wrong text:** `> Last updated: 2026-08-12`

**Problem:** Other meta files (`status.md`, `coverage_dashboard.md`, `topic_backlog.md`)
say "Last updated: 2026-08-13". The knowledge_graph.md file actually contains content
from 2026-08-13 batches (e.g., the "Git ↔ Other Topics" section in lines 382+) but the
header date says 2026-08-12.

**Correct text:** Update to `> Last updated: 2026-08-13`.

---

#### O-L6 · `meta/topic_backlog.md:170` — Stale "1,544 Markdown files" count

**Wrong text:** `Navigation: 1,544 Markdown files are present and 1,543 are linked from
SUMMARY.md (the Summary file is the only excluded Markdown file).`

**Problem:** This is in the "Integration Batch — 2026-08-12" section, so it may be
intentionally historical. However, it's presented without "historical:" prefix and
contradicts the current counts in coverage_dashboard.md. A reader could be confused.

**Correct text:** Either prepend "Historical (2026-08-12 snapshot):" or update to
current count.

---

#### O-L7 · `meta/topic_backlog.md:46` — Inconsistent storage coverage claim

**Wrong text:** `Storage: HDD/SSD/NVMe/object/block/file/distributed/Ceph/erasure-coding
(10 files) → 12 files with **WAL** + **LSM Compaction** + Bluetooth fix, still low
coverage (45%)`

**Problem:** Sentence is hard to parse — "10 files → 12 files" but the list of added
items (WAL, LSM Compaction, Bluetooth fix) is 3 items, which would make 13. Also, the
"Bluetooth fix" mention is odd in a Storage context.

---

### Systemic structural issue (32 files)

#### O-S1 · 32 README files have duplicate "Cross-References" + "Cross References" sections

**Pattern:** File ends with two near-identical sections:
```
## Cross-References
- [Link 1](target1.md) — description
- [Link 2](target2.md) — description

## Files confirmed clean (sample)

The following deeply-audited files had no findings:

- `introduction.md`, `glossary.md` (glossary has minor CFS staleness — see O-M2)
- `dsa/README.md`, `os/overview.md`, `networks/overview.md`, `dbms/overview.md`,
  `arch/overview.md`, `distributed/overview.md`, `cloud/overview.md`,
  `storage/overview.md`, `ml/overview.md`, `concurrency/overview.md`,
  `interview/overview.md`
- `git/README.md`, `software-engineering/README.md`,
  `programming-fundamentals/README.md`, `web-development/README.md`,
  `frontend/README.md`, `mathematics/README.md`, `cs-theory/README.md`,
  `anti-patterns/README.md`, `failure-modes/README.md`, `oop-patterns/README.md`,
  `behavioral-interviews/README.md`, `communication/README.md`,
  `practical-problems/README.md`, `aptitude/README.md`, `resume/README.md`,
  `machine-coding/README.md`, `security/README.md`, `web-servers/README.md`,
  `redis/README.md`, `iac/README.md`, `production-engineering/README.md`
- `interview/{behavioral,companies,coding,system-design,system-design/hld}/README.md`
- `cloud/{aws,kubernetes,observability,security,cicd,virtualization}/README.md`
- `distributed/{consensus,fundamentals,microservices,partitioning,mapreduce,replication,messaging}/README.md`
  (messaging, microservices, partitioning, mapreduce, replication have the duplicate-sections issue O-S1)
- `backend/README.md`, `backend/api/README.md`, `backend/containers/README.md`
- `languages/{cpp,rust,go,python,java}/README.md`
- `dbms/{internals,transactions,sql,relational-model,storage,query-processing,nosql,distributed,caching,analytics}/README.md`
  (most have the duplicate-sections issue O-S1)
- `dbms/postgresql/README.md` (has the stats collector issue O-M11)
- `os/{kernel,scheduling,processes,threads,io,memory,virtual-memory,synchronization,synchronization/deadlocks,filesystems,boot,containers,security}/README.md`
  (scheduling has the CFS/EEVDF issue O-M1; filesystems, boot, containers, security have the duplicate-sections issue O-S1)
- `linux/README.md` and most `linux/*/overview.md` files
- `llm/{llm-serving,moe,multimodal,sota,vision}/README.md`
- `ml/{llm,transformers,foundations}/README.md`
- `frameworks/spring-boot/README.md`

## Other notes (not flagged as findings)

- The `#quot;` Mermaid pattern (O-M12) also appears in non-README content files
  (paxos.md, rabbitmq.md, distributed.md, object-storage.md, memcached.md,
  cgroups-v2.md, consistency.md, distributed-lock.md). These are outside this chunk's
  scope but should be reviewed in a future audit.
- Many READMEs in `arch/`, `networks/`, `ml/`, `frameworks/` subdirectories were
  previously audited in chunks E, F, G, H, I, L; this audit focused on issues not
  previously caught.
- File counts in meta files (O-H4) are all understated relative to the actual 1,742 files
  on disk — likely because the meta files were last updated when the repo had fewer files.
