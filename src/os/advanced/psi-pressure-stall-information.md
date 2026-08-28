# PSI: Pressure Stall Information - Stall Time as a First-Class Metric

Every performance signal Linux exposed before 2018 answers a variant of "how busy is the machine"; none answer "how much work is being lost". Pressure Stall Information (PSI), designed by Johannes Weiner at Facebook for their Oomd fleet-management problem and merged into Linux 4.20 (October 2018 merge window), measures exactly that: the wall-clock time tasks spend stalled waiting for CPU, memory, or I/O, aggregated as percentages plus cumulative totals. A system can be at 100% CPU utilization and be perfectly healthy - or be thrashing itself to death - and load average cannot tell the two apart. PSI can, and it ships with a push-based notification API so userspace can react before the OOM killer does.

This page covers the semantics of the metric, the interface formats, the kernel accounting machinery, pressure triggers, and the userspace consumers (oomd, systemd-oomd, Android). The operations cookbook - commands, cgroup recipes, troubleshooting - lives in the companion page [Pressure Stall Information (PSI)](../../linux/kernel/processes/psi.md); the memory-side context (reclaim, OOM) is in [Memory Internals](memory-internals.md), and [KSM Page Merging](ksm-page-merging.md) is the other page in this group that exists because of memory-overcommit pressure.

## 1. What PSI measures: the "some" / "full" language

PSI distinguishes two severities of stall per resource:

- **some**: the share of time when *at least one* non-idle task is stalled on the resource. Work still progresses; other tasks keep the CPU busy. This is "partial stall".
- **full**: the share of time when *all* non-idle tasks are stalled on the resource *simultaneously*. In this state actual CPU cycles go to waste - nothing useful can run - and a workload spending extended time here is what the kernel documentation calls thrashing. This is "total stall", tracked separately precisely because the kernel doc draws the line there: some tasks stalled while the CPU still does productive work is a very different situation from everything being blocked.

Both lines exist for memory and I/O. CPU is the subtlety: "CPU full" is undefined at the system level (if every non-idle task were stalled waiting for a CPU, nothing - including the accounting itself - could run), so since v5.13 the kernel reports the CPU `full` line as zero for backward compatibility rather than a meaningless number.

| Resource | `some` means | `full` means | Reported? |
|----------|--------------|--------------|-----------|
| cpu | at least one task is runnable but waiting for a CPU | undefined at system level | yes; full always `0.00` since v5.13 |
| memory | at least one task is blocked in reclaim (direct reclaim/compaction) | every non-idle task is stalled on memory at the same instant | yes |
| io | at least one task is in iowait | every non-idle task is stalled on I/O at the same instant | yes |

Note what `some` does *not* say: it does not identify which task, how long any single task waited, or whether the stall is pathological. On a deliberately oversubscribed batch box, `cpu some` trending high is the design working. Interpretation comes from pairing the three resources and watching their ratios - the topic of section 8.

## 2. The interface: /proc/pressure and cgroup pressure files

System-wide values are exposed in three files under `/proc/pressure/`:

```text
$ cat /proc/pressure/memory
some avg10=0.12 avg60=0.05 avg300=0.01 total=41234567
full avg10=0.00 avg60=0.00 avg300=0.00 total=0
$ cat /proc/pressure/cpu        # note: full line present but always zero
some avg10=42.50 avg60=38.11 avg300=21.44 total=987654321
full avg10=0.00 avg60=0.00 avg300=0.00 total=0
```

| Field | Meaning |
|-------|---------|
| avg10 / avg60 / avg300 | percentage of the last 10 / 60 / 300 seconds spent in the stall state (plain window fractions, not exponential moving averages) |
| total | cumulative stall time in **microseconds** since boot; detects sub-window latency spikes the averages smooth away, and lets you compute custom windows |

With cgroup v2, the same format is available per control group as `cpu.pressure`, `memory.pressure`, and `io.pressure` inside each group's directory - which is what makes per-service policy (section 6) possible. PSI is gated by `CONFIG_PSI`; if the kernel is built with `CONFIG_PSI_DEFAULT_DISABLED=y` (some distros ship this), it must be enabled at boot with `psi=1`, otherwise `/proc/pressure/` does not exist at all.

The accounting pipeline, end to end:

```text
  task_struct state bits          per-CPU/cgroup aggregation        export
+------------------------+      +---------------------------+     +-----------------+
| TSK_RUNNING / TSK_ONCPU|      | psi_group_cpu:            |     | /proc/pressure/ |
| TSK_IOWAIT  TSK_MEMSTALL| --> | 6 stall-state time masks  | --> | cpu.pressure    |
| set/cleared at schedule |     | 2s tracking window split  |     | memory.pressure |
| points + memstall hooks |     | into 4 x 500ms buckets    |     | io.pressure     |
+------------------------+      +---------------------------+     +-----------------+
        psi_task_switch()         window recompute + triggers
        psi_memstall_enter/exit() poll() wakeups on threshold
```

## 3. Inside the kernel: how stall time gets accounted

The kernel does not sample; it observes every scheduling decision and stamps time deltas onto per-task state bits in `task_struct` (the `psi_flags`): `TSK_RUNNING` (task is running or runnable), `TSK_ONCPU` (actually on a CPU), `TSK_IOWAIT` (blocked in `io_schedule()`), and `TSK_MEMSTALL` (blocked in memory reclaim). From the combination of bits it derives the six PSI states - `IO_SOME`, `IO_FULL`, `MEM_SOME`, `MEM_FULL`, `CPU_SOME`, `CPU_FULL` - because, for example, a task that is runnable *and* in reclaim counts toward memory pressure, not CPU pressure.

Hook points:

- **Context switches** (`psi_task_switch`): when a task stops running, the bit changes propagate to every PSI state the task was contributing to, and the elapsed time is charged to the current bucket of each affected per-CPU group. When the next task is picked up, its contribution starts. A single context switch can therefore move time into several states at once (e.g. the outgoing task was in iowait-class accounting while the incoming one is immediately memstall).
- **Memory reclaim**: `psi_memstall_enter()` / `psi_memstall_exit()` bracket direct-reclaim sections (allocations going synchronous), so compaction and shrinker work show up as memory pressure even when the task is technically running a loop inside reclaim.
- **I/O**: iowait classification at schedule-out for tasks waiting on disk, which is why `io some` and the `vmstat` `b`/`wa` columns correlate (but are not identical - see section 8).

Aggregation: each task's deltas accumulate into the `psi_group_cpu` of its cgroup (and the root group), which keeps time-in-state per 500ms slot. A 2-second tracking window is divided into 4 such buckets; on window boundary the kernel recomputes the fractions of time in each stall state and feeds the rolling 10s, 60s, and 300s averages that `avg10/60/300` display. This two-level design (cheap per-switch bit stamping, periodic window recompute) is why PSI overhead stays low even on busy machines. Cgroup-level accounting and the trigger/monitor machinery both landed in v5.2, at which point Android's low-memory killer daemon could standardize on PSI as its primary signal.

One historical wrinkle worth knowing in interviews: PSI originally reported a real `cpu full` value; v5.13 zeroed it because "all non-idle tasks stalled on CPU" cannot actually occur at system scope, and a nonzero reading there was an artifact, not a signal.

## 4. Pressure triggers: push instead of poll

Reading `/proc/pressure/` on a timer is lossy and costs a wakeup storm at scale. Instead, a process can register a **trigger**: it opens a pressure file, writes a threshold plus a window, and then `poll()`s the descriptor - POLLPRI arrives when the cumulative stall in any window is about to exceed the threshold.

```text
# register: "<some|full> <stall threshold in us> <window in us>"
fd = open("/proc/pressure/memory", O_RDWR | O_NONBLOCK)
write(fd, "some 150000 1000000")   # wake me if 150ms of partial memory
...                                # stall accumulates within any 1s window
poll(fd, POLLPRI, -1)
```

The rules that matter in practice:

- Window sizes range from **500 ms to 10 s**; the kernel checks a trigger's growth rate 10 times per tracking window (so between 50 ms and 1 s between checks).
- **Unprivileged users** may register triggers only with window sizes that are multiples of 2 s (to bound resource use).
- A second `write()` to an fd that already carries a trigger fails with `EBUSY`; each trigger needs its own `open()` even for the same file, so they can be polled independently. Closing the fd de-registers the trigger.
- Notifications are **rate-limited to one per tracking window**, and a monitor stays armed for at least one window to avoid flapping when the system bounces in and out of a stall state.

This is the epoll-style design: the kernel does the watching, userspace sleeps. Android's `lmkd` uses exactly this mechanism (PSI monitors merged in v5.2 were shaped by its requirements), and oomd polls triggers rather than reading files on a timer.

## 5. OOM killer vs PSI: memory.full as the early warning system

The OOM killer fires only after allocation has *already* failed - swap exhausted, reclaim hopeless - and then the cure is killing something arbitrary-ish under a lock. Thrashing starts much earlier: the system is alive but spending most of its time reclaiming. That gap between "working" and "OOM" is precisely what `memory full` (and sustained high `memory some`) measures, and it is the entire design premise of PSI.

