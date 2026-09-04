# Globally Unique ID Generation

Every row, order, message, and URL redirect needs an ID, so ID generation looks like a detail — until you shard. The moment a single database stops numbering every row, "let the database assign the next integer" stops working, and ID generation becomes a *system design decision* with its own failure modes: hotspots, clock skew, coordination overhead, and index-locality side effects that silently move your p99. It pairs with [Database Sharding](../../../dbms/advanced/database-sharding.md) (sequential IDs interact badly with range partitioning) and [Database Selection and Design](./database-design.md) (its "Distributed ID Generation" table is this page in depth).

## Why This Is Hard

Four requirements collide, and no scheme maximizes all of them:

1. **Uniqueness** — the easy part; every strategy below achieves it.
2. **Ordering** — many features secretly depend on it: "newest first", cursor pagination (`WHERE id > :last`), replication ordering. A globally *strict* total order implies a global serialization point — exactly what a sharded system exists to avoid. The practical compromise is **K-sortability**: IDs generated around the same time sort near each other, and any single generator's output is monotonic.
3. **Coordination-free generation** — if every ID mint needs a round trip to a central authority, that authority caps throughput and availability. Generating IDs where the write happens removes the bottleneck but forces uniqueness to come from *structure* (bits of time + bits of who-where) rather than a shared counter.
4. **Opacity** — sequential IDs leak business volume: `/orders/17` and `/orders/18` reveal your order rate and enable enumeration attacks.

### The Collision Math for Random IDs

If IDs are drawn uniformly at random from `n` bits, the birthday bound gives the probability of at least one collision among `k` generated IDs:

```text
p(collision) ≈ 1 − e^(−k² / 2N),  N = 2^n
```

Two calibration points worth memorizing:

| Random bits | 1% collision risk at | ~50% collision at |
|---|---|---|
| 64 (random 64-bit token) | ≈ 6 × 10⁸ IDs | ≈ 5 × 10⁹ IDs |
| 122 (UUIDv4 payload) | ≈ 3 × 10¹⁷ IDs | ≈ 2.7 × 10¹⁸ IDs |

So 64-bit *random* tokens are not "collision-proof" — at one billion IDs you're past the 1% mark; you need uniqueness checks or more bits. 122 random bits (UUIDv4) push the 50% point to ~2.7 × 10¹⁸ IDs, which is why "no coordination" is safe there. Counter-based schemes (auto-increment, Snowflake, hi-lo) have zero collision probability by construction — that's the guarantee you're trading the coordination or clock dependencies for.

### Sortability vs Randomness: the Index-Locality Link

IDs are usually the primary key, and primary keys in B-tree-organized tables *are* the index. Monotonic IDs append at the right edge of the index; random IDs scatter across the whole tree, hit full pages, force splits, and churn the buffer pool. This one mechanism explains the classic "we switched the PK to UUIDv4 and inserts got 5× slower" war story (worked problem 3) and is the core argument for time-ordered IDs (UUIDv7, ULID, Snowflake). The randomness that buys opacity and coordination-freedom costs index locality — a genuine trade, not a free lunch.

## Strategy Catalog

### 1. Database Auto-Increment

Each table has a server-side counter. Mechanics are trivial; the failure modes are the interview content:

- **Hotspot on the right edge.** Every insert mutates the same index leaf. Fine on one node; a *hot range* under range-based sharding, because shard N+1 gets nothing until shard N's range fills. Sequential keys as a shard key is the textbook bad choice ([Database Sharding → Common Pitfalls](../../../dbms/advanced/database-sharding.md)).
- **Gaps are guaranteed, not a bug.** PostgreSQL documents this directly: because `serial` types are implemented using sequences, "there may be 'holes' or gaps in the sequence of values which appears in the column, even if no rows are ever deleted", and `nextval`/`setval` calls "are never rolled back" — a gapless counter would require table-level locking that's "much more expensive than sequence objects".
- **The MySQL 8.0 persistence change.** Before 8.0, InnoDB re-derived the counter from `SELECT MAX(ai_col)` at startup, so a restart after a rollback could *reuse* allocated values. In 8.0 "the current maximum auto-increment counter value is written to the redo log each time it changes and saved to the data dictionary on each checkpoint", making it persistent across restarts. Note what this does *not* promise: 8.0 prevents reuse, but interleaved lock mode (now the default, `innodb_autoinc_lock_mode=2`) means concurrent statements can receive values out of order — auto-increment is unique, not gapless, not ordered *between* concurrent transactions.
- **Per-shard offsets.** `auto_increment_increment = 2` with offset 1 on shard A and offset 2 on shard B interleaves odd/even IDs. The manual describes these variables as "intended for use with circular (source-to-source) replication"; repurposing them for sharding inherits their ceiling — range 1–65,535, no story for adding a third shard, zero global ordering.

