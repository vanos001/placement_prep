# Clock and Time Assumptions: What `time.now()` Silently Promises

## Overview

Almost every distributed system eventually contains a line of code that reads the clock and trusts it: to timestamp an event, to measure how long something took, to decide which of two writes is newer, or to expire a session. Each use hides a different assumption — that time moves forward uniformly, that wall-clock differences measure durations, that synchronized clocks imply ordered events, and that a timestamp written on one machine can be compared with one written on another. None holds in general, and each fails in a way that is invisible in unit tests, where the clock is quiet and the machines are one.

The failure modes are not exotic: NTP corrections step clocks backward, leap seconds make civil time non-monotonic, operating systems expose at least two clocks with different contracts, and timezones turn every naive timestamp string into a per-user interpretation. The corrected toolkit is small and well understood — monotonic clocks for durations, logical clocks for ordering, uncertainty-aware APIs for wall-clock coordination — but each member is scoped to exactly one of the failed assumptions, which is why using the wrong member is the standard time bug. The sibling chapter on network assumptions carries the leap-second incident narrative; the focus here is on the assumptions themselves.

## Assumption 1: "Time Moves Forward Uniformly"

### The taught rule

Call the clock, get a time; call it again later, get a larger time. Time advances at one second per second.

### The hidden assumptions

- The clock being read is the *right clock for the job*. POSIX systems expose at least `CLOCK_REALTIME` (wall time, adjusted by NTP, can jump) and `CLOCK_MONOTONIC` (never goes backward, but its zero point is unspecified and it means nothing on another machine). Code that measures durations with `gettimeofday`-style APIs assumes the wall clock never jumps.
- Uniformity is a property of *ideal* time, not of *civil* time. UTC inserts leap seconds (37 since 1972); POSIX smears them by pretending every day has exactly 86,400 seconds, so any implementation that honors leap seconds steps backward or repeats a second.
- NTP discipline is not "keep time exact"; it is "keep time convergent." For small offsets the daemon *slews* (adjusts the tick rate, typically capped around 500 ppm, so recovering a 1-second error takes many minutes); for large offsets it *steps* the clock, which can move it backward or forward by the whole error at once.
- Manual reconfiguration is a real event: a sysadmin correcting a VM's clock, a cloud instance restoring a drifted clock, a container image with the wrong date — all are backward jumps that no wall-clock difference-based code survives.

### Counterexample

Measure a 300 ms operation with the wall clock while an NTP correction steps the clock 500 ms backward between the two reads. The measured duration is -200 ms. Nothing crashes — but every downstream consumer of a non-negative duration is now exercising an untested branch. The canonical production shape is the Cloudflare RRDNS incident at the 2016–2017 leap second, documented in the sibling chapter: a clock that stepped during query processing produced a negative elapsed time that flowed into a computed TTL, and resolvers were served negative values. Go's subsequent addition of a monotonic reading inside `time.Now()` — so that subtracting two `time.Now()` values uses the monotonic clock — is the language-level acknowledgment that this bug class is structural, not incidental.

### What changes when the assumption is removed

Corrected statement: *measure durations with a monotonic clock, timestamp events with the wall clock, and never use the wall clock's differences as durations.* Concretely: `System.nanoTime()` in Java, `time.monotonic()` in Python, `CLOCK_MONOTONIC` in C, `time.Since()` in Go. Keep the two uses in separate types where the language allows, because the compiler is the only reviewer that never forgets which clock was intended. Also state the inverse explicitly: a monotonic clock is useless across processes and machines — its epoch is arbitrary, so it cannot be serialized into a timestamp at all.

### Consequences

The interview probe "why does Go have two clocks in one `time.Time`?" or "what breaks when the clock steps backward?" has a senior answer that names the two-clock contract, the 500 ppm slew limit (so a large error cannot be hidden quickly), and the leap-second history — then volunteers that expiry logic is the third victim: a token issued with a stepped-forward clock expires immediately; one issued before a backward step lives longer than intended.

