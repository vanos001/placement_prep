# Heterogeneous CPU Scheduling: One Runqueue, Unequal Cores

A symmetric multicore scheduler answers one question: *which* CPU. A
heterogeneous scheduler must first answer *what kind* of CPU this task
deserves, and only then *which one* — picking the wrong core type costs either
latency (a frame render on an efficiency core) or battery (a background sync
on a performance core). This page covers the mechanisms behind that decision:
capacity numbers, utilization signals, hardware classification hints, the
Energy-Aware Scheduling (EAS) placement algorithm, and the failure modes that
break schedulers designed for equal cores. Silicon-side details of specific
parts live in [Alder Lake](../modern/alder-lake.md) and [Arm cores](../modern/arm.md);
generic CFS/EEVDF mechanics live in
[scheduler internals](../../os/advanced/scheduler-internals.md).

## Three silicon recipes for asymmetry

| Design | Clustering | Core mix | Interconnect role |
|--------|-----------|----------|-------------------|
| Classic big.LITTLE (CCI) | separate big and little clusters | identical ISA, different microarch + DVFS range | CCI links fully separate clusters |
| DynamIQ (DSU) | 1-8 cores share a DynamIQ Shared Unit with its L3 | mixed core types *inside one cluster* allowed | DSU replaces CCI hop; L3 on the cluster itself |
| Intel hybrid (P/E) | P-cores SMT-enabled, E-cores in 4-wide clusters | Golden Cove-class P, Gracemont/Crestmont-class E, no SMT on E | ring/fabric; E-cluster appears as one sched domain node |

```text
   DynamIQ cluster (DSU)                 Intel hybrid package
  +---------------------------+        +---------------------------+
  | core0  core1  core2  core3|        |  P0 P1   (SMT x2, big)    |
  |  L2     L2     L2     L2  |        |   \ /                     |
  | +-----------+-----------+ |        |  ring  ---- P2 P3         |
  | |   shared L3 (DSU)      | |        |    \                      |
  | +-----------+-----------+ |        |  E-cluster [E0..E3]       |
  | core4  core5 (little mix) |        |  (1 sched_group, no SMT)  |
  +---------------------------+        +---------------------------+
```

The DSU change matters to the scheduler more than it looks: with classic
big.LITTLE, capacity differences aligned with *cluster boundaries*, so a sched
domain boundary was also an energy boundary. DynamIQ lets one domain contain
cores of different capacity, forcing capacity awareness to work at per-CPU
granularity rather than per-domain granularity.

## The scheduler's capacity currency

The kernel normalizes every CPU to a single scale: `SCHED_CAPACITY_SCALE`
(= 1024) is the capacity of the most capable CPU at its maximum frequency.
A Cortex-A55-class core typically reports roughly 400-500 against an A78-class
1024; Intel E-cores land around 0.6-0.8 of a P-core depending on generation.
Every placement decision on asymmetric silicon is arithmetic over this scale.

The signals the scheduler reads per task:

