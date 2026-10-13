# ionice — get or set process I/O scheduling class and priority

## Overview

`ionice` shows or changes the I/O scheduling class and priority of a process — the block-layer counterpart of `nice`. Three classes exist: **idle** (only gets disk time when nothing else wants it), **best-effort** (the normal class, with priorities 0-7), and **realtime** (served first — root-only and rarely wise). Wrapping a command (`ionice -c3 updatedb`) or retargeting a running process (`ionice -p 1234`) both work.

It ships in the `util-linux` package at `/usr/bin/ionice`. Reach for it to stop bulk jobs (backups, indexing, checksum sweeps) from wrecking interactive latency, and to give latency-critical jobs an edge. It is often confused with `nice` (CPU, not I/O — they compose), with `renice` (its CPU sibling for running processes), and — the big one — with the expectation that it always works: I/O priorities are only honored by schedulers that implement them (CFQ historically, BFQ today).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/ionice |
| First appeared | util-linux tool of the CFQ era (Linux 2.6.13+ ioprio support, mid-2000s) |
| Standards | None (Linux-specific ioprio syscalls) |

## Synopsis

```
ionice [options] -p <pid>...
ionice [options] -P <pgid>...
ionice [options] -u <uid>...
ionice [options] <command>
```

Common one-line forms:

```
ionice -c3 nice -n19 rsync -a src/ dst/    # background-grade backup
ionice -p 1234                             # show a process's class/priority
ionice -c2 -n7 -p 1234                     # drop a running job to lowest prio
ionice -c1 -n0 -p $$                       # (root) top real-time priority
```

## How It Works

### The class/priority model

The kernel tags each process with an I/O priority: a class plus a priority number within the class (0 = highest, 7 = lowest). The scheduler consults the tag when deciding which queued I/O to dispatch first.

```
class 1: REALTIME     priority 0..7   — always served first; can starve the
                                        system; needs CAP_SYS_ADMIN
class 2: BEST-EFFORT  priority 0..7   — the ordinary class; arbitration is
                                        between same-class processes
class 3: IDLE         (no priority)   — served only when no other class
                                        wants the disk right now
class 0: NONE         — unset; behaves like best-effort with a priority
                        derived from the CPU nice value: (nice + 20) / 5
```

A fresh process reports `none` — locally, `ionice -p $$` prints `none: prio 4` for an un-niced shell, exactly the formula's output for nice 0. Setting an explicit class overrides the derivation:

```bash
$ ionice -p $$
none: prio 4
$ ionice -c2 -n1 -p $$   # set best-effort priority 1
$ ionice -p $$
best-effort: prio 1
```

Children inherit the I/O priority across `fork()`, so wrapping a command covers its whole process tree — the standard way to demote a backup.

### Who actually honors it

The tag is advisory to the *scheduler*. It changes behavior only when the active block scheduler implements I/O priorities: **BFQ** (and the removed-in-5.0 **CFQ**) do; `mq-deadline`, `none`, and `kyber` do not. On a modern NVMe laptop running the default `none` scheduler, `ionice` is a placebo — check:

```bash
$ cat /sys/block/nvme0n1/queue/scheduler
none [mq-deadline] kyber bfq none
```

On SATA HDDs/SSDs where `bfq` is loadable, `echo bfq > /sys/block/sda/queue/scheduler` makes ionice meaningful. This "it didn't do anything" experience is the interview question hiding in plain sight.

### The idle class contract

`-c3` processes receive I/O service only when no non-idle request is pending — batch jobs effectively yield to everything. Under sustained competing load they can wait arbitrarily long; with no competition they run at full speed. That asymmetry (fair when idle, starved when busy) is precisely the desired semantics for `updatedb`, `fstrim`, or media-thumbnail sweeps.

### Realtime, and why it stays root-only

Class 1 processes preempt everything; a buggy or greedy realtime job can starve the entire system's I/O — including the filesystem journal. Hence `CAP_SYS_ADMIN` is required to *set* realtime, and most deployments never should. The legitimate niche: low-latency capture/playback appliances where one process's I/O must never wait.

### The syscall surface

`ionice` is a thin wrapper over `ioprio_get(2)` / `ioprio_set(2)`. An I/O priority is a single number: `(class << 13) | priority` — `IOPRIO_PRIO_VALUE` — and the syscall's "who" selects scope: `IOPRIO_WHO_PROCESS` (`-p`), `IOPRIO_WHO_PGRP` (`-P`), `IOPRIO_WHO_USER` (`-u`). The kernel stores the value in the task struct next to the CPU nice; children inherit it at `fork()`, and `exec` does not touch it. Permission rules mirror renice's: unprivileged callers may retarget only processes whose real UID matches their own, and `IOPRIO_CLASS_RT` requires `CAP_SYS_ADMIN`. There is no `/proc/<pid>/ioprio` — the syscall pair is the entire interface, which is why `ionice -p PID` is the diagnostic tool, not `cat`.

