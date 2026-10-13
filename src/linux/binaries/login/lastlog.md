# lastlog — last-login database and reporting tool

## Overview

`/var/log/lastlog` answers one question per account: *when did this UID last successfully log in, from where?* It is a flat, per-UID array of fixed-size records — timestamp, tty line, remote host — overwritten on every login, and the `lastlog(8)` tool (Debian bookworm: `/usr/bin/lastlog`, package `login`, source package `shadow`) prints it in a passwd-ordered table, including a bold **Never logged in** for accounts with no record. The same database feeds the `Last login: ...` banner printed by `login` and sshd. This is *not* the `last(1)` data: `last` replays `/var/log/wtmp` (full session history, rotated); `lastlog` keeps only the most recent login per UID, never rotated.

The tool itself is in decline: Debian 13 removed `lastlog` from the `login` package when it was rebuilt from util-linux (the binary and its man page are absent there), while util-linux's `login` still reads and writes `/var/log/lastlog`, and util-linux ships a separate, sqlite-backed successor, `lastlog2(1)`, packaged as `lastlog2`. The *file*, however, is a fixture of every Linux system — which is why the format, the sparse-file behavior, and the lastlog/last/w distinction remain core interview material.

| Field | Value |
| --- | --- |
| Package | login (Debian bookworm; source package `shadow`) — tool removed from the package after bookworm |
| Man section | 8 |
| Path | /usr/bin/lastlog (bookworm-era) |
| First appeared | 4.3BSD `lastlog` heritage; shadow-suite implementation on Debian |
| Standards | None; record layout is whatever the local libc/shadow writes |

## Synopsis

```
lastlog [options]
```

Common one-line forms (bookworm-era tool):

```
lastlog                  # one line per passwd account: Username Port From Latest
lastlog -u ann           # one account
lastlog -u 1000-1999     # UID range (also open-ended: 1000-, -1999)
lastlog -t 30            # only logins within the last 30 days
lastlog -b 365           # only logins older than a year
lastlog -C -u ann        # clear ann's record (modern shadow builds)
```

## How It Works

### The record layout

`struct lastlog` is defined by the C library; on this Debian 13 x86-64 system it compiles to 292 bytes, with a 4-byte time field:

```
 offset  field      size    meaning
      0  ll_time        4   time of last login (32-bit field in this libc)
      4  ll_line       32   tty name (pts/0, tty1, ...)
     36  ll_host      256   remote host (empty for console logins)
    292  — next record (UID+1) —
```

Portability caveat worth saying out loud: other architectures and libc versions lay this out differently (an 8-byte `time_t` yields 296-byte records), and shadow's writers use the platform `time_t` — so never hardcode 292 in cross-platform scripts; derive the stride locally.

### Addressing and the sparse trick

The record for UID *u* lives at byte offset *u* × record-size. A fresh system ships the file empty:

```bash
$ ls -l /var/log/lastlog
-rw-rw-r-- 1 root utmp 0 May  5 00:00 /var/log/lastlog
```

and it grows only as high as the highest UID that ever logs in — as a *sparse* file. The classic demonstration:

```bash
$ truncate -s 3200000 /var/tmp/lastlog.demo
$ ls -lh /var/tmp/lastlog.demo
-rw-rw-r-- 1 z z 3.1M Oct  9 15:53 /var/tmp/lastlog.demo
$ du -h /var/tmp/lastlog.demo
0	/var/tmp/lastlog.demo
$ rm /var/tmp/lastlog.demo
```

`ls` shows the addressed size, `du` the allocated blocks — zero. An all-zero (or absent) record means "never logged in", which is exactly what the tool prints.

### Who writes it

- `login`: the util-linux man page is explicit — if `/var/log/lastlog` exists, the last login time is printed and the current login is recorded.
- sshd: OpenSSH maintains lastlog records for interactive logins itself, which is why SSH sessions show up even though sshd never runs `/bin/login`.
- `pam_lastlog` (module option `showfailed`) on stacks that include it handles the banner/counting on some distributions; current Debian ships no `pam_lastlog.so`.

Reading does not require the tool: the banner path in `login`/sshd reads the file directly, and you can too.

