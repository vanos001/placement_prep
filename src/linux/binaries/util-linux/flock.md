# flock — acquire an advisory lock from shell scripts

## Overview

`flock` applies advisory file locks to files or directories from the command line, making it the standard tool for serializing cron jobs, systemd services, and shell pipelines that must never run concurrently. It wraps the Linux `flock(2)` syscall (and, with `--fcntl`, open-file-description `fcntl` locks), and its killer feature is lifespan management: the lock is held exactly as long as the locked command runs and is released automatically by the kernel when the process dies — even on crash or `kill -9`.

It ships in the `util-linux` package at `/usr/bin/flock`. Reach for it whenever two copies of a job would corrupt state: nightly backups, log rotation helpers, cache rebuilds, mail fetchers. It is often confused with the `flock` C-library call it wraps (byte-range `lockf`/`fcntl(F_SETLK)` locking), with the mkdir/create-and-check lockfile idiom (which leaks stale locks), and with `lockf` (POSIX record locks with different semantics).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/flock |
| First appeared | 1990s standalone tool by H. Peter Anvin; shipped with util-linux for decades |
| Standards | None (BSD flock(2) syscall; no POSIX command standard) |

## Synopsis

```
flock [options] <file>|<directory> <command> [<argument>...]
flock [options] <file>|<directory> -c <command>
flock [options] <file descriptor number>
```

Common one-line forms:

```
flock -n /run/lock/job.lock /usr/local/bin/job.sh   # skip if already running
flock -w 30 /run/lock/job.lock job.sh               # wait up to 30s
flock -s shared.lock -c 'read-only inspection'      # shared lock
exec 9>lockfile; flock 9; critical_section          # fd form inside a script
```

## How It Works

### Locks live on the open file description

`flock(2)` associates an exclusive or shared lock with an *open file description* (the kernel object created by `open()`, shared across `dup()` and inherited by children). Consequences that interviews probe:

- The lock does not depend on file content: the lockfile can stay empty.
- A lock is released when the last file descriptor referring to that open file description is closed, or when the holding process exits — any exit, including a signal death. There is no stale-lock problem by construction.
- Locks are *advisory*: cooperating processes honor them; oblivious processes are not stopped.
- Two processes that each `open()` the file get separate open file descriptions and can therefore contend — which is exactly the desired behavior for `flock file command`.

### The three invocation forms

```
form 1: flock [options] FILE COMMAND...   # fork COMMAND with the lock held
form 2: flock [options] FILE -c 'string'  # run string through sh -c
form 3: flock [options] FD                # lock fd FD in the current process
```

Form 1 is the workhorse: `flock` opens (or creates) the lock file, acquires the lock, then `exec`s or forks the command while holding it. Form 3 is used inside scripts with redirection (`exec 9>file; flock 9; ...`), letting you release precisely by closing fd 9.

```
 caller A                    kernel                     caller B
   │ open lockfile             │                          │
   │ flock(LOCK_EX) ──────────►│ granted (fd A)           │
   │ run backup.sh             │                          │
   │                           │◄── flock(LOCK_EX|NB) ────│ B: EWOULDBLOCK
   │ exit / close fd ─────────►│ lock released            │   exit code 1
   │                           │◄── flock(LOCK_EX) ───────│ B: granted
```

### Waiting strategies

Without flags, `flock` blocks until the lock is free. `-n, --nonblock` fails immediately with the conflict exit code; `-w, --timeout <secs>` gives up after a delay. The conflict exit code defaults to `1` but is settable with `-E, --conflict-exit-code <n>` so scripts can distinguish "someone else is running" (42, say) from "the job itself failed" (its own status).

### flock(2) vs fcntl locks

`flock(2)` locks cover the whole file and are keyed to the open file description. `fcntl(F_SETLK)` record locks cover byte ranges and are keyed to the process — closing *any* fd of that file drops them all, a classic fork-related trap. The two lock spaces are independent: a process holding `flock(2)` does not block an `fcntl` locker. `flock --fcntl` uses `fcntl(F_OFD_SETLK)` (open-file-description locks, Linux 3.15+), which behave like `flock(2)` but interoperate with NFSv4-style setups and tools that speak `fcntl`.

