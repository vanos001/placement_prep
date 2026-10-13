# pinky — lightweight finger: who is logged in

## Overview

`pinky` is GNU's minimal reimplementation of the classic `finger`
utility: it reads the `utmp` database (`/var/run/utmp` on Debian) and
prints who is currently logged in, where from, and since when — with none
of finger's network features, `.plan`/`.project` file exposition, or
remote-query capability. The whimsical name is deliberate: a *lighter*
finger.

It ships in the Debian `coreutils` package at `/usr/bin/pinky` as a GNU
original (1990s, no POSIX spec). Its lasting value is threefold: a
column-configurable `who` (the short format can drop or keep individual
columns via flags), a long format for one user that shows real name,
home directory, and shell from `passwd`, and a safe default — unlike
`finger`, it never reads users' `~/.plan` or `~/.project` files unless
asked (`-l` without `-h`/`-p`).

It is often confused with `who` (same utmp, fixed format), `w` (adds
per-process command lines, in procps), and `finger` (its heavyweight
ancestor, long gone from default installs).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Man section | 1 |
| Path | `/usr/bin/pinky` |
| First appeared | GNU coreutils (1990s) |
| Standards | GNU extension — not POSIX |

## Synopsis

```
pinky [OPTION]... [USER]...
```

Main forms:

```
pinky                 # short format: everyone in utmp
pinky alice           # short format, filtered to one user
pinky -l alice        # long format: real name, dir, shell for one user
pinky -q              # quiet short: logins only, no headers
```

## How It Works

Session-creating programs (`login`, `sshd`, display managers) append a
record to `/var/run/utmp` for every session: user name, tty line, remote
host, login time, PID. `pinky` walks that file, and for the long format
augments records with `passwd`/`gecos` data (real name, home, shell) and
optionally the user's `~/.project`/`~/.plan` files.

```
 login/sshd ──write──► /var/run/utmp ──read──► pinky
                         (user, tty, host,
                          time, pid)            ┌─ short: table of sessions
                                                ├─ long (+passwd/gcos):
                                                │   name, dir, shell, plan
```

The short format's columns and their control flags:

```
 Login    Name          TTY   Idle  When       Where
 ───────  ────          ───   ────  ────       ─────
 alice    Alice Doe     pts/0  00:01  Mon 09:00  10.0.0.5
 └        └             └      └      └          └
 -w drops -w drops      -i     -q     -q         -i drops; -q drops
```

On a box with no active logins (a fresh container, most CI runners), utmp
is empty and pinky prints just the header row and exits 0:

```bash
$ pinky
Login    Name                 TTY      Idle   When         Where
$ echo $?
0
```

The long format requires at least one USER argument and prints one block
per user, pulling the real name, home directory, and shell from `passwd`,
plus plan/project files unless suppressed:

```bash
$ pinky -l alice
Login name: alice                       In real life:  Alice Doe
Directory: /home/alice                  Shell:  /bin/bash
```

## Options That Matter

| Option | Effect |
|---|---|
| `-s` | Short format (default) |
| `-l` | Long format for the named USERs (adds home dir, shell, plan/project) |
| `-b` | Long format: omit home directory and shell |
| `-h` | Long format: omit the `~/.project` file |
| `-p` | Long format: omit the `~/.plan` file |
| `-f` | Short format: omit the column headings |
| `-w` | Short format: omit the full-name column |
| `-i` | Short format: omit full name and remote host columns |
| `-q` | Short format: omit full name, remote host, and idle time |
| `--lookup` | Resolve remote hostnames via DNS (default shows raw utmp host field) |

The single-letter flags compose: `pinky -fw` is "just logins, ttys, idle,
when, where" — a deliberately narrow table for scripting or MOTDs.

## Usage Patterns

```bash
# Quick "who is on this box" before rebooting
pinky
```

```bash
# Machine-readable login list for a watchdog script
pinky -q | awk '{print $1}' | sort -u
```

```bash
# Check whether a specific account is currently logged in
pinky alice | grep -q alice && echo "alice is logged in"
```

```bash
# Count active remote sessions (excluding local consoles)
pinky | awk '$NF ~ /\./ {n++} END {print n+0}'
```

```bash
# MOTD-friendly table without headers or full names
pinky -fw
```

```bash
# HR-safe long format: show shell/dir but not users' plan files
pinky -lbp alice
```

