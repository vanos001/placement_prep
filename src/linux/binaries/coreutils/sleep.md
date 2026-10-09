# sleep — pause for a given duration

## Overview

`sleep` delays for a requested amount of time, then exits successfully. It
has no data model, no files, no options beyond `--help`/`--version` — one
operand grammar, one syscall, one exit code. That minimalism is exactly why
it is everywhere: pacing loops, retry backoff, test settle time, container
keep-alives.

Despite looking like shell syntax, `sleep` is **not a shell builtin** in
bash — `type -a sleep` resolves to `/usr/bin/sleep` (and `/bin/sleep`, the
same binary through the merged-usr symlink). Every loop iteration forks and
execs it, which is negligible at second granularity and measurable in tight
sub-second polling.

It ships in the `coreutils` package (Debian bookworm: GNU coreutils 9.1) at
`/usr/bin/sleep`. It is often confused with `timeout` (which *enforces* a
limit around another command) and with `read -t` (which delays *until input
or deadline*). GNU's suffixes and fractional seconds are extensions — POSIX
only defines `sleep seconds` with a single unsigned decimal integer.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section | 1 |
| Path | `/usr/bin/sleep` |
| First appeared | Version 4 AT&T UNIX (1973) |
| Standards | POSIX.1-2018 (`sleep`); suffixes, fractions, multiple operands are extensions |

## Synopsis

```
sleep NUMBER[SUFFIX]...
sleep OPTION
```

Common forms:

```
sleep 5          # integer seconds — the only portable spelling
sleep 0.5        # fractional seconds (GNU/BSD extension)
sleep 1h 30m     # multiple operands: sleeps the SUM
sleep infinity   # GNU parses infinity — never returns on its own
```

## How It Works

### Operand grammar

Each operand is a number (integer or floating point) followed by an optional
suffix. All operands are parsed and summed **before** any sleeping starts —
an invalid operand aborts immediately without a partial sleep:

```bash
$ sleep 0.01m 0.01s          # 0.6s + 0.01s — operands add up
# process slept ~612 ms
$ sleep 1x; echo $?
sleep: invalid time interval '1x'
1
$ sleep 1,5; echo $?         # decimal point is '.', not the locale's
sleep: invalid time interval '1,5'
1
```

| Operand | Meaning |
|---|---|
| `N` | N seconds (integer; POSIX-compatible) |
| `N.N` | Fractional seconds (GNU; parsed with a `.` decimal point) |
| `Ns` / `Nm` / `Nh` / `Nd` | Seconds, minutes, hours, days |
| several operands | Their sum: `sleep 2d 3h 1m 0.5s` |
| `inf` / `infinity` | Infinite interval — accepted, never returns |
| `nan` | Rejected: `invalid time interval` |

The `inf` acceptance is a documented GNU behavior worth knowing cold:
`sleep infinity` is the idiomatic "do nothing forever" for PID-1 containers,
but a typo like `sleep 5inf`-adjacent mistakes (`sleep inf` where `sleep 5`
was meant) hangs a script until killed.

### The pause itself

`sleep` calls `nanosleep(2)` (with fallbacks) and blocks. The process state
is `S` (interruptible sleep): it consumes zero CPU, holds no locks, and is
visible in `ps` as exactly the diagnostic you'd expect. The kernel wakes it
when the timer expires, and `sleep` exits 0.

Two timing properties matter:

- **At-least semantics.** The kernel rounds the request up to timer
  granularity and the scheduler adds wakeup latency; under load, `sleep 1`
  can easily take 1.05 s. Never use `sleep` for precision timing.
- **Relative duration, realtime exposure.** The interval is measured against
  the wall clock; system clock steps, NTP corrections, and VM
  suspend/resume can shorten or lengthen long sleeps. Schedules that must be
  exact belong in cron or systemd timers, not `sleep 1d` loops.

```
 argv ──► parse each NUMBER[SUFFIX], sum the seconds
             │  invalid operand ──► stderr + exit 1 (before sleeping)
             ▼
      nanosleep(total)          process state: S, 0% CPU
             │  signal with default disposition (INT, TERM, HUP…)
             ├────────────► die — shell observes 128+signo (e.g. 143)
             ▼
      timer expires ─────────► exit 0
```

### Signals and interruption

