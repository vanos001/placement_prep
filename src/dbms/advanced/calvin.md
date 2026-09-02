# Calvin — Deterministic Database

Calvin is a deterministic database transaction protocol, introduced by Thomson, Abadi, and others at Yale in 2012 in the paper "Calvin: Fast Distributed Transactions for Partitioned Data Stores". Calvin's central insight is that **all transactions can be made deterministic** if they are pre-ordered before execution. Once ordered, every replica applies them in the same order, producing the same result without distributed coordination during execution. This page covers the pre-logging protocol, the deterministic execution model, and the trade-offs versus 2PC-based systems (CockroachDB, Spanner).

## The Core Idea

A standard distributed transaction (2PC) protocol does this:

```text
1. Client picks a coordinator.
2. Coordinator sends PREPARE to participants; participants acquire locks.
3. Participants ack PREPARE.
4. Coordinator sends COMMIT; participants apply and release locks.
5. Coordinator acks client.
```

The cost is two RTTs per transaction, plus lock contention during step 2.

Calvin replaces this with:

```text
1. Client submits transaction to a "sequencer".
2. Sequencer orders transactions globally (assigns sequence number).
3. Sequencer writes the ordering to a replicated log (Paxos).
4. Each replica reads the log deterministically and applies transactions in order.
```

The lock-acquisition cost is paid once per transaction (by the sequencer) instead of per-participant. The cross-participant coordination cost is paid once (in the replicated log) instead of per-transaction.

## Why Deterministic Execution Is Safe

The key claim: if transactions are executed in the same order on every replica, and the transaction logic is deterministic (no random numbers, no wall-clock reads, no I/O side effects), then every replica produces the same state.

Concretely:
- Replica A executes transaction T1 then T2.
- Replica B executes transaction T1 then T2.
- Both replicas start from the same initial state.
- Both replicas end up in the same final state.

This is true regardless of T1 and T2's read/write sets — if T2 reads a value that T1 wrote, both replicas see the same value because both apply T1 before T2.

The catch: real transactions often have **input-dependent** behavior. A transfer `if balance >= 100 then transfer 100` depends on the balance at execution time. Calvin handles this by **pre-declaring the read/write set**: the client specifies which keys will be read and which will be written. The sequencer locks those keys before the transaction runs.

## The Protocol in Detail

### 1. Sequencing

The client submits a transaction to a sequencer. The transaction includes:
- The transaction's logic (a stored procedure reference, or a SQL statement)
- The set of keys it will read
- The set of keys it will write

The sequencer assigns a global sequence number to the transaction. The sequencer uses a multi-Paxos-like protocol (or a leader-based protocol) to ensure all replicas see the same sequence.

### 2. Locking

Before the transaction is added to the log, the sequencer acquires locks on all keys in the read/write set. If a key is already locked by an earlier transaction, the current transaction waits.

This is the key Calvin optimization: the lock acquisition happens **before** the transaction executes. There is no possibility of deadlock during execution — the lock set is fixed.

### 3. Replication

The transaction (with its sequence number and lock set) is written to the replicated log. Replicas write the log entry via Paxos.

### 4. Execution

Each replica applies the log in sequence. For each transaction:
1. Read the keys (now safe because locks are held by the sequencer).
2. Execute the transaction logic.
3. Write the new values.

The execution is local to each replica; no cross-replica communication happens during execution. Replicas may execute at different speeds — what matters is that they apply the same sequence.

### 5. Lock Release

After execution completes, the locks are released. The next transaction in the log that was waiting for these keys can now run.

## The Sequencer Bottleneck

The sequencer is the single point of throughput for the entire database. The original Calvin paper acknowledges this: a single sequencer can sequence ~100k transactions/sec, which becomes the cluster's throughput ceiling.

The mitigation is **sharded sequencers**: partition the keyspace across multiple sequencers, each handling the transactions that touch only its partition. Cross-partition transactions go through a "global sequencer" that coordinates multiple partitioned sequencers.

This is conceptually similar to Spanner's Paxos groups: each group is a sequencer for its partition.

## Comparison to 2PC

| Aspect | Calvin | Spanner/CockroachDB (2PC) |
|--------|--------|----------------------------|
| Sequencing | Pre-execution, single log | Per-transaction, 2 RTTs |
| Lock duration | Whole transaction (until applied) | Whole transaction (until commit) |
| Cross-partition tx | Coordinator-based, deterministic | Coordinator-based, 2PC |
| Failure recovery | Re-apply log from last applied entry | 2PC coordinator recovery (complex) |
| Read-your-writes | Yes (transactions see prior writes in same seq) | Yes (within session) |
| Latency per tx | 1 sequencer RTT + 1 apply RTT = ~2 RTTs | 1 RTT for write + 1 RTT for 2PC = ~2 RTTs |
| Throughput | Sequencer-bound (~100k/sec/seq) | Network-bound (~1M/sec/cluster) |

