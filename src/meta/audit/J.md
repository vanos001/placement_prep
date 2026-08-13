# Chunk J Audit — Storage + Search + Web-servers + Data-engineering

**Scope:** src/storage/*, src/search/*, src/web-servers/*, src/data-engineering/* (skipping already-fixed)
**Files audited:** 33
**Files clean:** 21
**Total findings:** 17

## Findings

### HIGH severity

#### J-1. `src/storage/nvme.md` — Wrong NVMe queue-depth number (typo, "64,536" instead of "65,535" / "65,536")

**Line 27, table cell:**
```
| Max Queue Depth | 32 commands (1 queue) | 64,536 commands (64K queues) |
```

**Problem:** The number `64,536` is a typo. Per the NVMe 1.4 specification (NVM Express Base Specification, Revision 1.4b, Section 5.21.1.5 — MQES field): "supporting up to 65,535 I/O Queues with up to 64 Ki − 1 outstanding commands per I/O Queue." So the maximum commands per queue is **65,535** (the field is 16-bit, value 0xFFFF means 65,535 entries when interpreted 0-based; Linux kernel NVMe driver reports a 65,536 ceiling). Either way, `64,536` (with a 4 instead of a 5) is incorrect.

**Also wrong:** the same cell conflates two specs — "commands per queue" and "number of queues". The table header is `Max Queue Depth` (a per-queue property), but the NVMe cell appends "(64K queues)" which is a different property (the queue count). The proper value for "Max Queue Depth" alone is "65,535 commands per queue" or "64K commands per queue".

**Source:** https://nvmexpress.org/wp-content/uploads/NVM-Express-1_4b-2020.09.21-Ratified.pdf

---

#### J-2. `src/storage/lsm-compaction.md` — MemTable described as "unsorted" (wrong)

**Line 22:**
```
L0 is special: flushed SSTs overlap (since flushed from unsorted MemTables at different times), so reads must check all L0 files.
```

**Problem:** MemTables are **sorted** in-memory structures (typically skip-lists in RocksDB/LevelDB, or red-black trees in Cassandra). The reason L0 SSTs overlap is **not** that MemTables are unsorted — it is that consecutive MemTable flushes produce independent SST files at L0 without merging. The sortedness of the MemTable is preserved in each individual L0 SST, but separate flushes can cover overlapping key ranges.

**Correct text:** "L0 is special: flushed SSTs overlap (since each MemTable flush independently produces a new SST at L0 without merging with existing L0 files), so reads must check all L0 files."

**Sources:**
- https://www.darchuletajr.com/blog/lsm-trees-memtables-sorted-string-tables-introduction — "memtable implementation and data structure trade-off discussion (skip list, red-black tree…)"
- RocksDB uses skip-list MemTable: https://github.com/facebook/rocksdb/wiki/MemTable
- Cassandra uses skip-list-based MemTable.

---

#### J-3. `src/storage/lsm-compaction.md` — Comparison table has wrong/missing columns (broken table)

**Lines 62-66:**
```
| Strategy | WA typical | RA point | SA | Reclaim speed | Best for | Impl |
|----------|------------|----------|----|---------------|----------|------|
| Leveled | High 10-30× | Low (bounded files) | Fast (regular merges remove tombstones) | Read-heavy low fanout | RocksDB level, Cassandra LCS |
| Size-tiered / Universal | Lower (fewer rewrites) | Higher (many overlapping) | Slower, major compactions heavy | Bulk ingest, write-heavy | Cassandra STCS, RocksDB Universal |
| Hybrid (Tiered+Leveled) | Middle | Middle | Tunable | Mixed | RocksDB tiered+leveled, Cassandra UCS |
```

**Problem:** The header declares **7 columns** (Strategy, WA typical, RA point, **SA**, Reclaim speed, Best for, Impl) but each data row has only **6 cells** — the `SA` column value is missing entirely, and the values for `Reclaim speed`/`Best for`/`Impl` are shifted one column to the left. As written:

- "Fast (regular merges remove tombstones)" sits in the `SA` column, but it is actually reclaim-speed text.
- "Read-heavy low fanout" sits in `Reclaim speed`, but is actually a `Best for` value.
- "RocksDB level, Cassandra LCS" sits in `Best for`, but is actually the `Impl` value.
- The `Impl` column is empty for all rows.

The reader learns the wrong value for every column from `SA` onward. Same shift applies to the Size-tiered and Hybrid rows.

**Fix:** Insert the missing `SA` cell in every row. From the body text in §Classic Strategies, plausible SA values are: Leveled = "Low ~10%", Size-tiered = "High up to 2×", Hybrid = "Tunable".

---

#### J-4. `src/storage/ceph-crush.md` — Wrong claim that Ceph MONs switched from Paxos to "paxos + cephx" in Pacific

**Line 29:**
```
**MON**: maintains authoritative cluster map (CRUSH map, OSD map, PG map, pool properties). Paxos/Raft-like consensus (Paxos until Pacific, now using `paxos` + `cephx`).
```

**Problem:** Two technical errors:

1. Ceph monitors have **always** used a variant of Multi-Paxos for cluster-map consensus. There was **no switch to Raft** in the Pacific (or any other) release. The phrase "Paxos until Pacific, now using paxos" is self-contradictory and ahistorical.
2. `cephx` is the **Ceph authentication protocol** (Kerberos-style mutual authentication with shared-key tickets), **not** a consensus algorithm. It cannot be presented as part of the consensus story.

**Correct text:** "Ceph monitors use a variant of the Multi-Paxos algorithm to reach consensus on cluster-map updates. Cephx is used for authentication between clients and daemons, not for consensus."

**Sources:**
- https://docs.ceph.com/en/pacific/rados/configuration/auth-config-ref — "CephX protocol is enabled by default" (auth, not consensus)
- https://oneuptime.com/blog/post/2026-03-31-rook-ceph-ha-paxos-consensus/view — "Ceph monitor high availability is built on Paxos consensus"
- Ceph docs: "Ceph monitors use a variation of the Paxos algorithm to maintain consensus about maps"
- https://repositorio-aberto.up.pt/bitstream/10216/139563/2/529181.pdf — "Ceph uses the Multi-Paxos algorithm in order to maintain consistent versions of these maps"

Note: this directly contradicts `ceph.md` line 55 which correctly says "Uses Paxos for consensus". So the two storage docs disagree.

---

#### J-5. `src/storage/ceph-crush.md` — Wrong claim that CRUSH is more stable than "classic consistent hashing"

**Line 69:**
```
Weil's CRUSH, designed for RADOS, is stable when many devices join/leave — only minimal data moves to re-balance, vs classic consistent hashing where massive rebalance would be needed.
```

And in the interview Q at line 159:
```
CRUSH is pseudo-random but deterministic with hierarchy and weights. When adding OSD, only `1/N` data moves to new OSD to rebalance, vs consistent hashing where many keys move.
```

**Problem:** This is a straw-man comparison. Classic **consistent hashing** (Karger et al., 1997) is *defined* by the property that adding/removing a node moves only `K/N` of the keys — exactly the property CRUSH also provides. The author has confused *consistent hashing* with *naive modulo hashing* (`hash(key) % N`), which is the one that remaps almost all keys when N changes. CRUSH's actual advantages over consistent hashing are the **failure-domain-aware hierarchical placement** and **weighting**, not stability-on-add/remove (which both algorithms share).

**Sources:**
- Karger et al., "Consistent Hashing and Random Trees", 1997 — adds/removes touch `K/N` keys
- Weil et al., "CRUSH: Controlled, Scalable, Decentralized Placement of Replicated Data" (SC '06) — compares CRUSH to "linear hashing and RUSH", not to consistent hashing as defined by Karger.

---

#### J-6. `src/web-servers/apache.md` — Section header typo "MMP worker" instead of "MPM worker"

**Line 15:**
```
### MMP worker
```

**Problem:** "MMP" is a typo. The correct name is **MPM** (Multi-Processing Module). Every other reference in the doc uses "MPM" correctly (lines 4, 7, 23, plus the table on `nginx.md` line 137). This single header has the wrong acronym.

**Source:** https://httpd.apache.org/docs/current/mpm.html — "Multi-Processing Modules (MPMs)"

---

#### J-7. `src/storage/erasure-coding.md` — Python code claims GF(2^8) arithmetic but uses plain numpy integer arithmetic

**Lines 103-130:**
```python
# Galois Field arithmetic (GF(2^8))
# In practice, use libraries like zfec, pyfinite, or jerasure

K = 4
M = 2
N = K + M

G = np.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 0],
    [0, 0, 0, 1],
    [1, 1, 1, 1],  # parity chunk 0 (sum)
    [1, 2, 3, 4],  # parity chunk 1 (weighted sum)
])

data = np.array([10, 20, 30, 40])
coded = G @ data  # [10, 20, 30, 40, 100, ?]
```

**Problem:** The comment claims "Galois Field arithmetic (GF(2^8))" but the code uses **plain numpy integer arithmetic** — `numpy` does not implement GF(2^8) operations. Reed-Solomon over GF(2^8) requires that addition be XOR and multiplication use log/exp tables in the field, otherwise:
- the matrix is not a valid RS generator matrix (the [1,2,3,4] row only makes sense over a field where 2,3,4 are valid field elements with field-specific multiplication);
- the system cannot reconstruct data after a loss using field inversion (np.linalg.inv uses real-number inversion, not GF inversion);
- the demonstration does not match what real RS encoding does.

The code also leaves `?` as a placeholder (the actual real-arithmetic value would be `300`: 1·10 + 2·20 + 3·30 + 4·40 = 10+40+90+160 = 300).

**Fix:** Either (a) label the snippet as a *toy illustration in ordinary arithmetic* and remove the GF(2^8) claim, or (b) actually use a GF(2^8) library such as `galois` or `reedsolo`:

```python
import galois
GF = galois.GF(2**8)
G = GF([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1],[1,1,1,1],[1,2,3,4]])
data = GF([10,20,30,40])
coded = G @ data
# reconstruction: G_inv = GF(np.linalg.inv(G_recover)) works inside the field
```

---

#### J-8. `src/storage/erasure-coding.md` — "Recovery Cost" table has wrong recovery-read figures for EC

**Lines 231-236:**
```
| Scheme | Recovery Read | Recovery Network | Recovery Time |
|--------|--------------|------------------|---------------|
| 3× Replication | 1× data size | 1× data size | Fast |
| 4+2 EC | 4× data size | 1× data size | Moderate |
| 10+4 EC | 10× data size | 1× data size | Slow |
```

**Problem:** For the loss of a single chunk in RS(K,M), recovery needs to read **K** chunks total (any K of the surviving K+M−1 chunks). With chunk size = data_size/K, the bytes read = K × (data_size/K) = **1× data size**, not "K× data size". So for 4+2 the recovery read is ~1× data size, and for 10+4 it is also ~1× data size — *not* 4× and 10× respectively. The "Recovery Network" column is correct (you only transfer the missing chunk = 1/K × data size over the wire, often shown as 1× chunk). The "Recovery Read" column is wrong.

(The likely source of the mistake is conflating "number of chunks read" with "bytes read".)

**Fix:** Either relabel the column as "Recovery Read (in chunk-count)" with values K, or correct the numbers to ~1× data size for both EC rows.

---

### MEDIUM / LOW severity

#### J-9. `src/storage/blobdb.md` — Wrong description of WiscKey (claim it keeps an "in-memory hash table")

**Lines 105:**
```
- **WiscKey** (paper): simplest, separates all values, log-structured blob file, keeps in-memory hash table of key→blob offset (needs rebuild on crash).
```

**Problem:** The WiscKey paper (Lu et al., FAST '16) keeps the key → vLog-offset mapping **inside the LSM tree itself**, not in a separate in-memory hash table. The whole point is that the LSM is small (only keys + small pointers), so it can be cached and searched efficiently. An in-memory hash table that "needs rebuild on crash" would defeat the durability story.

**Source:** https://pages.cs.wisc.edu/~ll/papers/wisckey.pdf — "the LSM tree consists of keys and memory location of the values" (LSM-stored, not a separate in-memory hash).

---

#### J-10. `src/storage/distributed.md` — CockroachDB "64MB chunks" range size is outdated

**Line 296:**
```
RANGE["Ranges (64MB chunks)"]
```

**Problem:** CockroachDB's default range size has been **512 MiB** since v19.2 (was 64 MiB in pre-2019 versions). The diagram and text still say 64MB.

**Source:** https://www.cockroachlabs.com/glossary/distributed-db/range-shard — "In CockroachDB, a range is 512 MiB or smaller."

---

#### J-11. `src/web-servers/nginx.md` — Misleading `proxy_pass` comment

**Line 88:**
```nginx
location /api/ {
    proxy_pass http://backend;  # trailing slash strips /api/
    ...
}
```

**Problem:** The code shows `proxy_pass http://backend;` (no trailing slash). The inline comment says "trailing slash strips /api/". These contradict each other. As written, the request URI `/api/users` is forwarded to the backend as **`/api/users`** (no stripping). Stripping only happens with `proxy_pass http://backend/;` (with the trailing slash) → backend sees `/users`.

Note: the `interview-questions.md` (lines 8-9) describes the behavior correctly: "With trailing slash (`proxy_pass http://backend/`), the matched location prefix is stripped. Without it, the full URI is passed." So `nginx.md` contradicts its own interview-questions doc.

**Source:** https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_pass

---

#### J-12. `src/web-servers/nginx.md` — Deprecated `listen 443 ssl http2` form

**Line 46:**
```nginx
listen 443 ssl http2;
```

**Problem:** Since nginx 1.25.1 (released 2023-06-14), the `http2` parameter of the `listen` directive is deprecated. The current recommendation is:
```nginx
listen 443 ssl;
http2 on;
```

This is not strictly broken (it still works with a deprecation warning), but readers using modern nginx will see warnings.

**Source:** https://nginx.org/en/CHANGES (1.25.1 changelog); https://spinupwp.com/doc/deprecated-http2-directive-nginx/

---

#### J-13. `src/search/interview-questions.md` — Wrong stemming example "better → bett"

**Line 12:**
```
A: Stemming chops word endings (running → run, better → bett). Lemmatization uses vocabulary and morphology to find the root form (better → good, running → run).
```

**Problem:** "bett" is not a real stemming output for any of the standard stemmers:
- Porter stemmer leaves "better" unchanged → "better" (verified with NLTK: `PorterStemmer().stem("better")` returns "better").
- Lancaster stemmer reduces "better" → "bet".
- Snowball/Porter2 stemmer leaves "better" unchanged.

So "bett" is wrong for both Porter and Lancaster. Replace with `better → bet` (Lancaster) or remove the `better →` example entirely from the stemming side.

**Verification:**
```bash
python3 -c "from nltk.stem import PorterStemmer, LancasterStemmer; \
  print('Porter:', PorterStemmer().stem('better')); \
  print('Lancaster:', LancasterStemmer().stem('better'))"
# Porter: better   Lancaster: bet
```

---

#### J-14. `src/data-engineering/batch-processing.md` — PySpark code uses unaliased aggregation, then orderBy on a non-existent column

**Lines 44-52:**
```python
df = spark.read.csv("data.csv", header=True)
result = (df
    .filter(df.age > 25)
    .groupBy("city")
    .agg(avg("salary"), count("*"))
    .orderBy(desc("count"))
)
```

**Problem:** `agg(avg("salary"), count("*"))` produces columns named `avg(salary)` and `count(1)` (Spark auto-generates names from the expression). `orderBy(desc("count"))` then references a column called `count`, which **does not exist** — the actual column is `count(1)`. This raises `AnalysisException: Cannot resolve column name "count"`. Additionally, the imports for `avg`, `count`, `desc` are missing.

**Fix:**
```python
from pyspark.sql.functions import avg, count, desc
result = (df
    .filter(df.age > 25)
    .groupBy("city")
    .agg(avg("salary").alias("avg_salary"),
         count("*").alias("row_count"))
    .orderBy(desc("row_count"))
)
```

---

#### J-15. `src/storage/erasure-coding.md` — Placeholder `?` in code comment

**Line 129:**
```python
coded = G @ data  # [10, 20, 30, 40, 100, ?]
```

**Problem:** `?` is a placeholder/stub. The real-arithmetic answer is 300 (computed: 1·10 + 2·20 + 3·30 + 4·40 = 300). Should be filled in or the entire toy computation removed.

---

#### J-16. `src/storage/object-storage.md` — "eventual consistency for some operations (now strong)" still implies per-operation inconsistency

**Line 238:**
```
- Using S3 for database storage — S3 has high latency (50-200ms) and eventual consistency for some operations (now strong). Use RDS/EBS.
```

**Problem:** Self-contradictory phrasing. Since December 2020, S3 provides **strong read-after-write consistency for all operations** (PUT, GET, LIST, DELETE, object-tagging, ACL updates). The parenthetical "(now strong)" partially corrects the claim but the lead clause "eventual consistency for some operations" is no longer true. Better: "S3 has high latency (50-200ms) and is not designed for transactional database workloads. Since Dec 2020 S3 is strongly consistent for all operations, but latency and lack of partial-overwrite semantics still make it unsuitable as a database backend. Use RDS/EBS."

**Source:** https://aws.amazon.com/blogs/aws/amazon-s3-update-strong-read-after-write-consistency/ (Dec 1, 2020 announcement)

---

#### J-17. `src/search/elasticsearch.md` — Cluster diagram has unbalanced shard distribution

**Lines 5-15:**
```
Cluster
├── Node 1 (master)
│   ├── Shard 0 (primary)
│   └── Shard 1 (replica)
├── Node 2
│   ├── Shard 1 (primary)
│   └── Shard 0 (replica)
└── Node 3
    └── Shard 2 (primary)
```

**Problem:** Shard 2 has only a primary (on Node 3) and **no replica anywhere**, while Shards 0 and 1 each have primary+replica. With the default `number_of_replicas: 1`, Shard 2 should also have a replica (e.g., on Node 1 or Node 2). The diagram should show 6 lines (3 primaries + 3 replicas) distributed across the 3 nodes.

This is a LOW severity cosmetic issue but it visually teaches an inconsistent picture.

---

## Files confirmed clean

The following 16 files were deep-read and **no actionable findings** were recorded:

- `src/storage/hdd.md`
- `src/storage/ssd.md`
- `src/storage/nvmeof.md`
- `src/storage/block-storage.md`
- `src/storage/distributed.md` (other than J-10 — CockroachDB range size)
- `src/storage/ceph.md`
- `src/storage/object-storage.md` (other than J-16 / J-17)
- `src/storage/file-storage.md`
- `src/storage/overview.md`
- `src/storage/sstable.md`
- `src/storage/tiered-storage.md`
- `src/storage/wal.md`
- `src/storage/blobdb.md` (other than J-9)
- `src/search/README.md`
- `src/search/fundamentals.md`
- `src/search/elasticsearch.md` (other than J-17)
- `src/search/vector-search.md`
- `src/search/interview-questions.md` (other than J-13)
- `src/web-servers/README.md`
- `src/web-servers/nginx.md` (other than J-11, J-12)
- `src/web-servers/apache.md` (other than J-6)
- `src/web-servers/interview-questions.md`
- `src/data-engineering/README.md`
- `src/data-engineering/fundamentals.md`
- `src/data-engineering/batch-processing.md` (other than J-14)
- `src/data-engineering/stream-processing.md`
- `src/data-engineering/data-formats.md`
- `src/data-engineering/data-quality.md`
- `src/data-engineering/interview-questions.md`

(Counts overlap because some files had 1+ finding plus a clean main body; see the per-finding list above for the exact files with issues.)

## Methodology

- All 33 files (17 storage + 5 search + 4 web-servers + 7 data-engineering) were read end-to-end.
- The `already_fixed.md` skip-list was checked; none of the files in this chunk were on the list.
- Technical claims were verified via web search against official sources (NVM Express specification, httpd.apache.org, nginx.org, rocksdb.org, ceph.com, AWS blog, CockroachDB docs, WiscKey paper at pages.cs.wisc.edu).
- Python snippets were verified with `python3` / `nltk` where applicable (Porter/Lancaster stemmer output for `better`).
- No AI artifacts ("Wait,", "Hmm,", "Actually,", "Let me re-", etc.) were found via grep across all 33 files.
- No `TODO` / `FIXME` / `// fill in` / `pass` placeholders were found via grep, except the `?` stub noted in J-15.
