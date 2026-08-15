# Scheduler Internals

The [Linux CFS overview](../scheduling/linux-cfs.md) covers the basics of virtual runtime, red-black trees, and fairness. This section goes deeper into the actual data structures, the 2024 EEVDF transition, scheduler classes, real-time extensions (PREEMPT_RT), deadline scheduling, and NUMA-aware scheduling decisions.

## CFS Internals — The Red-Black Tree and Vruntime

The Completely Fair Scheduler maintains all runnable tasks of normal priority in a per-CPU **red-black tree** keyed by `vruntime`. The leftmost node (minimum vruntime) is the next task to run. On context switch, the current task's vruntime is updated and it's reinserted into the tree.

### Vruntime Calculation

```
vruntime_delta = actual_runtime * (NICE_0_LOAD / task.weight)
vruntime_new  = vruntime_old + vruntime_delta
```

Where `task.weight` comes from the `prio_to_weight[]` table (mapped from nice values -20 to +19). Nice 0 has weight 1024; nice -20 has weight 88761 (86.7x more CPU share). The weight table follows a ~25% per-nice-level geometric progression, matching the POSIX `nice()` specification.

### Sched Entity and CFS_rq

Every task is wrapped in a `sched_entity` structure containing vruntime, runqueue pointer, tree node, and statistics. For `CONFIG_CGROUP_SCHED`, task groups create hierarchical `task_group` structures, each with their own `cfs_rq` (CFS runqueue). This enables fair sharing not just between processes, but between cgroups — the root `cfs_rq` distributes CPU among cgroups, and each cgroup's `cfs_rq` distributes among its tasks.

```c
struct cfs_rq {
    struct rb_root_cached tasks_timeline;  // RB-tree of sched_entities
    struct rb_node *rb_leftmost;           // cached leftmost for O(1) pick_next
    u64 min_vruntime;                      // monotonic floor for vruntime
    unsigned int nr_running;               // queue length
    struct sched_entity *curr;             // currently running entity
    u64 runtime_spread;                    // max_vruntime - min_vruntime (fairness metric)
};

struct sched_entity {
    struct rb_node run_node;     // RB-tree node
    u64 vruntime;                // virtual runtime
    u64 sum_exec_runtime;        // total actual runtime
    struct load_weight load;     // priority weight
    struct cfs_rq *cfs_rq;       // which queue this entity is on
    struct cfs_rq *my_q;         // if this is a group, its child cfs_rq
};
```

## EEVDF — Earliest Eligible Virtual Deadline First

In Linux 6.6 (merged 2023, default in 6.8+), CFS was replaced by **EEVDF** as the scheduling algorithm for the `SCHED_NORMAL` class. The motivation: CFS has known fairness and latency issues.

### CFS Problems that EEVDF Solves

1. **Latency overshoot for short tasks**: CFS's vruntime only prevents starvation, not latency. A task that slept for a long time has very low vruntime and runs immediately, but a newly-woken short task might wait behind a long-running task with only slightly lower vruntime.

2. **Inability to set a latency target**: CFS has `sched_latency_ns` (target scheduling period) and `min_granularity_ns`, but they're weak heuristics. There's no mathematical guarantee that any task waits longer than the target.

3. **Throttling interaction**: CFS throttling (via `cfs_b` bandwidth control) interacts poorly with vruntime, causing bursty behavior.

### EEVDF Mechanism

EEVDF assigns each task a **virtual deadline** (`vruntime + requested_quota / weight`), not just a virtual runtime. The scheduler picks the task with the **earliest eligible** deadline. A task becomes eligible when its virtual time (not wall time) reaches its deadline.

```
CFS:   pick task with smallest vruntime
EEVDF: pick task with smallest (vruntime + slice / weight)
       but only if current_vruntime >= task's previous deadline
```

This provides a mathematical latency guarantee: no task waits longer than `sched_period * n_running`. The implementation in Linux (by Peter Zijlstra) replaces the RB-tree with a simpler **cached RB-tree** where the leftmost node is always the EEVDF candidate.

### Key Differences in Practice

