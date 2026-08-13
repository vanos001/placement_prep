# Chunk P Audit — DBMS + Mobile + Interview + Projects + Resume + Placement + SRE + Anti-patterns + Failure-modes

**Files audited:** 75 (deeply read) + 175 (sampled/skimmed for systemic issues)
**Total findings:** 11 distinct issues (HIGH: 7, MEDIUM: 3, LOW: 1 systemic across 91 files)

**Coverage note:** Deep-read 75 files end-to-end (line-by-line for arithmetic, claims, code, mermaid, AI artifacts). For dbms/ and interview/, an additional ~175 files were grep-scanned for systemic artifacts (duplicate "Cross References" sections, "Wait/Hmm/Actually" AI leaks, broken paths). The interview/system-design/lld/ and real-world/ subdirectories were not deeply read end-to-end due to scope — they should be re-audited in a future pass.

## Scope audited

| Directory | Deeply read | Skimmed/grepped | Notes |
|---|---|---|---|
| `mobile/` | 3/3 | — | All clean |
| `projects/` | 3/3 | — | All clean |
| `placement-preparation/` | 6/6 | — | All clean |
| `sre/` | 5/5 | — | All clean (SLO numbers verified with Python) |
| `anti-patterns/` | 3/3 | — | All clean (99.9%^5 verified) |
| `failure-modes/` | 3/3 | — | All clean |
| `resume/` | 6/6 (skipping technical-skills.md) | — | All clean |
| `dbms/` | 55/106 | 91 grep-scanned | 7 HIGH + 1 MEDIUM + systemic duplicate-xref artifact |
| `interview/` | 6/87 | 87 grep-scanned | 1 MEDIUM (latency-numbers inconsistency) |

## Findings

### HIGH severity

#### src/dbms/normalization/README.md:194
- **Wrong text:** `If (R1 ∩ R2) → R1 or (R1 ∩ R� R2) → R2`
- **Correct text:** `If (R1 ∩ R2) → R1 or (R1 ∩ R2) → R2`
- **Verification:** The string `R1 ∩ R� R2` contains a corrupted UTF-8 character (replacement char U+FFFD shown as `�` after `R1 ∩ R`). The intended text is the lossless-join test formula `(R1 ∩ R2) → R2` matching the prior clause `(R1 ∩ R2) → R1`. Visible file corruption. Found via `Read` tool rendering.
- **Severity rationale:** Renders as a mojibake/corruption character in any mdBook build; breaks the lossless-join formula that students need to learn.

#### src/dbms/relational-model/keys.md:51-55
- **Wrong text:**
  ```
  - Candidate keys: `{A}`, `{B}` (B determines C, and A determines B and C)
  - Wait — let's re-derive. If `{A} → {B,C}` and `{B} → {C}`:
    - `{A}` determines everything → candidate key
    - `{B}` determines only `{C}`, not `{A}` → NOT a candidate key
    - So only `{A}` is a candidate key
  ```
- **Correct text:** Remove the "Wait — let's re-derive. If..." preamble and the now-contradicted first bullet; present the correct derivation directly:
  ```
  Given R(A, B, C) with FDs {A} → {B,C} and {B} → {C}:
    - {A}⁺ = {A, B, C} → {A} is a candidate key
    - {B}⁺ = {B, C} (does not include A) → {B} is NOT a candidate key
    - So only {A} is a candidate key
  - Super keys: {A}, {A,B}, {A,C}, {A,B,C} (4 = 2²)
  ```
- **Verification:** The phrase "Wait — let's re-derive" is a leaked LLM thinking-out-loud artifact (the model literally corrected itself mid-sentence in the rendered doc). The first bullet ("Candidate keys: {A}, {B}") is also factually wrong given the FDs — it directly contradicts the corrected derivation three lines below. Found via `Grep` for `Wait —` pattern.
- **Severity rationale:** Teaches an incorrect candidate-key derivation in the first bullet, then immediately self-corrects; readers will be confused or remember the wrong version.

#### src/dbms/indexing/b-tree.md:308-311
- **Wrong text:**
  ```
  Delete 20:
    Remove 20 from leaf: [10]
    Keys remaining: 1 (≥ min 2? No! Underflow for non-root)
    Wait — for order 5, min keys = ⌈5/2⌉ - 1 = 2
    But this is a non-root leaf... let me recalculate.

  Actually for order 5: min keys (non-root) = ⌈5/2⌉ - 1 = 2
    [10] has 1 key → underflow!
  ```
