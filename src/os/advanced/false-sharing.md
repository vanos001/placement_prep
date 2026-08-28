# False Sharing and Cache-Line Bouncing

> Two threads on two cores, each writing to its own variable — and the
> machine slows down as if they were fighting over one variable. They
> are: the variables share a cache line, so the coherence protocol keeps
> transferring the line's ownership between cores even though no data is
> actually exchanged. This page explains the mechanics in terms of MESI
> states, shows the standard defenses (padding, alignment, per-CPU data),
> and how `perf c2c` finds the culprits.

## The MESI Mechanics of a Bounce

The MESI protocol gives every cache line one of four states per core:
**M**odified (owned, dirty), **E**xclusive (owned, clean), **S**hared
(read-only copies), **I**nvalid. The two rules that create false sharing:

- A core may **write** only from M/E state. To gain M, every other
  copy must be invalidated (an `Invalidate` bus message + acks).
- A core may **read** in S state; if another core holds M, that core
  must write back and demote to S.

Now place `int a` and `int b` on the same 64-byte line, core 0 writing
`a` and core 1 writing `b` in a loop:

```text
 round   core0 (writes a)        core1 (writes b)        line state
 -----   ---------------------   ---------------------   ----------------
 0       write a  -> gains M     (idle)                  L is M@core0
 1       (idle)                  write b -> InvReq(0)    M@core0 -> I,
                                                         M@core1
 2       write a  -> InvReq(1)   (idle)                  M@core1 -> I,
                                                         M@core0
 3       (idle)                  write b -> InvReq(0)    ...

 each round: 1 invalidation + ownership transfer (RFO) per write,
             despite a and b never being read by the "other" core
```

Every write is a *read-for-ownership* (RFO) across the coherence fabric.
At 3 GHz a core can issue one write per cycle; the fabric can service
far fewer cross-core RFOs per second than that, so the loop runs at the
fabric's rate, not the core's. Real measurements routinely show 2-10x
slowdowns for hot single-line ping-pong; the exact factor depends on
interconnect generation and the number of bouncers.

True sharing at least has an excuse: the data genuinely moves. False
sharing pays the same bill for data nobody shares — which is why it is
considered a bug, not an overhead.

## Where It Hides

```text
 64-byte cache line
+--------------------------------------------------------------+
| int a | int b | int c | int d | ...                          |
+--------------------------------------------------------------+
   ^       ^
   |       +-- thread 2's counter (core 1)
   +---------- thread 1's counter (core 0)

struct { long x; long y; }  -- x and y usually share a line
long counters[N_THREADS];   -- adjacent counters share lines
```

The classic offenders:

1. **Counter arrays indexed by thread id** (`counters[tid]++`) — the
   canonical case. Fix: pad each element to a line, or index by
   `tid * 64 / sizeof(long)`, or allocate per-thread.
2. **Structs with independently-locked fields** — two fields on one
   line, each with its own spinlock, means the *locks* false-share and
   hand off even when the critical sections never touch the same data.
3. **Work-queue tails/heads** — producer writes tail, consumer writes
   head; if both fit one line, every handoff bounces it.
4. **Stat counters in a global struct** — a metrics struct updated by
   many threads (bytes_sent, bytes_recv, errors...) is a bounce pad
   under load.

## The Defenses

### Padding and Alignment

```c
struct padded_counter {
    long v;                 // the hot value
    long pad[7];            // 8 longs = 64 bytes: private line
} __attribute__((aligned(64)));

struct padded_counter counters2[MAX_THREADS];
```

Cost: 7/8 of the memory is waste, and struct layouts leak into ABI.
That is why this is usually done only for known-hot arrays, not general
structs.

### Language-Level Primitives

- C/C++: `alignas(64)` / `__attribute__((aligned(64)))`; C++17 provides
  `std::hardware_destructive_interference_size` — the minimum spacing so
  two objects do not share a line — and
  `hardware_constructive_interference_size` for objects you *want* on
  one line (a lock plus its guarded word).
- Java: `@jdk.internal.vm.annotation.@Contended` pads annotated fields;
  enabled only with `-XX:-RestrictContended` for user code. The JDK uses
  it internally on hot classes (e.g., the FJ work-queue top/bottom
  indices in `java.util.concurrent.ForkJoinPool`).
- Linux kernel: `____cacheline_aligned`, `____cacheline_internodealigned_in_smp`,
  and per-CPU variables (`DEFINE_PER_CPU`), which isolate hot per-CPU
  state by construction: each CPU's copy lives in its own section of the
  `.data..percpu` area, so two CPUs' copies of the same variable are
  kilometers apart in address space.

### Per-CPU Aggregation

The general algorithmic fix: turn shared writes into private writes plus
a rare aggregation step. Counters become per-CPU and a reader sums them
(or reads a periodically-flushed approximate value). This trades read
freshness for write locality — usually a massive net win because writes
outnumber aggregated reads.

## Finding It: perf c2c

`perf c2c` (cache-to-cache) attributes HITM (Hit-Modified) events —
loads that found the line in another core's Modified state — to data
addresses and code paths:

```text
perf c2c record -a -e cpu/event=0xd4,umask=0x04/ sleep 5   # HITM on x86
perf c2c report --stdio

  # shows per-line HITM counts, the offenders' pid:ip, and whether the
  # line is "false sharing" (offsets spread across users of one line)
```

