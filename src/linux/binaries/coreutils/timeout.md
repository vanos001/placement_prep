# timeout — run a command with a time limit

## Overview

`timeout` starts a command and, if that command is still running after a
given duration, sends it a signal — `SIGTERM` by default. It is the standard
shell-level answer to "this call hangs sometimes": wrapping SSH one-liners,
network clients, batch jobs, and interactive prompts with a deadline without
writing watchdog logic in the caller.

It ships in the Debian `coreutils` package at `/usr/bin/timeout`. It is a
GNU addition with no POSIX specification and no traditional Unix heritage —
BSD has no direct equivalent — although busybox provides a reduced `timeout`
that embedded and rescue environments rely on. Scripts that may run outside
GNU userland should test for it rather than assume it.

It is often confused with two patterns: `sleep N; kill $!` in the background
(which cannot handle the command finishing early) and `watchdog`-style
supervisors (which can restart, but are not one-shot). `timeout` occupies
the middle: one-shot, self-cleaning, and transparent about exit status.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/timeout` |
| First appeared / lineage | GNU coreutils 7.x era (2008) |
| Standards | none — GNU extension, not in POSIX |

## Synopsis

```text
timeout [OPTION] DURATION COMMAND [ARG]...
timeout [OPTION]
```

```bash
timeout 5 COMMAND             # TERM after 5 seconds
timeout 90s make target       # explicit suffix
timeout -k 2 10 COMMAND       # TERM after 10s, KILL 2s later if alive
timeout --preserve-status -s INT 30 longjob
```

## How It Works

`timeout` forks, execs the command, and sets an internal timer for the
requested duration. If the command exits first, `timeout` passes its status
through; if the timer fires first, `timeout` sends the configured signal and
reports a timeout status. Unless `--foreground` is given, the child is placed
in its own process group, so the timeout signal reaches not just the direct
child but everything it spawned — a plain `sleep` child of a wrapped shell
dies with its parent.

```text
t=0          t=DURATION            t=DURATION+KILL (-k only)
┌────┐  exec ┌─────────┐  TERM   ┌─────────┐  KILL (if alive) ┌────────┐
│  I │ ────▶ │ COMMAND │ ──────▶ │ COMMAND │ ───────────────▶ │ SIGKILL│
└────┘       └─────────┘ (default)└─────────┘                  └────────┘
   │              │ finished early? → propagate its exit status
   ▼              ▼
 timer armed   timeout reports 124 (or child's status with --preserve-status)
```

The **duration grammar** is a floating-point number with an optional suffix:
`s` (seconds, the default), `m`, `h`, or `d` — so `0.2`, `1.5m`, `2h`, and
`7d` are all valid, and a duration of `0` disables the timeout entirely
(the command runs unbounded). Fractional durations make sub-second limits
practical for health checks.

```bash
$ timeout 1 sleep 5; echo $?        # killed at 1s
124
$ timeout 1.5 sleep 0.2; echo $?    # finishes first
0
$ timeout -k 0.3 1 sleep 30; echo $?
124
$ timeout --signal=INT 1 sleep 30; echo $?   # signal choice does not change 124
124
```

Two behaviours interviewers probe. First, the **default signal is TERM and
the default status is 124** regardless of which signal was sent — the status
only mirrors the child when `--preserve-status` is used. Second, **escalation
is not automatic**: a command that traps or ignores `SIGTERM` (a database
doing a clean shutdown) will survive the timeout indefinitely unless `-k`
schedules a follow-up `SIGKILL`, which cannot be caught:

```bash
$ timeout -k 0.3 0.2 bash -c 'trap "" TERM; sleep 5'; echo $?
137            # TERM was ignored, KILL landed: 128 + 9
```

`--preserve-status` makes `timeout` report the child's own status even when
the timeout fired — essential when the child distinguishes outcomes by exit
code (for example a trapped signal used as a controlled shutdown):

```bash
$ timeout --preserve-status -s INT 0.2 bash -c 'trap "exit 42" INT; sleep 5'
$ echo $?
42
```

## Options That Matter

| Option | Effect |
|---|---|
| `DURATION` | Float with optional `s`/`m`/`h`/`d` suffix; `0` disables the timeout |
| `-k, --kill-after=DURATION` | Send `SIGKILL` this long after the first signal, if still alive |
| `-s, --signal=SIGNAL` | Signal to send on timeout: name (`HUP`, `USR1`, `INT`) or number |
| `-p, --preserve-status` | Exit with the child's status even on timeout |
| `-f, --foreground` | No separate process group: child may read the TTY and get TTY signals; its children are *not* timed out |
| `-v, --verbose` | Diagnose on stderr whenever a signal is sent |

`--foreground` exists for two situations: when `timeout` itself is not
running from a shell prompt (services, cron) and the child needs terminal
interaction; and when the child manages its own process groups (session
leaders) that group-wide signals would disrupt.

`-v` makes every signal transmission visible on stderr, which turns the
escalation timeline from guesswork into an audit trail when debugging a
wrapper that "sometimes" kills things:

```bash
$ timeout -v -k 1 0.5 bash -c 'trap "" TERM; sleep 30'
timeout: sending signal TERM to command 'bash'
timeout: sending signal KILL to command 'bash'
$ echo $?
137
```

Durations compose with arithmetic in the caller — the shell expands
`$((60*60))` before timeout sees `3600` — and the special value `0`
disables the limit entirely, which is how wrapper scripts let users opt out
through an environment variable without a second code path.

## Usage Patterns

```bash
# Deadline for a network probe in a health-check script
timeout 5 bash -c '</dev/tcp/example.org/25' || echo "smtp down"
```

```bash
# SSH one-liners that must not hang on a dead host
timeout 10 ssh -o ConnectTimeout=5 backup host-sync.sh
```

```bash
# TERM, then hard KILL 3 seconds later — for jobs that trap TERM
timeout -k 3 60 rsync -a src/ dest/
```

```bash
# Interactive prompt with a default: INT, and keep the child's status
timeout --preserve-status -s INT 15 read -r -p "confirm? " answer
```

```bash
# Ask a daemon to reload instead of terminate
timeout --signal=USR1 20 ./worker --once
```

```bash
# Cron jobs should never overlap or hang forever
17 2 * * * timeout 4h /usr/local/bin/nightly-backup.sh
```

```bash
# Sub-second timeout for a latency sanity check
timeout 0.5 curl -s -o /dev/null https://example.org && echo fast
```

```bash
# Guard a foreground interactive program that reads the TTY
timeout --foreground 30 ./installer --console
```

```bash
# Watch whether the whole tree dies: the sleep child is killed too
timeout 0.3 bash -c 'sleep 30 & wait'
```

```bash
# Disable a configured timeout in a wrapper variable
LIMIT=${LIMIT:-0}; timeout "$LIMIT" ./job   # LIMIT=0 → unbounded
```

## Nuances and Gotchas

- **124 is the timeout status** — but only without `--preserve-status`. With
  it, a timed-out child's status (often `128+N` for signal `N`) propagates,
  and you lose the ability to distinguish "timed out" from "child exited
  with that value" without extra bookkeeping.
- **Signals that get ignored defeat timeout.** `SIGTERM` is catchable; a
  child that traps it survives. Always pair potentially-stubborn jobs with
  `-k DURATION`. `SIGKILL` escalation exits with `137` (128+9) on recent GNU
  coreutils.
- **`--foreground` disables tree-wide timeout.** In that mode children of
  the command are not signalled — fine for interactive wrappers, a footgun
  for anything that spawns daemons.
- **Processes in uninterruptible sleep (D state) ignore even SIGKILL** —
  usually NFS or storage hangs. `-k` will report success sending the signal
  while the process lingers; check `ps` state, not just the exit status.
- **`timeout` itself failing is 125, not 124**: bad options or a missing
  operand (`timeout 10` with no command) exit 125. 126/127 mean the child
  could not be executed / found, exactly like `env` and `xargs` semantics.
- **Durations are human units, not cron syntax**: `90s` works, `1m30s` does
  not — compose with the shell instead (`$((90))s`).
- **busybox timeout** supports `t DUR CMD` basics but lacks
  `--preserve-status`, `--foreground`, and rich signal names on some builds;
  portable scripts should degrade gracefully.
- **Wrapping a pipeline times out only the direct child.**
  `timeout 5 sh -c 'a | b'` limits the whole pipeline (it is one command);
  `timeout 5 a | b` limits only `a`, and `b` may hang forever on a stalled
  producer.

## Exit Status

| Status | Meaning |
|---|---|
| 124 | COMMAND timed out (default mode; overridden by `--preserve-status`) |
| 125 | `timeout` itself failed (bad option, missing operand) |
| 126 | COMMAND found but not executable |
| 127 | COMMAND not found |
| 137 | COMMAND was terminated by the escalated `SIGKILL` (128+9) |
| child's status | With `--preserve-status`, always the child's own status |

## Related Commands

- [`stdbuf`](./stdbuf.md) — the other wrapper you commonly stack around long-running pipeline stages.
- [`yes`](./yes.md) — unbounded producers that benefit from an external deadline.
- [`true`](./true.md) — trivial child whose exit status makes propagation visible.
- [coreutils collection](./overview.md) — sibling GNU coreutils pages.

## Interview Questions

### Q: A job under `timeout 60 job` keeps running forever. Diagnose.

Most likely the job traps `SIGTERM` (clean-shutdown handlers do) and never
finishes within 60 seconds of receiving it. `timeout` sent TERM and waited
indefinitely. Fix: `timeout -k 5 60 job` so SIGKILL follows five seconds
after TERM. If the job is in D state, even KILL will not reap it — check
`ps -o stat=` for `D` and look at storage/NFS, not at timeout.

### Q: Explain the difference in exit status between `timeout 5 slow` and `timeout --preserve-status -s INT 5 slow`.

In the first, a timeout reports 124 no matter which signal killed the child;
124 is timeout's own convention. In the second, `--preserve-status` reports
the child's actual outcome: if the child died from the INT signal, 130
(128+2); if it trapped INT and exited 3, then 3. The first answers "did the
deadline fire?", the second answers "what did the child do?" — pick based on
whether the caller cares about the distinction.

### Q: Why does timeout put the child in a new process group, and what changes with --foreground?

A separate process group lets the timeout signal reach the entire spawned
tree — shell wrappers that background `sleep` or helper daemons all die at
the deadline, which is usually the desired semantics for batch jobs.
`--foreground` keeps the child in timeout's group so it can read the
controlling terminal and receive TTY-generated signals normally, at the
price that only the direct child is timed out. Interactive programs need the
latter; headless jobs want the former.

### Q: What do exit codes 124, 125, 126, and 127 mean for timeout, and why does the distinction matter in scripts?

124: the command was killed by the timeout. 125: timeout itself failed (bad
arguments). 126: the command existed but could not be executed (permissions).
127: the command was not found. Scripts that treat "non-zero" as "timed out"
will misreport configuration errors as hangs; probing 125-127 separately is
how robust wrappers tell "my wrapper is broken" from "the job was too slow".

### Q: How would you bound a whole pipeline, and what is wrong with `timeout 5 a | b`?

Wrap the pipeline in a single shell: `timeout 5 sh -c 'a | b'` — timeout
signals one child (the shell) and, via the process group, both pipeline
members. `timeout 5 a | b` applies the deadline only to `a`; if `a` is
killed, `b` sees EOF and may exit, but if `b` is the slow side, it runs
unbounded while `timeout` reports success or timeout for `a` alone. The
general rule: timeout bounds exactly one child process tree, so decide which
tree that is.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/timeout.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
