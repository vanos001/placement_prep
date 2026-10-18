# Auto-Increment vs UUIDv4 vs UUIDv7 vs Snowflake: Who Generates the ID?

## Overview

An identifier looks like a type choice, but it is really a decision about **where the ID comes from, what the index does to every insert, and what the ID tells strangers**. Auto-increment sequences issue dense, ordered integers from a single authority — perfect for the B-tree, terrible for privacy and distribution. UUIDv4 issues 122 random bits from anywhere — perfect for distribution, hostile to index locality. Time-ordered UUIDv7/ULID and Snowflake-style coordinator IDs try to have both: locality from a timestamp, distribution from per-node entropy or an allocator, at the price of leaking creation time and, in Snowflake's case, needing worker-ID coordination.

This page runs the [handbook framework](./index.md) over the four. The preview: **auto-increment wins on index health and storage, and loses on coordination, sharding, and information leakage; random UUIDs win on offline generation and opacity, and lose on index locality in ways that get worse with every secondary index; time-ordered IDs are the compromise the industry converged on — with clock, monotonicity, and leakage caveats**. The edge cases — sharded sequence ranges, UUIDv4 fragmentation math, monotonicity within a millisecond — are where the default advice ("just use UUIDs") quietly breaks.

## Step 1: The Problem and Its Constraints

The workload: every inserted row needs a unique key; inserts arrive at thousands per second across one or many nodes; the key is stored in the primary key and copied into every secondary index (in clustered engines — see [clustered vs nonclustered](../../dbms/indexing/clustered-vs-nonclustered.md)). Constraints:

- **Insert pattern.** Monotonic keys append to the rightmost B-tree page — cheap, cache-hot, high fill factor. Random keys land anywhere — page splits, cold buffers, fragmented pages (the mechanics in [B+tree](../../dbms/indexing/b-plus-tree.md)).
- **Who may generate.** A single database can serialize allocation; twenty application nodes behind load balancers cannot all "ask the database" without making it a hot path — or can they? Latency and availability budgets decide.
- **Offline generation.** Mobile clients, event-sourced systems, and idempotency keys need IDs minted before any server sees the record.
- **What the ID reveals.** Order numbers that count up leak business volume to competitors; sequential IDs enable enumeration attacks; timestamps in IDs leak activity patterns. Privacy is a design constraint, not an afterthought.
- **Storage budget.** The key is stored once in the table and once per secondary index; in InnoDB, every secondary index entry carries the primary key (see [MySQL InnoDB internals](../../dbms/internals/mysql-innodb-internals.md)).

## Step 2: The Mechanisms

### Option 1: Auto-increment (database sequence)

- **Allocation is serialized at the issuing node.** The sequence is a counter the database increments under its own concurrency control: unique by construction, dense, ordered. The B-tree loves it — every insert is an append to the hottest page.
- **The coordination cost is the database itself.** Every insert must reach the issuing node; sharding means each shard runs its own sequence, and global uniqueness needs range blocks or interleaved steps (Step 5). The database becomes the ID bottleneck precisely at the scale where you sharded to escape it.
- **Storage is minimal** (8-byte bigint), which multiplies across every index in a clustered layout.
- **Leakage is structural.** `/orders/48153` tells a competitor you processed 48,152 orders; sequential IDs make enumeration trivial; even `nextval` gaps are information.

### Option 2: UUIDv4 — random

