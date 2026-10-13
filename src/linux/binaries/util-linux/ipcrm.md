# ipcrm — remove System V IPC resources

## Overview

`ipcrm` deletes System V inter-process communication objects: shared memory segments, semaphore arrays, and message queues. Every object that `ipcmk` creates, that an application leaks, or that survives a crashed program ends its life through `ipcrm` (or at reboot when the IPC namespace dies). It ships in the `util-linux` package (Debian bookworm) at `/usr/bin/ipcrm`.

`ipcrm` is often confused with its look-alike option alphabet: lowercase flags (`-m`, `-q`, `-s`) remove *by id*, uppercase flags (`-M`, `-Q`, `-S`) remove *by key*, and the letter itself selects the resource type (m = shared memory, q = queue, s = semaphores). It is also confused with POSIX IPC cleanup (`/dev/shm` files, `sem_unlink`/`mq_unlink`), which is a different namespace this tool does not touch.

Deletion permission follows the IPC model: a non-root user may remove only resources whose `uid` or `cuid` matches their own. Root can remove anything — which is exactly why `ipcrm --all` on a shared machine is a loaded weapon.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/ipcrm |
| First appeared | AT&T System V (early 1980s) |
| Standards | System V IPC (SVID); the command is not POSIX-specified |

## Synopsis

```
ipcrm [options]
ipcrm shm|msg|sem <id>...
```

Common one-line forms:

```
ipcrm -m 42             # remove shared memory segment with id 42
ipcrm -M 0x7fe18120     # remove segment by key
ipcrm -a                # remove ALL SysV IPC resources you own (careful!)
ipcrm shm 42            # legacy positional syntax, still accepted
```

## How It Works

### One syscall per removal

Each option translates directly into a control syscall:

```
ipcrm -m <id>     ──►  shmctl(id, IPC_RMID, 0)
ipcrm -s <id>     ──►  semctl(id, 0, IPC_RMID)
ipcrm -q <id>     ──►  msgctl(id, IPC_RMID, 0)
```

The kernel marks the object for deletion:

- **Shared memory:** the segment becomes inaccessible to new `shmat(2)` calls; already-attached processes keep their mapping until they detach or exit, then the memory is freed. `ipcs -m` shows the segment with a small `dest` status flag until the last detach.
- **Semaphores:** the array is destroyed immediately; pending `semop` operations fail.
- **Message queues:** queued messages are dropped; blocked senders/receivers wake with an error.

### The id/key option matrix

```
              by id (lowercase)      by key (uppercase)
 shmem        ipcrm -m <shmid>       ipcrm -M <key>
 msg queue    ipcrm -q <msqid>       ipcrm -Q <key>
 semaphore    ipcrm -s <semid>       ipcrm -S <key>
```

The casing rule is consistent: **lowercase = id, uppercase = key**, while the letter encodes the type. `ipcs` prints both columns, so the usual workflow is `ipcs` → copy the id → `ipcrm -m <id>`.

### Lifecycle of a doomed segment

Removal is a state transition, not an instant:

```
  ipcrm -m 0
      │
      ▼
 ┌────────────────────────────────────────────────────────────┐
 │ status: dest (destroy pending)                             │
 │  • new shmat() calls fail with EINVAL/ENOMEM               │
 │  • existing mappings keep working (read AND write)         │
 │  • ipcs -m keeps listing the segment                       │
 └────────────────────────────────────────────────────────────┘
      │  last process detaches or exits
      ▼
  kernel frees pages, shmid slot retired, next id is higher
```

For queues and semaphores the transition is immediate (no attachment concept); waiters receive `EIDRM`. The `dest` flag exists only for shared memory — and only while at least one mapping survives.

### Cleanup in CI and containers

Two environments make `ipcrm` part of the daily routine:

- **Test runners** leak SysV objects from crashed suites. A post-job `ipcrm --all=shm` scoped to the runner user (not root) reclaims the namespace cheaply; capture-and-trap cleanup inside the suite is the better fix.
- **Containers** own an isolated IPC namespace, so a container-wide sweep never bleeds into the host — but it also cannot reach leftovers left by *another* container. Debug leftover objects from inside the namespace that owns them (`nsenter -t <pid> -i` from the host gets you there).

### Finding the culprit before removing

Blind removal is how production incidents start. The standard triage pair before any `ipcrm`:

```bash
ipcs -m -p          # cpid/lpid: creator and last operator PIDs
lsipc -m -o ID,NATTCH,CPID,LPID,COMMAND --notruncate   # + executable name
```

`COMMAND` names the binary that created the object while its process is still alive; `cpid` survives even after the creator exited. Cross-check with `ps -fp <cpid>` and only then remove. Removing an object a *running* service still uses is rarely fatal on the spot (mappings persist) but guarantees a confusing failure at the service's next restart or new attach.

### Legacy syntax

The original form still works and is occasionally seen in old scripts:

```bash
$ ipcrm shm 42
resource(s) deleted
```

