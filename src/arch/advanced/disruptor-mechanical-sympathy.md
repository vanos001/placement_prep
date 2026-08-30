# The LMAX Disruptor: Mechanical Sympathy as a Design Discipline

To run a retail financial exchange on the JVM at 100K transactions per second under 1 ms
latency, LMAX profiled the obvious designs first: staged pipelines in the SEDA and Actor
styles, each stage connected by a queue. The queues won — at dominating the cost profile:
handoff latency came out in the same order of magnitude as disk IO, so a transaction
crossing several stages paid hundreds of microseconds just to move between threads. The
response was a teardown — keep the pre-allocated array, throw away the locks, condition
variables, per-message allocation, and the queue abstraction itself. The design habit
behind it — write code the way the machine's caches, store buffers, and prefetchers want —
the team calls "mechanical sympathy". The queue-family taxonomy it departs from is in
[Concurrent Queues](../../concurrency/concurrent-queues.md), the CAS machinery it drops
from the fast path in [Atomic Primitives](../../concurrency/atomic-primitives.md).

## 1. What a Queue Handoff Costs

Java's bounded queues are lock-based by construction. `ArrayBlockingQueue` guards head
and tail with one `ReentrantLock` and two conditions; `LinkedBlockingQueue` splits into a
"two lock queue" and allocates a `Node` per element. The white paper's calibration (500M
counter increments, 2.4 GHz Westmere) shows what arbitration costs once threads contend:
300 ms single-threaded, 10,000 ms with an uncontended lock, **224,000 ms with two threads
contending** — against 5,700 ms for single-threaded CAS and 4,700 ms for a plain volatile
write. A contended lock costs three orders of magnitude more than the write it guards,
because arbitration context-switches into the kernel and the losing core's caches go cold.

Queues concentrate that contention structurally: producers claim the head, consumers the
tail, a size counter watches the boundary — the hottest variables share one cache line —
and a steady-state queue is almost always full or empty, maximizing blocking. Two
more costs pile on. **GC pressure**: linked queues allocate a node per element, and under
load objects survive into old-gen collections the paper measures at "seconds per GB".
**Pointer chasing**: linked nodes scatter with no predictable stride, defeating the
prefetcher (see [Hardware Prefetching](hardware-prefetching.md)).

## 2. The Ring Buffer and the Sequence Model

Storage is a fixed array of entries allocated once, sized to a power of two so the index
is a mask (`seq & (SIZE - 1)`). Entries are containers reused forever: the producer
overwrites slot `seq & mask` when it claims sequence `seq`. All coordination lives in
plain 64-bit counters — one `cursor` for "published through here", one `Sequence` per
consumer for "consumed through here" (initialized to -1). Slots wrap; sequences never do.

```text
SIZE = 8 slots, mask = 7;  slot = sequence & 7
  slot index:      0     1     2     3     4     5     6     7
  holds sequence: 16    17    18    19    12    13    22    15      cursor = 22
  producer wants sequence 23 -> slot 7, which still holds sequence 15
  gate = min(gating sequences) = 9      (the slowest consumer has reached 9)
  wrap check:  23 - 8 = 15  >  9  ->  NOT free; the producer spins until
  that consumer passes 15, then claims, writes, publishes.
```

Because entries are pre-allocated and rewritten in place, the ring's memory is immortal
to the garbage collector, and contiguous slots walk as one prefetchable stride.

## 3. Claim and Gating Protocol

Each shared counter has exactly one writer, which is what removes the CAS machinery:

- **Single producer.** Claim = increment a plain long; publish = an ordered cursor
  write (the source comments "StoreLoad fence"). The paper is blunt: with one producer,
  "regardless of the complexity of the consumer graph, no locks or CAS operations are
  required" — only memory barriers. The wrap gate reads the minimum of consumer
  sequences, cached so retries do not hammer that line.
- **Multiple producers.** Producers race a CAS to claim; a committer spins until
  earlier claimers commit, then advances the cursor — one CAS per claim, not one per
  operation on head *and* tail.
