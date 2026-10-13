# setsid — run a program in a new session

## Overview

`setsid` starts a program in a brand-new *session*: the child becomes a
session leader with its own process-group ID, and (unless asked
otherwise) it loses the controlling terminal. This is the mechanism that
shields a process from terminal-wide signals — most notably the SIGHUP
delivered to a session when its terminal closes — which is why `setsid`
is the standard tool for launching long-running helpers from scripts and
shells. It ships with the `util-linux` package (Debian bookworm) at
`/usr/bin/setsid`.

`setsid` is often confused with `nohup` (keeps the process in the same
session, only ignores SIGHUP and redirects stdout), with the shell's `&`
(backgrounds the job but keeps the session and controlling terminal),
and with `disown` (removes the job from the shell's job table, session
unchanged).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/setsid |
| First appeared / lineage | long-standing util-linux tool wrapping the POSIX `setsid(2)` call |
| Standards | None as a command; the underlying syscall is POSIX |

## Synopsis

```
setsid [options] <program> [<argument>...]
```

Common one-line forms:

```
setsid ./daemon.sh               # new session, detach, return at once
setsid -w ./job.sh               # ... but wait and propagate exit status
setsid -f cmd                    # force a fork first
setsid -c ./interactive-helper   # keep the controlling terminal
```

## How It Works

### The syscall's one quirk drives the design

`setsid(2)` fails with `EPERM` if the calling process is already a
process-group leader. Interactive shells put each pipeline in a new
process group, so a directly launched `setsid` usually *is* a group
leader — and must fork before the syscall can succeed. `setsid(1)`
encapsulates this dance:

- If the caller is not a group leader, it calls `setsid(2)` in place and
  execs the program — no extra process.
- If it is (or `--fork` is given), it forks; the child performs the
  syscall and execs; the parent exits, orphaning the child.

Either way the program ends up with `SID == PID == PGID` — a fresh
session whose only member is the new program.

Observed on this system (`ps` before and after):

```bash
$ ps -o pid,ppid,pgid,sid,tty,comm -p $$
  PID  PPID  PGID   SID TT       COMMAND
28646 28644 28646 28646 ?        bash
$ setsid -w sh -c 'ps -o pid,ppid,pgid,sid,tty,comm'
  PID  PPID  PGID   SID TT       COMMAND
28648 28646 28648 28648 ?        sh
```

The child's SID equals its own PID: a new session. With `--fork` the
child is additionally orphaned to PID 1:

```bash
$ setsid --fork sh -c 'ps -o pid,ppid,pgid,sid,comm'
  PID  PPID  PGID   SID COMMAND
28925     1 28925 28925 sh
```

### Controlling terminal and stdio

A new session has *no* controlling terminal by default — the program
survives the old terminal closing (no SIGHUP), but its stdin/stdout/stderr
file descriptors may still point at that terminal. `-c/--ctty` makes the
current terminal the controlling terminal of the new session instead
(needed by programs that demand a tty). Clean detachment normally pairs
`setsid` with redirection:

```
              before                         after (setsid)
 old session ── bash(sid A)            old session ── bash(sid A)
    └─ pipeline in pgid B                    (gone)
                                            new session ── prog(sid P)
                                            no controlling terminal
```

### Waiting and status

Without `-w`, `setsid` returns 0 as soon as the program is launched —
you cannot learn how it ended. With `-w`, it waits and reproduces the
child's status, including signal deaths (`128+N`):

```bash
$ setsid -w sh -c 'exit 5'; echo $?
5
$ setsid -w sh -c 'kill -9 $$'; echo $?
137
$ setsid sh -c 'exit 5'; echo $?     # no -w: status is lost
0
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-f, --fork` | Always fork before the `setsid(2)` call — deterministic detachment. |
| `-w, --wait` | Wait for the program and return its exit status (including `128+signal`). |
| `-c, --ctty` | Set the controlling terminal of the new session to the caller's current terminal. |

That is the complete option list (plus `-h`/`-V`) — setsid is
deliberately tiny.

## Usage Patterns

```bash
# Detach a worker from an SSH session; log out right after
setsid /usr/local/bin/nightly-sync.sh >> /var/log/sync.log 2>&1
```

```bash
# Same, but detect failure of the detached job before finishing your script
setsid -w /usr/local/bin/migrate.sh || echo "migration failed"
```

```bash
# Force fork so behavior does not depend on job-control context
setsid -f unshare --mount --map-root-user chroot /srv/jail /init
```

```bash
# Long-running background poller started from a boot script
setsid ionice -c3 nice -n19 /usr/local/bin/indexer --loop
```

```bash
# Keep a controlling terminal for an interactive-ish helper in a new session
setsid -c script -t
```

