# pidwait — wait for processes matching criteria to exit

## Overview

`pidwait` completes the pgrep family: it runs the same selection machinery as `pgrep` and `pkill` — pattern plus attribute flags — but instead of listing or signalling the matches, it **blocks until they exit**. Nothing is printed by default; the command simply returns when the last matched process is gone. It ships in the `procps` package (Debian bookworm: procps-ng 2:4.0.4) at `/usr/bin/pidwait`, built from the same source as its siblings.

The shell builtin `wait` only waits for your own children. `pidwait` waits for *any* processes you can identify by attributes — a set of workers started by another process, a daemon found by pattern, the PIDs in a pidfile. That fills a real gap in container supervisors, CI teardown scripts, and test harnesses: "block here until everything matching this description is finished."

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 2:4.0.4) |
| Man section | 1 |
| Path | /usr/bin/pidwait |
| First appeared | procps-ng 3.3.x era (mid-2010s); absent from procps 3.3.9 and older |
| Standards | none; procps-ng specific |

## Synopsis

```
pidwait [options] pattern
```

Common one-line forms:

```
pidwait -x ffmpeg          # block until no process named ffmpeg remains
pidwait -f 'train.*py'     # wait for matching full command lines
pidwait -P 909             # wait for all children of PID 909
pidwait -e -x rsync        # echo the PIDs, then wait
pidwait -F /run/app.pid    # wait for the daemon named in a pidfile
```

## How It Works

### Snapshot, then wait

At startup, `pidwait` resolves its selection exactly like pgrep — one pass over `/proc`, attribute gates AND-combined, pattern (or `-f` cmdline, or `-x` exact) applied — and freezes the result. It then watches exactly that set of PIDs and returns when all of them have exited:

```
t=0   pgrep-style scan      -> {4711, 4712}
t=0+  pidwait blocks
t=60  PID 4711 exits        -> keep waiting
t=75  PID 4712 exits        -> return, exit status 0
```

The snapshot semantics matter: **processes started after pidwait launched are invisible to it** and do not extend the wait. A supervisor that restarts workers while pidwait runs will see pidwait return while brand-new workers are alive. For "wait until the system is quiet", either re-run pidwait in a loop or combine with a quiescence check. The converse is also true and is usually the desired behavior: workers spawning *after* your snapshot (children of matched processes, say) do not keep pidwait waiting.

### What "exit" means

A process is waited-for when it is gone from the PID namespace — which for children of a living parent happens only after the parent reaps it. A process that exits but sits as a zombie (parent stuck, not calling `wait()`) still exists in `/proc`, and pidwait keeps waiting for it. This is the same reaping discipline `ps` exposes as STAT `Z`, now with a blocking API in front of it.

### Exit status mirrors the family contract

The shared pgrep-family man page defines the exit codes, with pidwait's twist: success requires that the processes were not merely matched but successfully *waited for*.

| Code | Meaning |
| --- | --- |
| `0` | at least one process matched and was successfully waited for |
| `1` | nothing matched, or none could be waited for |
| `2` | syntax error in the command line |
| `3` | fatal error (out of memory, etc.) |

An empty match set returns immediately with exit 1 — pidwait never blocks forever on a query that matched nothing, and it does not wait for *future* matches (there is no "wait until something matching appears" mode).

### The sibling triangle

```
            selection engine (one source, three verbs)
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
     pgrep             pkill             pidwait
   "tell me"         "signal them"     "block until gone"
   prints PIDs       sends a signal    returns on their exit
```

Same flags, same 15-character comm cap, same `-f`/`-x` matching, same exit-code grammar. Choosing between them is choosing a verb, not learning a tool.

### The polling loop it replaces

Before pidwait, the idiom was a sleep-poll — and every clause of it is a bug waiting:

```bash
# The old way: racy, lossy, and CPU-burning
while pgrep -x worker >/dev/null; do sleep 1; done
```

Problems: a worker can exit and its PID be recycled between the `pgrep` and the next iteration (making the loop believe it is alive); the poll interval trades latency against load; and the loop holds no state, so "which PIDs was I actually watching?" is unanswerable. pidwait resolves the set once, watches exactly those PIDs, and returns a single meaningful exit status for the batch. For a single known PID, GNU tail's `tail -f log --pid=PID` offers a similar block-until-death primitive — but only pidwait composes the pgrep selection grammar with it.

### "Wait until quiet": the loop pattern

When the requirement is really "no process matching X exists anymore" — including respawned ones — pidwait becomes a loop with a termination condition:

```bash
while pidwait -x worker 2>/dev/null; do
    :  # the previous batch is gone; check for respawns once more
done
```