The report groups by physical cache line and shows each accessor's
offset within the line. A line with HITM events where the accessor
offsets are far apart and disjoint is the false-sharing signature; a
line where everyone touches the same offset is true sharing (fix the
algorithm, not the layout).

## Worked Demo: Bounce Traffic vs Padding

The demo is a deterministic cost model (not a timing benchmark): writes
to distinct slots cost 1 coherence event if the slots share a line, 0 if
isolated. It computes the coherence-event count for a counter array at
three layout strategies and a slot-offset map for the padded case.

```python
# Deterministic cost model: coherent-write events for counter layouts.
# Assumption: a write to a line owned by another core costs 1 event
# (RFO); a write to a line you own costs 0. Ownership follows the last
# writer of that line. Each thread writes ONLY its own slot, 1000 times.

LINE = 64                      # bytes

def events_for_layout(stride_bytes, n_threads=8, writes=1000):
    # thread k writes counters[k]; slot k lives at k * stride_bytes
    # line index of each slot:
    lines = [(k * stride_bytes) // LINE for k in range(n_threads)]
    # round-robin ownership sim: on each of the `writes` rounds, every
    # thread writes once; a thread's write costs 1 if another thread
    # owns that line currently (else 0), then it takes ownership.
    owner = {ln: None for ln in lines}
    events = 0
    for w in range(writes):
        for k in range(n_threads):
            ln = lines[k]
            if owner[ln] != k:
                events += 1            # RFO / invalidation
                owner[ln] = k
    return events

print("layout               coherence events per 8k writes")
for name, stride in (("adjacent (8B)", 8), ("64B-padded", 64), ("128B-padded", 128)):
    e = events_for_layout(stride)
    print(f"  {name:<18} {e:6d}")

# slot offsets in the padded layout: which line does each slot hit?
lines = [(k * 64) // 64 for k in range(8)]
print("\n64B-padded line indices per thread:", lines)
lines8 = [(k * 8) // 64 for k in range(8)]
print("adjacent  line indices per thread:", lines8)
```

Real output:

```text
layout               coherence events per 8k writes
  adjacent (8B)        8000
  64B-padded              8
  128B-padded             8

64B-padded line indices per thread: [0, 1, 2, 3, 4, 5, 6, 7]
adjacent  line indices per thread: [0, 0, 0, 0, 0, 0, 0, 0]
```

Read the rows together: all three layouts issue the same 8,000 writes
(8 threads x 1,000 rounds), but the adjacent layout pays **one
coherence event per write** — once the line is bouncing, every writer
must RFO it back, forever (100% bounce rate). The padded layouts pay
exactly 8 events *once* — the first write per thread pulls its private
line — and never again, because ownership never changes hands. On real
hardware this is the difference between a counter that scales and one
that gets slower as you add cores.

## Interview Questions

1. Why does false sharing not show up in single-threaded profiles, and
   why is `perf record` on one thread useless for it?
   (The stall is attributed to the *victim's* core; you need cross-core
   HITM sampling — that is exactly what c2c does.)
2. A struct has two mutex-protected fields. Locks false-share even
   though the data does not. Why does the bounce matter more for the
   lock word than for a data word?
   (The lock word is written on every acquire/release by design — it is
   the highest-frequency writer in the program. Any line it lives on
   becomes the hottest line in the process.)
3. Why is `hardware_destructive_interference_size` larger than 64 on
   some ABIs? (Adjacent prefetcher pairs and spatial prefetching mean a
   *neighboring* line can also be pulled in; 128B spacing defends
   against the prefetcher, not just the line.)
4. How does `DEFINE_PER_CPU` avoid false sharing by construction?
5. When is padding the wrong fix? (When memory footprint or TLB/socket
   pressure dominates, or when the line is mostly read — sharing reads
   is free in MESI; only writes bounce.)

## References

- Mellor-Crummey, J., Scott, M. *Algorithms for Scalable Synchronization
  on Shared-Memory Multiprocessors*. ACM TOCS 9(1), 1991 — the paper
  that quantified wait-loop traffic on shared lines.
  https://doi.org/10.1145/103727.103729
- Hennessy & Patterson, *Computer Architecture: A Quantitative Approach*,
  6th ed., ch. 5 (Snooping-cache coherence and its cost model).
- Linux kernel per-CPU layout: `include/linux/percpu.h` and the
  percpu allocator internals.
  https://github.com/torvalds/linux/blob/master/include/linux/percpu.h
  (probed 200)
- `perf-c2c(1)` manual: https://man7.org/linux/man-pages/man1/perf-c2c.1.html
  (probed 200)
- C++ `hardware_destructive_interference_size` is specified in
  [transitive.include] of the C++ standard; reference summary:
  https://en.cppreference.com/w/cpp/thread/hardware_destructive_interference_size
  (official reference site bot-walls automated probes: 403 for curl)
- OpenJDK JEP 142 *Reduce Cache Contention on Specified Fields*
  (`@Contended`): https://openjdk.org/jeps/142 (probed 200)

## Cross-References

- [MCS locks and the qspinlock](./mcs-qspinlocks.md) — the lock design
  whose whole point is waiting on your own line.
- [NUMA-aware scheduling](../../linux/kernel/processes/numa-scheduling.md)
  — locality's other half: which cores your threads land on.
- [Memory disambiguation and weak memory](../../arch/advanced/memory-disambiguation.md)
  — the correctness side of shared memory.