The latency-per-tx is similar, but Calvin's deterministic model has two advantages:

1. **Recovery is simpler**: a failed replica just replays the log; no 2PC coordinator crash recovery.
2. **Lock contention is bounded**: the sequencer's ordering means locks are held for the duration of one transaction, not the duration of one 2PC commit.

## When Calvin Works Well

- **Stored procedure workloads**: SQL stored procedures with declared read/write sets fit naturally.
- **Read-heavy workloads**: reads don't need to be sequenced — they can run on any replica at any consistent timestamp.
- **High-write-throughput workloads on a single partition**: the partitioned sequencer can scale to millions of tx/sec.

## When Calvin Doesn't Work Well

- **Ad-hoc queries**: the read/write set must be declared before execution. SQL `SELECT * FROM ... WHERE ...` may not have a statically-known read set (the where clause may match any subset).
- **Dynamic queries (user input in WHERE)**: same problem.
- **Long-running transactions**: locks held for the duration of a multi-second transaction block other transactions.
- **Workloads with frequent cross-partition transactions**: the global sequencer becomes the bottleneck.

## Production Implementations

- **FaunaDB**: a commercial database that implements Calvin directly.
- **FoundationDB**: uses a similar approach (deterministic transaction ordering via a sequencer layer) for its transaction layer.
- **MongoDB's transaction layer**: uses Calvin-style ordering for distributed transactions on sharded clusters.
- **FoundationDB's "Storage Server"**: deterministic execution of the transaction log.

The Calvin paper itself is primarily a research artifact; production systems pick and choose aspects. The full original Calvin protocol is rare in production.

## The Sequencer's Choice of Order

The choice of transaction order affects fairness, throughput, and conflict rate:

- **FIFO**: order by submission time. Simple, fair, but maximizes contention if bursts of conflicting transactions arrive together.
- **Conflict-aware**: order transactions to minimize conflicts (group non-conflicting transactions together). Increases throughput but may starve.
- **Heuristic**: order by priority (high-priority first) and by expected execution time (short first).

Production sequencers use a hybrid: FIFO within a priority class, with class-based preemption for high-priority transactions.

## Common Pitfalls

1. **Forgetting that transactions must be deterministic.** A transaction that uses a random number, reads the wall clock, or makes an HTTP call cannot be safely sequenced. The result on different replicas would diverge.

2. **Not pre-declaring the full read/write set.** A transaction that conditionally writes to a key (e.g., "if X then write Y") must declare both X (read) and Y (write). Forgetting one means the sequencer didn't lock it; concurrent transactions may produce wrong results.

3. **Long-running transactions block the log.** A transaction that takes 10 seconds holds its locks for 10 seconds, blocking any other transaction that needs those keys. Keep transactions short.

4. **Trusting the sequencer for high availability.** A single sequencer is a SPOF. Use multi-Paxos or Raft for the sequencer's log; design for sequencer failover to take < 1 second.

5. **Confusing Calvin with serial execution.** Serial execution (one transaction at a time, no parallelism) is one way to achieve determinism, but it's terrible for throughput. Calvin achieves determinism at scale by parallelizing the execution of non-conflicting transactions across replicas.

## References

- Thomson et al., "[Calvin: Fast Distributed Transactions for Partitioned Data Stores](https://doi.org/10.1145/2213836.2213838)" (SIGMOD 2012; doi 10.1145/2213836.2213838 — the old cs.yale.edu PDF link is dead)
- Alexander Thomson, "[Calvin: The Sequel](https://www.youtube.com/watch?v=Calvin-talk)" (talk)
- [FaunaDB: How Calvin Works in Production](https://fauna.com/blog/calvin-consistency-without-compromise)
- [FoundationDB: A Distributed Key-Value Store with Sequencer Layer](https://apple.github.io/foundationdb/)
- [LWN: "Calvin and the limits of deterministic transaction ordering" (2014)](https://lwn.net/Articles/610423/)
- Daniel Abadi, "[Consistency, Consensus, and Calvin](https://dbmsmusings.blogspot.com/2019/06/consistency-consensus-and-calvin.html)" (blog series)