GNU `sleep` installs no signal handlers: SIGINT, SIGTERM, or SIGHUP kill it
outright, and the shell reports `143` for a SIGTERM death. It does not save
or resume the remaining interval.

The interaction with bash traps is the part interviews probe. Bash executes
a trapped signal's handler only **after the current foreground command
completes** — so in

```bash
trap 'echo shutting down; exit' TERM
sleep 300        # kill -TERM $$ lands here... after 300 s
```

the handler waits out the full 300 seconds. The standard fix is to make the
sleep a background job and block on `wait`, which *is* interruptible:

```bash
sleep 300 & wait $!   # trap runs the instant the signal arrives
```

## Options That Matter

There are only two — `sleep` has no functional options, which is itself the
answer to "what flags does sleep take":

| Option | Effect |
|---|---|
| `--help` | Usage; documents the suffix set and sum semantics |
| `--version` | Version string (`sleep (GNU coreutils) …`) |

Operand edge cases that behave like options or errors:

| Input | Result |
|---|---|
| `sleep -1` | `invalid option -- '1'`: leading `-` is parsed as a flag, then rejected |
| `sleep` (no args) | `missing operand`, exit 1 |
| `sleep 0` | Valid: nanosleep(0), returns immediately |
| `sleep 1m 30s` | 90 seconds — operands sum |

## Usage Patterns

```bash
# The classic pacing loop
while :; do
    check_service || alert
    sleep 30
done
```

```bash
# Exponential backoff between retries
delay=1
until curl -sf "$URL"; do sleep $delay; delay=$((delay * 2)); [ $delay -gt 60 ] && exit 1; done
```

```bash
# Fractional settle time in test scripts
start_service; sleep 0.2; run_assertions
```

```bash
# Rate-limit an API loop to ~2 requests/second
while read -r row; do call_api "$row"; sleep 0.5; done < rows.txt
```

```bash
# Countdown in a deploy script
for i in 3 2 1; do echo "cutover in $i"; sleep 1; done
```

```bash
# Container keep-alive: PID 1 that holds the namespace open
# Dockerfile: CMD ["sleep", "infinity"]  →  docker exec -it box bash
exec sleep infinity
```

```bash
# Bounded hold: sleep forever until an external cap kills it
timeout 0.5 sleep infinity; echo "exit=$?"   # 124 (timeout's code)
```

```bash
# Interruptible wait: script reacts to TERM instantly instead of after the nap
trap 'cleanup; exit 0' TERM INT
while :; do work; sleep 60 & wait $!; done
```

```bash
# Poll for a condition instead of sleeping a fixed guess
until [ -f /var/run/ready ]; do sleep 2; done
```

```bash
# Stagger fleet-wide cron jobs to avoid a thundering herd
sleep $((RANDOM % 60)); run_heavy_job
```

```bash
# Throttle a hot loop without busy-waiting
while :; do poll_queue; sleep 0.05; done
```

## Nuances and Gotchas

- **Portability cliff at the grammar.** POSIX `sleep` takes exactly one
  unsigned decimal integer: `sleep 5` is portable; `sleep 5s`, `sleep 0.5`,
  and `sleep 1h 30m` are not. GNU and modern BSD sleep accept suffixes and
  fractions, but minimal busybox builds accept fractions only when compiled
  with `FANCY_SLEEP`. In shared scripts, use integers or probe first.
- **Not a builtin.** Each call is a fork+exec of `/usr/bin/sleep`. Fine at
  Hz rates; for sub-second loops, `sleep 0.05` still forks thousands of
  processes per minute — acceptable, but know the cost (zsh ships a builtin;
  bash does not).
- **`sleep infinity` really is infinite.** GNU parses `inf`/`infinity` as an
  infinite interval (while rejecting `nan`). A stray `sleep inf` in a script
  hangs until killed; also, `sleep -1` is an *option-parse* error, not a
  negative delay.
- **Traps wait for sleep.** As shown above, bash defers trap handlers until
  the foreground command returns. Any daemon-ish script that must react to
  signals needs `sleep n & wait $!` — this is the single most common sleep
  bug in service scripts.
- **Validation happens up front.** `sleep 100 1x` sleeps nothing and fails
  immediately; conversely `sleep 1x 100` also fails with no partial sleep.
  Compose intervals carefully — there is no rollback.