| Property | flock(2) | fcntl(F_SETLK) | fcntl(F_OFD_SETLK) |
| --- | --- | --- | --- |
| Granularity | whole file | byte ranges | byte ranges |
| Owned by | open file description | process | open file description |
| Inherited on fork | yes | no | yes |
| Dropped when | last related fd closes | *any* fd of the file closes | last related fd closes |
| Visible to the other spaces | no | no | no |
| NFS | emulated/unsupported | yes (NFSv4) | yes (modern) |

The command's `--fcntl` switch picks the right column for cross-tool locking — e.g. coordinating with applications that use POSIX record locks.

### Choosing where the lock file lives

The lock file is a marker, not a resource; treat it as infrastructure:

- `/run/lock` — the canonical place: tmpfs, wiped at boot, group-writable (`lock`) on Debian. Use it for system services.
- `/tmp` — fine for user-level one-offs, but cleaned by tmp cleaners mid-run on some distros (which would silently reset protection).
- Next to the data — convenient, but backup/sync tools may copy or delete the zero-byte file, and some editors "clean" them.
- Never on NFS for classic flock(2) — semantics vary; prefer `--fcntl` or a coordinator.

Name it after the resource, not the tool: `/run/lock/nightly-backup.lock` beats `/run/lock/flock1.lock` when three different scripts all need to agree.

### Waiting, signals, and observability

A blocking `flock(fd, LOCK_EX)` parks the caller on the lock's kernel wait queue — no polling, no CPU burned. The wait is *interruptible*: a signal breaks it and the acquisition fails. That is exactly what makes `timeout` composable (it SIGTERMs the waiting flock, exit 124) and why Ctrl-C never wedges a waiting script. Verified behavior:

```bash
$ (exec 9>/tmp/lk; flock 9; exec sleep 60) &
$ timeout 1 flock /tmp/lk true; echo $?     # gave up while waiting
124
```

The kernel exposes every advisory lock in `/proc/locks` — type (`FLOCK`/`POSIX`/`OFDLCK`), advisory mode, read/write class, owning PID, and the lock object's `dev:inode`. `lslocks` renders the same table with paths and command names:

```
2: FLOCK  ADVISORY  READ 909 00:2b:72057594037928184 0 EOF
   ^type             ^mode ^class ^pid ^lockfile's dev:inode
```

The inode field is the operational hook: match a stuck job's lockfile with `find /run/lock -inum <inode>` (or read lslocks' PATH column), then inspect the holder's tree with `ps`/`pstree`. The overwhelmingly common finding is the inherited-fd daemon covered in the gotchas below.

### Crash safety, demonstrated

The property that sells flock over lockfiles is observable in four lines: kill the sole fd holder and the lock is gone — no sweep, no `.stale` files, no recovery logic. Here the holder is a `sleep` process (the `exec` makes the pid you capture the actual fd holder):

```bash
sh -c 'exec 9>/tmp/demo.lock; flock 9; exec sleep 30' & HOLDER=$!
sleep 0.5; kill -9 "$HOLDER"
flock -n /tmp/demo.lock true && echo "free - no stale-lock sweep needed"
# free - no stale-lock sweep needed
```

`kill -9` is the strongest possible kill and it still cannot leak the lock: the open file description dies with its last file descriptor, and lock teardown is part of that. Every lockfile-based scheme reimplements this behavior with timestamp heuristics and gets it wrong under load.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-s, --shared` | Shared (read) lock; many holders allowed |
| `-x, --exclusive` | Exclusive lock — the default |
| `-u, --unlock` | Drop a previously taken lock (mainly fd form) |
| `-n, --nonblock` | Fail immediately instead of waiting |
| `-w, --timeout <secs>` | Wait at most `<secs>` seconds, then fail |
| `-E, --conflict-exit-code <n>` | Exit code on lock conflict/timeout (default 1, range 0-255) |
| `-c, --command <string>` | Run a single command string via `sh -c` |
| `-o, --close` | Close the lock fd before exec'ing the command |
| `-F, --no-fork` | Execute the command without forking (keeps the child as flock itself) |
| `--fcntl` | Use `fcntl(F_OFD_SETLK)` instead of `flock(2)` |
| `--verbose` | Report lock acquisition/release on stderr |

## Usage Patterns

```bash
# Never let two cron runs of the same backup overlap
flock -n /run/lock/nightly-backup.lock /usr/local/bin/backup.sh

