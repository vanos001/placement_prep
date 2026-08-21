# Concurrent Queues — SPSC, MPSC, MPMC, and the LMAX Disruptor

A queue is the most common shape of producer/consumer concurrency, but
the right implementation depends entirely on the fan-in/fan-out
topology. A queue with one producer and one consumer can be a
lock-free ring buffer with two indexes; a queue with many producers and
many consumers needs careful per-cell sequencing to avoid ABA. The
LMAX Disruptor throws the queue abstraction away and replaces it with a
sequenced ring buffer, getting ~3x the throughput of an
ArrayBlockingQueue because the JVM memory model and the cache hierarchy
were what was limiting them.

This chapter assumes the [Lock-Free Programming](./lock-free.md) and
[Atomic Primitives](./atomic-primitives.md) background. The relevant
tricks there — `acquire`/`release` pairing, false sharing avoidance,
CAS-loop retry — are all on display here.

## SPSC ring buffer

Single-producer single-consumer, bounded, fixed element type. This is
the easiest concurrent data structure in existence, and the fastest:
the fast path has no atomic RMW at all, just relaxed stores and
acquire/release loads.

```
       head (consumer)        tail (producer)
          |                       |
          v                       v
+----+----+----+----+----+----+----+----+
| D0 | D1 |    |    |    |    |    |    |   size = 8 (power of 2)
+----+----+----+----+----+----+----+----+
  ^                                  ^
  +----- producer wraps here -------+
```

The producer owns `tail`, the consumer owns `head`. Neither needs to
CAS the other side — each only reads the other side's index, and writes
only its own. The synchronization is the release-store on the producer's
write of `tail`, paired with the acquire-load of `tail` on the consumer
side.

```cpp
template <typename T, size_t Cap>           // Cap must be power of 2
struct SpscRing {
    static_assert((Cap & (Cap - 1)) == 0, "Cap must be power of 2");
    T buf[Cap];
    std::atomic<size_t> head{0};            // consumer-owned write
    std::atomic<size_t> tail{0};            // producer-owned write

    bool push(const T& v) {
        size_t t = tail.load(std::memory_order_relaxed);
        size_t h = head.load(std::memory_order_acquire);
        if (t - h == Cap) return false;      // full
        buf[t & (Cap - 1)] = v;             // size-1 mask, not modulo
        tail.store(t + 1, std::memory_order_release);
        return true;
    }

    bool pop(T& out) {
        size_t h = head.load(std::memory_order_relaxed);
        size_t t = tail.load(std::memory_order_acquire);
        if (h == t) return false;            // empty
        out = buf[h & (Cap - 1)];
        head.store(h + 1, std::memory_order_release);
        return true;
    }
};
```

Three subtleties:

1. **Power-of-two capacity.** The index-masking `t & (Cap - 1)` is a
   single AND instruction; `t % Cap` is an integer division. The
   compiler can sometimes turn `%` into a multiply-shift, but only when
   `Cap` is a compile-time constant. Explicit power-of-two is the only
   thing that always works.
2. **Monotonic indices, not modulo'd.** `head` and `tail` wrap
   naturally at `size_t` overflow, which is billions of operations
   away on 64-bit. Wrapping into the array is done with the mask. This
   removes a whole class of "is the queue full or empty?" bugs.
3. **No shared cache line.** `head` and `tail` must be on separate
   cache lines or the producer's store invalidates the consumer's line
   (false sharing). Crossbeam's `ArrayQueue` aligns them with
   `#[repr(align(64))]`. The C++ above omits the padding for brevity
   but it is required for production code.

The Disruptor paper quotes 50-100M ops/s for an SPSC ring of small
types on a modern x86 box.

## MPSC bounded queue

Multiple producers, single consumer. The classic implementation is
Dmitry Vyukov's bounded MPSC queue: an intrusive singly-linked list
with a stub node, an atomic `tail` that producers contend on, and a
non-atomic `head` that only the consumer touches.

```cpp
struct Node {
    std::atomic<Node*> next;
    T data;
};

std::atomic<Node*> tail;      // initially points to the stub
Node* head;                   // consumer-private; initially the stub

void push(Node* n) {
    n->next.store(nullptr, std::memory_order_relaxed);
    // exchange is a single atomic RMW; the producer that won the
    // exchange is responsible for linking the previous tail to n
    Node* prev = tail.exchange(n, std::memory_order_acq_rel);
    prev->next.store(n, std::memory_order_release);
}

Node* pop() {
    Node* h = head;
    Node* next = h->next.load(std::memory_order_acquire);
    if (!next) return nullptr;                 // empty
    head = next;
    return next;                               // h was the stub
}
```

