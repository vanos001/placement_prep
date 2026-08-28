# PREEMPT_RT: Making the Kernel Fully Preemptible

A mainline kernel with `PREEMPT_FULL` still has a wall of unpreemptible
contexts: spinlock-held sections, interrupt handlers, softirqs, the scheduler
itself. For desktop and server work that wall is invisible; for an audio
buffer deadline of 2.7 ms or an industrial motion-control loop, the wall is
the bug. The PREEMPT_RT patch set - slowly absorbed into mainline over fifteen
years, with the core merged for x86-64, arm64 and riscv in kernel 6.12 -
systematically dismantles that wall. This page covers the preemption spectrum,
the three structural conversions RT performs, and how real-world latency is
actually measured.

Lock mechanics are a deep topic in their own right: the rt_mutex slow path,
PI chain walks and PI futexes are covered in
[rt_mutex internals](./rtmutex-pi-futex.md); the scheduling classes and
throttling in [RT scheduling groups](https://docs.kernel.org/scheduler/sched-rt-group.html)
(kernel docs); futex user surface in [futexes](./futex.md).

## The preemption spectrum

The kernel exposes the trade as a single build choice:

| model                | what can preempt the kernel                    | typical worst-case scheduling latency |
|----------------------|------------------------------------------------|----------------------------------------|
| `PREEMPT_NONE`       | only user preemption at syscall boundaries     | tens of milliseconds (batch-oriented)  |
| `PREEMPT_VOLUNTARY`  | explicit might_sleep() reschedule points       | still unbounded under spinlock holds   |
| `PREEMPT_FULL`       | above + preemptible while no spinlock held     | low, but hardirq/softirq walls remain  |
| `PREEMPT_LAZY`       | FULL + tasks get a tick to drain before resched| a middle point (6.12+ option)          |
| `PREEMPT_RT`         | nearly everything: even in-kernel spinlock sections sleep | bounded by irq-handling path |

The headline claim of RT is not "faster" - average throughput usually drops
slightly - but *bounded*: the tail of the scheduling-latency distribution
stops growing with load, because the mechanisms that create unbounded
preemption-off windows are converted or eliminated.

## Conversion 1: spinlocks that sleep

On RT, in-kernel `spinlock_t` becomes an rt_mutex-based sleeping lock.
Sections "holding a spinlock" become ordinary preemptible code, which is
what allows high-priority work to preempt low-priority lock holders. The
conversion respects these distinctions:

- `raw_spinlock_t` stays a true spinning lock - for code that must not
  sleep (the scheduler core, low-level irq entry, per-CPU critical state).
  An audit converted thousands of call sites to `raw_` where semantics
  require it.
- `spin_lock_irqsave()` on RT does NOT disable hardware irqs (that would be
  an unbounded latency source); it disables *preemption* and relies on the
  handler-threading below. The rare sites that truly need irq-off get
  explicit `local_irq_save()` and are audited as such.
- Sleeping under a spinlock becomes legal in most driver code - a massive
  semantic change that broke the assumption "atomic context" in printk,
  allocator paths and timekeeping, each requiring rework (printk grew
  nbcon-based non-blocking consoles for exactly this reason).

Priority inheritance is not optional in this world: a sleeping lock held by
a lower-priority task would otherwise unbound the very latency RT exists to
bound, so every rt_mutex carries the PI machinery - and PI chains (task A
blocks on a lock held by B blocked on a lock held by C) require the
chain-walk algorithm covered in [rt_mutex internals](./rtmutex-pi-futex.md).

## Conversion 2: threaded interrupt handlers

The top/bottom-half split ([interrupt handling](../interrupts/top-bottom-halves.md))
gets a structural reinterpretation: on RT, almost every device IRQ handler
runs as a schedulable kernel thread (`irq/<n>-<dev>`), which the RT
scheduler can prioritize, migrate and preempt. The primary handler keeps
only the minimal "ack the device, wake the thread" work. Consequences:

- Softirqs become preemptible too (and `TASKLET` semantics get executed in
  the same threaded context); network RX can no longer hog a CPU in
  softirq land for unbounded batches.
- Spinlocks taken from both a threaded handler and process context are
  ordinary sleeping locks - the lock is the synchronization, not CPU
  residency.
- Devices that genuinely need hard-irq latency get `IRQF_NO_THREAD`.

## Conversion 3: local locks and migrate_disable

Code that used `get_cpu_var()` (preempt-off + CPU-pin in one primitive)
needed a replacement that preserves correctness but not unbounded
non-preemption. RT's answer is `local_lock_t` plus `migrate_disable()`:
the task stays on its CPU (cache correctness, per-CPU data integrity) but
may be preempted *in place* by a higher-priority task that runs on the same
CPU. Preemption is restored without giving up per-CPU guarantees - the key
insight that unlocked most of the per-CPU code in the kernel for RT.

## Measuring: what cyclictest and oslat actually do

`cyclictest` measures how late a timer wakeup happens: a thread sleeps on a
timer, records `now - deadline`, optionally locks memory and pins CPUs to
remove noise. `oslat` (added for RT evaluation) measures the CPU's own
activity instead: a busy loop timestamps continuously and reports gaps - the
distribution of *everything that interrupted the loop*, which catches SMIs
and hypervisor steal that cyclictest cannot see. Reading the output is an
interview skill in itself:

```text
cyclictest -p99 -m -h 100 -q (histogram mode), 1h run, 8 cpus:
  # Max Latencies: 00042 00051 00039 00055 ...     (per-cpu max, microseconds)
  # Histogram (us): buckets 0-99
  interpretation targets: audio-grade setups aim p99 < 200 us, max < 1 ms;
  industrial motion control: max < 100 us on isolated cpus.
```

The demo below models the latency budget in both worlds: a hardirq-serviced
wakeup versus a threaded-irq wakeup under RT, with a realistic load term
where a non-preemptible section blocks the wakeup. The point is the
*mechanism* of the tail: mainline latency spikes when the wakeup lands
inside an unbounded spinlock-held section; RT's worst case is the thread
scheduler's own dispatch path.

```python
#!/usr/bin/env python3
"""Deterministic latency-budget model: wakeup delivery on mainline
(PREEMPT_FULL + hardirq) vs PREEMPT_RT (threaded irq + sleeping locks).

Model per wakeup:
  mainline: wakeup runs in hardirq context. If the CPU is inside a
  non-preemptible section (spinlock hold, softirq batch), delivery waits
  for the section to end. Model: uniform section cost 0..B_us, hit with
  probability P_INSECTION per wakeup; plus a fixed irq entry cost.
  RT: handler is a thread at SCHED_FIFO prio 98. Delivery cost = scheduler
  dispatch (fixed) + possible preemption by a same-or-higher-prio thread
  (modeled as a bounded preemption slice). No unbounded section: RT locks
  sleep, so the blocking term is bounded by the RT critical section budget.

Constants are engineering-plausible magnitudes from published cyclictest
comparisons, not measurements of this machine."""
import random

WAKEUPS = 200_000
SEED = 11

IRQ_ENTRY_US = 1.5          # hardirq entry/exit (mainline)
DISPATCH_US = 6.0           # thread wakeup->run dispatch (RT)
SECTION_MEAN_US = 220.0     # mean unbounded-ish section cost (mainline)
SECTION_CAP_US = 1200.0     # tail cap for the model (BPF/prog paths can exceed)
P_INSECTION = 0.30          # probability wakeup lands inside a section
RT_SLICE_US = 50.0          # bounded RT critical-section budget
P_RTPREEMPT = 0.05          # wakeup preempted by higher-prio RT thread


def simulate(mode, rng):
    lats = []
    for _ in range(WAKEUPS):
        base = IRQ_ENTRY_US if mode == "mainline" else DISPATCH_US
        if mode == "mainline":
            if rng.random() < P_INSECTION:
                # exponential-ish section cost, capped for the model
                cost = min(rng.expovariate(1 / SECTION_MEAN_US), SECTION_CAP_US)
            else:
                cost = 0.0
        else:
            cost = RT_SLICE_US if rng.random() < P_RTPREEMPT else 0.0
        lats.append(base + cost)
    lats.sort()
    n = len(lats)
    return (lats[int(0.5 * n)], lats[int(0.99 * n)], lats[int(0.999 * n)], lats[-1])


rng = random.Random(SEED)
ml = simulate("mainline", rng)
rt = simulate("rt", rng)
print(f"model: {WAKEUPS:,} wakeups, seed={SEED}, costs in microseconds")
print(f"{'mode':<9} | {'p50':>7} | {'p99':>7} | {'p99.9':>7} | {'max':>8}")
print("-" * 50)
print(f"{'mainline':<9} | {ml[0]:>7.1f} | {ml[1]:>7.1f} | {ml[2]:>7.1f} | {ml[3]:>8.1f}")
print(f"{'rt':<9} | {rt[0]:>7.1f} | {rt[1]:>7.1f} | {rt[2]:>7.1f} | {rt[3]:>8.1f}")
print()
print("reading the shape: mainline's p99.9/max is governed by the section-")
print("cost tail (unbounded in reality - the cap here flatters mainline);")
print("RT's tail is the dispatch path plus a bounded preemption slice,")
print("which is what makes the max roughly predictable in advance.")
```

```text
model: 200,000 wakeups, seed=11, costs in microseconds
mode      |     p50 |     p99 |   p99.9 |      max
--------------------------------------------------
mainline  |     1.5 |   741.4 |  1201.5 |   1201.5
rt        |     6.0 |    56.0 |    56.0 |     56.0

reading the shape: mainline's p99.9/max is governed by the section-
cost tail (unbounded in reality - the cap here flatters mainline);
RT's tail is the dispatch path plus a bounded preemption slice,
which is what makes the max roughly predictable in advance.
```

Note the deliberate trade in the numbers: RT's p50 (6 us) is *worse* than
mainline's (1.5 us) - thread dispatch costs more than hardirq entry - while
the tail collapses. That inversion of average-vs-tail is the entire product
PREEMPT_RT sells.

## Deployment realities

- **Which workloads actually need it**: audio production (2.7 ms buffer at
  48 kHz/128 frames), CNC and motion control, test-and-measurement, some
  telecom framing. If the requirement is "no dropped frames under load",
  plain PREEMPT_FULL with CPU isolation often suffices; RT is for hard
  deadlines.
- **Tunings that matter more than the patch**: CPU isolation (`isolcpus`,
  `nohz_full`, irqaffinity), SCHED_FIFO priorities for the handler threads,
  `rcu_nocbs` for offloaded RCU callbacks, disabling C-states that carry
  deep-exit latency. RT without isolation still loses the tail to housekeeping.
- **The upstreaming story**: with 6.12 the core is mainline; remaining
  patch-carried pieces are driver-level and niche-arch items. Distributions
  ship `kernel-rt` variants that track this; the OSADL project publishes
  long-term latency QA data for embedded targets.

## Interview probes

- Why does PI become *mandatory* once spinlocks sleep, and what breaks if a
  driver takes a raw_spinlock inside a PI chain-walk?
- A device driver wants sub-microsecond interrupt response. Explain why
  threading its handler is wrong and what `IRQF_NO_THREAD` changes.
- What exactly does `migrate_disable()` preserve that `preempt_disable()`
  does not, and why is that the right primitive for per-CPU data?
- cyclictest shows a p99 of 800 us on an RT system: name four suspects and
  the tool or knob for each.

## References

1. [RT scheduling groups - kernel documentation](https://docs.kernel.org/scheduler/sched-rt-group.html)
   - SCHED_FIFO/SCHED_RR semantics and throttling, the priority world RT
   threads live in.
2. [LWN: Real-time interrupt threading](https://lwn.net/Articles/146861/)
   - the threaded-IRQ design as it landed.
3. [LWN: PREEMPT_RT after ten years](https://lwn.net/Articles/738541/) -
   retrospective on the conversion effort and the remaining hard parts.
4. [OSADL real-time Linux project](https://www.osadl.org/Real-time-Linux.realtime.0.html)
   - long-running production latency QA for embedded RT systems.
