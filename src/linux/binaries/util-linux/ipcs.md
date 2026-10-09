# ipcs — report System V IPC facilities status

## Overview

`ipcs` is the classic inspector for System V inter-process communication objects: shared memory segments, message queues, and semaphore arrays. It reads the kernel IPC tables via the `/proc/sysvipc/` interface (or legacy `IPC_INFO`/`SHM_INFO`-style sysctls) and prints them in the traditional fixed-column format that dates back to System V. Ships in the `util-linux` package (Debian bookworm) at `/usr/bin/ipcs`.

Reach for it to answer "what IPC objects exist, who owns them, how big are they, who is attached, and what are the limits?" — the standard first step before `ipcrm` cleanup or when debugging applications that use SysV IPC. It is often confused with its modern sibling `lsipc` (same data, machine-readable formats, richer columns) and with `ipcmk`/`ipcrm` (create/remove, not report). `ipcs` itself changes nothing; it is read-only.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/ipcs |
| First appeared | AT&T System V (early 1980s) |
| Standards | System V IPC (SVID); the command is not POSIX-specified |

## Synopsis

```
ipcs [resource-option...] [output-option]
ipcs -m|-q|-s -i <id>
```

Common one-line forms:

```
ipcs                    # all three classes, default columns
ipcs -m                 # shared memory only
ipcs -m -i 42           # full detail for shmid 42
ipcs -l                 # kernel limits (SHMMAX, MSGMNB, SEMMNI, ...)
```

## How It Works

### Two axes: which class, which output

Every invocation is a cross product of *resource selection* and *display mode*:

```
   select class                 display mode
   ────────────────             ────────────────────────────────
   -m  shared memory            (default)  summary table
   -q  message queues           -t   attach/detach/change times
   -s  semaphores               -p   creator/last-op PIDs
   -a  all (default)            -c   creator and owner uids
                                -l   kernel limits
   -i <id> single object        -u   usage summary counters
        (full detail dump)      --human   sizes human-readable
```

### The default table, column by column

```bash
$ ipcs -m
key        shmid      owner      perms      bytes      nattch     status
0x7fe18120 0          z          644        1048576    0
```

- **key** — the rendezvous value (hex); random for `ipcmk`-created objects.
- **shmid** — the kernel handle programs pass to `shmat(2)`.
- **owner / perms** — current owning uid and octal mode (`0644` = world-readable).
- **bytes** — requested segment size; **nattch** — number of live `shmat` mappings.
- **status** — flags: `dest` (IPC_RMID issued, waiting for last detach), `locked` (shm locked into RAM).

### Single-object detail with -i

`-i <id>` bypasses the table and dumps everything known about one object — the raw `shmctl(..., IPC_STAT)` view:

```bash
$ ipcs -q -i 0

Message Queue msqid=0
uid=1000        gid=1000        cuid=1000       cgid=1000       mode=0644
cbytes=0        qbytes=16384    qnum=0  lspid=0 lrpid=0
send_time=Not set
rcv_time=Not set
change_time=Thu Oct  9 13:38:40 2025
```

Here `qbytes` is the queue capacity (MSGMNB), `qnum` the message count, and `lspid`/`lrpid` the last PIDs to send/receive — the fastest way to see whether a queue is stalled.

### Limits and usage summaries

`ipcs -l` prints the tunables that creation calls are measured against (`SHMMAX`, `SHMALL`, `MSGMNB`, `SEMMNI`…). `ipcs -u` prints aggregate counters — segments allocated, pages resident, swap attempts. Both are the first stop when a create fails or memory accounting looks odd; `lsipc` presents the same information with a USED/USE% column.

### The class tables in detail

**Semaphores** (`ipcs -s`) list *arrays*, not individual semaphores: one `semid` row covers `nsems` counting semaphores. Their values are invisible to `ipcs` — that requires `semctl(GETALL)` in code. **Message queues** (`ipcs -q`) show `used-bytes` (queued payload) and `messages` (count); a queue with bytes but no moving `lspid/lrpid` (add `-p`) is a stalled consumer. **Shared memory** (`ipcs -m`) is where the `dest`/`locked` status flags appear.

Time columns (`-t`) fill three moments per class — for shared memory: last attach, last detach, last change (mode/size mutation). `Not set` means the operation never happened; a queue showing `send_time` advancing while `rcv_time` freezes is the signature of a dead reader.

### Machine-readability: none by design

The default layout is fixed-width and locale-formatted — fine for eyes, hostile for parsers (truncated owner names, merged columns). For scripts prefer the modern sibling:

```bash
lsipc --json          # stable JSON
lsipc -m -o KEY,ID,BYTES,NATTCH --noheadings
```