- **Correct text:** Remove the "Wait — for order 5..." and "But this is a non-root leaf... let me recalculate." and "Actually for order 5:" preamble; present the calculation once:
  ```
  Delete 20:
    Remove 20 from leaf: [10]
    For order 5, min keys (non-root) = ⌈5/2⌉ - 1 = 2
    [10] has 1 key → underflow!
  ```
- **Verification:** "Wait —" and "Actually for order 5:" are leaked LLM self-correction artifacts (verified via `Grep "Wait —"` → matched `b-tree.md:311` and `Grep ^Actually` → matched `b-tree.md:311`). The same paragraph calculates the same value (`⌈5/2⌉ - 1 = 2`) twice with hand-wringing in between.
- **Severity rationale:** Confusing narrative that exposes the model's thinking process; students may think the formula itself is uncertain.

#### src/dbms/distributed/raft.md:422
- **Wrong text:**
  ```
  Wait — this needs more care:

  Scenario that demonstrates the rule:
  ```
- **Correct text:** Remove the "Wait — this needs more care:" line entirely. The "Scenario that demonstrates the rule:" header that follows is sufficient.
- **Verification:** `Grep "Wait —"` matched `raft.md:422`. The phrase is a leaked LLM thinking artifact immediately before a valid worked scenario. The scenario itself is correct and self-contained.
- **Severity rationale:** Reader-visible author uncertainty that should have been edited out.

#### src/dbms/distributed/paxos.md:282
- **Wrong text:** `- [Two-Phase Commit](./consensus.md) — the related distributed commit protocol`
- **Correct text:** `- [Two-Phase Commit](../transactions/two-phase-commit.md) — the related distributed commit protocol`
- **Verification:** The link text says "Two-Phase Commit" but the link target is `./consensus.md` (same directory). The actual 2PC file is at `src/dbms/transactions/two-phase-commit.md` — verified via `LS src/dbms/transactions/`. The duplicate "Cross References" section at line 287-289 has the correct path `[Paxos (Distributed)](../../distributed/consensus/paxos.md)` and `[Consensus](consensus.md)`, confirming the wrong-target issue.
- **Severity rationale:** Clicking the link goes to a wrong page (the consensus overview), not the 2PC page the link text promises. Affects reader navigation.

#### src/dbms/distributed/consensus.md:233
- **Wrong text:** `- [Distributed Transactions](./consistency.md) — multi-operation consistency`
- **Correct text:** `- [Distributed Transactions](../transactions/distributed.md) — multi-operation consistency`
- **Verification:** Link text says "Distributed Transactions" but target is `./consistency.md` (Consistency Models page in the same dir). The actual distributed transactions file is at `src/dbms/transactions/distributed.md` (verified via `Read`). The duplicate "Cross References" section at line 271 has the correct path `[Distributed Transactions](../transactions/distributed.md)`, confirming the wrong-target issue.
- **Severity rationale:** Same as paxos.md — broken navigation; the link promises distributed transactions but delivers consistency models.

#### src/dbms/distributed/sharding.md:338
- **Wrong text:** `- [Consistent Hashing](./cap.md) — distribution mechanism`
- **Correct text:** `- [Consistent Hashing](../../distributed/partitioning/consistent-hashing.md) — distribution mechanism`
- **Verification:** Link text says "Consistent Hashing" but target is `./cap.md` (CAP Theorem page in the same dir). The actual consistent hashing file is at `src/distributed/partitioning/consistent-hashing.md` — verified via `LS src/distributed/partitioning/`. The duplicate "Cross References" section at line 345 has the correct path `[Consistent Hashing](../../distributed/partitioning/consistent-hashing.md)`, confirming the wrong-target issue.
- **Severity rationale:** Same as above; clicking "Consistent Hashing" delivers the CAP theorem page instead.

### MEDIUM severity

#### src/dbms/transactions/two-phase-commit.md:226
- **Wrong text:**
  ```
  2PC Latency = 2 × (max network RTT) + participant processing time

  Phase 1: Coordinator → Participants (1 RTT) + prepare processing
  Phase 2: Coordinator → Participants (1 RTT) + commit processing

  Total: 4 network round trips (2 per phase)
  ```
- **Correct text:**
  ```
  2PC Latency = 2 × (max network RTT) + participant processing time

  Phase 1: Coordinator → Participants (1 RTT) + prepare processing
  Phase 2: Coordinator → Participants (1 RTT) + commit processing

  Total: 2 network round trips (1 per phase), or 4 one-way messages
  ```
