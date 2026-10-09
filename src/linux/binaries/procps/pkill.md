# pkill — signal processes by name or attributes

## Overview

`pkill` is `pgrep` with a payload: instead of printing the PIDs that match a pattern and selection flags, it sends each of them a signal. The default is SIGTERM — the polite request to shut down — not SIGKILL, a distinction that is the heart of every `pkill` discussion worth having. It ships in the `procps` package (Debian bookworm: procps-ng 2:4.0.4) at `/usr/bin/pkill`, built from the same source as `pgrep` and `pidwait`, with byte-identical selection flags.

`pkill` replaces `kill $(pgrep ...)` one-liners and the `ps | awk | xargs kill` pipelines of shell antiquity. It is often confused with `killall` (which matches by exact name and has different semantics — and on Debian comes from psmisc) and with `kill` (takes PIDs, not patterns). The danger profile is the inverse of pgrep's: a wrong `pgrep` prints an extra PID, a wrong `pkill` kills something.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 2:4.0.4) |
| Man section | 1 |
| Path | /usr/bin/pkill |
| First appeared | procps, late 1990s (alongside pgrep) |
| Standards | none; procps-ng convention (Solaris pkill is similar, busybox is a subset) |

## Synopsis

```
pkill [options] pattern
pkill [options] --signal <signal> pattern
```

Common one-line forms:

```
pkill -x nginx                # SIGTERM the exact-name match
pkill -f 'app/worker.py'      # match full command line
pkill -KILL -x stuckproc      # SIGKILL escalation
pkill -HUP -x rsyslogd        # signal as control (reload)
pkill -u alice                # everything of a user (careful!)
pkill -e -x sleep             # echo what gets signalled
```

## How It Works

### Selection, then signal

`pkill` runs exactly the pgrep selection machinery — pattern against process name (or full cmdline with `-f`), AND-combined attribute flags — and then calls `kill(2)` on every surviving match instead of writing PIDs to stdout. There is no intermediate list you can inspect; the query and the action are fused. That fusion is the feature (no PID-reuse races between listing and acting) and the hazard (no preview) — which is why the disciplined workflow is `pgrep` first, then `pkill`:

```
$ pgrep -l -f 'worker.py'      # preview: what WOULD die?
  917 python3 /opt/app/worker.py
$ pkill -f 'worker.py'         # now do it
```

### Signals: name it, number it, or take the default

Three spellings for the signal:

```
pkill -x nginx              # default: SIGTERM (15)
pkill -9 -x nginx           # numeric, BSD-style leading dash
pkill -KILL -x nginx        # signal name, leading dash
pkill --signal=HUP -x nginx # long form; the only spelling accepted
                            # together with other pgrep-mode options
```

Leading-dash signal arguments must come *before* the pattern (`pkill -9 foo`, never `pkill foo -9` — that trailing token becomes part of the pattern... actually the last form makes `foo -9` a two-word pattern operand problem; keep the signal first). The `--signal` long option exists precisely because in pgrep/pidwait compatibility mode a bare `-9` is ambiguous.

SIGTERM is the default because most software has a TERM handler: flush buffers, close sockets, remove pidfiles, tell its supervisor. SIGKILL cannot be caught — no cleanup, no flushing, no child reaping, pidfiles left behind, databases resorting to crash recovery. The `-9` habit produces the exact messes that cause the next outage.

### Escalation pattern: TERM, wait, KILL

The professional shutdown loop gives processes a grace period:

```bash
pkill -x myapp                    # polite TERM
for i in $(seq 1 10); do
    pgrep -x myapp >/dev/null || exit 0   # gone — done
    sleep 1
done
pkill -KILL -x myapp              # escalate only after 10s
```

`pkill --signal 0` is a harmless ping: signal 0 performs no action, so it turns pkill into a pure existence test with pgrep's exit codes.

### The signals that matter in practice

`pkill` can deliver anything `kill(2)` can, but a handful cover nearly all real usage — and each has a distinct contract (numbers shown for x86-64; some architectures renumber the real-time-adjacent signals):