## Assumption 2: "Wall-Clock Time Measures Durations"

### The taught rule

A deadline is a timestamp: store "this lease is valid until T" or "this token expires at T," and compare the current wall clock against T.

### The hidden assumptions

- A stored wall-clock deadline silently assumes the *reading clock* will remain synchronized to the *writing clock* for the lifetime of the deadline. Any drift between the two machines during that window shifts the effective validity — in both directions.
- Expiry checks compare against values that can move: a lease "valid until T" on a clock running 2 seconds fast is effectively 2 seconds shorter; on a slow clock it outlives its promise. Lease systems therefore need a safety margin at least as large as the clock error bound between participants.
- Retry and timeout logic built on wall-clock deadlines inherits Assumption 1's jump problem: a backward step extends every outstanding deadline by the size of the step, fleet-wide, all at once.
- Durations measured across process restarts assume the clock moved forward across the restart; VM snapshots and containers restored from checkpoints can violate even that.

### Counterexample

Two services share a 30-second lease: service A grants it by writing `expires_at = now + 30s` on its clock; service B checks renewal by comparing its own clock against that timestamp. With a 1-second clock error bound between them, the overlap-free handover requires B to treat the lease as expiring 1 second *early* and A to grant 1 second late — the uncertainty-aware pattern. Without margins, the failure is a split brain: B still believes it holds the lease in the window where A has already re-granted it, and two writers proceed under one lease. The consensus-and-leases chapter develops the mechanism and its safety argument; the point here is that the bug enters through the *timestamps*, not the lease protocol — the protocol was fine under its unstated clock-synchronization precondition.

### What changes when the assumption is removed

Corrected statement: *a wall-clock deadline is a promise about two clocks, not one, and its safety margin must cover the error between them.* Use short leases sized against the measured clock error (this is why leases are seconds, not hours), pass monotonic-relative durations for in-process deadlines, and prefer uncertainty-aware time APIs where correctness demands it. Google's TrueTime API in Spanner is the reference design: it returns an interval `[earliest, latest]` instead of a point, and Spanner *waits out the uncertainty interval* before committing, which converts bounded clock error into externally consistent ordering.

### Consequences

The interview probe "how long should a lease be?" is this assumption: the expected answer derives the length from clock error bounds and retry characteristics, not convenience. The same reasoning explains why token expiries and lock timeouts all carry the sentence "assuming clocks are synchronized within N seconds" that nobody wrote down.

## Assumption 3: "Synchronized Clocks Mean Ordered Events"

### The taught rule

If all machines sync via NTP, compare timestamps to order events: the write with the newer timestamp wins, and the log sorted by timestamp is the true history.

### The hidden assumptions

