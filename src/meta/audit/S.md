# Chunk S Audit — DBMS deep-read (nosql/postgresql/storage/caching/query-processing/interview-problems)

**Files audited:** 33 (nosql/×6, postgresql/×3, storage/×5, caching/×4 [buffer-pool.md skipped — already deeply read in Chunk P], query-processing/×9, interview-problems/×6)
**Total findings:** 25 (HIGH: 7, MEDIUM: 13, LOW: 5)

## Scope

Deep-read of the DBMS subdirectories that Chunk P only grep-skimmed. Every file was read end-to-end; arithmetic verified with Python; SQL syntax verified against PostgreSQL/MySQL references; technical claims verified against PostgreSQL docs, MongoDB docs, Memcached docs, Facebook's "Scaling Memcache" paper, and the MySQL parser source.

## Findings

### HIGH severity

#### src/dbms/nosql/document.md:226
- **Wrong text:** `| **Offline** | No | Yes (Couchbase Lite) |`  (in the CouchDB column of the MongoDB-vs-CouchDB feature table)
- **Correct text:** `| **Offline** | No | Yes (PouchDB) |`
- **Verification:** Couchbase Lite is the offline-sync client for **Couchbase** (a completely different database vendor). The offline-sync library for **CouchDB** is **PouchDB** — "PouchDB and CouchDB were designed for one main purpose: sync" (pouchdb.com/guides/replication.html; pouchdb.apache.org: "It enables applications to store data locally while offline, then synchronize it with CouchDB and compatible servers"). Confirmed via web search.
- **Severity rationale:** Teaches the wrong library for CouchDB offline sync. A candidate mentioning "Couchbase Lite" in a CouchDB context would be marked wrong.

#### src/dbms/nosql/graph.md:246
- **Wrong text:**
  ```sql
  CREATE TABLE edges (
    source_id INT REFERENCES nodes(id),
    target_id REFERENCES nodes(id),
    edge_type VARCHAR,
    properties JSONB,
    PRIMARY KEY (source_id, target_id, edge_type)
  );
  ```
- **Correct text:**
  ```sql
  CREATE TABLE edges (
    source_id INT REFERENCES nodes(id),
    target_id INT REFERENCES nodes(id),
    edge_type VARCHAR,
    properties JSONB,
    PRIMARY KEY (source_id, target_id, edge_type)
  );
  ```
- **Verification:** `target_id REFERENCES nodes(id)` is missing the column type declaration. PostgreSQL grammar requires `column_name data_type column_constraint` — `REFERENCES` alone is a constraint, not a type. SQLite accepts this (permissive BLOB type), but PostgreSQL/MySQL/SQL Server all reject it with a syntax error. Confirmed by attempting the DDL through `python3 sqlite3` (which accepted it, because SQLite allows type-less columns) and by checking the PostgreSQL grammar: `column_def: ColId typeName optCollateClause columnConstraint*`.
- **Severity rationale:** Code block is presented as a runnable PostgreSQL DDL pattern but would fail at parse time in PostgreSQL — the very database the surrounding text uses (JSONB, etc.).

#### src/dbms/nosql/newsql.md:419
- **Wrong text:** `F -->|No, eventual is OK| G["Use Cassandra with LWT"]`  (in the "When to Use NewSQL" decision flowchart; `F` is the "Need strong consistency?" decision node)
- **Correct text:** `F -->|No, eventual is OK| G["Use Cassandra (regular writes)"]`
- **Verification:** Cassandra LWT (Lightweight Transactions) provide **linearizable/strong** consistency via Paxos — they are *stronger* than regular Cassandra writes, not weaker. The decision branch is labeled "No, eventual is OK", which means the user does NOT want strong consistency; routing them to LWT (the strongest Cassandra option) is the opposite of the stated intent. Per Cassandra docs and the Paxos protocol LWT uses, LWT trades latency for linearizable consistency.
- **Severity rationale:** Inverted decision-tree logic — sends readers who want weak consistency to the strong-consistency option. The remaining three branches of the flowchart (Yes → Use NewSQL, No ACID+scale → PostgreSQL, No SQL → Cassandra/DynamoDB) are consistent, so this one branch stands out as a logical error.