- **Consumers.** Each volatile-reads the cursor, processes `[own sequence + 1 .. cursor]`,
  and updates its own `Sequence`. Gating: producers cannot overrun unread slots, and a
  consumer whose input is other consumers gets a `SequenceBarrier` over their sequences —
  the slowest gates it.

## 4. Wait Strategies

When a consumer has drained everything published, it decides how to wait — a pluggable
`WaitStrategy`; the trade is latency versus CPU burned.

| WaitStrategy | Mechanism | Cost profile | Fits when |
| --- | --- | --- | --- |
| Blocking (default) | lock + condition variable | slowest; no idle CPU | scarce cores, loose SLOs |
| Sleeping | spin, then `parkNanos(1)` (~60 us on Linux) | near-zero CPU, higher latency | async logging |
| Yielding | spin with `Thread#yield()` | burns CPU, low latency | handlers < logical cores |
| BusySpin | tight spin on the sequence | highest performance | handlers < physical cores |

## 5. Consumer Wiring: One Ring, Many Topologies

A queue-based pipeline pays the Section 1 tax at every arc; a fork multiplies queues, a
re-join multiplies contention. The Disruptor expresses the same graph as sequence barriers
on one ring — the user guide's example is LMAX's journal-replicate-business-logic diamond:

```text
        producer (reads orders)
            |  claim + publish           one ring, one copy of each event
            v
   +---------------------+               barrier = producer cursor
   |                     |
 C1 journaling     C2 replicate     <- parallel consumers: each reads
   |                     |              every event, no queue between them
   +----------+----------+
              |
       C3 business logic            <- SequenceBarrier over (C1, C2):
```

Swapping an AND barrier for competing processors gives work distribution instead of
ordering, and the DSL's `EventHandlerGroup` composes both shapes. The paper's only caveat:
state written by independent consumers must not share cache lines.

## 6. Why It Is Fast: the Mechanical Sympathy Inventory

1. **Single-writer principle.** One thread owns each mutable location — cursor, each
   consumer `Sequence`, each slot — needing only visibility, not exclusion.
2. **No CAS where one writer is possible.** The single-producer fast path is increments
   and ordered writes; CAS survives only in the multi-producer claim, where contention is
   irreducible (mechanics in [Atomic Primitives](../../concurrency/atomic-primitives.md)).
3. **Padding against false sharing.** `Sequence` pads its volatile value with 56 bytes
   each side ("to be more efficient with regards to false sharing"), as does
   `SingleProducerSequencer`'s cursor and gate cache — producer and consumer updates never
   invalidate each other's lines; see [Cache Coherence](cache-coherence-advanced.md);
   JEP 142 added `@Contended` platform-side.
4. **Arrays the prefetcher can ride.** Contiguous pre-allocated slots give every
   consumer walk a fixed stride inside the ~2048-byte stride-detection window.
5. **Allocation is a startup event.** Immortal slots: no per-message garbage, no
   promotion, no collector on the hot path.
6. **The batching effect.** A consumer finding the cursor ahead processes `[from..to]`
   per wake — one barrier interaction amortized over many events; latency stays nearly
   flat as load rises, instead of queues' "J curve".

## 7. Worked Demo: Gating and Batching, No Locks

The model reduces the protocol to its integer skeleton: one producer publishes into a
64-slot ring in bursts of 8; three consumers wake per burst with per-wake budgets; at the
wrap point only the gate consumer advances. Deterministic, no clocks or randomness.

