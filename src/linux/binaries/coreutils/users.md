# users — print the user names currently logged in

## Overview

`users` prints the login names of users with active sessions on the system,
on a single space-separated line, sorted and deduplicated. It reads the
system's `utmp` database — `/var/run/utmp` by default, or a file given as
an argument — and is the most condensed member of the login-visibility
family: one line, names only, nothing else.

It ships in the Debian `coreutils` package at `/usr/bin/users` and descends
from BSD. It is *not* POSIX-standardized, which matters for the
`#!/bin/sh`-portable crowd: the standardized way to ask the same question is
`who -q`. On busybox-based rescue systems, `users` may be absent while
`who` is present.

The family it belongs to, from terse to verbose: `users` (names),
`who -q` (names plus a count), `who`/`w` (per-session detail with times and
terminals), and `last` (login *history* from `wtmp`). Interviews like asking
where exactly one tool ends and the next begins.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/users` |
| First appeared / lineage | BSD lineage; in GNU coreutils |
| Standards | none — not in POSIX (use `who -q` for standardized output) |

## Synopsis

```text
users [OPTION]... [FILE]
```

```bash
users                    # current logins from /var/run/utmp
users /var/log/wtmp      # same query against the history database
users | wc -w            # quick "how many distinct people are on"
```

## How It Works

Every login session registers a record in the `utmp` database: a struct
containing the username, terminal line, host, login time, and a record type
(USER_PROCESS for live sessions, DEAD_PROCESS for exited ones, BOOT_TIME,
RUN_LVL, and bookkeeping types). `users` walks the file, keeps only the
live user records, extracts the names, sorts them, removes duplicates, and
prints the result on one line:

```text
/var/run/utmp ──▶ [USER_PROCESS records] ──▶ names ──▶ sort -u ──▶ "alice bob carol"
```

Deduplication is the semantics worth internalizing: a user with three SSH
sessions and a console login appears once. What `users` reports is "which
accounts have at least one live login", not "how many sessions exist" —
for session counts you need `who` or `w`.

```bash
$ users
alice bob
$ who
alice    pts/0        2026-07-01 09:12 (10.0.0.5)
bob      pts/1        2026-07-01 09:40 (gateway.corp)
bob      pts/2        2026-07-01 09:41 (gateway.corp)
```

Here `users` prints `alice bob` — bob twice over, but once on the line.
`who -q` would additionally report the session count (`# users=3`).

On minimal systems — fresh containers, chroots, single-user rescue boots —
`utmp` is empty or absent, and `users` prints an empty line and exits 0.
That is correct behaviour, not breakage: no records means no logins.

The FILE argument is the underused half of the tool. Pointing it at
`/var/log/wtmp` (the historical database every login also appends to) turns
"who is logged in" into "who has ever logged in" — the same query the
`last` utility answers with formatting and duration information.

## Options That Matter

| Option | Effect |
|---|---|
| `FILE` | Read login records from FILE instead of `/var/run/utmp` (`/var/log/wtmp` is the common choice) |
| `--help` / `--version` | Standard coreutils informational options |

There are no filtering or formatting options — the tool's value is its
inability to do anything complicated. Anything richer belongs to `who` or
`w`.

## Usage Patterns

```bash
# Quick "is anyone else on this box before I reboot?"
users
```

```bash
# Distinct-user count for a status banner
echo "logged-in users: $(users | wc -w)"
```

```bash
# Check for a specific account before restarting a shared service
users | grep -qw alice || systemctl restart app
```

```bash
# History query: which accounts appear in the wtmp database at all
users /var/log/wtmp
```

```bash
# Set-compare live sessions against an allowlist
comm -23 <(users | tr ' ' '\n' | sort -u) <(sort allowlist.txt)
```

```bash
# In a weekly report, list who was on the machine (from wtmp)
echo "[$(date -I)] active accounts: $(users /var/log/wtmp)" >> report.log
```

```bash
# Trigger an alert if more than one distinct user is logged in
[ "$(users | wc -w)" -gt 1 ] && logger -t watchdog "multi-user activity"
```

## Nuances and Gotchas

- **Deduplicated output can mislead.** `users | wc -w` counts *accounts*,
  not sessions; two admins each with three terminals is still `2`. For
  session counts use `who -q` (prints `# users=N`) or `who | wc -l`.
- **utmp is not guaranteed truthful.** Crashed sessions, killed `sshd`s,
  and misbehaving programs leave stale `USER_PROCESS` records; `who`
  mitigates with idle-time heuristics (`-u`), `users` has no such logic and
  will happily report ghosts.
- **Empty output with exit 0 is normal** on containers, fresh chroots, and
  systems where nothing ever wrote utmp. Scripts must treat empty as a
  valid answer, not an error.
- **Not in POSIX.** For portable scripts prefer `who -q` (standardized) and
  derive names from it; `users` is a convenience, not a contract.
- **File argument changes the meaning silently.** `users /var/log/wtmp`
  lists every account ever logged in — potentially hundreds of names on an
  old server. It looks identical in shape to the live query; comment such
  invocations well.
- **utmp readability**: on some hardened systems `/var/run/utmp` is
  group-restricted; `users` then reports an empty line even while sessions
  exist. Diagnose with `ls -l /var/run/utmp` before blaming the tool.

## Exit Status

| Status | Meaning |
|---|---|
| 0 | Query completed (including "no records found") |

Failure modes — unreadable or missing file — produce an error diagnostic
and a nonzero status in the standard coreutils style; there is no richer
status vocabulary.

## Related Commands

- [`who`](./who.md) — the same utmp records with per-session detail and headers.
- [`whoami`](./whoami.md) — the current effective user, unrelated to utmp logins.
- [`tty`](./tty.md) — prints the terminal whose name fills utmp's `LINE` field.
- [coreutils collection](./overview.md) — sibling GNU coreutils pages.

## Interview Questions

### Q: Compare users, who -q, and w — what does each add?

`users` prints deduplicated, sorted account names on one line. `who -q`
prints the same names plus a session count (`# users=N`), and is the
POSIX-standardized spelling of the query. `w` shows every *session*: user,
terminal, source host, login time, idle time, CPU usage, and the current
command. The progression is accounts → sessions → per-session activity;
choosing wrong usually means someone needed `w`'s idle column and used
`users` instead.

### Q: Where does users get its data, and what are the failure modes of that source?

From `/var/run/utmp`, the live-session database that login programs
(`sshd`, `login`, `su -`, display managers) write `USER_PROCESS` records
into and clean up on exit. Failure modes: stale records after crashes or
SIGKILLed daemons (phantom users), missing or empty utmp in containers and
chroots (empty output, exit 0), and restricted file permissions on hardened
systems (empty output despite active sessions). `users` applies no
heuristics — garbage in, names out.

### Q: A user with three SSH sessions appears once in users output. Why, and how would you count sessions instead?

`users` deduplicates: it answers "which accounts have a live login", so
multiple sessions collapse to one name. To count sessions, use `who -q`
whose `# users=N` line counts records, or `who | wc -l`. The distinction
between account presence and session count is the entire reason both tools
exist in parallel.

### Q: What does `users /var/log/wtmp` do, and what is the better tool for that job?

It runs the same "extract live user records" query against the wtmp
history database, which yields every account that has ever logged in
rather than those currently logged in. `last` is the proper tool for that
job — it formats wtmp entries with terminals, hosts, timestamps, and
session durations, and supports filtering by user or terminal. `users
/var/log/wtmp` survives as a quick "which accounts exist in history" probe.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/users.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
