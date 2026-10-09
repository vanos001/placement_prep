# ipcmk — create System V IPC resources (shared memory, semaphores, message queues)

## Overview

`ipcmk` creates System V inter-process communication (IPC) objects from the command line: shared memory segments (`-M`), semaphore arrays (`-S`), and message queues (`-Q`). It is the creation-side counterpart of `ipcrm` (deletion) and `ipcs`/`lsipc` (reporting), and is mostly used for experiments, reproducing IPC bugs, and quick labs where writing a C program that calls `shmget(2)`/`semget(2)`/`msgget(2)` would be overkill.

It ships in the `util-linux` package (Debian bookworm) at `/usr/bin/ipcmk`. Reach for it when you need an IPC object to exist *right now* — e.g. testing whether an application handles a pre-existing segment, checking kernel limits, or demonstrating IPC concepts. It is often confused with the POSIX IPC APIs (`shm_open(3)`, `sem_open(3)`, `mq_open(3)`, exposed under `/dev/shm` and `/dev/mqueue`), which are a different namespace with different tools; classic `ipcmk`/`ipcrm`/`ipcs` speak only System V IPC.

Note the asymmetry with `ipcrm`: `ipcmk` can only *create* with a generated key. It cannot create with a caller-chosen `ftok(3)`-style key, and it does not attach to the segment — a created shared memory segment has `nattch = 0` until some process calls `shmat(2)`.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/ipcmk |
| First appeared | System V IPC toolset lineage (early 1980s); `ipcmk` itself added by util-linux |
| Standards | System V IPC (SVID); the command is not POSIX-specified |

## Synopsis

```
ipcmk [options]
```

Common one-line forms:

```
ipcmk -M 64K            # shared memory segment, 64 KiB
ipcmk -S 8              # semaphore array with 8 elements
ipcmk -Q                # message queue
ipcmk -M 1M -p 0600     # private-ish segment, owner-only permissions
```

## How It Works

### What happens on `ipcmk -M`

`ipcmk` performs exactly the same syscall family an IPC program would:

```
ipcmk -M 1M
   │
   ├─ pick a random 32-bit key (not ftok-derived — see below)
   ├─ shmget(key, 1048576, IPC_CREAT | 0644) ──► kernel allocates a shmid
   └─ print "Shared memory id: <id>"            segment exists, nattch = 0
```

The kernel records the segment in its global IPC namespace table. Every subsequent process in the same IPC namespace can reach the object by *id* (unambiguous) or by *key* (the random value printed as `key` in `ipcs -m`). Creation succeeds only if the requested size is within `SHMMAX` and the total is within `SHMALL` — inspect both with `ipcs -l` or `lsipc`.

### Keys vs IDs

System V IPC objects are double-keyed, and every classic IPC bug starts here:

```
            ┌──────────── kernel IPC table ────────────┐
 key (32bit)│  key        id      perms   owner        │
 ──────────►│  0x7fe18120 0       0644    z            │
 (lookup,   │                                           │
  may clash)│  id = the handle programs pass to shmat() │
            └───────────────────────────────────────────┘
```

- The **id** is the kernel-allocated handle; `shmat(id)` needs it, and it is what `ipcrm -m <id>` removes.
- The **key** is the public rendezvous value; programs that want independent processes to find the same object usually derive it with `ftok(path, proj)`.
- `ipcmk` generates its key randomly, so two `ipcmk` runs almost certainly produce different objects — `ipcmk` cannot be used to emulate "get-or-create by known key" semantics. For deterministic keys you need `ftok(3)` in code (or the same binary doing `shmget` with `IPC_CREAT`).

### Permissions

The default mode is `0644`: world-readable. For shared memory that means any local user who obtains the key/id can `shmat` the segment *read-only* — usually not what you want. Pass `-p 0600` for private data, or `-p 0666`/`0660` when another account must attach read-write. The mode argument is parsed as octal; `ipcmk -p 644` works, `ipcmk -p 640` works, a non-octal digit such as `8` is rejected.

### Sizes and suffixes

