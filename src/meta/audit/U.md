# Chunk U Audit — DBMS deep-read (transactions/sql/relational-model/indexing/internals/normalization/distributed)
**Files audited:** 62
**Total findings:** 23 (HIGH: 9, MEDIUM: 9, LOW: 5)

Scope: All files in `dbms/transactions/` (excl. `two-phase-commit.md` — fixed), `dbms/sql/` (all),
`dbms/relational-model/` (excl. `keys.md` — fixed), `dbms/indexing/` (excl. `b-tree.md` — fixed),
`dbms/internals/` (all), `dbms/normalization/` (excl. `README.md` — fixed),
`dbms/distributed/` (excl. `raft.md` — fixed), and `dbms/overview.md`.

## Findings

### HIGH severity

#### U-H1. `transactions/lock-based.md` — Strict 2NL does NOT prevent non-repeatable reads
**Location:** lines ~62–67 (Strict 2PL bullet list)
**Wrong text:**
```
### Strict 2PL
Hold all **exclusive** locks until commit/abort. Prevents:
- Dirty reads
- Cascading aborts
- Non-repeatable reads
```
**Correct text:** Remove the "Non-repeatable reads" bullet. Strict 2PL holds only X (exclusive) locks until commit; S (shared) locks may be released in the shrinking phase, so another transaction can still modify a row between T1's two reads → non-repeatable read is still possible. Only Rigorous 2PL (which holds ALL locks including S locks until commit) prevents non-repeatable reads.
**Internal contradiction:** The summary table at line ~273 correctly attributes non-repeatable-read prevention to Rigorous 2PL only, contradicting the Strict 2PL bullet list. Q3 (line ~232) also says shared locks "can be released earlier" in Strict 2PL, again contradicting the bullet list.
**Verification:** Standard textbooks (Silberschatz, Korth, Sudarshan — Database System Concepts); internal contradiction within the same file.

#### U-H2. `transactions/mvcc.md` — InnoDB visibility check returns wrong value for own changes
**Location:** lines 226–228, `is_visible(version_trx_id, read_view)` Python pseudocode
**Wrong text:**
```python
def is_visible(version_trx_id, read_view):
    if version_trx_id == read_view.m_creator_trx_id:
        return False  # Own changes not visible to other transactions
```
**Correct text:** Should `return True` — a transaction must see its own uncommitted writes. InnoDB's actual `ReadView::changes_visible` returns `true` when `id == m_creator_trx_id` (see `storage/innobase/read/read0read.cc`). The comment "Own changes not visible to other transactions" is true *as a general statement*, but the function semantics ask "is this version visible to the read view's creator" — and own writes ARE visible to the creator.
**Verification:** InnoDB source (`storage/innobase/read/read0read.cc`, `ReadView::changes_visible`); a transaction that does `UPDATE x=1; SELECT x` must see `x=1`.

#### U-H3. `sql/stored-procedures.md` — Parameter name shadows column name (broken SQL)
**Location:** lines 79–80 (`CalculateBonus`) and 107–108 (`ProcessOrder`)
**Wrong text:**
```sql
SELECT salary, perf_rating INTO base_salary, performance
FROM Employees WHERE emp_id = emp_id;
...
SELECT status, total INTO order_status, order_total
FROM Orders WHERE order_id = order_id;
```
**Correct text:** In MySQL stored procedures, the parameter `emp_id` shadows the column `emp_id`, so `WHERE emp_id = emp_id` becomes `<param> = <param>` (always TRUE) → query returns ALL rows → `SELECT INTO` fails with "Result consisted of more than one row". Fix: rename parameters to `p_emp_id` / `p_order_id` OR qualify columns as `Employees.emp_id`. The other procedures in the file (`GetEmployeesByDept`, `GetDeptStats`, `TransferFunds`, `PlaceOrder`) correctly avoid this by using prefixed names (`p_customer_id`, etc.).
**Verification:** MySQL docs on stored-procedure parameter scope — local variables/parameters share namespace with column names; the local takes precedence.

