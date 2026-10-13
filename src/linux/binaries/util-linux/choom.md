# choom — display or change the OOM-killer score of a process

## Overview

`choom` reads and adjusts a process's OOM (out-of-memory) score
adjustment: the one knob the Linux kernel's OOM killer consults besides
its own badness calculation. It wraps two `/proc` files —
`/proc/<pid>/oom_score` (read-only, kernel-computed) and
`/proc/<pid>/oom_score_adj` (writable, sticky) — into one command that can
either report, adjust an existing PID, or launch a command with the
adjustment pre-set. It ships in the `util-linux` package at `/usr/bin/choom`.

You reach for it when a workload must never be OOM-killed (databases
before a maintenance window, a watchdog), when a job is expendable and
should die first under memory pressure (batch crons, caches), or when an
init script needs a child spawned with a given score without shell races.
It is often confused with `nice`/`renice` (CPU scheduling weight, not
memory pressure), with `ulimit -v` (hard address-space caps), and with
cgroup memory limits (which kill by cgroup, not by score).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/choom |
| First appeared | util-linux 2.26 (2014), replacing ad-hoc /proc echo tricks |
| Standards | Linux /proc oom_score / oom_score_adj interface |

## Synopsis

```
choom [options] -p pid
choom [options] -n number -p pid
choom [options] -n number [--] command [args...]
```

Main one-line forms:

```
choom -p 1234                  # show current score and adjust value
choom -n 500 -p 1234           # make pid 1234 more OOM-killable
choom -n -800 -- mysqld        # start mysqld with a "don't kill me" score
```

The adjust value range is **-1000 to +1000**.

## How It Works

### The kernel's OOM math

When the kernel must kill something, it picks the task with the highest
`oom_score`, computed from *badness* — roughly memory footprint (RSS,
swap, page tables) — scaled by the adjustment:

```
oom_score ≈ badness * (oom_score_adj + 1000) / 1000

   oom_score_adj = -1000  ->  score 0        ->  never selected
   oom_score_adj =    0   ->  raw badness    ->  neutral (default)
   oom_score_adj = +1000  ->  double badness ->  selected first
```

`oom_score` is recomputed constantly and means nothing in isolation;
`oom_score_adj` is the writable, inherited-on-fork policy input. That
split is the whole design: the kernel keeps the measurement, operators
keep the opinion.

### The three forms

```
$ choom -p 1
pid 1's current OOM score: 666
pid 1's current OOM score adjust value: 0

$ choom -n 500 -p 1234          # write 500 to /proc/1234/oom_score_adj

$ choom -n -800 -- mydaemon     # fork, set adj on the child, exec mydaemon
#   equivalent to the classic (racy) shell idiom:
#   ( echo -800 > /proc/self/oom_score_adj; exec mydaemon )
```

The command form is the reason the tool exists for init scripts: the
adjustment is set on the exact process that execs the daemon, before it
has done anything, with no window where the wrong value applies.

### What the files say

```
$ cat /proc/self/oom_score /proc/self/oom_score_adj
0
0
$ choom -n 1000 -p $$ && cat /proc/self/oom_score_adj
1000
```

Only `oom_score_adj` is writable; writes to `oom_score` fail. The
`oom_score_adj` of a new process is inherited from its parent — so a
+500 batch job spawns +500 children automatically, which is usually the
desired semantics (and a surprise when it is not).

## Options That Matter

| Option | Effect |
| --- | --- |
| `-p, --pid <num>` | Target process; with no `-n`, display its values |
| `-n, --adjust <num>` | Set `oom_score_adj` to num (-1000..1000); with a command, launch it |
| `--` | Separator: everything after is the command to run |
| `-h, --help` / `-V, --version` | Usage / version |

## Usage Patterns

```bash
# Which process is the kernel currently most likely to kill?
ps -eo pid,comm --sort=-rss | head
for p in $(pgrep -f worker); do choom -p $p; done
```

```bash
# Protect a database from the OOM killer during a maintenance window
choom -n -1000 -p "$(pgrep -x postgres | head -1)"
#   (undo afterwards: choom -n 0 -p ...)
```

```bash
# Make expendable nightly jobs die first under memory pressure
choom -n 1000 -p "$(pgrep -f backup.sh)"
```

```bash
# Start a daemon with the adjustment baked in from process birth
choom -n -500 -- /usr/local/bin/memcached -m 8192
```

```bash
# Check the current policy of every process of a user
for p in $(pgrep -u deploy); do choom -p $p; done | grep adjust
```

```bash
# The equivalent raw /proc write (what choom -n does)
echo 500 > /proc/1234/oom_score_adj
```