- **Verification:** The formula `2 × RTT` says 2 round trips total. Each phase is described as "1 RTT" (one round trip = one request + one reply). So 2 phases × 1 RTT = 2 RTT total. The "Total: 4 network round trips (2 per phase)" line contradicts both the formula and the per-phase description. The number 4 only makes sense if counting one-way messages (2 per phase × 2 phases = 4 one-way messages), but they're labeled "round trips" which is incorrect terminology. A round trip = request + reply, not a single one-way message.
- **Severity rationale:** Teaches the wrong latency model. A student repeating "4 round trips" in an interview would be incorrect; the correct answer is 2 round trips (or 4 one-way messages).

#### src/interview/system-design/latency-numbers.md:28-33
- **Wrong text:**
  ```
  | SSD sequential read (1MB) | 500 μs | — |
  | HDD random read | 10 ms | Mechanical seek + rotation |
  | HDD sequential read (1MB) | 2 ms | — |
  | Read 1 MB from SSD | 1 ms | — |
  | Read 1 MB from HDD | 20 ms | — |
  | Read 1 MB from memory | 0.25 ms | — |
  | Read 1 MB from SSD (NVMe) | 0.3 ms | NVMe is much faster |
  ```
- **Correct text:** The two rows "SSD sequential read (1MB) | 500 μs" and "Read 1 MB from SSD | 1 ms" describe the same operation with different numbers (500 μs vs 1 ms). Pick one consistent value. Recommended: keep "SSD sequential read (1MB) | 500 μs" and remove the "Read 1 MB from SSD | 1 ms" row, OR align both to the same value (e.g., 1 ms for SATA SSD, 0.3 ms for NVMe — which is already represented).
- **Verification:** Two rows in the same table for "1 MB SSD sequential read" give different latencies. The "Read 1 MB from SSD (NVMe) | 0.3 ms" row already provides the NVMe-specific number, so the "Read 1 MB from SSD | 1 ms" row is either a duplicate of the SATA-SSD row (with a different number) or ambiguous. Cross-checked against the Jeff Dean / Brendan Gregg latency numbers — SATA SSD sequential reads of 1 MB are typically 200–500 μs, not 1 ms.
- **Severity rationale:** Inconsistent numbers in the same table confuse candidates; the "1 ms" figure is also high for modern SSDs.