Two cute bits:

- `tail.exchange(n, ...)` is a single atomic operation; producers
  serialize on this CAS-equivalent, but only for the duration of the
  RMW. After it, they go off and do their own store to `prev->next`.
- The producer never touches `head`, so producers do not generate
  coherence traffic with the consumer's line. The only cross-thread
  cache traffic is on `tail` and on the per-node `next` field.

This is what Rust's `crossbeam_queue::SegQueue` uses under the hood,
and roughly what the Linux kernel's `llist` does for MPSC lists.

## MPMC bounded queue — Vyukov

For many producers *and* many consumers, the right design is a fixed
array of *cells*, where each cell carries a per-cell sequence counter.
Vyukov's bounded MPMC queue is the canonical implementation; it is
reused by Rust's `crossbeam_queue::ArrayQueue` and Intel TBB's
`concurrent_bounded_queue`.

```
       head                           tail
        |                              |
        v                              v
+--------+   +--------+   +--------+   +--------+
| seq=0  |   | seq=0  |   | seq=1  |   | seq=0  |   <- all cells have
+--------+   +--------+   +--------+   +--------+      per-cell seq
   cell[0]    cell[1]      cell[2]      cell[3]
```

The trick is the per-cell sequence counter, which makes the ABA problem
disappear: if producer A reads `cell.seq == 5`, gets preempted, then
another producer fills the cell, the consumer empties it, and a third
producer re-fills it, the cell's sequence is now `7`. Producer A's CAS
sees `diff != 0` and reloads the tail.

