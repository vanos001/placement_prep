# Distributed Mutual Exclusion: Message-Economy Algorithms

Before leases, quorum locks and coordination services, the question "who may
enter the critical section?" was answered by pure message-passing algorithms
with provable message counts. They are the right vehicle for understanding
what coordination *costs*: Lamport's algorithm spends `3(N-1)` messages per
entry, Ricart-Agrawala gets that to `2(N-1)`, Maekawa trades correctness
headroom for `O(sqrt(N))`, and token schemes pay nothing at all when nobody is
contending. None of them survive careless deployment on real networks - and
knowing exactly why is the point of studying them.

This page sits in the algorithm layer between [Lamport clocks](./lamport.md)
(which define the timestamp order these algorithms rely on), [distributed
locks as practiced](./distributed-locks.md) (lease-based systems that replaced
them), and [ZooKeeper](./zookeeper.md) (the coordination service most teams
actually reach for). Clock semantics more broadly are covered in
[time](./time.md).

## The model every algorithm assumes

The classical setting is N processes, reliable asynchronous channels, and no
shared memory. Correctness properties:

- **Mutual exclusion**: at most one process is in the critical section (CS).
- **No deadlock**: some process eventually enters when the CS is idle.
- **No starvation** (the stronger guarantee some algorithms give): every
  request is eventually granted.
