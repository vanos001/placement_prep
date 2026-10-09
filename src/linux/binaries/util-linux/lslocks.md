# lslocks — list local file locks held by processes

## Overview

`lslocks` lists the file locks currently held on the system: `flock(2)` locks, `fcntl` POSIX byte-range locks, and (on modern kernels) open-file-description locks. It reads the kernel's lock table from `/proc/locks` and joins it against `/proc/<pid>/fd` to resolve which file each lock actually points at, then renders the result through the standard util-linux table machinery. Typical jobs: finding who holds the lock that blocks an `umount`, an apt run, or an application stuck on startup.

It ships in the `util-linux` package at `/usr/bin/lslocks`. It is often confused with `flock` (the tool that *takes* flock locks — lslocks only observes), with `lsof`/`fuser` (which list open files, not lock state — a file can be open with no lock and locked with no plain open in the same process), and with `lockf`/`fcntl` in code.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/bin/lslocks |
| First appeared | util-linux 2.22 era (early 2010s) |
| Standards | None — Linux procfs-specific |

## Synopsis

```
lslocks [options]
```

Common one-line forms:

```
lslocks                          # all locks, default columns
lslocks -p 1234                  # locks held by one process
lslocks -J                       # JSON output
lslocks -o COMMAND,PID,MODE,PATH # selected columns
```

## How It Works

### Two kernel sources joined into one table

The lock list itself lives in `/proc/locks` — the kernel's global, text-formatted list of every file lock. But `/proc/locks` identifies the locked object only by inode and device; it does not name the file. `lslocks` therefore walks `/proc/<pid>/fd/*`, stats each open descriptor, and matches inode + device numbers to produce the `PATH` column:

```
/proc/locks ────────────▶ lock records: PID, type, mode, range, i_ino, i_dev
                                    │ join on (device, inode)
/proc/<pid>/fd/* ──stat──▶ open-file table: pid, command, path
                                    ▼
   COMMAND PID TYPE SIZE MODE M START END PATH
```

Because the join needs to inspect other processes' file descriptors, unprivileged runs see less: descriptors of other users are hidden by procfs permissions, so those locks appear with a blank/unknown path (unless root). The lock list itself is always global.

### What the columns mean

A real run with a lock held by `flock /tmp/lockdemo -c 'sleep 8'`:

```
$ lslocks
COMMAND   PID  TYPE SIZE MODE  M START END PATH
flock   25978 FLOCK      WRITE 0     0   0 /tmp/lockdemo
```

- `TYPE` — `FLOCK` for `flock(2)` locks, `POSIX` for `fcntl` byte-range locks, `OFDLCK` on modern kernels for open-file-description locks.
- `MODE` — `READ` (shared) or `WRITE` (exclusive).
- `SIZE` — byte length of the lock; empty for FLOCK (whole-file semantic, no byte range).
- `START`/`END` — the locked byte range; `START 0, END 0` means "whole file to EOF" for FLOCK-style locks.
- `M` — mandatory-locking flag; with mandatory locking removed from the kernel (5.15+ deprecated it) this is effectively historical, and it stays `0` on current systems.

Newer util-linux releases expose additional columns via `-o`/`--output-all`, including `INODE`, `MAJ:MIN`, `BLOCKER` (PID of a process blocking a waiting lock request) and `HOLDERS` (OFD locks can have several holders on one description).

### FLOCK vs POSIX in practice

The visible difference matters when debugging: `flock` locks have no byte range and die with the file description; POSIX `fcntl` locks are per-process, per byte-range, and released when *any* fd of that file in the process is closed — a classic source of "my lock vanished" bugs. `lslocks` makes the distinction directly observable, which is why it is the go-to tool for lock deadlock triage.

### The kernel list underneath: /proc/locks

Reading `/proc/locks` directly shows the same locks in the kernel's own notation, one entry per lock with an auto-incremented slot number:

```
$ cat /proc/locks
1: FLOCK ADVISORY WRITE 25978 00:12:158769 0 EOF
```

Fields map to lslocks columns (`FLOCK ADVISORY WRITE`, holder PID, `dev:inode`, byte range). `LEASE` entries also appear in this file — kernel file leases used by delegation protocols — but they are a niche concern; day-to-day triage is about `FLOCK`/`POSIX`/`OFDLCK`. When lslocks output looks suspicious, cross-checking the raw file is the ground truth.

### Cost of the join

