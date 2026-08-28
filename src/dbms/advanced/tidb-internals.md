# TiDB Internals: TiKV, PD, and the Multi-Raft Storage Stack

The [architecture overview](./tidb.md) covers what the TiDB layers are. This page goes one level down: how a SQL row becomes a byte range inside TiKV, where MVCC versions and Percolator locks physically live, how PD batches 47+18-bit timestamps, how the coprocessor pushes work into storage, and how PD's scheduler machinery keeps hundreds of thousands of regions even. The design here is a good interview deep-cut because TiDB is the cleanest open example of a *separation of compute and state*: the SQL layer holds no durable state, and every guarantee lives in TiKV plus PD.

## One Write, End to End

```text
MySQL client
   |  MySQL wire protocol
   v
TiDB server (stateless):  parse -> plan -> DistSQL scheduler
   |  prewrite / commit RPCs (Percolator 2PC, start_ts + commit_ts from PD)
   v
TiKV raftstore (per-region):  leader appends Raft log
   |  Raft replication: 2 followers (quorum) + optional learners
   v
apply: RocksDB column families -> data persisted, MVCC versions visible

PD (3-5 nodes, Raft):  hands out TSOs, tracks region metadata,
   issues split / merge / move-peer / transfer-leader operators
```

Three things make this different from a classic shared-nothing sharded MySQL:

1. A TiDB node can be killed and replaced with no data movement — it holds no data, only session state. Scale-out is a load-balancer change.
2. A single write to a wide row, a secondary index, and a statistics counter may hit three *different regions*, so the Percolator two-phase protocol — not a local commit — is the default path (see [Multi-Raft](../../distributed/consensus/multi-raft.md) for why consensus groups are per-range).
3. Every timestamp in the system comes from one component, PD. That single fact shapes availability, latency, and how transactions read snapshots.

## How SQL Rows Become Bytes

TiKV is an ordered map of bytes. TiDB maps SQL objects into that map with short binary prefixes:

```text
row of table t=10, handle 42   ->  key: t10_r42
index i=1 on (a,b), values (7,'x')  ->  key: t10_i1{7,'x'}42   (handle appended)
cluster metadata               ->  key: m...     (schema, DDL jobs, stats)
MVCC version of any key above  ->  user_key ++ 8-byte big-endian commit_ts
```

Details that matter in practice:

- Integers are encoded in a signed-flip big-endian form so that byte order equals numeric order — that is what makes range scans and index seeks work on raw bytes.
- Variable-length index values are padded to fixed-size chunks so that `t10_i1{7,...}` and `t10_i1{77,...}` cannot become prefix-ambiguous.
- With a clustered primary key (default for new tables since TiDB v5.0), the primary key value *is* the row handle: one key instead of an index entry plus a hidden `_tidb_rowid`. Non-clustered tables pay two keys per row.

## Four RocksDB Column Families

Each TiKV store is a RocksDB instance with four column families (CFs), each an independent LSM-tree:

| CF | Lives in | Contents | Why separate |
|---|---|---|---|
| `raft` | raftstore | the region's Raft log | truncate early; never blocks data reads |
| `write` | RocksDB | MVCC metadata, commit records, short values (<= 256 B inline) | tiny entries, always read |
| `default` | RocksDB | values larger than 256 B | big blobs written once per commit |
| `lock` | RocksDB | Percolator locks (primary/secondary pointers, TTL) | drained to zero in steady state |

The read path is: probe `lock` for a conflicting lock (and resolve it if stale), then binary-search `write` for the newest commit record with `commit_ts <= snapshot_ts`, then fetch the value from `default` if it was not inlined. This split is why a scan of a snapshot touches mostly the compact `write` CF, and why compaction tuning of the two CFs is done independently.

## MVCC Without HLC

Versions are `(start_ts, commit_ts)` pairs of PD-allocated timestamps; a snapshot read at `start_ts` sees exactly the versions committed at or below it — this is ordinary single-versioned-key-range snapshot semantics, described further in [MVCC internals](./mvcc-internals.md). What is special is the clock source: unlike CockroachDB's hybrid logical clocks, TiDB nodes keep *no* local logical clock for correctness. Garbage collection is explicit: a background GC worker advances the safe point (default 10 min watermark retention) and rewrites compactable old versions away, so long-running transactions physically pin old versions in the `write` CF.

