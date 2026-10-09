# nohup — run a command immune to hangup signals

## Overview

When a terminal closes — SSH drop, laptop lid, window shutdown — the
terminal driver sends `SIGHUP` to the foreground process group and the
session leader broadcasts it onward. Background jobs started from an
interactive shell may also receive it depending on shell `huponexit`
settings. `nohup` immunizes a command against that signal: it sets
`SIGHUP` to `SIG_IGN` (ignored) and then `exec`s the command, so the
process outlives the terminal that spawned it.

It is not a session manager and not a daemonizer — it changes exactly one
thing (signal disposition) and one side effect (where output goes). It
ships in the Debian `coreutils` package at `/usr/bin/nohup` and is
POSIX-standardized. You reach for it to keep one-off jobs alive across a
dropped SSH connection; you reach for `tmux`/`screen` when you also want
to *reattach*, and `setsid` when you want to escape the controlling
terminal entirely. It is often confused with `disown` (shell builtin that
removes a job from the job table) and with backgrounding via `&` alone,
which does *not* block SIGHUP.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Man section | 1 |
| Path | `/usr/bin/nohup` |
| First appeared | early AT&T Unix |
| Standards | POSIX 2018 utility |

## Synopsis

```
nohup COMMAND [ARG]...
nohup OPTION
```

Main forms:

```
nohup ./longjob.sh &            # survive terminal close
nohup make > build.log 2>&1 &   # capture output yourself
nohup --version                 # version information
```

## How It Works

`nohup` installs `SIG_IGN` for `SIGHUP` and, because ignored-signal
dispositions survive `exec()`, the child carries the immunity into the
actual program. It then patches the standard file descriptors so the
process does not die or scribble on a terminal that is about to vanish:

```
                 before exec                    after exec
 stdin  tty ───► redirected from an unreadable file (if tty)
 stdout tty ───► append to ./nohup.out  (else $HOME/nohup.out) (if tty)
 stderr tty ───► redirected to stdout   (if tty)
 SIGHUP  default ─────────────────────► SIG_IGN (survives exec)
```

Rules from the implementation, grounded against `nohup --help`:

- stdin, if a terminal, is redirected from an *unreadable* file — reads
  fail with an error instead of hanging on a dead tty.
- stdout, if a terminal, is appended to `nohup.out` in the current
  directory, or `~/nohup.out` if the cwd is not writable.
- stderr, if a terminal, is redirected to wherever stdout went (so both
  streams land in one file).
- If you redirect stdout/stderr yourself, `nohup` leaves them alone —
  which is why the idiom `nohup cmd > log 2>&1 &` is preferred in scripts.

```bash
# No redirection: stdout was a pipe here (not a tty), so no nohup.out is made
$ rm -f nohup.out && nohup true && ls nohup.out
ls: cannot access 'nohup.out': No such file or directory

# Explicit redirection: full control, recommended for scripts
$ nohup sh -c 'echo out; echo err >&2' > o.txt 2> e.txt
$ cat o.txt e.txt
out
err
```

The immunity is one-directional and permanent for the life of the process:
a `SIGHUP` sent explicitly with `kill -HUP` is *also* ignored (that is how
daemons traditionally reload configs — which is why `nohup`'d workers need
`kill -TERM` or newer signals to be controlled).

Exit-status behavior is the standard run-command ladder, documented in the
help text: `125` if `nohup` itself fails, `126` if the command exists but
cannot be invoked, `127` if not found, otherwise the command's own status.

## Options That Matter

| Option | Effect |
|---|---|
| `--help` | Print usage (including the fd-redirect rules) and exit |
| `--version` | Print version and exit |

No behavioral flags exist. Everything `nohup` does is automatic based on
which of the three standard fds are terminals.

## Usage Patterns

```bash
# Long download survives the SSH session dying
nohup rsync -aP big.iso mirror:/srv/isos/ &
```

```bash
# Production-grade: log to a real file, drop stdin
nohup ./etl-worker --once > /var/log/etl-$(date +%F).log 2>&1 < /dev/null &
```

```bash
# Keep output but never block on it
nohup python3 train.py > train.out 2>&1 &
```

```bash
# Belt and suspenders: nohup + disown (shell builtin removes it from the job table)
nohup ./server & disown
```

```bash
# Nightly one-shot from a jump host you're about to log out of
ssh admin@host 'nohup /usr/local/bin/nightly.sh > /tmp/nightly.log 2>&1 &'
```

```bash
# Rebuild something huge, then come back and check
nohup make -j"$(nproc)" > build.log 2>&1 & echo "pid $!"
```

```bash
# Verify immunity: the process ignores an explicit HUP too
nohup sleep 300 & pkill -HUP -f 'sleep 300' && ps -o pid,stat,cmd -C sleep
```

```bash
# Combined with nice for long batch work
nice -n 10 nohup ./reindex.sh > reindex.log 2>&1 &
```

## Nuances and Gotchas

- **`&` alone does not protect anything.** Backgrounded jobs still get
  `SIGHUP` at shell exit when `huponexit` is set (login shells), and the
  terminal teardown can still close their tty fds. `nohup` (or `disown`
  plus redirection) is what makes it survive.