Enqueue (paraphrased from Vyukov's 1024cores writeup):

```cpp
bool enqueue(Cell& c) {
    size_t pos = tail.load(std::memory_order_relaxed);
    for (;;) {
        Cell& cell = cells[pos & mask];          // mask = N - 1
        size_t seq = cell.seq.load(std::memory_order_acquire);
        intptr_t diff = (intptr_t)seq - (intptr_t)pos;

        if (diff == 0) {                         // slot is ready
            if (tail.compare_exchange_weak(pos, pos + 1,
                    std::memory_order_relaxed,
                    std::memory_order_relaxed)) {
                cell.data = c.data;
                cell.seq.store(pos + 1, std::memory_order_release);
                return true;
            }
            // lost the race; loop with updated `pos`
        } else if (diff < 0) {                   // queue full
            return false;
        } else {                                 // stale, reload
            pos = tail.load(std::memory_order_relaxed);
        }
    }
}
```

The symmetric dequeue reads `head` instead of `tail` and expects
`seq == pos + 1` (consumer side; producer writes `pos+1`, consumer
expects that exact value, then writes `pos + N` to "empty" the slot).

Two engineering details:

- `head` and `tail` must be on separate cache lines, both aligned to 64.
- The per-cell `seq` shares the cache line with `data`, so a producer
  storing `seq = pos + 1` brings the whole line to the consumer (which
  is what we want — the consumer needs the data anyway).

## LMAX Disruptor

The Disruptor is what happens when a financial exchange team (LMAX,
running 100k+ TPS on the JVM) refuses to accept that ArrayBlockingQueue
is the fastest they can do. The Disruptor paper quotes ~3x throughput
vs ArrayBlockingQueue and ~8x for a chained 3-stage pipeline. The
secret is not a better algorithm — it's a cache-aware re-organization
of the producer/consumer pattern.

Components:

- **RingBuffer** — storage of `2^N` pre-allocated entries, slots reused.
  Slots are large enough (≥64 bytes typically) to avoid false sharing.
- **Sequencer** — `SingleProducerSequencer` or `MultiProducerSequencer`
  hands out monotonically increasing sequence numbers. The sequencer is
  the only thing producers contend on.
- **SequenceBarrier** — each consumer reads up to a published sequence
  number; the barrier exposes the *minimum* of the sequences it depends
  on, so a consumer is gated by the slowest upstream.
- **EventProcessor** — the consumer thread, looping on `waitFor(seq)`.
- **WorkerPool** — for the MPMC work-distribution case, a pool of
  processors consuming the same ring.

```
Producer -> Sequencer -> claim next seq -> write slot -> publish seq
                                  |
                                  v
                      SequenceBarrier (depends on producer)
                                  |
              +-------------------+-------------------+
              v                   v                   v
           C1 (decode)        C2 (dup)          C3 (journal)
              |                   |                   |
              v                   v                   v
       last_seq per consumer  (a separate Sequence each)
                                  |
                                  v
                Producer's gating barrier: cannot claim past min(C1,C2,C3)
```

The producer is gated by the slowest consumer's last-claimed sequence
(plus the ring size), so it never overwrites a slot still being read.
This is what replaces "blocking queue is full" — instead of blocking,
the producer retries the claim or signals back-pressure.

Why it is faster than ArrayBlockingQueue:

1. No locks on the fast path (single CAS-equivalent claim).
2. No allocation per event (slots are pre-allocated and reused).
3. Cache-line aligned slots — no false sharing between producers and
   consumers.
4. Memory-model-friendly publication: `lazySet` for the published
   sequence (a store-release in C++/C11 terms), and a volatile read in
   the consumer's loop.
5. The barrier lets the consumer batch: it reads *up to* the published
   sequence, not one at a time, which amortizes the cache-miss cost
   across many events.

The Disruptor is what a careful MPMC queue looks like when you remove
every other abstraction layer. The full design is in the
[LMAX technical paper](https://lmax-exploratory.github.io/disruptor/).

## Comparison to channels

Channels are queues + closure + blocking + cancellation + select, all
bundled together. They are much more than a buffer.

- **Go channels**: MPMC by default. The buffered channel is a lock
  (`sync.Mutex`) around a ring buffer; the unbuffered channel uses a
  synchronous handoff (a `sudog` queue per side). The implementation in
  `src/runtime/chan.go` is careful but not lock-free. Throughput is in
  the 10-50M ops/sec range; SPSC rings and Disruptor-class designs are
  10-100x faster.
- **Rust crossbeam channels**: scoped channels built on crossbeam's
  MPMC queue. Now considered legacy in favor of `crossbeam-queue`
  directly, but still the standard for "send a value across threads."
- **Java SynchronousQueue**: zero-capacity; `put` blocks until a `take`
  is paired. Internally it is a "dual data structure" — every operation
  has a complementary operation, and the queue holds whichever side
  arrived first. Implemented via `TransferStack` (LIFO) or
  `TransferQueue` (FIFO), each a CAS-based stack or queue of waiting
  operations. Used by `Executors.newCachedThreadPool` for handoff
  between submitter and worker.
- **Clojure `core.async`**: similar to Go channels but on top of a
  thread pool; Go's runtime is itself a thread pool, so the analogy is
  exact.

The right framing: a channel is the right tool when you want
*composition* (select, fan-out, cancellation, back-pressure) and the
throughput you need is below what a lock-free queue buys you. For a
latency-sensitive producer feeding a hot consumer — an HFT pipeline, a
media encoder, a kernel trace buffer — drop down to SPSC ring or
Disruptor.

## When to use what

| Topology | Latency target | Pick |
|---|---|---|
| 1 producer, 1 consumer, fixed type | sub-microsecond | SPSC ring buffer |
| N producers, 1 consumer (logger) | tens of microseconds | Vyukov MPSC |
| N producers, M consumers, bounded | sub-millisecond | crossbeam ArrayQueue / Disruptor |
| N producers, M consumers, unbounded | any | linked MPMC (Michael-Scott) |
| Handoff, cancellation, select | any | channel |

## Cross-references

- [Producer-Consumer](./producer-consumer.md) — the pattern itself
- [Work-Stealing Scheduler](./work-stealing.md) — Chase-Lev deque = SPSC ends
- [Thread Pools](./thread-pools.md) — channels as the handoff primitive
- [Lock-Free Structures](./lock-free-structures.md) — Michael-Scott and Treiber
- [Go Channels](./go-channels.md) — Go's runtime channel implementation
- [Atomic Primitives](./atomic-primitives.md) — the orderings used here

## References

- LMAX Disruptor: [Technical Paper](https://lmax-exploratory.github.io/disruptor/) and [Disruptor github](https://github.com/LMAX-Exchange/disruptor) — the original writeup, with throughput numbers
- Dmitry Vyukov, [bounded MPMC queue](https://www.1024cores.net/home/lock-free-algorithms/queues/bounded-mpmc-queue) — the canonical 1024cores post
- Crossbeam queue docs: [crossbeam-queue](https://docs.rs/crossbeam-queue/latest/crossbeam_queue/) — `ArrayQueue` and `SegQueue` Rust implementations
- OpenJDK `SynchronousQueue` source: [`java.util.concurrent.SynchronousQueue`](https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/concurrent/SynchronousQueue.java) — `TransferStack`/`TransferQueue` internals
- Brian Goetz et al., *Java Concurrency in Practice* ch 5 "Building Blocks" — `ArrayBlockingQueue` vs `LinkedBlockingQueue` trade-offs
- Go runtime channel implementation: [`src/runtime/chan.go`](https://github.com/golang/go/blob/master/src/runtime/chan.go) — the hchan struct, sudog wait lists, fast paths