```python
# Lock-free ring-buffer handoff, Disruptor-style, deterministic: one producer
# advances `cursor`; each consumer owns a gating `sequence` and processes
# [seq+1 .. seq+take] per wake. Coordination = wrap check vs min(gating seqs).
RING_SIZE, ENTRIES, BURST = 64, 512, 8
BUDGET = (12, 4, 2)                     # entries per wake: fast -> slow
NAME = ("C0 fast", "C1 medium", "C2 slow")
N, LAST = len(BUDGET), ENTRIES - 1      # LAST: highest sequence (0-based)
cursor = -1                             # highest published sequence
seq = [-1] * N                          # per-consumer gating sequence
wake = [0] * N                          # wake-ups == batches consumed
hist = [{} for _ in range(N)]           # batch size -> count
stalls = [0] * N                        # producer stalls attributed to gate g
max_lag = 0                             # worst gate lag behind the cursor
def drain(only=None):
    "Wake consumers with pending work; on a producer stall only the gate runs."
    for i in range(N):
        if only is not None and i != only:
            continue
        avail = cursor - seq[i]
        if avail > 0:
            take = min(BUDGET[i], avail)
            wake[i] += 1
            hist[i][take] = hist[i].get(take, 0) + 1
            seq[i] += take
for n in range(ENTRIES):                # claim/publish sequences 0 .. LAST
    while n - RING_SIZE > min(seq):     # wrap point: slot not yet consumed
        g = seq.index(min(seq)); stalls[g] += 1
        max_lag = max(max_lag, cursor - min(seq))
        drain(g)                        # producer spins; gate advances
    cursor = n                          # publish: one ordered write
    if n % BURST == BURST - 1:
        drain()
while min(seq) < LAST:                  # final drain after the last publish
    drain()
print("ring-buffer handoff: %d entries (sequences 0..%d), ring %d slots (index = seq & %d)"
      % (ENTRIES, LAST, RING_SIZE, RING_SIZE - 1))
print("consumer budget per wake: C0=%d C1=%d C2=%d; %d published/round" % (BUDGET + (BURST,)))
print()
print("consumer   wake-ups  entries  avg batch  batch-size histogram (size x count)")
for i in range(N):
    items = "  ".join("%d x %d" % (s, c) for s, c in sorted(hist[i].items()))
    print("%-9s   %5d  %6d  %8.2f  %s"
          % (NAME[i], wake[i], ENTRIES, ENTRIES / wake[i], items))
print()
print("producer gated at wrap point: %d stall rounds" % sum(stalls))
print("  gate attribution: C0=%d  C1=%d  C2=%d" % (stalls[0], stalls[1], stalls[2]))
print("  worst lag of gate behind cursor: %d entries (ring holds %d)"
      % (max_lag, RING_SIZE))
print("  final sequences: cursor=%d  C0=%d  C1=%d  C2=%d" % (cursor, seq[0], seq[1], seq[2]))
print()
print("wake-ups consumed: disruptor batching %d vs per-entry signaling %d (%.1fx)"
      % (sum(wake), N * ENTRIES, N * ENTRIES / sum(wake)))
```

Real output (Python 3.12):

```text
ring-buffer handoff: 512 entries (sequences 0..511), ring 64 slots (index = seq & 63)
consumer budget per wake: C0=12 C1=4 C2=2; 8 published/round

consumer   wake-ups  entries  avg batch  batch-size histogram (size x count)
C0 fast        64     512      8.00  8 x 64
C1 medium     128     512      4.00  4 x 128
C2 slow       256     512      2.00  2 x 256

producer gated at wrap point: 210 stall rounds
  gate attribution: C0=0  C1=49  C2=161
  worst lag of gate behind cursor: 64 entries (ring holds 64)
  final sequences: cursor=511  C0=511  C1=511  C2=511

wake-ups consumed: disruptor batching 448 vs per-entry signaling 1536 (3.4x)
```

Gating: the fast consumer never blocks the producer, the medium one does 49 times, the
slow one 161 — and the worst stall leaves the gate exactly one full ring behind the
cursor. Batching: per-entry signaling would wake every consumer 512 times for batches of
1; here the fast consumer wakes 64 times, and the system spends 448 wake-ups instead of
1,536 — more throughput, fewer coordination events.

## 8. Disruptor versus Bounded Blocking Queues

All numbers are the white paper's benchmarks (best of 3, 500M messages, Java 1.6,
`ArrayBlockingQueue` per pipeline arc vs Disruptor barriers).

| Configuration (Table 2) | ArrayBlockingQueue | Disruptor |
| --- | --- | --- |
| Unicast 1P-1C, ops/s | 5,339,256 | 25,998,336 |
| Pipeline 1P-3C, ops/s | 2,128,918 | 16,806,157 |
| Multicast 1P-3C, ops/s | 1,077,384 | 9,377,871 |

