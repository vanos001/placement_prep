# utmpdump — dump and reload binary login-accounting files

## Overview

`utmpdump` converts the binary `utmp`/`wtmp`/`btmp` files — the kernel-era login accounting that tools like `who`, `w`, `last`, and `lastlog` read — into plain ASCII records, and (`-r`) converts such ASCII back into binary. It ships in the Debian `util-linux` package at `/usr/bin/utmpdump` and is the standard tool for *inspecting*, *migrating*, and *repairing* accounting logs.

You reach for it when `last` output isn't enough: you need exact timestamps with microseconds, raw entry types, PIDs, terminal IDs and IP fields; when converting wtmp after a libc or struct-layout change (the classic libc5→libc6 migration use case); or when cleaning up corrupt `wtmp` entries after an unclean shutdown. It is often confused with [`last`](./last.md) (human-oriented *report* over wtmp, with its own filtering) and with `lastlog` (a different file, per-user last-login records, not a stream).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/utmpdump |
| First appeared | long-standing util-linux tool; output format redesigned in the 2.30 era (2017) for y2038-safe timestamps |
| Standards | none; `utmp(5)` binary layouts |

## Synopsis

```
utmpdump [options] [filename]
```

Main one-line forms:

```
utmpdump /var/log/wtmp               # dump wtmp to readable records
utmpdump -f /var/log/wtmp            # follow the file as it grows
utmpdump /var/log/wtmp > wtmp.txt    # snapshot for editing/migration
utmpdump -r < wtmp.txt > wtmp.new    # reload: ASCII -> binary
```

## How It Works

### The three files and their entry shape

`utmp` (current state, in memory-mapped userspace convention at `/run/utmp`), `wtmp` (append-only history at `/var/log/wtmp`, including BOOT_TIME and shutdown markers), and `btmp` (failed logins, `/var/log/btmp`) all store fixed-size `struct utmp` records:

```
type        USER_PROCESS(7), DEAD_PROCESS(8), BOOT_TIME(2), ...
pid         process id of the login session
line        tty/pts name            ("pts/0")
id          inittab id              ("ts/0")
user        login name
host        remote host / kernel version for boot records
addr        IPv4/IPv6 address of the remote peer
tv          seconds + microseconds of the event
```

`utmpdump` prints one bracketed ASCII record per entry, in field order, and `-r` parses exactly that grammar back — the dump format *is* the interchange format. Type numbers follow `utmp(5)`:

```
0 EMPTY  1 RUN_LVL  2 BOOT_TIME  3 NEW_TIME  4 OLD_TIME
5 INIT_PROCESS  6 LOGIN_PROCESS  7 USER_PROCESS  8 DEAD_PROCESS  9 ACCOUNTING
```

### Reading a real record

```bash
$ utmpdump /var/log/wtmp | tail -3
[2] [0000000] [~~  ] [reboot] [~  ] [6.1.0-0-amd64] [0.0.0.0        ] [2024-01-15T08:59:59,000001+00:00]
[7] [19721  ] [ts/0] [pts/0] [root ] [server01] [203.0.113.10    ] [2024-01-15T09:30:12,123456+00:00]
[8] [19721  ] [    ] [pts/0] [     ] [       ] [0.0.0.0        ] [2024-01-15T17:45:03,000000+00:00]
```

Field order: `[type] [pid] [id] [line] [user] [host] [addr] [time]`, plus an optional trailing comment (`kernel`, `shutdown`) on system-event records. The time field is ISO-8601 with microseconds and UTC offset (`2024-01-15T09:30:12,123456+00:00`) — newer util-linux releases print this form for y2038-safety; older releases printed ctime-style strings. A `[2]` reboot record is how `last` knows to print "system boot"; the matching shutdown shows as `[1]` RUN_LVL or a commented entry.

### Record types cheat sheet

Keep this mapping handy; it is the fastest way to read a dump without the `utmp(5)` man page:

```
type  name            typical producer          what last(1) does with it
----  --------------  ------------------------  -------------------------
 0    EMPTY           (unused slot)             ignores
 1    RUN_LVL         init/systemd level change shutdown marker heuristics
 2    BOOT_TIME       kernel/init at boot       prints "system boot"
 3    NEW_TIME        clock change: new time    prints "old/new time"
 4    OLD_TIME        clock change: old time    (pair with 3)
 5    INIT_PROCESS    init spawning a process   internal
 6    LOGIN_PROCESS   getty/login registered    internal
 7    USER_PROCESS    login/sshd/su             session line
 8    DEAD_PROCESS    session ended             closes the session line
 9    ACCOUNTING      accounting daemons        internal
```

A *clean* history alternates 7 (open) with 8 (close) per terminal; a crash leaves dangling 7s — which is why `last` shows sessions that "never ended" and why repair scripts hunt for them.

### Who writes these files

Writers are the login stack, not the kernel: `sshd`, `login`/`getty`, `su`/`sudo` (with `pam_lastlog`), `init`/systemd (boot, runlevel, session tracking), and `last`-adjacent tools read them. On systemd systems much of this duplicates `wtmpdb`/journal session records — utmp is the legacy interface, but it is still written by default, and its readers (`who`, `w`, `last`, `users`, `lslogins`) are what scripts actually consume.

