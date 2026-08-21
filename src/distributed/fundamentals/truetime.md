# TrueTime

TrueTime is Google's clock abstraction used by Spanner to provide externally-consistent distributed transactions. It exposes time as an interval `[T_earliest, T_latest]` rather than a point, where the interval's width represents the *uncertainty* in the time estimate. This page covers the API, the implementation (GPS receivers + atomic clocks in datacenters), the commit-wait rule that makes external consistency possible, and the critique that TrueTime is a "bold engineering workaround" rather than a fundamental solution to clock uncertainty.

## The API

TrueTime exposes two operations:

```cpp
struct TTinterval {
    int64_t earliest;  // microsecond-precision Unix epoch
    int64_t latest;
};

class TrueTime {
public:
    // Returns the current time as an interval.
    TTinterval Now();

    // Returns true if `t` is definitely in the past.
    bool After(int64_t t);

    // Returns true if `t` is definitely in the future.
    bool Before(int64_t t);
};
```

The crucial point: `Now()` returns an *interval*, not a point. The application code that uses TrueTime must treat time as uncertain — any commit timestamp is "in [earliest, latest]".

In a typical datacenter, `TT.uncertainty()` = `latest - earliest` is 1-7 ms. In a multi-region cluster with a GPS receiver in each region, it can be 5-20 ms depending on the receiver synchronization protocol.

## The Implementation

Each datacenter has multiple **time masters** — a mix of GPS receivers (which get UTC from GPS satellites) and atomic clocks (BTS-204C cesium clocks). These are mutually redundant: GPS receivers fail during satellite-visibility issues; atomic clocks drift slowly but reliably.

Each machine in the datacenter polls its time masters every 30 seconds (default `tiger`-interval). The machine computes its local time as a weighted average of the masters' reported times, adjusted by the network delay and the local crystal's drift rate. The uncertainty interval is widened to account for:

- The poll interval (clock may drift between polls).
- The network delay variance (estimated from previous polls).
- The local crystal's drift rate (typically 100-300 ppm = parts per million).

```text
TT.earliest = master_time - local_drift_since_last_poll - network_delay_jitter
TT.latest   = master_time + local_drift_since_last_poll + network_delay_jitter
```

A machine that fails to poll a master for >30 seconds increases its uncertainty interval exponentially — at 90 seconds without a poll, the uncertainty is ~10 ms; at 5 minutes, ~50 ms; at 30 minutes, the machine is considered "out of sync" and is excluded from Spanner's Paxos groups.

## Commit-Wait: Why External Consistency Holds

External consistency (linearizability + serializability) means: if transaction T1 commits before transaction T2 starts (in real time), then T1's commit timestamp is strictly less than T2's commit timestamp.

The proof:

1. T1 picks commit timestamp `s1` such that `s1 >= TT.latest()` at the moment of picking.
2. T1 commits by waiting for `TT.After(s1)` to return true (the "commit-wait").
3. T2 starts after T1 has committed, so T2's leader picks `s2` from a `TT.Now()` call that is *after* `TT.After(s1)` returned true — meaning `TT.earliest() > s1`.
4. Therefore `s2 > s1`.

The commit-wait is the price: every Spanner transaction waits `TT.uncertainty()` (typically 4-7 ms) before its commit is visible. The trade-off is no clock-skew-related inconsistencies across regions, which is what enables external consistency.

## Why Spanner Needs This

Compare with conventional systems:

- **Snapshot Isolation (PostgreSQL)**: each transaction picks a `now()` timestamp. Under clock skew, two transactions on different nodes can pick timestamps that disagree with real-time ordering. This is fine for snapshot isolation (which doesn't promise real-time ordering) but breaks linearizability.

- **Logical Clocks (Lamport, HLC)**: timestamps are derived from message passing, not from wall clocks. They correctly order events that have a happens-before relationship but cannot order concurrent events. Spanner needs to order concurrent events by real time.

- **Hybrid Logical Clocks (HLC)**: combine logical and physical clocks. They are correct under arbitrary clock skew but don't provide external consistency for concurrent events.

TrueTime's insight: if you bound the clock uncertainty and use commit-wait, you can recover external consistency. The bounded uncertainty is the engineering input; everything else follows.

## Critiques

1. **"It's just a bold engineering workaround."** TrueTime requires GPS receivers in every datacenter, atomic clock redundancy, and a custom kernel module. This is not a general solution — only a hyperscaler can afford it. The "TrueTime abstraction" is not really an abstraction; it's a tightly-coupled hardware-software stack.

2. **The commit-wait latency is wasted throughput.** Every transaction waits 4-7 ms that is "dead time" — no useful work is done. At scale, this is millions of dollars of CPU time per year on a Spanner cluster.

3. **Failure modes are catastrophic.** If a datacenter loses GPS reception and atomic clock sync simultaneously, TrueTime uncertainty grows unboundedly. Spanner's design guarantees safety (commit-wait grows with uncertainty, eventually blocking commits), but availability drops to zero — no transactions can commit.

4. **Spanner's commit-wait is not strictly necessary for external consistency.** Several academic proposals (e.g., "Adaptive Paxos" and "Luxo") have shown that external consistency can be achieved without commit-wait under looser assumptions. None has been productionized.

## Open-Source Equivalents

CockroachDB, TiDB, and YugaByte DB provide externally-consistent SQL without TrueTime. They use **Hybrid Logical Clocks** (HLC) instead:

- Each transaction's timestamp is `(physical_clock, logical_counter)`.
- The physical clock is the wall time; the logical counter is incremented when the physical clock would collide with another transaction.
- No commit-wait: clocks may skew, but the HLC's logical component disambiguates.

The trade-off: HLC requires extra RPC round-trips to ensure timestamps are correctly ordered across Paxos groups. CockroachDB pays ~1 extra RTT for cross-range transactions compared to Spanner. The lack of GPS-receiver infrastructure makes it affordable to deploy anywhere.

## Common Pitfalls

1. **Assuming `TT.Now()` returns a point.** Code that does `int64_t t = TT.Now().earliest;` is wrong — it discards the uncertainty. Always use `Now()` as an interval and reason about both endpoints.

2. **Forgetting commit-wait is on the critical path.** A Spanner transaction that does `BEGIN; INSERT INTO orders VALUES (...); COMMIT;` pays the Paxos RTT (~5-10 ms) + the commit-wait (~4-7 ms). The commit-wait is not parallelizable with the Paxos write.

3. **Treating TrueTime uncertainty as constant.** In production, `TT.uncertainty()` varies 1-7 ms normally, but spikes to 50+ ms during GPS receiver handoffs. Production monitoring must alert on sustained uncertainty > 10 ms.

4. **Confusing TrueTime with NTP.** NTP provides millisecond-precision time, not microsecond-precision intervals. NTP's drift rate (50-500 ms/day = 5-50 µs/sec) is far higher than TrueTime's (100 ppm = 100 µs/sec on a typical crystal). NTP is unsuitable for TrueTime-like commit-wait protocols.

5. **Assuming external consistency comes for free.** Spanner's external consistency requires TrueTime + the commit-wait rule + the leader-lease protocol + the Paxos-replicated timestamps. Removing any one breaks the property. Naive implementations that copy just TrueTime and skip the other parts produce subtly incorrect systems.

## References

- [Spanner: Google's Globally-Distributed Database](https://research.google/pubs/pub39966/) (OSDI 2012) — the original TrueTime description
- Wilson Hsieh, "[Spanner and TrueTime in Google's Globally-Distributed Database](https://www.youtube.com/watch?v=ql666uYU3qk)" (Google Tech Talk)
- [CockroachDB: How CockroachDB Uses HLC for Distributed Consistency](https://www.cockroachlabs.com/blog/cockroachdb-living-without-true-time/)
- David Karger et al., "[Consistency in Distributed Systems](https://sigops.org/s/conferences/hotos/2021/)" (HotOS 2021)
- [Lamport: Time, Clocks, and the Ordering of Events in a Distributed System](https://lamport.org/pubs/pubs.html#time-clocks) — the foundation
- [Spanner TrueTime internals (Google Research blog)](https://research.google/pubs/pub48286/)