**Verdict**: correct default for a single writer; the first shard boundary or the first privacy requirement kills it.

### 2. Central Ticket Server

Flickr's 2008 design: one small database hands out IDs from `AUTO_INCREMENT`, and *only* the ticket server ever allocates IDs. To amortize round trips, a client reads a *chunk* — "give me the next 100" — and mints locally from it. That single trick raises the ID service's capacity a hundredfold, because the expensive operation (an insert into the ticket table) happens once per chunk, not once per ID.

The HA story is the lesson. One ticket server is a SPOF that takes down every write in the company. Flickr's answer was two ticket servers, one generating even IDs and one odd — you *tolerate gaps* to survive a failure. Any scheme that buys availability with "skip some values" follows this pattern. The remaining limits are classic single-node ones: cross-datacenter latency, and a write rate that — even chunked — eventually becomes the bottleneck of an otherwise shardable system.

### 3. Range/Block Allocation (Hi-Lo)

Hi-lo generalizes chunking into a client library: a client grabs a *hi* value from the coordinator and mints IDs in `[lo, lo + hi)` locally; the coordinator's counter moves once per block.

- **Amortization**: one DB round trip per `hi` IDs — a block of 1000 turns 10k IDs/s into 10 allocs/s.
- **Gaps on crash**: a client that dies holding 700 unused slots loses them permanently. Every block-allocator accepts this; handing back unused ranges reintroduces coordination.
- **Ordering becomes block-grained.** Blocks are allocated over time, so IDs are *coarsely* monotonic — but a client holding block 50 can emit IDs after another client holding block 51 started. Per-event ordering must come from another mechanism (a timestamp or version column), not from hi-lo IDs.
- **Shard interaction**: IDs within a block are sequential, so range-sharding by them recreates the auto-increment hotspot unless you interleave (e.g., seed each shard's blocks with the shard number).

### 4. UUIDs (RFC 9562) and ULID

UUIDs generate coordination-free from any node. The versions differ in what fills the 128 bits:

| Version | Content | Sortable? | Notes |
|---|---|---|---|
| v1 | 60-bit Gregorian time + clock seq + node (MAC) | Yes (layout scrambled for sort) | MAC leaks identity/privacy |
| v4 | 122 random bits | No | The "random UUID"; opaque but index-hostile |
| v6 | v1 fields reordered for lexicographic sort | Yes | Compatibility shim for v1-era systems |
| v7 | 48-bit Unix ms + 74 configurable bits | Yes (K-sortable) | The recommended default |

**UUIDv7** embeds the Unix timestamp in milliseconds, then lets implementations fill the remaining 74 bits ("rand_a" + "rand_b") with randomness — or, to "guarantee additional monotonicity within a millisecond", with "an OPTIONAL sub-millisecond timestamp fraction" and/or "an optional counter", then randomness. That counter is what makes v7 usable at microsecond-scale generation rates: within one millisecond you increment instead of re-sampling, so equal-timestamp IDs still sort.

The RFC is explicit about *why* time-ordering matters, and it's the index-locality argument: random UUIDs "have poor database-index locality", while "time-ordered monotonic UUIDs benefit from greater database-index locality because the new values are near each other in the index", with real-world differences that "can be one order of magnitude or more."

**ULID** is the 128-bit sibling: 48 bits of millisecond timestamp plus 80 bits of randomness, encoded in **Crockford Base32** (alphabet `0123456789ABCDEFGHJKMNPQRSTVWXYZ`, excluding I, L, O, U to avoid transcription confusion) — 26 characters whose lexicographic order *is* time order, in any system that treats the ID as an opaque string. ULID also offers an optional monotonic mode: within the same millisecond, increment the previous ID's random part instead of re-sampling. Compared to UUIDv7 (same 48-bit timestamp idea), ULID trades RFC standardization for a fixed, readable encoding.

### 5. Snowflake

Twitter's 2010 design packs a 64-bit signed integer with the bits that matter:

```text
sign(1) | timestamp ms since custom epoch (41) | datacenter (5) | worker (5) | sequence (12)
```

The numbers come straight from the original `IdWorker`: `workerIdBits = 5`, `datacenterIdBits = 5`, `sequenceBits = 12`, epoch `1288834974657` (Nov 2010). The mechanics of `nextId()`:

- Same millisecond → increment `sequence`; 12 bits give **4096 IDs/ms/worker (~4.1M/s)**. Overflowing the sequence *stalls* the generator to the next millisecond (`tilNextMillis`), it does not spill into another worker's space.
- New millisecond → reset sequence to 0.
- **Worker IDs are assigned, not chosen.** The original `SnowflakeServer` claims an ID through ZooKeeper (with checks like "Failed to claim worker id. Gonna wait a bit and retry..."). Any coordination service works (etcd is today's common choice); the requirement is that two live workers never share an ID, because worker ID + timestamp + sequence *is* the uniqueness argument. Handing out static IDs at deploy time is the zero-dependency fallback.
- **Clock skew is the failure mode.** The 2010 code refuses to generate: "Clock moved backwards. Refusing to generate id for %d milliseconds." Every production descendant has to pick a policy — reject and back off, wait for the clock to catch up, or keep minting into the (now skewed) timestamp and accept small disorder. NTP makes this concrete: *slewed* corrections are harmless, but a *stepped* correction (or VM migration, or a leap-smear edge) can move `System.currentTimeMillis()` backwards, which violates the generator's core assumption. Defensive variants keep a sanity margin on the last timestamp, use a monotonic clock source, or absorb small negative deltas with sequence bits.
- 41 timestamp bits ≈ 69 years from the chosen epoch — pick the epoch once, document it, and note that a truncation/rollover decision is decades out but *not* optional.

**Discord's production lessons (2023)** verify the throughput argument end-to-end. Every message ID is a Snowflake, "making it chronologically sortable", and messages are partitioned by channel plus a bucket — "a static time window". The pitfall they documented is not generation but *placement*: "One channel and bucket pair received a large amount of traffic" became a hot partition that "frequently affected latency across our entire database cluster". Time-ordered IDs concentrate new writes by construction — if you also *cluster* by those IDs, you concentrate them twice. The fix is upstream routing controls, not a different ID.

### 6. MongoDB ObjectId

The 12-byte client-generatable ID: "A 4-byte timestamp... measured in seconds since the Unix epoch. A 5-byte random value generated once per client-side process... A 3-byte incrementing counter per client-side process, initialized to a random value." It's a Snowflake with different dials: only *second* granularity (so "roughly sortable", ties are normal), no coordination service (the 5-byte process-random value substitutes for a registry), and big-endian field ordering chosen precisely so the timestamp sorts. Interview takeaway: ObjectId shows the honest floor of "sortable" — second-grained, monotonic only within one process — and that it's sufficient for its use case.

### 7. Firebase Push IDs

The most client-side extreme of the spectrum: offline-capable clients mint ordered IDs with no server contact. The SDK's `nextPushId` produces a 20-character key: the first 8 characters encode a millisecond timestamp in an ordered alphabet, followed by "72-bits of random data after the timestamp so that IDs won't collide with other clients' IDs". Its documented properties are the design in miniature: "They sort *lexicographically* (so the timestamp is converted to characters that will sort properly)" and "They're monotonically increasing. Even if you generate more than one in the same timestamp, the latter ones will sort after the former ones" — implemented by *incrementing* the previous random suffix rather than re-sampling. One caveat: the timestamp is encoded in an ordered but non-obvious alphabet — obfuscated against casual reading, but recoverable given the format's fixed epoch. Treat it as *encoded*, not secret.

## Selection Framework

Answer these in order; each decision eliminates a branch:

```text
1. Do you need global strict ordering?        → almost never true; if truly yes, you need a
                                                serialized writer (ticket server / one DB counter)
2. K-sortable enough? (cursors, "recent" views) → time-ordered: Snowflake (compact, 8B) or
                                                UUIDv7/ULID (opaque, 16B/26ch)
3. Order irrelevant, opacity matters           → UUIDv4 / random token + a separate ordered column
4. Max throughput, zero infrastructure         → client-side (v7, ULID, ObjectId, push IDs)
5. Simplest thing that works, single DB        → auto-increment; revisit before sharding
```

- **Ordering**: distinguish per-entity ordering (fine with any scheme + a `created_at`/version column) from global ordering (requires serialization). Most "we need sortable IDs" requirements are really "we need *approximate* recency" — K-sortable is the right tool.
- **Coordination-freedom**: generation must be O(1) local work. Snowflake needs worker-ID assignment once per boot (ZooKeeper/etcd/static); hi-lo contacts the coordinator once per block; UUIDs need nothing, ever.
- **Opacity/enumeration**: sequential IDs in public URLs are a security bug, not a style issue — `/orders/17` invites IDOR and competitor scraping. Either use non-sequential IDs in URLs, or keep sequences internal and expose an independent random token (which you can rotate without migrating data).
- **Shard-key interaction**: the ID is a candidate shard key, and its structure matters twice. A time-ordered ID range-sharded by value recreates the hot-range problem (Discord's hot partitions); hash-sharded, a time-ordered ID is fine, because sortability and routing are decoupled. Decide ID scheme and shard key *together*.
- **Embedded time**: helps debugging (IDs self-describe their creation time), TTL policies, and backup archaeology; costs some privacy (volume/timing leaks) and adds clock dependence (41-bit horizon, NTP step-backs). If clocks are untrusted in your environment, lean toward random or hybrid-clock-based generation ([Hybrid Logical Clocks](../../../distributed/advanced/hybrid-logical-clocks.md) shows how to make "time" that can't step backwards).

## Interview Problems

### Problem 1 — URL shortener IDs

Design a shortener at 100M new URLs/month. The short-code *is* an ID: 100M/month ≈ 38/s, trivial throughput, so the interesting constraints are length and opacity. With a 62-char alphabet, 7 characters give 62⁷ ≈ 3.5 × 10¹². Options: (a) a global counter + base62 encoding — compact and retry-free, but codes are enumerable and the counter is a SPOF (acceptable: one tiny service, chunked allocation); (b) random 7-char codes with a uniqueness check on insert — per-insert collision rate ≈ k/N where k is live codes, so at 100M live URLs it's ~0.003% per insert (~1,400 cumulative retries over that history) — cheap, as long as the retry loop exists; (c) random 6-char codes (62⁶ ≈ 5.7 × 10¹⁰) run the same scale at ~0.2% per insert and degrade as the table fills — workable, wrong trend line. Best practice: counter-based internal ID, base62-encoded, *plus* treat codes as semi-public — or random codes if enumeration of the code space itself must be useless. Full design in [URL Shortener](../real-world/url-shortener.md).

### Problem 2 — Ticket IDs at 50k/s with per-ms ordering

A ticketing platform sells 50,000 tickets/second at flash-sale open, and support tooling requires "tickets created in the same millisecond are ordered consistently". Budget first: 50k/s = 50 IDs/ms — one Snowflake worker with the standard 12-bit sequence (4096/ms ≈ 4.1M/s) covers it 80× over, and 41 timestamp bits cover decades. So this is *not* a throughput problem; it's a correctness-under-failure problem: (1) HA means ≥2 generators, so per-worker monotonicity no longer gives a global order — two workers can emit out-of-order IDs in the same ms; the stated requirement is satisfiable by K-sortability + a tiebreaker, and you should say so explicitly; (2) worker IDs from ZooKeeper/etcd with fencing on reassignment, so a paused-then-revived worker can't mint duplicates (see [Database Sharding → Shard Metadata Correctness](../../../dbms/advanced/database-sharding.md) for the fencing pattern); (3) NTP discipline: prefer slewing, alert on step corrections, and decide the negative-delta policy *before* the sale; (4) opacity: 8-byte Snowflakes in emails/URLs are not sequentially guessable across workers (only within one), which may or may not meet the threat model — if it doesn't, pair each Snowflake with a random token.

### Problem 3 — "Our UUIDv4 primary key made inserts 5× slower than serial. Why?"

The mechanism is index locality. With a serial key, every insert appends to the right-most index page: the page is warm in the buffer pool, rarely full, and WAL writes are localized. With UUIDv4, the key is uniform over 122 bits, so each insert targets a *random* B-tree page: (1) pages must be faulted in — buffer-pool churn makes the working set effectively "the whole index"; (2) the target page is usually full → a page split, copying ~half its rows and dropping fill factor toward 50–70%, so the index grows larger and deeper; (3) every split dirties more pages → more WAL, more checkpoints, more I/O. The RFC's estimate that the locality difference "can be one order of magnitude or more" is exactly this. Fixes, in order of preference: UUIDv7/ULID (keep the opaque client-generated ID, restore locality); or a serial internal PK with the UUID as a *secondary* unique key for external references; or cluster the table by `created_at` instead of the random key. Residual risk: v7 IDs cluster by millisecond *as generated* — under heavy concurrency from many nodes, timestamps interleave near-perfectly but not strictly, which is still fine for locality.

## Key Takeaways

- Uniqueness is cheap; *order* is the expensive property. Strict global order requires serialization; K-sortability is the compromise that composes with sharding.
- Random 64-bit IDs are *not* collision-proof (birthday bound: ~1% risk near 6 × 10⁸ IDs). 122 random bits are. Counters have zero collision risk but bring coordination, gaps, or clock dependence.
- IDs are primary keys, and primary keys are index structure: time-ordered IDs append, random IDs split pages. This is why UUIDv7/ULID/Snowflake beat v4 for insert-heavy tables by up to an order of magnitude.
- Every generator's failure mode is predictable: auto-increment → hotspots and shard-key conflicts; ticket server → SPOF (mitigated by chunking + even/odd); hi-lo → block-grained order and crash gaps; Snowflake → worker-ID assignment and clock steps; ObjectId → second-grained order; push IDs → none, at the cost of a fixed epoch.
- Decide the ID scheme and the shard key together; a time-ordered ID used as a range shard key recreates the hotspot you paid to remove.

## References

- [RFC 9562: UUIDs (Universally Unique IDentifiers)](https://www.rfc-editor.org/rfc/rfc9562.html) — version layouts, UUIDv7 74-bit sub-fields and monotonicity methods, index-locality rationale.
- [PostgreSQL: CREATE SEQUENCE](https://www.postgresql.org/docs/current/sql-createsequence.html) — non-transactional `nextval`/`setval`, gapless-assignment warning, sequence `CACHE` out-of-order behavior.
- [PostgreSQL: Numeric Types (`serial`)](https://www.postgresql.org/docs/current/datatype-numeric.html) — "holes or gaps" note for sequence-backed columns.
- [MySQL 8.0 Reference Manual: AUTO_INCREMENT Handling in InnoDB](https://dev.mysql.com/doc/refman/8.0/en/innodb-auto-increment-handling.html) — 8.0 counter persistence via redo log/data dictionary, 5.7-vs-8.0 reuse behavior, `innodb_autoinc_lock_mode` defaults. *(Fetched and content-verified; the docs site returns 403 to automated probes but serves plain HTTP clients.)*
- [MySQL 8.0 Reference Manual: Replication Source Options](https://dev.mysql.com/doc/refman/8.0/en/replication-options-source.html) — `auto_increment_increment`/`auto_increment_offset` semantics and limits. *(Same fetch note.)*
- Twitter Snowflake (2010 release, source code): [`IdWorker.scala`](https://github.com/twitter/snowflake/blob/snowflake-2010/src/main/scala/com/twitter/service/snowflake/IdWorker.scala) — bit layout, epoch, sequence mask, clock-moved-backwards handling; [`SnowflakeServer.scala`](https://github.com/twitter/snowflake/blob/snowflake-2010/src/main/scala/com/twitter/service/snowflake/SnowflakeServer.scala) — ZooKeeper worker-ID claiming.
- [Discord, "How Discord Stores Trillions of Messages" (2023)](https://discord.com/blog/how-discord-stores-trillions-of-messages) — Snowflake IDs, channel+time-bucket partitioning, hot-partition case study.
- [MongoDB Manual: ObjectId](https://www.mongodb.com/docs/manual/reference/method/ObjectId/) — 4-byte timestamp + 5-byte process random + 3-byte counter layout.
- [Firebase Realtime Database: Save Data](https://firebase.google.com/docs/database/admin/save-data) — `push()` unique-and-chronological keys; [firebase-js-sdk `NextPushId.ts`](https://github.com/firebase/firebase-js-sdk/blob/main/packages/database/src/core/util/NextPushId.ts) — 8-char timestamp + 72-bit random, lexicographic ordering, same-ms increment.
- [ULID spec](https://github.com/ulid/spec) — 48-bit ms + 80-bit random, Crockford Base32, lexicographic sortability, optional monotonicity.

*(The Flickr ticket-server design (2008) is described in the ticket-server section above from the engineering literature's standard account; the original post is no longer retrievable at its source, so it is not listed as a verified reference.)*

## Cross-References

- [Database Design](./database-design.md) — database selection, sharding strategies, and the Distributed ID Generation table
- [URL Shortener](../real-world/url-shortener.md) — worked design using short-code IDs
- [Database Sharding](../../../dbms/advanced/database-sharding.md) — shard keys, hot ranges, fencing
- [Hybrid Logical Clocks](../../../distributed/advanced/hybrid-logical-clocks.md) — timestamp generation that tolerates skew
- [Idempotency](../../../backend/patterns/idempotency.md) — client-supplied keys and safe retries
- [Caching Strategy](./caching-strategy.md) — where generated IDs interact with cache-aside invalidation