# Wait up to 5 minutes for a previous run to finish, then give up distinctly
flock -w 300 -E 42 /run/lock/nightly-backup.lock /usr/local/bin/backup.sh
# exit 42  => superseded by another run; other codes => backup's own status

# Serialize with a shell one-liner (note -c quoting)
flock /run/lock/cache.lock -c 'rebuild_index --quiet'

# Shared lock for readers, exclusive for the one writer
flock -s /srv/data.lock  report_reader &
flock -x /srv/data.lock  data_updater

# Lock a directory to serialize per-project jobs
flock -n /srv/project/.job.lock ./deploy.sh

# fd form: lock, do work, release exactly at fd close
exec 9>/run/lock/migrate.lock
flock 9
psql -f migration.sql mydb
exec 9>&-   # lock released here

# Parallel xargs workers, each with its own per-slot lock
printf '%s\n' a b c d | xargs -P2 -I{} sh -c "flock /tmp/slot.lock -c 'process {}'"

# Prevent double-start of a systemd-style service wrapper
ExecStart=/usr/bin/flock -n /run/lock/myjob.lock /usr/bin/myjob

# lock a whole-system resource: the device
flock -n /dev/sdb dd if=/dev/sdb of=/backup/sdb.img bs=4M

# Timeout ladder: try nonblocking, then short wait, then give up loudly
flock -n /run/lock/sync.lock sync.sh \
  || flock -w 60 /run/lock/sync.lock sync.sh \
  || { logger -t sync "giving up, another sync running"; exit 42; }

# Serialize apt/dpkg-style work across multiple machines via one shared NFS lock
flock --fcntl /net/lock/deploy.lock ./deploy.sh

# One-shot status probe without side effects (exit code only)
flock -n /run/lock/nightly-backup.lock true && echo idle || echo busy

# Stagger worker starts with per-index locks
for i in 0 1 2 3; do flock /run/lock/worker$i.lock worker.sh $i & done

# Bound the WAIT with timeout(1): 124 = gave up waiting, 0/other = command ran
timeout 30 flock /run/lock/deploy.lock ./deploy.sh

# Contended-run telemetry: measure how long the lock was actually waited on
START=$(date +%s); flock -w 120 /run/lock/etl.lock ./etl.sh \
  || echo "etl wait exceeded: $(( $(date +%s) - START ))s" | logger -t etl

