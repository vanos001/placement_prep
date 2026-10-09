# kill — send a signal to a process

## Overview

`kill` sends signals to processes — terminate, but also reload (`HUP`), dump state (`USR1`/`USR2`), pause (`STOP`), and resume (`CONT`). The name undersells it: `kill` is the *signal* command, and signaling is the standard inter-process control mechanism on Unix. On Debian bookworm the standalone binary `/usr/bin/kill` ships in the **procps** package (procps-ng); upstream util-linux also builds a compatible `kill(1)`, but Debian installs the procps one. The whole story matters because interactive shells (bash, dash, zsh) provide a `kill` *builtin* that shadows `/usr/bin/kill`, and the two differ in small but real ways.

Reach for it in scripts and admin work: graceful shutdowns, service reloads, liveness probes (`kill -0`), process-group termination. It is often confused with `pkill`/`pgrep` (find by name, then signal), `killall` (same idea, exact-name match), and with `kill -9` folklore ("just force-kill it") which skips the graceful-termination protocol that well-behaved programs expect.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) — but note: `/usr/bin/kill` ships from procps; util-linux also provides one upstream |
| Man section | 1 |
| Path | /usr/bin/kill (shell builtin normally intercepts first) |
| First appeared | AT&T UNIX, early 1970s |
| Standards | POSIX.1-2018 (`kill` utility) |

## Synopsis

```
kill [options] <pid> [...]
kill -<signal> <pid>...          # compact, ubiquitous form
kill -l [<exit_status>|<signal>]
```

Common one-line forms:

```
kill 1234                # SIGTERM (15) — the polite default
kill -9 1234             # SIGKILL — last resort
kill -HUP $(pidof nginx) # reload daemons
kill -- -PGID            # signal an entire process group (leading -)
```

## How It Works

### Three implementations, one name

```
you type:  kill 1234
              │
              ▼
   shell resolves the name "kill"
              │
   ┌──────────┴───────────────┐
   ▼                          ▼
builtin (bash/dash/zsh)   /usr/bin/kill (procps-ng on Debian)
• needs -n for numbers      • no -n (numbers via -<n> or -s <n>)
• understands %jobspecs     • no job control awareness
• -l decodes exit status    • -L aligned table, -q sigqueue value
```

The builtin exists because job control (`kill %1`) requires shell state. Scripts run with `sh`/`bash` therefore get the builtin; `env kill` or the full path `/usr/bin/kill` reach the procps binary (`command kill` bypasses shell *functions* but still resolves the builtin). Behavior for plain `kill <pid>` is identical; the edges (jobspecs, `-n`, exit-status decoding) differ.

### Signals: what actually travels

A signal is a tiny kernel-delivered notification with a number, a name, and a default disposition. `kill -L` (procps) shows the standard table:

```
 1 HUP      2 INT      3 QUIT     4 ILL      5 TRAP     6 ABRT
 7 BUS      8 FPE      9 KILL    10 USR1    11 SEGV    12 USR2
13 PIPE    14 ALRM    15 TERM    16 STKFLT  17 CHLD    18 CONT
19 STOP    20 TSTP    21 TTIN    22 TTOU    23 URG     24 XCPU
25 XFSZ    26 VTALRM  27 PROF    28 WINCH   29 POLL    30 PWR
31 SYS
```

Signal numbers 32+ are glibc/NPTL internals and realtime signals (`SIGRTMIN`…`SIGRTMAX`, typically 34–64) used for queuing with values (`sigqueue`). Beyond the table:

- `TERM` (15) — catchable request to exit; the default and the *right* first move.
- `KILL` (9) — uncatchable, unconditional; destroys the process but not its children or locks cleanup.
- `HUP` (1) — conventionally "re-read your configuration".
- `STOP`/`TSTP`, `CONT` (19/20, 18) — pause/resume; `STOP` cannot be caught.
- `INT`/`QUIT` (2/3) — what Ctrl-C / Ctrl-\ deliver.

### Delivery rules

`kill` performs `kill(2)`/`sigqueue(3)`. To signal a process you must be root or have the same *real or effective* uid (setuid binaries complicate this — the kernel checks real/effective/save-set uids). Special operands:

- **pid > 0** — that process.
- **pid = 0** — every process in the caller's *process group* (your whole pipeline).
- **pid = -1** — every process you may signal except init and yourself (`kill -9 -1` as root ends the system's userland; famous foot-gun).
- **pid < -1** — the process group with that PGID; `kill -- -1234` needs `--` so `-1234` is not parsed as a flag.

### Dispositions: what each signal does by default

Every signal has a default disposition, and the catchable/uncatchable split is the heart of `kill` practice:

```
signal   number   default action      catchable?   typical use
TERM     15       terminate           yes          polite shutdown (default)
KILL     9        terminate           NO           last resort
HUP      1        terminate           yes          config reload convention
INT      2        terminate           yes          Ctrl-C
QUIT     3        terminate+core      yes          Ctrl-\, diagnostics
USR1/2   10/12    terminate           yes          app-defined hooks
PIPE     13       terminate           yes          reader vanished
ALRM     14       terminate           yes          timeout(1) machinery
CHLD     17       ignore              yes          child state change
STOP     19       suspend             NO           supervisor pause
TSTP     20       suspend             yes          Ctrl-Z
CONT     18       resume              yes          job control
```

The two **uncatchable, unblockable** ones — `KILL` and `STOP` — are the kernel's enforcement layer; everything else is a request a program may decline, including `CONT`, which a process may trap to react to being resumed.

### Realtime signals and -q

Above the standard 31, POSIX realtime signals `SIGRTMIN`…`SIGRTMAX` (34–64 on glibc; 32/33 are reserved by NPTL) queue instead of collapsing: send ten `SIGRTMIN` to a blocked process and it receives ten. Procps `kill -q <value>` delivers through `sigqueue(3)`, attaching an integer payload the handler reads from `siginfo_t` — the shell-side end of a mechanism that, without a cooperating handler, behaves like an ordinary kill.

### What SIGKILL does and does not clean

```
kernel reclaims at SIGKILL:        NOT reclaimed/repaired:
✓ memory, file descriptors         ✗ SysV IPC objects (need ipcrm)
✓ flock/fcntl file locks           ✗ pidfiles, temp files
✓ record locks on process death    ✗ network connections (RST/timeout)
✓ (child) zombie adoption by init  ✗ filesystem state mid-write
                                   ✗ the children it leaves behind
```

This asymmetry is why runbooks say `TERM` first: programs convert the *request* into an orderly version of what the kernel would otherwise do crudely.

### Graceful termination is a protocol

```
kill <pid>          # SIGTERM: handler may save state, close files, exit
   │  no exit within your patience window?
   ▼
kill <pid>          # re-check liveness: kill -0 <pid> || still-alive
   │
   ▼
kill -9 <pid>       # SIGKILL: kernel reclaims memory, no handler runs,
                    # tmpfiles/sockets/locks left as-is
```

Well-written services trap `TERM`; escalation exists for the ones that ignore it.

## Options That Matter

| Option | Effect |
| --- | --- |
| `<pid>...` | One or more targets: pids, `0`, `-1`, or `-PGID` |
| `-<signal>` | Compact form: `kill -9`, `kill -HUP`, `kill -USR1` |
| `-s, --signal <signal>` | Signal by name or number (`-s TERM`, `-s 15`) |
| `-q, --queue <value>` | Deliver via `sigqueue(3)` with an integer payload (recent procps) |
| `-l, --list[=<sig>]` | List signal names, or convert a number to a name / name to a number |
| `-L, --table` | Aligned name/number table (procps extension) |

Bash-builtin-only extras: `-n <num>` (numeric spec), `%jobspec` targets, and `kill -l $exit_status` decoding a wait status to a signal name.

## Usage Patterns

```bash
# Graceful stop, then verify, then escalate
kill 1234
sleep 5
kill -0 1234 2>/dev/null && kill -KILL 1234

# Reload a daemon's configuration (the HUP convention)
sudo kill -HUP "$(pidof sshd)"

# Ask nginx to reopen log files after logrotate moved them
sudo kill -USR1 "$(cat /run/nginx.pid)"

# Liveness probe that never changes process state (0 = no signal sent)
kill -0 "$pid" 2>/dev/null && echo alive || echo gone

# Terminate an entire background pipeline (its process group)
kill -- -"$pgid"

# Suspend and resume a CPU hog
kill -STOP "$pid"; ...; kill -CONT "$pid"

# Shell job control via the builtin
kill %1              # TERM the first background job
kill -l              # list signals (builtin form)

# Signal by exact name for another user's process (or use pkill)
sudo pkill -TERM -u deploy -f myworker   # find+signal; kill needs pids

# Convert exit status 143 (128+15) back to its signal
kill -l 143          # TERM — "the process died from SIGTERM"

# Queue a realtime signal with a value (sigqueue, recent procps)
kill -q 42 --signal RTMIN "$pid" 2>/dev/null || true

# Send TERM to a whole service tree after locating the PGID
PGID=$(ps -o pgid= -p "$pid" | tr -d ' ')
kill -- -"$PGID"

# Graceful shutdown handler: convert TERM into cleanup, then exit
trap 'echo cleaning; rm -f /run/lock/job.lock; exit 0' TERM INT
while :; do sleep 1; done     # until something kills us

# Escalation ladder in a stop script (name-based, portable)
kill -s TERM "$pid"; for i in 1 2 3 4 5; do kill -0 "$pid" 2>/dev/null || exit 0; sleep 1; done
kill -s KILL "$pid"

# Number-to-name conversions without memorizing the table
kill -l TERM    # 15
kill -l 15      # TERM

# Kill children of a PID (its direct descendants) when no group id exists
pkill -TERM -P "$pid"

# Test what your shell would do: builtin or binary?
type -a kill
kill --version 2>/dev/null || echo "builtin has no --version"

# Backgrounded pipeline: kill its jobs via the builtin's job table
sleep 300 & sleep 301 & jobs -l
kill %2          # TERM the second background job
```

## Nuances and Gotchas

- **`kill -9` as first resort breaks cleanup.** SIGKILL skips handlers: no fsync, no lock release (file locks do die with the process, but SysV IPC and tmp state linger), no child reaping. Always try `TERM` first, wait, then `KILL`.
- **Some processes ignore even SIGKILL.** Uninterruptible `D`-state tasks (stuck NFS, failing storage) and zombies (already dead, awaiting `wait()` by their parent) cannot be signaled away. `kill -9` on a zombie does nothing — fix the parent.
- **`kill -1` is HUP; `kill -- -1` is a system-wide bomb.** A bare `-1` *pid* operand targets every process you may signal except init and yourself — as root that ends userland. Keep the `--` habit for anything starting with `-`, and never let untrusted strings become pid operands.
- **Signal *names* are portable, numbers are not.** Numbers 1–31 agree on Linux but differ on other Unices (and SIGUSR* placement varies historically). Scripts should use `TERM`, `HUP`, `-s TERM`.
- **`SIG` prefix optional; prefer names over numbers.** `kill -TERM`, `kill -term`, and `kill -s SIGTERM` all resolve (procps strips the prefix and is case-insensitive). Numbers are compact but not portable across Unices — names survive renumbering.
- **Exit status is all-or-nothing:** 0 only if signaling *every* listed target succeeded; 1 if any target was missing or protected. That makes `kill -0 $pid` a cheap "may I signal it / does it exist" probe.
- **Builtin vs binary drift:** procps `kill` has `-L` and `-q`; the bash builtin has `-n` and `%jobs`. `kill -l 143` decodes to `TERM` in bash but procps expects `-l <sigspec|exit_status>` similarly — verify in your shell, not by memory.
- **Children are not inherited targets.** Killing a parent orphans children to init; killing a process group (`kill -- -PGID`) is the way to take down a tree. `pkill -P` and `setsid`-aware wrappers exist for gnarlier trees.
- **`kill 0` is a group bomb in scripts:** it signals the *caller's own* process group — under cron/systemd that can be your whole job, not the daemon you meant.
- **Exit status 143 is 128+signal**, not an exit code the program chose. Shell conventions (`$?` after a signaled child) and `wait`-based tooling decode it; log collectors that treat 143 as "app error" mislabel SIGTERM restarts.
- **`pkill`/`killall` match by name — different trust model.** `kill` targets pids you have already verified; pattern tools can match an unlucky process (a user named `deploy` running `vim` while you `pkill -f deploy`). Prefer explicit pids in automation, or anchor patterns (`-x`, `-f` with full path).
- **Signal delivery is not synchronization.** A process may receive your TERM while holding a lock mid-operation; anything needing ordering (flush then stop) belongs in the handler or in a supervisor that waits (`TimeoutStopSec`).
- **Permissions:** you may signal processes whose real/effective uid you share; `sudo` otherwise. `kill -0` distinguishes "doesn't exist" from "exists but you may not signal" only by errno, not by exit code (both exit 1).

## Exit Status

- `0` — a signal was successfully sent to every listed target (for `kill -0`, all targets exist and are signalable).
- `1` — failure: unknown or protected pid, invalid signal spec, usage error. With several pids, one failure fails the whole invocation.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`bash`](../../shell/bash.md) — the builtin `kill`, job control (`%1`), and `trap` handlers for graceful shutdown.
- [`process-management`](../../admin/process-management.md) — signals, process states, and `ps`/`pgrep`/`pkill` in context.
- [`systemd`](../../admin/systemd.md) — how service managers deliver TERM/KILL (`KillMode`, `TimeoutStopSec`).
- [`flock`](./flock.md) — locks that survive or die with signaled processes; the cleanup semantics behind SIGKILL fear.
- [`internals`](../../internals.md) — signal delivery, pending/masked signal queues, and process-group mechanics.