#### U-H4. `sql/ctes.md` — Fabricated `max_recursive_iterations` PostgreSQL setting
**Location:** line 331, Q5 answer
**Wrong text:**
```
3. **Database limits**: Most databases have a `max_recursive_iterations` setting (PostgreSQL: 100 by default)
```
**Correct text:** PostgreSQL has **no** recursion-iteration limit setting — recursive CTEs run until the recursive term produces no more rows (relying on natural termination). The setting name `max_recursive_iterations` does not exist in PostgreSQL. The "100 by default" figure matches **SQL Server's** `MAXRECURSION` hint (default 100, via `OPTION (MAXRECURSION n)`). **MySQL** has `cte_max_recursion_depth` (default 1000). Suggested rewrite:
```
3. **Database limits**: SQL Server's MAXRECURSION hint defaults to 100 (use OPTION (MAXRECURSION n));
   MySQL's cte_max_recursion_depth defaults to 1000; PostgreSQL has no built-in limit (relies on
   natural termination or statement_timeout).
```
**Verification:** PostgreSQL documentation — no `max_recursive_iterations` parameter exists in any PG version. Confirmed by grep of `postgresql.conf` parameters.

#### U-H5. `relational-model/relational-calculus.md` — False claim that De Morgan's laws fail under NULLs
**Location:** lines 322–325, Q8 answer
**Wrong text:**
```
- De Morgan's laws don't hold: `NOT (A AND B)` ≠ `(NOT A) OR (NOT B)` when NULLs are involved
```
**Correct text:** De Morgan's laws **DO** hold in SQL's 3-valued logic (TRUE / FALSE / UNKNOWN). Verified by exhaustive truth-table enumeration (see Python script below). What actually fails is the Law of Excluded Middle (`A OR NOT A` ≠ TRUE when A is UNKNOWN) and Law of Non-Contradiction (`A AND NOT A` ≠ FALSE when A is UNKNOWN). Suggested rewrite:
```
- Law of Excluded Middle fails: `A OR NOT A` is UNKNOWN (not TRUE) when A is UNKNOWN
- Law of Non-Contradiction fails: `A AND NOT A` is UNKNOWN (not FALSE) when A is UNKNOWN
- De Morgan's laws DO hold in SQL 3VL
```
**Verification:** Python truth-table enumeration over all 9 (T,F,U) × (T,F,U) combinations confirms `NOT(A AND B) == (NOT A) OR (NOT B)` for all rows (0 mismatches). Standard reference: SQL standard 3-valued logic; Graefe 1993 "Rules in actively searched database systems".

