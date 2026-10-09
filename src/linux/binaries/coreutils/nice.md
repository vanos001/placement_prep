# nice — run a command with an adjusted scheduling niceness

## Overview

`nice` starts a command with a modified *niceness* — a hint the scheduler
uses to decide how CPU time is distributed among runnable processes. It
wraps `setpriority(PRIO_PROCESS, ...)` before `exec`-ing the command, so
the target program runs its entire life at the adjusted value with no
cooperation required. The name is imperative: a "nicer" process yields to
its neighbors.

Niceness ranges from **-20** (most favorable) to **19** (least favorable),
with lower values winning scheduling contests. The unprivileged rule is
asymmetric and is the classic interview trap: *you may increase niceness
(lower priority) freely, but decreasing it (raising priority) requires
`CAP_SYS_NICE`* — root, or a specially configured `pam_limits`/`systemd`
grant. The tool ships in the Debian `coreutils` package at
`/usr/bin/nice`; note that your shell may also provide a `nice` builtin
(the coreutils binary even says so in its help text), which shadows the
external one for interactive use.

It is often confused with `renice` (changes an already-running process)
and `ionice` (same idea for I/O bandwidth, util-linux).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Man section | 1 |
| Path | `/usr/bin/nice` |
| First appeared | early AT&T Unix |
| Standards | POSIX 2018 utility; kernel interface `setpriority(2)` |

## Synopsis

```
nice [OPTION] [COMMAND [ARG]...]
```

Main forms:

```
nice                          # print current niceness
nice command args...          # run at default adjustment (+10)
nice -n 15 command args...    # run at explicit adjustment
nice -n -5 command args...    # raise priority (needs privilege)
```

## How It Works

`nice` calls `setpriority()` for its own process, then `exec()`s the
command. The niceness is inherited: every child the command spawns gets
the same value, so `nice -n 19 make` yields an entire build tree at
niceness 19 (unless a child explicitly re-adjusts).

```bash
# No command: print the caller's current niceness
$ nice
0

# Default adjustment is +10 (POSIX-specified behavior when -n is absent)
$ nice -n 10 bash -c 'nice'
10

# Adjustments are relative and stack across nested nice invocations
$ nice -n 5 nice -n 3 bash -c 'nice'
8
```

The scheduling model: each CPU picks runnable tasks weighted by their
priority; niceness translates into a weight where roughly *each step of 5
niceness ≈ halving the CPU share* a competing process gets — but only when
there is contention. A nice'd process on an idle multicore box runs at
full speed; the value only matters when cores are busy.

```
  runnable tasks on one CPU
  ┌───────────────────────────────┐
  │ make -j8     nice 0   ▓▓▓▓▓▓▓ │  ~87% share
  │ gzip backup  nice 10  ▓       │  ~13% share
  └───────────────────────────────┘
        (only while both are runnable)
```

The privilege boundary, grounded:

```bash
# Unprivileged: increasing niceness is always allowed
$ nice -n 10 true; echo $?
0

# Unprivileged: decreasing niceness fails — but the command STILL RUNS
$ nice -n -5 true
nice: cannot set niceness: Permission denied
$ echo $?
0
```

That last behavior is easy to misread: GNU `nice` warns and *executes the
command anyway, without the adjustment*. If you need the priority change
to be mandatory, check for the failure explicitly or run it under a user
that holds `CAP_SYS_NICE`.

## Options That Matter

| Option | Effect |
|---|---|
| `-n, --adjustment=N` | Add `N` to the current niceness (default `10` if no `-n` given but a command is present) |
| `--help` / `--version` | Informational |

Details worth knowing:

- `N` is a *relative* adjustment from the invoking process's niceness, not
  an absolute target. `nice -n -5 cmd` in a shell at 0 attempts -5; the
  same command in a shell already at 10 attempts 5.
- Without `-n`, `nice cmd` uses the POSIX default adjustment of `10`.
- Values outside -20..19 are clamped by the kernel to the range; requests
  below the unprivileged floor fail as shown above.
- `--` ends option parsing, which lets you nice a command that starts
  with a dash: `nice -n 10 -- -weird-flag-cmd`.

## Usage Patterns

```bash
# Be a good citizen: run a long compression at lowest priority
nice -n 19 tar czf backup.tar.gz /data
```

```bash
# Whole build tree inherits the niceness
nice -n 10 make -j"$(nproc)"
```

```bash
# One-shot CPU-burning cleanup during business hours
nice -n 15 find /var/tmp -depth -type f -mtime +30 -delete
```

```bash
# Nested: benchmark harness a bit nicer, the compile itself much nicer
nice -n 5 nice -n 10 make -j8
```

```bash
# Cron entry that plays nice with production traffic
0 2 * * * nice -n 10 ionice -c3 /usr/local/bin/nightly-sync.sh
```

```bash
# Print current niceness inside a pipeline or subshell
bash -c 'nice'
```

