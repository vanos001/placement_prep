# tty — print the filename of the terminal connected to stdin

## Overview

`tty` answers one question: *is standard input a terminal, and if so, which
one?* With no arguments it prints the device filename (`/dev/pts/3`,
`/dev/ttyS0`, ...) of the terminal attached to its stdin, or the words
`not a tty` on stderr with exit status 1 when stdin is something else — a
file, a pipe, a socket, or nothing at all.

It ships in the Debian `coreutils` package at `/usr/bin/tty` and descends
from early Unix. It is POSIX-standardized. In scripts its exit status is
worth more than its output: `tty -s` is the classic "am I running
interactively?" probe, the portable alternative to bash's `[ -t 0 ]` test.

Confusion comes from the overloading of the word: `tty` the command, the
`/dev/tty*` device family it names, and the controlling-terminal concept
from `posix_openpt`/`setsid` discussions all share the name. The command
itself is a two-syscall wrapper: `isatty(0)` for the decision and
`ttyname_r(0)` for the filename.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/tty` |
| First appeared / lineage | Unix v7 era; in GNU coreutils |
| Standards | POSIX.1-2017 |

## Synopsis

```text
tty [OPTION]...
```

```bash
tty          # print the terminal name of stdin, or "not a tty"
tty -s       # print nothing; exit status only
tty < /dev/tty   # ask about the controlling terminal regardless of redirection
```

## How It Works

The kernel tags each open file description with a device; for terminal
devices that device has a name in `/dev` (modern sessions allocate
`/dev/pts/N` pseudo-terminals). `tty` calls `isatty(3)` on file descriptor 0
and, when the answer is yes, `ttyname(3)` to render the name:

```bash
$ tty                  # in an interactive terminal
/dev/pts/0
$ tty < /etc/hostname  # stdin redirected from a file
not a tty
$ echo $?
1
$ echo hi | tty        # stdin is the pipe
not a tty
```

The decisive detail is that **stdin is the only thing examined**. Redirect
stdout, stderr, or run `tty` at the end of a pipeline and its answer still
depends solely on fd 0. Scripts in cron jobs, CI runners, and containers
have no controlling terminal at all, and `tty` reports that consistently.

`-s` (silent/quiet) suppresses the filename and the `not a tty` message,
leaving pure exit-status semantics — which is what makes it composable in
conditionals:

```bash
$ tty -s < /dev/null; echo $?
1
```

The filename `tty` prints is also identity: two processes sharing a
terminal share the same name, which is how `who`, `w`, and `pkill -t pts/0`
correlate sessions with devices.

## Options That Matter

| Option | Effect |
|---|---|
| `-s`, `--silent`, `--quiet` | Print nothing; report through exit status only |

No other options exist — the tool is intentionally minimal. Anything more
elaborate (window size, termios settings) belongs to `stty`.

## Usage Patterns

```bash
# Interactive guard at the top of a script
if tty -s; then
    echo "running interactively"
else
    echo "non-interactive: assuming defaults" >&2