| Aspect | CFS | EEVDF |
|--------|-----|-------|
| Pick criterion | Min vruntime | Min eligible deadline |
| Latency guarantee | Heuristic | Mathematical (≤ period × n) |
| Sleeper bonus | Large (vruntime lags) | Controlled (max lag bounded) |
| CPU-bound fairness | Good | Good (equivalent) |
| Interactive responsiveness | Good | Better (latency-targeted) |
| Data structure | RB-tree (same) | RB-tree (same, different key) |

## Scheduler Classes

Linux uses a pluggable scheduler class system. Each CPU's runqueue (`rq`) contains linked lists for each class, and the highest-priority class with runnable tasks wins:

```c
// Scheduler class hierarchy (highest to lowest priority)
static const struct sched_class *sched_class_hierarchy[] = {
    &stop_sched_class,     // per-CPU stop task (highest, not preemptible)
    &dl_sched_class,       // SCHED_DEADLINE (bandwidth-reserved)
    &rt_sched_class,       // SCHED_FIFO / SCHED_RR (real-time)
    &fair_sched_class,     // SCHED_NORMAL / SCHED_BATCH (CFS/EEVDF)
    &idle_sched_class,     // SCHED_IDLE (lowest, only when nothing else)
    NULL
};
```

The `pick_next_task()` function walks this list: if the deadline class has runnable tasks, it wins over real-time, which wins over fair. The `check_preempt_wakeup()` function determines if a newly-woken task should preempt the current task, again respecting class priority.

## SCHED_DEADLINE

`SCHED_DEADLINE` (Linux 3.14+, EDF scheduler) implements the **Earliest Deadline First** real-time scheduling algorithm with bandwidth reservations. Each deadline task specifies three parameters:

- **runtime**: maximum CPU time per period
- **deadline**: relative deadline within each period
- **period**: length of the repeating cycle

```bash
# Assign 10ms of CPU every 50ms, with 30ms deadline within each period
chrt -d -T 50000000 -D 30000000 -P 50000000 10 $$
```

The admission controller ensures total deadline bandwidth on a CPU doesn't exceed available capacity (with a small reserve for non-deadline tasks). The underlying data structure is a **red-black tree** sorted by absolute deadline. This is used in audio processing, industrial control, and Kubernetes `SCHED_DEADLINE` pod support (v1.28+).

## CPU Affinity and Scheduling Domains

### `sched_setaffinity()` and `cpuset`

CPU affinity constrains a task to a subset of CPUs via a bitmask (`cpumask_t`). The scheduler only places the task on allowed CPUs. `cpuset` (cgroup controller) extends this to groups of tasks. `numactl --cpunodebind=0` sets affinity for all CPUs in NUMA node 0.

### Scheduling Domains and Topology

The kernel builds a hierarchy of **scheduling domains** from the CPU topology (parsed from ACPI/Device Tree). Each domain has a `sd_level` and `sd_flags` controlling load balancing behavior:

```
SMT domain (hyperthreads share core)
    │ balance: only if core is idle
    MC domain (cores share LLC cache)
        │ balance: frequently (shared cache)
    NUMA domain (sockets, separate memory)
        │ balance: infrequently (cross-socket migration costly)
    DIE domain (multi-socket)
        │ balance: rarely
```

`SD_LOAD_BALANCE`, `SD_BALANCE_WAKE`, `SD_ASYM_PACKING` (prefer one hyperthread per core before filling both) are flags that tune when and how aggressively the kernel migrates tasks between CPUs.

## NUMA-Aware Scheduling

NUMA scheduling extends scheduling domains with memory locality awareness. When the scheduler considers migrating a task from CPU A to CPU B, it estimates the **memory migration cost**: how many of the task's pages are on node A's memory vs. node B's. The `task_numa_fault()` infrastructure tracks per-node page access frequency using a two-pass sampling scheme (see [NUMA](../memory/numa.md)).

The `numad` daemon and the kernel's `sched_numa` balance work together: the kernel tracks per-task NUMA fault statistics, and `sched_balance_numa()` migrates tasks to nodes where most of their memory resides, subject to a "migration threshold" to prevent ping-pong.

