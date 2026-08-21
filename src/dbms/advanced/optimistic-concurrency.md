# Optimistic Concurrency Control (OCC)

Optimistic Concurrency Control (OCC), introduced by Kung and Robinson in 1981, is a transaction scheduling technique that assumes conflicts are rare and never acquires locks during the working phase. Instead of blocking writers behind readers (or vice-versa), every transaction reads, writes, and computes freely against a private workspace, then runs a **validation** step at commit time to prove that its effects are equivalent to a serial execution. If validation fails, the transaction aborts and restarts. The bet is that the cost of occasional aborts is lower than the cost of lock waits, deadlocks, and lock-manager bookkeeping for the common conflict-free workload.

OCC dominates workloads that are read-mostly, low-contention, or distributed across wide-area networks where holding locks for the round-trip latency of two-phase commit (2PC) is prohibitive. FoundationDB, CockroachDB, Google Spanner's read-write transactions, PerconaFT's Optimistic, and many in-memory stores (e.g., Reactor's STM, Software Transactional Memory) lean on OCC for exactly this reason.

## The Three-Phase Protocol

Kung & Robinson's original OCC has three phases per transaction T:

```
                ┌─────────────────────────────────────┐
   begin T ───▶│  1. READ PHASE                      │
                │  - read set  RS(T) from shared DB   │
                │  - write set WS(T) into private buf │
                │  - assign tentative write ts       │
                └──────────────┬──────────────────────┘
                               ▼
                ┌─────────────────────────────────────┐
                │  2. VALIDATION PHASE                │
                │  - acquire commit timestamp ts(T)   │
                │  - check serializability vs all     │
                │    transactions that committed      │
                │    while T was active               │
                └──────────────┬──────────────────────┘
                               ▼  (abort on fail → restart)
                ┌─────────────────────────────────────┐
                │  3. WRITE PHASE                     │
                │  - copy WS(T) from private buffer   │
                │    into the shared database         │
                │  - make writes visible atomically   │
                └─────────────────────────────────────┘
```

### Phase 1 — Read

T reads its needed data items into a local workspace. Writes are buffered in the same workspace — they are *not* visible to other transactions yet. The transaction records both `RS(T)` (the set of items read, with version numbers) and `WS(T)` (the set of items written). The intuition is that conflicts are rare, so blocking during the long working phase would waste throughput.

### Phase 2 — Validation

At commit time, T gets a monotonically increasing timestamp `ts(T)`. Then T must prove it is serializable against all transactions T' that *finished* (committed) during T's lifetime. The serial order is the commit-timestamp order.

### Phase 3 — Write

If validation succeeds, T's writes are copied from the private workspace to the shared database and become visible. This must happen atomically with respect to new readers — typically implemented by writing all values and then flipping a "committed" flag, or by writing under a brief exclusive lock per item.

## Validation Rules: Backward and Forward

Kung & Robinson give two equivalent ways to define "T is serializable after T'". Let `ts(T)` be T's validation timestamp, and `fin(T)` the moment T finishes phase 3.

### Backward validation (validate against older, already-committed transactions)

For every transaction T_i that committed *before* T starts validation (i.e., `fin(T_i) < start(T)`), no conflict check is needed — they were already gone when T started.

For every transaction T_i that committed *during* T's lifetime (`start(T) ≤ fin(T_i) ≤ start_validation(T)`), T must satisfy one of:

1. `fin(T_i) < start(T)` — T_i finished before T started (covered above).
2. `WS(T_i) ∩ RS(T) = ∅` — T_i didn't write anything T read.
3. `ts(T_i) < ts(T)` and `WS(T_i) ∩ WS(T) = ∅` and ... the writes of T_i don't overlap T's writes, OR they overlap but T's writes logically "follow" T_i's (the version T read for any overlapping item is still the pre-T_i version).

The cleanest formulation (used in many textbook proofs): T is valid against T_i if **T_i's writes don't touch T's reads** — i.e., `WS(T_i) ∩ RS(T) = ∅`. If this holds for every overlapping T_i, T's snapshot was consistent and T can commit.

### Forward validation (validate against newer, still-running transactions)

Alternatively, T checks against transactions T_j that are *still running* when T wants to commit. T_j started before T finishes, but hasn't validated yet. For every such T_j:

- T aborts T_j if `WS(T) ∩ RS(T_j) ≠ ∅` (T is about to write something T_j read).

Forward validation aborts *other* transactions, not the one committing. This is friendlier to long-running transactions but breaks the "commit timestamp = serial order" invariant slightly, since the victim hasn't picked a timestamp yet.

In practice most production systems (FoundationDB, CockroachDB's `SERIALIZABLE` path) use **backward validation** because it's easier to reason about and the abort cost lands on the transaction that's already at the commit step (where retry is cheap).

## Multi-Version OCC and Timestamp Ordering

Plain OCC (single version per item) requires the writer to re-check at validation that no one wrote the item it read since it read it. Multi-version OCC (MV-OCC), as formalized by Reed (1983) and refined by Bernstein & Goodman, attaches a **commit timestamp** to every version. The three-phase protocol becomes:

```
Read phase:
  When T reads item X, it sees the version with the largest
  timestamp ≤ ts(T). Call this X[ts_read(X)].
  T records (X, ts_read(X)) in RS(T).

Validation phase (backward):
  For every T_i that committed during T's lifetime:
    for each (X, ts_r) in RS(T):
      if some version of X was created by T_i and
         ts(T_i) > ts_r  and  ts(T_i) ≤ ts(T):
        ABORT  -- T read an old version; a newer one is now
                 committed; the serial order is violated

Write phase:
  Create new versions X[ts(T)] for every X in WS(T).
```

MV-OCC gives every reader a consistent snapshot for free; the validation only has to confirm that the snapshot T used is still consistent with everything that committed since. This is essentially what PostgreSQL does internally with its xmin/xmax tuples, except that Postgres uses Snapshot Isolation (a slightly weaker predicate check) rather than full OCC validation.

## The Phantom Problem in OCC

Phantoms are subtle in OCC because there is no lock to "hold" on a predicate. Consider:

```sql
-- T1: count users with balance > 1000
SELECT count(*) FROM users WHERE balance > 1000;  -- returns 5
-- ... makes a decision based on "5"

-- T2 (concurrent): insert a new user with balance 1500
INSERT INTO users VALUES (..., 1500);  -- commits while T1 still running

-- T1: inserts an audit row based on count = 5
INSERT INTO audit_log VALUES (5, now());
COMMIT;
```

T1 read "5 users", T2 inserted a 6th, T1's audit row is now wrong. Plain OCC's `RS(T)` only contains the *items actually read* — five user rows — not the rows that *would have been read* if the predicate were re-evaluated. So `WS(T2) ∩ RS(T1) = ∅`, and validation passes despite the phantom.

The standard fix is **predicate locking / index interval locking**: T1 records not just the five rows but the *range predicate* (`balance > 1000`) as part of its read set. T2's insert must check against any active predicate read set whose range covers the inserted key, and force a conflict. This is exactly what Serializable Snapshot Isolation (SSI) does in PostgreSQL via its "SIREAD locks" on GiST/B-tree ranges. In a distributed OCC system like FoundationDB, the equivalent is **range reads** that register themselves in the conflict-range database; the resolver rejects commits whose write ranges overlap any active read range.

## OCC vs 2PL: When to Use Each

| Dimension | OCC | Strict 2PL |
|---|---|---|
| Working phase | No locks; private workspace | Lock every item read and written |
| Memory | Must buffer all writes | Just lock table entries |
| Deadlocks | Impossible | Possible (and must be detected) |
| Throughput under low contention | High (no waits) | Lower (lock acquire/release cost) |
| Throughput under high contention | Catastrophic (retry storms) | Limited by wait queue |
| Long transactions | Vulnerable (high abort probability) | Block others, may stall system |
| Distributed commit | Cheap; conflict ranges fit in a message | Expensive; 2PC holds locks during RTT |

A rule of thumb: if conflict probability p is small and the cost of retry R is small relative to lock-acquire cost L, OCC wins when `p·R < L`. In wide-area databases (Spanner, CockroachDB, FDB), L is dominated by a 100 ms RTT and p is often <1% for well-sharded workloads, so OCC dominates.

## Production Use

### FoundationDB

FoundationDB (now Apple's underlying store for iCloud, Notes, etc.) is the cleanest production realization of MV-OCC. Clients read against a version V (a 64-bit timestamp assigned by a *proxies* service). Writes accumulate in a local mutation buffer. At commit time, the client sends a single message containing:

```
CommitRequest {
   read_conflict_ranges: [...],   // predicate ranges read at version V
   write_conflict_ranges: [...],  // ranges that should be exclusive to this txn
   writes: [(key, value), ...],  // actual mutations
}
```

The *resolver* (Paxos-replicated) checks each conflict range against the committed-write-range index between V and the current commit version. If any overlap, the commit is rejected with `commit_unknown_result` or `not_committed` and the client retries the entire transaction. Reads never block, writes never block — only commits can fail, and they fail fast.

Documentation: <https://apple.github.io/foundationdb/transaction-logging.html> and the conflict-range rationale in the FDB developer guide.

### CockroachDB

CockroachDB defaults to Serializable isolation implemented as distributed MV-OCC with clock uncertainty. Each transaction picks a provisional timestamp `ts`, writes intents (not committed values) at that timestamp, and at commit time calls a `RecordCommit` on the transaction record. If a concurrent writer (with a higher timestamp) bumps `ts` via the **write-intent push** mechanism, the transaction must be **restarted** at a new timestamp. Read-write conflicts are detected through timestamp caching on each range — the leaseholder tracks "the highest read timestamp seen" for each key, and any later intent write below that timestamp is pushed forward.

CockroachDB uses **epoch-based** restarts (in 22.x) to avoid re-executing read work — the transaction can be "refreshed" by re-reading only the conflict ranges. This is the same essential trade-off as FDB but executed at the per-range lease level rather than centralized resolvers.

Docs: <https://www.cockroachlabs.com/docs/stable/architecture/transaction-layer.html>.

### Google Spanner

Spanner uses OCC for its read-write transactions across Paxos groups. Reads acquire read locks (so technically not pure OCC), but writes are buffered client-side and committed via a 2PC over the participating Paxos leaders. The "lock" is held for only the duration of the 2PC prepare, which — combined with TrueTime's bounded clock uncertainty — is what makes Spanner's external-consistency guarantee possible. The clock-uncertainty interval `[ts-ε, ts+ε]` essentially replaces the "snapshot version" of single-node OCC.

Paper: <https://research.google/pubs/spanner-googles-globally-distributed-database/>.

## Worked Example: OCC Banking Transfer

Two transactions concurrently transfer money between accounts A, B, C (initial balances 100, 200, 300):

```
T1: withdraw $50 from A, deposit $50 into B
T2: withdraw $70 from B, deposit $70 into C

T1 reads A=100, B=200. WS(T1) = {(A, 50), (B, 250)}.
T2 reads B=200, C=300. WS(T2) = {(B, 130), (C, 370)}.

Both commit at the same timestamp... validation:
  WS(T1) ∩ RS(T2) = {B}   ← T1 wrote B; T2 read B's old value
  Conflict!  Exactly one of T1, T2 must abort.

Backward validation (whichever validates last loses):
  Suppose T1 validates first → T2's validation sees T1 already committed
  with newer version of B → T2 aborts and retries.
  T2 restart, reads B=250 (new value), C=300, computes B=180, C=370, commits.
```

The shared conflict on B is detected because both transactions included B in their respective RS/WS. This is the OCC analog of the *write skew* problem: had T1 and T2 written *different* accounts (T1: A→B; T2: C→D), validation would succeed even though the resulting state is no longer equivalent to either transaction's view of the world. OCC gives serializability only because the snapshot read in phase 1 plus the read-set check in phase 2 enforce an equivalent serial order — but only if the read set is the *full* set the application reasoning depends on.

## Pitfalls

1. **Long transactions starve.** A 30-second transaction in a high-write system will fail validation almost every time. Fix: split into smaller batches, or use snapshot isolation (no abort on read-only) and accept write-skew.
2. **Phantom reads slip past naive read sets.** Without predicate conflict ranges, range-scan-based decisions are unsafe at SERIALIZABLE. Use range reads / SSI.
3. **Clients must be idempotent.** OCC abrts require the client to re-execute the entire transaction body. If the body has side effects (sending email, charging a card), wrap in an idempotency key.
4. **Read-set size matters.** FDB and CockroachDB serialize conflict ranges — a transaction reading 1M keys pays a large commit-message cost. Use covered indexes or read at lower isolation when possible.
5. **Skewed hot keys.** A single hot key (e.g., a counter) turns the system into a serial retry queue. Use CRDT-style counters (e.g., FDB's `atomic_op(ADD, n)`) which avoid validation.

## References

- H. T. Kung and J. T. Robinson, "[On Optimistic Methods for Concurrency Control](https://www.eecs.harvard.edu/~htk/publication/1981-tods-kung-robinson.pdf)", *ACM TODS* 6(2), 1981 — the foundational OCC paper.
- P. Bernstein and N. Goodman, "[Concurrency Control Algorithms and the Problem of Schedule Equivalence](https://dl.acm.org/doi/10.1145/356824.356828)", *ACM Computing Surveys*, 1981 — survey placing OCC in context with 2PL, timestamps, and multiversion.
- D. P. Reed, "[Implementing Atomic Actions on Distributed Data](https://dl.acm.org/doi/10.1145/800216.806585)", *SOSP 1983* — introduces multiversion OCC, the basis for most production systems.
- FoundationDB developers, "[Key Ranges in Conflict Ranges](https://apple.github.io/foundationdb/developer-guide.html#conflict-ranges)", official developer guide.
- Cockroach Labs, "[Transaction Layer — Architecture](https://www.cockroachlabs.com/docs/stable/architecture/transaction-layer.html)", CockroachDB reference docs.
- J. Baker et al., "[Megastore: Scalable Highly Available Storage](https://research.google/pubs/megastore-scalable-highly-available-storage/)", *CIDR 2011* — production Google system using OCC + 2PC over Paxos groups.
- J. C. Corbett et al., "[Spanner: Google's Globally-Distributed Database](https://research.google/pubs/spanner-googles-globally-distributed-database/)", *OSDI 2012* — OCC + TrueTime + 2PC, the most-cited modern OCC paper.
- H. Berenson et al., "[A Critique of ANSI SQL Isolation Levels](https://www.cs.umb.edu/~poneil/iso.pdf)", *SIGMOD 1995* — defines the anomaly taxonomy that explains when OCC's promises are enough.
