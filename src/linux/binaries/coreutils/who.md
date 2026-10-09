# who — show who is logged in

## Overview

`who` prints one line per active login session: username, terminal, login
time, and (for remote sessions) the source host. It reads the system's
`utmp` database (`/var/run/utmp`), and given a file argument it can replay
history from `wtmp` — the raw material behind the `last` command. Beyond
session listing it reports system events recorded in the same database:
boot time (`-b`), runlevel (`-r`), and dead processes (`-d`).

It ships in the Debian `coreutils` package at `/usr/bin/who` and is one of
the oldest Unix commands still in daily use, standardized by POSIX. busybox
ships a reduced `who`, and util-linux's `w` and `last` consume the same
databases with richer formatting.

Its position in the lineage: `who` = per-session snapshot; `w` = snapshot
plus idle time and the command each session is running; `users` = deduplicated
names only; `last` = wtmp *history* with durations. Interview questions love
drawing this map.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/who` |
| First appeared / lineage | Unix v1 era; in GNU coreutils |
| Standards | POSIX.1-2017 |

## Synopsis

```text
who [OPTION]... [ FILE | ARG1 ARG2 ]
```

```bash
who               # current sessions from /var/run/utmp
who -b            # last system boot time
who -r            # current runlevel
who -u            # sessions with idle time (dead sessions visible)
who -H            # column headers
who /var/log/wtmp # replay the login history database
```

## How It Works

Each login (ssh, console, display manager, `su -`) appends a record to
`/var/run/utmp`: record type, username, terminal line, process id, login
time, and remote host. On logout or process death the record is rewritten
as `DEAD_PROCESS`. `who` scans the file and formats the live
`USER_PROCESS` records as text lines:

```text
/var/run/utmp
┌────────────────────────────────────────────────┐
│ type=USER_PROCESS  user=bob   line=pts/1       │──▶ bob   pts/1  2026-07-01 09:40 (gw.corp)
│ type=USER_PROCESS  user=alice line=pts/0       │──▶ alice pts/0  2026-07-01 09:12 (10.0.0.5)
│ type=BOOT_TIME                                 │──▶ (shown by who -b)
│ type=DEAD_PROCESS                              │──▶ (hidden unless -d/-a)
└────────────────────────────────────────────────┘
```

```bash
$ who -H
NAME     LINE         TIME             COMMENT
alice    pts/0        2026-07-01 09:12 (10.0.0.5)
bob      pts/1        2026-07-01 09:40 (gateway.corp)
```

The two-argument form is a compatibility relic of early Unix — `who am i`
(or the whimsical `who mom likes`) restricts output to the invoking
session's own terminal, which on a real terminal shows your login record.
It is how scripts can find "my own line" without parsing the full table.

The FILE argument generalizes the tool: `who /var/log/wtmp` walks the
append-only history database instead of the live one. Since every login is
appended to wtmp and never removed, this is the lineage view — and the
mechanism `last` wraps with durations and reverse-chronological sorting.

System-event record types surface through flags: `BOOT_TIME` (`-b`),
`RUN_LVL` (`-r`), `DEAD_PROCESS` (`-d`), login-process entries (`-l`), and
`-a` shows everything the implementation considers interesting.

## Options That Matter

### Session display

| Option | Effect |
|---|---|
| `-H`, `--heading` | Print column headers (NAME LINE TIME COMMENT) |
| `-u`, `--users` | Include idle time and PID; marks dead entries |
| `-T`, `-w`, `--mesg` | Show message-forcing state: `+` writable, `-` not, `?` unknown |
| `-i`, `--idle` | Legacy spelling of idle-time inclusion (obsolete in GNU) |
| `--lookup` | Attempt DNS canonicalization of hostnames (deprecated) |

### System events and counts

| Option | Effect |
|---|---|
| `-b`, `--boot` | Time of the last system boot |
| `-r`, `--runlevel` | Current (and previous) runlevel |
| `-d`, `--dead` | Dead (not-cleanly-terminated) processes |
| `-l`, `--login` | Login processes (getty-style) |
| `-a`, `--all` | Combine `-b -d --login -p -r -t -T -u` |
| `-q`, `--count` | Names only plus `# users=N` (the POSIX-count mode) |

### Data source

| Option | Effect |
|---|---|
| `FILE` | Read records from FILE (`/var/log/wtmp` for history) |
| `ARG1 ARG2` | The `who am i` two-argument legacy form |

## Usage Patterns

```bash
# Who is on the box right now, with headers for reports
who -H
```

```bash
# Find abandoned sessions: idle time as HH:MM, "old" for a day+
who -u
```

```bash
# Quick uptime alternative (boot time, no uptime math)
who -b
```

```bash
# What runlevel am I in (systemd systems: usually '5 graphical')
who -r
```

```bash
# Count of distinct users — the standardized quick query
who -q
```

