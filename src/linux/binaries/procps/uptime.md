# uptime — system up-time and load average in one line

## Overview

`uptime` prints a single line: the current time, how long the system has been running, how many login sessions exist, and the 1/5/15-minute load averages. It ships in the `procps` package at `/usr/bin/uptime` and is deliberately the smallest tool in this collection — three flags, one output format, no filtering, no interactivity. Its value is that the line it prints is the shared opening of [w](./w.md) and the first line of [top](./top.md), so it is the canonical reference for what "load average" means on Linux.

It is often confused with `who` and `users` (which enumerate login records instead of summarizing them) and with `w`, whose header is literally `uptime`'s output. The interview gravity of `uptime` is entirely in the load triple — especially the fact that Linux counts *uninterruptible* tasks into it, a behavior specific to Linux that changes how the numbers must be interpreted.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 4.x) |
| Man section | 1 |
| Path | /usr/bin/uptime |
| First appeared | BSD lineage; modern form from procps/procps-ng |
| Standards | None (load-average semantics are OS-specific) |

## Synopsis

```
uptime [options]
```

Common one-line forms:

```
uptime          # the one-liner
uptime -p       # pretty: "up 7 hours, 42 minutes"
uptime -s       # boot timestamp: "2026-10-09 07:51:11"
```

## How It Works

### Anatomy of the line

Grounded output:

```
15:33:34 up  7:42,  0 users,  load average: 0.00, 0.05, 0.01
```

