# chrt — show or change real-time scheduling attributes

## Overview

`chrt` sets or displays a process's scheduling policy and priority: the
interface to Linux real-time scheduling from the shell. It can launch a
command under a chosen policy (`SCHED_FIFO`, `SCHED_RR`, `SCHED_BATCH`,
`SCHED_IDLE`, `SCHED_DEADLINE`, or plain `SCHED_OTHER`), or retune a
running PID via `sched_setscheduler(2)`/`sched_setattr(2)`. It ships in
the `util-linux` package at `/usr/bin/chrt` and is the standard tool for
making one workload run *before* all others.

You reach for it for low-latency audio, packet-forwarding planes, soft-IRQ
sensitive userspace, benchmark isolation (BATCH/IDLE for background
noise), and DEADLINE reservations on modern kernels. It is often confused
with `nice`/`renice` (which tune weight *within* `SCHED_OTHER`, strictly
below any real-time policy), with `taskset` (which chooses *where* a
process may run, not when), and with `ionice` (I/O scheduling class).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/chrt |
| First appeared | util-linux 2.8-era lineage, extended for sched_setattr in 2.26 |
| Standards | POSIX.1-2008 defines SCHED_FIFO/RR semantics; DEADLINE is Linux-specific |

## Synopsis

```
chrt [options] <priority> <command> [<arg>...]
chrt [options] --pid <priority> <pid>
chrt [options] -p <pid>
```

Main one-line forms:

```
chrt -f 50 mytask            # run mytask under SCHED_FIFO, prio 50
chrt -r 20 -p 1234           # switch running pid 1234 to SCHED_RR
chrt -p 1234                 # show the current policy/priority
chrt -d --sched-runtime 2000000 --sched-deadline 10000000 \
     --sched-period 10000000 mytask   # SCHED_DEADLINE reservation
```

## How It Works

### The policy menu

```
$ chrt -m
SCHED_OTHER min/max priority : 0/0
SCHED_FIFO   min/max priority : 1/99
SCHED_RR     min/max priority : 1/99
SCHED_BATCH  min/max priority : 0/0
SCHED_IDLE   min/max priority : 0/0
SCHED_DEADLINE min/max priority: 0/0        # params, not priorities
```

```
policy          meaning                          priority
-----------     ------------------------------   ------------------
SCHED_OTHER     default fair (CFS) scheduling    always 0, weight = nice
SCHED_FIFO      run until block/yield; preempt   1 (low) .. 99 (high)
                everything below, no timeslice
SCHED_RR        FIFO + round-robin timeslice     1..99
SCHED_BATCH     CFS without interactive boost    0 (batch-friendly)
SCHED_IDLE      only when nothing else wants CPU 0 (background jobs)
SCHED_DEADLINE  CPU-time reservation (EDF/CBS)   runtime/period/deadline
```

Any nonzero real-time priority outranks *every* OTHER/BATCH/IDLE task,
whatever its nice value — nice and real-time priority are different
dimensions.

### What a launch actually does

```
$ chrt -f 50 ping -c1 host
#  1. fork? no — chrt calls sched_setscheduler(0, SCHED_FIFO, {50})
#  2. on success: execvp("ping") keeps the policy (attributes survive exec)
#  3. on EPERM:   "chrt: failed to set pid 0's policy: Operation not permitted"
```

Both the policy and priority survive `exec(2)`, which is why one chrt at
launch is enough for a whole daemon. For running processes,
`chrt -p <prio> <pid>` rewrites the attributes in place; `-a` walks all
threads of the process (`/proc/<pid>/task/*`).

### Deadline scheduling in one picture

```
      period (P)  = how often the task becomes runnable
      runtime (T) = CPU time the task gets per period   (T <= D <= P)
      deadline(D) = when within the period it must finish

      |<-------------------- period P -------------------->|
      |<--- runtime T --->|        ...free...              |
      |<---------------- deadline D -------------------->|
      kernel enforces via Constant Bandwidth Server (CBS):
      overrun -> throttled until next period, cannot starve others
```

