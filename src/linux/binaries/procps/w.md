# w — who is logged in and what they are running

## Overview

`w` answers two questions at once: *who* is on the system (like `who`) and *what* are they doing right now (per-session idle time, CPU totals, and the foreground command). It ships in the `procps` package at `/usr/bin/w` and prints two things: a header that is byte-for-byte the [uptime](./uptime.md) line, then one row per login session with `USER TTY FROM LOGIN@ IDLE JCPU PCPU WHAT`.

It is often confused with `who` (rows without the WHAT/IDLE/CPU columns), `users` (names only), and `last` (historical logins, not current sessions). Its niche is live accountability on shared systems — build servers, jump hosts, teaching machines — where "who is hogging the CPU" is a daily question. The `JCPU`/`PCPU` columns are the parts interviews probe, because their definitions are precise and easily garbled.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 4.x) |
| Man section | 1 |
| Path | /usr/bin/w |
| First appeared | BSD lineage (plan (1) ancestor); modern form in procps/procps-ng |
| Standards | None (column set is a BSD/procps convention) |

## Synopsis

```
w [options] [user]
```

Common one-line forms:

```
w                # every session, full columns
w alice          # only alice's sessions
w -s             # short format: drop LOGIN@, JCPU, PCPU
w -h             # no header — parseable
```

## How It Works

### Two-part output

The header is the uptime one-liner (same procps code, same `/proc` sources):

```
 15:33:34 up  7:42,  0 users,  load average: 0.00, 0.05, 0.01
USER     TTY      FROM             LOGIN@   IDLE   JCPU   PCPU  WHAT
```

On a live multi-user host it reads like this (illustrative values):

```
USER     TTY      FROM             LOGIN@   IDLE   JCPU   PCPU  WHAT
alice    pts/0    10.0.0.5         09:12    1:04m  0.15s  0.02s -bash
bob      pts/1    10.0.0.9         09:40    0.00s  2:31m  0.10s vim main.c
carol    pts/2    db.internal      Mon14    5:17m  1:02h  0.45s top
```

