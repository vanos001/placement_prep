# uclampset — manipulate utilization clamping for a process or the system

## Overview

`uclampset` reads or sets the **utilization clamping** attributes (`uclamp_min`, `uclamp_max`) of a single task (all its threads with `-a`) or of the whole system (`-s`). Utilization clamping is a kernel scheduler feature (mainline since kernel 5.3, `CONFIG_UCLAMP_TASK`) that bounds the *utilization signal* a task contributes to frequency-selection (DVFS) and energy-aware placement decisions: `uclamp_min` boosts a task so it always "looks" at least N/1024 busy, and `uclamp_max` caps it so it can never request more than N/1024 worth of capacity. The tool ships in the Debian `util-linux` package at `/usr/bin/uclampset`.

You reach for `uclampset` on mobile/embedded and power-sensitive servers: keep a UI or latency-critical task from idling into low frequencies (`uclampset -m 512 -p PID`), stop a background scanner from forcing big cores or high clocks (`uclampset -M 128 cmd`), or bias task placement on asymmetric big.LITTLE systems. It is often confused with `taskset` (pins CPUs; `uclampset` biases *frequency/placement preference* without restricting where the task runs) and `chrt` (policy and priority, not utilization). It manipulates the same clamp the cgroup v2 files `cpu.uclamp.min`/`cpu.uclamp.max` express for groups.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/uclampset |
| First appeared | util-linux 2.36 era (2020), alongside kernel 5.3 util clamp |
| Standards | none; Linux-specific (`sched_setattr(2)`, `SCHED_FLAG_UTIL_CLAMP_*`) |

## Synopsis

```
uclampset [options] [-m uclamp_min] [-M uclamp_max] command [argument...]
uclampset [options] [-m uclamp_min] [-M uclamp_max] -p PID
uclampset [options] -s | -p PID        # read current values
```

Main one-line forms:

```
uclampset -p 1234                  # show PID 1234's current util_min/util_max
uclampset -m 512 cmd               # run cmd boosted: min utilization 512/1024
uclampset -M 256 -p 1234           # cap PID 1234's utilization request at 256/1024
uclampset -s -M 512                # system-wide max clamp
uclampset -R -m 256 cmd            # boost cmd, reset clamps for its children
uclampset -aM 128 -p 1234          # cap every thread of a process
```

## How It Works

### What the clamp clamps

The scheduler tracks each task's utilization (roughly: how much CPU time it would like per second, expressed 0..1024). That signal drives:

1. **Frequency selection** (schedutil governor: aggregate utilization → clock rate).
2. **Energy-aware placement** on heterogeneous CPUs (task capacity vs core capacity).

Clamping rewrites the *ends* of that signal per task:

```
raw utilization:   0 ................. 1024
uclamp_min (512):      [=============|.................   never reported below 512
uclamp_max (256):  0 .................|====]              never reported above 256
```

The task still runs wherever the load balancer puts it and can use as much *CPU time* as the policy allows — the clamp changes the *performance request* attached to the task, not its entitlement. That distinction (uclamp = frequency/placement bias; cgroup CPU bandwidth = time entitlement) is the interview-grade takeaway.

### Setting it: `sched_setattr(2)`

For a task or thread group, `uclampset` issues `sched_setattr(2)` with `SCHED_FLAG_UTIL_CLAMP_MIN`/`SCHED_FLAG_UTIL_CLAMP_MAX` carrying the new values. System scope writes the kernel's `sched_util_clamp_min`/`sched_util_clamp_max` sysctls, which bound the effective clamp of every task. With `-R` the kernel's reset-on-fork flag is also set so forked children drop back to the defaults.

```
$ uclampset -p <pid>          # read via sched_getattr(2)
$ uclampset -m 512 -M 900 -p <pid>
$ uclampset -m -1 -p <pid>    # -1 resets an attribute to the system default
```

### The energy-aware scheduling context

Clamps only matter because of *who consumes the utilization signal*:

- **schedutil governor**: aggregate per-CPU utilization (including clamped values) maps to a frequency request. A boosted task drags the cluster's request up; a capped task stops dragging it up.
- **Energy-Aware Scheduling (EAS)** on asymmetric topologies: task *capacity* demand (clamped utilization) is matched against per-core capacity curves to pick the cheapest core that satisfies the demand. Boost above a LITTLE core's capacity and the task gravitates to big cores; cap below it and the task becomes LITTLE-eligible.
- **Idle injection / thermal pressure** interact too: caps express "this task must not force high clocks", which complements thermal throttling instead of fighting it.