### How BFQ actually consumes the tag

Under BFQ the (class, priority) pair is translated into an internal *weight* that shares the device's service budget: best-effort priority 4 — the default — is the neutral weight, lower numbers get proportionally more service per dispatch round, and idle-class queues are served only when nothing else is pending. The scheduler is also where cgroup policy enters: with BFQ active, cgroup v2 exposes `io.bfq.weight`, so host-level weights (cgroups) and per-process courtesy (ionice) act on the same dispatch decisions. On schedulers without ioprio support, none of this machinery runs — the tag is stored and ignored.

### What ionice does not reach

ionice tags I/O the process itself issues: reads, `O_DIRECT` writes, `fsync`/`fdatasync`. The later flush of buffered dirty pages is issued by kernel writeback workers, whose shaping lives in cgroup I/O controls (`io.max`, `io.latency`), not in the writing process's ioprio. A demoted process can still cause bursts of un-niced write I/O when its dirty pages flush — the standard complement is to run the job inside a cgroup with `io.max` set, with ionice handling its synchronous I/O.

### Reading the display, and the self-query form

Bare `ionice` (no `-p`, no command) prints the calling process's own setting — handy in scripts as a sanity probe:

```bash
$ ionice
none: prio 4
$ ionice -c2 -n1          # a class without -p or a command is a usage error
ionice: bad usage
```

The output format is `class: prio N` — `none`, `realtime`, `best-effort`, or `idle`; idle prints no priority because the class has none. The setting is process-wide: it applies to I/O on every block device the process touches, not per-device.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-c, --class <class>` | Class by name or number: `0 none, 1 realtime, 2 best-effort, 3 idle` |
| `-n, --classdata <num>` | Priority 0-7 within realtime or best-effort (0 highest) |
| `-p, --pid <pid>...` | Operate on running PIDs (show, or set with `-c/-n`) |
| `-P, --pgid <pgid>...` | Operate on process groups |
| `-u, --uid <uid>...` | Operate on all processes of a user |
| `-t, --ignore` | Ignore failures to set the priority; run the command anyway |

Without `-p/-P/-u` and without `-c`, ionice prints the current priority of the given PIDs; with a command, it forks it with the requested settings. `-n` without a meaningful class is rejected (idle/none take no priority data).

## Usage Patterns

```bash
# Demote a bulk backup below all interactive I/O
ionice -c3 nice -n19 tar -cf - /data | ssh backup "cat > /vol/data.tar"

# Ionice an already-running runaway indexer
ionice -c3 -p $(pgrep -f updatedb)

# Lowest best-effort priority: still gets service when nothing else competes
ionice -c2 -n7 -p 4242

# Show the I/O scheduling state of a process (defaults derived from nice)
ionice -p $$
# none: prio 4

# Raise the priority of a latency-sensitive capture process (root)
sudo ionice -c1 -n0 -p $(pgrep capture)

# Batch demote everything owned by the backup user
sudo ionice -c3 -u backup

# -t: proceed even if the kernel/scheduler refuses (portable scripts)
ionice -t -c2 -n5 make -j8

# Combine with CPU controls for a true background job
ionice -c3 nice -n19 taskset -c 3 ./rebuild_index.sh

# Verify the scheduler actually implements ioprio (else ionice is a no-op)
cat /sys/block/sda/queue/scheduler

# Confirm a change landed on the live process (query right after setting)
ionice -c3 -p "$(pgrep -x updatedb | head -1)" && ionice -p "$(pgrep -x updatedb | head -1)"
# idle

# Tiered batch jobs: cache rebuild at BE7, stats at BE5 — rebuild yields first
ionice -c2 -n7 rebuild_cache.sh & ionice -c2 -n5 compute_stats.sh &

# A/B test under load: run both while a competing reader hammers the disk
ionice -c3 dd if=/dev/vda of=/dev/null bs=1M count=2000 status=none
dd if=/dev/vda of=/dev/null bs=1M count=2000 status=none

# Declarative equivalent in a systemd unit (same classes, service-scoped)
# [Service]
# IOSchedulingClass=idle
# IOSchedulingClass=best-effort
# IOSchedulingPriority=7

# Cron-shaped guard: demote-and-verify, log if the kernel refused
ionice -c3 -p "$$" && exec /usr/local/bin/bigbatch.sh