`ipcs` has no JSON/raw mode in Debian bookworm; treat its output as display-only. The stable machine interface underneath both tools is procfs:

```bash
$ cat /proc/sysvipc/shm
       key      shmid perms                  size  cpid  lpid nattch   uid ...
 558841829          2   644               1048576 26592     0      0  1001 ...
```

There the key is decimal, sizes are bytes, and timestamps are epoch seconds — unwieldy for humans, ideal for `awk`. Notice what the file exposes that the pretty tables do not: separate `uid`/`cuid` ownership pairs and raw `rss`/`swap` residency for shared memory.

### Where the objects live in the kernel

Each IPC class is one kernel table per IPC namespace, keyed exactly as the tools show them:

```
 /proc/sysvipc/shm   ──►  shm_ids.idr     (key, id, perms, size, nattch)
 /proc/sysvipc/sem   ──►  sem_ids.idr     (key, id, perms, nsems)
 /proc/sysvipc/msg   ──►  msg_ids.idr     (key, id, perms, qbytes, qnum)
```

`ipcs` is a formatted reader over that state plus `IPC_STAT`-style detail calls. Nothing it shows is cached — every invocation re-reads current kernel state, which is why it is the honest answer to "what exists right now".

## Options That Matter

| Option | Effect |
| --- | --- |
| `-m, --shmems` | Show shared memory segments |
| `-q, --queues` | Show message queues |
| `-s, --semaphores` | Show semaphore arrays |
| `-a, --all` | Show all classes (default) |
| `-i, --id <id>` | Full detail for one resource (combine with `-m/-q/-s`) |
| `-t, --time` | Attach/detach/change times columns |
| `-p, --pid` | Creator and last-operator PIDs |
| `-c, --creator` | Creator and owner (cuid/cgid vs uid/gid) |
| `-l, --limits` | Kernel limits per class |
| `-u, --summary` | Aggregate usage counters |
| `--human` | Human-readable sizes (KiB/MiB) in the tables |

## Usage Patterns

```bash
# First look: what IPC objects exist right now?
ipcs

# Find the id to hand to ipcrm (classic cleanup pair)
ipcs -m
ipcrm -m 0

# Is anyone actually using the segment? (nattch = attached processes)
ipcs -m

# Which process touched a queue last — stalled consumer hunt
ipcs -q -p
# cpid/lpid columns; cross-check with ps

# Who created it vs who owns it now (chown history)
ipcs -m -c

# What are the kernel limits on this box?
ipcs -l

# Aggregate counters: segments, pages resident, swap activity
ipcs -u

# Full detail for one segment (the shmctl IPC_STAT dump)
ipcs -m -i 0

# Show times to see whether a queue is actually used
ipcs -q -t

# Sizes in human units for a quick capacity review
ipcs -m --human

# Everything the kernel knows about semaphore usage
ipcs -s -u

# Distinguish 'never used' from 'stalled': queue with sends but frozen receives
ipcs -q -p; ipcs -q -t

# Verify a cleanup worked: the table should be empty afterward
ipcrm -m 0 && ipcs -m

# Cross-check uid vs creator (was it chowned after creation?)
ipcs -m -c

# Watch a segment's attachment count while starting a service
ipcs -m; systemctl start myservice; ipcs -m

# Quick scan for permissive modes on any class (0666/0664/0677...)
ipcs -m | grep -E ' (6[67][67]) '
ipcs -q -s | grep -E ' (6[67][67]) '
```

## Nuances and Gotchas

- **Output is not stable across versions/locales** — columns can be wider/narrower, times are locale-formatted. Never `awk` on `ipcs`; use `lsipc` (raw/JSON) or read `/proc/sysvipc/{shm,msg,sem}` directly, which is stable and world-readable.
- **`-i` needs the class flag**: `ipcs -i 0` alone is an error; spell `ipcs -m -i 0`. The id is namespace-scoped — a shmid from another container is "not found" here.
- **`nattch` counts live mappings**, not users: a program that shmat'd and forked shows 2. `nattch 0` with `status dest` means removal is pending on the last detach.
- **Default mode 0644 surprises** — `ipcmk` defaults to world-readable segments; check the `perms` column before assuming privacy, and remember IPC modes have no umask.
- **Times are wall-clock, subject to clock changes**; `Not set` simply means the operation never happened yet (fresh object).
- **Semaphore "arrays"** — one `semid` row in `ipcs -s` covers N semaphores (`nsems` column); per-element values are *not* shown by `ipcs` at all (that needs `semctl GETALL` in code).
- **`bytes` is the requested size**, not pages; resident accounting appears only in `ipcs -u` and `ipcs -l` context. Compare `--human` output against `SHMMAX` with the same units.
- **Limits are per-IPC-namespace** tunables (`kernel.shmmax`, `kernel.sem`); inside containers they may differ from the host despite reading the same sysctls.
- **`ipcs` shows SysV only.** POSIX shared memory (`/dev/shm`), POSIX semaphores, and POSIX message queues (`/dev/mqueue`) are invisible; audit those with `ls` and `lsipc -M/-Q/-S` on newer util-linux.
- **Read-only, but not free** — on huge systems (thousands of segments) the table walk costs a moment; `lsipc -m --noheadings` is measurably cheaper for scripts.
- **`dest` is the only status flag most boxes ever show.** `locked` appears when segments are pinned with `SHM_LOCK` (mlock-style residency guarantees); if you see it unexpectedly, someone is deliberately keeping pages in RAM — accounting implications follow.
- **`ipcs -c` shows TWO owners.** `cuid/cgid` (creator at creation time) vs `uid/gid` (current owner, changeable via `chown`-equivalent `IPC_SET`). Divergence is a legit audit finding, not a display bug.
- **Aggregate counters are page-based.** `ipcs -u` counts pages (SHMALL units), not bytes — comparing them with `bytes` columns needs the page size; `lsipc -b` spares you that conversion.