| Signal | Number | Effect | Caught by default handlers? |
| --- | --- | --- | --- |
| `TERM` | 15 | polite shutdown request | yes — cleanup, then exit |
| `KILL` | 9 | immediate destruction by the kernel | no — uncatchable, unblockable |
| `HUP` | 1 | conventionally "reload config" for daemons | yes |
| `INT` | 2 | what Ctrl-C sends | yes |
| `QUIT` | 3 | terminate + core dump | yes |
| `USR1`/`USR2` | 10/12 | application-defined (reopen logs, rotate, debug dump) | yes — and apps without a handler *die* |
| `STOP`/`CONT` | 19/18 | freeze / resume the process (job control) | no — but reversible, unlike KILL |
| `0` | 0 | no signal sent; pure existence check | n/a |

The `USR1`-kills-unhandled-processes row is its own interview trap: signaling a process that never installed a USR1 handler terminates it — daemon control via USR signals assumes you know the target's signal contract.

### Signals and permissions

`kill(2)` enforces ownership: non-root may signal only processes with the same effective UID (plus the usual capabilities exception for root, CAP_KILL). A non-root `pkill -x sshd` matches, attempts, gets EPERM on every entry, and exits 1 — matches without delivery are failure. Under `sudo` the same command succeeds and *hits every sshd on the box*, which is why previewing with pgrep before escalating privileges is not paranoia but procedure.

### Counting — and why -c still signals

`-c` suppresses the PID output and prints the number of matching processes — but it does **not** suppress the signal. `pkill -c` is a full kill run with a count at the end:

```
$ sleep 300 & sleep 301 & pkill -c -x sleep
2                      # both sleeps matched, were signalled, and died
```

The man page is explicit: for pkill and pidwait the count is the number of *matching* processes, not the number successfully signalled or waited for. Anyone reaching for `pkill -c pattern` as a "dry run" gets a live-fire exercise instead — the safe rehearsal is `pgrep -l pattern`, or `pkill --signal 0 pattern` which matches and checks permissions without delivering anything.

### The self-preservation rules

Two invariants worth knowing cold:

- `pkill` **never signals itself** — no self-match suicide.
- It **will signal its own ancestors** if they match: `pkill -f bash` from an interactive shell kills your own terminal's shell, and `pkill -f sshd` can sever the session you typed it into. Scope patterns (`-x`, `-u`, `-t`) and lean on `-A` (`--ignore-ancestors`) in scripts.

### Exit codes carry the outcome

Because the action can fail per-process (not owner: EPERM; already a zombie; vanished mid-scan), pkill's success requires *at least one successful signal*, not just a match. This differs subtly from pgrep, where a match alone suffices.

## Options That Matter

### Signal selection

| Option | Effect |
| --- | --- |
| (none) | SIGTERM (15) — the default |
| `-\d+` (e.g. `-9`) | numeric signal, leading dash |
| `-NAME` (e.g. `-KILL`) | signal by name, leading dash |
| `--signal SIG` | long form; required in pgrep/pidwait-compat contexts |
| `-q, --queue VALUE` | send a real-time signal with a value (sigqueue) |
| `-H, --require-handler` | only signal processes that have a userspace handler for the signal |
| `-e, --echo` | print each match as it is signalled: `sleep killed (pid 4711)` |
| `-c, --count` | print the count of matching processes — but still signal them |
| `-0` (signal zero) | existence probe — matches counted, nothing delivered |

### Selection (identical to pgrep)

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
| `-F, --pidfile FILE` | read PIDs from a pidfile (skip pattern matching) |
| `-L, --logpidfile` | fail if the pidfile is not locked |
| `-A, --ignore-ancestors` | exclude pkill's own ancestors |
| `--ns PID` / `--nslist` | namespace-based selection |
| `--cgroup LIST` | cgroup v2 membership |

## Usage Patterns