```bash
# Verify inheritance: children of an adjusted shell inherit the score
choom -n 300 -p $$; choom -p $$       # parent
bash -c 'choom -p $$'                 # child shows adjust value 300
```

```bash
# Watch a process's live badness while it leaks
watch -n2 "choom -p $(pgrep -f leaky-daemon)"
```

```bash
# systemd services set the same value (cheat sheet for cross-checking)
systemctl show -p OOMScoreAdjust nginx
```

## Nuances and Gotchas

- **You cannot make a process *less* killable than your inheritance.**
  Without `CAP_SYS_RESOURCE`, a process may only *raise* its own
  `oom_score_adj` (toward +1000); lowering it below the value inherited
  at fork fails with `EPERM`. The observed error — `choom: failed to set
  score adjust value: Permission denied` — is exactly this rule.
- **`oom_score` is dynamic.** The printed score is a snapshot; a process
  that frees memory drops in score immediately. Only the adjust value is
  stable policy.
- **Inheritance is the silent part.** `oom_score_adj` is copied on
  `fork()`; a daemon started from an adjusted shell carries the shell's
  value, and so do its workers. Reset with `choom -n 0` when inheriting
  is wrong.
- **-1000 is a big hammer.** A protected process makes the OOM killer
  pick something *else* — often your SSH session or init. Protecting the
  biggest process on a box just moves the kill elsewhere; pair
  protection with cgroup memory limits or real capacity fixes.
- **cgroup v2 changes the game.** With `memory.oom.group`, the kernel
  kills the whole cgroup instead of the highest-scoring task, and
  per-process adjustments matter less; check the cgroup configuration
  before debugging "choom didn't work".
- **It is not a memory limit.** choom never prevents OOM; it reorders
  victims. `ulimit -v`, cgroup `memory.max`, or adding RAM prevent it.
- **Does not touch swap behavior or scheduling.** Despite the charming
  name, it has no relation to nice values, rlimits, or swappiness.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Display succeeded or the adjustment was applied (and command exec'd if given) |
| 1 | Usage error, no such PID, or `EPERM` from the kernel on the write |

## Related Commands

- [`chrt`](./chrt.md) — the neighboring scheduling-policy knob; both are `sched_*` wrappers
- [`chcpu`](./chcpu.md) — sysfs counterpart: tuning what the kernel runs on, not whom it kills
- [`../../admin/process-management.md`](../../admin/process-management.md) — where choom sits among process-control tools
- [util-linux overview](./overview.md) — the rest of the process/system toolset

## Interview Questions

### Q: How does the kernel decide which process to kill when memory runs out?

It walks candidate tasks and computes `oom_score` from badness —
dominated by RSS, swap usage, and page tables — then scales it by the
task's `oom_score_adj` (`score = badness * (adj + 1000) / 1000`) and
kills the highest scorer, honoring cgroup constraints first. Root
processes and long-lived ones get small bonuses. The operator-controlled
part is exactly the adjust value, which is what choom writes.

### Q: Why does `choom -n -500 -p $$` fail as an ordinary user?

The kernel forbids unprivileged processes from lowering
`oom_score_adj` below the value inherited from their parent — otherwise
any user could make their processes unkillable. Raising the value
(becoming more expendable) is always allowed; lowering toward -1000
requires `CAP_SYS_RESOURCE`. The failure mode is a clean `EPERM` from the
/proc write.

### Q: What is the practical difference between oom_score and oom_score_adj?

`oom_score` is the kernel's live measurement (badness), recomputed as
memory usage changes, read-only, meaningless in isolation.
`oom_score_adj` is the persistent policy input, writable, inherited by
children, and the only part a tool like choom can change. Debugging
means reading both: score tells you who dies today, adj tells you who
dies tomorrow.

### Q: When would you use `choom -n N -- command` instead of adjusting an existing PID?

When the value must be correct from process birth — init scripts,
systemd `ExecStart=` lines, or wrappers spawning daemons. Writing to a
PID after startup leaves a window where the wrong policy applies and
races with memory pressure. The command form also guarantees the value
applies to the exact process that execs, not to an intermediate shell.

### Q: A service with oom_score_adj -1000 still died under memory pressure. What happened?

Likely it was killed by cgroup memory enforcement rather than the global
OOM killer: hitting `memory.max` (or `memory.oom.group` semantics)
triggers a cgroup-local kill where per-process adjustment carries less
weight — and with oom.group set, the whole cgroup dies together. Check
`systemctl status`, cgroup `memory.events`, and kernel logs for the
difference between a global OOM event and a cgroup one.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/choom.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