Prefer the option form in new code; the legacy form only addresses objects by id.

### Bulk removal

`--all[=<type>]` removes everything (optionally restricted to `shm`, `msg`, or `sem`) that the invoking user — or root — is allowed to remove. It exists for the "clean the lab" case and for wiping leftovers in containers; on multi-user hosts scope it with `=<type>` or, better, target explicit ids.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-m, --shmem-id <id>` | Remove shared memory segment by id |
| `-M, --shmem-key <key>` | Remove shared memory segment by key |
| `-q, --queue-id <id>` | Remove message queue by id |
| `-Q, --queue-key <key>` | Remove message queue by key |
| `-s, --semaphore-id <id>` | Remove semaphore array by id |
| `-S, --semaphore-key <key>` | Remove semaphore array by key |
| `-a, --all[=shm\|msg\|sem]` | Remove all resources (optionally one class) you may remove |
| `-v, --verbose` | Explain each removal as it happens |
| `shm\|msg\|sem <id>...` | Legacy positional form, ids only |

## Usage Patterns

```bash
# Standard cleanup: list, then remove by id
ipcs -m
ipcrm -m 0

# Remove by key when only the key is known (e.g. from application logs)
ipcrm -M 0x7fe18120

# Clear out a demo set in one call
ipcrm -m 0 -s 1 -q 0

# Wipe only shared memory, leaving semaphores and queues alone
ipcrm --all=shm

# Full sweep as root on a throwaway container
sudo ipcrm -a

# Tear down exactly what this script created (capture ids, remove in trap)
ID=$(ipcmk -M 1M -p 0600 | awk '{print $4}')
trap 'ipcrm -m "$ID"' EXIT
./use_segment.sh

# Verbose mode shows what was actually deleted
ipcrm -v -a=shm
# resource(s) deleted: shmid 3

# Remove a leaked segment that a crashed test left behind
ipcs -m | awk '$6 == 0 && $1 ~ /^0x/ {print $2}' | xargs -r -n1 ipcrm -m

# Legacy syntax still found in old init scripts
ipcrm sem 5 && ipcrm shm 7

# Root removing a dead user's leftovers
sudo ipcrm -m 12

# CI teardown: drop this runner's shared memory and semaphores only
ipcrm --all=shm && ipcrm --all=sem

# Find and remove only ORPHANED segments (zero attachments, dest-less)
lsipc -m -o ID,NATTCH --noheadings | awk '$2 == 0 {print $1}' \
  | xargs -r -n1 ipcrm -m

# Prove the dest-flag semantics: remove, then watch nattch/flags
ID=$(ipcmk -M 1M | awk '{print $4}')
ipcrm -m "$ID"          # removal issued
ipcs -m                 # segment still listed, status dest

# Enter a container's IPC namespace from the host to clean its leftovers
sudo nsenter -t "$(pgrep -f mycontainer-init)" -i ipcrm --all=shm

# Safely delete by key captured from an application config
KEY=$(awk -F'[=,]' '/shm_key/{print $2}' /etc/myapp.conf)
ipcrm -M "$KEY"

# Dry-run shape: print what WOULD be removed, then act
lsipc -m -o ID,KEY,COMMAND --notruncate
# ...review, then replace the listing with ipcrm -m <id> ...