## Exit Status

- `0` — report produced (even if the selected class is empty).
- `1` — error: invalid option combination, unknown id for `-i`, or inability to read the IPC tables.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`ipcmk`](./ipcmk.md) — creates the objects `ipcs` lists; ids printed there are `ipcs -i` targets.
- [`ipcrm`](./ipcrm.md) — removal, using the ids/keys that `ipcs` reveals.
- [`lsipc`](./lsipc.md) — same data with JSON/raw/export modes and richer columns; the scripting choice.
- [`flock`](./flock.md) — the file-locking alternative whose state is visible in the filesystem instead of kernel tables.
- [`internals`](../../internals.md) — IPC namespaces, kernel object tables, and `/proc/sysvipc` plumbing.

## Interview Questions

### Q: How do you find all System V shared memory on a machine and determine whether anything still uses it?

`ipcs -m` lists segments with `nattch` showing live attachment counts; add `-p` for creator/last-op PIDs and cross-check those PIDs with `ps`. A segment with `nattch 0` and status `dest` is pending removal after the final detach; `nattch > 0` names live users. For scripts, the same data comes from `/proc/sysvipc/shm` or `lsipc -m --json`.

### Q: What is the difference between `ipcs -l` and `ipcs -u`?

`-l` prints the *limits* — the tunables creation calls are checked against (`SHMMAX`, `SHMALL`, `MSGMNB`, `SEMMNI`), matching `sysctl kernel.shm* kernel.msg* kernel.sem`. `-u` prints current *usage* counters — how many objects exist, pages allocated/resident/swapped. Debugging a failed create starts at `-l`; memory accounting starts at `-u`.

### Q: Why shouldn't scripts parse `ipcs` output, and what should they use instead?

The default format is a fixed-width display: values can be truncated (owner names), columns merged when a field is empty, and times follow the locale. `lsipc` offers `--json`, `-r` raw, `--noheadings`, and explicit column selection (`-o KEY,ID,BYTES,NATTCH`), and `/proc/sysvipc/*` is a stable, parseable kernel interface. Reserve `ipcs` for humans.

### Q: You see a segment in `ipcs -m` with `status dest` and `nattch 3`. What happened and what will happen next?

Someone issued `IPC_RMID` (via `ipcrm -m` or `shmctl`). New `shmat` calls fail, but the three attached processes keep valid mappings; the kernel frees the segment when the last one detaches (or exits). Anything that tries to find the object by key or id from now on gets an error — this is the "remove is not revoke" semantics of SysV shared memory.

### Q: How can you tell which process is blocking a message queue?

`ipcs -q -p` shows `cpid` (creator) and `lpid` (last operator) — a queue whose `lspid` keeps changing but `lrpid` froze indicates a dead or stuck receiver. Confirm with `ps -o pid,stat,wchan -p <lpid>`. For exact times, `ipcs -q -t` shows last send/receive/change timestamps, distinguishing "nobody ever sent" (`Not set`) from "receiver stopped".

### Q: Why does `ipcs` not show anything under /dev/shm-based shared memory?

`/dev/shm` objects are POSIX shared memory — a different kernel namespace (`shm_open(3)`) represented as files on a tmpfs, cleaned up with `rm`/`unlink` and visible to `ls`. System V segments (what `ipcs` reports) are anonymous kernel objects addressed by key/id and created by `shmget(2)`. The two mechanisms do not interoperate, which is why modern code often prefers the POSIX form (filesystem visibility, automatic cleanup on unlink-and-close).

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/ipcs.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
