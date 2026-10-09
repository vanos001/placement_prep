# last — list recent logins and reboots from wtmp

## Overview

`last` walks `/var/log/wtmp` backwards and prints the login history of the machine: which users logged in, on which terminals, from which hosts, when they arrived, and how long they stayed. It also surfaces system events recorded as pseudo-users — `reboot`, `shutdown`, and runlevel changes — making it the classic first look at "who was on this box and when did it bounce". Ships in the `util-linux` package (Debian bookworm) at `/usr/bin/last`.

`wtmp` is written by login processes (via the `utmp`/`wtmp` bookkeeping APIs): `agetty`/`login`, `sshd`, display managers, and `init`/systemd for boot/shutdown records. `last` is a *reader* over that binary log, with time filtering, address formatting, and duration arithmetic. It is often confused with `who` (a snapshot of *current* sessions from `utmp`), `lastlog` (a different file, `/var/log/lastlog`, keyed per-user: most recent login per account), and `journalctl` (systemd's richer, structured journal — which does not read wtmp and vice versa).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/last |
| First appeared | BSD lineage (early 1980s) |
| Standards | None (BSD wtmp file format; no command standard) |

## Synopsis

```
last [options] [<username>...] [<tty>...]
lastb [options] [<username>...] [<tty>...]
```

Common one-line forms:

```
last                    # everything wtmp remembers, newest first
last -5                 # five most recent sessions
last reboot             # boot history
last -x                 # include shutdown and runlevel records
last -s -7days user     # that user's sessions since a week ago
```

## How It Works

### Reading wtmp backwards

`wtmp` is an append-only sequence of `utmp`-style records (user, tty, host, PID, timestamps, type). `last` seeks to the end of the file and walks records backwards, pairing each login record with its matching logout record to compute the session duration:

```
 record type      what you see in the output
 ───────────────  ─────────────────────────────────────────────
 USER_PROCESS     alice   pts/0   10.1.2.3   Mon 09:12   still logged in
 DEAD_PROCESS     alice   pts/0   10.1.2.3   Mon 09:12 - 09:40  (00:28)
 BOOT_TIME        reboot  system boot  6.1.0-13-amd64  Mon 05:02  still running
 RUN_LVL          runlevel (to lvl 5) ...
```

Interpretation of the tail column: `still logged in` (no matching logout yet), `(HH:MM)` duration, `crash` (session ended without clean logout — power loss/panic), `down` (system went down), or `gone - no logout` (file was rotated mid-session).

### The bookkeeping file map

Four files, four questions — `last` is only the second row:

```
file                written by                read by      question answered
/run/utmp           login/sshd/getty          who, w       who is logged in NOW
/var/log/wtmp       login machinery, init     last         session HISTORY
/var/log/btmp       failed logins             lastb        failed attempts
/var/log/lastlog    login                     lastlog      most recent login per UID
```

On systemd systems the journal (`journalctl`) shadows wtmp for depth, but wtmp keeps being written for compatibility — and `last` remains the fastest human query over it.

### Record anatomy and type pairing

Each wtmp record is a fixed-size `utmp`-style struct: record type, PID, device, user id/name, host, and an epoch timestamp. `last` pairs records by session: a `USER_PROCESS` entry matches a later `DEAD_PROCESS` entry carrying the same PID and device; `BOOT_TIME` (`reboot` rows) and `RUN_LVL` entries stand alone. Consequences:

- a missing partner becomes `still logged in`, `crash`, or `down` depending on what followed;
- the pairing key is PID+tty, so PID reuse across boots is harmless (different boots, different file sections);
- a truncated file mid-session yields `gone - no logout`.

### The utmp record, field by field

wtmp rows are fixed-size `struct utmp` records (384 bytes on x86-64 glibc Linux), so the file is a pure record array — which is what lets `last` walk backwards by fixed strides with no index. The fields that matter to `last`:

```
ut_type     record kind (USER_PROCESS, DEAD_PROCESS, BOOT_TIME, RUN_LVL...)
ut_pid      writer's PID — half of the login/logout pairing key
ut_line     tty name (pts/0, tty1); "system boot" for reboot rows
ut_user     username; pseudo-users "reboot"/"shutdown"/"runlevel" appear here
ut_host     remote host for sshd sessions; kernel release for reboot rows
ut_tv       timestamp — 32-bit seconds + microseconds even on 64-bit builds
ut_addr_v6  remote IPv4/IPv6 address, when the writer supplied one
```

Two consequences worth knowing in interviews. The pairing key is (PID, line): PID reuse inside one file segment is the mechanism behind mispaired session durations. And the 32-bit `ut_tv` is a Y2038 landmine — wtmp archives written today still carry 32-bit seconds, one of the quiet reasons journal-first audit designs replaced wtmp for anything long-lived.

### Duration arithmetic

The trailing `(00:28)` is plain subtraction of the two timestamps, rendered as wall-clock. `last -F` prints both endpoints in full so you can recompute honestly; duration display is coarse (minutes), and DST shifts appear as ±1h distortions even though the epoch math is right.

### What each record means

- **User sessions** — written by `login`, `sshd`, display managers on login and logout.
- **`reboot` rows** — one per boot (kernel boot time), host column shows the kernel release.
- **`shutdown` rows** — appear with `last -x`; ordinary shutdowns still leave a `down`-ish trace in the previous session's exit.
- **Runlevel rows** — legacy sysvinit bookkeeping; sparse on pure systemd systems.

### Reading one output line, field by field

```
alice   pts/0        10.1.2.3        Mon May 13 09:12 - 09:40  (00:28)
└─┬──┘  └───┬──┘     └────┬─────┘     └──────────┬─────────┘ └───┬──┘
 user      tty           source host        login - logout    duration
```

Pseudo-user rows reuse the same grid: `reboot` in the user column, `system boot` in the tty column, the kernel release in the host column, boot time as the timestamp. A `still logged in` tail (or `still running` for reboot) means no closing record exists *yet*.

### Filtering mechanics

Positional arguments match usernames *or* tty names; multiple operands OR together (`last alice bob` = either). `-s`/`-t` are inclusive bounds parsed liberally (`-s -2hours`, `-s "2024-05-01 09:00"`, `-t yesterday`); `-p` collapses both to a single instant — internally it asks "which session intervals contain this moment?". `-n` truncates output *after* filtering and reading backwards, so `last -n 5 alice` is the five most recent alice sessions, not the five newest rows filtered later.

Output shaping is orthogonal to filtering: `-a` moves the host to the last column (grep-friendly), `-d` resolves IPs to hostnames, `-i` forces numeric IPs, `-F` expands both timestamps, `-w` disables field truncation, `-R` drops the host column entirely.

### Variants: lastb and friends

- **`lastb`** — the same tool pointed at `/var/log/btmp` (bad logins: failed `login`/`ssh` attempts). Records there carry the *attempted* user and source address, so `lastb -n 50` / `lastb | awk '{print $3}' | sort | uniq -c | sort -nr` is the classic brute-force reconnaissance. It reads sensitive data, so `/var/log/btmp` is root-only and `lastb` must run as root.
- **`last -f /var/log/wtmp.1`** — wtmp rotates monthly via logrotate; "last month" lives in the rotated file, not in `last`'s default view.
- **`lastlog`** (separate binary) — per-account most-recent-login from `/var/log/lastlog`; sparse-file keyed by UID, answers a different question (never logged in?).

## Options That Matter

| Option | Effect |
| --- | --- |
| `-n <num>` / `-<num>` | Limit output to the most recent `<num>` sessions |
| `-f <file>` | Read `<file>` instead of `/var/log/wtmp` (rotations, btmp) |
| `-s <when>`, `-t <when>` | Show sessions since / until the given time |
| `-p <when>` | Who was logged in at the given moment |
| `-F, --fulltimes` | Full date+time on login and logout columns |
| `-a, --hostlast` | Print hostname in the last column (grep-friendly) |
| `-d, --dns` | Resolve remote IPs back to hostnames |
| `-i, --ip` | Show numeric IPs instead of resolved names |
| `-R, --nohostname` | Omit the hostname column |
| `-w, --fullnames` | Do not truncate user/tty/host fields |
| `-x, --shutdown` | Include shutdown and runlevel-change records |

## Usage Patterns

```bash
# Overview: the most recent logins and current session state
last | head -20

# Was the machine rebooted this week? Boot history with kernels
last reboot

# Include shutdown/runlevel rows to reconstruct the full boot/shutdown story
last -x | head -20

# One user's sessions, newest first
last alice

# What happened in the last 24 hours (login window filter)
last -s -24hours

# Who was logged in at 02:00 last night? (point-in-time query)
last -p "yesterday 02:00"

# Brute-force source analysis over failed logins (root)
sudo lastb -n 50
sudo lastb | awk '{print $3}' | sort | uniq -c | sort -nr | head

# Last month's history (logrotate moved the rest into wtmp.1)
last -f /var/log/wtmp.1 -s "2024-05-01" -t "2024-06-01"

# Machine-readable-ish, full timestamps, IPs only
last -F -i -w -a | head

# How long did sessions on pts/3 last?
last pts/3 -F

# Find crash endings (sessions ended without clean logout)
last -F | grep -E 'crash|down' | head

# Hosts a user came from (deduplicated address report)
last -i -w alice | awk '{print $3}' | sort -u | head

# Session counts per user this week
last -s "-7 days" | awk '/ pts\.| tty/{print $1}' | sort | uniq -c | sort -rn | head

# Correlate a reboot with the kernel that booted
last reboot -F | head -3

# Point-in-time staffing check: who was on at 03:00 last Tuesday?
last -p "2024-05-14 03:00"

# SSH brute-force sources, top 10 (as root)
sudo lastb -n 1000 | awk '{print $3}' | grep -E '^[0-9]+\.' | sort | uniq -c | sort -nr | head

# Check whether utmp matches reality after a crashed session (stale rows)
last | head -3

# Five most recent sessions of two users at once (operands OR together)
last -n 5 alice bob

# Full-width, IP-only, newest 50 for an incident timeline export
last -n 50 -F -i -w -a > /tmp/login-timeline.txt

# Was the system up during the incident window? (interval overlap check)
last -x reboot shutdown -s "2024-05-14 02:00" -t "2024-05-14 04:00"
```

```bash
# Absolute-date window (audit one shift, full timestamps)
last -s "2024-05-01 08:00" -t "2024-05-01 18:00" -F
```

```bash
# Read a rotated wtmp without leaving temp state behind
zcat /var/log/wtmp.2.gz > /tmp/w2 && last -f /tmp/w2; rm -f /tmp/w2
```

```bash
# Cross-check current state (utmp) against history (wtmp) for stale rows
who; echo ---; last -5
```

## Nuances and Gotchas

- **Rotation hides history.** `last` reads only the current `/var/log/wtmp`; anything older is in `wtmp.1`, `wtmp.2.gz`. Scripts that audit "all of last quarter" must iterate rotated files (gunzipping as needed).
- **wtmp is not tamper-proof.** It is a plain file writable by the login machinery; attackers with root routinely truncate it (`> /var/log/wtmp`). Entries are written *after* authentication, and the host column is the peer address for sshd (client-supplied and spoofable only on legacy remote-login protocols) — either way, treat `last` output as evidence of bookkeeping, not a security audit trail; journaling/auditd is the durable source.
- **`gone - no logout`** appears when wtmp rotated while a session was open — the logout record landed in a different file. It is a rotation artifact, not a ghost login.
- **Clock changes distort durations.** Duration = logout timestamp minus login timestamp; DST jumps and NTP corrections make long sessions look 1h shorter/longer, and dual-boot machines with skewed RTCs produce nonsense ranges.
- **Timezone is interpreted at read time.** Records store seconds-since-epoch; `last` renders them with the *current* local timezone. Analyzing logs collected in another TZ shifts all displayed times.
- **`lastb` needs root and is a privacy sink** — it records attempted usernames and source addresses of failed logins; `/var/log/btmp` permissions exist for a reason, and its file grows fast under internet-facing ssh (size the logrotate policy accordingly).
- **Busybox/system differences:** busybox has no `last`; BSD/macOS `last` shares the concept but differs in options (`-s/-t` time filters are util-linux). Portable scripts stick to `last`, `last user`, and `-n`.
- **systemd systems still write wtmp** (sshd/login do), but service-level session detail (unit, cgroup) lives only in the journal — `journalctl _COMM=sshd` goes where `last` cannot.
- **Column truncation** — long usernames/hosts are clipped to fixed widths; add `-w` before parsing textually.
- **No stdin form.** The `-f` operand must be a real path; auditing gzipped rotations means `zcat wtmp.2.gz > /tmp/w2 && last -f /tmp/w2`.
- **`reboot` rows show the kernel in the host column** — grep-able, but only because the boot record's host field carries `uname -r`; do not build logic on "hostname" semantics there.
- **`who`/`w` vs `last`:** a stale utmp (crashed login process) makes `who` show ghosts; `last` reads wtmp and is immune to that class of staleness — comparing the two is the standard way to spot it.
- **Fixed-size records mean fixed-stride parsing.** `last` walks the file in record-size steps; a wtmp copied from a different architecture or written by a differently-aligned implementation parses as garbage rather than failing cleanly. Regenerate history per-architecture instead of copying files around.
- **`-d` triggers reverse DNS per row.** Resolving every source address is slow and can hang on broken resolver configurations; scripts should use `-i` (numeric) and resolve in bulk, separately, with their own timeout.
- **An empty wtmp is not "no users ever".** After log cleaning, a rebuild, or a first boot, `last` prints nothing and exits 0 — absence of rows is absence of *records*, not evidence about logins. Cross-check `lastlog` and the journal before concluding anything.

## Exit Status

- `0` — records were read and displayed (including an empty wtmp).
- `1` — error: unreadable file (missing wtmp, permission denied on btmp as non-root) or invalid options.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`agetty`](./agetty.md) — the login-side writer that appends the session records `last` reads.
- [`dmesg`](./dmesg.md) — kernel-side boot/reboot evidence to corroborate `last reboot`.
- [`systemd`](../../admin/systemd.md) — the journal as the richer, tamper-evident session source on modern systems.
- [`users-groups`](../../admin/users-groups.md) — account model behind the user column.
- [`process-management`](../../admin/process-management.md) — tying sessions (pts, sshd PIDs) to running processes.