## PREEMPT_RT — Real-Time Preemption

The PREEMPT_RT patch set (mainlined incrementally since v5.0, largely complete in v6.12) converts most Linux kernel spinlocks to **preemptible mutexes**, allowing kernel code to be preempted by real-time tasks. The key changes:

1. **Spinlocks → `rt_mutex`**: Most `spin_lock()` calls become preemptible sleeping locks. Only raw spinlocks (hardware access, scheduler internals) remain truly spinning.

2. **Interrupt handlers → threads**: Hardware interrupt handlers (`IRQF_` handlers) run in kernel threads with real-time priorities. This allows a high-priority `SCHED_FIFO` task to preempt interrupt handling.

3. **Local lock removal**: `local_irq_save()`/`local_irq_disable()` are replaced with preemptible per-CPU locks, eliminating interrupt masking as a synchronization mechanism.

```c
// Before PREEMPT_RT:
spin_lock(&lock);  // disables preemption, may disable interrupts
// ... critical section ...
spin_unlock(&lock);

// After PREEMPT_RT:
// spin_lock(&lock) becomes rt_mutex_lock(&lock)
// A higher-priority RT task can preempt this critical section
// (if it doesn't need the same lock)
```

This is critical for audio (JACK, PipeWire), industrial control, and automotive (ELISA project). The trade-off: slightly higher overhead for lock acquisition (mutex vs. spinlock) and increased kernel complexity.

## Scheduling Isolation

`sched_setaffinity` constrains *where* a task runs. **Isolation** constrains *what else runs there*:

- `isolcpus=1,2,3` (kernel boot parameter): removes CPUs 1-3 from the general scheduling domain. No load balancing, no timer ticks migrate to them. Only tasks explicitly pinned run there.

- `nohz_full=1,2,3`: disables periodic timer ticks on those CPUs (adaptive ticks). Reduces wakeups from ~250 Hz (CONFIG_HZ=250) to near-zero, critical for latency-sensitive workloads.

- `rcu_nocbs=1,2,3`: moves RCU callbacks off isolated CPUs (see [sync-primitives.md](./sync-primitives.md)).

- `taskset`/`cset` for runtime affinity management. Kubernetes uses `CPUManager` with the `static` policy to pin guaranteed pods to exclusive cores.

## Interview Questions

1. **"Why did Linux replace CFS with EEVDF?"** Answer hint: CFS uses vruntime for fairness but provides no mathematical latency bound. A task can wait arbitrarily long behind slightly-lower-vruntime tasks. EEVDF adds deadline semantics: each task's virtual deadline is computed from its weight and requested slice, and the scheduler picks the earliest eligible deadline. This guarantees max wait time ≤ sched_period × n_running.

2. **"How does PREEMPT_RT affect a driver writer?"** Answer hint: Under PREEMPT_RT, `spin_lock()` may sleep, so you can't hold one while in atomic context (no `kmalloc(GFP_ATOMIC)` reasoning — actually you *can* use GFP_KERNEL now in many places). You must use `raw_spin_lock_t` for true non-preemptible sections (register access, scheduler data). Interrupt handlers run as threads, so they have a process context and can sleep.

3. **"What happens when a SCHED_DEADLINE task exceeds its runtime?"** Answer hint: It is throttled — moved off the runqueue until the next period begins. The kernel tracks consumed runtime per period. If the task uses more than its reserved `runtime` within a `period`, it's descheduled. This prevents one deadline task from starving others and enforces the admission control contract.

## References
- Zijlstra, P. "EEVDF Scheduling." LKML patch series, 2023.
- Baruah et al. "The Earliest Eligible Virtual Deadline First Scheduling Algorithm." RTSS 2019.
- Cerqueira & Brandenburg. "A Comparison of Scheduling Latency in Linux PREEMPT_RT and LITMUS^RT." RTAS 2013.
- Linux source: `kernel/sched/fair.c`, `kernel/sched/rt.c`, `kernel/sched/deadline.c`.