### last(1) versus the raw records

`last` performs real work over the raw stream: pairing open/close records, reverse-order formatting, duration computation, and filtering (`-n`, `-s`, `-t`). When its output confuses — duplicate sessions, "still logged in" ghosts, missing boots — dropping to `utmpdump` shows the unmediated records and usually identifies a crashed session (dangling type 7), a clock jump (types 3/4), or a rotated-then-concatenated file whose ordering broke the pairing.

### The round-trip workflow

`-r` reads the ASCII form from stdin and writes binary records to stdout, so migration and repair follow one pattern:

```bash
# 1. dump        2. (optionally filter/fix with sed/awk)      3. reload
utmpdump /var/log/wtmp.old | utmpdump -r > /var/log/wtmp
```

Typical jobs: converting wtmp across a struct-layout change, dropping junk records from a corrupted file, or stitching rotated logs. Always work on a copy and stop the writers (or do it in single-user mode) — concurrent appends while you rewrite the file will lose records.

```
binary wtmp ──utmpdump──> ASCII text ──(grep/sed/awk)──> ──utmpdump -r──> binary wtmp'
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-f, --follow` | Keep reading and emit new records as the file grows (tail -f for utmp/wtmp). |
| `-r, --reverse` | Reverse mode: read ASCII records from stdin, write binary to stdout. |
| `-o, --output <file>` | Also write the dump to `<file>`. |
| `-h, -V` | Help / version. |

## Usage Patterns

```bash
# Full login history with microsecond timestamps
utmpdump /var/log/wtmp | less
```

```bash
# Show only interactive logins (type 7)
utmpdump /var/log/wtmp | awk -F']' '$1 ~ /\[7/'
```

```bash
# Follow live logins the way tail -f follows a log file
utmpdump -f /var/log/wtmp
```

```bash
# Who is logged in right now, raw equivalent of `who`
utmpdump /run/utmp | grep '\[7\]'
```

```bash
# Inspect failed logins (brute-force indicator) in btmp
utmpdump /var/log/btmp | grep '\[7\]' | tail -50
```

```bash
# Boot and shutdown timeline from wtmp
utmpdump /var/log/wtmp | grep -E '\[(1|2)\]'
```

```bash
# Snapshot, clean, and reload a corrupted wtmp (single-user mode!)
utmpdump /var/log/wtmp > /tmp/w.txt
grep -v '0.0.0.0        ] \[' /tmp/w.txt > /tmp/w2.txt   # drop junk rows
utmpdump -r < /tmp/w2.txt > /var/log/wtmp
```

```bash
# Merge two rotated logs chronologically for last(1)
{ utmpdump /var/log/wtmp.2; utmpdump /var/log/wtmp; } | sort -t] -k9 | utmpdump -r > /tmp/wtmp
```

```bash
# Check a file's record integrity: -r then re-dump must round-trip
utmpdump /var/log/wtmp | utmpdump -r | utmpdump | cmp - <(utmpdump /var/log/wtmp)
```

```bash
# Count sessions per user across the whole history
utmpdump /var/log/wtmp | awk -F']' '$1 ~ /\[7/ {print $6}' | sort | uniq -c | sort -rn
```

```bash
# Find the actual boot time the fast way (type 2 record)
utmpdump /var/log/wtmp | grep '^\[2\]' | tail -1
```

```bash
# Track wtmp growth live during a suspected credential-stuffing burst
utmpdump -f /var/log/btmp | grep --line-buffered '\[7\]'
```

```bash
# Extract source IPs of successful SSH sessions for a report
utmpdump /var/log/wtmp | grep '\[7\]' | awk -F']' '{print $8}' | sort | uniq -c
```

```bash
# Diff two accounting eras after a migration (text form compares cleanly)
utmpdump /var/log/wtmp.old > /tmp/old.txt; utmpdump /var/log/wtmp > /tmp/new.txt; diff /tmp/old.txt /tmp/new.txt
```

## Nuances and Gotchas