## Interview Questions

### Q: What is the difference between utmp, wtmp, btmp, and lastlog?

`utmp` is the volatile snapshot of *current* login state in `/run/utmp` (what `who` reads). `wtmp` is the historical archive of sessions and boot/shutdown events (`/var/log/wtmp`, what `last` reads, rotated by logrotate). `btmp` records *failed* login attempts (`/var/log/btmp`, read by `lastb`, root-only). `lastlog` is a per-UID sparse file holding each account's most recent successful login (read by the `lastlog` command, printed at login). Different files, different questions — `last` is only the wtmp reader.

### Q: How would you determine whether a server was rebooted uncleanly last week?

`last -x reboot shutdown` shows boot rows and their kernel; the session immediately before the boot ending in `crash` or `down` indicates a non-clean transition, while a normal shutdown shows an explicit shutdown record. Corroborate with `last -f /var/log/wtmp.1` if the window rotated, and with `journalctl --list-boots` / `dmesg` timestamps. The pairing of a `reboot` row with the previous session's abrupt ending is the tell.

### Q: Why can `last` lie during an intrusion investigation?

wtmp is an ordinary, root-writable file: a competent intruder truncates or edits it, and sessions spanning a rotation show `gone - no logout`. It is subject to clock manipulation, and some of its fields are self-reported by whatever process writes them. Use it for continuity, then verify against the systemd journal, `auth.log`/`secure`, and auditd, which are append-heavy and harder to surgically rewrite.