| | classic OOM killer | PSI-driven daemon |
|---|--------------------|-------------------|
| trigger condition | allocation failure, no reclaim progress | sustained memory stall fraction above threshold |
| reaction time | after the system is already wedged | seconds to minutes of thrashing warning |
| decision basis | oom_score, heuristics at kill time | per-cgroup pressure + policy config |
| action | SIGKILL one victim process | SIGKILL a chosen *cgroup*, load-shed, or alert |
| failure mode | kills the wrong thing late | needs sane thresholds per workload |

Facebook's experience was that reclaim-based heuristics (like the older `vmpressure` notifications - see [vmpressure](../../linux/kernel/memory/vmpressure.md)) produced an order of magnitude more false positives than stall-time measurements; PSI monitors were measured at roughly 10x fewer false positives versus vmpressure in the kernel's own Android integration work.

## 6. Userspace consumers

**oomd** ([github.com/facebookincubator/oomd](https://github.com/facebookincubator/oomd)) is the userspace OOM killer Facebook built *for* PSI. It reads pressure information (system and per-cgroup), evaluates rules - e.g. "kill the highest-swap-usage descendant of this cgroup when its `memory.full`-class pressure stays above X% for Y seconds" - and kills cgroups, not individual PIDs, respecting configurable kill preferences. It has run across Meta's fleet since the PSI days and is the reference design for pressure-driven management.

**systemd** integrates the same idea: `systemd-oomd.service` (the userspace OOM killer shipped with systemd since v245, based on the oomd experience) consumes per-cgroup pressure data. Units/cgroups opt in with the `ManagedOOMSwap=` and `ManagedOOMMemoryPressure=` properties (values `auto` or `kill`); `ManagedOOMMemoryPressureLimit=` sets the percentage threshold for that unit, overriding `oomd.conf` defaults. When the pressure limit is passed, systemd-oomd SIGKILLs the processes of a selected descendant cgroup. The man page documenting these is [systemd.resource-control(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html) (oomd behavior in systemd-oomd.service(8) and oomd.conf(5)).

**Android**: `lmkd` registers PSI triggers for memory stall and chooses victims using per-process watermarks plus pressure events - replacing the older minfree-style polling.

For the SRE angle: PSI totals are a natural saturation SLI for capacity planning (see [Capacity Planning](../../sre/capacity-planning.md)) - "memory some > 5% for more than 1% of a week" is a far more honest capacity metric than a hard memory-utilization watermark, because it measures *lost work* rather than *fill level*.

## 7. A worked model of the aggregation

The script below builds a synthetic 4-task timeline (states: on-CPU, runnable-waiting-for-CPU, stalled-in-reclaim, stalled-in-iowait, idle), computes the `some`/`full` percentages per 1s window exactly per the definitions in section 1, and emulates a trigger registered as `some 200000 1000000` on memory (one wakeup per window, as the kernel rate-limits). The story: a batch task starts reclaiming (t=2s), the system tips into thrashing (t=4-6s, note `memory.full` at 80-100% while `io.full` stays 0 - the memory stall masks the I/O stall), a daemon kills the batch task, and pressure decays.

```python
# PSI aggregation model: 4 tasks, 10 windows x 10 ticks of 100 ms.
# Per-task states: R = on-CPU, C = runnable waiting for CPU, M = stalled in
# memory reclaim, I = stalled in iowait, _ = idle (not counted at all).
RUN, CPU, MEM, IO, IDLE = "run", "cpu", "mem", "io", "idle"
CHAR = {"R": RUN, "C": CPU, "M": MEM, "I": IO, "_": IDLE}
tasks = ["A", "B", "C", "D"]                      # A/B foreground, C batch, D io worker
windows = [                                        # one pattern string per task per window
    ["RRRRRRRRRR", "RRRRRRRCRR", "__________", "I__I__I__I"],  # 0 calm
    ["RRRRRRRRRR", "RRRRRRRCRR", "__________", "I__I__I__I"],  # 1 calm
    ["RRRRRMMMMM", "RRRRRRRRRR", "____MMMMMM", "I____I____"],  # 2 reclaim ramps up
    ["RRRRRMMMMM", "RRRRRRRRRR", "____MMMMMM", "I____I____"],  # 3
    ["MMMMMMMMMM", "MMMMMMMMMM", "MMMMMMMMMM", "IIMMMMMMMM"],  # 4 thrashing
    ["MMMMMMMMMM", "MMMMMMMMMM", "MMMMMMMMMM", "IIMMMMMMMM"],  # 5
    ["MMMMMMMMMM", "MMMMMMMMMM", "MMMMMMMMMM", "MMMMMMMMMM"],  # 6 peak: memory full
    ["MMRRRRRRRR", "RRRRRRRRRR", "__________", "II________"],  # 7 daemon killed task C
    ["RRRRRRRRRR", "RRRRRRRRRR", "__________", "I____I____"],  # 8 recovered
    ["RRRRRRRRRR", "RRRRRRRRRR", "__________", "I____I____"],  # 9
]
TICK_US, THRESH, WINDOW_US = 100_000, 200_000, 1_000_000   # 100 ms tick; "some 200000 1000000"
totals = {r: {"some": 0, "full": 0} for r in ("memory", "io", "cpu")}
for w, pats in enumerate(windows):
    grid = [[CHAR[c] for c in pat] for pat in pats]           # grid[task][tick]
    nonidle = [t for t in range(len(tasks)) if any(grid[t][k] != IDLE for k in range(10))]
    acc = {r: {"some": 0, "full": 0} for r in totals}
    for k in range(10):
        states = {r: [grid[t][k] for t in nonidle] for r in ("mem", "io", "cpu")}
        acc["memory"]["some"] += any(s == MEM for s in states["mem"])
        acc["io"]["some"] += any(s == IO for s in states["io"])
        acc["cpu"]["some"] += any(s == CPU for s in states["cpu"])
        for r, ch in (("mem", MEM), ("io", IO), ("cpu", CPU)):
            # full: ALL non-idle tasks stalled on the same resource in this tick
            if states[r] and all(s == ch for s in states[r]):
                acc["memory" if r == "mem" else r]["full"] += 1
    line = f"t={w}s"
    for r in ("memory", "io", "cpu"):
        for m in ("some", "full"):
            us = acc[r][m] * TICK_US
            totals[r][m] += us
            pct = 100.0 * acc[r][m] * TICK_US / WINDOW_US
            if m == "some" or us or r != "cpu":               # cpu full always zeroed (v5.13+)
                line += f"  {r}.{m}={pct:5.2f}%"
    print(line)
    if acc["memory"]["some"] * TICK_US >= THRESH:             # trigger "some 200000 1000000"
        print(f"t={w}s  [trigger] memory some: {acc['memory']['some']*TICK_US}us "
              f">= {THRESH}us within {WINDOW_US}us window -> poll() POLLPRI wakeup")
print("final totals (us):", {r: f"some={totals[r]['some']} full={totals[r]['full']}" for r in totals})
```

Output (real run of the script above):

```text
t=0s  memory.some= 0.00%  memory.full= 0.00%  io.some=40.00%  io.full= 0.00%  cpu.some=10.00%
t=1s  memory.some= 0.00%  memory.full= 0.00%  io.some=40.00%  io.full= 0.00%  cpu.some=10.00%
t=2s  memory.some=60.00%  memory.full= 0.00%  io.some=20.00%  io.full= 0.00%  cpu.some= 0.00%
t=2s  [trigger] memory some: 600000us >= 200000us within 1000000us window -> poll() POLLPRI wakeup
t=3s  memory.some=60.00%  memory.full= 0.00%  io.some=20.00%  io.full= 0.00%  cpu.some= 0.00%
t=3s  [trigger] memory some: 600000us >= 200000us within 1000000us window -> poll() POLLPRI wakeup
t=4s  memory.some=100.00%  memory.full=80.00%  io.some=20.00%  io.full= 0.00%  cpu.some= 0.00%
t=4s  [trigger] memory some: 1000000us >= 200000us within 1000000us window -> poll() POLLPRI wakeup
t=5s  memory.some=100.00%  memory.full=80.00%  io.some=20.00%  io.full= 0.00%  cpu.some= 0.00%
t=5s  [trigger] memory some: 1000000us >= 200000us within 1000000us window -> poll() POLLPRI wakeup
t=6s  memory.some=100.00%  memory.full=100.00%  io.some= 0.00%  io.full= 0.00%  cpu.some= 0.00%
t=6s  [trigger] memory some: 1000000us >= 200000us within 1000000us window -> poll() POLLPRI wakeup
t=7s  memory.some=20.00%  memory.full= 0.00%  io.some=20.00%  io.full= 0.00%  cpu.some= 0.00%
t=7s  [trigger] memory some: 200000us >= 200000us within 1000000us window -> poll() POLLPRI wakeup
t=8s  memory.some= 0.00%  memory.full= 0.00%  io.some=20.00%  io.full= 0.00%  cpu.some= 0.00%
t=9s  memory.some= 0.00%  memory.full= 0.00%  io.some=20.00%  io.full= 0.00%  cpu.some= 0.00%
final totals (us): {'memory': 'some=4400000 full=2600000', 'io': 'some=2200000 full=0', 'cpu': 'some=200000 full=0'}
```

Two things the model makes visible. First, `full` is a strict subset of `some` for the same resource - every full tick also counts as some - which is why `memory.full` can be 80% while `memory.some` reads 100%. Second, the real kernel does not recompute at window boundaries only: trigger monitors sample the stall *growth rate* 10 times per window so that a fast ramp fires mid-window; the boundary evaluation here is a simplification that keeps the model one page long.

## 8. PSI vs load average vs vmstat

| Signal | What it reports | Blind spots |
|--------|-----------------|-------------|
| load average (1/5/15) | exponentially-smoothed count of runnable + uninterruptible tasks | conflates CPU demand, reclaim, and disk wait into one number, so a thrashing box and a CPU-saturated box can read identically; no totals, no push |
| vmstat `r` / `b` / `wa` | instantaneous samples of run-queue length, blocked tasks, iowait share | point-in-time snapshots miss spikes between samples; cannot distinguish memory vs io as the blocking resource for a runnable-but-waiting task |
| PSI | per-resource stall fractions over 10/60/300s windows + us-accurate totals + threshold push events | no per-task attribution; `some` does not say which task or why; averages lag short spikes unless you use totals/triggers |

The load-average comparison deserves precision, because Linux's loadavg already folds `D`-state (uninterruptible) tasks into the count, so a thrashing box inflates loadavg too. The difference is *decomposition and actionability*: loadavg says "something is queued"; PSI says "X% of the last minute was spent stalled on memory specifically, here is a cumulative counter, and I will wake you when it crosses your threshold". vmstat's `wa` column is the closest legacy analogue to `io some`, but it is a sampled estimate rather than exact accounting, and it has no `full`-class notion at all.

## 9. Tuning knobs and caveats

- **Enablement**: build with `CONFIG_PSI=y`; if `CONFIG_PSI_DEFAULT_DISABLED=y` (a common distro choice to save the small per-switch overhead on machines that will never read it), boot with `psi=1` or the pressure files simply do not exist.
- **CPU pressure is subtle**: `cpu some` counts runnable-but-waiting time, which on an intentionally packed batch server is permanently high and *healthy*; alarm only on changes from the box's own baseline, and remember `cpu full` is always zero by definition since v5.13.
- **Averages lag; totals spike**: a 300ms stall inside a 10s window vanishes into `avg10=3.00` but shows up exactly in the `total=` delta - latency-sensitive services should alert on totals deltas or register triggers, not on the averages.
- **Trigger limits**: windows below 500ms are rejected, and one wakeup per window maximum - PSI triggers are for pressure management, not for microsecond-latency tracing (use ftrace/BPF for that).
- **Overhead is small but real**: every context switch touches the PSI state machine; the design (bit stamping + periodic bucket recompute) keeps it in the noise for most workloads, which is why distros feel comfortable shipping it enabled - but it is not free, hence `CONFIG_PSI_DEFAULT_DISABLED` existing at all.
- **Containers see host values in /proc**: system-wide `/proc/pressure/*` is the *host's* numbers; inside a container use the cgroup's own `cpu.pressure` / `memory.pressure` / `io.pressure` files for a scoped view.
- **KSM interplay**: memory-overcommit tricks like [KSM page merging](ksm-page-merging.md) trade CPU and page-fault cost for RAM; PSI is the honest scoreboard for whether that trade is paying off on a given host.
- **Legacy precursor**: cgroup v1's `vmpressure` notifications solved a sliver of this problem with far more noise; new code should target PSI only.

## References

1. Kernel documentation: *PSI - Pressure Stall Information* (Johannes Weiner, kernel.org) - <https://docs.kernel.org/accounting/psi.html>
2. LWN: *Tracking pressure-stall information* (Jonathan Corbet, July 2018) - <https://lwn.net/Articles/759781/>
3. LWN: *Pressure stall monitors* (Jonathan Corbet, September 2018) - <https://lwn.net/Articles/775971/>
4. oomd - userspace OOM killer built on PSI (Facebook/Meta) - <https://github.com/facebookincubator/oomd>
5. systemd.resource-control(5) - `ManagedOOMMemoryPressure=`, `ManagedOOMSwap=`, `ManagedOOMMemoryPressureLimit=` - <https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html>