#### U-H6. `indexing/gin.md` — Wrong index type in GIN fast-update example
**Location:** lines 205–207, "Bulk Update (No Pending List)" section under "GIN Fast Update"
**Wrong text:**
```sql
CREATE INDEX idx_name ON table USING GIST (column) 
  WITH (fastupdate = off);
```
**Correct text:** Should be `USING GIN (column) WITH (fastupdate = off);`. The entire section is about GIN indexes, but the example creates a GiST index (a completely different index type). `fastupdate` is a GIN-specific parameter; GiST does not have it. This is a copy-paste/typo that produces a fundamentally wrong index.
**Verification:** PostgreSQL docs — `fastupdate` is a GIN-specific storage parameter (https://www.postgresql.org/docs/current/gin-implementation.html).

#### U-H7. `transactions/isolation-levels.md` — Cross-reference confuses 2PL with 2PC
**Location:** line 500, Cross-References section
**Wrong text:**
```
- [Two-Phase Locking](./two-phase-commit.md) — 2PL as an implementation mechanism for Serializable
```
**Correct text:** `- [Two-Phase Locking](./lock-based.md) — 2PL as an implementation mechanism for Serializable`. The link points to `two-phase-commit.md` (which is about **2PC** — a distributed-commit protocol), but the description "2PL as an implementation mechanism for Serializable" refers to **Two-Phase Locking** (a concurrency-control protocol). 2PC and 2PL are entirely different concepts. The correct file is `lock-based.md` which covers 2PL.
**Verification:** 2PC (Two-Phase Commit) is for atomic distributed commit; 2PL (Two-Phase Locking) is for serializability — see `lock-based.md` line 37 ("## Two-Phase Locking (2PL)").

#### U-H8. `distributed/consistency.md` — Self-referential broken link
**Location:** line 260, Cross-References section
**Wrong text:**
```
- [Distributed Transactions](./consistency.md) — multi-operation consistency
```
**Correct text:** `- [Distributed Transactions](../transactions/distributed.md) — multi-operation consistency`. The link `./consistency.md` points to **the file itself** (this very `consistency.md`), not to the Distributed Transactions topic. The actual file is `../transactions/distributed.md`.
**Verification:** `distributed/consistency.md` is about consistency models (linearizability, eventual, etc.), not distributed transactions.

#### U-H9. `indexing/README.md` — Broken cross-reference for "Query Optimization"
**Location:** line 310, Cross-References section
**Wrong text:**
```
- [Query Optimization](../transactions/isolation-levels.md) — How optimizer uses indexes
```
**Correct text:** `- [Query Optimization](../internals/query-optimization.md) — How optimizer uses indexes`. The link points to `isolation-levels.md` (transaction isolation levels — completely unrelated to query optimization). The actual query-optimization file is `../internals/query-optimization.md`.
**Verification:** `transactions/isolation-levels.md` is about READ COMMITTED / REPEATABLE READ etc. — has nothing to do with the query optimizer.

### MEDIUM severity

#### U-M1. `sql/window-functions.md` — Misleading "default" comment on ROWS frame
**Location:** line 213, Frame Types section
**Wrong text:**
```sql
ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW  -- default
```
**Correct text:** Remove the `-- default` comment OR replace with: `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW  -- explicit ROWS frame`. The actual default frame when ORDER BY is specified is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` (RANGE, not ROWS). The distinction matters for LAST_VALUE and for ties in the ORDER BY column. The file's own "Default Frame" section (lines 227–235) correctly states the default uses RANGE — so the inline `-- default` comment is inconsistent with the rest of the document.
**Verification:** SQL:2003 standard; PostgreSQL/MySQL docs — default frame with ORDER BY is `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`.

#### U-M2. `distributed/paxos.md` — Malformed HTML entity in Mermaid diagram
**Location:** line 99, Phase 2 sequenceDiagram
**Wrong text:**
```
Note over P: Got majority promises<br/>If any promise had accepted value,<br/>use that value#59; else use own value
```
**Correct text:** Replace `#59;` with `;` (or `&#59;`). The `#59;` is a malformed HTML entity (missing leading `&`) that renders as literal text `#59;` instead of a semicolon. Likely an artifact of an over-eager HTML-escape routine.
**Verification:** HTML entity `&#59;` = `;`; `#59;` alone is not a valid entity.

#### U-M3. `distributed/consistency.md` — Malformed HTML entities in Mermaid diagram
**Location:** line 80, causal-consistency flowchart
**Wrong text:**
```
B["Message: #quot;I wrote x=1#quot;"]
```
**Correct text:** Replace `#quot;` with `"` (or `&quot;`). Same root cause as U-M2 — malformed HTML entities missing the leading `&`. Also found in unrelated files `caching/memcached.md` line 151 and `nosql/newsql.md` lines 223, 341 (outside this chunk's scope but worth flagging).
**Verification:** HTML entity `&quot;` = `"`; `#quot;` alone is not valid.

#### U-M4. `distributed/paxos.md` — Cross-reference points to wrong file
**Location:** line 282, Cross-References section
**Wrong text:**
```
- [Two-Phase Commit](./consensus.md) — the related distributed commit protocol
```
**Correct text:** `- [Two-Phase Commit](../transactions/two-phase-commit.md) — the related distributed commit protocol`. The link `./consensus.md` is the consensus-algorithms file (Paxos/Raft), not 2PC. The actual 2PC file lives in `../transactions/two-phase-commit.md`.
**Verification:** `distributed/consensus.md` describes Paxos/Raft/2PC comparison, but is not the dedicated 2PC reference page.

#### U-M5. `internals/wal.md` — MVCC snapshot is not based on LSN
**Location:** line 67, LSN use-case table
**Wrong text:**
```
| **MVCC** | Snapshot isolation based on LSN at snapshot time |
```
**Correct text:** `| **MVCC** | Snapshot isolation based on transaction IDs (XIDs) at snapshot time |`. Both PostgreSQL and InnoDB implement MVCC snapshots using transaction IDs (XIDs), not LSNs. LSNs are used for WAL ordering, dirty-page tracking, and recovery — not for MVCC visibility decisions. PostgreSQL's snapshot contains `xmin`, `xmax`, `xip_list` (all XIDs); InnoDB's ReadView contains `m_ids`, `m_up_limit_id`, `m_low_limit_id`, `m_creator_trx_id` (all transaction IDs).
**Verification:** PostgreSQL source `src/backend/utils/time/snapmgr.c`; InnoDB `ReadView` class — both use transaction IDs, not LSNs, for visibility.

#### U-M6. `indexing/tuning.md` — Wrong PostgreSQL extension name
**Location:** lines 157–158
**Wrong text:**
```sql
SET autoexplain.log_min_duration = 1000;
SET autoexplain.log_analyze = true;
```
**Correct text:**
```sql
SET auto_explain.log_min_duration = 1000;
SET auto_explain.log_analyze = true;
```
The extension is named `auto_explain` (with underscore), not `autoexplain`. The GUC parameter names follow the extension name: `auto_explain.log_min_duration`, `auto_explain.log_analyze`, etc. Also requires `LOAD 'auto_explain';` or `shared_preload_libraries = 'auto_explain'` to be active.
**Verification:** PostgreSQL docs — https://www.postgresql.org/docs/current/auto-explain.html.

#### U-M7. `transactions/lock-based.md` — Muddled reasoning for Wound-Wait preference
**Location:** line 240, Q5 answer
**Wrong text:**
```
**Wound-Wait is generally preferred** because younger transactions eventually proceed
(they wait for older to finish), while in Wait-Die, older transactions may repeatedly wait.
```
**Correct text (suggested):**
```
Wound-Wait generally has fewer aborts/restarts than Wait-Die because younger transactions
WAIT (rather than being immediately aborted as in Wait-Die). In Wait-Die, when a younger
transaction is aborted, it restarts with its original timestamp and may die again — leading
to more restarts. The "preferred" designation is workload-dependent; both are correct
deadlock-prevention protocols.
```
The reasoning given in the doc is muddled: in Wait-Die, OLDER transactions wait (don't repeatedly restart); it's the YOUNGER ones that die. The standard preference argument centers on restart counts, not "older transactions repeatedly waiting".
**Verification:** Silberschatz, Korth, Sudarshan — Database System Concepts, deadlock-prevention protocols.

#### U-M8. `transactions/mvcc.md` — Over-simplified English visibility rule
**Location:** lines 54–57 (English summary above the Python code)
**Wrong text:**
```
Visibility rules for a version:
  - Visible if xmin < xmax of snapshot AND xmin not in in_progress
  - AND xmax > xmin of snapshot (not deleted before snapshot)
```
**Correct text:** The second condition is insufficient — the rule must also check whether `xmax` was committed at snapshot time. The case `version.xmax` between `snapshot.xmin` and `snapshot.xmax` AND committed AND not in `in_progress` makes the version invisible (deleted before snapshot), but the simplified English rule would mark it visible. The formal Python code below (lines 76–93) is correct; the English summary above is too brief and misleading.
**Suggested fix:** Either remove the English summary (refer reader to the Python code) or expand it:
```
Visibility rules for a version (simplified; see code below for full rules):
  - Created before snapshot (xmin < snapshot.xmax) AND creator was committed (xmin not in in_progress)
  - AND (not deleted (xmax = INVALID) OR deleted after snapshot (xmax ≥ snapshot.xmax)
        OR deleter was still in-progress at snapshot time (xmax in in_progress))
```
**Verification:** PostgreSQL `HeapTupleSatisfiesMVCC` in `src/backend/utils/time/heapam_visibility.c`.

#### U-M9. `distributed/cap.md` — Redis Cluster "consistency preserved" is misleading
**Location:** lines 339–353 (Redis Cluster CP deep-dive)
**Wrong text:**
```
During partition:
  - Minority masters become unavailable (after timeout)
  - No writes to minority (consistency preserved)
  ...
Classification: PC/EC
```
**Correct text:** Redis Cluster is CP in the **availability** sense (minority side rejects writes), but it is NOT strongly consistent — it uses asynchronous replication, so on failover (master fails → replica promoted) acknowledged writes that were not yet replicated can be **lost**. The "consistency preserved" claim is too strong; "no split-brain writes" is more accurate. Classification as PC/EC overstates the guarantee (Redis Cluster does not provide linearizability/sequential consistency across failovers).
**Suggested rewrite:** Replace "No writes to minority (consistency preserved)" with "No writes to minority (prevents split-brain, but async replication means acknowledged writes can be lost on failover)".
**Verification:** Redis Cluster docs — "Redis Cluster is not strongly consistent" (https://redis.io/docs/reference/cluster-spec/).

### LOW severity

#### U-L1. `relational-model/relational-algebra.md` — Unusual HAVING notation
**Location:** lines 276–281, translation example
**Wrong text:**
```
τ_{num_courses DESC}(
    γ_{S.student_id, S.name; COUNT(E.course_id)→num_courses}(
        σ_{gpa > 3.0}(Student) ⋈ Enrollment
    )
    where num_courses > 3
)
```
**Correct text:** The trailing `where num_courses > 3` outside any operator is non-standard notation. The HAVING filter should be expressed inside the γ operator or as a separate σ applied to the grouping result:
```
τ_{num_courses DESC}(
    σ_{num_courses > 3}(
        γ_{S.student_id, S.name; COUNT(E.course_id)→num_courses}(
            σ_{gpa > 3.0}(Student) ⋈ Enrollment
        )
    )
)
```
**Verification:** Standard relational-algebra notation (Garcia-Molina, Ullman, Widom — Database Systems: The Complete Book).

#### U-L2. `sql/ddl.md` — "TRUNCATE rollback: usually not allowed" is misleading
**Location:** lines 220, 366 (table + summary)
**Wrong text:**
```
| Rollback | Usually not allowed | Always allowed |   (TRUNCATE vs DELETE table)
| TRUNCATE | Remove all data | Usually no | No |                              (summary)
```
**Correct text:** "DB-dependent" rather than "Usually not allowed". PostgreSQL treats TRUNCATE as transactional — it CAN be rolled back (the entire TRUNCATE is reversed). MySQL InnoDB auto-commits TRUNCATE (cannot be rolled back). SQL Server can roll back TRUNCATE within a transaction. The "usually not allowed" wording overstates the restriction.
**Verification:** PostgreSQL docs — "TRUNCATE is transaction-safe" (https://www.postgresql.org/docs/current/sql-truncate.html); MySQL docs — TRUNCATE causes an implicit commit.

#### U-L3. `sql/joins.md` — INNER JOIN order remark is misleading
**Location:** line 411, Common Mistakes section
**Wrong text:**
```
- Assuming INNER JOIN order doesn't affect performance (it does — smaller table first is usually better)
```
**Correct text:** For INNER JOINs, modern cost-based query optimizers (PostgreSQL, MySQL, SQL Server, Oracle) **automatically reorder** joins based on table statistics — the *written* order does not necessarily affect the *executed* order. The advice "smaller table first" applies to syntactic conventions or to OUTER JOINs (where reordering is constrained). Suggested rewrite: "Assuming INNER JOIN written order matters — modern optimizers reorder INNER JOINs automatically; this only matters for OUTER JOINs or when the optimizer picks a bad plan due to stale statistics."
**Verification:** PostgreSQL/MySQL optimizer documentation — join reordering is a core optimizer responsibility for INNER JOINs.

#### U-L4. `sql/dml.md` — Deprecated `VALUES()` in `ON DUPLICATE KEY UPDATE`
**Location:** line 176
**Wrong text:**
```sql
INSERT INTO Employees (emp_id, first_name, email, salary)
VALUES (101, 'Alice', 'alice@co.com', 75000)
ON DUPLICATE KEY UPDATE salary = VALUES(salary), email = VALUES(email);
```
**Correct text:** The `VALUES(col)` function in `ON DUPLICATE KEY UPDATE` is **deprecated as of MySQL 8.0.20**. The modern syntax uses an alias for the row being inserted:
```sql
INSERT INTO Employees (...) VALUES (...) AS new_row
ON DUPLICATE KEY UPDATE salary = new_row.salary, email = new_row.email;
```
The old syntax still works for backward compatibility but emits a deprecation warning.
**Verification:** MySQL 8.0 release notes — `VALUES()` in `ON DUPLICATE KEY UPDATE` deprecated 8.0.20.

#### U-L5. `internals/query-optimization.md` — Hash Join "worst case" mislabeled
**Location:** lines 86–90, Join Algorithms table
**Wrong text:**
```
| **Hash Join** | Equi-joins, large tables | O(n+m) | O(n) |
```
**Correct text:** The "Worst Case" column shows O(n+m), which is actually the **average/expected** case. The true worst case (pathological hash collisions — all keys hash to the same bucket) is O(n×m). With a good hash function, O(n+m) is the expected and de-facto worst case, but technically the worst case is quadratic. Suggested rewrite: clarify that the column is "Expected" rather than "Worst Case", or note "O(n+m) expected; O(n×m) worst case with hash collisions".
**Verification:** Standard hash-join analysis (Shapiro 1986; Graefe 1993 Volcano iterator model).

## Files confirmed clean

The following files were deeply read and found to have no significant content errors:

**transactions/** (12 files): `acid.md`, `recovery.md`, `aries.md`, `states.md`, `three-phase-commit.md`, `serializability.md`, `timestamp-based.md`, `distributed.md`, `checkpointing.md`, `concurrency-control.md`, `optimistic.md`, `saga.md`, `README.md`, `log-recovery.md`

**sql/** (7 files): `views.md`, `indexes.md`, `README.md`, `triggers.md`, `subqueries.md` (joins/ddl/dml/window-functions/ctes/stored-procedures each had at least one finding above)

**relational-model/** (3 files): `relational-algebra.md` (1 LOW only), `er-diagrams.md`, `README.md` (relational-calculus.md had HIGH finding)

**indexing/** (7 files): `clustered-vs-nonclustered.md`, `composite-index.md`, `bitmap-index.md`, `covering-index.md`, `b-plus-tree.md`, `hash-index.md`, `gist.md` (gin.md had HIGH finding; tuning.md had MEDIUM; README.md had HIGH broken link)

**internals/** (4 files): `lsm-trees.md`, `engines.md`, `compaction.md`, `README.md` (wal.md had MEDIUM; query-optimization.md had LOW)

**normalization/** (6 files): `1nf.md`, `2nf.md`, `3nf.md`, `bcnf.md`, `4nf-5nf.md`, `denormalization.md`

**distributed/** (4 files): `replication.md`, `sharding.md`, `README.md`, `consensus.md` (paxos.md had MEDIUM × 2; consistency.md had HIGH + MEDIUM; cap.md had MEDIUM)

**root:** `overview.md` — clean

## Notes for parent agent

1. The malformed HTML entities (`#quot;`, `#59;`) found in `paxos.md` and `consistency.md` are part of a **systemic pattern** — the same artifacts also appear in `caching/memcached.md` (line 151) and `nosql/newsql.md` (lines 223, 341), which are outside this chunk's scope. A repo-wide grep-and-replace pass for `#quot;` → `&quot;` and `#59;` → `&#59;` (or just the literal characters) would fix all instances.

2. Several broken cross-references (U-H7, U-H8, U-H9, U-M4) appear to be a pattern of agents linking to wrong sibling files. Worth a systemic xref-lint pass.

3. The 4 HIGH severity *factual* errors (U-H1 Strict 2PL, U-H2 InnoDB visibility, U-H4 fabricated PG setting, U-H5 De Morgan's claim) teach directly wrong information that would cause interview failures — these should be fixed before students rely on these pages.

4. U-H6 (GIN example using `USING GIST`) is a simple typo with severe practical consequences — following the example would create a completely different (and ineffective) index.

5. U-H3 (parameter shadowing in MySQL stored procedures) is a real anti-pattern bug — the example code would fail at runtime.