### Q: You see `gone - no logout` for a session from three weeks ago. What happened?

The logout record went to the *rotated* file: logrotate moved `wtmp` to `wtmp.1` while the session was still open, so the `DEAD_PROCESS` record never met its login record in one file. Verify with `last -f /var/log/wtmp.1 user`. It is a bookkeeping seam, not an anomaly — but it means naive duration accounting across rotations undercounts.

### Q: How does `lastb` help with SSH hardening, and what are its limits?

`lastb` lists failed authentication attempts with source IP and attempted username, so quick aggregations (`lastb | awk '{print $3}' | sort | uniq -c | sort -nr`) identify brute-force sources for firewall/fail2ban decisions. Limits: it only captures attempts that reach the wtmp-writing layer (not connection-level probes), btmp grows fast and needs rotation, and serious analysis should use `auth.log`/journald filters which carry more context (cipher, key vs password).

### Q: Why do session durations look one hour off around DST changes, and how do you get reliable durations?

Durations are simple timestamp subtraction rendered in local time, so the wall-clock rendering shifts by the DST delta while the underlying interval is correct. Use `last -F` for absolute, full-precision timestamps and do your own arithmetic in UTC (or read the raw records), especially when reporting SLAs across March/October boundaries.

### Q: What is inside a wtmp record, and why does the format constrain tools like last?

A fixed-size `struct utmp`: record type, PID, tty line, inittab id, username, host, exit status, session id, a 32-bit seconds/microseconds timestamp, and a 16-byte address field. Because every row is the same width, `last` can walk backwards without an index and pair login/logout records by PID+tty. The costs are equally structural: no variable-length fields (long names/hosts truncate), 32-bit timestamps (Y2038), and binary fragility across architectures — the reasons structured, variable-length journals displaced wtmp for audit-grade history.

### Q: How would you build "uptime history with downtime" for a fleet of legacy servers?

`last -x reboot shutdown -F` per host gives boot and shutdown rows with kernel versions and crash markers; walk rotated wtmp files (`wtmp.1`, `wtmp.2.gz`) for older windows and compute intervals between consecutive rows — the gap between one boot row and the next is uptime, and a missing shutdown record before a boot row marks a crash. Corroborate anomalies with `journalctl --list-boots` where the journal exists. The interview point is composing record types into intervals yourself instead of trusting the duration column, which lies across DST and file rotations.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/last.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