- **Overshoot is normal.** `sleep 60` in a `while` loop with real work
  drifts: each iteration takes work-time plus 60 s. For fixed-rate
  schedules, compute the next deadline or use a scheduler; for one-shot
  delays, the drift usually does not matter.
- **Exit status is almost always 0 or 1.** A killed sleep surfaces in the
  shell as 128+signo (`143` after SIGTERM), which scripts mistake for
  sleep's own status — check `$?` semantics where it matters.
- **Locale decimals.** The decimal point is `.`; `sleep 1,5` is an invalid
  interval. Generate operands programmatically with `awk`/`printf` in the C
  locale if you compute delays.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Slept the requested duration (sum of operands) |
| 1 | Invalid time interval, missing operand, or bad option — before any sleeping |

A sleep killed by a signal reports the conventional shell status `128+signo`
(130 on Ctrl-C, 143 on SIGTERM); that value comes from the shell, not from
sleep's own error codes.

## Related Commands

- [`timeout`](./timeout.md) — runs a command under a duration cap; the inverse contract of `sleep`.
- [`nohup`](./nohup.md) — the other half of long-nap scripts: survive hangups while you wait.
- [`nice`](./nice.md) — irrelevant for sleep itself (it blocks, not burns), but pairs with the loops that follow it.
- [`date`](./date.md) — timestamps around `sleep` for measuring real elapsed time.
- [`true`](./true.md) — `while true; do …; sleep n; done` is the idiomatic polling frame.
- [bash](../../shell/bash.md) — `read -t`, traps, and `wait`: the shell-side machinery sleep interacts with.
- [Process management](../../admin/process-management.md) — signals and states behind the `143` and the `S` in `ps`.
- [systemd](../../admin/systemd.md) — timers replace `sleep 1d`-style scheduling when precision matters.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [Linux Userland Binaries](../overview.md) — the part this page belongs to.

## Interview Questions

### Q: A script has `trap cleanup TERM` and `sleep 300` in its loop, but `kill -TERM` takes up to five minutes to act. Why, and what is the fix?

Bash runs trap handlers only after the currently executing foreground
command finishes, so the pending TERM waits out the entire sleep. Make the
sleep a background job and block with `wait $!`: `wait` is interruptible by
trapped signals, so the handler fires the moment the signal arrives. The
same pattern (`sleep n & wait`) is the backbone of well-behaved container
entrypoint scripts.

### Q: Does `sleep 60` consume CPU? What is the process actually doing?

No. It sits in a single blocking `nanosleep(2)`; `ps` shows state `S`
(interruptible sleep) with 0% CPU. The kernel timer wakes it, and the only
CPU spent is the fork/exec and the exit — which is why `sleep` is cheap as
pacing but not free as a call rate: a `sleep 0.001` loop forks a thousand
processes per second while still burning no CPU inside sleep itself.

### Q: Why does `while :; do job; sleep 60; done` drift, and what are two fixes?

Each iteration adds `job`'s runtime to the 60-second nap, so the loop period
is 60 s + work time and the schedule slides. Fix one: compute the next
deadline before sleeping and sleep only the remainder. Fix two: hand the
schedule to a real timer — cron or a systemd timer — which fires on clock
time, not on loop period. Interviewers accept "fixed-rate vs fixed-delay
scheduling" phrasing.

### Q: Why does `CMD ["sleep", "infinity"]` keep a container running, and when would you choose it over other keep-alives?

A container lives while its PID 1 lives; `sleep infinity` (GNU accepts the
infinite interval) is a process that blocks forever, consumes no CPU, and
exits immediately on SIGTERM, so `docker stop` is instant. Alternatives:
`tail -f /dev/null` (also blocks; also coreutils) or a shell reading stdin —
but `sleep` is the smallest, clearest choice. For a *bounded* hold, wrap it:
`timeout 1h sleep infinity`.

### Q: Is `sleep 5s` safe to put in a script that also runs on Alpine?

Not unconditionally. POSIX defines only an unsigned integer operand, so
`sleep 5` is the portable spelling; suffixes and fractions are GNU/BSD
extensions, and minimal busybox builds (Alpine's default shell tools) accept
fractions only with `FANCY_SLEEP` compiled in — though busybox does support
suffixes. For cross-platform scripts: integers, or probe `sleep 0.1` once
and branch.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/sleep.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — sleep](https://pubs.opengroup.org/onlinepubs/9699919799/)
