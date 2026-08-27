# Jepsen: Fault Injection and Correctness Checking

## What Jepsen Is

Jepsen is the distributed-systems testing project started by Kyle Kingsbury (Aphyr) in 2010–2011, and — via its published analyses — the most influential public body of evidence about what real databases do under failure. A Jepsen test takes a *real, deployed* system (etcd, MongoDB, PostgreSQL, Kafka, Cassandra, Redis, TiDB, ...), installs it on a cluster of real nodes, drives concurrent client operations against it while an adversary — the **nemesis** — bends the environment (partitions the network, skews clocks, kills processes, degrades disks), records the full **history** of what clients observed, and then feeds that history to a **checker** that decides whether the system violated the consistency model it documents.

The Jepsen analyses have repeatedly found that widely deployed, "highly consistent" systems lose acknowledged writes or serve stale data under ordinary failures: acknowledged Redis writes lost after async-replication failover (2013), MongoDB rolling back acknowledged writes in its default configuration (2013–2015), Aerospike losing data when a disk failed (2015), Galera serving stale reads against claims of linearizability (2014), stale reads in etcd 2.x (2016), and retracted guarantees from an earlier Kafka analysis being re-established with the 2020 "idiomatic Kafka" analysis (which found that with `acks=all`, `min.insync.replicas`, and `read_committed` reads, Kafka's log behaves as a strictly serializable object — while weaker configurations can lose acknowledged writes). None of these findings came from exotic hardware; they came from network partitions and process kills that every production system eventually meets.

The lasting contribution is methodological: **state the consistency model, generate a concurrent history under faults, and verify the history against the model** — turning "we think it's safe" into a mechanical question.

## Anatomy of a Jepsen Test

```text
        ┌────────────────────────── control node ──────────────────────────┐
        │  nemeses (partitioner, clock skower, killer, slow-disk, ...)     │
        │  client threads ── op generator ──▶ history log (time-stamped)   │
        │  checker (Knossos / Elle) ◀── history                            │
        └───────┬───────────────────┬───────────────────┬─────────────────┘
                │ ssh               │ ssh               │ ssh
        ┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
        │   node n1     │   │   node n2     │   │   node n3     │
        │  real system  │   │  real system  │   │  real system  │
        │  under test   │   │  under test   │   │  under test   │
        └───────────────┘   └───────────────┘   └───────────────┘
```

The moving parts:

1. **Setup.** The system under test is installed and started on N nodes exactly as an operator would (packages, config files, no mocks).
2. **Workload.** Client threads execute generated operations through the system's real client library. Workloads are chosen so their *expected outcomes are checkable*: atomic registers and compare-and-set (checkable for linearizability), lists that clients append unique elements to (checkable for transactional read-modify-write anomalies), sets, counters, queues.
3. **Nemeses.** While clients run, faults are applied:
   - **Partitions**: cut the network between halves (majority/minority), isolate a bridge node, partition one node from the leader, or make the network cyclic (nodes see each other in rings, not as one partition);
   - **Clock events**: step clocks forward/back, skew NTP sources, so leader election and timestamps misbehave;
   - **Process events**: SIGKILL and restart nodes, suspend (SIGSTOP) and resume them;
   - **Disk events**: `fsfreeze`, full disks, I/O throttling — anything that makes fsync latency spike or persistence questionable;
   - **Application-level turbulence**: membership changes, leader transfers, failovers, compactions.
4. **History.** Every operation is recorded with invoke/complete (or crash) wall-clock times, including operations whose *outcome is unknown* — the client timed out but the write may have committed. Unknown-outcome operations are the heart of distributed testing: a protocol's job is to make them resolve safely.
5. **Checker.** The checker replays the history and reports *anomalies* — concrete, named violations such as "lost update," "stale read," "G2 (anti-dependency cycle)," "non-repeatable read," or a full "not linearizable" verdict with a violating subsequence.

## The Core Check: Linearizability

Linearizability is the strongest single-object consistency model: every operation appears to take effect *atomically at some instant between its invocation and its response*, and that instant respects real time. It is the natural contract for a lock service, an election, or a leader lease.

A register history fails linearizability if the read values cannot be explained by any legal ordering. For example — a client writes `x = 1`, *gets an ack*, and a later read (from another client, after the ack) still returns `0`:

```text
t0 ── write(x=1) ──▶ ok! ──────────────────────────▶ t2   (client A)
                     └────────── read(x) → 0 ──▶ t1        (client B, t1 > t2)

No linearization point exists: the write completed before the read began,
so the read may not return the old value. This history is illegal.
```

Checking this mechanically is expensive — the number of candidate orderings is exponential — and the Jepsen ecosystem's **Knossos** checker implements the Wing & Gong / Lowe algorithm with memoization to prune the search. For transactional workloads (append-to-list, read-write registers), the newer **Elle** checker looks for dependency cycles between transactions (read-write and write-write anti-dependencies) that witness specific isolation-level violations, and renders the offending cycles for humans.

## What Checkers Actually Look For

| Anomaly | What the history shows | Model violated |
|---|---|---|
| Lost update | two clients read `x`, both increment, final value reflects one write | any read-modify-write contract |
| Stale read | a read returns a value older than a previously *acknowledged* write | linearizability, monotonic reads |
| Dirty read | a read observes a value of a transaction that later aborted | read committed |
| Write skew (G2) | two transactions read disjoint rows and write disjoint rows; constraint total is violated | serializability |
| Non-repeatable read | same read twice in one transaction returns different values | repeatable read |
| Broken CAS | compare-and-set succeeded although the register did not hold the expected value | linearizability |
| Duplicate/lost append | list-append workload: an appended element appears twice or not at all | transactional durability |

A useful mental model: the checker is a *tiny specification engine*. It does not know or care how the database implements replication; it only asks whether the observed history is one that the documented model permits. This black-box posture is why Jepsen findings are so hard to argue with — and why they occasionally bounce off a vendor who then simply documents a weaker model ("this product provides eventual consistency") rather than fixing the behavior.

## How to Read (and Run) a Jepsen Analysis

A finding is a conjunction: *system X, version Y, configuration Z, workload W, nemesis set N ⇒ anomaly A*. Every clause matters. The 2020 Kafka result is the canonical example — the anomaly profile flips entirely on `acks` and `min.insync.replicas` settings. When you read an analysis, extract all five clauses before concluding "X is unsafe"; when you defend your own system, know your five clauses.

Running Jepsen-style tests yourself is practical: the [jepsen-io/jepsen](https://github.com/jepsen-io/jepsen) framework drives clusters provisioned by Docker, Vagrant, or Terraform, and its checkers (Knossos, Elle) are reusable libraries. Teams at Cockroach Labs, MongoDB, ScyllaDB, and others ship Jepsen-style tests in CI as a matter of course. The honest limits:

- **Passing is not proving.** A Jepsen run explores a tiny fraction of the schedule space; passing means "not caught this time." Complement it with deterministic simulation and (for protocols) model checking.
- **Environment realism cuts both ways.** Real TCP and disks are realistic, but a test cluster's failure distribution rarely matches production's (no NUMA weirdness, no kernel panics mid-fsync, no NIC firmware bugs).
- **Checkers are model-bound.** If your workload can't express the guarantee you sell, the checker can't audit it.

## Interview Angles

- **Your database claims serializability. What would a Jepsen test of that claim look like?** Multi-key transactions under concurrent load, with list-append or read-write-register workloads, a partition nemesis plus kill/restart, checked by Elle for dependency cycles (G1, G2) — and expect to discuss why a single register workload would *not* test serializability (it tests linearizability of one object).
- **Why are unknown-outcome operations (timeouts) the crux?** A timed-out write may or may not have committed; the system must resolve it consistently (e.g., fencing/monotonicity), and checkers explicitly model "crashed" invocations — a candidate interviewer follow-up on idempotency.
- **Design a Jepsen-style test for a distributed lock service.** CAS registers as "lock tokens," partitions to force split-brain, checker asserts at most one holder at a time (this exact test is how fencing-token gaps get found).
- **How is Jepsen different from chaos engineering?** Chaos engineering asks "does the system *recover and stay available*"; Jepsen asks "is the *data* consistent with the documented model during and after faults." Production systems need both, and they use overlapping tooling.

## References

- [Jepsen — project home and consistency-model discussions](https://jepsen.io)
- [Jepsen Analyses — the published database analyses](https://jepsen.io/analyses)
- [jepsen-io/jepsen — the testing framework](https://github.com/jepsen-io/jepsen)
- [jepsen-io/knossos — linearizability checker](https://github.com/jepsen-io/knossos)
- [jepsen-io/elle — transactional consistency checker](https://github.com/jepsen-io/elle)
- [Jepsen consistency models reference](https://jepsen.io/consistency)