| Signal | Meaning | Producer |
|--------|---------|----------|
| `util_avg` | decaying-average CPU demand of the task (~32 ms half-life) | PELT |
| `util_est` | estimate for a just-woken task (max of enqueued history and util_avg) | PELT + wakeup history |
| `uclamp.min` | floor on effective utilization (boost: forces frequency + placement headroom) | cgroup v2 `cpu.uclamp.min` / `sched_setattr` |
| `uclamp.max` | ceiling (throttle background work's frequency demand) | cgroup v2 `cpu.uclamp.max` |
| ITD class 0-3 | hardware classification of the instruction mix (Intel only) | Thread Director via HFI tables |

`schedutil` turns the aggregate utilization into a frequency request
(`next_freq = 1.25 * max_util * max_freq`), which is why the
[cpufreq governor](../../linux/kernel/drivers/cpu-freq.md) choice is not
orthogonal to placement: EAS refuses to run without schedutil, because an
on-demand governor that jumps to max frequency erases the energy difference
the placement was optimizing.

## Who decides what a task is: software signals vs hardware hints

On ARM the classification is entirely software: a task's PELT history *is* its
classification. A task that just ran with `util_avg` 850 is a "big task"; one
at 120 is a "little task". This works but lags: a bursty task that sleeps
between bursts decays back to little-sized, then misfits on wake-up.

Intel's Thread Director (Alder Lake onward) attacks the lag with hardware
monitoring: fixed-function counters watch each software thread's instruction
mix (branch density, vector usage, memory-stall profile) and assign one of
four classes (0-3; class 0 is the unspecified default, the rest are
microarchitecture-defined per generation). The classes reach the OS through
the Hardware Feedback Interface: a per-CPU capability table (performance and
efficiency as 0-255 values) refreshed on a thermal interrupt, configured via
the `IA32_HW_FEEDBACK_*` MSRs. Hybrid enumeration is via CPUID leaf `0x1A`
(core type: `0x40` = Core/P, `0x20` = Atom/E). Linux currently consumes HFI
for thermal capacity adjustment; full per-task ITD classification drives
placement in Windows 11's scheduler and Intel's downstream kernel work, not
(yet) in mainline EAS — so today's mainline answer to "what is this task"
remains PELT + uclamp, on both ISAs.

## The EAS placement algorithm

The kernel's
[Energy Aware Scheduling doc](https://docs.kernel.org/scheduler/sched-energy.html)
specifies the preconditions, and the
[capacity-aware scheduling doc](https://docs.kernel.org/scheduler/sched-capacity.html)
specifies the arithmetic. EAS activates only when all of these hold:

1. The system is asymmetric in capacity (sched domain flag `SD_ASYM_CPUCAPACITY`).
2. An Energy Model exists: per performance domain, a table of
   (frequency, capacity, power) triples, sourced from DT/ACPI OPP data.
3. `schedutil` is the CPUfreq governor.
4. The system is **not overutilized** — once total demand exceeds capacity
   somewhere, EAS stands down and classic load balancing takes over, because
   at that point throughput matters more than energy.

Given those preconditions, wake-up placement (`find_energy_efficient_cpu()`)
has this shape:

```text
for each performance domain PD with a spare, capacity-fitting CPU:
    for each candidate CPU c in PD:
        if not fits_capacity(task, c):      # util > 80% of c's capacity
            skip
        delta_energy = compute_energy(schedule task->c)  \
                     - compute_energy(schedule task->none) # via PM EM tables
        track min delta_energy (tie-break: least loaded / lowest wake cost)
if best_delta exists: place on best CPU
else: mark misfit; load balancer will migrate to highest-capacity CPU
```

The 80% threshold in `fits_capacity()` is a deliberate safety margin: the last
20% of a CPU's capacity is left for non-scheduler activity (interrupts,
kernel threads, thermal headroom). Recent kernels also detect *capacity
inversions* — a big core downclocked far enough that its effective capacity
drops below a little core's, which flips naive energy arithmetic — inside the
energy computation.

Android layers policy on top of the same kernel EAS: the framework assigns
cpusets (`top-app`, `foreground`, `background`) and sets `uclamp` boosts per
task ("this render thread matters"), so per-app priority is expressed as
capacity clamps rather than nice values, and vendor energy models are compiled
from device OPP tables. ARM documents the same flow in its
[EAS writeup](https://developer.arm.com/community/arm-community-blogs/b/architectures-and-processors-blog/posts/energy-aware-scheduling-in-linux)
(bot-blocked to curl; search-verified). For the general DVFS/thermal stack
this sits on, see [Linux CPU performance management](../../linux/performance/cpu.md);
for the energy-vs-carbon variant at fleet scale, see
[carbon-aware scheduling](../../cloud/carbon-aware-scheduling.md).

## Why naive load balancing breaks

A load balancer written for equal cores fails on hybrid silicon in specific,
recurring ways:

| Failure mode | What happens | Kernel answer |
|--------------|--------------|---------------|
| Fair-share across unequal CPUs | CFS fairness spreads runtime equally; little cores saturate while bigs idle at low util | per-CPU capacity normalization + misfit detection |
| Misfit ping-pong | a task oscillating around the 80% threshold migrates little<->big every interval | utilization decay (PELT) + misfit hysteresis |
| Idle balance over-pull | periodic balance pulls tasks onto big cores "for throughput", burning energy | EAS disables periodic pull when not overutilized |
| Packing vs spreading confusion | packing on little saves idle power but raises OPP (power ~ freq^3-ish); spreading lowers OPP but wakes more cores | energy model tables decide, not static policy |
| SMT asymmetry | P-cores expose 2 hw threads, E-cores 1; a "CPU" is no longer a fixed unit of capacity | SMT-aware sched groups; E-core cluster as one group |
| IRQ/softirq on big cores | default irqbalance spreads device IRQs everywhere; bigs never reach idle | per-cluster IRQ affinity masks, housekeeping CPUs |
| Capacity inversion | big core thermally throttled below little capacity; old logic still calls it "big" | inversion-aware capacity in EAS |

Two of these deserve emphasis because they invert expectations. First,
**packing is not always the energy win**: on this page's model and real EM
tables, power grows superlinearly with frequency, so stacking four tasks on
one little core can cost more energy than spreading them at lower OPPs — but
it also keeps three cores in deep idle, which on some designs wins anyway.
The energy model, not intuition, is the arbiter. Second, **the misfit path is
the load balancer's remaining job**: EAS handles the well-behaved case; a
task whose util exceeds even the biggest CPU's fit threshold gets flagged and
actively migrated to the highest-capacity CPU available.

## IRQ affinity on asymmetric silicon

Interrupt handling is scheduling policy done badly by default. Two patterns
dominate hybrid deployments:

- **Pin housekeeping IRQs (timer, IPI, many device IRQs) to the little
  cluster.** Little cores handle the constant drip of small work at a fraction
  of the energy; big cores stay in idle long enough to reach their deep C/P
  states, where most of their efficiency lives.
- **Pin latency-critical device IRQs (display vblank, touch, high-rate NIC)
  next to the threads that consume the data** — on hybrid phones this usually
  means the cluster where the latency-sensitive thread was uclamp-boosted.

The tuning surface is `/proc/irq/<n>/smp_affinity_list`, plus boot-time
`isolcpus`/`nohz_full` for cores that must not see background interruptions at
all. Getting this wrong shows up as "the big cores never idle" — a symptom
that looks like a scheduler bug but is an affinity bug.

## A placement policy shootout

The model below places the same ten-task mix under three policies on a
2-big/4-little topology, with per-cluster OPP tables (capacity, power in mW).
Duration = work × 1024 / OPP-capacity; energy = OPP power × duration; tasks
sharing a CPU run sequentially. uclamp.min boosts raise both the placement
floor and the frequency demand (as the kernel does).

```python
"""Energy-performance placement optimizer over a hybrid CPU task mix.

Topology: 2 big CPUs (capacity 1024, 4 OPPs) + 4 little CPUs (capacity 430,
4 OPPs). Ten tasks, each with a utilization demand (0-1024 scale), a work
budget W (ms of execution at full big-core speed), and an optional uclamp.min
boost that raises its minimum acceptable capacity.

Model: a CPU picks the smallest OPP whose capacity covers the task's demand;
duration = W * 1024 / opp_capacity; energy = opp_power * duration. Tasks on
one CPU run sequentially. Three deterministic policies are compared:
spread round-robin, big-first packing, and an EAS-style greedy energy
optimizer with the 80% fits-capacity margin.
"""
BIG_OPPS = [(430, 250), (600, 420), (800, 700), (1024, 1100)]   # (cap, mW)
LITTLE_OPPS = [(215, 55), (300, 95), (365, 140), (430, 200)]
BIG_CAP, LITTLE_CAP = 1024, 430
FIT_MARGIN = 0.8  # EAS fits_capacity() headroom

# (name, util, work_ms, uclamp_min)
TASKS = [
    ("camera_p0",    900, 10, 1024),
    ("ui_render",    500, 20,    0),
    ("audio_cb",     120, 40,  768),
    ("gc_thread",    350, 50,    0),
    ("codec",        420, 35,    0),
    ("db_query",     300, 30,    0),
    ("net_rx",       200, 25,    0),
    ("sensor_fuse",  150, 45,    0),
    ("json_parse",   250, 30,    0),
    ("telemetry",     80, 60,    0),
]


def pick_opp(opps, demand):
    for cap, mw in opps:
        if cap >= demand:
            return cap, mw
    return opps[-1]  # misfit: demand exceeds cluster max -> clamp to top OPP


def duration_cost(cluster, util, work):
    """Return (duration_ms, energy_uJ) for one task on a cluster."""
    opps = BIG_OPPS if cluster == "big" else LITTLE_OPPS
    hit = pick_opp(opps, util)
    dur = work * 1024 / hit[0]
    return dur, hit[1] * dur


def fits(cluster, util):
    cap = BIG_CAP if cluster == "big" else LITTLE_CAP
    if util <= cap * FIT_MARGIN:
        return True
    return False


def place(policy):
    cpus = [("big", i) for i in range(2)] + [("little", i) for i in range(4)]
    queues = {c: [] for c in cpus}
    for name, util, work, clamp_min in TASKS:
        cand = list(cpus)
        if policy == "spread-rr":
            target = cand[TASKS.index((name, util, work, clamp_min)) % len(cand)]
        elif policy == "big-first":
            target = next((c for c in cand if c[0] == "big" and fits("big", util)), None)
            if target is None:
                target = next((c for c in cand if c[0] == "little"), cand[0])
        else:  # eas-greedy
            boosted = clamp_min > 0
            eff = max(util, clamp_min)  # uclamp.min raises frequency demand too
            options = []
            for c in cand:
                cl = c[0]
                if boosted and clamp_min > (BIG_CAP if cl == "big" else LITTLE_CAP):
                    continue
                if not boosted and not fits(cl, eff):
                    continue
                options.append((duration_cost(cl, eff, work)[1], len(queues[c]), c))
            if not options:  # misfit: pick highest-capacity cluster, least loaded
                options = [(0.0, len(queues[c]), c) for c in cand if c[0] == "big"]
            target = min(options)[2]
            util = eff
        queues[target].append((name, util, work))
    return queues


def evaluate(queues):
    energy = big_ms = little_ms = 0.0
    makespan = 0.0
    for cpu, q in queues.items():
        busy = 0.0
        for name, util, work in q:
            dur, en = duration_cost(cpu[0], util, work)
            busy += dur
            energy += en
        makespan = max(makespan, busy)
        big_ms += busy if cpu[0] == "big" else 0.0
        little_ms += busy if cpu[0] == "little" else 0.0
    return energy / 1000.0, makespan, big_ms, little_ms  # mJ


def main():
    print(f"{'policy':<12} {'energy':>8} {'makespan':>9} {'big-busy':>9} {'little-busy':>12}")
    for policy in ("spread-rr", "big-first", "eas-greedy"):
        q = place(policy)
        en, mk, b, l = evaluate(q)
        print(f"{policy:<12} {en:>7.2f}m {mk:>8.1f}m {b:>8.1f}m {l:>11.1f}m")
    print()
    for policy in ("spread-rr", "eas-greedy"):
        q = place(policy)
        big = sum(len(v) for k, v in q.items() if k[0] == "big")
        lit = sum(len(v) for k, v in q.items() if k[0] == "little")
        print(f"{policy}: big={big} tasks, little={lit} tasks")
        for cpu in sorted(q):
            if q[cpu]:
                names = ",".join(n for n, _, _ in q[cpu])
                print(f"  {cpu[0]}[{cpu[1]}]: {names}")
    print()
    dur, en = duration_cost("big", 120, 40)
    dl, el = duration_cost("little", 120, 40)
    print(f"audio_cb on big (u=120 -> OPP430): {dur:.1f} ms / {en/1000:.1f} mJ")
    print(f"audio_cb on little (u=120 -> OPP215): {dl:.1f} ms / {el/1000:.1f} mJ")
    db, eb = duration_cost("big", 768, 40)
    print(f"audio_cb boosted (uclamp.min=768 -> OPP800 on big): {db:.1f} ms / {eb/1000:.1f} mJ")


if __name__ == "__main__":
    main()
```

```text
policy         energy  makespan  big-busy  little-busy
spread-rr     148.97m    426.0m    210.8m       904.7m
big-first     206.63m    784.3m    784.3m        23.8m
eas-greedy    165.29m    388.2m    297.8m       824.0m

spread-rr: big=4 tasks, little=6 tasks
  big[0]: camera_p0,net_rx
  big[1]: ui_render,sensor_fuse
  little[0]: audio_cb,json_parse
  little[1]: gc_thread,telemetry
  little[2]: codec
  little[3]: db_query
eas-greedy: big=5 tasks, little=5 tasks
  big[0]: camera_p0,audio_cb,codec
  big[1]: ui_render,gc_thread
  little[0]: db_query,telemetry
  little[1]: net_rx
  little[2]: sensor_fuse
  little[3]: json_parse

audio_cb on big (u=120 -> OPP430): 95.3 ms / 23.8 mJ
audio_cb on little (u=120 -> OPP215): 190.5 ms / 10.5 mJ
audio_cb boosted (uclamp.min=768 -> OPP800 on big): 51.2 ms / 35.8 mJ
```

Reading the shootout:

- **big-first loses on both axes** (206.63 mJ, 784.3 ms): packing everything
  on two big CPUs queues tasks sequentially at expensive OPPs, and — the
  subtle trap — its 80% margin check refuses the 900-util camera task on big,
  dumping the *most* demanding task onto a little core where it clamps to the
  top OPP and runs slow. A capacity check without a capacity-*sorted*
  fallback is worse than none.
- **spread-rr has the lowest energy** (148.97 mJ) but only by ignoring
  constraints: `audio_cb` lands on a little core at 190.5 ms — a deadline
  disaster for an audio callback. Energy is not the only objective, and a
  policy that looks cheapest in a table can be unusable in production.
- **eas-greedy** spends ~11% more energy than spread-rr (165.29 vs 148.97 mJ)
  to honor the uclamp boosts and get the best makespan (388.2 ms). The
  boosted audio callback costs 3.4x the energy on big (35.8 vs 10.5 mJ) to
  run 3.7x faster — that is the energy-for-latency exchange uclamp.min
  encodes, and it is the correct trade for real-time-adjacent work.

The general lesson: hybrid placement is *constrained* optimization, not load
balancing. The kernel's EAS implements exactly the greedy heuristic in the
demo — cheapest fitting CPU, misfit fallback to the most capable core — and
lets policy (uclamp, cpusets, IRQ affinity) express the constraints it cannot
infer from utilization alone.

## Worked drills

| Drill | Answer |
|-------|--------|
| What scale do kernel capacities use? | 1024 (`SCHED_CAPACITY_SCALE`), most capable CPU at max freq |
| Which governor does EAS require? | schedutil (utilization-driven frequency) |
| When does EAS disable itself? | System overutilized — throughput beats energy, load balancer takes over |
| What is a misfit task? | One whose util exceeds the fit threshold (80% margin) of its current CPU |
| What does Intel CPUID `0x1A` return? | Core type per CPU: `0x40` P-core, `0x20` E-core |
| What is a capacity inversion? | A throttled big core whose effective capacity falls below a little core's |
| Why is big-first with a margin check dangerous? | It can eject the largest task to the weakest cluster (see shootout) |

## Cross-references

- [Scheduler internals](../../os/advanced/scheduler-internals.md) — CFS/EEVDF machinery EAS plugs into
- [Linux CPU performance](../../linux/performance/cpu.md) — cpufreq governors, PELT tooling, tunables
- [Alder Lake](../modern/alder-lake.md) and [Arm big.LITTLE cores](../modern/arm.md) — the silicon side
- [SMT](../../arch/parallelism/smt.md) — why P-core hw threads are not 2x capacity
- [CPU frequency drivers](../../linux/kernel/drivers/cpu-freq.md) — the OPP sources behind the energy model

## References

- [Linux kernel: Energy Aware Scheduling](https://docs.kernel.org/scheduler/sched-energy.html) — preconditions, energy model, fits-capacity margin. (curl-verified)
- [Linux kernel: Capacity Aware Scheduling](https://docs.kernel.org/scheduler/sched-capacity.html) — capacity scale, sched domain asymmetry flags. (curl-verified)
- [Arm: big.LITTLE Technology](https://www.arm.com/technologies/big-little) — the original asymmetric pairing design. (curl-verified)
- [Arm: DynamIQ](https://www.arm.com/technologies/dynamiq) — DSU clustering, mixed cores per cluster, on-cluster L3. (curl-verified)
- [Intel: What Is Intel Thread Director?](https://www.intel.com/content/www/us/en/support/articles/000097053/processors/intel-core-processors.html) — hardware task classification overview. (intel.com blocks bots; search-verified)