- **Ordering / fairness**: entries respect the happens-before order of
  requests (Lamport's definition of fairness).

The failure model is benign: no crashes, no message loss. That is precisely
why these algorithms became textbook classics *and* production rarities - each
was later patched, at real complexity cost, to tolerate the failures the model
pretends away. Keep this in mind while reading the message-count tables: the
numbers are for the failure-free case.

## Permission-based algorithms

### Lamport: total order via broadcast

Each process keeps a Lamport clock. To enter:

1. Broadcast `REQUEST(ts, i)` to all others; store it locally.
2 On receiving `REQUEST(ts, j)`: reply immediately *unless* you are
   requesting or in the CS and your own request has lower `(ts, i)`, in which
   case defer the reply.
3. Enter the CS when `2(N-1)` messages are accounted for: a REPLY from
   everyone else, and your REQUEST at the head of everyone's (acknowledged)
   queue - in practice, implemented as "REPLY from all".
4. On exit: broadcast `RELEASE(ts, i)`; each receiver removes the entry.

Counting: `N-1` requests + `N-1` replies + `N-1` releases = **`3(N-1)`
messages per entry**. The release broadcast is what later algorithms shave
off: it is pure bookkeeping, since the deferred-reply rule of
[Ricart-Agrawala](#ricart-agrawala-dropping-the-release) makes explicit
releases redundant.

### Ricart-Agrawala: dropping the release

Ricart and Agrawala's 1981 observation: the `RELEASE` phase is unnecessary if
each process only defers replies to *lower-priority* requests. A process
holding a higher-priority pending request will reply to you on its exit
implicitly, because by then your request outranks its own. So:

- `REQUEST(n-1)`, then wait for `n-1` REPLYs; no release broadcast.
- **`2(N-1)` messages per entry** - the classic bound.

The deferred-reply bookkeeping is the subtle part: each process maintains a
set of requests it has seen but deliberately not answered, and drains it in
timestamp order. The optimization most implementations add ("RA-implicit"):
if two contenders exchange requests, the one with the *higher* priority does
not reply to the lower one at all - its own outstanding REQUEST already tells
the loser everything the reply would. Under contention this cuts real
traffic below the `2(N-1)` bound; our demo measures it on a synthetic trace.

### Maekawa: voting sets and the deadlock caveat

Maekawa's insight: a process does not need *everyone's* permission, just a
majority-ish **voting set**. Assign each of N processes a set of `K ~
sqrt(N)` peers such that any two sets intersect (a finite projective plane
construction gives exactly this). Request permission only from your set;
enter when all reply.

- **Messages per entry: `O(sqrt(N))`** down, but the fine print is brutal.
- Intersection without *sufficient* coordination means two processes can each
  collect "yes" from their overlapping sets and enter simultaneously unless
  voters are programmed to lock - and locking voters deadlock: A waits on a
  voter held by B, B waits on a voter held by A. The fixes (timestamp-based
  abort of pending grants, i.e. probe-and-kill) add complexity that mostly
  cancelled the message savings in practice. Maekawa matters today as the
  intellectual ancestor of quorum systems - see [quorum systems](../advanced/quorum-systems.md) for the modern treatment.

### Comparison table

| algorithm       | msgs/entry (free CS) | msgs/entry (k contenders) | starvation | failure Achilles heel        |
|-----------------|----------------------|---------------------------|------------|------------------------------|
| Lamport         | 3(N-1)               | 3k(N-1) per epoch         | no         | N-wide broadcast per entry   |
| Ricart-Agrawala | 2(N-1)               | ~2k(N-1)                  | no         | one dead process stalls all  |
| RA + implicit   | 2(N-1)               | k(N-1) + C(k,2) + k(N-k)  | no         | same, slightly less traffic  |
| Maekawa         | ~2sqrt(N)            | ~2sqrt(N)                 | deadlock-prone naively | voting-set deadlock     |
| Suzuki-Kasami   | 0 (have token)       | N on first grab           | no (token) | token loss needs recovery    |
| token ring      | 0                    | 1 hop per hand-off        | no (token) | ring partition               |

## Token-based algorithms

### Suzuki-Kasami: the broadcast token

A single TOKEN message circulates logically; it carries a queue `Q` of pending
requests and an array `LN[]` of the last fulfilled request number per process.
To enter: if you hold the token, go now. Otherwise broadcast `REQUEST(i, seq)`
and wait. The token holder serves the queue in order, updating `LN`.

The economics are inverted relative to permission schemes: **zero messages
when the CS is uncontended** (you already hold the token), and N messages to
grab it the first time (the token holder broadcasts... rather, it sends the
token to the next requester after serving). The pathological case is token
loss on crash: unlike permission algorithms, which degrade to "requests never
granted", a lost token requires an explicit election/recovery protocol -
bulletin-board style recovery (re-collect everyone's `LN[]` and regenerate the
queue) was the standard add-on.

### Token ring: the physical circuit

Arrange the N processes in a unidirectional ring; the token travels
ring-neighbor to ring-neighbor. Per CS entry the marginal cost is **1 hop**
(the token must physically arrive). Entry latency under no contention is up
to N hops *waiting* for the token to arrive, which is the trade: minimal
message load, worst-case latency proportional to ring size, and a
partitioned ring is a lost token. Practical influence: the design of
in-kernel and bus-protocol arbitration, more than datacenter systems.

## The demo: theory versus a real trace

The closed-form numbers hide the contention structure. The script below
simulates 64 time slots over N=8 processes where each slot spawns an epoch of
`k` simultaneous contenders (seeded, deterministic), then totals messages for
Lamport, Ricart-Agrawala and RA-with-implicit-replies. Assertions pin the
closed forms at `k=1` and `k=N` so the epoch arithmetic cannot silently drift.

```python
#!/usr/bin/env python3
"""Message-count simulation: Lamport vs Ricart-Agrawala vs RA+implicit-reply
on a synthetic critical-section request trace (pure stdlib, deterministic).

Model
-----
N processes. Time is slotted; in each slot a seeded subset of processes
issue CS requests. All requests in one slot form an "epoch" of k <= N
contenders; Lamport timestamps totally order them and they enter the CS
one after another.

Message counting per epoch of k contenders (n = N):
  Lamport    : every request is ACKed, RELEASE broadcast on exit
               -> 3*(n-1) per entry  => 3*k*(n-1) per epoch
  RA         : REQUEST(n-1) + REPLY(n-1) per entry (replies may be
               deferred but are still sent) => 2*k*(n-1) per epoch
  RA-implicit (optimization): a contender that receives a strictly
               higher-priority REQUEST does NOT answer it -- its own
               REQUEST is proof it is out of the CS and will defer.
               Per contender pair exactly 1 reply flows (winner -> loser,
               on exit); only non-contenders reply explicitly to everyone:
                 requests:  k*(n-1)
                 replies :  C(k,2) + k*(n-k)
"""
import random

N = 8            # processes
SLOTS = 64       # time slots in the trace
SEED = 42


def epoch_cost(k, n):
    """Total messages exchanged by one epoch of k contenders (k >= 1)."""
    lamport = 3 * k * (n - 1)
    ra = 2 * k * (n - 1)
    ra_impl = k * (n - 1) + (k * (k - 1)) // 2 + k * (n - k)
    return lamport, ra, ra_impl


def build_trace(mean_k, rng):
    """One slot = one epoch; each process requests with prob mean_k/N."""
    p = mean_k / N
    epochs = []
    for _ in range(SLOTS):
        k = sum(1 for _proc in range(N) if rng.random() < p)
        if k:
            epochs.append(k)
    return epochs


def main():
    print(f"trace: {SLOTS} slots over N={N} processes, seed={SEED}")
    print()
    print(f"{'mean k':>6} | {'epochs':>6} | {'reqs':>5} | {'max k':>5} | "
          f"{'Lamport':>8} | {'RA':>8} | {'RA-impl':>8} | {'saved vs RA':>11}")
    print("-" * 74)
    for mean_k in (1, 2, 4, 8):
        rng = random.Random(SEED)
        epochs = build_trace(mean_k, rng)
        lam = sum(epoch_cost(k, N)[0] for k in epochs)
        ra = sum(epoch_cost(k, N)[1] for k in epochs)
        rai = sum(epoch_cost(k, N)[2] for k in epochs)
        saved = 100.0 * (ra - rai) / ra
        print(f"{mean_k:>6} | {len(epochs):>6} | {sum(epochs):>5} | {max(epochs):>5} | "
              f"{lam:>8} | {ra:>8} | {rai:>8} | {saved:>10.1f}%")

    # per-entry view at mean_k=4 (moderate contention)
    rng = random.Random(SEED)
    epochs = build_trace(4, rng)
    hist = {}
    for k in epochs:
        hist[k] = hist.get(k, 0) + 1
    print()
    print("epoch-size histogram at mean_k=4: " +
          ", ".join(f"k={k}:{hist[k]}" for k in sorted(hist)))
    entries = sum(epochs)
    lam = sum(epoch_cost(k, N)[0] for k in epochs)
    ra = sum(epoch_cost(k, N)[1] for k in epochs)
    rai = sum(epoch_cost(k, N)[2] for k in epochs)
    print()
    print(f"per-entry message cost ({entries} entries, mean_k=4):")
    print(f"  Lamport             {lam/entries:6.2f} msgs/entry   (theory 3(N-1)={3*(N-1)})")
    print(f"  Ricart-Agrawala     {ra/entries:6.2f} msgs/entry   (theory 2(N-1)={2*(N-1)})")
    print(f"  RA + implicit reply {rai/entries:6.2f} msgs/entry   (theory < 2(N-1) when contended)")

    # sanity checks against closed forms for single epochs
    assert epoch_cost(1, N) == (3*(N-1), 2*(N-1), 2*(N-1))
    assert epoch_cost(N, N) == (3*N*(N-1), 2*N*(N-1), 3*N*(N-1)//2)
    print()
    print("sanity: k=1 -> RA == RA-implicit == 2(N-1); "
          f"k=N -> RA-implicit = 1.5*N*(N-1) = {3*N*(N-1)//2} (25% below RA)")


if __name__ == "__main__":
    main()
```

```text
trace: 64 slots over N=8 processes, seed=42

mean k | epochs |  reqs | max k |  Lamport |       RA |  RA-impl | saved vs RA
--------------------------------------------------------------------------
     1 |     44 |    63 |     4 |     1323 |      882 |      859 |        2.6%
     2 |     58 |   135 |     5 |     2835 |     1890 |     1767 |        6.5%
     4 |     63 |   257 |     7 |     5397 |     3598 |     3150 |       12.5%
     8 |     64 |   512 |     8 |    10752 |     7168 |     5376 |       25.0%

epoch-size histogram at mean_k=4: k=1:2, k=2:4, k=3:13, k=4:22, k=5:15, k=6:4, k=7:3

per-entry message cost (257 entries, mean_k=4):
  Lamport              21.00 msgs/entry   (theory 3(N-1)=21)
  Ricart-Agrawala      14.00 msgs/entry   (theory 2(N-1)=14)
  RA + implicit reply  12.26 msgs/entry   (theory < 2(N-1) when contended)

sanity: k=1 -> RA == RA-implicit == 2(N-1); k=N -> RA-implicit = 1.5*N*(N-1) = 84 (25% below RA)
```

Reading the numbers: at zero-to-one contenders the algorithms are within a
few percent (the implicit-reply optimization has nothing to optimize); at
full contention (every process requests every slot, `k=N`) it saves exactly
25% over plain RA - the `C(k,2)` pairwise reply elimination. Lamport's
overhead is structural: the release broadcast costs a third of its budget no
matter what contention does.

## Why production systems do not use any of this

Every algorithm above assumes failure-free operation, and each has a single
well-known failure cliff:

- **Participant crash**: RA deadlocks (a dead process never replies); the fix
  (timeouts + heuristic abort) breaks the correctness proof.
- **Token loss** (Suzuki-Kasami, ring): exclusion is *satisfied* vacuously
  while liveness is destroyed; recovery protocols race against the token
  reappearing.
- **Network partition**: permission algorithms at least stay *safe* (no
  double entry) but lose liveness across the partition; token algorithms can
  lose the token into the minority side.

The systems that replaced them invert the economics: **leases** (time-bounded
grants that expire on their own, converting crash-failure into
wait-out-the-clock), **quorum acquisition** (grab a majority, so two
grant-holders imply intersection), and **coordination services** (ZooKeeper
recipes) where the lock is a znode with an ephemeral sequential marker and
watch-based hand-off. See [distributed locks](./distributed-locks.md) for
that stack, and [CAP](./cap.md) for why partition behavior dominates the
design space once real networks are assumed.

## Interview-grade questions this page equips you to answer

- Derive the `2(N-1)` bound and explain precisely which broadcast the
  implicit-reply optimization removes - and why the removed reply cannot
  carry information the loser needs.
- Why does Maekawa's `sqrt(N)` message saving not translate into deployed
  systems? (Answer with the deadlock scenario, not vibes.)
- Suzuki-Kasami sends the token *unsolicited* to the next requester after
  serving the queue: why is that N messages total for the first grab, and
  what invariant does `LN[]` maintain to make regeneration after loss safe?
- Where exactly does each algorithm break under a partition, and which class
  stays *safe* (if not live) - and why does that property survive into
  quorum-based lock services?

## References

1. Lamport, "Time, clocks, and the ordering of events in a distributed
   system", CACM 21(7), 1978,
   [doi:10.1145/359545.359563](https://doi.org/10.1145/359545.359563) -
   Section 3 contains the original mutual-exclusion algorithm and its
   anomaly-free ordering argument.
2. Ricart & Agrawala, "An optimal algorithm for mutual exclusion in computer
   networks", CACM 24(1), 1981,
   [doi:10.1145/358527.358537](https://doi.org/10.1145/358527.358537) -
   the `2(N-1)` bound and the deferred-reply protocol.
3. Maekawa, "A sqrt(N) algorithm for mutual exclusion in decentralized
   systems", ACM TOCS 3(2), 1985,
   [doi:10.1145/214438.214445](https://doi.org/10.1145/214438.214445) -
   voting sets and the mutual-exclusion-by-intersection construction.
4. Suzuki & Kasami, "A distributed mutual exclusion algorithm", ACM TOCS
   3(4), 1985, [doi:10.1145/6110.214406](https://doi.org/10.1145/6110.214406)
   - the broadcast-token algorithm and the `LN[]/Q` recovery regeneration.
5. Attiya & Welch, *Distributed Computing: Fundamentals, Simulations and
   Advanced Topics*, 2nd ed., Wiley 2004 - chapter 9 frames the
   permission/token taxonomy and the formal impossibility of doing better
   than these bounds in the standard model.