```bash
# Run a command that must not die with the terminal, but keep tabs on it
setsid -w tcpdump -i eth0 -c 1000 -w /tmp/capture.pcap
```

```bash
# Classic one-shot from cron/at where the caller session goes away
setsid sh -c 'exec /opt/job/run' </dev/null >>/var/log/job.log 2>&1
```

```bash
# Verify detachment before depending on it
setsid -f sleep 60 & pgrep -a sleep | tail -1
```

## Nuances and Gotchas

- **Without `-w` you always get 0.** `setsid cmd` reports success for
  *launching*; if the command immediately fails, your wrapper cannot
  tell. Scripts that care use `setsid -w`.
- **Whether it forks is context-dependent.** From an interactive shell
  with job control the child is a group leader and setsid forks; in
  non-interactive contexts it may not. If your logic depends on process
  relationships (e.g. `$!`), use `--fork` explicitly and account for the
  orphaning.
- **No controlling terminal does not mean no connection to the
  terminal.** stdin/stdout/stderr still reference the old tty unless you
  redirect; writes can fail or interleave, and reading can block on a
  terminal that is about to vanish. Redirect all three for real
  daemons.
- **`-c` only helps if the caller had a controlling terminal**; in cron
  or systemd units there is nothing to attach.
- **It does not change scheduling or identity.** setsid moves the
  process into a new session — nothing else. Pair with `nice`, `ionice`,
  `setpriv` or `su` as needed; each wraps the next.
- **Do not use it to "daemonize" fully.** No double-fork bookkeeping, no
  pidfile, no descriptor hygiene beyond what you redirect, no
  `/dev/null` cwd guarantees. Real service management belongs to
  systemd (which itself uses sessions/cgroups, not setsid).
- **BusyBox ships a compatible setsid** with the same `-c`, `-f`, `-w`
  flags, so embedded initramfs scripts behave the same.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Program launched (without `-w` this is all you get). |
| exit status of the program | With `-w`: the child's status, including `128+N` when it dies from signal N. |
| 127 | The program could not be executed (observed: `setsid: failed to execute ...`). |

## Related Commands

- [`kill`](./kill.md) — sessions and process groups are the units its `-N`/`-g` targeting acts on.
- [`flock`](./flock.md) — companion for "run one detached instance only".
- [`ionice`](./ionice.md) — commonly wrapped by setsid for background I/O-friendly jobs.
- [Process management](../../admin/process-management.md) — sessions, process groups and controlling terminals in depth.
- [bash](../../shell/bash.md) — job control: how the shell creates process groups in the first place.
- [util-linux overview](./overview.md) — collection hub for the other util-linux pages.

## Interview Questions

### Q: Why does setsid sometimes fork and sometimes not?

Because `setsid(2)` fails if the caller is a process-group leader.
Interactive shells make each job a process group, so the setsid binary
itself is typically a leader and must fork first. In non-interactive
contexts it may proceed in place. The `--fork` flag makes the behavior
deterministic; the cost is that the child is orphaned to PID 1.

### Q: How do setsid, nohup and the shell's & differ?

`&` backgrounds a job in the same session and process-group hierarchy —
it still gets SIGHUP when the terminal closes unless the shell
disowns/ignores it. `nohup` ignores SIGHUP and redirects output but
keeps the session and controlling terminal. `setsid` moves the process
into an entirely new session with no controlling terminal, so
terminal-wide signals simply do not reach it. For robust detachment,
combine setsid with explicit redirection of the three standard
descriptors.

### Q: A script runs setsid ./worker && echo done — "done" prints but the worker failed seconds later. Why?

Without `-w`, `setsid` returns 0 once it has launched the program; it
never observes the exit. Use `setsid -w` to propagate the child's exit
status (including `128+signal` for signal deaths), or move the success
logic into the worker itself.

### Q: What does the new session look like from ps?

The program's SID and PGID equal its own PID (`sid == pid == pgid`), its
TTY column is `?` (no controlling terminal), and with `--fork` its PPID
is 1 once the intermediate parent exits. That triple — own sid, no tty,
orphaned — is the fingerprint of a setsid-detached process.

### Q: Why is setsid alone insufficient as a daemonization routine?

True daemons also need their standard descriptors detached (you get only
session detachment otherwise), a stable working directory, pidfile/
single-instance handling, and restart supervision. setsid addresses one
kernel-level concern — session membership — which is why production
systems use service managers (systemd) that handle all of it plus
cgroup accounting, rather than hand-rolled setsid chains.

### Q: When would you use -c/--ctty?

When the program must run in a new session yet still own a terminal —
for example a login-style helper that needs tty ioctls, job control, or
terminal input. Without `-c` the new session has no controlling
terminal, and programs relying on tty semantics (line discipline
signals like SIGINT from ^C) would never receive them.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/setsid.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