DEADLINE uses `sched_setattr(2)` with nanosecond parameters, which is
exactly why chrt grew the `-T/-P/-D` options; classic
`sched_setscheduler` has no way to express it.

### The RT throttle: why the box survives a bad FIFO loop

```
$ cat /proc/sys/kernel/sched_rt_period_us /proc/sys/kernel/sched_rt_runtime_us
1000000
950000
# every 1 s period, real-time tasks may consume at most 0.95 s;
# the remaining 50 ms belongs to non-RT tasks — that is why a runaway
# SCHED_FIFO busy-loop makes the system sluggish but not dead.
# (echo -1 > sched_rt_runtime_us disables the guard: do not, on prod.)
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-f, --fifo` | Policy SCHED_FIFO (priority 1-99 required) |
| `-r, --rr` | Policy SCHED_RR (priority 1-99); the default policy |
| `-o, --other` | Policy SCHED_OTHER (priority must be 0) |
| `-b, --batch` | Policy SCHED_BATCH (priority 0) |
| `-i, --idle` | Policy SCHED_IDLE (priority 0) |
| `-d, --deadline` | Policy SCHED_DEADLINE (needs -T/-P/-D, not a priority) |
| `-T, --sched-runtime <ns>` | Deadline: CPU nanoseconds per period |
| `-P, --sched-period <ns>` | Deadline: period in nanoseconds |
| `-D, --sched-deadline <ns>` | Deadline: relative deadline in nanoseconds |
| `-R, --reset-on-fork` | Children reset to SCHED_OTHER (stops RT inheritance) |
| `-a, --all-tasks` | Apply to all threads of the given PID |
| `-v, --verbose` | Show status (policy string) of the operation |
| `-p, --pid <pid>` | Operate on an existing process instead of launching |

## Usage Patterns

```bash
# What is this process scheduled as?
chrt -p $(pgrep -x mysqld)
```

```bash
# Launch an audio thread FIFO 80 (the JACK recommendation)
chrt -f 80 jackd -d alsa
```

```bash
# Demote a noisy background job to IDLE — runs only when the box is idle
chrt -i 0 ./reindex.sh
```

```bash
# Benchmarks: BATCH keeps them polite without changing nice
chrt -b 0 python bench.py
```

```bash
# Switch a running process to round-robin 20
sudo chrt -r -p 20 1234
```

```bash
# Apply to every thread of a multithreaded server
sudo chrt -a -f 40 -p 1234
```

```bash
# Deadline reservation: 2 ms runtime every 10 ms period
sudo chrt -d --sched-runtime 2000000 --sched-deadline 10000000 \
           --sched-period 10000000 ./control-loop
```

```bash
# Stop RT policies leaking to children of a privileged launcher
sudo chrt -f 50 -R ./rt-service
```

```bash
# Enumerate the priority ranges before choosing one
chrt -m
```

```bash
# Non-RT priority sanity: OTHER always reports 0
chrt -p 1        # pid 1's current scheduling policy: SCHED_OTHER, priority 0
```

```bash
# Round-trip: policy survives exec, so check the final process
chrt -f 30 sleep 300 & chrt -p $!
```

## Nuances and Gotchas

- **EPERM is the default experience.** Real-time policies require
  `CAP_SYS_NICE`. Unprivileged attempts fail with `Operation not
  permitted` — as seen from `chrt: failed to set pid 0's policy:
  Operation not permitted`. The sanctioned alternative is the
  `RLIMIT_RTPRIO` rlimit (limits.conf / systemd `LimitRTPRIO=`), which
  lets non-root users take RT policies up to the limit.
- **Priority 0 is invalid for FIFO/RR.** Their range is 1-99; `chrt -f 0`
  is a usage error. Conversely, OTHER/BATCH/IDLE must be 0 — their weight
  is tuned by `nice`, a separate call.
- **FIFO loops are near-deadlocks.** A compute-bound SCHED_FIFO task
  starves everything at lower priority on its CPU. The RT throttle
  (95% default) is the only thing between you and a reboot; never disable
  `sched_rt_runtime_us` casually.