### Reading it: tool output and the lastlog/last/w split

```
Username         Port     From             Latest
root             pts/0    203.0.113.7      Mon Jan  6 09:12:44 +0000 2025
ann              tty1                      Tue Mar  4 08:41:10 +0000 2025
svc-ci                                        **Never logged in**
```

(Illustrative format; the column headers and the **Never logged in** marker are the tool's.)

| Tool | File | Granularity | Question it answers |
| --- | --- | --- | --- |
| who | /run/utmp | active sessions | who is on right now? |
| w | /run/utmp + /proc | active sessions + current command | what are they running? |
| last | /var/log/wtmp | full session history | when did sessions start/end? (rotated) |
| lastb | /var/log/btmp | failed logins | who is hammering the door? |
| lastlog | /var/log/lastlog | one record per UID | when did each account last log in? |

`lastlog` never rotates and never grows beyond one record per UID; `last` depends on wtmp rotation policy (`/var/log/wtmp.1`) and holds real history. Confusing the two is the most common interview slip.

## Options That Matter

| Option | Effect |
| --- | --- |
| (none) | Report every account in /etc/passwd order, including "Never logged in". |
| `-u`, `--user LOGIN\|RANGE` | One login name or UID range (`-u 1000-`, `-u -1999`, `-u 1000-1999`). |
| `-t`, `--time DAYS` | Print only records *newer* than DAYS. |
| `-b`, `--before DAYS` | Print only records *older* than DAYS — the dormant-account query. |
| `-C`, `--clear` | Zero a user's record (requires `-u`; modern shadow builds). |
| `-S`, `--set` | Set a user's record to the current time (requires `-u`; test/deprovisioning helper). |
| `-R`, `--root CHROOT_DIR` | Examine the database under a chroot (image builds). |

## Usage Patterns

```bash
# 1. Dormant human accounts: logged in, but not for a year
$ sudo lastlog -b 365 | grep -v 'Never logged in'
```

```bash
# 2. Accounts created but never used (candidate for cleanup)
$ lastlog | grep 'Never logged in'
```

```bash
# 3. Audit a UID range (humans live at 1000+ on Debian)
$ sudo lastlog -u 1000-1999
```

```bash
# 4. Activity in the last month, one line per account
$ sudo lastlog -t 30
```

```bash
# 5. Read the raw record for UID 1000 (stride = sizeof(struct lastlog) on THIS libc)
$ sudo od -A d -j $((1000*292)) -N 292 /var/log/lastlog
```

```bash
# 6. Apparent vs real size of the database (sparse!)
$ ls -lh /var/log/lastlog; du -h /var/log/lastlog
```

```bash
# 7. Deprovisioning: wipe the record of a retired account
$ sudo lastlog -C -u retired-alice
```

```bash
# 8. Back it up without inflating the holes
$ sudo cp --sparse=always /var/log/lastlog /var/backups/lastlog.$(date +%F)
$ sudo rsync -S /var/log/lastlog backup-host:/var/backups/lastlog
```

```bash
# 9. No "Last login:" banner? Check the quiet-login marker before blaming the file
$ ls -l ~ann/.hushlogin 2>/dev/null && echo "hushlogin active"
```

```bash
# 10. On Debian 13, confirm what you actually have (tool gone; file and successor remain)
$ command -v lastlog lastlog2 || true
$ dpkg -l lastlog2 2>/dev/null | tail -1
```

## Nuances and Gotchas

- **Sparse-file traps on copy.** `scp`/plain `cp`/`tar` without `-S` materialize the holes: a "2 MB" lastlog lands as 2 MB of zeros on the other side, and systems with high UIDs (some distros create users at 60000+) look enormous. Use `rsync -S`, `cp --sparse=always`, `tar -S`.
- **UID-keyed, passwd-ordered.** The tool iterates `/etc/passwd`, so pure-NSS users (LDAP-only) do not appear; two accounts sharing a UID share one record.
- **"Never logged in" is a claim about records, not reality** — records can be absent (fresh system, cleared with `-C`) or the account may have been used only through su/sudo/cron, none of which write lastlog. Only real login sessions (console via login, sshd) update it.
- **`.hushlogin` hides the banner but not the write.** A user with a quiet login still updates lastlog; the banner is suppressed, not the record.
- **Permissions**: Debian ships it `-rw-rw-r-- root utmp` — group `utmp`, so members of that group (classic `w`/`finger` tooling) can read it; tighten if last-login data is sensitive on your hosts.
- **32-bit time field**: on this libc layout `ll_time` is 4 bytes, so the classic Y2038 question applies to raw parsing — another reason not to hand-parse across platforms.
- **Tool vs file lifetime**: Debian 13 dropped the `lastlog` binary; the file keeps being written by `login`/sshd, and util-linux's `lastlog2` (sqlite-backed, `lastlog2` package) is the designated successor. Scripts calling `lastlog` need a fallback there.
- **`-t` and `-b` measure "now"**, not each other: `-t 30 -b 365` together is self-contradictory and returns nothing sensible — pick one window per query.

## Exit Status

- `0` — records read (even if the answer is "Never logged in").
- `1` — failure: unreadable database (permissions), malformed selection, or user/range not found.

## Related Commands

- [`login`](./login.md) — the writer behind the banner; documents the lastlog read/write behavior.
- [`faillog`](./faillog.md) — the sibling per-UID database for failed logins; same addressing and sparse tricks.
- [Overview — the login collection](./overview.md) — the session-accounting files (utmp/wtmp/btmp/lastlog) in context.
- [Users and groups](../../admin/users-groups.md) — UID allocation and the passwd file that orders lastlog output.

## Interview Questions

### Q: How can /var/log/lastlog be "500 MB" while the disk shows almost nothing used?

It is sparse: the record for UID *u* sits at offset *u* × record-size, so a system that once logged in a UID-60000 user has a 500 MB *addressed* file with a few allocated blocks (`du` ≈ 0). Consequences: copying tools without sparse support inflate it, and "big lastlog" is never by itself a disk-space incident.

### Q: What is the difference between lastlog, last, and w?

Different files and different questions: `lastlog` reads `/var/log/lastlog` — exactly one overwritten record per UID ("last login ever", never rotated). `last` reads `/var/log/wtmp` — an append-only, logrotate-rotated *history* of sessions with durations. `w` reads `/run/utmp` plus `/proc` — who is logged in *right now* and what they run. Bonus point: `lastb` reads btmp for *failed* logins.

### Q: A user is currently logged in, but lastlog says "Never logged in". How?

lastlog records are written only by real login-session machinery: `login` and sshd. If the session came through `su`/`sudo`/`runuser`, was started by a daemon (e.g. a service manager session), the record was cleared (`lastlog -C`), or the user shares a UID with an account whose record you're reading — the report can legitimately disagree with reality. Check `who`/`w` for the live session and the shared-UID case in passwd.

### Q: Why does sshd update lastlog even though it never runs /bin/login?

OpenSSH implements login sessions natively and carries its own lastlog read/update code (with PAM variants on some systems), precisely because sshd does not exec `/bin/login`. That is why SSH logins appear in lastlog and get the "Last login:" banner. It is also the standing reminder that session *accounting* in Linux lives in files and conventions, not in one program.

### Q: How would you produce a compliance report of accounts not used in 90 days?

`lastlog -b 90 | grep -v 'Never logged in'` for dormant-but-used accounts, `lastlog | grep 'Never logged in'` for never-used ones, then cross-check with `last -F` (wtmp history) because lastlog only proves the *last* login was old — a burst of logins 100 days ago followed by nothing looks identical to 20 years of silence. On Debian 13+ note the tool's removal and use `lastlog2` or parse wtmp.

### Q: You copied /var/log/lastlog to a backup host and the file tripled in size. What happened and how do you fix it?

The copy tool materialized the sparse holes. Fix: transfer with `rsync -S`, `cp --sparse=always` from a tar stream made with `tar -S`, or compress (zeros compress away). Prevention is understanding the per-UID addressing: the "size" of lastlog is a function of your highest UID, not of your login history.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/login/lastlog.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