The design intent (visible in the kernel docs uclampset's man page points to) is that *userspace knows its latency vs power contract better than a generic heuristic* — clamps are how an app or a service manager states that contract.

### Task scope vs cgroup scope vs system scope

```
scope          knob                          typical owner
-------------  ----------------------------  ------------------------
per-thread     sched_setattr (uclampset)     hand-tuned services, tests
cgroup v2      cpu.uclamp.min / cpu.uclamp.max   systemd slices, runtimes
system         sched_util_clamp_min/max sysctls   platform tuning
```

Effective clamping is computed through this stack: a task cannot exceed what its cgroup allows, and no task can exceed the system sysctls. `uclampset` covers the first and last scope; cgroup scope is edited via files or `systemd` directives — but all three describe the same per-task attribute aggregation.

### Interaction with the system-wide sysctls and cgroups

Effective clamping is the task value intersected with the system sysctls and then combined with the task's cgroup hierarchy:

```
effective uclamp_min = min( task uclamp_min,  system sched_util_clamp_min )
effective uclamp_max = max( task uclamp_max,  ... combined with cgroup clamps )
```

(The exact aggregation is hierarchical in the cgroup v2 cpu controller — `cpu.uclamp.min`/`max` files — and is documented in the kernel's `sched-util-clamp` documents.) The practical rule: to *guarantee* a boost you may need to raise the system-wide `util_clamp_min` sysctl first, since the sysctl caps every task's clamp.

### big.LITTLE placement effect

On asymmetric cores, clamps participate in placement: a task boosted above a LITTLE core's capacity tends to be placed on a big core; a task capped at/below LITTLE capacity is free to stay there even at 100% actual usage. This is exactly the scenario the man page calls out.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-m <value>` | Set `util_min` (0..1024, or `-1` to reset to system default). |
| `-M <value>` | Set `util_max` (0..1024, or `-1` to reset). |
| `-p, --pid <pid>` | Operate on an existing PID. |
| `-a, --all-tasks` | Apply to all threads of the PID, not just the main task. |
| `-s, --system` | Operate on the system-wide clamp (sysctls) instead of a task. |
| `-R, --reset-on-fork` | Set the reset-on-fork flag: children of this task start unclamped. |
| `-v, --verbose` | Print status information while operating. |

## Usage Patterns

```bash
# Inspect the clamp of a running multimedia process
uclampset -p $(pidof video_worker)
```

```bash
# Boost a UI/latency task so DVFS never treats it as idle
uclampset -m 512 -p $(pidof ui_render)
```

```bash
# Cap a background indexer so it stops driving up core frequencies
uclampset -aM 128 -p $(pidof tracker)
```

```bash
# Launch a test workload pre-capped, then compare benchmark numbers
uclampset -M 384 ./perf_test
```

```bash
# Boost the task but let its forked children run unclamped
uclampset -Rm 768 ./pipeline
```

```bash
# Read the system-wide clamps
uclampset -s
```

```bash
# Raise the system-wide floor so per-task boosts are actually honored
uclampset -s -m 256
```

```bash
# Reset a task's attributes back to the system defaults
uclampset -m -1 -M -1 -p 1234
```

```bash
# Apply to every thread of a multithreaded server
uclampset -aM 512 -p $(pidof mysqld)
```

```bash
# Combine with taskset in a tuning script: pin + boost
taskset -c 4-5 uclampset -m 384 ./voice_agent
```

```bash
# Boost an audio thread and verify the clamp took (verbose)
uclampset -v -m 1024 -p $(pidof jackd)
```

```bash
# Cap a nightly backup so it never pushes the cluster to max frequency
uclampset -M 256 -a -p $(pidof backup_agent)
```

```bash
# Cap the launch phase but let daemons it forks run free
uclampset -RM 512 ./supervisor
```

```bash
# Compare benchmark medians with and without a boost floor
hyperfine 'uclampset -m 700 ./workload' './workload'
```

```bash
# Read system-wide defaults in a tuning playbook
uclampset -s
```

## Nuances and Gotchas

- **Kernel support is not universal.** Below kernel 5.3 or without `CONFIG_UCLAMP_TASK`, `uclampset` fails with `EINVAL`/`ENOSYS` from `sched_setattr`. Many older datacenter kernels ship without it — check `zcat /proc/config.gz | grep UCLAMP` or just try a read.
- **Boosts can be silently ignored.** A task-level `uclamp_min` above the system `sched_util_clamp_min` sysctl is capped by it; if you "boost to 512" and see no frequency change, verify the system value first.
- **Clamp ≠ quota.** `uclamp_max` does not limit CPU *time* — a capped task still gets its full scheduler entitlement; it merely stops requesting high frequency/placement. Conflating the two is the most common conceptual error.
- **Threads again.** Like `taskset`, setting on the PID touches one thread unless `-a` is given.
- **`-1` is the reset sentinel**, not a valid clamp; the range is `[0,1024]`. Reset means "back to system default" (min 0, max 1024), not "unset".
- **System scope is privileged** and affects *every* task; lowering the system `util_clamp_max` globally is a power trick with subtle latency side effects — test, don't deploy blind.
- **Not a portable tool.** Linux-only, no POSIX analogue, no BusyBox equivalent; scripts must tolerate its absence on other systems.
- **Boosts cost power even when the task is idle.** `uclamp_min` inflates the reported utilization whenever the task runs, so a bursty task boosted to 1024 pins the cluster at max frequency during every burst. Scope boosts to latency-critical threads (`-a` to exclude the rest), not whole daemons.
- **Aggregation surprises.** A task's effective clamp also depends on ancestors in the cgroup hierarchy — a cap set on a parent slice constrains every boost you try inside it. When a task-level setting "does nothing", walk up the cgroup tree.
- **The signal is advisory.** Governors may clamp the clamp (thermal limits, other policies). Treat uclamp as a *hint with priority*, and verify effects with frequency counters (`cpupower frequency-info`, perf) rather than assuming.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Read or set succeeded (`sched_getattr(2)`/`sched_setattr(2)` OK, sysctl writes OK). |
| nonzero | Usage error, unsupported kernel (`ENOSYS`), permission denied, or PID vanished (`ESRCH`). In command mode the child's exit status is propagated. |

## Related Commands

- [`taskset`](./taskset.md) — hard CPU-set restriction; the placement counterpart of this frequency/placement bias.
- [`chrt`](./chrt.md) — scheduling policy and real-time priority via the same `sched_setattr` family.
- [`choom`](./choom.md) — adjusts another per-task kernel knob (OOM score); same "act on a live PID" shape.
- [`ionice`](./ionice.md) — per-task biasing for the I/O layer instead of the CPU layer.
- [`../../admin/process-management.md`](../../admin/process-management.md) — process attributes and control context.
- [`./overview.md`](./overview.md) — util-linux collection hub.

## Interview Questions

### Q: What problem does utilization clamping solve that nice/chrt/taskset cannot?

None of those tell the frequency governor anything. A nice-0 task or a pinned task with tiny bursts still reports low utilization, so the CPU idles into low clocks and every burst pays ramp-up latency. `uclamp_min` makes the task's *reported* utilization floor explicit so DVFS keeps clocks high; `uclamp_max` does the inverse for power. It is a performance/power contract, orthogonal to CPU time entitlement.

### Q: You set `uclampset -m 800 -p PID` and observe no frequency increase. Walk through the diagnosis.

Check the system-wide `sched_util_clamp_min` sysctl first — effective per-task clamp min is capped by it, so a system default of 0..low silently clips the boost. Then confirm kernel support (`CONFIG_UCLAMP_TASK`), confirm the governor is schedutil rather than a static one that ignores utilization, and confirm you hit the right thread (`-a`). Finally remember placement on heterogeneous cores also consumes the clamp; a boost below the LITTLE cores' capacity changes nothing.

### Q: Explain the difference between `uclamp_max` and a cgroup CPU quota in one paragraph.

A quota (`cpu.max`) bounds actual CPU *time*: exceed it and the task is throttled. `uclamp_max` bounds the *performance request*: the task may still consume as much time as the scheduler grants, but the cluster won't raise frequency or choose big cores because of it. One controls "how much CPU you may eat", the other "how fast the CPU runs / where you belong while eating".

### Q: What does `-R/--reset-on-fork` do and why is it useful?

It sets the kernel flag so that any task forked from the clamped one drops back to default clamps. Useful when a supervisor bootstrap phase needs a boost (or a cap) but the workers it spawns should run with normal behavior — prevents an accidental boost/cap inheritance leaking into the whole process tree.

### Q: How do `uclampset` and cgroup v2 `cpu.uclamp.*` relate?

They expose the same kernel mechanism at two scopes: `uclampset` is per-task/per-thread (syscall) or system-wide (sysctl), while `cpu.uclamp.min`/`max` are per-cgroup aggregate controls managed by systemd or the orchestrator. Effective clamping is computed hierarchically, so a task's effective clamp reflects both its own value and its group's — an interviewer expects you to know both doors into the same hardware knob.

### Q: Why would a mobile-style workload set `uclamp_min` on a *render* thread but `uclamp_max` on a *prefetch* thread of the same process?

The two threads have opposite performance contracts: the render thread's short bursts must not be mistaken for light load, or every burst pays frequency ramp-up latency (hence a floor). The prefetch thread produces no user-visible latency and should never be the reason the SoC leaves low-power states (hence a ceiling). Clamps let one process express both contracts per-thread — something nice, affinity, or cgroup CPU weight cannot express at the DVFS layer.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/uclampset.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