```bash
# Resolve where users came from (DNS lookup of the host column)
pinky --lookup
```

```bash
# Poll for a login in a provisioning script
until pinky -q | grep -q bob; do sleep 5; done
```

## Nuances and Gotchas

- **utmp is not an audit log.** Entries vanish at logout and the file is
  small and recycled; for session history use `last` (reads `wtmp`) or
  `journalctl _COMM=sshd`. `pinky` sees *only the present*.
- **Empty output is normal in containers.** No `sshd`/`login` traffic →
  empty utmp → header-only output, exit `0`. Scripts must not assume at
  least one row.
- **Idle time comes from utmp, and many session types never update it.**
  On modern systems the column is often blank or stale; `w` computes
  idle more reliably from tty activity.
- **The `--lookup` DNS query is a latency and privacy footgun.** It makes
  a reverse-DNS call per session and can hang minutes on broken resolver
  setups; also leaks internal hostnames into logs. Use deliberately.
- **Long format reads users' files.** `pinky -l` displays `~/.plan` and
  `~/.project` (unless `-h`/`-p`) — a mild information-disclosure
  consideration on multi-user boxes, and the reason plain `pinky` is the
  safe default.
- **`-l` needs a USER argument.** POSIX-style long format with no
  arguments is an error; the flag set for `-l` mode (e.g. `-b`, `-h`,
  `-p`) is disjoint from short-format trimming flags in intent.
- **Non-POSIX, GNU-only.** Absent from some minimal images; busybox
  builds typically ship `who` but not `pinky`. Portability scripts use
  `who` (POSIX) instead.
- **Column drift under non-ASCII names.** Full-name fields from gecos can
  be wide; parsing pinky's *short* table with awk assumes the `-w`/`-q`
  trims, which is exactly what the flags are for.

## Exit Status

| Code | Meaning |
|---|---|
| `0` | Report produced (even if zero sessions were listed) |
| `1` | Failure: unknown USER, bad option, or unreadable utmp |

## Related Commands

- [`./overview.md`](./overview.md) — GNU Coreutils collection hub.
- [`./logname.md`](./logname.md) — the same utmp database, one session at a time.
- [`./pathchk.md`](./pathchk.md) — validate the filenames plan/project paths produce.

`who` and `w` live outside this collection and are intentionally not
linked here; the hub page `./overview.md` indexes related tooling.

## Interview Questions

### Q: What is pinky, and what did it deliberately leave out of finger?

A minimal, local-only `finger`: it lists current sessions from utmp and,
in long format, adds passwd-derived details. It drops finger's network
protocol, remote queries, and by default the `~/.plan`/`~/.project`
exposition — keeping a "who is logged in" tool that is safe to run
anywhere and cheap to parse. The name signals the relationship: finger,
minus most of the hand.

### Q: How do pinky, who, and w differ?

All three read utmp. `who` (POSIX) prints a fixed session table; `w`
(procps) adds uptime, load averages, and the command each session is
running (from process accounting per tty); `pinky` offers *configurable*
short-format columns via flags plus a finger-style long format with real
name, home, shell, and plan files. Choose `who` for portability, `w` for
"what are they doing", `pinky` for tailored columns or the long view.

### Q: Why does pinky print only headers with exit status 0 in a container?

Because utmp records sessions created by `login`/`sshd`/display managers,
and a container or CI runner usually has none — nobody "logged in", so
the database is empty. Exit `0` is correct: the report succeeded and
happens to contain zero rows. Scripts counting logins must handle the
empty case rather than assuming at least the current user appears.

### Q: What are the security-relevant flags in pinky's long format?

`-h` omits `~/.project` and `-p` omits `~/.plan`, so `pinky -lhp user`
shows identity and shell without exposing user-authored files; `-b`
additionally hides home directory and shell. Since plan/project files are
world-readable by convention and user-controlled in content, systems that
expose long-format output to untrusted parties restrict or trim them —
one reason the default short format never reads user files at all.

### Q: Where does pinky's data come from, and what are its staleness failure modes?

From `/var/run/utmp`, written at session start and updated (ideally) on
activity. Failure modes: entries disappear at logout (no history — that
is `wtmp`/`last`'s job), some session types never update the idle field,
and crashed sessions can leave stale rows. So pinky answers "what does
utmp say right now", which is not always identical to "who is actually at
a keyboard".

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/pinky.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