| Segment | Meaning |
| --- | --- |
| `15:33:34` | Current local time |
| `up 7:42` | Time since boot; beyond 24 h it renders as `up 3 days, 2:05` |
| `0 users` | Number of login sessions recorded in utmp (or systemd's session table) |
| `load average: 0.00, 0.05, 0.01` | Exponentially damped averages over the last 1, 5, and 15 minutes |

The "up" duration comes from `/proc/uptime` (seconds since boot, plus cumulative idle seconds across all cores), and the load triple comes from `/proc/loadavg`. `uptime` computes nothing itself — it formats two kernel-maintained counters, which is why the same numbers appear identically in `w` and `top`.

### What load average actually counts

This is the load-bearing definition:

```
load average = exponentially damped moving average of
               tasks that are runnable (R)
             + tasks in uninterruptible sleep (D)
```

- **Runnable (R)**: using a CPU right now, or waiting for a free one. This is the part every Unix counts.
- **Uninterruptible (D)**: blocked in a syscall that cannot be interrupted — overwhelmingly disk and NFS I/O, occasionally certain locks. **Counting these is Linux-specific.** BSD-derived systems count only runnable tasks, so a Linux box wedged on a dead NFS mount can report load 50 while every CPU idles — impossible on classic Unix semantics.

The samples are taken every 5 seconds and folded into the averages with an exponential decay whose time constant is the window itself: the 1-minute figure moves toward the true load with a ~1-minute time constant (roughly 63% of the way after one constant), the 15-minute figure barely reacts to a two-minute spike. That is the entire reason three numbers exist: 1-minute for "what just happened", 15-minute for "what has actually been true", 5-minute as the tiebreaker.

```
true load:      |                ____________  ← flatlines at 8
                |           ____/
damped 1-min:   |        ____/   ~1 min time constant — chases every move
damped 15-min:  |     ___/      ~15 min — barely notices the transition
                +--------------------------------→ time
```

### Reading the triple

Load is a unitless *average task count*, not a percentage. Interpretation always starts from the core count:

```
$ nproc
4
```

| Observation on a 4-core box | Diagnosis |
| --- | --- |
| `0.5, 0.4, 0.4` | Healthy headroom; CPUs mostly idle |
| `3.9, 4.0, 4.0` | Fully utilized and stable — requests queue with zero waste |
| `9.0, 6.0, 2.0` | Load climbing fast; check 1-min-driven alarms now |
| `12.0, 11.5, 11.8` with `id` high | `D`-state wedging (storage/NFS), not CPU — see `vmstat b` |
| `30.0, 1.0, 0.1` | A recent spike; the 15-min figure has not caught up yet |

- Sustained load ≈ core count → fully utilized, requests queuing at 100% efficiency.
- Sustained load ≫ core count → CPU contention (if `r` is the driver) or I/O wedging (if `D` is).
- Trend beats absolute: compare the triple as `15→5→1` to see whether load is falling or climbing; the 15-minute number is the one to alert on, the 1-minute number the one to debug.

Cross-check which population drives it with [vmstat](./vmstat.md): its `r` column is the instantaneous runnable count, `b` the instantaneous `D`-state count, and load average ≈ their damped history.

### uptime vs who vs users

The three session reporters answer different questions about the same utmp data:

| Command | Question answered | Output |
| --- | --- | --- |
| `uptime` | How busy is the box? | One summary line; sessions as a count |
| `who` | Which sessions exist right now? | One line per session: user, tty, host, time |
| `users` | Who (distinct names) is in? | One line, space-separated names, deduplicated |

`w` is the fourth member: its header is `uptime`'s output verbatim, and its body is `who`'s rows enriched with idle and CPU columns.

### /proc/loadavg, decoded

```
$ cat /proc/loadavg
0.00 0.05 0.01 1/199 8002
```

| Field | Meaning |
| --- | --- |
| `0.00 0.05 0.01` | The same 1/5/15 load triple `uptime` prints |
| `1/199` | Currently runnable / total scheduling entities (threads, not processes) |
| `8002` | PID most recently allocated on this system |

The last two fields are free debugging data: `1/199` shows queue depth right now, and the last PID grows monotonically — a host whose last-PID spins rapidly is fork-storming (containers restarting, cron loops). `uptime`, `w`, and `top` all read this one file.

### Boot time

```
$ cat /proc/uptime
27752.26 54816.67        # seconds since boot, seconds of idle summed over cores

$ uptime -s
2026-10-09 07:51:11      # wall clock minus /proc/uptime[0]

$ uptime -p
up 7 hours, 42 minutes
```

Note the idle figure is summed across cores, so it can exceed the uptime value on multi-core machines. `uptime -s` is a derived timestamp — it assumes the clock has not been stepped since boot — and `uptime -p` exists mostly for humans and shell prompts.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-p`, `--pretty` | Human phrasing: `up 7 hours, 42 minutes` |
| `-s`, `--since` | Boot time as an ISO-style timestamp |
| `-h`, `--help` | Usage text |
| `-V`, `--version` | procps-ng version |

That is the complete option surface — `uptime` has no interval, no filtering, no output control. Anything more elaborate is `w`, `vmstat`, or `top` territory.

## Usage Patterns

```bash
# The one-liner for a shell prompt or login banner
uptime

# How long has this box actually been up? (patch/reboot verification)
uptime -p

# Exact boot timestamp for postmortems
uptime -s

# Compare load against core count in one glance
uptime && nproc

# Watch load trend without retyping (see ./watch.md)
watch -n5 uptime

# Raw source: queue depth and last PID come free
cat /proc/loadavg

# Fork-storm detector: last PID spinning upward across samples
watch -n1 'awk "{print \$NF}" /proc/loadavg'

# Is load CPU-driven or D-state-driven? Compare r and b
vmstat 1 5

# Load in every monitoring one-liner since 1980
uptime | awk -F'load average:' '{print $2}'

# Sanity line at the top of a health-check script
echo "$(hostname): $(uptime)" | tee -a /var/log/health.log

# Strip the load triple into three plain numbers for other tools
tr ',' ' ' < /proc/loadavg | awk '{print $1, $2, $3}'
```

## Nuances and Gotchas

- **The "users" count is sessions, not people.** It counts utmp entries: one human with three terminals shows as 3, a screen/tmux session counts, and on a headless container with no utmp activity it is `0 users` despite running processes. Use `w` to see the sessions individually.
- **Linux includes D-state tasks in load.** The classic misread: load 80, `id` 100%, everyone blames CPU — the real story is an NFS mount or dying disk leaving tasks uninterruptibly blocked. Always pair load with `vmstat`'s `b` before concluding CPU saturation.
- **Load is not CPU%.** A load of 1.0 on a 32-core box is 3% busy; a load of 1.0 on a 1-core box is saturated. Percentages and task counts are different units and quoting one as the other is the classic interview trap.
- **The three numbers disagree by design.** After a reboot the 1-minute value ramps from zero and the 15-minute value lags for many minutes; a freshly rebooted box can show `0.20, 0.05, 0.02` while already busy. Wait a window before trusting the trend.
- **Load average counts scheduling entities (threads).** A multithreaded service with 50 worker threads contributes up to 50 to load when all are runnable — compare against core count, not process count.
- **Containers see the host's load.** `/proc/loadavg` is not namespaced by default, so `uptime` inside a container reports host load — misleading if you expected the container's own contention.
- **`uptime -s` is arithmetic, not recorded.** It subtracts `/proc/uptime` from the current clock, so clock adjustments (NTP steps, VM pauses) can skew the boot timestamp slightly.
- **The `gu`/steal caveat applies upstream.** Steal time never appears in load average — a badly overcommitted VM can show *low* load while `st` in `top`/`vmstat` reveals the hypervisor is eating cycles.

## Exit Status

| Code | When |
| --- | --- |
| 0 | Line printed successfully |
| 1 | Failure opening `/proc/uptime` or the session source (effectively never seen) |

No exit codes are formally documented; `uptime` either prints its line or dies early.

## Related Commands

- [`w`](./w.md) — `uptime`'s line plus the per-session breakdown: who, from where, doing what.
- [`vmstat`](./vmstat.md) — the instantaneous `r` and `b` columns that load average smooths together.
- [`top`](./top.md) — the same load line above a per-process table.
- [`free`](./free.md) — the other half of "is the box healthy": memory, which load ignores.
- [Process management](../../admin/process-management.md) — task states (`R`, `D`) that define what load counts.
- [procps overview](./overview.md) — the rest of the collection.

## Interview Questions

### Q: What does a load average of 1.00 mean, and is it bad?

It means that over the averaging window, an average of one task was either running or waiting on uninterruptible I/O. Whether that is bad depends entirely on the core count — 1.00 on one core is saturation, 1.00 on 32 cores is nearly idle — and on *which* tasks were counted, since Linux folds `D`-state I/O waiters into the figure. Load is an average queue length, not a utilization percentage; `top`'s `%Cpu(s)` or `vmstat`'s `id` are the percentage views.

### Q: Why does Linux include uninterruptible tasks in load average, and why do interviewers care?

Because the load number then reflects "how much work the system owes", including I/O the kernel cannot cancel — a fuller health signal during storage storms. The catch: it makes Linux load incomparable with other Unices and open to misreading. The canonical scenario is a dead NFS mount producing load in the dozens with idle CPUs. Interviewers use it to test whether you know that load ≫ cores with idle CPUs points at I/O, not compute — and that `vmstat`'s `b` column, not load, is the direct count of the blocked population.

### Q: Why three numbers instead of one?

The triple is the same quantity measured with three exponential decay windows — 1, 5, and 15 minutes — sampled every 5 seconds. Short windows react fast but thrash on spikes; long windows are stable but stale. Reading them together gives a trend for free: `0.2, 3.0, 8.0` is a system rapidly recovering; `8.0, 3.0, 0.2` is one rapidly degrading. A single number would force a choice between responsiveness and stability that the triple sidesteps.

### Q: What are the fourth and fifth fields of /proc/loadavg?

`running/total` scheduling entities and the most recently assigned PID. The first is an instantaneous snapshot of queue depth (contrast with the damped averages to the left); the second is a monotonic counter that exposes fork activity — watching it climb fast reveals restart loops or fork bombs long before other metrics move. All of `uptime`, `w`, and `top` read this single file for their load displays.

### Q: How would you find out when the system was last rebooted, and how reliable is it?

`uptime -s` prints the boot timestamp, which procps derives by subtracting `/proc/uptime` (seconds since boot) from the current wall clock. It is reliable to the extent the clock is: NTP step adjustments or long VM pauses introduce error, and hibernation can make "uptime" discontinuous. For forensics, cross-check with `who -b`, the kernel timestamps in `journalctl --list-boots`, or the mtime of `/proc/1` — disagreement between sources is itself a finding.

### Q: Where does the "users" count come from, and when is it wrong?

`uptime` counts entries in the login-session records (utmp, or systemd's equivalent session table). It is wrong in the direction of *undercounting relevance* on headless systems — a container or cron-only box shows `0 users` while real work runs — and in the direction of *overcounting people* on interactive hosts, where one human with several terminals, or a nested `su`, produces multiple entries. Treat it as "how many login sessions exist", and reach for `w` (which shows each session with its tty, source, and activity) when the distinction matters.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/uptime.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