## Percolator, as Implemented in TiKV

The protocol (prewrite: lock primary + secondaries; commit: write primary, secondaries lazily) is explained once in [Percolator](../../distributed/fundamentals/percolator.md); here is only how TiKV lands it in the CFs above:

- `start_ts` and `commit_ts` are both TSOs from PD; the client-side TiDB node acts as the transaction coordinator.
- Prewrite writes the new MVCC value and a `lock`-CF entry; the *primary* is chosen as the first written key of the batch.
- Commit writes the `write`-CF commit record for the primary at `commit_ts`; secondaries get their records in a follow-up round, and a reader that meets an orphan secondary lock checks the primary to decide rollback vs. roll-forward.
- Production evolutions cut round trips: **async commit** lets secondaries commit once their own prewrites have quorum (commit_ts derived from a min bound), and **one-phase commit (1PC)** commits a region-local batch with a single raft write. Both shipped in TiDB v5.0.

## PD's Timestamp Oracle: 47 + 18 Bits

A TSO is a 63-bit value, and PD hands them out in windows:

```text
TSO bit layout:   [ 47 bits: physical ms since epoch ][ 18 bits: logical ]
per-ms window:    up to 2^18 = 262,144 timestamps handed out under one
                  in-memory latch; clients batch requests to amortize RPCs
```

Consequences worth stating in an interview:

- Timestamp throughput is *not* one RPC per transaction; a window covers hundreds of thousands of TSOs per millisecond, so PD is rarely the throughput bottleneck.
- It is, however, an availability bottleneck by construction: no TSO means no new transaction can begin or commit cluster-wide. This is the deliberate trade against HLC systems, which keep writing during a metadata-plane outage but pay uncertainty intervals on reads.
- Physical bits are 47: the format survives roughly 4,400 years of milliseconds, so no wraparound engineering is needed.

## Regions: 96 MiB Raft Groups