- **`nohup.out` appears wherever the cwd was.** Run it from `/` without
  redirection and you get `/nohup.out` (permission-denied as a normal
  user, silently falling back to `~/nohup.out`). Scripts should *always*
  redirect explicitly.
- **It cannot reattach.** Once started, you interact only through files
  and signals. If you might want to reconnect to the session itself, use
  `tmux`/`screen` from the start; migrating a running `nohup` process
  into one later is not possible.
- **Ignored HUP also blocks legitimate reloads.** Many daemons use
  `SIGHUP` as "reload config"; a `nohup`'d process will ignore that too.
  Control it with `SIGTERM`/`SIGINT`-style signals instead.
- **stderr follows stdout.** Without explicit redirection, both go to
  `nohup.out`. If you wanted only stdout there, redirect stderr somewhere
  real — uncaught tracebacks and logs will otherwise be interleaved.
- **stdin becomes unreadable on purpose.** Anything that tries to prompt
  (apt, installers, `sudo`) will error instead of hanging — usually the
  behavior you want for unattended jobs, a surprise otherwise.
- **It does not create a new session.** The process keeps its controlling
  terminal context and process group; `setsid` is the tool for full
  detachment (new session, no controlling tty). Some supervision setups
  require `setsid` semantics and reject `nohup`'d processes.
- **Not a daemon supervisor.** No restart-on-crash, no PID files, no
  logging rotation. That is systemd units, `supervisor`, or `tmux` +
  tooling territory.
- **`nohup time cmd` pitfall.** `nohup` execs its argument; wrapping
  builtins (`time`, shell keywords) requires `nohup bash -c 'time cmd'`.

## Exit Status

| Code | Meaning |
|---|---|
| command's status | The command ran; `nohup` forwards its exit status |
| `125` | `nohup` itself failed (e.g. cannot write nohup.out or fall back) |
| `126` | COMMAND found but not invocable |
| `127` | COMMAND not found |

## Related Commands

- [`./overview.md`](./overview.md) — GNU Coreutils collection hub.
- [`./nice.md`](./nice.md) — the other common command-prefix wrapper.
- [`./sleep.md`](./sleep.md) — pacing and idle-keeping in long-lived jobs.
- [`./nproc.md`](./nproc.md) — right-size the parallelism of the job you detach.
- [`../../shell/bash.md`](../../shell/bash.md) — job control, `&`, `disown`, and `huponexit`.

## Interview Questions

### Q: What exactly does `nohup` change about the process it starts?

Two things: it sets `SIGHUP` disposition to ignored (`SIG_IGN`), which
survives `exec()` into the target program, and it redirects any of
stdin/stdout/stderr that are attached to a terminal — stdout to
`nohup.out` (append) or `~/nohup.out`, stderr to stdout, stdin from an
unreadable file. It does not fork, daemonize, change sessions, or restart
anything.

### Q: Why does `nohup cmd &` sometimes still produce `nohup.out`, and how do you prevent it?

`nohup` only redirects stdout when it is a terminal. In scripts run under
cron/CI, stdout is usually already a pipe or file, so `nohup.out` never
appears; run interactively with plain `&`, stdout *is* the tty and lands
in `nohup.out`. Prevent it by redirecting explicitly:
`nohup cmd > log 2>&1 &` — then `nohup`'s automatic patching never fires.

### Q: Compare `nohup cmd &`, `cmd & disown`, and `setsid cmd`.

`nohup cmd &` ignores SIGHUP and detaches output from the tty, but keeps
the controlling terminal and job-table entry. `cmd & disown` removes the
job from the shell's job table (so the shell won't HUP it on exit per
`huponexit`), but the process still holds the tty as its terminal —
writes to it can fail or block once the tty is gone. `setsid cmd` starts
a brand-new session with no controlling terminal at all — the cleanest
detachment, and what service wrappers prefer. In practice: quick job,
`nohup`; interactive session you may return to, `tmux`; supervised
service, systemd.

### Q: A colleague says "nohup makes it a daemon." Correct the record.

No. A daemon conventionally forks, `setsid()`s, closes/rebinds the std fds,
and detaches from any terminal, often supervised by init. `nohup` only
ignores one signal and patches std descriptors; the process remains a
child of your shell in your session. Kill it when your session dies? No —
that's the point it survives — but it also never restarts on failure,
logs nowhere useful without redirection, and keeps whatever process group
it had.

### Q: How do you stop a nohup'd process that ignores SIGHUP, and why does this happen?

With `kill -TERM PID` (or `SIGKILL` if it ignores TERM). `nohup` sets
SIGHUP to `SIG_IGN`, and *explicitly sent* HUPs are equally ignored —
there is no distinction between the terminal's HUP and `kill -HUP`. This
collides with programs that treat SIGHUP as "reload config": such
programs cannot be reloaded while nohup'd, another reason `nohup` is a
one-shot tool rather than service infrastructure.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/nohup.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — nohup](https://pubs.opengroup.org/onlinepubs/9699919799/)