fi
```

```bash
# Only prompt when a human is present; default otherwise
if tty -s; then read -r -p "proceed? [y/N] " a; else a=n; fi
```

```bash
# Which terminal am I on? (session identity in logs)
echo "$(whoami) on $(tty)"
```

```bash
# Portable shell spelling of bash's [ -t 0 ]
tty -s && echo stdin is a terminal
```

```bash
# Force a TTY for programs that demand one, then verify
ssh -t admin@host 'tty'    # prints /dev/pts/N on the remote side
```

```bash
# Detect accidental pipeline use of an interactive-only tool
tty -s || { echo "refusing to run in a pipeline" >&2; exit 1; }
```

```bash
# Ask about the controlling terminal even inside a pipeline
find . | xargs echo | tty < /dev/tty
```

```bash
# Log which pts a long job ran on for later pkill -t targeting
echo "started on $(tty) at $(date)" >> /var/tmp/job.log
```

## Nuances and Gotchas

- **stdin, not "my terminal".** `tty | cat` prints `not a tty` because the
  pipeline replaces fd 0. The reflex fix is `tty < /dev/tty`, which asks
  about the session's controlling terminal instead of the inherited stdin.
- **`not a tty` goes to stderr** — redirect `2>/dev/null` if the message
  would pollute captured output; `tty -s` avoids it entirely.
- **`tty -s` vs `[ -t 0 ]`**: equivalent for fd 0, but the builtin `[ -t 1 ]`
  can test other descriptors (stdout, stderr) while `tty` cannot. bash also
  offers `[ -t 0 ]`; POSIX sh always has `tty -s`.
- **Containers and cron have no controlling terminal.** `docker exec -it`
  allocates one, `docker exec` does not; CI logs routinely contain `not a
  tty` from scripts that forgot this. Design scripts to *default* their
  behaviour rather than require a TTY.
- **`ssh host tty` prints nothing** unless a TTY is allocated (`ssh -t`),
  because the remote command's stdin is not a terminal by default. This is
  a frequent "works interactively, fails in automation" root cause.
- **Exit 1 is "not a terminal", not an error.** Under `set -e`, a bare
  `tty -s` in a non-interactive context aborts the script — same class of
  trap as a failing `test` outside a condition.

## Exit Status

| Status | Meaning |
|---|---|
| 0 | stdin is a terminal (name printed unless `-s`) |
| 1 | stdin is not a terminal ("not a tty" on stderr) |
| 2 | Invalid arguments (unknown option) |
| 3 | Write error while printing the result |

Statuses 0/1 are the POSIX contract; 2 and 3 are documented GNU extensions
to it.

## Related Commands

- [`stty`](./stty.md) — change what `tty` merely names: speeds, echo, special characters.
- [`test`](./test.md) — `[ -t 0 ]`, the builtin spelling of the same question.
- [`who`](./who.md) — maps terminal names (`LINE` column) back to logged-in users.
- [`users`](./users.md) — the login list behind those same utmp terminal records.
- [coreutils collection](./overview.md) — sibling GNU coreutils pages.

## Interview Questions

### Q: What exactly does `tty` examine, and why does `tty | cat` report failure?

It examines file descriptor 0 — stdin — via `isatty(3)`. In `tty | cat`
the shell has already connected `tty`'s stdin to the pipe, so the answer is
"not a terminal" regardless of the grandparent context. Asking about the
session's controlling terminal instead requires `tty < /dev/tty`. The
design point: `tty` answers "what is connected to *my* stdin", not "does my
process have a terminal somewhere".

### Q: How do you write a script that behaves differently when run interactively vs from cron?

Probe once at startup: `if tty -s; then ... fi` (or `[ -t 0 ]` in bash), and
fall back to defaults, non-prompting behaviour, and stderr-only logging in
the non-interactive branch. The important discipline is that the
non-interactive path must be complete and safe by itself — cron, CI, and
systemd have no TTY, so any code path requiring one will fail there in
ways that are hard to reproduce.

### Q: Why does `ssh host tty` print nothing while `ssh -t host tty` prints a device?

Without `-t`, ssh does not allocate a pseudo-terminal on the remote side;
the remote command's stdin is a pipe, so `tty` answers "not a tty". `-t`
(forces allocation) or `-tt` (forces even when stdin is not a TTY) creates a
pts, and `tty` then reports its name. This distinction is the root cause of
many "prompt breaks only in automation" situations, including sudo's
`requiretty`-style behaviours.

### Q: What are the documented exit statuses of `tty` and why is status 1 not an error?

0: stdin is a terminal; 1: it is not; 2: bad arguments; 3: write error.
Status 1 is a *query result*, not a failure — the question "is this a
terminal?" was answered negatively. That is why `tty -s` composes cleanly
in `if` conditions and `&&` chains, and why scripts under `set -e` must
place it in condition position rather than as a bare command.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/tty.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