# Demote every process of a cgroup's owner scope, one syscall per PID
for pid in $(pgrep -u backup); do ionice -c3 -p "$pid"; done

# fstrim and friends: the canonical idle-class residents
ionice -c3 fstrim -av
```

## Nuances and Gotchas

- **Noop without BFQ/CFQ.** The default scheduler on NVMe (`none`) and common server choices (`mq-deadline`, `kyber`) ignore I/O priorities entirely. Always verify the scheduler before promising ionice behavior — this is the difference between a fix and a placebo.
- **Idle can starve.** `-c3` processes may wait indefinitely under load; long-running idle jobs that also hold locks (db migrations, package managers) can block everything else in *application* space even while the disk is idle. Demote CPU-heavy, lock-free jobs.
- **Realtime is system-level dangerous.** Class 1 can starve journal and metadata I/O, freezing the machine. Root-only for a reason; production use is nearly always a mistake.
- **Class 0 is not a setting, it's a state.** You can *report* none, but setting `-c0` means "remove the explicit setting" (fall back to nice-derived best-effort) — don't script `-c0` expecting an actual class.
- **Inheritance covers children, not already-running daemons.** Wrap at launch, or retarget each PID; `-u`/`-P` help for process groups and users, but a supervisor respawning children resets nothing (children inherit the *parent's* setting, so fix the parent).
- **I/O priority ≠ throughput guarantee.** It orders dispatch decisions; a single sequential reader at best-effort 7 still saturates a spinning disk when nothing competes. Combine with cgroup I/O limits (`io.max`) for bandwidth caps — different tool, different layer.
- **Interaction with cgroups v2.** When `io.cost`/`io.bfq`-style control or cgroup weights are in play, per-process ioprio and per-cgroup weights both influence service; debugging latency with only ionice in view misses half the picture.
- **`-t` trades correctness for availability.** With `-t`, a refused priority change is ignored and the command runs anyway — right for portable scripts, wrong when the demotion *was* the point (a failed idle-set then runs at full speed).
- **The one-`cat` preflight.** `cat /sys/block/<dev>/queue/scheduler` before designing anything around ionice; `none`, `mq-deadline`, and `kyber` ignore ioprio entirely. On NVMe-only hosts, plan around cgroup `io.*` controls — do not ship ionice and assume.
- **Readahead and journal I/O are not yours to demote.** The block layer issues readahead and the filesystem issues journal writes on its own behalf; a demoted process still competes with those at the device. Latency SLOs are best protected with `io.latency`/`io.cost`, with ionice as the per-job courtesy layer.
- **`-t` can mask a useless configuration.** `ionice -t -c3 cmd` on a `none`-scheduler host runs cmd at full speed and exits 0 — the protection silently absent. Log the scheduler name alongside the job-start line in any script that relies on ionice.
- **Demoting an already-running daemon misses its supervisor.** `ionice -c3 -p PID` fixes one process; a supervisor that respawns workers passes its *own* (undemoted) class down. Fix the parent, or use `-u`/`-P` scopes, then confirm with `ionice -p` on a fresh child.
- **ioprio is process-wide, not per-device.** One task struct, one tag — a process writing to an NVMe array and a USB stick carries the same class on both. Split workloads into separate processes when they need different per-device courtesy.
- **Container root may still lack the capability.** `IOPRIO_CLASS_RT` needs `CAP_SYS_ADMIN` in the caller's user namespace; a container's root without it gets EPERM. `-t` turns that into "run anyway" — acceptable when the demotion is cosmetic, dangerous when it was the whole point.
- **The tag can outlive your intent.** A daemon ionice'd to idle at launch keeps that class across config reloads that only restart workers. Record the intended class next to the pidfile so monitoring can diff "what it is" against "what it should be".

## Exit Status

- `0` — success: the query printed, or the priority was set, or the command completed.
- Nonzero — failure to get/set the priority (permission, invalid class data, unsupported operation); with `-t`, failures to *set* are ignored and the exit status is that of the wrapped command.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`taskset`](./taskset.md) — CPU affinity sibling with the same wrap-or-retarget interface.
- [`renice`](../bsdutils/renice.md) — CPU-priority sibling for running processes.
- [`fstrim`](./fstrim.md) — classic companion: trim jobs are run ionice'd to stay invisible.
- [`process-management`](../../admin/process-management.md) — scheduling, priorities, and signals context.
- [`internals`](../../internals.md) — block layer scheduling where ioprio tags are consumed.

## Interview Questions

### Q: What are the I/O scheduling classes and how does priority 0-7 fit in?

Three usable classes: realtime (1) and best-effort (2) carry a priority 0-7 (0 best), idle (3) has none and only runs when nothing else wants the disk. A process with no explicit setting (class none) behaves as best-effort with priority derived from its CPU nice value via (nice + 20)/5 — nice 0 maps to priority 4, which is what `ionice -p $$` on an un-niced shell reports.

### Q: You ionice'd a job to idle but disk latency for users didn't improve. What do you check first?

Whether the block scheduler implements I/O priorities at all: `cat /sys/block/<dev>/queue/scheduler`. On `none` (typical NVMe default), `mq-deadline`, or `kyber`, ioprio tags are ignored — switch to `bfq` to make them meaningful, or use cgroup-based I/O control instead. ionice is an instruction to the scheduler, not to the device.

### Q: How do you prevent a nightly backup from degrading interactive performance — precisely, and why each piece?

Wrap it: `ionice -c3 nice -n19 rsync ...`. The idle I/O class yields the disk to all interactive traffic; nice 19 yields CPU; children inherit both. If the backup must finish by morning regardless, use best-effort priority 7 (`-c2 -n7`) instead of idle — still lowest, but not starvable under sustained load.

### Q: What happens when you ionice a process to realtime, and why is it root-only?

Class-1 requests preempt all other I/O on the device; a runaway realtime process can starve journal writes and metadata I/O to the point of system unresponsiveness. Because the failure mode is system-wide, setting the class requires CAP_SYS_ADMIN. Legitimate uses are narrow: dedicated appliances where one process must never wait for I/O.

### Q: Explain what `ionice -p $$` printing `none: prio 4` means.

The shell has no explicit I/O priority (class none/0). The displayed priority 4 is the kernel's derived best-effort priority from the CPU nice level: (0 + 20) / 5 = 4. It tells you effective scheduling today — and predicts that `nice -n10` on the same shell would also demote its I/O to priority 6 without any ionice call.

### Q: How do ionice and cgroup I/O control (io.max / io.latency) differ?

ionice is a per-process ordering hint consumed by the scheduler (BFQ/CFQ): it influences *who goes first* but not how much bandwidth anyone gets. cgroup I/O control enforces *limits* (throttle bytes/IOPS per device, latency targets) regardless of scheduler choice. High-level policy uses cgroups; process-level courtesy uses ionice — production setups often need both, and confusing the two is a design smell.

### Q: Which syscalls implement ionice, and what exactly is stored?

`ioprio_get(2)` and `ioprio_set(2)`, carrying a 16-bit value `(class << 13) | priority` scoped by `IOPRIO_WHO_PROCESS/PGRP/USER`. The kernel keeps it in the task struct; it is inherited across fork and untouched by exec. `ionice -p PID` is a plain ioprio_get; the launcher mode is ioprio_set followed by exec. Worth knowing because there is no `/proc/<pid>/ioprio` file — the syscall pair is the only interface, and `ionice` itself is the standard way to read it.

### Q: You added `ionice -c3` to a backup script; the DBA says checkpoints still stall. Why, and what actually fixes it?

The backup's own read stream is now idle-class, but the DB's stall is usually write-side: journal commits and checkpoint flushes competing with the backup's dirty-page writeback — I/O issued by kernel writeback workers, which ionice does not demote. Fixes: run the backup inside a cgroup with `io.max` on its slice, shrink `vm.dirty_bytes` so bursts stay small, and keep the idle class for the backup's synchronous I/O. ionice fixed what it could see; the write path needed cgroup policy.

### Q: Compare ionice with nice end to end: same knob, different layer — where does the analogy break?

Both tag tasks with a class plus a level, both are inherited across fork, both restrict unprivileged users to demotions. It breaks three ways: (1) scope — nice is honored by the CPU scheduler unconditionally, while ioprio only exists under BFQ/CFQ, so ionice can be a complete no-op; (2) coupling — class `none` derives effective best-effort priority from the CPU nice ((nice+20)/5), so `renice` silently moves I/O priority too; (3) enforcement — cgroup `cpu.max` and `io.max` bound *amounts*, which neither nice nor ionice can promise when a job must finish by a deadline.

### Q: What does running `ionice` with no arguments show, and why is that useful?

It queries the *calling* process: bare `ionice` prints e.g. `none: prio 4` — the self-query form with no syscall flags needed in a script. It is the cheap sanity check in wrappers: run it before and after setting, log the result, and you have evidence the demotion actually landed on the process (or that `-t` swallowed a refusal). A class given without `-p` or a command is a usage error, which surprises people who try `ionice -c2 -n1` expecting a self-set.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/ionice.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