A region is a contiguous key range with its own Raft group (3 voters by default). The size target is **96 MiB**: writes grow a region until it reaches about 1.5x that (144 MiB), at which point raftstore commits a split entry into the Raft log, halving the range — the split is consensus-replicated state, not a control-plane action. Splits at 96 MiB are small compared with the 512 MiB ranges of CockroachDB: more groups means more scheduling freedom and lower blast radius, at the price of more heartbeat traffic (store heartbeats and region heartbeats both default to 10 s in PD's configuration).

Compared with classic fixed-hash shards, regions are *variable-count, variable-size, splittable* units: the number of regions is an output of workload growth, and rebalancing means moving whole small Raft groups (add learner peer, catch up, promote to voter, drop old peer) rather than replaying shard data. That mechanic is why TiKV's multi-raft layer, covered in depth in [Multi-Raft](../../distributed/consensus/multi-raft.md), behaves like a distributed file-system block layer under the SQL layer.

## Coprocessor Pushdown and the DAG Request

TiDB compiles a query into a physical plan, then serializes per-region fragments as a DAG request (protobuf) and ships them to the region's leader:

```text
SELECT sum(amount) FROM orders WHERE ts > 1000

TiDB plan:   TableScan(ts > 1000) -> HashAgg(final)
             fragmented per key range into DAG requests
region [k1,k100):    coprocessor: filter ts>1000, aggregate -> partial (cnt,sum)
region [k100,k200):  coprocessor: filter ts>1000, aggregate -> partial (cnt,sum)
      |  partial results stream back as column chunks
      v
TiDB: merge partials -> one result row
```

Filters, projections, top-N, limits, and partial aggregation are all candidates for pushdown; whether a query is fast depends heavily on how selective the pushed predicate is relative to the 96 MiB region scan it triggers. Two failure modes to know: a full-table scan with a weak filter makes every region a coprocessor worker (memory pressure), and the optional coprocessor cache is keyed per key-range *plus* region epoch — any split invalidates cached fragments.

## TiFlash: Raft Learners, DeltaTree, and MPP

TiFlash replicates each region as a **Raft learner**: it receives the same log entries but does not vote, so its lag never delays OLTP commits, and reads there are still consistent because reads are gated on the applied log index matching the snapshot timestamp. Storage is the DeltaTree engine:

```text
stable layer:  DTFiles, columnar, sorted by (table, segment) -> big scans
delta layer:   in-memory tail + small column files, background delta-merge
read:          merge stable + delta up to requested raft applied index
```

On top of TiFlash sits the **MPP engine** (TiDB v5.0+): the planner can shard a join across all TiFlash nodes with exchange operators and hash-partitioned redistribution, rather than only pushing per-region fragments. This is the HTAP story from the [TiDB VLDB 2020 paper](https://www.vldb.org/pvldb/vol13/p3072-huang.pdf): row and columnar replicas of the *same* log, chosen per query by cost.

## PD Scheduling: Operators and Hot Regions

PD is not just metadata; it is a control loop. Schedulers run continuously and emit **operators** — ordered step lists such as `transfer leader` or `add learner -> promote -> remove peer`:

| Scheduler | Signal it watches | Typical action |
|---|---|---|
| `balance-leader` | leader count per store | move leaders off over-loaded stores |
| `balance-region` | region size per store | move peer replicas to even capacity |
| `balance-hot-region` | per-region byte/key rates from heartbeats | relocate hot leaders or peers |
| `evict-leader` | operator-forced policy | drain a store before maintenance |

Hot-region scheduling is the subtle one: heartbeats carry per-region write/read byte and key statistics; PD computes moving averages, then decides whether the cure is moving a leader (read/write skew, cheap) or moving a peer (space skew, expensive), and rate-limits both to avoid thrash. It is also the scheduler most often fought by applications: a monotonically increasing key makes *every* new row land on the same region, and no placement algorithm can split a single logical hotspot — only schema changes (`SHARD_ROW_ID_BITS`, random keys) can.

## Growing a Keyspace: Split-and-Rebalance Simulator

A minimal deterministic model of the loop above: writes grow regions; raftstore splits anything past 144 MiB; PD moves one leader per round while store imbalance exceeds one.

```python
# Region growth, splitting, and PD leader rebalancing (toy deterministic model).
# Rules: regions split at 144 MiB (1.5x the 96 MiB target); each round the
# workload spreads writes evenly; PD moves one leader from the store with the
# most leaders to the store with the fewest while the gap exceeds 1.

SPLIT_AT, STORES, WRITES = 144.0, 6, 480.0  # MiB threshold, stores, MiB/round

regions = [[10.0, i % STORES] for i in range(8)]   # [size MiB, leader store]

print(f"{'rnd':>3} {'regions':>7} {'leaders per store':<24} {'gap'}")
for rnd in range(1, 9):
    for r in regions:                      # 1. workload lands on leaders
        r[0] += WRITES / len(regions)
    regions = [                            # 2. raftstore splits at threshold
        piece for size, lead in regions
        for piece in ([[size / 2, lead]] * 2 if size >= SPLIT_AT else [[size, lead]])
    ]
    counts = [0] * STORES                  # 3. PD balance-leader, one move
    for r in regions:
        counts[r[1]] += 1
    if max(counts) - min(counts) > 1:
        hi, lo = counts.index(max(counts)), counts.index(min(counts))
        regions[next(i for i, r in enumerate(regions) if r[1] == hi)][1] = lo
    counts = [0] * STORES
    for r in regions:
        counts[r[1]] += 1
    print(f"{rnd:>3} {len(regions):>7} {str(counts):<24} {max(counts) - min(counts)}")

print(f"final: {len(regions)} regions (from 8), leader gap = {max(counts) - min(counts)}")
```

Real output (executed with Python 3.11):

```text
rnd regions leaders per store        gap
  1       8 [2, 2, 1, 1, 1, 1]       1
  2       8 [2, 2, 1, 1, 1, 1]       1
  3      16 [2, 4, 4, 2, 2, 2]       2
  4      32 [6, 6, 8, 4, 4, 4]       4
  5      32 [6, 6, 7, 5, 4, 4]       3
  6      32 [6, 6, 6, 5, 5, 4]       2
  7      32 [5, 6, 6, 5, 5, 5]       1
  8      64 [12, 10, 12, 10, 10, 10] 2
final: 64 regions (from 8), leader gap = 2
```

The shape is the lesson: every burst of splits doubles leader counts instantly and the gap jumps (rounds 3-4, 8), then the balancer claws it back at exactly one move per round. Splitting is fast and local — each region owns its own decision — while rebalancing is deliberately slow; in a real cluster PD caps concurrent operators far below the split rate on purpose, which is why balance progress looks stair-stepped in monitoring.

## TiDB vs CockroachDB vs Spanner

| Aspect | TiDB | CockroachDB | Spanner |
|---|---|---|---|
| Timestamp source | PD TSO (central, batched windows) | HLC, node-local | TrueTime (GPS + atomic clocks) |
| Transaction protocol | Percolator-style 2PC locks | Percolator-derived intents | 2PC over Paxos groups + commit-wait |
| Default isolation | Snapshot Isolation (`REPEATABLE READ`) | Serializable | External consistency |
| Replication unit | Region, 96 MiB target | Range, 512 MiB default | Tablet (directory-sized) |
| Storage engine | RocksDB (4 CFs) | Pebble (Go LSM) | SSTs on Colossus |
| Write latency floor | 1 TSO RTT + Raft quorum | Raft quorum only | Raft quorum + commit-wait (>= 2x epsilon) |
| HTAP | TiFlash columnar + MPP | none built-in | built-in columnar reads |
| Wire protocol | MySQL | PostgreSQL | SQL/gRPC (proprietary) |

The deepest structural difference is the clock plane. TiDB centralizes ordering in PD and accepts the availability floor; CockroachDB distributes ordering into per-node HLCs and pays with uncertainty restarts; Spanner outsources ordering to hardware and pays with commit-wait. All three nonetheless converge on the same per-range consensus + range-split + placement-scheduler skeleton — see [CockroachDB Architecture](./cockroachdb.md) and [Spanner](../../distributed/fundamentals/spanner.md) for the other two variants.

## Common Pitfalls

1. **Lock-CF pile-ups from long transactions.** A stale secondary lock forces every reader to chase the primary for resolution; at scale that turns into `resolve_lock` storms. Watch transaction TTL and avoid multi-minute OLTP transactions.
2. **Hot regions versus balance-region thrash.** Moving a hot leader changes the hotspot's location without removing it; if schema keeps funneling writes into one region, PD rate-limits itself and the hotspot persists. Fix the key layout, not the placement.
3. **Coprocessor memory blowups.** A pushed-down scan over thousands of regions with a weak filter allocates in every TiKV store at once; enforce limits and check `EXPLAIN` for how much survived pushdown.
4. **TiFlash learner lag.** Just-committed data may not yet be applied at the learner; queries either wait for the required applied index or fall back per cost model. Freshly written data read through TiFlash is where the lag shows.
5. **Region count as memory cost.** Every region carries raft state and heartbeat metadata per store; hundreds of thousands of tiny regions (aggressive splits, tiny tables) inflate raftstore memory and PD's scheduling surface — merges exist for this.
6. **Assuming TSO allocation is free.** It is batched, but it is still one central service on the critical path of *every* commit; capacity-plan PD and monitor TSO wait, the way you would monitor any singleton dependency.

## References

- D. Huang et al., "TiDB: A Raft-based HTAP Database," PVLDB 13(12), 2020. <https://www.vldb.org/pvldb/vol13/p3072-huang.pdf> (doi: 10.14778/3415478.3415535)
- D. Peng, F. Dabek, "Large-Scale Incremental Processing Using Distributed Transactions and Notifications," OSDI 2010. <https://www.usenix.org/legacy/events/osdi10/tech/full_papers/Peng.pdf>
- TiDB Architecture (PingCAP docs). <https://docs.pingcap.com/tidb/stable/tidb-architecture>
- TiDB Scheduling and PD configuration (PingCAP docs). <https://docs.pingcap.com/tidb/stable/tidb-scheduling>
- TiKV deep-dive: Multi-Raft. <https://tikv.org/docs/deep-dive/scalability/multi-raft/>
- Source: tikv/tikv. <https://github.com/tikv/tikv>