#### src/dbms/storage/buffer-management.md:194
- **Wrong text:**
  ```sql
  -- Set buffer pool size (in 8KB pages)
  SET shared_buffers = '4GB';  -- 4GB buffer pool
  ```
- **Correct text:**
  ```sql
  -- Set buffer pool size (requires server restart)
  ALTER SYSTEM SET shared_buffers = '4GB';  -- then restart PostgreSQL
  -- or edit postgresql.conf and restart
  ```
- **Verification:** `shared_buffers` has context `postmaster` in `pg_settings`, which means it can only be set at server start. Running `SET shared_buffers = '4GB';` in a session returns: `ERROR: parameter "shared_buffers" cannot be changed without restarting the server`. The official PostgreSQL docs state "This parameter can only be set at server start." Confirmed via web search (postgresqlco.nf, postgresql.org/docs/9.1/runtime-config-resource.html, learnomate.org documentation-of-postgresql-conf-file).
- **Severity rationale:** Teaches a SQL command that fails on every PostgreSQL instance. A candidate or reader trying to follow the example verbatim would hit an error.

#### src/dbms/storage/record-formats.md:139
- **Wrong text:** `│ NULL bitmap (variable)       │  Bit per column: 1=NULL`
- **Correct text:** `│ NULL bitmap (variable)       │  Bit per column: 1=NOT NULL, 0=NULL`
- **Verification:** From the official PostgreSQL documentation (https://www.postgresql.org/docs/current/storage-page-layout.html, section "Heap Tuple Headers"): *"The null bitmap is only present if the HEAP_HASNULL bit is set in t_infomask. In this list of bits, a 1 bit indicates not-null, a 0 bit is a null."* The PostgreSQL source macro `att_isnull(attnum, bits)` returns true when the bit is NOT set. The doc's stated convention is therefore exactly inverted.
- **Severity rationale:** Teaches the opposite of PostgreSQL's actual NULL-bitmap convention — a candidate repeating "1=NULL" in an interview on PostgreSQL internals would be marked wrong.

#### src/dbms/query-processing/parsing.md:145
- **Wrong text:** `MySQL uses a hand-written recursive descent parser (not generated). Key files:` followed immediately by `sql/sql_yacc.yy — grammar (Bison)`
- **Correct text:** `MySQL uses a Bison-generated LALR parser (the lexer is hand-written). Key files:` (and the `sql_yacc.yy` reference is correct)
- **Verification:** The two adjacent sentences directly contradict each other in the same paragraph: "not generated" vs. "grammar (Bison)". The truth is that MySQL's **lexer** is hand-written (`sql_lex.cc`) but the **parser** is generated by Bison from `sql_yacc.yy`. Confirmed by MySQL blog "SQL parser refactoring in 5.7.4" ("Bison/YACC parser generators … they generate bottom-up parsers") and O'Reilly's *flex & bison* book ("MySQL actually uses a bison parser to parse its SQL input … it's the file sql/sql_yacc.yy"). PostgreSQL's parser is also Bison-generated (`gram.y`) — the doc gets PG right and MySQL wrong in the same file.
- **Severity rationale:** Self-contradictory paragraph that teaches the wrong parser architecture for MySQL. The contradiction is reader-visible (the two sentences are 2 lines apart).

#### src/dbms/interview-problems/join-problems.md:89
- **Wrong text:** `- Functions or casts on join columns do not prevent index use.`
- **Correct text:** `- Functions or casts on join columns **do** prevent index use (unless a matching expression index exists).`
- **Verification:** Wrapping a column in a function or cast defeats B-tree index lookup because the index is sorted on the raw column value, not the function output. `LOWER(a.name) = LOWER(b.name)` cannot use a plain index on `name` — it requires an expression index on `LOWER(name)`. Similarly `a.id::text = b.id_text` defeats indexes on `id`. This is one of the most common index-misuse footguns documented in PostgreSQL's "Indexes — Expression Indexes" section and in *Use The Index, Luke*. The doc states the opposite.
- **Severity rationale:** The "Useful checks" list purports to tell readers what to verify in query plans; this item asserts a falsehood that would lead readers to write queries with hidden function-call index defeats.

### MEDIUM severity

#### src/dbms/postgresql/README.md:18
- **Wrong text:** `├── stats collector`
- **Correct text:** Remove the `stats collector` line (replaced by an in-memory cumulative statistics subsystem). Optionally add `├── walreceiver / walsender` and `├── logical replication launcher`.
- **Verification:** PostgreSQL 15 (released 2021-10) removed the standalone stats collector process; statistics are now collected in shared memory (Percona blog "PostgreSQL 15: Stats Collector Gone?", postgresql.org/docs/current/monitoring-stats.html — "Cumulative statistics are collected in shared memory"). The list also omits `walwriter` and the logical replication launcher which are present in modern PG.
- **Severity rationale:** Outdated architecture list — the stats collector has been gone for ~3 years.

#### src/dbms/postgresql/advanced-features.md:7
- **Wrong text:** ```` ```json ```` (opening fence for a code block containing `CREATE TABLE`, `INSERT`, `SELECT` — pure SQL)
- **Correct text:** ```` ```sql ````
- **Verification:** The fenced block contains SQL DDL/DML, not JSON. mdBook/Syntax highlighters will mis-render.
- **Severity rationale:** Cosmetic but produces wrong syntax highlighting in the rendered book.

#### src/dbms/storage/README.md:51
- **Wrong text:** `HDD sequential read       1 ms            200 MB/s`
- **Correct text:** `HDD sequential read       20 ms           200 MB/s` (1 MB block, ~Jeff-Dean-style reference number)
- **Verification:** Common latency references (Jeff Dean's "Latency Numbers Every Programmer Should Know") cite ~20 ms for "Read 1 MB sequentially from disk". 1 ms does not match either a 1 MB transfer at 200 MB/s (= 5 ms transfer alone, plus 5–10 ms rotational/seek for the first block) nor a per-page 4 KB read (~20–50 μs after seek). The 1 ms figure is internally inconsistent with the 200 MB/s throughput on the same line.
- **Severity rationale:** Misleading latency number that doesn't match any standard reference.

#### src/dbms/storage/column-stores.md:200
- **Wrong text:** `| **Cassandra** | NoSQL | Column-family store |`  (in the "Real-World Column Store Systems" table)
- **Correct text:** Remove the Cassandra row entirely (Cassandra is a wide-column NoSQL store, not a columnar/OLAP store).
- **Verification:** The same file at line 251 explicitly warns: *"Confusing column-family stores (Cassandra) with column stores — They're different! Cassandra is a wide-column NoSQL store, not a true columnar store."* The table at line 200 and the warning at line 251 contradict each other.
- **Severity rationale:** Internal self-contradiction within the same file.

#### src/dbms/caching/redis.md:273
- **Wrong text:** `For CPU-bound operations (Lua scripts, big sorted sets), Redis 6+ supports I/O threads.`
- **Correct text:** `For network-I/O-bound workloads (many concurrent connections), Redis 6+ supports I/O threads. Command execution remains single-threaded.`
- **Verification:** Redis 6 introduced `io-threads` for **network I/O** (socket reads/writes), not for command execution. CPU-bound operations (Lua scripts, big sorted set ops) still run on the main thread and do NOT benefit from I/O threads. Redis.io blog "Diving into Redis 6": *"while it retains a core single-threaded data-access interface, I/O is now threaded."* Confirmed via web search.
- **Severity rationale:** Misattributes the benefit of I/O threads to CPU-bound operations, which they do not help.

#### src/dbms/caching/memcached.md:89-93
- **Wrong text:**
  ```
  Class 1:   64 bytes  (item overhead: 48 bytes → 16 bytes data)
  Class 2:  128 bytes  (80 bytes data)
  Class 3:  256 bytes  (208 bytes data)
  ```
- **Correct text:**
  ```
  Class 1:   ~96 bytes  (item overhead: ~48-56 bytes → ~40 bytes data)
  Class 2:  ~120 bytes
  Class 3:  ~152 bytes
  ...
  Growth factor: 1.25 (default)
  ```
- **Verification:** The Memcached default minimum chunk size (`-n` flag) is 48 bytes of payload, which with the ~48–56 byte item header gives a real Class-1 chunk size of ~96 bytes. Multiple references confirm "slab class 1: chunk size 96" (siemens.blog 2022, Memcached 5.5 reference manual: "the default size for the smallest block is 88 bytes (40 bytes of value, and the default 48 bytes for the key and flag data)"). The doc's "64 bytes" is too low for any standard Memcached version.
- **Severity rationale:** Wrong default slab sizes; readers running `stats slabs` on real Memcached will see different numbers.

#### src/dbms/caching/memcached.md:238
- **Wrong text:** `Items with TTL=0 (never expire) are evicted first`
- **Correct text:** `Items are evicted by LRU (least recently used) regardless of TTL setting; TTL=0 items are not prioritized for eviction.`
- **Verification:** Memcached uses per-slab-class LRU eviction (segmented into HOT/WARM/COLD/TEMP since 1.5). There is no rule that TTL=0 items are evicted first — all items compete on access recency. Confirmed via Memcached docs (memcached.org/blog/modern-lru) and the protocol.txt description of the segmented LRU.
- **Severity rationale:** States an eviction rule that doesn't exist in Memcached.

#### src/dbms/caching/memcached.md:308
- **Wrong text:** `Facebook uses a lease mechanism built into their modified Memcached (memcachelint).`
- **Correct text:** `Facebook uses a lease mechanism built into their modified Memcached (called "Memcache" in their paper).`
- **Verification:** Facebook's "Scaling Memcache at Facebook" (Nishtala et al., USENIX ATC 2013) introduces "leases" to address stale sets and thundering herds. The system is called **Memcache** (not "memcachelint"). No reference to "memcachelint" appears in the paper or in Facebook's open-source memcached fork. The tool name appears to be hallucinated.
- **Severity rationale:** Cites a non-existent tool name; readers searching for "memcachelint" will find nothing.

#### src/dbms/nosql/newsql.md:307
- **Wrong text:** `YEDIS["YEDIS<br/>(Redis-compatible)"]`  (presented as a current YugabyteDB API in the architecture diagram)
- **Correct text:** Either remove YEDIS or annotate as deprecated.
- **Verification:** YugabyteDB's YEDIS (Redis-compatible API) was deprecated. From dev.to/yugabyte (Dec 2022) and the YugabyteDB docs: *"Important: YEDIS is deprecated!"* The doc presents YEDIS as an active YugabyteDB API alongside YSQL and YCQL without noting its deprecation.
- **Severity rationale:** Outdated — readers following the doc would adopt a deprecated API.

#### src/dbms/query-processing/sort-merge.md:38-53
- **Wrong text:**
  ```python
  while r is not null and s is not null:
      if r.join_key == s.join_key:
          s_mark = s
          while r is not null and r.join_key == s_mark.join_key:
              s = s_mark
              while s is not null and s.join_key == r.join_key:
                  emit (r, s)
                  s = next(sorted_S)
              r = next(sorted_R)
          s = next(sorted_S)  # Move past the group    ← BUG
      elif r.join_key < s.join_key:
          r = next(sorted_R)
      else:
          s = next(sorted_S)
  ```
- **Correct text:** Delete the line `s = next(sorted_S)  # Move past the group`. After the inner while-loops, `s` is already pointing at the first tuple past the matching group; advancing it again skips a tuple. Standard sort-merge join pseudocode (e.g., Silberschatz, Korth, Sudarshan, *Database System Concepts*) does not include this extra advance.
- **Verification:** Traced the algorithm with `R = [(1, A), (2, B)]`, `S = [(1, X), (2, Y), (2, Z)]`. Expected output: `(A,X), (B,Y), (B,Z)`. Actual output with the buggy line: `(A,X), (B,Z)` — the match `(B,Y)` is skipped because `s` advances past `(2,Y)` to `(2,Z)` after the inner loops complete. The standard textbook algorithm omits this extra `s = next(sorted_S)`.
- **Severity rationale:** Pseudocode produces wrong output for any dataset where consecutive matching groups exist.

#### src/dbms/nosql/graph.md:91-92
- **Wrong text:** `B --> B2["4 JOINs, O(N²) or worse"]`  (in the relational-DB-vs-graph-DB traversal comparison)
- **Correct text:** `B --> B2["3 JOINs, O(K²)"]` (to match the SQL on the line above, which has exactly three JOINs)
- **Verification:** The SQL on the preceding line has exactly 3 JOIN clauses: `JOIN friends f1 ON u1.id = f1.user_id`, `JOIN friends f2 ON f1.friend_id = f2.user_id`, `JOIN users u2 ON f2.friend_id = u2.id`. The "4 JOINs" label is incorrect. Also, the complexity label "O(N²)" doesn't match the later "O(K²) where K = avg friends" on the graph-DB side — the relational side should be expressed in similar terms for the comparison to make sense.
- **Severity rationale:** Mislabeled JOIN count and inconsistent complexity notation in a teaching diagram.

#### src/dbms/interview-problems/classic-problems.md:128-130
- **Wrong text:**
  ```sql
  SELECT user_id FROM (
    SELECT user_id, login_date,
      login_date - INTERVAL ROW_NUMBER() OVER (
        PARTITION BY user_id ORDER BY login_date
      ) DAY as grp
    FROM logins
  ) GROUP BY user_id, grp
  HAVING COUNT(*) >= 3;
  ```
- **Correct text:** (PostgreSQL) `login_date - (ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) * INTERVAL '1 day') as grp`  — or label the snippet as MySQL-specific.
- **Verification:** `INTERVAL <expression> DAY` is **MySQL** syntax (MySQL allows `INTERVAL expr UNIT` with a non-literal expression). Standard SQL / PostgreSQL requires `INTERVAL '1' DAY * expr` or `(expr || ' days')::interval`. PostgreSQL's grammar for interval literals requires a string literal: `INTERVAL '1 day'` — it does not accept `INTERVAL ROW_NUMBER() OVER (...) DAY`. The rest of the file uses PostgreSQL-flavored syntax (e.g., line 16 `OFFSET 1`), so this snippet is dialect-inconsistent.
- **Severity rationale:** Code as written will fail in PostgreSQL; would-be runners will hit a syntax error.

#### src/dbms/nosql/document.md:252-263
- **Wrong text:**
  ```javascript
  session.startTransaction()
  try {
    db.accounts.updateOne({ _id: 1 }, { $inc: { balance: -100 } }, { session })
    db.accounts.updateOne({ _id: 2 }, { $inc: { balance: 100 } }, { session })
    session.commitTransaction()
  } catch (e) {
    session.abortTransaction()
  }
  ```
- **Correct text:** Add `const session = db.getMongo().startSession();` before `session.startTransaction()` (and ideally `await` since MongoDB transactions are async).
- **Verification:** The variable `session` is used (in `startTransaction()`, the `{ session }` options, `commitTransaction()`, `abortTransaction()`) but never declared. Running the snippet verbatim throws `ReferenceError: session is not defined`. MongoDB's official transaction example always begins with `const session = client.startSession()`.
- **Severity rationale:** Code is not runnable as written; students copy-pasting will get a ReferenceError.

### LOW severity

#### src/dbms/interview-problems/README.md:5-9
- **Wrong text:** The "Chapters" table only lists two files: `classic-problems.md` and `optimization-problems.md`.
- **Correct text:** Add rows for `join-problems.md`, `window-function-problems.md`, and `concurrency-scenarios.md` (all present in the same directory).
- **Verification:** `LS src/dbms/interview-problems/` shows 5 content .md files plus the README. Three of them are not listed in the README's chapter table.
- **Severity rationale:** Navigation gap — readers using the README as an index will miss 3 of 5 problem sets.

#### src/dbms/query-processing/execution-plans.md:159
- **Wrong text:** `Limit (if TOP N)`  (top node of the plan tree diagram for the query `SELECT name FROM students WHERE gpa > 3.5 ORDER BY name`)
- **Correct text:** Remove the `Limit (if TOP N)` node from this plan tree (the example query has no `LIMIT`/`TOP` clause), or change the example query to include `LIMIT 10`.
- **Verification:** The example query is `SELECT name FROM students WHERE gpa > 3.5 ORDER BY name` — no `LIMIT`. The plan tree shows a `Limit` node that wouldn't exist in the actual plan.
- **Severity rationale:** Plan-tree diagram doesn't match the example query.

#### src/dbms/query-processing/execution-plans.md:222
- **Wrong text:** `PostgreSQL: Limited adaptive capabilities (mostly through GEQO for many-way joins)`
- **Correct text:** `PostgreSQL: Limited adaptive capabilities (mostly plan-time, e.g. GEQO for many-way joins). Runtime adaptation is minimal compared to SQL Server Adaptive Joins or Oracle Adaptive Plans.`
- **Verification:** GEQO (Genetic Query Optimization) is a **plan-time** algorithm for choosing join order in queries with ≥12 tables. It is not runtime adaptive query processing. The doc's section header is "Adaptive Query Processing" (runtime plan adjustment), so citing GEQO there is a category error.
- **Severity rationale:** Conflates plan-time optimization with runtime adaptation.

#### src/dbms/nosql/column-family.md:153
- **Wrong text:** `**Quorum formula:**`  (section header, immediately followed by `Strong consistency: W + R > N`)
- **Correct text:** `**Strong consistency condition:**` (or `**Quorum-based consistency:**`)
- **Verification:** The formula `W + R > N` is the **strong consistency condition**, not the quorum formula. The actual quorum is `⌊N/2⌋ + 1`. The doc's content correctly states the strong-consistency condition; only the section header is mislabeled.
- **Severity rationale:** Mislabels a formula. The content is correct, so impact is limited.

#### src/dbms/storage/file-organization.md:213
- **Wrong text:** `TOAST:      16384 (toast table for large values)`
- **Correct text:** `TOAST:      16384_toast (toast table for large values; file uses the TOAST table's own OID, not the main table's OID)`
- **Verification:** PostgreSQL names a table's TOAST table with its own OID (e.g., `16389`), not the parent table's OID. The main data file is `16384`, and the TOAST table is a separate relation with a separate OID — typically visible as `pg_toast.pg_toast_<main_oid>`. Labeling the TOAST file with the same `16384` OID is misleading.
- **Severity rationale:** Minor inaccuracy in the file-naming diagram.

## Files confirmed clean

The following deeply-read files had no arithmetic, technical, code, Mermaid, LaTeX, or Markdown errors:

### nosql/
- `nosql/key-value.md` — Redis/DynamoDB/RocksDB API examples and partitioning diagrams all correct; CRC16 vs DynamoDB partition hash correctly presented as generic example
- `nosql/README.md` — CAP classification table (Redis CP, DynamoDB AP, MongoDB CP, Cassandra AP, HBase CP) is standard; mermaid diagrams clean

### postgresql/
- `postgresql/interview-questions.md` — VARCHAR vs TEXT, TOAST expansion ("The Oversized-Attribute Storage Technique"), CTE materialization (PG 12+), EXPLAIN fields — all correct

### storage/
- `storage/buffer-management.md` (apart from the two HIGH findings) — clock-sweep trace, pin-count/dirty-bit semantics, block-nested-loop formula `Br + ⌈Br/(B-2)⌉ × Bs`, direct-IO/double-buffering discussion all correct

### caching/
- `caching/README.md` — cache hierarchy, topologies, policies (cache-aside/read-through/write-through/write-behind/write-around) all standard
- `caching/query-cache.md` — MySQL 8.0 query-cache removal history correct; materialized-view example valid PostgreSQL; cache-key design discussion sound

### query-processing/
- `query-processing/README.md` — pipeline overview, optimizer comparison table correct (PG GEQO, MySQL cost-based, Oracle adaptive, SQL Server query store, CockroachDB distributed)
- `query-processing/optimization.md` — join-ordering counts verified (Catalan(N-1) × N!): N=3 → 12 ✓, N=5 → 1,680 (~10³) ✓, N=10 → ~17.6 billion (~17×10⁹) ✓; selectivity formulas (1/NDV, range, AND=×, OR=1-(1-s)(1-s)) all verified; System R DP O(3^N) stated correctly
- `query-processing/joins.md` — join selectivity formula and example (10000 × 50000 / 200 = 2,500,000) verified; comparison table accurate
- `query-processing/nested-loop.md` — all four cost calculations verified with Python (simple NL 5,000,050; index NL 5,050; block NL 250,050; buffered block NL 5,050)
- `query-processing/hash-join.md` — simple hash-join cost 1,100, Grace hash-join 3,300 (3 × (100+1000)), all math verified; partition count ceil(100/8)=13 verified
- `query-processing/cost-estimation.md` — all selectivity math verified (0.5 × 2500/10000 = 0.125; 10000 × 50000/200 = 2,500,000; 100000 × 100/8192 = 1,221; 3 + 0.01 × 1221 = 15.21; 1250 × 100000/10000 = 12,500; 12,500 × 500/500 = 12,500); independence/OR/AND selectivity formulas standard
- `query-processing/execution-plans.md` (apart from the LOW findings) — EXPLAIN-output walk-through valid; parameter-sniffing explanation correct; covering-index example valid

### interview-problems/
- `interview-problems/optimization-problems.md` — covering index `INCLUDE` syntax valid PostgreSQL; composite-index leftmost-prefix rule correct; GIN-on-tsvector index correct
- `interview-problems/window-function-problems.md` — top-row-per-group, running totals, gaps-and-islands (cumulative-SUM-of-break-flag pattern), LAST_VALUE frame-default trap all correct; PostgreSQL interval comparison syntax valid
- `interview-problems/concurrency-scenarios.md` — lost-update atomic UPDATE pattern, deadlock description, isolation-anomaly table (dirty read / non-repeatable read / phantom / write skew), optimistic concurrency CAS pattern all correct; cross-references to `../../os/synchronization/deadlocks/README.md`, `../../backend/patterns/idempotency.md`, `../../concurrency/aba-problem.md` all verified to exist
- `interview-problems/join-problems.md` (apart from the HIGH finding on line 89) — LEFT-JOIN-becomes-INNER-JOIN trap, NOT IN null semantics, EXISTS vs JOIN guidance all correct; cross-references valid

## Top issues summary

1. **HIGH — `record-formats.md:139`** — PostgreSQL NULL bitmap convention inverted (doc says `1=NULL`, official docs say `1=NOT NULL`)
2. **HIGH — `graph.md:246`** — `target_id REFERENCES nodes(id)` missing `INT` type → PostgreSQL syntax error
3. **HIGH — `buffer-management.md:194`** — `SET shared_buffers = '4GB';` always fails (postmaster context, needs restart + `ALTER SYSTEM`)
4. **HIGH — `parsing.md:145`** — Self-contradiction: "MySQL uses hand-written recursive descent (not generated)" immediately followed by listing `sql_yacc.yy — grammar (Bison)`
5. **HIGH — `join-problems.md:89`** — "Functions or casts on join columns do not prevent index use" — exactly inverted; functions/casts DO prevent regular index use
6. **HIGH — `document.md:226`** — CouchDB offline library listed as "Couchbase Lite" (should be PouchDB; Couchbase Lite is for Couchbase, a different database)
7. **HIGH — `newsql.md:419`** — Decision-tree branch "No, eventual is OK → Use Cassandra with LWT" is logically inverted (LWT provides strong consistency, opposite of eventual)
8. **MEDIUM — `sort-merge.md:49`** — Pseudocode has extra `s = next(sorted_S)` that skips tuples; traced bug drops matches
9. **MEDIUM — `memcached.md:308`** — Hallucinated tool name "memcachelint" (Facebook's system is called "Memcache")
10. **MEDIUM — `caching/redis.md:273`** — I/O threads misattributed to CPU-bound operations (they help network I/O only)

## Verification commands used

```bash
# Graph DDL syntax check (sqlite is permissive; PostgreSQL is not)
python3 -c "import sqlite3; sqlite3.connect(':memory:').executescript('CREATE TABLE nodes (id INT PRIMARY KEY); CREATE TABLE edges (source_id INT REFERENCES nodes(id), target_id REFERENCES nodes(id), edge_type VARCHAR, properties TEXT, PRIMARY KEY (source_id, target_id, edge_type))')"
# → SQLite accepts both; PostgreSQL rejects the doc's version (verified via grammar)

# Cost-arithmetic verification (nested-loop, hash-join, cost-estimation)
python3 -c "print('simple NL:', 50 + 1000*5000); print('index NL:', 50 + 1000*(3+2)); print('block NL:', 50 + 50*5000); print('buffered:', 50 + (50//50)*5000); print('hash simple:', 100+1000); print('grace:', 3*(100+1000))"
# → 5000050, 5050, 250050, 5050, 1100, 3300 ✓

# Join-ordering counts (Catalan(N-1) × N!)
python3 -c "from math import factorial, comb; N=10; catalan = comb(2*(N-1), N-1)//N; print(N, factorial(N)*catalan)"
# → 10 17643225600  ≈ 17.6 billion ✓

# PostgreSQL NULL bitmap convention (web-verified)
# Source: https://www.postgresql.org/docs/current/storage-page-layout.html
# "a 1 bit indicates not-null, a 0 bit is a null"

# shared_buffers context (web-verified)
# Source: https://postgresqlco.nf/doc/en/param/shared_buffers
# "This parameter can only be set at server start."

# MySQL parser (web-verified)
# Source: https://dev.mysql.com/blog-archive/sql-parser-refactoring-in-5-7-4-lab-release
# "Bison/YACC parser generators (they generate bottom-up parsers)"
# Source: O'Reilly flex & bison: "MySQL actually uses a bison parser … sql/sql_yacc.yy"

# Facebook Memcache paper (web-verified)
# Source: Nishtala et al., "Scaling Memcache at Facebook", USENIX ATC 2013
# "We introduce a new mechanism we call leases to address … thundering herds"
# (No "memcachelint" appears in the paper.)

# YugabyteDB YEDIS deprecation
# Source: https://dev.to/yugabyte/yugabytedb-yedis-11k3 (Dec 2022)
# "Important: YEDIS is deprecated!"

# PostgreSQL 15 stats collector removal
# Source: https://www.percona.com/blog/postgresql-15-stats-collector-gone-whats-new
# "the 'stats collector' is missing, and it is gone for good"
```

## Next actions for parent agent

1. **Apply HIGH-severity fixes first** (7 findings): the inverted NULL bitmap, the missing `INT`, the broken `SET shared_buffers`, the self-contradictory MySQL parser paragraph, the inverted "functions/casts don't prevent index use" claim, the Couchbase Lite → PouchDB correction, and the Cassandra-LWT decision-tree inversion.
2. **Apply MEDIUM fixes** (13 findings): sort-merge pseudocode bug, Memcached slab sizes / TTL=0 eviction / memcachelint name, Redis I/O-threads scope, YEDIS deprecation note, decision-tree dialect fix, MongoDB session-creation snippet, column-stores table Cassandra row, and the latency / stats-collector / fence-language fixes.
3. **Apply LOW fixes** (5 findings) opportunistically: README chapter list, plan-tree Limit node, GEQO adaptive wording, quorum-formula header, TOAST OID label.