| Latency per hop, 3-stage pipeline (Table 3) | ArrayBlockingQueue | Disruptor |
| --- | --- | --- |
| Min / Mean | 145 / 32,757 ns | 29 / 52 ns |
| 99% / 99.99% under | 2,097,152 / 4,194,304 ns | 128 / 8,192 ns |

Punchline: locks and condition-variable signalling cause the queue's 32.8 microseconds
per hop; 52 ns is barely a cache round-trip, and the 99.99% row shows batching's tail
discipline — no J curve.

## 9. Where Not to Use It

Skip the Disruptor when **the handler dominates** (microseconds of real IO, crypto, or
parsing work — a 100 ns handoff was never the bottleneck, and a blocking queue is within
noise); when you want **unbounded buffering** (the ring back-pressures at `SIZE` by
design); with **heterogeneous or huge payloads** (slots are pre-allocated at the largest
event size); when you need **per-event acks, priorities, or reordering** (consumers track
positions, not item identities); or when **cores are scarce and shared** (the low-latency
wait strategies spin; `BlockingWaitStrategy` puts you back near blocking-queue behavior).

## 10. Interview Q&A

**Q: Why does a single-producer Disruptor need no CAS at all, and what replaces it?**
Every shared location has exactly one writer: the producer writes cursor and slots, each
consumer only its own `Sequence`. Exclusion is needed only for contended writes; the
remaining problem is visibility, solved with barriers — publish is an ordered cursor
write, the wait a volatile read. CAS survives only in the multi-producer claim, where
two writers are irreducible.

**Q: Replace "queue full" for me — what actually happens when the ring wraps?**
Claiming sequence `s` checks `s - RING_SIZE <= min(gating sequences)`. If the slot about
to be overwritten holds a sequence some consumer hasn't passed, the producer spins (or
parks) until the gate advances. The demo charges that stall to the slowest consumer, with
worst-case backlog exactly one ring — that inequality is the entire back-pressure protocol.

**Q: The mean per-hop latency is 32,757 ns versus 52 ns. Where does the queue's time go?**
Into lock arbitration and condition-variable signalling: a contended lock
context-switches to the kernel, parks the waiter, wakes it later, and the waking core's
caches are cold — the calibration table turns 300 ms of work into 224 seconds. The
spinning consumer instead re-reads a cached sequence on its own core and processes a
whole batch without touching a coordination primitive.

**Q: When does the batching effect hurt?**
When work is keyed to batch boundaries or per-entry timeliness: flushing on `endOfBatch`
collapses flush frequency to batch rate, a large batch's head event waits behind the
rest, and a slow consumer gates the producer for the full ring depth. The user guide's
"Dealing With Large Batches" chunking exists for exactly these handlers.

## References

1. M. Thompson, D. Farley, M. Barker, P. Gee, A. Stewart. *Disruptor: High performance alternative to bounded queues for exchanging data between concurrent threads.* White paper v1.0, LMAX, May 2011. <https://lmax-exchange.github.io/disruptor/files/Disruptor-1.0.pdf>
2. LMAX Disruptor user guide: gating, wait strategies, "Dealing With Large Batches". <https://lmax-exchange.github.io/disruptor/user-guide/index.html>
3. LMAX-Exchange/disruptor source: `Sequence` padding, `SingleProducerSequencer`, wait strategies, `BatchEventProcessor`. <https://github.com/LMAX-Exchange/disruptor>
4. M. Thompson. *LMAX - How to Do 100K TPS at Less than 1ms Latency.* InfoQ presentation. <https://www.infoq.com/presentations/LMAX/>
5. M. Thompson. *Single Writer Principle.* Mechanical Sympathy blog, 2011. <https://mechanical-sympathy.blogspot.com/2011/09/single-writer-principle.html>
6. JEP 142: Reduce Cache Contamination on Field Access (`@Contended`). <https://openjdk.org/jeps/142>
7. `java.util.concurrent.ArrayBlockingQueue`, JDK 21 API documentation. <https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ArrayBlockingQueue.html>
9. M. Welsh, D. Culler, E. Brewer. *SEDA: An Architecture for Well-Conditioned, Scalable Internet Services.* SOSP 2001, 230-243. [doi:10.1145/502034.502057](https://doi.org/10.1145/502034.502057)