```bash
# Preview, then terminate — the disciplined pair
pgrep -a -f 'celery.*worker' && pkill -f 'celery.*worker'

# Graceful reload of a daemon (HUP as a control signal)
pkill -HUP -x rsyslogd

# Kill only one user's runaway processes
pkill -KILL -u training-user -x stress

# Kill by exact name — avoid matching ssh-agent when you mean ssh
pkill -x ssh-agent

# Kill children of a specific parent (process-tree cleanup)
pkill -TERM -P "$(pgrep -x supervisord)"

# Escalation: TERM, wait, then KILL (see the loop above)
pkill -x myapp; sleep 5; pkill -KILL -x myapp

# Count matches — WARNING: -c still signals; this killed two sleeps
pkill -c -x sleep

# Echo each kill for the audit log
pkill -e -x sleep

# Clear a dead session's processes by terminal
pkill -t pts/3

# Signal zero as an existence check with pkill's exit codes
pkill --signal 0 -x myapp && echo running || echo stopped

# Only processes that can actually handle it (newer procps-ng)
pkill -H --signal USR1 -x mydaemon

# Freeze, inspect, resume — debugging without killing
pkill -STOP -x myapp && ps -o pid,stat,wchan,cmd -C myapp && pkill -CONT -x myapp

# Roll a log file open across every worker of a service
pkill -USR1 -f 'nginx: worker'

# Signal exactly one newest instance (e.g. stop the latest of many)
pkill -n -x backup.sh

# Existence check scoped to a user, no output, exit-code only
pkill --signal 0 -u ci-runner -x java

# Terminate a leftover watchdog from a finished CI job
pkill -e -f '/opt/ci/watchdog.sh' || echo "no watchdog found"

# Kill everything in a session left behind by a broken SSH login
pkill -KILL -s 4711

# Stop only workers that have been stuck for over an hour
pkill -O 3600 -f 'app/worker'
```

## Nuances and Gotchas

- **Default is SIGTERM, and that matters.** `-9` skips handlers entirely: no log flush, no socket close, no pidfile removal, no child reaping, crash-recovery on next start. Escalate to KILL only after TERM fails within a grace period.
- **`-9` cannot kill D-state processes either.** A process parked in uninterruptible IO ignores every signal; the only exit is IO completion or reboot. Killing "-9 everything" during storage incidents changes nothing.
- **Pattern-too-broad is the classic outage.** `pkill -f test` matches your integration tests, your editor's cmdline, and possibly the deploy script doing the killing. Prefer `-x` for names, anchor `-f` regexes (`'^/opt/app/'`), and preview with `pgrep -a`.
- **`pkill -f` matches its own shell's cmdline.** A script that runs `pkill -f deploy.sh` from `bash deploy.sh` kills its own parent. `-A` (`--ignore-ancestors`) exists for exactly this.
- **Order of arguments matters.** `pkill -9 foo` is signal-then-pattern; `pkill foo -9` treats `-9` oddly (as part of pattern parsing) — keep the signal immediately after the options, pattern last. When composing programmatically, use `--signal=NAME`.
- **`killall` is a different tool.** Debian's `killall` (psmisc) matches exact names and has `-i` interactive mode; busybox `killall` differs again. `pkill -x` is the portable procps spelling of "by exact name".
- **Zombies match but cannot die again.** A Z-state process still appears in /proc and can match; signalling it is a no-op, though it still counts as a "successful" signal for exit-status purposes in practice.
- **`-c` is not a dry run.** It prints the count of matching processes *and still signals them* — the count covers matches, not successful deliveries. The safe rehearsal of a kill policy is `pgrep -l` (see the set) or `pkill --signal 0` (test permissions, deliver nothing).
- **Permissions leak through silently.** Signalling another user's process fails with EPERM per-process; pkill reports nothing per-PID unless `-e`, and exits 1 if *nothing* could be signalled. Scripts checking "did it work" must use the exit code, not stdout.
- **pidfiles beat patterns for daemons.** `-F /run/app.pid` targets the authoritative PID; `-L` additionally insists the pidfile is locked, filtering out stale files whose PID was recycled.
- **busybox pkill is a subset.** No `-r`, `-O`, `-A`, `--ns`, `--cgroup`, and signal parsing can differ; keep portable scripts to `-f -x -u -P` plus explicit signal names.
- **`-t` takes the tty name, not the device path.** `pkill -t pts/3` is right; `pkill -t /dev/pts/3` is not — the `/dev/` prefix form matches nothing and exits 1.
- **`-n`/`-o` reduce the kill set to one process** — newest or oldest by start time. Useful for "kill the newest duplicate", but verify with `pgrep -n -l` first: start-time ties are resolved arbitrarily.
- **`--signal 0` still exercises selection and permissions** — it reports "would I match, and could I signal?" without touching the target. That makes it the cheapest safe rehearsal of a pkill policy before replacing `0` with `TERM`.