```bash
# Fail loudly if the priority raise could not be applied (root scripts)
nice -n -10 rt-worker || echo "warning: ran at default priority"
```

```bash
# Compare scheduling behavior under contention (two terminals, then top)
nice -n 19 sha256sum /dev/zero &   # terminal 1
sha256sum /dev/zero &              # terminal 2 — watch %CPU in top(1)
```

## Nuances and Gotchas

- **Unprivileged decrease fails silently-ish.** The warning goes to stderr
  and the command runs *at the unmodified niceness*, exiting with the
  command's status. Scripts that assume `-n -5` took effect are wrong; the
  only observable difference is the warning line.
- **`nice` is not a security or resource control.** It is a scheduling
  hint. A nice 19 process can still saturate I/O, allocate all RAM, and —
  with only one runnable competitor — get full cores. Use cgroups
  (`systemd-run --scope -p CPUQuota=`) for hard limits.
- **Niceness is inherited, not propagated later.** Children spawned before
  a `renice` on the parent keep their old value; `renice` must target the
  whole process group or each PID.
- **Nice does not affect I/O priority.** A nice'd `dd` will still hammer
  the disk; pair with `ionice -c3` (idle I/O class) when that matters.
- **The multi-CPU illusion.** On an idle 32-core box, a nice 19 job is
  indistinguishable from nice 0 in wall-clock terms. Benchmarks must
  create contention to test niceness.
- **Shell builtins may shadow it.** Bash does not provide a `nice`
  builtin, but some shells (and older environments) do; coreutils' help
  text explicitly warns "Your shell may have its own version of nice".
  In scripts, `command nice` or an absolute path removes doubt.
- **POSIX `-n` value grammar.** POSIX allows the old-style detached form
  `nice -5 cmd` (meaning +5, no sign-to-operand confusion). GNU requires
  `nice -n 5 cmd` for the same effect; the old spelling still works but is
  a portability minefield because `-5` also looks like an option.
- **Cannot nice *another* process.** That is `renice`'s job. `nice` only
  affects the command it is about to exec.

## Exit Status

| Code | Meaning |
|---|---|
| command's status | The command ran; `nice` forwards its exit status (success of the adjustment failure does not change this) |
| `125` | `nice` itself failed (bad options, invalid adjustment) |
| `126` | COMMAND found but not executable |
| `127` | COMMAND not found |

## Related Commands

- [`./overview.md`](./overview.md) — GNU Coreutils collection hub.
- [`./nohup.md`](./nohup.md) — the other "wrap a command, change how it lives" prefix.
- [`./nproc.md`](./nproc.md) — size parallelism before you nice it.
- [`./sleep.md`](./sleep.md) — pacing companion for batch scripts.

Unrelated links are intentionally omitted: `renice` (adjust running
processes) and `ionice` (I/O scheduling) ship in `procps`/`util-linux`
and are covered elsewhere in the book.

## Interview Questions

### Q: What is the valid niceness range and what can an unprivileged user change?

-20 (most favorable) through 19 (least favorable). Unprivileged users may
only *increase* niceness (make the process less favorable); decreasing it
needs `CAP_SYS_NICE` (root or a configured grant). The kernel clamps
out-of-range requests. This asymmetry prevents users from grabbing
scheduler priority at others' expense while letting them volunteer to
yield.

### Q: `nice -n -5 cmd` as a normal user prints "cannot set niceness: Permission denied" and then... what happens?

The command runs anyway, at the original niceness, and `nice` exits with
the command's exit status. The failure to adjust is non-fatal by design.
A robust script that *requires* the priority must detect the condition
(check stderr, compare `nice` output before/after) or run with privilege.

### Q: Why did `nice -n 19 make` not slow the build down at all on an idle 64-core machine?

Niceness only arbitrates *contention*. With idle cores, the scheduler
runs every runnable task at full speed regardless of niceness; the value
would matter only when more runnable tasks exist than cores (or against
other busy processes). This is also why benchmarks of niceness require a
loaded system.

### Q: Difference between `nice` and `renice`?

`nice` sets an *initial* adjustment before a command starts (it wraps
exec); `renice` changes the niceness of *already-running* processes by
PID, user, or process group. They complement each other: launch batch
jobs with `nice -n 19`, and if an operator realizes the batch is starving
something critical mid-run, `renice -n 0 -p PID` (privileged) re-prioritizes
without restarting it.

### Q: A script does `nice -n 10 ionice -c3 tar czf ...`. Why combine the two?

They control different resources: niceness shapes *CPU* scheduling;
`ionice` shapes disk *I/O* scheduling. A tar.gz of a huge tree is
alternately CPU-bound (gzip) and I/O-bound (reading the tree), so one
knob alone would leave the other resource unthrottled. `ionice -c3` (idle
class) additionally only grants I/O time when nothing else wants the disk.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/nice.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — nice](https://pubs.opengroup.org/onlinepubs/9699919799/)