- **RR timeslice is tunable.** `/proc/sys/kernel/sched_rr_timeslice_ms`
  (default 100 on many kernels) — interviewers like the question "how
  long is an RR quantum".
- **DEADLINE ignores nice, needs all three parameters, and enforces
  runtime <= deadline <= period.** It also bypasses the classic RT
  priorities entirely; mixing DEADLINE and FIFO tasks requires careful
  capacity planning.
- **Policy survives fork and exec.** Daemons inherit RT from their parent
  unless `-R` (reset-on-fork) is used; systemd services use the same
  flag semantics via `CPUSchedulingPolicy=`.
- **Container caveat.** In cgroup v2, controllers may restrict RT
  bandwidth (`cpu.rt_runtime_us` legacy; cpu controller throttling); chrt
  may succeed while the scheduler still throttles the task.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Policy set/displayed; launched command exited 0 if the command form was used |
| 1 | Usage error, or the `sched_setscheduler`/`sched_setattr` call failed (`EPERM`, `EINVAL`) |
| (command form) | The exit status of the launched command otherwise propagates |

## Related Commands

- [`choom`](./choom.md) — the OOM-score knob; chrt's sibling for "which process, when" vs "who dies first"
- [`chcpu`](./chcpu.md) — CPU topology side of the same tuning story
- [`../../admin/process-management.md`](../../admin/process-management.md) — where scheduling fits among process-control tools
- [Linux internals](../../internals.md) — the CFS/RT scheduler structures these syscalls poke
- [util-linux overview](./overview.md) — the rest of the process toolset

## Interview Questions

### Q: Explain the difference between SCHED_FIFO and SCHED_RR.

Both are fixed-priority real-time policies (1-99) that preempt all
normal tasks. FIFO runs a task until it blocks, yields, or is preempted
by something higher — there is no quantum. RR is FIFO plus a round-robin
timeslice: equal-priority RR tasks rotate through the CPU. A runaway
FIFO task starves its peers permanently; an RR task only holds the CPU
for one timeslice at a time.

### Q: What is the relationship between nice and chrt priorities?

Orthogonal dimensions. Nice tunes the weight of a task inside
SCHED_OTHER (and affects BATCH); it never competes with real-time. Any
SCHED_FIFO/RR task with priority 1 outranks a nice -20 OTHER task on the
same CPU. Conversely, switching a task from FIFO 50 back to OTHER (with
`chrt -o 0`) demotes it beneath every OTHER weight game — the interview
point is that "high priority" means nothing across the RT boundary.

### Q: An unprivileged script runs `chrt -f 50 cmd` and gets EPERM. Give three ways to make it work.

Grant `CAP_SYS_NICE` (run as root, or file capabilities on the launcher);
raise the `RLIMIT_RTPRIO` rlimit for the user (limits.conf or systemd
`LimitRTPRIO=`) so chrt can take RT policies up to the limit without
root; or pre-approve the specific binary via a service unit with
`CPUSchedulingPolicy=fifo` so systemd (privileged) sets it. The rlimit
path is the canonical answer for unprivileged RT.

### Q: How does the kernel prevent a buggy SCHED_FIFO busy-loop from hanging the system?

Real-time bandwidth throttling: within `sched_rt_period_us` (1 s), RT
tasks may consume at most `sched_rt_runtime_us` (950 ms by default); the
rest is reserved for normal tasks, keeping at least one CPU timeslice
available for rescue. DEADLINE tasks have their own CBS enforcement,
which throttles an overrunning task until its next period.

### Q: When would you choose SCHED_DEADLINE over FIFO, and what must you specify?

When a task needs a guaranteed share of CPU per period rather than
absolute preemption: control loops, media pipelines. You must specify
runtime, deadline, and period (in nanoseconds, `-T/-P/-D`) with runtime
<= deadline <= period; the kernel then guarantees the reservation via
EDF plus CBS, and the task cannot starve others the way FIFO can. It
requires privileges and careful capacity math against the CPUs available.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/chrt.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