# Reclaim space after a crashed benchmark suite (this user only)
ipcrm --all=shm 2>/dev/null; ipcrm --all=sem 2>/dev/null; ipcs
```

## Nuances and Gotchas

- **`--all` is not scoped by default.** As root it deletes *every* IPC resource on the machine, including ones owned by running services (databases, message systems, licensed software that uses SysV semaphores). Always prefer explicit ids, or `--all=<type>`.
- **"removed" ≠ "gone" for shared memory.** After `IPC_RMID`, attached processes keep working until they detach; memory is reclaimed only after the last detach. The segment shows the `dest` (destroy) status flag in `ipcs -m`. Debugging tip: a program "still using" a removed segment is normal, not a leak.
- **Case is semantic, not cosmetic.** `ipcrm -m 0` (by id) vs `ipcrm -M 0` (by key `0` — probably not what you meant). Mixing them up yields "specified id not found" errors that look like the resource vanished.
- **Keys are usually written `0x…` in `ipcs` but accepted in decimal too.** `ipcrm -M 2145601024` and `-M 0x7fe18120` can address the same object; pass the literal exactly as you have it and check the error message if unsure.
- **Permissions are uid/cuid based.** You can remove an object if you created it or own it now; otherwise `EPERM`. `sudo` is the escalation path — and the reason admins must be careful with `--all`.
- **Deletion wakes waiters with errors.** Removing a queue or semaphore set that other processes are blocked on delivers `EIDRM`/`EINTR`-style failures; applications that do not handle `EIDRM` may crash or hang in loops.
- **No undo.** There is no unremove; the id space increments monotonically, so even a recreated object gets a *new* id. Anything caching an old id will fail afterward.
- **POSIX IPC is untouched.** `/dev/shm` objects and POSIX semaphores/message queues are filesystem entries; clean them with `rm`/`unlink`-style APIs, not `ipcrm`.
- **`nsenter` is the host-side escape hatch.** Leftovers inside a container's IPC namespace are invisible to host `ipcs`; enter the namespace (`nsenter -t <pid> -i`) to see and remove them — and remember the reverse: container-internal cleanup cannot touch host objects.
- **Orphan detection needs nattch, not just presence.** A listed segment may be actively used by a detached-background worker; filter on `NATTCH == 0` plus PID checks (`ipcs -m -p`) before removing, or you will delete live data invisibly — the mapping keeps working and nobody gets an error until restart.
- **Verbose mode is your audit trail.** `ipcrm -v` prints each deletion; in shared environments wrap bulk removals with it and log to the session transcript — `--all` without `-v` is an unrecorded operation.
- **Namespaces matter.** Inside a container, `ipcrm` only affects that container's IPC namespace. Host-level leftovers are invisible (and unreachable) from inside.

## Exit Status

- `0` — all requested resources were removed (or nothing needed doing).
- `1` — at least one operation failed: id/key not found, permission denied (EPERM), or invalid arguments. stderr carries the reason; processing of further arguments continues.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`ipcmk`](./ipcmk.md) — creation-side twin; its printed ids are `ipcrm` targets.
- [`ipcs`](./ipcs.md) — the listing tool you always run first to find ids and keys.
- [`lsipc`](./lsipc.md) — script-friendly IPC reporter (JSON/raw) for building automated cleanup.
- [`flock`](./flock.md) — file-based locking with automatic release, avoiding manual IPC cleanup entirely.
- [`permissions`](../../admin/permissions.md) — why uid/cuid ownership governs who may delete an IPC object.
- [`internals`](../../internals.md) — kernel IPC tables, namespaces, and the `dest`-flag lifecycle.

## Interview Questions

### Q: What happens to processes currently attached to a shared memory segment when you `ipcrm -m` it?

`IPC_RMID` only prevents new attachments and schedules destruction. Existing mappings stay valid — attached processes read and write normally until they detach or exit; the kernel frees the memory after the last detach. `ipcs -m` marks such a segment with the `dest` status flag. This is why "I deleted it" never stops a running consumer.

### Q: Explain the lowercase/uppercase option convention of ipcrm.

The letter selects the resource type (m = shared memory, q = message queue, s = semaphore set); the case selects the addressing: lowercase removes by numeric id, uppercase by key. So `-q 3` removes msqid 3 while `-Q 0x1a` removes the queue whose key is `0x1a`. One consistent rule across all three types.

### Q: A crashed application left a semaphore set with `SEM_UNDO`-adjusted values. How do you clean up safely?

Identify it with `ipcs -s`, verify nobody still uses it (`ipcs -s -p` shows creator/last-op PIDs), then `ipcrm -s <id>`. Any process blocked in `semop` on it will fail with `EIDRM` — make sure the application tolerates that before removing. As root you can remove regardless of ownership; otherwise you must be the owner or creator.

### Q: Why is `sudo ipcrm -a` considered dangerous on production machines?

`-a` deletes every IPC object the operator may remove — as root, that is all of them, including *attached* segments: mappings keep working until the process restarts or attempts a new attach and fails with EINVAL, so the damage surfaces later and far from the cause. Widely deployed software (old Oracle, IBM products, some telephony stacks, PostgreSQL's SysV mode) keeps semaphores and shared memory for its entire runtime. Scoped removal by id, or `--all=<type>` after inventorying with `ipcs`, is the safe pattern.

### Q: How would you write a script that never leaks the SysV resources it creates?

Create with `ipcmk`, capture the printed id, and register cleanup in an `EXIT` trap (`trap 'ipcrm -m "$ID"' EXIT`), also covering signals via `trap ... INT TERM`. Because SysV objects outlive their creator, the trap is the only line of defense against leftovers after a crash — or avoid SysV entirely and use file-based `flock`, which the kernel releases automatically at process death.

### Q: A monitoring script calls `ipcrm --all=shm` nightly as root. What is the realistic worst case?

It deletes segments owned by any root service — databases, application servers, license daemons — including attached ones, which keeps working silently until those processes restart or attempt a fresh attach and get EINVAL. The failure surfaces far from the deletion, making correlation painful. Scope it: run as the owning user, harvest explicit ids from `lsipc`, or filter on `NATTCH == 0` plus a known `COMMAND` before deleting.

### Q: Which kernel object survives `ipcrm` removal: a message queue's queued messages, a semaphore's `semadj`, or an attached shared memory mapping?

The attached mapping survives: `IPC_RMID` on a segment does not unmap existing attachments. Queued messages are destroyed with the queue, and per-process `semadj` undo values disappear with the semaphore set (or the process). This asymmetry is the classic interview hook for "remove is not revoke".

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/ipcrm.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