# Quiet cron skip: contended runs are normal, not failures — exit 0
flock -n /run/lock/poller.lock ./poll.sh || true
```

## Nuances and Gotchas

- **Advisory only.** `flock` will not stop a process that does not ask for the lock. Every writer of the resource must cooperate; otherwise the lock is theater.
- **Inherited descriptors keep locks alive.** Children inherit the open file description; a long-lived daemon spawned by the locked command holds the lock after `flock` returns. `-o, --close` closes the lock fd before exec so the command's children cannot retain the lock by accident.
- **`flock file cmd` creates `file` if missing.** The lockfile is a zero-byte artifact; do not point it at a data file you care about, and keep lock files in `/run/lock` or `/tmp`, not in synced directories.
- **Same process, same fd = no contention.** Re-running `flock 9` on an fd you already locked is a no-op/conversion, because both refer to one open file description. Contention requires separate `open()`s — which is what separate `flock FILE ...` invocations do.
- **Conflict exit code collision.** With the default `-E 1`, "lock not acquired" is indistinguishable from "command exited 1". Use a dedicated code (`-E 42`) in scripts that branch on the result.
- **`-w` without `-n` is the timeout form** — `-n` and `-w` are mutually exclusive ways to bound waiting. `flock -w 0` is effectively non-blocking.
- **NFS and network filesystems.** Classic `flock(2)` over NFS is emulated or unsupported depending on server/version; for cross-host or cross-protocol locking, `--fcntl` (OFD locks) or explicit coordination (e.g., a lock in a shared DB) is safer.
- **Not POSIX.** `flock(2)` is BSD/Linux; portable code needing byte ranges should use `fcntl`/`lockf`. Busybox ships a compatible-but-smaller `flock`; macOS has `flock(2)` but historically no `flock(1)` command in the base system.
- **Directory locks are legitimate.** Locking a directory works and survives file recreation — handy when a lockfile itself might be deleted by cleanup jobs, which would silently reset protection.
- **Deleting the lock file does not release anything** — and is harmful: a second process that opens a fresh inode of the same name locks a *different* object and both proceed. Never `rm` a live lock file; fix whatever holds the lock.
- **`flock -w 0` is legal and equals non-blocking**; `-n` is just the idiomatic spelling. Negative or non-numeric timeouts are usage errors.
- **Symlinked lock paths are resolved once at open.** If `/run/lock/x.lock` is a symlink to a rotating path, two invocations around the rotation may lock different inodes. Keep lock paths plain files.
- **Busybox flock is narrower.** It supports the core forms (`-s/-x/-n/-w/-c`) but not all options (`-E`, `--fcntl`, fd-number form details differ); portable scripts should stick to the common subset or require util-linux.
- **Blocking waits are interruptible.** SIGTERM/SIGINT break a pending acquisition (the kernel wait is interruptible); a supervised script that gets SIGHUP/SIGTERM on redeploy dies mid-wait rather than finishing the previous run. Bound waits explicitly with `-w` (or `timeout`) when a redeploy must not kill in-flight jobs.
- **Multiple lockfiles need a global acquisition order.** A job that takes lock A then B can deadlock against a job taking B then A; flock will not detect or resolve it. Convention: acquire in a fixed order (e.g. sorted paths) in every script that touches more than one lockfile.
- **Shared→exclusive upgrade is not atomic.** The kernel drops the existing lock before queueing for the new one (documented flock(2) conversion semantics); two processes upgrading at once can deadlock. Take `-x` from the start, or model the write phase as a separate lockfile.
- **There is no mandatory mode to fall back on.** Linux removed mandatory file locking entirely (kernel 5.15); the old setgid-directory trick to enable it is dead. Advisory-only is the model — enforce cooperation with ownership and permissions, not hopes.

## Exit Status

- `0` — the lock was acquired and the command ran (flock's exit status is the *command's* exit status).
- `-E` value (default `1`) — the lock could not be acquired: `-n` found it held, or `-w` timed out. The command never ran.
- Nonzero — the command failed with its own exit status, or flock itself hit an error (bad arguments, unopenable lock file).

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`ionice`](./ionice.md) — same "wrap a command and degrade politely" pattern for I/O priority.
- [`lslocks`](./lslocks.md) — inspect which processes currently hold flock/fcntl locks.
- [`findmnt`](./findmnt.md) — `fsck -l` and device serialization meet flock's syscall underneath.
- [`getopt`](./getopt.md) — sibling "shell programming helper" binary.
- [`bash`](../../shell/bash.md) — fd redirection (`exec 9>lock`) that powers the fd form.
- [`xargs`](../../shell/xargs.md) — parallel workers that need per-resource serialization.
- [`process-management`](../../admin/process-management.md) — where locking sits relative to signals and job control.
- [`internals`](../../internals.md) — open file descriptions and the VFS lock lists behind flock(2).

## Interview Questions

### Q: Why use flock instead of the classic `mkdir /var/lock/job` or pidfile idiom?

Both classics leak state: if the writer crashes, the mkdir lock or stale pidfile remains and blocks all future runs until manually cleaned. flock is a kernel-held advisory lock tied to process lifetime — death by signal, OOM kill, or crash releases it automatically. A pidfile also records *which* pid ran, which flock does not; combine them when you need both liveness and identity.

### Q: Your cron wrapper exits 1 and you cannot tell whether the backup ran. What do you change?

Use `flock -E 42` so "lock already held" exits with 42 while "backup itself failed" propagates the backup's own status. Then the cron mail/monitoring can distinguish superseded runs (42, log only) from real failures (any other nonzero). Without `-E`, both cases exit 1 by default.

### Q: A command under `flock file cmd` finishes, but the next invocation still reports the lock busy. How is that possible?

The command forked a long-lived child that inherited the lock file descriptor; the open file description — and therefore the lock — stays alive as long as *any* descriptor is open. Fix with `flock -o` (close the fd before exec) or make the daemon close inherited fds when daemonizing. This is the most common "flock leaks" bug in the wild.

### Q: Explain the difference between `flock` (the command, via flock(2)) and `fcntl` record locks.

flock(2) locks the whole file and is owned by the open file description: inherited by children, released when all related fds close, and independent of byte ranges. fcntl(F_SETLK) locks byte ranges and is owned by the *process*: closing any descriptor for that file silently drops all its record locks, and locks are not inherited across fork. The two spaces do not interoperate — a flock holder and an fcntl holder can both "hold" the file simultaneously — which is why `flock --fcntl` (OFD locks) exists as a bridge for NFS and fcntl-speaking tools.

### Q: How do you implement reader/writer semantics from the shell?

Shared vs exclusive modes: readers take `flock -s`, the writer `flock -x`. Any number of shared holders coexist; the exclusive holder waits until all shared holders release. Since flock is whole-file only, "row-level" granularity is out of scope — use one lockfile per resource to partition, or a database for fine-grained locking.

### Q: What happens if you kill -9 the flock process — and its command?

`kill -9` cannot be caught, yet the lock still disappears: the kernel releases locks when the owning open file description is destroyed at process exit. This crash-safety is the core design argument for flock over on-disk lockfiles. The child command (forked before the kill if you targeted flock) may keep the lock via the inherited fd — again the reason `-o` exists.

### Q: How would you allow at most N parallel instances of a job using flock?

Create N lock files (`/run/lock/job.0` … `job.N-1`) and have each invocation try them non-blockingly in turn, running with the first free one:

```bash
for i in $(seq 0 3); do
    if flock -n /run/lock/job.$i true; then
        exec flock /run/lock/job.$i ./worker.sh
    fi