Each successful return means one snapshot has drained; the loop re-snapshots until a scan comes up empty. It is not elegant, but it is the honest encoding of "wait until quiet" given that pidwait deliberately has no appear-later mode.

### Where it earns its keep: containers and teardown

The canonical pidwait shapes:

- **Container supervisor:** an entrypoint starts background workers, then `pidwait -x worker` blocks until the last one dies — the entrypoint stays alive as long as any matched process, without being their parent and therefore without `wait` builtin access.
- **CI teardown:** `pidwait -f '/opt/ci/watchdog'` blocks until the watchdogs finish before the runner cleans the workspace.
- **Test harnesses:** start a service externally, `pidwait -x myservice` to synchronize on its termination instead of polling `pgrep` in a sleep loop.
- **Pidfile-driven waiting:** `pidwait -F /run/app.pid` blocks until the daemon recorded in the pidfile exits — a poor man's `Type=forking` completion signal for software that predates systemd.

## Options That Matter

### Waiting

| Option | Effect |
| --- | --- |
| `-e, --echo` | print each matched PID before waiting for it |
| `-c, --count` | print the count and exit — no waiting happens |
| `-F, --pidfile FILE` | read the PIDs to wait for from a pidfile |
| `-L, --logpidfile` | fail if the pidfile is not locked |

### Selection (identical to pgrep/pkill)

| Option | Effect |
| --- | --- |
| `-f, --full` | match the full command line |
| `-x, --exact` | whole-name match |
| `-i, --ignore-case` | case-insensitive |
| `-u / -U LIST` | effective / real user |
| `-g / -G LIST` | process group / real group |
| `-P, --parent LIST` | children of the given parent(s) |
| `-s, --session LIST` | session ID |
| `-t, --terminal LIST` | controlling terminal |
| `-r, --runstates LIST` | kernel run states (D,S,R,Z,T,I) |
| `-n / -o` | only newest / oldest match |
| `-O, --older SECS` | only processes older than SECS |
| `-A, --ignore-ancestors` | exclude pidwait's own ancestors |
| `--ns PID` / `--nslist` | namespace-based selection |
| `--cgroup LIST` | cgroup v2 membership |

Note what is absent: `--signal` appears in the help output only for flag-set compatibility with pgrep/pkill; in pidwait mode it has no effect unless combined with handler-based filtering in the shared implementation — do not expect pidwait to signal anything. pidwait waits; it never sends signals.

## Usage Patterns

```bash
# Block until every ffmpeg job is done (whatever started them)
pidwait -x ffmpeg && echo "all transcodes finished"

# Echo the watch set, then wait — visibility for logs
pidwait -e -x rsync

# Wait for a specific daemon recorded in its pidfile
pidwait -F /run/myapp.pid && rm -f /run/myapp.pid

# Wait for all children of a supervisor to exit
pidwait -P "$(pgrep -o -x supervisord)"

# Container entrypoint: stay alive while any worker lives
node worker.js & node worker2.js &
pidwait -x node

# CI: block until watchdog processes end, then clean up
pidwait -f '/opt/ci/watchdog' || true

# How many matches right now, without waiting (a pgrep -c alias)
pidwait -c -x myapp

# Guard the pattern against matching your own wrapper
pidwait -A -f 'deploy-worker' || true

# Bounded wait for a hung process: timeout, then escalate
timeout 300 pidwait -x stuckproc || { pkill -KILL -x stuckproc; pidwait -x stuckproc; }

# Wait until quiet, tolerating respawns (loop until empty scan)
while pidwait -x worker 2>/dev/null; do :; done

# Synchronize a test on an externally started service's death
./start-service.sh & spid=$!
pidwait -x service-under-test
./assert-shutdown.sh
```

## Nuances and Gotchas