Session data comes from utmp (or systemd's session table on modern init systems); the per-session idle and CPU figures come from the tty and `/proc` — `w` walks each tty, finds its attached processes, and sums their CPU time.

### The model behind a row

Each row is a *session* (utmp record) joined against a *tty* (process group membership):

```
utmp record:  alice, pts/1, from 10.0.0.5, login 09:12
                 │
                 ▼
tty pts/1 ────┬─ login shell  (-bash)      ← foreground when idle
              ├─ background job (make)     ← counts into JCPU while running
              └─ its children (cc1, ...)   ← foreground when the job is fg'd
                         │
   IDLE  ← last input on pts/1        JCPU ← Σ CPU of everything above
                                      PCPU ← CPU of the one foreground task
```

This is why the row is a *tty* view and not a *user* view: the same user on three terminals is three rows, and a process detached from the tty (nohup, daemon, tmux-detached job) drops out of every column even while it consumes the box. `w -p` surfaces the two PIDs (session leader and current process) that this model hides.

### The columns, one by one

| Column | Meaning |
| --- | --- |
| `USER` | Login name of the session owner |
| `TTY` | Terminal device: `pts/N` (pseudo-terminal: ssh, tmux panes) or `ttyN` (console/virtual terminal) |
| `FROM` | Remote host the session came from (IP resolved to hostname when possible); `-` or `:0` for local/X displays; hidden or shown with `-f` |
| `LOGIN@` | When the session logged in: `HH:MM` for today, an abbreviated date otherwise |
| `IDLE` | Time since the last activity on that tty — seconds below a minute (`0.00s`), minutes as `m:ss` (`5:17m`), days beyond that; `-o` blanks sub-minute values; `old` appears when idle time cannot be determined |
| `JCPU` | CPU time used by *all* processes attached to the tty — past background jobs excluded, currently running background jobs included |
| `PCPU` | CPU time used by the *current* process — the one named in `WHAT` |
| `WHAT` | Command line of the session's current foreground process (login shell if idle) |

The JCPU/PCPU pair is the precision test: **JCPU is a per-tty aggregate** (everything ever attached to that terminal, minus finished background jobs), while **PCPU belongs to exactly one process** — the foreground one in `WHAT`. A user who ran a 2-hour compile *in the background* and now idles at a shell prompt shows small `PCPU` (the idle shell) and large `JCPU` (the compile still running attached to the tty), or small `JCPU` if the compile finished — its time is *not* retroactively credited.

### Idle time: where it comes from and how it reads

`IDLE` is measured from the tty's last-activity timestamp, so it reflects keyboard/terminal traffic, not "how busy the user's processes are". A session can show `0.00s` idle while a background job burns CPU, and `2days` idle on a session whose long-running job is doing all the work. Formats used by procps:

```
0.00s     under a minute (blank in -o old-style output)
5:17m     minutes:seconds
1:02h     hours:minutes
2days     days
old       idle time unavailable (e.g. stale utmp entry)
```

### Modes and sources

`w` chooses its session source automatically: systemd's session table where available, else utmp. Two newer procps modes change the source or the payload:

- `-t` (`--terminal`): ignore session tables entirely and scan `/dev/tty*` and `/dev/pts/*` for attached processes — useful when utmp is stale or missing, at the cost of a different (and larger) notion of "user count".
- `-p` (`--pids`): prefix the `WHAT` column with the PID of the login process and the current process — turning `w` into a quick "give me the PID to signal" tool.

### w vs who vs users vs last

| Command | Scope | Shows |
| --- | --- | --- |
| `uptime` | Summary | Session *count* + load; no identities |
| `users` | Now | Distinct login names, nothing else |
| `who` | Now | One row per session: user, tty, source, login time |
| `w` | Now | `who` plus IDLE, JCPU, PCPU, WHAT — and uptime's line as header |
| `last` | History | Past sessions from wtmp/btmp, with durations |

The optional `user` argument filters rows to matching login names.

## Options That Matter

| Option | Effect |
| --- | --- |
| `user` | Restrict output to sessions of that login name |
| `-h`, `--no-header` | Drop the header — machine-parsable rows |
| `-s`, `--short` | Short format: omit `LOGIN@`, `JCPU`, `PCPU` |
| `-f`, `--from` | Toggle the `FROM` (remote host) column |
| `-i`, `--ip-addr` | Show the IP address instead of the resolved hostname in `FROM` |
| `-t`, `--terminal` | Discover sessions by scanning tty devices instead of reading session tables |
| `-p`, `--pids` | Show PIDs of the login process and the `WHAT` process |
| `-u`, `--no-current` | Ignore the invoking user's identity when attributing the current process (the `su` demo: `su -; w` vs `w -u`) |
| `-o`, `--old-style` | Legacy layout; sub-minute idle printed as blank space |
| `-V`, `--version` | procps-ng version |

## Usage Patterns

```bash
# The daily question: who is on my build box and who is burning CPU
w

# Everything one user is running
w alice

# Machine-parsable session list (user + tty + what)
w -h | awk '{print $1, $2, $NF}'

# Sessions with PIDs, ready to feed pkill (see ./pkill.md)
w -p

# Look at remote origins by IP, skipping DNS
w -i

# Compact presence check in a shell prompt
w -s

# Who has the most CPU attached to their tty?
w -h | sort -k5 -r | head        # JCPU is column 5 in the default layout

# Quick PID lookup for a stuck session's current process
w -p | grep pts/2

# Compare presence tools in one shot
uptime; who; users; w -s

# Cross-check JCPU vs PCPU for a suspicious session
w; ps -o pid,etime,time,tty -t pts/1

# Find sessions idle for days (candidates for cleanup)
w -h | awk '$5 ~ /days/ {print $1, $2, $5}'

# Live watch of a shared jump host (see ./watch.md)
watch -n5 'w -s'

# Count active SSH sessions for a change window
w -h | grep -c '^.*pts/'

# Every process alice owns, not just her foreground ones
w alice; pgrep -u alice -a
```

## Nuances and Gotchas

- **WHAT shows the foreground process only.** Daemons, background jobs, and detached processes never appear — a user can be "idle at `-bash`" while their background job is the CPU hog. Correlate with `ps -t` or [top](./top.md) before accusing anyone.
- **JCPU excludes *finished* background jobs.** CPU time from completed background work disappears from the column entirely; only currently attached processes count. `w` is not an accounting tool — `sa`/`acct` or the audit log are.
- **Idle is tty-activity based.** GUI sessions (X/Wayland) and sessions whose input never touches the tty (tmux attach chains) can show misleading idle values — often a huge IDLE while the user is active in another pane.
- **Multiple sessions, multiple rows.** One user on three terminals appears three times with independent JCPU/PCPU per tty; the person-vs-session distinction is the same as [uptime](./uptime.md)'s user count.
- **utmp is trust-me data.** Login records are userland files (`/var/run/utmp`); crashed sessions leave ghosts, and a rootkit can edit them freely. `w` is for situational awareness, not security auditing.
- **`-u` exists for a reason.** Inside a `su` shell, `w` attributes the current process to the *switched* identity; `w -u` ignores the invoking username when computing current-process and CPU figures — the man page's own demo of the difference.
- **`FROM` depends on DNS.** Reverse lookups can make `w` slow (or show stale names) on hosts with broken resolver config; `-i` sidesteps it.
- **Containers typically show nothing.** No utmp activity means no rows even though processes run — the same headless caveat as `uptime`'s user count.
- **Column positions shift with `-s`/`-f`.** Scripts that parse by column number break when the layout changes; use `-h` and match on content, or parse `who` instead.
- **`LOGIN@` is compacted for old sessions.** A session opened before today renders as an abbreviated date rather than a time, and very old utmp entries can be stale leftovers from an unclean shutdown — `last` is the historical view, `w` the current one.
- **`FROM` shows where the *session* came from, not the chain.** Through a jump host or tmux pair, you see the immediate predecessor (the jump host's address, or the tmux client's), not the human's original machine.

## Exit Status

| Code | When |
| --- | --- |
| 0 | Sessions listed (even if the list is empty) |
| 1 | Failure opening the session source or `/proc` (rare) |

Neither code is formally documented in `w(1)`; empty output is normal, not an error.

## Related Commands

- [`uptime`](./uptime.md) — `w`'s header, standalone: load and session count.
- [`top`](./top.md) — the per-process view that explains what `JCPU`/`PCPU` are summing.
- [`ps`](./ps.md) — per-tty process listing (`ps -t pts/1`) behind the `WHAT` column.
- [`pgrep`](./pgrep.md) — everything a user owns, foreground or not (`pgrep -u alice -a`).
- [`pkill`](./pkill.md) — act on the PIDs that `w -p` surfaces, by session or name.
- [Process management](../../admin/process-management.md) — foreground/background process groups that define `WHAT`.
- [procps overview](./overview.md) — the rest of the collection.

## Interview Questions

### Q: Explain exactly what JCPU and PCPU measure.

`JCPU` is the total CPU time of all processes attached to that session's tty — including currently running background jobs, excluding *finished* background jobs, whose time simply vanishes from the display. `PCPU` is the CPU time of the single process shown in `WHAT`, i.e. the session's current foreground process. So a user with a huge background compile shows a large `JCPU` and a small `PCPU` (their idle shell is the foreground process); once the compile finishes, its time is no longer reflected at all. The pair answers "how much CPU does this session cost" (JCPU) versus "what is the active process costing" (PCPU).

### Q: A user complains "I wasn't doing anything, why is my session at the top by CPU?" — walk through the diagnosis.

Read the columns in order: `PCPU` small but `JCPU` large means the foreground process is innocent and some *background* process attached to that tty accumulated the time — check `ps -o pid,time,stat,comm -t <tty>` to find it. `IDLE` large with high `JCPU` fits that story perfectly. If both `JCPU` and `PCPU` are large, the foreground process is genuinely burning CPU (e.g. an editor running a build plugin). Remember `WHAT` only ever shows the foreground process, so `w` alone cannot name a background culprit — that needs `ps` or `top`.

### Q: How do w, who, users, and uptime differ in what they report?

All four read the same session records but summarize differently: `uptime` gives one count of sessions plus system load; `who` lists each session (user, tty, source host, login time); `users` collapses that to a deduplicated list of names on one line; `w` is `who` plus idle time, per-tty CPU totals (`JCPU`), current-process CPU (`PCPU`), and the foreground command — with `uptime`'s line as its header. Escalating detail: uptime → users → who → w.

### Q: Why does w -u exist, and what does it change?

`w` tries to identify the invoking user's own session to attribute "current process" CPU figures correctly, and inside a `su` shell that attribution can be surprising — the man page demonstrates it directly: run `su`, then compare `w` with `w -u`. `-u` makes `w` ignore the username while computing current-process and CPU times, which matters for scripts that must report the same thing regardless of who runs them. It is a niche flag, but knowing it signals familiarity with how `w` builds its rows from utmp plus `/proc`.

### Q: How reliable is w as a security signal for "who is on this box"?

Only as reliable as utmp, which is a plain userland file that any process with the right permissions can write — crashed sessions leave stale rows, and malware can add, remove, or rewrite entries at will (rootkits historically did exactly that). `w` is situational awareness for interactive hosts; for auditing, use the kernel-level sources: login records from `last`/`journalctl`, and process truth from `/proc` or auditd. The `WHAT` column also inherits the same blind spot as `top`'s `COMMAND`: a trojaned binary can rename itself, and short-lived processes may never be shown.

### Q: On a tmux-heavy jump host, w shows users idle for hours who are actively working. Why, and what do you check instead?

Idle is measured from activity on the *tty of the session* — inside tmux, keystrokes go to the tmux server's pty, while the outer ssh session's tty genuinely sees nothing, so the outer `w` row accumulates idle time no matter how busy the user is. The same applies to detached-but-running jobs: `w` cannot see through a multiplexer. Check `tmux list-sessions` for real activity, read load average and `top` to see whether CPU work is happening at all, and treat `IDLE` on multiplexed hosts as "no direct terminal input on this tty" rather than "this person is gone".

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/w.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