- **Generation needs nobody.** 122 random bits from any node's CSPRNG; collision probability at realistic scales is negligible. Uniqueness no longer depends on coordination — this is the property that made UUIDs the default for distributed systems and offline-first clients.
- **Index hostility is the price.** Random 16-byte keys insert at uniformly distributed positions: each insert can split a page, pages fill to ~50–70% instead of 90%+, the working set of "hot" pages becomes the whole index, and buffer-pool hit rates fall. With InnoDB's clustered layout, the fragmentation multiplies across every secondary index carrying that key.
- **Storage is 16 bytes binary — or worse.** Stored as `CHAR(36)` with hyphens (plus collation overhead) it is nearly triple; the fix is `BINARY(16)` or engine-native UUID types (PostgreSQL's `uuid`), which teams omit surprisingly often.
- **Leaks nothing** — no time, no volume, no source. The opacity is a feature.

### Option 3: UUIDv7 / ULID — time-ordered

- **Structure carries the locality.** UUIDv7 ([RFC 9562](https://datatracker.ietf.org/doc/html/rfc9562)) embeds a 48-bit Unix millisecond timestamp in the leading bits, with randomness in the remainder; ULID is the same idea (Crockford-base32 encoded). Leading timestamps sort like auto-increment: inserts append to the hot page, and IDs encode creation order — useful for debugging and cursor pagination.
- **Distribution without an allocator.** Any node generates; uniqueness comes from the random bits, sortability from the timestamp. No coordinator, no worker registry.
- **The monotonicity caveat.** Within the same millisecond, ordering of random-suffix IDs is not guaranteed; RFC 9562 describes monotonicity methods (incrementing the random portion when the timestamp repeats, with counter-roll safeguards), but implementations differ — "UUIDv7 is monotonic" is an implementation claim, not a spec guarantee.
- **The leakage caveat.** Creation time is in the clear. For some records that is harmless; for others (user activity, outage forensics visible to third parties) it is a disclosure decision to make consciously.

### Option 4: Snowflake-style coordinator IDs

- **Structure: timestamp + worker ID + per-node sequence.** Twitter's Snowflake (2010) minted 64-bit IDs — milliseconds since a custom epoch, a worker ID assigned by a coordination service, and a per-millisecond sequence. Sorting is near-exact; IDs are half the storage of a UUID; per-node throughput is bounded by the sequence bits.
- **Coordination moves to worker-ID assignment.** Allocation itself is local and lock-free; the coordination cost is paid once per node at startup (ZooKeeper historically; today often a lease-based allocator — see [consensus and leases](../connection-atlas/consensus-leases.md)). The trade versus UUIDv7: more uniqueness bits per node, tighter ordering, explicit infrastructure.
- **Clock sensitivity is the tax.** A clock step backward (NTP correction, VM migration) risks duplicate timestamps and sequence collisions; production implementations either wait out the skew or accept a bounded reordering. Snowflake APIs are famously strict about wall-clock dependence.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Auto-increment | UUIDv4 | UUIDv7/ULID | Snowflake-style |
|----------|----------------|--------|-------------|-----------------|
| Index locality | Optimal (append) | Worst (random) | Near-optimal (time-ordered) | Near-optimal |
| Storage per ID | 8 bytes | 16 bytes binary / 36 as text | 16 bytes | 8 bytes |
| Generation authority | The database | Any node, offline | Any node, offline | Any node with worker ID |
| Coordination requirement | The issuing DB per insert | None | None | Worker-ID service at startup; clock discipline |
| Ordering guarantee | Global, exact | None | Time-approximate; per-ms ordering implementation-dependent | Time-exact within node; global within clock skew |
| Leakage | Volume, rate, enumerability | Nothing | Creation time | Creation time + fleet topology hints |
| Sharding story | Range blocks or interleaved steps; resharding pain | Free | Free | Worker registry is the sharding story |
| Signature failure | Bottleneck + enumeration | Page splits, index bloat, buffer misses | Monotonicity assumptions; clock-suffix collisions | Clock skew duplicates; worker-ID exhaustion/misassignment |

**The secondary-index multiplier is the hidden column.** In clustered engines the primary key is copied into every secondary index entry, so a key choice is not one B-tree decision but N decisions — the fragmentation tax of UUIDv4 is paid on every index the table has. Row-organized engines (PostgreSQL heap + separate indexes) pay a smaller, still nonzero version of the same bill.

## Step 4: When Each Wins

**Auto-increment wins** when: a single issuing database is acceptable (the common monolith); storage and index health dominate; IDs are never exposed to users without an indirection layer; and no sharding is on the roadmap. It remains the correct default for the systems where it was always correct — the failure mode is applying it past its coordination ceiling.

**UUIDv4 wins** when: IDs are minted offline or pre-assignment is required (idempotency keys, event-sourced commands); opacity matters more than locality; the table is insert-light or the index cost is acceptable; or the ID is primarily an opaque handle (session tokens, object IDs) rather than a clustered key.

**UUIDv7/ULID wins** when: distributed generation and index locality are both required — the standard modern answer for new distributed tables; time-sortability is wanted for cursor pagination; and time leakage is acceptable. Pair with binary storage and an engine that keeps 16-byte keys cheap.

**Snowflake-style wins** when: 8-byte IDs matter at fleet scale (every byte × every index × every replication stream); near-exact global ordering is needed; and operating a worker-ID allocator and clock discipline is within the team's operational budget. It is the ID of very large sharded fleets — and a component most teams should not build for the first time themselves.

## Step 5: Edge Cases and Counterexamples

- **Sharded auto-increment interleaves or blocks.** Give each of N shards a sequence with increment N (shard k starts at k) and global uniqueness holds — but IDs are no longer sortable by creation time globally, gaps encode the shard count, and adding a shard means renumbering the step (a migration under load). Range blocks (shard 1 gets 1–1M) preserve density but turn resharding into an allocation exercise — see [online resharding](../../dbms/advanced/online-resharding.md). The "simple" option quietly became a distributed allocator.
- **UUIDv4 fragmentation is arithmetic, not folklore.** Random keys mean each insert's target page is unpredictable; pages split at ~50% fill; a 16-byte key with fill 60% versus 95% inflates the index by roughly 1.5×, and every lookup descends one more level sooner. On a hot OLTP table with five secondary indexes in InnoDB, that is five inflated trees and a measurably larger buffer pool — the "just use UUIDs" default has a quantified bill.
- **Monotonic hot spots in time-ordered IDs.** Locality is a benefit for the index and a hazard for the *shard*: if the ID's timestamp is the sharding key prefix, the current millisecond's writes land on one shard — the hot-partition problem (see [partitioning](../../distributed/partitioning/README.md) and [consistent hashing](../../distributed/partitioning/consistent-hashing.md)). Hash on the ID, or on a separate key, when distributing by ID.
- **Time-order leakage is bidirectional.** UUIDv7 reveals when a record was created — mostly harmless, occasionally sensitive (the timestamp of a support ticket in a URL reveals activity patterns). The inverse edge: opaque UUIDv4 in public URLs *prevents* enumeration, which is itself a security control (IDOR mitigation — see [web security](../../security/web-security.md)); switching to sortable IDs for "developer ergonomics" can silently remove that control.
- **Clock skew and the Snowflake duplicate window.** Two nodes with worker IDs and skewing clocks can mint the same (timestamp, worker, sequence) tuple if assignment or clock discipline fails. Production mitigations: monotonic-clock assertions, wait-for-skew on backward steps, and lease-based worker IDs that expire — the failure mode is silent duplication, which no index will warn you about.
- **The text-storage trap.** Storing UUIDs as `CHAR(36)`/`VARCHAR` with default collations inflates every index and invites case/hyphen inconsistencies; the fix (`BINARY(16)`, `uuid` types) is unglamorous and doubles the effective win of any ID-size argument.

## Step 6: Decision Framework

1. **Can a single database issue every ID without becoming the bottleneck?** Yes → auto-increment; it is the healthiest index and the smallest storage.
2. **Must any node mint IDs offline, before any server sees the record?** Yes → UUIDv4 (opacity priority) or UUIDv7 (sortability priority).
3. **Is the ID the clustered key of a hot, write-heavy table?** Yes → never random v4; choose monotonic-family (auto-increment, v7, Snowflake) or accept the quantified fragmentation bill.
4. **Is the ID exposed in URLs or APIs?** Then leakage is a security decision: opaque IDs for enumeration resistance, sortable IDs only where time disclosure is acceptable (or behind opaque public handles mapped to internal IDs).
5. **Is the fleet large enough that 8 vs 16 bytes matters everywhere?** Yes → Snowflake-style, if worker-ID coordination and clock discipline are operationally acceptable; otherwise UUIDv7 with binary storage.
6. **Default in doubt:** UUIDv7 stored as 16 binary bytes, hashed (never used directly) as a sharding key — the modern distributed default — unless a single-database system's simplicity argues for auto-increment.

## Interview Questions

1. **Why do random UUIDs degrade B-tree indexes, mechanically?** Every insert targets a uniformly random page: page splits fire constantly, fill factor drops to ~50–70%, the "hot page" working set becomes the whole index, and buffer-pool hit rates fall. In clustered engines the same key is copied into every secondary index, multiplying the damage; the fix family is time-ordered keys or hash-sharded tables.
2. **What exactly does an auto-increment ID leak, and why is it a security issue beyond business intelligence?** Volume and rate (competitor metrics), enumerability (sequential IDs invite IDOR and scraping), and activity gaps. Enumeration is the security core: an attacker walks `/orders/47000..48000` without any ID guessing. Mitigation is an indirection layer (opaque public handles) rather than hoping endpoints check authorization perfectly.
3. **Your team shards a table and keeps auto-increment IDs with per-shard sequences using step = shard count. What breaks?** Global uniqueness holds, but global ordering by ID no longer reflects creation time across shards, gaps encode topology, and resharding (adding a shard) requires changing every sequence's step — a live migration. The "no coordination" choice acquired coordination at the schema level.
4. **Why does Snowflake need a worker-ID service at all if generation is local?** The ID embeds a worker ID to guarantee cross-node uniqueness within the same millisecond; uniqueness therefore depends on assignment correctness. That is the coordination — paid once per node at startup rather than per ID, traded against UUIDv7's random bits, which buy uniqueness without any registry but with less ordering precision and 2× storage.
5. **A competitor estimates your daily order volume from your public order IDs. Which ID properties allowed that, and what are two different fixes?** The IDs were monotonic and exposed. Fix one: keep monotonic IDs internally and expose opaque random handles at the API boundary (enumeration resistance, no schema change). Fix two: switch generation to random or time-ordered-with-random-suffix IDs — accepting index-locality costs, which is why fix one is usually cheaper.

## Key Takeaways

- The ID decision is three decisions in one: who coordinates generation, how the B-tree experiences inserts, and what strangers learn from the value. No option wins all three.
- Auto-increment: best index, smallest storage, worst coordination and leakage — correct inside its single-writer ceiling.
- UUIDv4: perfect distribution and opacity, quantified index damage — correct for offline generation and opaque handles, wrong as a hot clustered key.
- UUIDv7/ULID: the modern distributed compromise — locality from a timestamp, distribution from randomness, caveats on monotonicity and time leakage.
- Snowflake-style: fleet-scale efficiency with real infrastructure (worker registry, clock discipline); build it when the bytes matter enough, buy it otherwise.
- The key is copied into every secondary index in clustered engines — one ID decision is N index decisions, which is where all the arithmetic above multiplies.

## Cross-References

- [B+Tree](../../dbms/indexing/b-plus-tree.md) — page splits, fill factor, and the mechanics behind locality.
- [Clustered vs Nonclustered](../../dbms/indexing/clustered-vs-nonclustered.md) — why the primary key rides inside every secondary index.
- [MySQL InnoDB Internals](../../dbms/internals/mysql-innodb-internals.md) — the clustered-layout cost model concretely.
- [Database Sharding](../../dbms/advanced/database-sharding.md) and [Sharding](../../dbms/distributed/sharding.md) — the distribution constraints ID choice interacts with.
- [Online Resharding](../../dbms/advanced/online-resharding.md) — the migration pain of sharded sequence schemes.
- [Partitioning](../../distributed/partitioning/README.md) and [Consistent Hashing](../../distributed/partitioning/consistent-hashing.md) — distributing by ID without hot spots.
- [Database Indexes: Follow-up Tree](../followup-tree/database-indexes.md) — escalating chain on the index mechanics here.
- [URL Shortener: Follow-up Tree](../followup-tree/url-shortener.md) — ID generation as a system-design exercise.
- [DB Indexes and Data Structures: Connection Atlas](../connection-atlas/db-indexes-data-structures.md) — the dependency web of key choice to engine behavior.
- [Consensus and Leases: Connection Atlas](../connection-atlas/consensus-leases.md) — the lease-based worker assignment this page's coordination relies on.
- [Web Security](../../security/web-security.md) — enumeration and IDOR, the security half of ID opacity.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