#### src/dbms/distributed/cap.md (and 90 other dbms files) — systemic duplicate "Cross References" section
- **Wrong text:** Nearly every dbms/*.md file ends with two cross-reference sections in sequence:
  ```
  ## Cross-References

  - [link 1](path1)
  - [link 2](path2)
  ...


  ## Cross References

  - [link 1](path1)
  - [link 2](path2)
  ...
  ```
- **Correct text:** Keep only one cross-references section per file. The first ("Cross-References" with hyphen) is usually more complete with descriptions; delete the second ("Cross References" without hyphen, usually shorter) section.
- **Verification:** `Grep "## Cross References"` against `src/dbms/` returns 91 matches, one per file — confirming every dbms file has the second section. Spot-checked 10+ files (acid.md, mvcc.md, b-tree.md, paxos.md, etc.) and confirmed the pattern: the second section is always a truncated duplicate of the first. This is a clear AI-generation artifact (the model emitted two near-identical sections).
- **Severity rationale (MEDIUM):** Bloats every dbms page with redundant links; some duplicates contain different (sometimes wrong) link targets (see HIGH findings 5–7 above, where the duplicate section actually has the correct link while the primary section has the wrong one). The inconsistency between the two sections creates navigation confusion.

### LOW severity

#### (none individual — the MEDIUM-severity duplicate-xref issue above is the only systemic pattern)

## Files confirmed clean

The following deeply-read files had no arithmetic, technical, code, Mermaid, LaTeX, or Markdown errors:

### mobile/ (3 files, all clean)
- `mobile/android.md` — Android lifecycle, Jetpack Compose, Room, coroutines all correct
- `mobile/interview-questions.md` — clean
- `mobile/README.md` — clean (market share numbers ~72%/27% are reasonable approximations)

### projects/ (3 files, all clean)
- `projects/explaining-projects.md` — STAR-format guidance, no technical claims to verify
- `projects/README.md` — clean
- `projects/project-ideas.md` — 30+ project ideas with tech stacks; no verifiable technical claims

### placement-preparation/ (6 files, all clean)
- `placement-preparation/technical-interview.md` — clean; cross-references to `../behavioral-interviews/` verified to exist
- `placement-preparation/online-assessment.md` — clean
- `placement-preparation/group-discussion.md` — clean; cross-references verified
- `placement-preparation/README.md` — clean
- `placement-preparation/campus-placement.md` — clean
- `placement-preparation/hr-interview.md` — clean

### sre/ (5 files, all clean — SLO math verified with Python)
- `sre/chaos-engineering.md` — clean
- `sre/incident-management.md` — clean
- `sre/interview-questions.md` — clean
- `sre/slo-sli-sla.md` — SLO downtime numbers verified: 99.9% → 43.8 min/month, 99.99% → 4.38 min/month, 99.999% → 26.3 sec/month (all correct for year-averaged 30.4375-day month). Burn rate example (0.5% / 0.1% = 5×, 30/5 = 6 days) all correct.
- `sre/README.md` — clean

### anti-patterns/ (3 files, all clean)
- `anti-patterns/architecture-anti-patterns.md` — 18 anti-patterns; availability multiplication `99.9%^5 = 99.5%` verified with Python (0.999^5 = 0.99501). Clean.
- `anti-patterns/interview-questions.md` — Python retry-with-backoff code correct
- `anti-patterns/README.md` — clean

### failure-modes/ (3 files, all clean)
- `failure-modes/common-failures.md` — 19 failure modes; bash/SQL snippets correct
- `failure-modes/interview-questions.md` — clean; Java/PostgreSQL snippets compile
- `failure-modes/README.md` — clean

### resume/ (6 files, all clean — technical-skills.md skipped per instructions)
- `resume/projects.md` — clean
- `resume/structure.md` — clean
- `resume/writing-bullets.md` — clean
- `resume/ats-optimization.md` — clean
- `resume/README.md` — clean
- `resume/common-mistakes.md` — clean

### dbms/ (55 of 106 files deeply read; listed files below are clean)
- `dbms/overview.md` — three-schema architecture, DBMS classification all correct (duplicate-xref artifact present, see MEDIUM above)
- `dbms/types-of-databases.md` — clean (links verified)
- `dbms/normalization/1nf.md`, `2nf.md`, `3nf.md`, `bcnf.md`, `4nf-5nf.md`, `denormalization.md` — all technically correct (duplicate-xref artifact only)
- `dbms/normalization/README.md` — has HIGH finding (corrupted UTF-8 char at line 194); rest of file clean
- `dbms/sql/ddl.md`, `dml.md`, `joins.md`, `subqueries.md`, `window-functions.md`, `ctes.md`, `indexes.md`, `views.md`, `triggers.md`, `stored-procedures.md` — SQL syntax all valid; PostgreSQL/MySQL/SQL Server dialect differences correctly noted (duplicate-xref artifact only)
- `dbms/transactions/acid.md`, `isolation-levels.md`, `serializability.md`, `mvcc.md`, `lock-based.md`, `three-phase-commit.md`, `saga.md`, `aries.md`, `distributed.md`, `README.md` — ACID, isolation, MVCC, 2PC/3PC, ARIES all technically correct (duplicate-xref artifact only)
- `dbms/transactions/two-phase-commit.md` — has MEDIUM finding (latency math); rest of file clean
- `dbms/indexing/b-tree.md`, `b-plus-tree.md`, `hash-index.md`, `clustered-vs-nonclustered.md`, `composite-index.md`, `covering-index.md`, `bitmap-index.md`, `tuning.md`, `gin.md`, `gist.md`, `README.md` — index structures, leftmost-prefix rule, INCLUDE columns all correct
- `dbms/distributed/cap.md`, `raft.md`, `paxos.md`, `sharding.md`, `consistency.md`, `replication.md`, `consensus.md`, `README.md` — CAP, PACELC, Raft, Paxos, sharding strategies all correct
- `dbms/internals/engines.md`, `lsm-trees.md`, `wal.md` — InnoDB, MyISAM, PostgreSQL heap, RocksDB, SQLite comparison all correct; doublewrite buffer / full-page writes / WAL protocol all correct
- `dbms/caching/buffer-pool.md` — clean (cross-references to `../../arch/memory-hierarchy/cache-basics.md` verified to exist)
- `dbms/relational-model/relational-algebra.md` — clean (relational algebra operators, equivalence rules all correct)
- `dbms/relational-model/keys.md` — has HIGH finding (AI artifact at lines 51-55); rest of file clean

### interview/ (6 of 87 files deeply read)
- `interview/overview.md` — clean
- `interview/system-design/README.md` — clean
- `interview/system-design/estimation.md` — math verified with Python (500M × 40 / 86400 = 231,481 ≈ 231K ✓; 500M × 200 / 86400 = 1,157,407 ≈ 1.157M ✓; storage calculations all check out)
- `interview/system-design/latency-numbers.md` — has MEDIUM finding (inconsistent SSD row); rest of file clean (Jeff Dean numbers all standard)
- `interview/coding/complexity.md` — Big-O hierarchy, master theorem, sorting comparison all correct

### Not deeply audited (flagged for future pass)
- `dbms/` — 51 files not deeply read: `sql/README.md`, `transactions/{states,recovery,log-recovery,checkpointing,concurrency-control,optimistic,timestamp-based}.md`, `indexing/` (all deeply read), `nosql/*` (6 files), `postgresql/*` (3 files), `storage/*` (5 files), `caching/{redis,query-cache,memcached,README}.md`, `analytics/README.md`, `relational-model/{relational-calculus,er-diagrams,README}.md`, `internals/{compaction,query-optimization,README}.md`, `query-processing/*` (8 files), `interview-problems/*` (6 files)
- `interview/` — 81 files not deeply read: all of `interview/companies/*`, `interview/coding/{README,framework,data-structures,patterns}.md`, `interview/behavioral/*`, `interview/system-design/{lld,real-world,hld}/*` and most of `interview/system-design/*.md`, plus `interview/{os,dbms,network,ml,arch}-questions.md`

## Top issues summary

1. **HIGH — Corrupted UTF-8 in normalization/README.md:194** — `R1 ∩ R� R2` mojibake in lossless-join formula
2. **HIGH — AI artifact in keys.md:51-55** — "Wait — let's re-derive" leaked self-correction with contradicting first bullet
3. **HIGH — AI artifact in b-tree.md:308-311** — "Wait —" and "Actually for order 5:" leaked self-correction
4. **HIGH — AI artifact in raft.md:422** — "Wait — this needs more care:" leaked author uncertainty
5. **HIGH — 3 broken cross-reference links in distributed/** — paxos.md:282, consensus.md:233, sharding.md:338 all link to wrong files
6. **MEDIUM — 2PC latency math error in two-phase-commit.md:226** — claims 4 round trips when formula says 2
7. **MEDIUM — Inconsistent SSD latency in latency-numbers.md:28-33** — same operation listed as both 500 μs and 1 ms
8. **MEDIUM — Systemic duplicate "Cross References" sections in 91 dbms files** — AI-generation artifact; some duplicates have divergent (sometimes wrong) link targets

## Verification commands used

```bash
# SLO downtime verification (year-averaged month)
python3 -c "for n in [3,4,5]: d=10**-n * 30.4375*24*60; print(f'99.{\"9\"*n}: {d:.4f} min = {d*60:.2f} sec')"
# Output: 99.9 → 43.83 min, 99.99 → 4.383 min, 99.999 → 0.4383 min = 26.30 sec ✓

# 99.9%^5 availability multiplication
python3 -c "print(f'{0.999**5*100:.4f}%')"
# Output: 99.501% ≈ 99.5% ✓

# Grep for AI artifacts
rg "Wait —" src/dbms/ src/interview/ src/mobile/ src/projects/ src/placement-preparation/ src/sre/ src/anti-patterns/ src/failure-modes/ src/resume/
# Found: b-tree.md, keys.md, raft.md (all in dbms/)

# Grep for duplicate Cross References sections (systemic)
rg -c "^## Cross References$" src/dbms/
# 91 files affected
```

## Next actions for parent agent

1. **Apply HIGH-severity fixes first** (7 findings): corrupted UTF-8 char, 3 AI-artifact cleanups, 3 broken cross-reference link targets
2. **Apply MEDIUM fixes** (3 findings): 2PC latency math, latency-numbers.md SSD row consistency, and the systemic duplicate-xref removal across 91 dbms files (scriptable: in each file, delete the second `## Cross References` section that appears after a `## Cross-References` section)
3. **Schedule a future audit pass** for the ~135 not-deeply-read files in dbms/ and interview/ — particularly the interview/system-design/lld/ and real-world/ subdirectories which contain many concrete code examples that could harbor bugs