`-M <size>` accepts a byte count optionally followed by a binary suffix — `KiB`, `MiB`, `GiB`, … with the `iB` part optional, so `64K`, `64KiB`, and `65536` all mean 65536 bytes. The kernel rounds segment sizes up to page granularity internally, but `ipcs -m` reports the requested size.

### The kernel limits that gate creation

Every create call is measured against namespace-wide tunables. Knowing their names turns a mysterious `ipcmk` failure into a one-line diagnosis:

```
sysctl                       lsipc row    meaning
kernel.shmmax     SHMMAX     max bytes of ONE segment
kernel.shmall     SHMALL     total pages usable by ALL segments
kernel.shmmni     SHMMNI     max number of segments
kernel.sem        SEMMNI/    vector: SEMMSL SEMMNS SEMOPM SEMMNI
                  SEMMNS     (arrays, semaphores, ops, identifiers)
kernel.msgmni     MSGMNI     max message queues
kernel.msgmax     MSGMAX     max size of ONE message
kernel.msgmnb     MSGMNB     default bytes per queue
```

`ipcmk -M 2G` failing on a host with `shmmax = 1G` returns `EINVAL`; exhausting `SHMMNI`/`SEMMNI` returns `ENOSPC`. `ipcs -l` or `lsipc` (with its USE% column) shows which one is the wall.

### What the id is good for

`ipcmk` stops at creation; the id it prints is consumed by:

- `ipcs -m -i <id>` — inspect the object's full state (mode, size, attach count, times).
- `ipcrm -m <id>` — remove it (or, in real code, the process exit path).
- application code — `shmat(id, NULL, 0)` maps the segment into a process address space; nothing else can actually *use* the memory. A segment nobody attaches is pure bookkeeping.

This is why `ipcmk` demos usually pair with a small C/Python harness — the tool creates the stage, the program performs.

### System V vs POSIX IPC, at creation time

`ipcmk` speaks only System V. The POSIX flavor creates differently and looks different to the admin:

| Aspect | System V (`ipcmk`) | POSIX (`shm_open`/`sem_open`/`mq_open`) |
| --- | --- | --- |
| Naming | numeric key, kernel-assigned id | name in a filesystem (`/dev/shm/...`, `/dev/mqueue/...`) |
| Visibility | `ipcs`/`lsipc`/`/proc/sysvipc` | `ls /dev/shm`, `ls /dev/mqueue` |
| Cleanup | explicit `ipcrm` (or namespace death) | `unlink` when refcount hits zero |
| Persistence | until removed/reboot | until unlinked (files persist) |
| Limits | `kernel.shm*`/`kernel.sem` | `RLIMIT_NOFILE`-ish + mounts |

Debian bookworm's util-linux tools do not create or list POSIX IPC; anything under `/dev/shm` belongs to the POSIX world.

### Resource kinds, one mode each

`ipcmk` does exactly one thing per invocation; combine by running it several times:

```bash
$ ipcmk -M 1M          # shared memory segment
Shared memory id: 0
$ ipcmk -S 2           # semaphore array with 2 elements
Semaphore id: 0
$ ipcmk -Q             # message queue
Message queue id: 0
```

Semaphores are created as *arrays*: `-S 8` gives eight counting semaphores addressable by `semctl`/`semop` index 0–7. Message queues are created empty with the default queue byte limit (`MSGMNB`, see `ipcs -l`).

## Options That Matter

| Option | Effect |
| --- | --- |
| `-M, --shmem <size>` | Create a shared memory segment of `<size>` bytes (suffixes `K`/`M`/`G`… allowed) |
| `-S, --semaphore <n>` | Create a semaphore array with `<n>` elements |
| `-Q, --queue` | Create a message queue |
| `-p, --mode <mode>` | Permission bits for the new resource (octal, default `0644`) |
| `-h, --help` | Usage summary |
| `-V, --version` | Version string |

There is deliberately no option to choose a key: System V `get` calls with `IPC_CREAT | IPC_EXCL` and an application-chosen key belong in program code, not in this tool.

## Usage Patterns