done
echo "all 4 slots busy" >&2; exit 42
```

(The probe and the real acquisition must use the same file; for airtightness open the fd once and flock it, rather than probing and re-acquiring.) This gives a counting semaphore built from exclusive locks — no daemons, no state files.

### Q: A cron job hangs forever at its flock line. How do you debug it, and what are the usual culprits?

Check `/proc/locks` (or `lslocks`) for FLOCK entries; match the device:inode to the lockfile and read the owning PID. Usual culprits: a child spawned by the locked command inherited the fd and outlived the wrapper (fix: `-o`, or have the daemon close inherited fds); a second job holding far longer than designed; or an NFS-mounted lock path where flock semantics degrade. Then decide: kill the holder, raise the timeout, or add an alert on lock wait time.

### Q: Why is an in-place shared-to-exclusive upgrade dangerous, and what are the alternatives?

flock(2) conversion removes the existing lock before queueing for the new one, so two processes that both hold shared locks and both ask for exclusive can deadlock — each waits for a shared holder that no longer exists. Alternatives: hold the exclusive lock for the whole critical section even when you expect to only read (simplest); use two lockfiles with a fixed acquisition order; or take `-w` so a stuck upgrade surfaces as a bounded error instead of a hung job.

### Q: Where does flock end and distributed locking begin? Sketch the layered design.

flock is host-local, kernel-volatile, crash-safe: ideal for serializing workers on one machine, meaningless across hosts or reboots. Distributed locks (etcd/Consul leases, database advisory locks) add consensus and expiry — slower, but cross-host. The layered pattern: a coordination-service lease elects the host that runs the job; flock serializes concurrent invocations on that host. The known anti-pattern is flock on an NFS mount standing in for a distributed lock — semantics vary by NFS version and client, and recovery after a network partition is exactly the problem the real coordinator exists to solve.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/flock.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