- **The match set is a snapshot.** Processes spawned after pidwait starts are neither waited for nor detected later. Scripts assuming "wait until nothing matching exists" must loop pidwait until it exits 1.
- **Empty match returns immediately, exit 1.** There is no blocking-until-appears mode; pidwait cannot be used as "sleep until the service starts". For that, poll `pgrep`.
- **Zombies keep it waiting.** An exited-but-unreaped process still occupies its /proc entry; if a broken parent leaks zombies, pidwait blocks on processes that are functionally dead. Fix the reaping, or select with `-r` to exclude Z state.
- **No timeout option.** A wedged D-state process blocks pidwait indefinitely — uninterruptible IO tasks never exit. Wrap the invocation in `timeout 300 pidwait ...` when the wait must be bounded.
- **`-c` does not wait.** It prints the current count and exits, making it a synonym-flavored `pgrep -c` — including the exit-1-on-zero behavior. Do not mistake it for "wait until count is zero".
- **It waits, it never signals.** The `--signal` option in the help output is family plumbing, not a feature; combining pidwait with a signal requires an explicit `pkill` step.
- **Waiting is not reaping.** pidwait does not take over the exit status of processes it watches; parents still owe their `wait()` calls. Observing an exit is not the same as collecting it.
- **Same 15-character comm cap.** Without `-f`, patterns over 15 characters match nothing; the pgrep warning and remedies apply verbatim.
- **Ancestor matching bites harder here than in pgrep.** A wrapper script that both matches the pattern and *is* an ancestor it should outlive creates a self-deadlock: pidwait waits for its own parent to exit. `-A` (`--ignore-ancestors`) is the fix; recognize the shape — a supervisor script whose own name contains the worker pattern.
- **`-F pidfile` freezes the PIDs at read time.** A daemon that forks and rewrites its pidfile after startup leaves pidwait watching the wrong (stale) generation; combine with `-L` to at least require the pidfile to be locked by its writer.
- **Signals are irrelevant to the wait.** Whether the processes exit on their own, get SIGTERMed by someone else, or are OOM-killed makes no difference — pidwait observes the disappearance, not the cause. Correlating cause needs `dmesg`/journal, not pidwait.

## Exit Status

| Code | Meaning |
| --- | --- |
| `0` | at least one process matched and all were waited to completion |
| `1` | nothing matched, or none could be waited for |
| `2` | syntax error in the command line |
| `3` | fatal error (out of memory, etc.) |

The `0`/`1` pair is the scripting contract: exit 0 means "the wait set existed and is now gone", exit 1 means "there was nothing to wait for or the wait failed" — distinguish them deliberately in supervision logic.

## Related Commands

- [`pgrep`](./pgrep.md) — the listing sibling; same flags, prints instead of blocking.
- [`pkill`](./pkill.md) — the signalling sibling; pairs with pidwait in TERM-wait-KILL escalation loops.
- [`ps`](./ps.md) — states (D, Z) that determine whether a wait can ever finish.
- [`pidof`](./pidof.md) — exact-name lookup from the sysvinit side of the family tree.
- [`overview`](./overview.md) — procps collection hub.
- [Process management](../../admin/process-management.md) — reaping, zombie handling, and supervision context.

## Interview Questions

### Q: What does pidwait do that the shell builtin `wait` cannot?

`wait` works only on the calling shell's own children. pidwait selects arbitrary processes by pattern and attributes — name, cmdline regex, parent, user, terminal, run state, namespace — and blocks until they exit, regardless of who spawned them or when. That is the missing piece for container entrypoints supervising non-child workers, CI teardown scripts, and harnesses that must synchronize on external processes. The cost is snapshot semantics and no reaping: pidwait observes exits, it does not collect them.

### Q: A script runs `pidwait -x worker` while a supervisor respawns crashed workers. Why can pidwait return while workers are still running?

The wait set is resolved once at startup; pidwatch — pidwait — blocks for exactly those PIDs. Workers restarted after the snapshot are new PIDs that were never in the set, so their lives do not extend the wait. Correct patterns: loop pidwait until it exits 1 ("no matches left"), or fix the supervisor to not respawn during shutdown. The snapshot model also cuts the other way — children spawned *by* matched processes are not waited for either.

### Q: How would you build a bounded wait for a possibly-hung process?

pidwait has no timeout and a D-state process may never exit (uninterruptible IO ignores everything, including process termination). The pattern is `timeout 300 pidwait -x stuckproc || { pkill -KILL -x stuckproc; pidwait -x stuckproc; }` — bound the wait, escalate with KILL on timeout, then wait again for the kill to land. The exit codes make each stage testable: 0 means the wait completed, 124 from timeout means it did not.

### Q: Why does pidwait exist as a separate binary instead of people looping `pgrep`?

A polling loop is racy (the match can appear and vanish between polls), burns cycles proportional to the poll rate, and re-implements in every script what one /proc-aware process does internally. pidwait centralizes the block-until-exit primitive with the family's exact selection grammar and exit-code contract — and unlike ad-hoc loops, it handles the zombie/reaping subtleties and returns a single meaningful status for the whole wait set.

### Q: Compare pidwait with GNU `tail --pid=PID` and the bash builtin `wait` for synchronizing on process death.

`wait` is children-only but returns the child's exit status — the only one of the three that reaps. `tail --pid=PID` blocks on one specific PID and is handy when you are already tailing a log, but takes no selection logic. pidwait handles an arbitrary set resolved by the full pgrep grammar (name, cmdline, attributes, namespaces), at the price of snapshot semantics, no exit-status collection, and no appear-later mode. Choosing is about what you know up front: a child → `wait`; one PID plus a log → `tail --pid`; a dynamic match set → pidwait.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/pidwait.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
