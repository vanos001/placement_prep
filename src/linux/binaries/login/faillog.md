# faillog — login failure accounting database

## Overview

`faillog` is the shadow suite's per-account record of *failed logins*: a fixed-layout binary file, `/var/log/faillog`, holding one record per UID — the failure count since the last successful login, a maximum-failure threshold, the tty of the last failure, its timestamp, and a lockout duration — plus the `faillog(8)` tool that displays and administers it. `login` writes the records as failures happen and enforces the lockout; the tool resets counters and sets policy. On Debian, both shipped in the `login` binary package (source package `shadow`) through bookworm — the man page referenced below is the *format* page (section 5); the tool's own page is `faillog(8)` in the same package.

The feature has been quietly dying, and that decay is itself the lesson. The util-linux `login` used by Fedora, Arch, and — since Debian 13 — by Debian has no faillog support at all; Linux-PAM standardized counting with `pam_tally`/`pam_tally2` and then `pam_faillock`, which keep state elsewhere; and shadow 4.17-era packaging dropped the tool from Debian's `login` package after bookworm. On a current Debian system you will find neither the binary nor the man page, but `/etc/security/faillock.conf` and the `pam_faillock.so` module are present. Interviews ask about faillog precisely to see whether you understand *where* login-failure counting lives on a given system.

| Field | Value |
| --- | --- |
| Package | login (Debian bookworm; source package `shadow`) — removed from the package after bookworm |
| Man section | 8 for the tool; this page documents the format (section 5) |
| Path | /usr/sbin/faillog (bookworm-era) |
| First appeared | System V faillog heritage, implemented by the shadow suite |
| Standards | None; shadow-suite-specific file format |

## Synopsis

```
faillog [options]
```

Common one-line forms (bookworm-era tool):

```
faillog                 # report every account in passwd order
faillog -u ann          # one account's record
faillog -t 7            # failures recorded in the last 7 days
faillog -m 5 -l 600 -u ann   # after 5 failures, lock ann for 600 s
faillog -r -u ann       # reset ann's counters (also: -r for all)
```

## How It Works

### The file format

`/var/log/faillog` is a flat array of fixed-size records, addressed by UID: the record for UID *u* starts at byte offset *u* × record-size, and the file is created sparse so it grows only as far as the highest UID that ever failed. The shadow-era record (x86-64) is 32 bytes:

```
 offset  field          size   meaning
      0  fail_cnt           2  failures since last successful login
      2  fail_max           2  failure threshold before lockout (0 = no limit)
      4  fail_line[12]     12  tty of the last failed attempt
     16  fail_time          8  timestamp of the last failed attempt
     24  fail_locktime      8  seconds to lock once fail_max is reached
     32  — next record (UID+1) —
```

Exact byte layout is the shadow suite's business (it varies with platform word sizes), which is why the format has its own man page rather than being folded into the tool's.

### Record math, worked once

For UID 1001 with 32-byte records: offset = 1001 × 32 = 32032. The first record (UID 0) starts at 0, so a file of apparent size *S* spans `S / record_size` UID slots — a 2 MB faillog is "we have UIDs past 65000", not "we have 2 MB of failures". A populated record for one user is barely 32 bytes; the *shape* of the file says something about your UID allocation, the *contents* say something about your attackers.

### faillog, btmp, faillock: three counting systems

Login-failure state in the wild lives in three unrelated places, and mixing them up is the standard debugging mistake:

```
 system    state file            writer                 reader          scope
 --------- --------------------- ---------------------- --------------- ------------------
 faillog   /var/log/faillog      shadow login(1)        faillog(8)      console logins only
 btmp      /var/log/btmp         login, sshd (varies)   lastb           failed sessions
 faillock  /run/faillock/<user>  pam_faillock           faillock(8)     any PAM service
```

Only the first is this page's subject; the third is its functional successor. All three can be simultaneously present on one machine and disagree, because they count different things at different layers.

### Why the file is (usually) mostly holes

A system with users at UID 1000–1010 has meaningful data only in the first ~32 KB — but if anyone ever failed a login at UID 65534, the file *appears* to be ~2 MB. Reading it is cheap and random-access; copying it naively is not. The sparse trick is identical to [`lastlog`](./lastlog.md)'s:

```bash
$ truncate -s 3200000 /var/tmp/faillog.demo    # pretend: 100000 UIDs x 32 bytes
$ ls -lh /var/tmp/faillog.demo
-rw-rw-r-- 1 z z 3.1M Oct  9 15:53 /var/tmp/faillog.demo
$ du -h /var/tmp/faillog.demo
0       /var/tmp/faillog.demo
$ rm /var/tmp/faillog.demo
```

`ls` reports the addressed size, `du` the blocks actually allocated. `cp` without sparse handling, `scp`, and `tar` without `-S` inflate the holes into zero bytes on disk.

### Who writes and enforces it

Under the bookworm-era stack, the shadow `login` binary did all the work:

- On a **failed** login it appended the tty and timestamp, incremented `fail_cnt`, and — once `fail_cnt` reached `fail_max` — refused further logins for `fail_locktime` seconds.
- On a **successful** login it cleared the counter (that is what "failures since the last successful login" means) and offered the "last failed login" summary.
- Participation was gated by `FAILLOG_ENAB` in `/etc/login.defs`; that key no longer exists in current `login.defs(5)`, along with the rest of the feature.

Two clarifications people get wrong: the familiar banner *"There were N failed login attempts since the last successful login"* on Debian/Ubuntu SSH logins comes from `pam_lastlog`'s `showfailed` reading `/var/log/btmp`, **not** from faillog; and Linux-PAM has never shipped a `pam_faillog` module — the PAM-side counters are `pam_tally`/`pam_tally2` (removed from modern releases) and `pam_faillock`.

### What replaced it

```bash
$ ls /lib/x86_64-linux-gnu/security/ | grep -E 'faillock|tally'
pam_faillock.so
$ grep -E '^(deny|unlock_time|fail_interval)' /etc/security/faillock.conf 2>/dev/null
```

`pam_faillock` (configured via `/etc/security/faillock.conf` or module arguments: `deny=`, `unlock_time=`, `fail_interval=`) keeps per-user state in `/run/faillock/` and is the modern answer on Debian 13, RHEL, and friends. It works for *any* PAM service — including sshd, which faillog never covered since sshd does not run shadow's `login`. Debian 13 ships the companion tool:

```bash
$ faillock --help 2>&1 | head -2
Usage: faillock [--dir /path/to/tally-directory] [--user username] [--reset] [--legacy-output]
```

So the bookworm-era `faillog -u ann` / `faillog -r -u ann` pair translates to `faillock --user ann` / `faillock --user ann --reset` on current systems — same operator workflow, different state store.

## Options That Matter

| Option | Effect |
| --- | --- |
| (none) | Print the faillog record for every user in /etc/passwd. |
| `-a`, `--all` | Force display (or apply changes) to all records, including "clean" ones. |
| `-u`, `--user LOGIN\|RANGE` | Select one account or a UID range (e.g. `-u 1000-1999`). |
| `-t`, `--time DAYS` | Display only records newer than DAYS. |
| `-m`, `--maximum MAX` | Set the failure threshold (with `-u`); 0 disables lockout. |
| `-l`, `--lock-sec SEC` | Set the lockout duration once the threshold is hit (with `-u`). |
| `-r`, `--reset` | Reset failure counters/lock state (all accounts, or with `-u`). |
| `-R`, `--root CHROOT_DIR` | Operate on a chroot — useful in image builds. |

## Usage Patterns

```bash
# 1. Audit who is being attacked at the console (bookworm-era system)
$ sudo faillog | awk 'NR==1 || $3+0 > 0'
```

```bash
# 2. One account's failure record
$ sudo faillog -u ann
```

```bash
# 3. Failures recorded this week only
$ sudo faillog -t 7
```

```bash
# 4. Policy: lock an account for 10 minutes after 5 consecutive failures
$ sudo faillog -m 5 -l 600 -u ann
```

```bash
# 5. Reset one user after helping them (or all users after an incident)
$ sudo faillog -r -u ann
$ sudo faillog -r
```

```bash
# 6. Apply the same policy to every human account in a range
$ sudo faillog -m 5 -l 600 -u 1000-1999
```

```bash
# 7. Image builds: edit the database inside a chroot
$ sudo faillog -R /mnt/rootfs -r
```

```bash
# 8. The modern equivalent on Debian 13+: pam_faillock policy
$ grep -E '^(deny|unlock_time)' /etc/security/faillock.conf
deny = 3
unlock_time = 600
```

```bash
# 9. Read a raw record forensically (record size differs by platform: check locally)
$ sudo od -A d -j $((1000*32)) -N 32 -t x1 /var/log/faillog
```

```bash
# 10. Confirm the feature is really gone on trixie before scripting against it
$ command -v faillog || echo "not shipped by this release"
not shipped by this release
```

```bash
# 11. Modern equivalent: inspect the pam_faillock state for one user
$ sudo faillock --user ann
```

```bash
# 12. Modern equivalent of 'faillog -r -u ann': clear the faillock tally
$ sudo faillock --user ann --reset
```

```bash
# 13. Distinguish the two databases when triaging an incident
$ ls -l /var/log/faillog /run/faillock 2>&1 | head -3
```

## Nuances and Gotchas