- NTP synchronization has an error bound (milliseconds on well-run LANs, worse across WANs, unbounded across clock steps), and an error bound is not zero. Two events closer together than the bound have an *unknowable* order from timestamps alone.
- Timestamp order is not *causal* order. If A learns about event e1 and then causes e2, causality says e1 precedes e2 — but if e2 happens on a machine whose clock is slightly behind, the timestamp order says otherwise. Causality is captured by happens-before relationships (Lamport's formulation), not by any single clock.
- Conflict resolution by newest-timestamp (last-write-wins) turns clock error into silent data loss: the "wrong" winner overwrites the "right" value with no error and no trace beyond the two timestamps themselves.
- Even a *correct* timestamp order may be unrepresentable: distributed systems can generate events with identical timestamps at high rates, and tie-breaking needs a deterministic secondary key (node ID, sequence number) that most designs never specify.

### Counterexample

A distributed database resolves concurrent updates to one row by last-write-wins on client-supplied timestamps. A client with a clock running 60 seconds fast retries a failed write; its retried write — semantically *older* in causality than the write that already succeeded — carries a timestamp 60 seconds in the future and wins every subsequent conflict for a long window. Every legitimate write made in the meantime is silently shadowed. The fix families are all known: Lamport clocks or vector clocks to capture happens-before (the clock only guarantees that a *message's receipt* is ordered after its send, never global agreement), server-side timestamp assignment (the client's clock is an input, not an authority), and bounded-uncertainty designs like Spanner's that wait out the error window when external ordering is required. The documented pattern of client clock skew poisoning last-write-wins conflict resolution is precisely why production databases moved toward server-side or hybrid logical clocks.

### What changes when the assumption is removed

Corrected statement: *order by causality when correctness requires it; use timestamps as a tie-broken heuristic only when the conflict cost is acceptable and known.* Concretely: logical clocks (Lamport for total order among communicating processes, vector clocks for concurrency detection), hybrid logical clocks when wall-clock-ish ordering is wanted with causal safety, and deterministic conflict rules independent of which clock happened to be ahead. And state what "synchronized" meant: NTP gives an error *bound*, not equality, and steps violate the bound transiently by design.

### Consequences

"Design an ordering guarantee for events from multiple regions" is a staple system-design prompt, and its escalation ladder is exactly this chapter: timestamps → clock skew → Lamport/vector clocks → uncertainty windows. The interview-visible skill is naming the naive design's silent precondition: it holds only if clock error stays below the minimum gap between events.

## Assumption 4: "Timestamps Can Be Compared Across Machines"

### The taught rule

Serialize `now` as an ISO-8601 string (or epoch integer), ship it in the payload, and any receiver can parse and compare it.

### The hidden assumptions

- A timestamp without an offset is a *local* reading. `2025-03-04T09:00:00` is meaningful only in some timezone the string does not name; comparing it against a UTC timestamp silently produces a shift equal to the unrecorded offset — including historical DST rules, which differ per zone and change over time.
- Epoch-based integers hide a different triple of assumptions: the epoch origin (Unix vs Windows vs GPS vs TAI), the unit (seconds, milliseconds, microseconds, nanoseconds), and the timescale (POSIX seconds-that-ignore-leap-seconds vs UTC-with-leap-seconds). Cross-language mismatches here are ordinary: milliseconds-vs-seconds bugs pass every test with small test fixtures.
- Precision mismatch silently truncates: a nanosecond-precision writer and a millisecond-precision reader make every sub-millisecond gap look like equality, feeding tie-breaking logic (Assumption 3) that has no real ties.
- Even well-formed, offset-explicit strings are only comparable if both sides agree on the calendar and the leap-second policy — and "UTC" from a leap-second-aware source can contain a second POSIX systems have never heard of.

### Counterexample

A batch job writes `started_at` using the server's local timezone (a wall string without offset). A reporting service in UTC reads the strings, parses them as UTC, and computes job durations. During DST transitions the parse is wrong by one hour for jobs that started in the affected window — and for the local hour that *does not exist* (spring forward) or *occurs twice* (fall back), the naive parse either fails or collapses two distinct runs into one. The corrected encoding discipline is small and absolute: store and transmit UTC with an explicit offset (or epoch in a stated unit), keep timezone conversion strictly a presentation-layer concern, and reject at parse time any timestamp that lacks the information needed to interpret it. The "validate at boundaries" pattern from the testing chapter applies directly: the boundary is where the string becomes a time value, and that is where ambiguity must be refused.

### What changes when the assumption is removed

Corrected statement: *a timestamp is only comparable if its encoding carries epoch, unit, offset, and timescale — treat any timestamp missing one of those as unparsable input, and normalize at ingestion.* Adopt one internal representation (UTC epoch in one stated unit), one canonical wire format (offset-explicit ISO-8601), and round-trip tests across DST boundaries as part of the contract tests the API-contracts chapter describes. For scheduling rather than recording, invert the rule: cron-like systems need wall-clock semantics (run at 09:00 local), which is why the same system often needs *both* kinds of time and must never conflate them.

### Consequences

The interview probe "a user in one region sees reports shifted by one hour; where do you look?" walks this assumption set: encoding, storage-layer timezone handling (databases differ on `TIMESTAMP` vs `TIMESTAMP WITH TIME ZONE` semantics), application defaults, and presentation. The durable takeaway: comparability is a property of the *pair* of encodings, not of the timestamp itself — and the cheap defense is refusing to store anything that cannot be unambiguously re-read.

## Interview Questions

1. **Why does measuring elapsed time with `System.currentTimeMillis()` sometimes return a negative value, and what is the fix?** Wall time can step backward (NTP corrections, leap-second handling); the difference of two wall readings is not a duration. Fix: monotonic clocks — `System.nanoTime()`, `CLOCK_MONOTONIC`, Go's monotonic `time.Since()` — and keep wall clocks for timestamps only.
2. **Your last-write-wins store lost writes after a client had a 60-second-fast clock. Reconstruct the mechanism and name two fixes.** The future-dated timestamp wins every conflict until real time catches up, silently shadowing newer-in-causality writes. Fixes: server-side or hybrid logical clocks for ordering, or vector clocks/causal conflict resolution; alternatively bounded-uncertainty time (TrueTime-style) with commit waits.
3. **What does NTP actually guarantee, and how does it affect lease length?** An error bound plus slew/step behavior: small offsets are slewed at a limited rate, large ones stepped. A lease must be sized so its safety margin exceeds the clock error bound between grantor and holder — otherwise the same lease can be validly held by two parties.
4. **Two services log the same request with timestamps 400 ms apart. Can you conclude the request hit the second service after the first?** Not from timestamps alone: the machines' clocks differ by an error bound, so events closer than that bound have unknowable order. Establish happens-before via correlation/context propagation or logical clocks; use timestamps only where the gap dwarfs the error.
5. **A stored timestamp string parses differently on two servers during a DST change. What went wrong structurally?** The encoding omitted the offset (or the parser defaulted to local time), so interpretation became machine-dependent. Structural fix: store UTC with explicit offsets, parse strictly at the boundary, and never let timezone conversion into the persistence layer.

## Key Takeaways

- There are two clocks with two contracts: monotonic for durations (never backward, meaningless across machines) and wall for timestamps (comparable, but can jump). Using one for the other's job is the root of most time bugs.
- NTP provides an error bound, not equality; leases, deadlines, and retries must carry a margin derived from that bound, and a stored wall-clock deadline is a claim about two clocks.
- Timestamp order is not causal order; only happens-before (logical clocks) or uncertainty-aware designs (TrueTime-style commit waits) support ordering claims that survive clock skew.
- Last-write-wins converts clock error into silent data loss — no error message, only wrong data, which makes it among the most expensive assumption failures in this collection.
- Comparability is a property of encodings: epoch, unit, offset, and timescale must all be explicit; anything less is local text that someone else's clock will reinterpret.

## Cross-References

- [Network and distributed assumptions](network-distributed.md) — the leap-second incident narrative and the synchronized-clocks fallacy among the Eight Fallacies.
- [Consensus and leases](../connection-atlas/consensus-leases.md) — lease-based failure detection and the clock-error safety argument.
- [Timeouts and retries](timeouts-and-retries.md) — deadlines as propagated budgets, the other consumer of the same clock contracts.
- [Concurrency and scheduling](concurrency-and-scheduling.md) — sleep durations and scheduler time at the single-machine layer.
- [Lamport clocks](../../distributed/fundamentals/lamport.md) — happens-before and logical time, the ordering foundation.
- [Vector clocks](../../distributed/fundamentals/vector-clocks.md) — concurrency detection when timestamps cannot decide.
- [TrueTime](../../distributed/fundamentals/truetime.md) and [the time page](../../distributed/fundamentals/time.md) — uncertainty intervals and the survey of timekeeping in distributed systems.
- [Testing assumptions](testing-assumptions.md) — clock-controlled code and why time-dependent tests pass deterministically.
