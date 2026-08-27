# Hybrid Logical Clocks (HLC)

A hybrid logical clock produces an O(1)-size timestamp that buys two properties at once:
it orders events by causality the way a Lamport clock does, and it never drifts far from
the wall clock the way a physical clock does. One scalar-ish value can therefore drive both
"which write wins" and "how stale is this read". The design comes from Kulkarni,
Demirbas, Madeppa, Avva and Leone, "Logical Physical Clocks" (OPDIS 2014), and it powers
timestamping in CockroachDB, YugabyteDB and MongoDB. Background on Lamport clocks, vector
clocks, dotted version vectors and interval tree clocks is in
[Clocks & Ordering](clocks-ordering.md) - this page assumes you know what a happened-before
edge is and moves straight to what those clocks cannot do.

## What Lamport and Vector Clocks Cannot Express

A Lamport counter gives you a partial-order-respecting total order, but the numbers carry
no information about real time. After a few minutes of traffic, a Lamport clock can sit at
47,382,111 while the wall clock says 10:02:00 - the gap is arbitrary. That makes plain
logical clocks unusable for questions real systems ask constantly:

- "Is this cached page older than 60 seconds?" (TTL semantics need physical meaning.)
- "Give me a consistent snapshot as of 10:02:00." (Snapshot cuts need wall-clock cuts.)
- "Bound this replica's staleness to 250 ms." "Show me the commit timestamp." (Staleness
  bounds and humans both compare against UTC.)

Vector clocks fix causality completeness but not this: they are O(n) in size and to
compare, and their components are still unrelated to physical time - storing a vector
per key is why Dynamo-style systems paid real bytes for conflict detection. The naive
fix - run a Lamport clock and a wall clock side by side - fails because the two values
are updated by different rules and diverge: a decision made with one can contradict the
other, and snapshots cut by wall time can silently violate causality captured by the
logical side. HLC's move is to fold both into one timestamp with one update rule.

## Why "Just Sync the Wall Clock" Fails

If NTP made clocks agree, you would stamp events with `CLOCK_REALTIME` and be done. It
does not, for structural reasons:

- **Drift between syncs.** A typical quartz oscillator is off by 20-100 ppm. Uncorrected,
  that is roughly 1.7-8.6 seconds per day. NTP corrects continuously, but between
  corrections a host walks away from its peer.
- **Sync quality is bounded, not exact.** Well-tuned LAN deployments land within a few
  milliseconds of a local stratum source; across the WAN, tens of milliseconds is normal.
  Two hosts are never equal - only within an error bound.
- **Steps happen.** On large corrections chrony/ntpd can step the clock instead of slewing
  it. VM migrations, host resumes and cloud live-maintenance also produce jumps.
  `CLOCK_REALTIME` is not monotonic; a timestamp can go backwards.
- **Leap seconds.** UTC inserts a 23:59:60 second. The June 2012 insertion froze servers
  at Reddit, Mozilla and LinkedIn when Java runtimes spun on the kernel's handling of
  the extra second. The last inserted leap second was December 31, 2016, and CGPM 2022
  Resolution 2 commits metrologists to abolishing leap seconds by 2035 - but until then,
  smeared implementations (Google, AWS smear over 24 hours) and non-smeared hosts
  disagree by up to 1 second around the event.

So physical timestamps alone give you collisions (same millisecond), non-monotonicity
(backwards steps), and no causality (a response can carry a smaller timestamp than its
request). HLC is designed to survive exactly this environment.

## The Clock State

The persistent timestamp is a pair `(l, c)`:

- `l` - the logical time. It is a physical-style reading (same units as the wall clock)
  but it is only ever moved forward: `l` is the maximum wall-clock reading this process
  has ever directly observed or heard about via a message.
- `c` - a counter disambiguating events that share the same `l`.

The local physical reading `pt()` (what `CLOCK_REALTIME` says now) is an input to the
update rules, not part of the timestamp. Implementations ship `(l, c)` as a fixed-size
struct: CockroachDB stores a 64-bit wall-nanoseconds field plus a 32-bit logical
counter; YugabyteDB's hybrid time packs physical milliseconds into the high-order bits
of a 64-bit integer with the counter in the low-order bits, so comparing the integer
compares the HLC.

## The Update Rules

On every event - local action, message send, or message receive - the clock advances:

```text
state: l, c              # persistent timestamp (l, c)
       pt()              # current local physical reading

local / send event:
    l' = max(l, pt())
    c' = c + 1   if l' == l          # same instant -> bump counter
       = 0      otherwise            # physical time advanced -> fresh instant
    l = l'

receive message carrying (lm, cm):
    l' = max(l, pt(), lm)
    if l' == l:         c' = max(c, cm) + 1   # our instant survives; dominate both counters
    elif l' == lm:      c' = cm + 1           # sender's instant dominates ours
    else:               c' = 0                # local physical time dominates: fresh instant
    l = l'
```

Two sharp edges hide in those rules, and both are about the counter:

- When the receiver already sits at the same `l` as the message (`l' == l`), the new
  counter must beat both sides: `max(c, cm) + 1`. A form of the receive rule quoted as
  "take the message counter plus one" has two holes here. If the incoming counter is
  larger than yours, causality breaks (your receive timestamp lands below the message's).
  If your own counter is larger than the incoming one, per-process monotonicity breaks
  (your clock moves backwards). Taking the max before incrementing closes both, and this
  is what production implementations do - CockroachDB's `hlc.Clock.Update` keeps the
  larger logical counter and then increments on the next tick.
- The receive rule is monotone but not idempotent: receiving the same message twice
  bumps `c`. Protocol code should merge timestamps explicitly, not replay them.

A worked example, times in abstract units:

```text
node A: pt=100                      node B: pt=100
  e1: local  -> (100, 1)
  e2: local  -> (100, 2)            # counter breaks the same-instant tie
  send(e2) --msg(100,2)--> B
                                    e3: recv -> l'=max(100,100,100)=100
                                              tie -> c'=max(0,2)+1=3   (100,3)
                                              # > (100,2): causality held
node A: pt jumps to 105
  e4: local  -> (105, 0)            # physical advanced, counter resets
```

## Properties

1. **Causality preservation.** If event `e` happened-before `f` (same process, or `f`
   received a message from `e`'s process carrying `e`'s timestamp), then
   `(l_e, c_e) < (l_f, c_f)` lexicographically - the `max` in each rule plus the
   counter rules make every case go through; the simulation below checks it.
2. **Bounded divergence from physical time.** `l - pt` only becomes positive when this
   node hears about a wall-clock reading ahead of its own. If every node's clock is
   within `epsilon` of true time and you reject incoming timestamps beyond
   `pt() + epsilon`, then `l - pt <= epsilon` forever. This is the property that lets a
   manager treat HLC comparisons as approximately UTC comparisons.
3. **O(1) size and compare.** 96 bits in CockroachDB versus O(n) for vectors; comparison
   is two integer compares.
4. **Per-process monotonicity.** A node's own timestamps never decrease, even when NTP
   steps the physical clock backwards: `l` simply stays put until `pt()` catches up, and
   the counter churns meanwhile.

## Failure Modes

- **Backwards NTP step.** Harmless to ordering, but the `l - pt` gap widens by the step
  size, so staleness-style reasoning gets conservative until real time catches up.
- **A node with a fast clock** (or a buggy peer) injects future timestamps; the `max`
  rule then pins every node it talks to. CockroachDB's answer is enforcement: with a
  default maximum clock offset of 250 ms, a node that observes a peer timestamp too far
  ahead kills the process rather than risk ordering decisions built on a lie (see "Max
  clock offset enforcement" in the CockroachDB docs below).
- **HLC is not a total order.** Concurrent events on different nodes can share the same
  `l` with incomparable counters. If you need a strict total order (last-writer-wins
  storage, for example), break ties with a node ID - and understand that such a tie-break
  is arbitrary, which is precisely why CockroachDB adds uncertainty waits around reads
  instead of pretending equal timestamps are ordered.

## Who Uses HLCs

| System | Where the HLC appears | Enforcement mechanism |
| --- | --- | --- |
| CockroachDB | Every transaction and write timestamp | NTP required; default max offset 250 ms; offending nodes self-terminate; uncertainty intervals on reads |
| YugabyteDB | Hybrid time on every DocDB write and snapshot | Clock sync via chrony/NTP checked at startup; skew beyond tolerance aborts operations |
| MongoDB | Cluster time on oplog entries (BSON Timestamp: 32-bit seconds + 32-bit ordinal) | Causally consistent sessions (since 3.6) track and advance cluster time; no hard offset enforcement |

For contrast, Spanner solves the same problem from the hardware side - bounded
uncertainty from GPS plus atomic clocks - and pays for it with specialized
infrastructure. See [TrueTime](../fundamentals/truetime.md). HLC's bet is that software
NTP sync plus a logical component gets you most of the benefit on commodity machines.

Note on attribution: HLC is often misattributed to Lloyd et al. 2011 (the COPS paper)
because COPS used client-supplied physical-ish timestamps; the HLC algorithm and proofs are Kulkarni et al. 2014.

## A Runnable Simulation

The checker below is the complete, self-contained program used for this page
(deterministic output, standard library only). It runs a tiny 3-node cluster through
2000 randomized schedules of 400 events each - local actions, message deliveries
between drifting clocks, and occasional backwards NTP steps - asserting after every
event that a received message's timestamp orders below the receiver's new timestamp,
and that no node's timestamp ever moves backwards:

```python
import random

class HLC:
    def __init__(self, name, wall):
        self.name, self.wall, self.l, self.c = name, wall, wall(), 0
        self.ts = (self.l, self.c)

    def local(self):
        pt = self.wall()
        if max(self.l, pt) == self.l:      # pt() <= l: same instant, bump counter
            self.c += 1
        else:                              # physical time moved: fresh instant
            self.l, self.c = pt, 0
        self.ts = (self.l, self.c)

    def recv(self, lm, cm):
        pt = self.wall()
        l = max(self.l, pt, lm)
        if l == self.l:
            self.c = max(self.c, cm) + 1   # our instant survives: dominate both counters
        elif l == lm:
            self.c = cm + 1                # sender's instant dominates ours
        else:
            self.c = 0                     # local physical time dominates: fresh instant
        self.l = l
        self.ts = (self.l, self.c)

def hlc_le(a, b):
    return a[0] < b[0] or (a[0] == b[0] and a[1] <= b[1])

def run(seed):
    rng, T = random.Random(seed), {"a": 1000, "b": 1005, "c": 998}
    nodes = {n: HLC(n, (lambda n=n: T[n])) for n in T}
    for _ in range(400):
        n = rng.choice(sorted(nodes))
        before = nodes[n].ts
        if rng.random() < 0.45:
            m = rng.choice([x for x in sorted(nodes) if x != n])
            nodes[n].recv(*nodes[m].ts)
            assert hlc_le(nodes[m].ts, nodes[n].ts)    # causality across this message
        else:
            nodes[n].local()
        assert hlc_le(before, nodes[n].ts)             # per-node monotonicity
        if rng.random() < 0.03:                        # NTP steps the clock BACKWARDS
            T[n] = max(0, T[n] - rng.randint(1, 60))

for seed in range(2000):
    run(seed)
print("2000 random schedules x 400 events: causality and monotonicity held in all cases")
```

Real output of the checker:

```text
2000 random schedules x 400 events: causality and monotonicity held in all cases
```

## Interview Sharp Edges

- "Why not just a Lamport clock plus a separate wall clock?" Every decision that mixes
  the two (snapshot cuts, TTLs, staleness bounds) has to reconcile independent state
  machines; HLC makes one value satisfy both predicates with proofs.
- "What happens if a node's clock is 10 minutes fast?" Its timestamps inject `l` values
  far ahead; the `max` rule pins peers until real time catches up - and CockroachDB
  self-terminates the offending node outright.
- "Does HLC give you linearizability for free?" No. It gives you timestamps that respect
  causality and approximately track UTC; turning that into external consistency still
  needs uncertainty waits (Spanner) or max-offset-bounded read rules (CockroachDB).
- "Counter overflow?" `c` only grows when events land inside the same nanosecond
  repeatedly; 32-bit counters with per-instant resets make this a non-issue. But a HLC
  under a tight event loop is a monotonic counter, not a clock reading - do not log it
  and expect humans to read it as UTC.

## References

- Logical Physical Clocks - Kulkarni, Demirbas, Madeppa, Avva, Leone (OPDIS 2014): https://doi.org/10.1007/978-3-319-14472-6_2
- CockroachDB architecture - Time and hybrid logical clocks, max offset enforcement: https://www.cockroachlabs.com/docs/stable/architecture/transaction-layer
- YugabyteDB docs - YugabyteDB timekeeping with hybrid time: https://docs.yugabyte.com/preview/architecture/core-functions/yugabyte-timekeeping-hybrid-time/
- MongoDB manual - BSON Timestamps (seconds + ordinal, the cluster-time carrier): https://www.mongodb.com/docs/manual/reference/bson-types/
- CGPM 2022 Resolution 2 - leap second discontinuation: https://www.bipm.org/en/cgpm-2022/resolution-2