```bash
# Check whether a terminal is writable before running write/wall
who -T | grep pts/2
```

```bash
# My own session record without parsing the whole table
who am i
```

```bash
# Login lineage: everything recorded since wtmp was last rotated
who /var/log/wtmp | tail -20
```

```bash
# Audit script: alert on sessions idle longer than a workday
who -u | awk '$4 ~ /old/ {print "stale session:", $1, $2}'
```

```bash
# Everything the database knows about system events and sessions
who -a
```

## Nuances and Gotchas

- **utmp reflects cooperation, not truth.** Records are written and cleaned
  up by userland processes; crashes and SIGKILLed daemons leave stale
  entries. `who -u`'s idle column and `?`/dead markers exist precisely to
  expose them; `users` has no such heuristics.
- **Empty output with exit 0 is valid** — fresh containers, chroots, and
  minimal VMs often have no utmp records at all. A missing utmp file is
  also not fatal for GNU who.
- **`who -b` on systemd systems** comes from the boot record wtmp/utmp
  received at startup; if the database was rotated or the record lost, the
  answer degrades silently. `uptime -s` is an independent cross-check.
- **`--lookup` is deprecated and slow** (reverse DNS per entry); modern
  practice keeps the raw source host, since the "canonical" name is rarely
  more truthful.
- **`who am i` needs a controlling terminal.** In cron, CI, or after
  redirections it prints nothing useful or errors; it is a terminal-era
  convenience, not a script API. Use `tty` plus `who` filtering if you need
  session self-identification robustly.
- **Time column is login time, not idle** — pairing `-u` (idle) with the
  TIME column is the standard way to separate long-lived-but-active
  sessions from truly abandoned ones.
- **Lineage clarity**: `last` reads the same wtmp with better formatting;
  `w` adds `WHAT` (current command); `users` collapses to names. On busybox
  systems several of these may be missing while `who` survives.

## Exit Status

| Status | Meaning |
|---|---|
| 0 | Query completed — including when no entries are found |
| 1 | Invalid usage (unknown option, bad operand count) |

Notably, "nobody logged in" is status 0 with empty output, not an error —
scripts must distinguish emptiness, not just status.

## Related Commands

- [`users`](./users.md) — `who`'s output collapsed to deduplicated names.
- [`whoami`](./whoami.md) — effective-user identity, independent of utmp sessions.
- [`tty`](./tty.md) — the terminal name that fills `who`'s LINE column.
- [coreutils collection](./overview.md) — sibling GNU coreutils pages.

## Interview Questions

### Q: Map the who / w / users / last family onto the utmp and wtmp databases.

`who` reads `/var/run/utmp` (live sessions plus system-event records like
boot and runlevel). `w` reads the same utmp but enriches each session with
idle time, JCPU/PCPU, and the current command from process accounting of
ttys. `users` reads utmp and prints deduplicated names. `last` reads
`/var/log/wtmp` — the append-only history that every login also writes —
and reconstructs login history with durations. Point any of them at a
different file (e.g. `who /var/log/wtmp`) and you swap databases manually.

### Q: What does `who -u` show that plain `who` does not, and why does it matter operationally?

Idle time and the process ID, with dead entries surfaced. Operationally,
this is how you find abandoned sessions: a `pts` line idle for days ("old"
in the idle column) usually means a disconnected SSH client whose server
side never noticed. The PID lets you verify the session's process tree
before killing it. Plain `who` shows login times only, which cannot
distinguish "logged in for days and active" from "logged in for days and
gone".

### Q: A cron job runs `who am i` and gets nothing. Why?

`who am i` is a two-operand legacy form that reports the record for the
invoking session's controlling terminal. Cron jobs have no controlling
terminal and no utmp login record — cron does not create sessions in utmp —
so there is nothing to report. Robust self-identification in scripts uses
`tty` (checking for a terminal at all) plus `ps`/environment data rather
than the interactive-session conventions of the 1970s.

### Q: Why can who output be wrong after an unclean shutdown, and which flags help diagnose?

utmp is maintained by userland: login processes add `USER_PROCESS`
records and their exit paths rewrite them as `DEAD_PROCESS`. A crash or
SIGKILL skips the rewrite, leaving phantom sessions. `who -u` exposes
suspicious entries (ancient idle times), `who -d` lists the dead-process
records that *were* recorded, and `who -a` shows the full record mix
including boot and runlevel events so you can correlate against the last
boot. The deeper point: utmp is a cooperative cache, not kernel truth.

### Q: What is the difference between `who -q` and `users`?

Both list currently logged-in accounts from utmp. `who -q` is POSIX
standardized and appends a session count (`# users=N`); `users` is a BSD
lineage convenience that prints only the sorted, deduplicated names and is
not standardized. When portability or a session count matters, `who -q`
wins; `users` exists for terse one-line status banners.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/who.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