## Exit Status

| Code | Meaning |
| --- | --- |
| `0` | at least one process matched **and** was successfully signalled |
| `1` | no processes matched, or none could be signalled |
| `2` | syntax error in the command line |
| `3` | fatal error (out of memory, etc.) |

Note the stricter zero than pgrep's: a match that cannot be signalled (EPERM, vanished) is failure here.

## Related Commands

- [`pgrep`](./pgrep.md) — the same selection machinery without the payload; use it to preview what pkill will hit.
- [`pidwait`](./pidwait.md) — wait until matches exit; pairs with the TERM-then-wait-then-KILL escalation.
- [`pidof`](./pidof.md) — literal exact-name lookup for `kill $(pidof foo)` scripting.
- [`ps`](./ps.md) — inspect states (D, Z) that predict whether the signal can work at all.
- [`overview`](./overview.md) — procps collection hub.
- [Process management](../../admin/process-management.md) — signal semantics, termination, and cleanup context.

## Interview Questions

### Q: Why is the reflexive `pkill -9` considered an anti-pattern?

SIGKILL cannot be caught, so the process skips every shutdown path: buffers and logs are not flushed, sockets are not closed gracefully, pidfiles and temp files survive, children are left orphaned, and stateful software must run crash recovery on restart. SIGTERM gives the process the chance to clean up, and the correct pattern is TERM, wait a grace period, then KILL as escalation. `-9` is a last resort, not a habit — and on D-state processes it does nothing anyway.

### Q: You run `pkill -f worker` on a box and your SSH session drops. What happened?

The pattern matched the full command line of an ancestor: your session's processes (sshd child, the shell) have `worker` somewhere in their cmdline — for instance if the command itself contains the word. `pkill -f` matches arguments too, and it happily signals its own ancestry. Prevention: exact-match with `-x`, anchor `-f` patterns, add `-A` to ignore ancestors, and preview with `pgrep -a -f` before arming the signal.

### Q: What does `pkill -e` change, and why is it valuable in automation?

It echoes each signalled match to stdout in the form `name killed (pid N)`, converting an otherwise silent action into an audit trail. In automation this is the difference between "something got a TERM, presumably" and a log line naming every PID and process affected — invaluable when reconstructing what a cron job or rollback script actually killed.

### Q: How would you safely stop a process group of workers with a timeout?

Preview with `pgrep -a -f` scoped tightly (anchored regex, `-u` if applicable), then `pkill -TERM -f 'app/worker'`, poll with `pgrep -f` (or `pidwait -f`) inside a timeout loop, and only then `pkill -KILL -f 'app/worker'` for stragglers. Using `-P` against a known supervisor PID is even tighter than pattern matching. The exit code 0 confirms at least one signal was delivered; exit 1 means nothing matched or nothing could be signalled — both should be logged, not assumed.

### Q: What is the difference between pkill's and pgrep's exit code 0, and why does the distinction exist?

pgrep exits 0 when one or more processes merely matched; pkill exits 0 only if at least one match was *successfully signalled* — a match that fails to receive the signal (EPERM on another user's process, or it vanished mid-scan) yields exit 1. The distinction exists because pkill's job is the action, not the report: a count of matches that received nothing is operationally a failure.

### Q: How do you reload a daemon's configuration with pkill, and what makes HUP the conventional choice?

`pkill -HUP -x daemonname`. HUP became the reload convention because daemons detached from terminals would otherwise never receive it — SIGHUP historically meant "terminal hung up", an event a daemonized process cannot experience, so authors recycled it as "re-read your config". The caution: HUP-as-reload is a convention, not a guarantee; some programs treat HUP as terminate. Know the target's documented signal contract (its man page, or `kill -l` cross-referenced with its docs) before wiring HUP into automation.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/pkill.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