Resolving PATH means statting every open descriptor of every relevant process. On hosts with hundreds of thousands of fds (busy container hosts), an unfiltered `lslocks` does measurable work; scoping with `-p` keeps it cheap. If you only need lock records without path resolution, the raw `/proc/locks` read is the free version of the same data.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-p, --pid <pid>` | Only locks held by this process |
| `-o, --output <list>` | Comma-separated column selection |
| `--output-all` | All available columns (adds INODE, MAJ:MIN, BLOCKER, HOLDERS on recent releases) |
| `-J, --json` | JSON output |
| `-r, --raw` | Raw, unpadded output for scripts |
| `-n, --noheadings` | Omit header row |
| `-b, --bytes` | Print SIZE numerically instead of human-readable |
| `-u, --notruncate` | Do not truncate wide text columns |
| `-i, --noinaccessible` | Skip locks whose path cannot be resolved (permissions) |
| `-H, --list-columns` | Print available column names |

## Usage Patterns

```bash
# Who is holding this file? Classic "umount: target is busy" triage
lslocks | grep /mnt/data
```

```bash
# All locks held by one process (e.g. a suspected stuck daemon)
lslocks -p 1234
```

```bash
# Whole-file flock vs byte-range fcntl in one view
lslocks -o COMMAND,PID,TYPE,MODE,START,END,PATH
```

```bash
# JSON snapshot for a monitoring or incident tool
lslocks -J > /tmp/locks.json
```

```bash
# Demonstrate flock lock visibility (two shells)
touch /tmp/demo && flock /tmp/demo -c 'sleep 30' &
lslocks | grep demo
```

```bash
# Test a POSIX byte-range lock with python's fcntl, then observe it
python3 -c "import fcntl; f=open('/tmp/demo','w'); fcntl.lockf(f, fcntl.LOCK_EX); import time; time.sleep(30)" &
sleep 1; lslocks | grep demo
```

```bash
# Script-friendly: raw, no header, specific columns
lslocks -n -r -o PID,MODE,PATH
```

```bash
# Find WRITE locks only (the ones that block other writers)
lslocks -r | awk '$5 == "WRITE"'
```

```bash
# Sizes in plain bytes for arithmetic
lslocks -b -o PID,SIZE,PATH
```

```bash
# Before unmounting a busy filesystem, list every lock rooted in it
lslocks -u -o PID,TYPE,PATH | grep '^ *[0-9].*/mnt/data' | sort -u
```

```bash
# Wait politely until a file lock is released (poll with a timeout)
while lslocks -r | grep -q '/tmp/batch.lock'; do sleep 1; done
```

```bash
# App won't start: is a stale lock holder still around?
lslocks -o PID,COMMAND,TYPE,MODE,PATH | grep -i myapp
```

```bash
# Ground truth for one lock: the kernel's own record
lslocks | grep /tmp/lockdemo; grep -E 'FLOCK.*25978' /proc/locks
```

```bash
# Only shared (READ) locks — who is holding read-side during a migration?
lslocks -r -o PID,COMMAND,MODE,PATH | awk '$3 == "READ"'
```

```bash
# Log lock-holders of a hot file every minute for an hour (cron one-liner)
lslocks -n -r -o PID,COMMAND,PATH >> /var/log/lock-watch.log
```

```bash
# Diff two snapshots to spot long-lived holders (snapshot at t0 and t0+30min)
lslocks -J > /tmp/l0; sleep 1800; lslocks -J > /tmp/l1; diff /tmp/l0 /tmp/l1
```

## Nuances and Gotchas

- **Unprivileged output is incomplete.** Resolving `PATH` requires reading `/proc/<pid>/fd` of the lock holder; without root you see your own locks with paths and other users' locks with empty paths. Run under `sudo` for the full picture — scripts that quietly ran unprivileged are a common source of "lslocks shows nothing".
- **`/proc/locks` is global.** Locks are not namespaced, so inside a container `lslocks` shows host-wide locks — with PIDs that may not exist in your PID namespace. Cross-check `PATH`/`INODE` before acting on a PID.
- **FLOCK rows have no SIZE and START=END=0.** That is not a rendering bug: `flock` has no byte-range concept. Do not treat "END 0" as a zero-length lock.
- **POSIX locks release on any close.** If a process holds a POSIX lock via one fd and closes another fd of the same file, the lock drops — `lslocks` will simply stop showing it. People expect flock semantics and get confused.
- **Mandatory locking is dead.** The `M` column refers to mandatory locking (`mount -o mand` + setgid-noexec files), deprecated in kernel 5.15 and no longer enforceable on modern systems. Seeing `M 0` everywhere is normal, not a misconfiguration.
- **Open with no lock is invisible here.** `lslocks` shows lock state only. For merely-open files, that is `lsof`/`fuser` territory; the two tools answer different questions and are often used together before `umount`.
- **Column padding breaks `cut`.** As with all util-linux tables, use `-r -o ...` (raw) or `-J` rather than fixed-width slicing.
- **Locks and NFS are different worlds.** `/proc/locks` is the *local* VFS lock list; NFSv4 delegations and remote lock managers have their own state. lslocks is not an NFS lock forensics tool.
- **Containers see host locks.** Combined with PID-namespace translation gaps, an lslocks run inside a container can show a lock whose holder PID is meaningless locally — anchor on PATH or INODE instead.
- **Waiting vs holding.** A process blocked *acquiring* a lock is not listed as holding one; it simply shows nothing until granted. `BLOCKER` (newer releases) surfaces who is in the way for pending requests, but a plain lslocks run answers "who holds", not "who waits".
- **The TYPE vocabulary can grow.** Treat unknown TYPE strings (new lock flavors added by future kernels) as pass-through data; scripts that hard-match only `FLOCK|POSIX` silently drop rows.
- **Byte ranges are offsets, not sizes.** START/END are file offsets (END may be `EOF`); converting them to "locked bytes" requires the END semantics, not subtraction blind trust. With `-b`, SIZE is the honest length where one exists.
- **Whole-file flock does not equal "whole current file".** The lock binds the file, not a length snapshot; appends by the holder are covered, which is why FLOCK rows never need a SIZE. Byte-range locks, in contrast, cover exactly the offsets recorded.

## Exit Status

- `0` — success.
- `1` — failure: cannot read `/proc/locks` or `/proc`, invalid option or column list.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`flock`](./flock.md) — takes the whole-file locks this tool lists.
- [`lsns`](./lsns.md) — same procfs-scanning, table-output design for namespaces.
- [`process management`](../../admin/process-management.md) — where `/proc` inspection fits in debugging workflows.

## Interview Questions

### Q: What are the two main lock types lslocks shows, and how do they differ observably?

`FLOCK` rows come from `flock(2)` (whole-file, tied to the open file description, no byte range — hence empty SIZE and 0/0 range). `POSIX` rows come from `fcntl` locks: per-process, byte-range, released when any fd for that file closes in the process. Modern kernels also list `OFDLCK` for open-file-description locks. The TYPE column makes the distinction directly visible during deadlock triage.

### Q: umount says "target is busy" but lsof shows nothing. How does lslocks help?

lsof lists open files; a lock can outlive any *normal* open you recognize (held via a different mount, another namespace-visible path, or by a process whose fds you cannot see unprivileged). `sudo lslocks | grep /mountpoint` shows lock holders by PID and path; combined with `lsof` it covers both "open" and "locked" causes of EBUSY.

### Q: Why might lslocks run unprivileged show a lock with no PATH?

The PATH column is produced by joining `/proc/locks` records (which carry only inode+device) with the holder's `/proc/<pid>/fd` entries. Procfs hides other users' file descriptors, so an unprivileged run cannot resolve their paths — the lock still appears, but anonymous. Running as root completes the join.

### Q: A process holds a POSIX lock on a file, opens the same file a second time, and closes that second fd. What does lslocks show?

Nothing — the lock is gone. POSIX (fcntl) locks are dropped when *any* fd referring to the file in that process is closed, even the unrelated one. This asymmetry versus flock is one of the classic file-locking footguns, and watching the row disappear in `lslocks` is the cleanest way to demonstrate it.

### Q: Why do FLOCK rows show START 0 and END 0, and how is that different from an empty lock?

flock has no byte-range concept, so the kernel records the whole-file lock with range markers rather than sizes; lslocks renders that as 0/0 with an empty SIZE column. It means "entire file", not "zero bytes". Byte-range granularity only exists in the POSIX/OFD rows, where START/END are real offsets.

### Q: How would you monitor for stuck locks in production?

Poll `lslocks -J` (point-in-time snapshots) and diff across samples: a holder whose PID, path, and mode persist far beyond the application's expected critical-section time is the stuck candidate; `BLOCKER` on waiting locks identifies the culprit directly. Correlate with application logs, because lslocks cannot know whether a 30-minute WRITE lock is legitimate batch processing or a leak.

### Q: What is the difference between what lsof and lslocks tell you about the same file?

lsof lists open file descriptors — a file can be open with no lock at all. lslocks lists lock state — a lock can exist without an ordinary visible open (held via a description created differently, or in another namespace's view of the same inode). Before `umount`, you want both: lsof for "who has it open", lslocks for "who has it locked". Either alone produces false negatives.

### Q: How do you get a rate or duration out of lslocks for monitoring?

lslocks is a point-in-time snapshotter; there is no built-in history. Monitoring setups poll it (often `-J` JSON) and diff over time — a lock whose PID and path persist across many samples is a candidate stuck holder; a BLOCKER column value on a waiting lock points at the culprit directly.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/lslocks.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