```bash
# Spin up a 1 MiB segment for an IPC experiment and note the id
ipcmk -M 1M
# Shared memory id: 0

# Use the printed id immediately: inspect, then remove
ID=$(ipcmk -M 64K | awk '{print $4}')
ipcs -m -i "$ID"
ipcrm -m "$ID"

# Create a segment with owner-only permissions (the sane default for private data)
ipcmk -M 4M -p 0600

# Create an 8-element semaphore array for a producer/consumer lab
ipcmk -S 8 -p 0660

# Create a message queue sized for testing, then check its byte limit
ipcmk -Q
ipcs -q -l

# Build the whole demo set in one go (segment + semaphores + queue)
ipcmk -M 1M -p 0600 && ipcmk -S 4 && ipcmk -Q

# Verify what was created (sizes, keys, nattch) before handing ids to a program
ipcs -m

# Check whether the requested size is even possible on this kernel
ipcs -l        # compare against SHMMAX / SHMALL
lsipc          # same limits in a unified LIMIT/USED/USE% view

# Reproduce a "resource already exists" bug: create, run the app, watch EEXIST
ipcmk -M 1M; ./myapp; ipcrm -m 0

# Stress-test cleanup logic: create many small segments, then drop them all
for i in 1 2 3 4 5; do ipcmk -M 4K; done
ipcs -m

# Prove a limit exists: create segments until the kernel says no
while ipcmk -M 4K 2>/dev/null; do :; done; echo "stopped at $(ipcs -m | grep -c ^0x)"
ipcrm --all=shm

# Hand a created segment to a program: verify its state first
ID=$(ipcmk -M 1M -p 0600 | awk '{print $4}')
ipcs -m -i "$ID"        # mode=0600, nattch=0, size=1048576

# Reproduce an EEXIST bug deterministically: app expects its own key,
# so pre-creating with ipcmk shows whether it collides or coexists
ipcmk -M 1M && ./app-that-creates-shm; ipcs -m

# Namespace isolation demo (inside vs outside a container)
ipcmk -M 1M            # visible in this namespace only
ipcs -m                # empty from the host for the same container
```

## Nuances and Gotchas

- **Default mode 0644 is world-readable.** Shared memory containing anything sensitive should be created with `-p 0600`. Anyone with the key (and read access) can map the segment read-only.
- **Random keys are not ftok keys.** Programs that expect to find "the" segment by a well-known key derived from a filename will *not* see an `ipcmk`-created object; conversely `ipcmk` may collide with an existing key in rare cases (the kernel rejects duplicates for `IPC_CREAT|IPC_EXCL`, `ipcmk` retries with a new key).
- **`nattch = 0` is normal at creation.** `ipcmk` never attaches; a segment with no attachments and no id-holder is even a candidate for kernel reclamation under some configurations. Attach from a real program to make the object durable while in use.
- **Nothing survives reboot.** System V IPC objects live in kernel memory of the current IPC namespace. Containers each have their own namespace: an `ipcmk` inside a container is invisible from the host and vice versa.
- **Limits bite at create time.** `SHMMAX` (max single segment), `SHMALL` (total pages), `SEMMNI`/`MSGMNI` (counts) are tunables (`sysctl kernel.shmmax kernel.shmall kernel.sem`). A create that returns `ENOSPC`/`EINVAL` usually means a limit, not a syntax error — confirm with `ipcs -l`.
- **Sudo does not transfer ownership.** Objects belong to the creating uid; `ipcrm` cleanup by another user needs root, and `--all`-style wipes on multi-user hosts destroy *other people's* objects.
- **Octal mode parsing.** `-p 644` is fine, but remember it is parsed as octal — `-p 777` grants everything, and there is no umask influence on IPC objects.
- **Not portable.** BSD/macOS ship no `ipcmk`; busybox has none. For portable experiments use a few lines of C against `sys/ipc.h`, or POSIX IPC under `/dev/shm` (`ls /dev/shm`).
- **`ipcmk` cannot attach, write, or size-check contents.** Creating a segment is not using it; a demo that ends at `ipcmk` proves only that the kernel accepted the reservation. Pair with a program for anything meaningful.
- **Semaphore arrays are created empty at value 0.** A fresh `ipcmk -S 4` array blocks every `semop` with wait-for-zero semantics until someone sets values via `semctl SETVAL`/`SETALL` — a create-then-deadlock pattern that puzzles first-timers.
- **Message queues start at the default capacity.** `MSGMNB` (commonly 16 KiB) is the queue's byte limit; `ipcmk -Q` cannot change it. `msgctl IPC_SET` in code adjusts `qbytes` per queue — or fix the sysctl for the default.
- **Sequential ids aid testing, but are not a contract.** Ids increment across the namespace (new objects often get `id 0` in a fresh container); never treat low ids as stable handles across cleanups — capture and pass the printed value.