- **Permissions.** `/var/log/wtmp` is group-writable only by `utmp`, `btmp` is more restrictive; reading them as a normal user fails with EACCES unless you are root or in the `utmp` group. `utmpdump` does not and cannot bypass file permissions.
- **The round-trip is the safe edit path.** Editing the binary file with a hex editor or naive `dd` truncation is how `last` output gets permanently weird; dump → filter → `-r` keeps record boundaries and field sizes intact.
- **Rotated logs lose chronology.** `last` relies on append order, not embedded sorting; the merge recipe above must re-sort by timestamp before reloading or your "history" reorders itself.
- **Format changed across releases.** Old dumps show ctime-style times (`[Thu Jan 15 09:30:12 2024]`); new ones ISO-8601 with comma microseconds. `-r` accepts what its sibling release prints — mixing a binary from a different `utmp(5)` layout is exactly the migration case, but *scripts parsing the text form* must accept both.
- **utmp is advisory, not authoritative.** Entries are written by login programs and can lie or linger (crashed sessions leave stale `[7]` records); auditing off utmp is a classic mistake — use `auditd`/journal instead.
- **y2038 and 32-bit.** Old 32-bit layouts store 32-bit `time_t`; the 2.30-era format change exists to survive 2038. Archives from 32-bit systems may need conversion — which is precisely this tool's job.
- **Follow mode and rotation.** `-f` does not track log rotation the way `tail -F` re-opens files; after `logrotate` moves wtmp you keep reading the old inode.
- **btmp can be huge and hostile.** Failed-login logs grow unbounded under brute force and contain attacker-controlled strings in user/host fields — treat utmpdump output as untrusted text in any downstream parser, and consider `lastb`-style postrotate handling.
- **Timezone vs stored UTC.** The printed offset comes from the record's `ut_tv` rendered with the *reader's* timezone; dumps taken on machines with different TZ settings show different wall times for the same record. For forensics, compare epoch fractions (or force `TZ=UTC`), not formatted strings.
- **wtmpdb is coming.** systemd-era distros are migrating session accounting to a sqlite-backed `wtmpdb` with proper 64-bit times; utmp/wtmp remain for compatibility. New tooling should not hard-wire utmpdump assumptions forever.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | File dumped, followed, or reloaded successfully. |
| nonzero | Unreadable/missing file, malformed ASCII input in `-r` mode, or write failure. |

## Related Commands

- [`last`](./last.md) — the human-facing report over the same wtmp records utmpdump shows raw.
- [`lslogins`](./lslogins.md) — user-centric view of login data from the same accounting ecosystem.
- [`mesg`](./mesg.md) — toggles the tty write bit recorded alongside utmp sessions; same login-session machinery.
- [`../../admin/systemd.md`](../../admin/systemd.md) — where session accounting lives on systemd systems (`utmp` vs journal).
- [`./overview.md`](./overview.md) — util-linux collection hub.

## Interview Questions

### Q: What are utmp, wtmp and btmp, and how does utmpdump relate to them?

utmp holds current login state (`who`, `w` read it), wtmp is the append-only history (`last` reads it, including boot/shutdown markers), btmp records failed logins (`lastb`). All are fixed-size binary `struct utmp` streams; `utmpdump` prints them as bracketed ASCII fields and `-r` converts such ASCII back to binary — making it the inspect/migrate/repair tool for all three.

### Q: You need to prove when a specific SSH session started to the second. Why utmpdump over last?

`last` formats for humans and can merge or summarize records; `utmpdump` exposes the raw entry — type 7 USER_PROCESS with exact `tv_sec`/`tv_usec` (ISO timestamp with microseconds), PID, line, and remote address. For evidence-grade timestamps you want the unmediated record, and for cross-checking you can correlate the PID/line pair with journal or wtmp session-closing records.

### Q: Describe a safe procedure to repair a corrupted /var/log/wtmp.

Stop or avoid concurrent writers (single-user/rescue, or accept losing the tail), copy the file, `utmpdump` it to text, inspect for malformed rows, filter them out with grep/sed, then `utmpdump -r < cleaned > wtmp` and verify with a re-dump. Never rewrite the binary in place with arbitrary tools: record boundaries and struct layout are what `-r` preserves.

### Q: Why did util-linux change utmpdump's timestamp output format?

The classic 32-bit `time_t` in `struct utmp` breaks in 2038 (y2038), and ctime-style text loses sub-second resolution. The 2.30-era releases print ISO-8601 with microseconds and UTC offset, which is timezone-explicit and forward-compatible — but scripts that parsed the old text format must handle both spellings.

### Q: Can utmp records be trusted for security auditing?

Only as weak corroborating evidence. utmp/wtmp are userspace files written cooperatively by login programs — a compromised root can forge or delete entries freely, and crashed sessions leave stale USER_PROCESS rows. For real auditing use the kernel-backed audit subsystem or the (systemd/journald) logs, treating utmp as convenience data.

### Q: What is the purpose of the reboot `[2]` and shutdown entries in wtmp?

They are time anchors: `last` prints "system boot" from BOOT_TIME records and can infer clean versus unclean shutdowns from RUN_LVL records that follow. Without them, session lifetimes in wtmp would have no machine-wide markers to frame them.

### Q: Design a migration: a legacy appliance's wtmp must be imported into a modern system's history. Where does utmpdump fit and what breaks?

Pipeline: `utmpdump old.wtmp > old.txt` (binary layout differences disappear in text), adapt lines if needed (fix time offsets, drop EMPTY padding records), then `utmpdump -r < old.txt > wtmp` into the new system — the ASCII form is precisely the layout-independent interchange. Breakage points: the old file may use 32-bit times (y2038-era conversion), text parsing must handle both ctime and ISO timestamp spellings, and appends after the migration must not interleave with the pre-sorted import — sort chronologically before reloading, and verify with a round-trip `cmp` as in the usage patterns.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/utmpdump.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