## Interview Questions

### Q: On Debian, why can `kill --version` show "procps" while the collection is util-linux?

Three `kill(1)` implementations coexist historically: the shell builtin, procps-ng's `/usr/bin/kill`, and util-linux's own (not installed by Debian bookworm; `/usr/bin/kill` belongs to procps). Interactive use resolves to the builtin; `env kill` or scripts with `PATH` manipulation reach the binary. Core behavior is POSIX-aligned, but extensions differ (`-L`/`-q` in procps, `-n`/jobspecs in bash).

### Q: Why is `kill -9` discouraged as the default, and when is it *required*?

SIGTERM lets a process run cleanup handlers — flush buffers, remove pidfiles, notify peers, reap children. SIGKILL is kernel-immediate: data in flight is lost and resources dangle. It is required when a process traps/ignores TERM and must not be allowed to continue, or when a stuck process blocks a filesystem operation (after confirming it is not in uninterruptible D state, where even KILL waits).

### Q: Explain the exit status of `kill -0 1 999999` and how you would probe liveness correctly.

Procps `kill` signals every listed pid and returns 1 if any fails — pid 1 exists but 999999 does not, so the whole call exits 1 even though nothing was "wrong" with pid 1. Correct probing is per-pid: `if kill -0 "$pid" 2>/dev/null; then ...`. Note `kill -0` sends no signal; it only performs the permission/existence check, so it can report "exists and I may signal it" — not "is healthy".