## Exit Status

- `0` — resource created successfully; the id is printed on stdout.
- `1` — creation failed (bad size/mode, kernel limit reached, resource type not supported); an error goes to stderr and nothing is created.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`ipcrm`](./ipcrm.md) — delete the resources `ipcmk` creates; lowercase = by id, uppercase = by key.
- [`ipcs`](./ipcs.md) — classic reporter listing keys, ids, sizes, attachment counts.
- [`lsipc`](./lsipc.md) — modern, script-friendly IPC reporter with JSON/raw output and limit overviews.
- [`flock`](./flock.md) — the file-locking alternative when persistent-on-disk serialization is preferred over SysV objects.
- [`internals`](../../internals.md) — how the kernel organizes IPC namespaces and object tables.

## Interview Questions

### Q: What does `ipcmk -M 1M` actually do, and what does it not do?

It calls `shmget(2)` with a randomly generated key, `IPC_CREAT`, size 1 MiB and mode 0644, printing the allocated shmid. It does *not* attach the segment (`nattch` stays 0), does not let you choose the key, and the object dies with the kernel namespace at reboot. Actual use still requires a program (or `shmat`-capable tool) to map and touch the memory.

### Q: How would you make two unrelated processes share memory using only System V IPC?

Both call `shmget` with the *same key* and `IPC_CREAT` (first one creates, second one finds), then `shmat`. The key is typically derived with `ftok(pathname, proj_id)` so both sides agree without coordination. `ipcmk` cannot play this role directly because its keys are random — it is a lab/demo tool, not an application rendezvous mechanism.

### Q: A script does `ipcmk -M 2G` and fails. Walk through your debugging.

First check the two likely limits: `ipcs -l` (or `lsipc`) shows `SHMMAX` — if 2 GiB exceeds it, the create fails with `EINVAL`. If `SHMMAX` is fine, check `SHMALL` (total system pages committed to shared memory) and whether the namespace is exhausted (`ipcs -m | wc`). Also confirm the size suffix parsed as expected (`-M 2G` vs a typo). The failure is a kernel limit far more often than a syntax problem.

### Q: Why does the classic advice say "use file locking instead of System V IPC" for shell scripts?

SysV objects are invisible to the filesystem, have no stale-lock-free lifetime story (an object outlives its creator until explicitly removed or the namespace dies), require C calls to operate semaphores, and their cleanup is manual (`ipcrm`). `flock`-style file locks release automatically when the process exits and live in the normal filesystem, which is why shell-level coordination almost always prefers them.

### Q: What is the difference between the `key` and the `id` of an IPC object?

The id is the kernel-allocated handle programs pass to `shmat`/`semop`/`msgsnd`; it is unique in the namespace. The key is a 32-bit rendezvous value used at creation/lookup time (often via `ftok`); multiple lookups with one key yield one id. Tools mirror the split: `ipcrm -m <id>` vs `ipcrm -M <key>`, lowercase for ids and uppercase for keys.

### Q: Why does `ipcs` show a segment you just created with `nattch 0`, and why can that be a problem?

`ipcmk` only allocates the object; nobody has called `shmat(2)`. If the creator process exits without holding the id/key anywhere, the segment lingers until explicitly removed — a common source of "orphan" IPC objects after test runs. Habit: create, attach, use, and `ipcrm` within the same controlled script.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/ipcmk.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