- **Enforcement lives in `login`, not in the file.** Deleting `/var/log/faillog` does not unlock anyone (recreate it and reset instead); and any service that does not run shadow's `login` — above all sshd — was never counted by it.
- **UID-keyed records.** Two accounts sharing a UID share one record; the tool lists users by iterating `/etc/passwd`, so NSS-only users have no entry.
- **Sparse-file traps** when archiving: use `cp --sparse=always`, `rsync -S`, `tar -S`. A 2 MB file with zero allocated blocks is normal, and `ls`/`du` disagreement is diagnostic, not corruption.
- **`-m`/`-l` with no `-u`** apply to the whole database — easy way to lock out everyone's semantics at once; check the man page of your exact release before bulk changes.
- **Lockout vs `passwd -l`**: faillog's lock is temporary and counter-driven (`fail_locktime` seconds); `passwd -l`/`usermod -L` flip a permanent `!` onto the hash. Different mechanisms, different undo procedures.
- **The banner confusion**: `pam_lastlog showfailed` + btmp produce the "N failed login attempts" line users see; faillog never fed sshd. Debugging "why does faillog look empty" usually ends there.
- **Removal after bookworm**: Debian 13 ships no `faillog` binary or man page (the `login` package was rebuilt from util-linux), and `FAILLOG_ENAB` is gone from `login.defs(5)`. Scripts that call `faillog -r` in maintenance jobs break — port them to `pam_faillock` state (`faillock --user ann` on releases that ship the companion tool).
- **Portability**: the 32-byte record assumed here is x86-64 shadow; other architectures/libc layouts differ, so never hardcode offsets in cross-platform scripts.
- **Tool vs database**: `/usr/sbin/faillog` is the reader/admin tool, `/var/log/faillog` is the database; scripts that test `-x /usr/sbin/faillog` as a proxy for "failure counting is on" get it wrong — the file and the `FAILLOG_ENAB` policy are the truth.
- **Neither system grows from successes.** faillog is fixed-size by construction; btmp is append-only and *does* need logrotate (Debian ships a rotation stanza). A huge btmp plus an empty faillog on a bookworm box means "SSH attacks", not console ones.

## Exit Status

- `0` — success.
- `1` — permission denied: most operations (display of others, policy changes, resets) require root.
- `2` — invalid command syntax (bad option, malformed UID range).

## Related Commands

- [`login`](./login.md) — the writer/enforcer of the faillog database under the shadow implementation.
- [`lastlog`](./lastlog.md) — the sibling per-UID database for the *last successful* login; same sparse-file tricks.
- [Overview — the login collection](./overview.md) — where failure accounting sits among the session-entry tools.
- [Users and groups](../../admin/users-groups.md) — shadow-file mechanics that faillog records hang off.

## Interview Questions

### Q: How does faillog find the record for a given user without an index?

The file is a direct-address array: record size × UID is the byte offset, records are fixed-size, and the file is kept sparse so unpopulated UIDs cost nothing. That is why the format is stable per platform and why the file can "look" huge. The same trick underlies `/var/log/lastlog`.

### Q: How would you lock an account after 3 failed console logins, and what would you actually deploy today?

Bookworm-era answer: `faillog -m 3 -l 900 -u ann` and let shadow's `login` enforce it. Today's answer on Debian 13/RHEL: `pam_faillock` with `deny = 3`, `unlock_time = 900` in `/etc/security/faillock.conf`, because it counts across services (including sshd) and survives the shadow→util-linux login switch. Saying both, with the sshd caveat, is the point.

### Q: faillog shows nothing for a user who clearly mistyped their password five times over SSH. Why?

Because faillog was only ever fed by shadow's `login` — the console path. sshd authenticates through its own PAM stack and never touches `/var/log/faillog`. SSH failures land in `/var/log/btmp` (see `lastb`) and, on modern stacks, in `pam_faillock`'s `/run/faillock/` state.

### Q: Why did most distributions drop faillog?

Convergence of reasons: util-linux's `login` (Fedora, Arch, now Debian 13) never implemented it; PAM centralized failure counting in `pam_tally2` and then `pam_faillock`; sshd — the main attack surface — bypasses `login` entirely; and the sparse file sat unread on most systems. Debian shipped the tool through bookworm and removed it afterward; upstream shadow dropped the feature in the same era.

### Q: A user is "locked out" and you suspect faillog. Walk the fix.

Check the record (`faillog -u ann` — bookworm-era) or the faillock state file; distinguish faillog's *timed* lock (expires after `fail_locktime` seconds, or reset with `faillog -r -u ann`) from a shadow-hash lock (`passwd -u ann` for a `!` prefix) and from `pam_faillock` (`faillock --user ann --reset` or wait out `unlock_time`). Three locks with similar symptoms; knowing which file holds the state is the actual question.

### Q: Where does login-failure state live on a system whose main entry point is sshd?

Not in faillog — sshd never runs shadow's `login`, so `/var/log/faillog` stays empty on such hosts no matter how hard the box is hammered. The state lives in btmp (`lastb` shows the failed sessions) and, on modern stacks, in `pam_faillock`'s per-user tallies under `/run/faillock/` (inspect with `faillock --user`, reset with `--reset`). Mapping each *file* to the layer that writes it is the actual interview answer.

### Q: What does the `fail_cnt` field mean exactly, and when is it cleared?

Failures *since the last successful login*: a successful login zeroes the counter, so it measures consecutive failures, not lifetime history. The lifetime record lives in the timestamp/tty fields plus btmp/wtmp elsewhere. `fail_cnt` reaching `fail_max` triggers the `fail_locktime` refusal — that relationship is the whole policy model of the format.

## References

- [Man page(5) — manpages.debian.org](https://manpages.debian.org/bookworm/login/faillog.5.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