### Q: What is the difference between `kill -STOP` and SIGTSTP, and why does Ctrl-Z generate the latter?

SIGSTOP (19) is kernel-imposed and uncatchable — a supervisor's pause. SIGTSTP (20) is the interactive request that terminals send on Ctrl-Z; programs may catch it to tidy up before stopping. Both resume with SIGCONT. Interviewers probe whether you know job-control signaling is layered: terminal → SIGTSTP → shell marks the job stopped → `fg` sends SIGCONT.

### Q: A process group has a runaway child that re-spawns. How do you stop the whole tree?

Find the process group (`ps -o pgid= -p <pid>`) and `kill -- -PGID` to hit every member at once, or signal the session leader. If something re-forks into new groups, escalate to the parent (systemd unit, supervisor script) — `systemctl stop` with `KillMode=control-group` is the robust production answer, since the manager kills the entire cgroup, not just the leader.

### Q: Exit code 143 from a command — what happened and how do you confirm?

128 + signal number means the process died from a signal; 143 = SIGTERM, typically from `timeout`, an orchestrator's stop, or an operator. Confirm with the signal table (`kill -l 143` → TERM) and correlate with logs. Bash reports `SIGNAL` in `$?`-derived statuses; traps and `wait` can recover which signal fired. Knowing the 128+n convention turns mysterious nonzero exits into diagnoses.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/kill.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
