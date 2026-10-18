# Temp File and Atomicity Assumptions: What "Write to /tmp and Rename" Silently Promises

## Overview

The write-temporary-file-then-atomic-rename pattern is the standard answer to "how do I update a file safely," and it deserves its reputation — on a POSIX filesystem, `rename()` within one filesystem really is atomic, and readers see either the old file or the new one. But the pattern as taught compresses four separate assumptions into one idiom: that the rename covers everything (it does not cover durability without `fsync`), that `/tmp` is private scratch space (it is world-writable and policed by cleanup daemons), that the temp file is removed when the work is done (crashes disagree), and that a full disk announces itself on every write (the page cache disagrees, and that disagreement is the worst of the four).

This chapter audits the temp-file family with the collection's five-step pattern. The durability sequence cited below — write, `fsync` the file, rename, `fsync` the directory — comes from the SQLite atomic-commit documentation, which is the most carefully reasoned public account of what the filesystem actually promises, and from the sibling chapter on filesystem durability, which treats the `fsync` story at full depth. The Python `tempfile` module documentation supplies the safe-name API contract (`mkstemp` and friends), and the `open(2)` manual page documents `O_TMPFILE`, the kernel's answer to the invisible-temp-file problem. The ENOSPC analysis is worked from buffered-I/O semantics that every Unix accepts and few programs check.

## Assumption 1: "Write-Then-Rename Is Atomic Everywhere"

### The taught rule

Write the new content to a temporary file in the same directory, then `rename()` it over the target — readers see the old or the new file, never a partial one.

### The hidden assumptions

- The atomicity holds only within a single filesystem: `rename()` across filesystems returns `EXDEV` (invalid cross-device link) rather than moving the file, and a fallback that silently copies-then-deletes has just reintroduced the non-atomic window the pattern exists to avoid.
- Atomicity is not durability. After `rename()` returns, the new name is in memory only; on ext4's delayed allocation, a power loss can leave a zero-length file at the target name — the zero-length-file-after-crash episode that the ext4 community worked through in the late 2000s. The complete sequence is write, `fsync` the file, rename, then `fsync` the containing directory.
- The reader's side has its own gap: a reader that opened the file before the rename keeps reading the old inode after it, which is usually desirable, but a reader that re-opens mid-sequence and reads *both* files across the boundary can stitch together inconsistent views — atomicity is per-open, not per-logical-read-across-opens.
- Windows and network filesystems do not carry the same contract: `MoveFileEx` with `MOVEFILE_REPLACE_EXISTING` is close but not identical, and NFS rename semantics are weaker than local disk in exactly the crash-and-cache windows the pattern cares about.

### Counterexample

A config-management tool updates `/etc/app/rules.json` with write-then-rename. It runs correctly for a year. Then a kernel update changes the mount layout, and the temp directory `/etc/app/.tmp` is a separate mount (an admin mounted a scratch volume there); `rename()` now returns `EXDEV`. The tool's fallback copies to the destination directly — so during every subsequent update, readers see a truncated file for the copy duration, and one day a consumer parses the partial JSON and crashes mid-morning. The audit that prevents this: assert same-filesystem temp placement at startup (stat the st_dev of temp and target), perform the full `fsync` sequence including the directory, and test the power-loss path the SQLite documentation's atomic-commit chapter describes rather than the happy path. The sibling filesystem-durability chapter works the zero-length-file arithmetic in full.

### What changes when the assumption is removed

Corrected statement: *rename is atomic within one filesystem and atomicity is separate from durability; the pattern is complete only as write, fsync-file, rename, fsync-directory, with the temp file created on the target's filesystem and the cross-device case rejected loudly.* Operationally: derive the temp file's directory from the target's directory (never from a global `/tmp`), check `st_dev` equality as a startup invariant, and treat `EXDEV` as a configuration error, not a fallback trigger.

### Consequences

The interview probe "you rename over the config file and the power dies — what does the file contain?" is exactly this assumption, and the answer (a zero-length file, on filesystems with delayed allocation, without the directory fsync) reliably surprises. The durability half lands harder in production than the atomicity half, because atomicity bugs need a reader to catch while durability bugs need only a power cut.

## Assumption 2: "/tmp Is Mine"

### The taught rule

Temp files go in `/tmp` — it exists for scratch data, is writable by everyone, and needs no further thought.

### The hidden assumptions

- World-writable means other local users can write it too, and a predictable temp name (`/tmp/app.pid` or `/tmp/data.tmp`) is a symlink-attack target with decades of documented history: the attacker pre-creates the path as a symlink to a file the program will open for writing, and the program writes through the link.
- The directory is policed: systemd-tmpfiles and its cousins age out old files, so a "temporary" file that a long-running process still needs can be deleted mid-life — and if the process re-opens by path, it now reads a stranger's file or fails.
- In containers, `/tmp` is frequently a shared volume or an empty-dir with a size limit; two pods sharing a volume race on names, and a size limit turns a large temp write into an ENOSPC failure that looks like a disk problem but is a quota.
- The name-collision story is real even alone: `mktemp`-style unpredictable names are not paranoia, they are the API — `mkstemp` and `O_TMPFILE` exist because "a name nobody else guesses" is a security property, not a convenience.

### Counterexample

Two pods in a shared-volume arrangement both write `/tmp/report.csv.tmp` before renaming to `/tmp/report.csv`. Pod A creates the file, pod B creates the same path (truncating A's open file descriptor — both hold different fds to the same inode now), A writes its data, B writes its data, B renames, and the published report contains interleaved garbage from both writes. Nothing failed; every syscall returned success. The fix stack: per-process unique names from `mkstemp` (or `O_TMPFILE`, which never has a directory-visible name to collide with), a per-writer subdirectory (`/tmp/app-A/`), and for multi-tenant hosts the sticky bit plus `noexec`/`nosuid` mount options that the containers chapter situates in the isolation picture. The security half of the fix is non-negotiable on shared hosts: predictable names plus world-writable directories is the classic local-privilege pattern the symlink race exploits.

### What changes when the assumption is removed

Corrected statement: *`/tmp` is shared, policed, and size-limited; a temp file needs an unguessable name (or no name at all via `O_TMPFILE`), a scope the process controls, and the assumption that age-out may remove it at any time.* Operationally: use the standard library's temp-file APIs (the Python `tempfile` documentation's `mkstemp`/`NamedTemporaryFile` contract is the reference shape), place rename-pairs on the target filesystem rather than in `/tmp`, and never persist anything in `/tmp` past the process's need for it.

### Consequences

The interview probe "why does the linter flag `/tmp/fixed-name.tmp`?" has a two-layer answer — collision and symlink race — and a memorable coda: the modern kernel answer `O_TMPFILE` removes the name from the equation entirely, at the cost of needing `linkat()` if you ever want to publish the result. The isolation angle (shared volumes, size limits) belongs to the containers chapter's resource picture.

## Assumption 3: "The Temp File Gets Cleaned Up"

### The taught rule

The code deletes the temp file when it finishes — with try/finally around it — so no garbage accumulates.

### The hidden assumptions

- `finally` runs on normal exits and handled exceptions; it does not run on `SIGKILL`, power loss, or a kernel OOM kill of a sibling in a cgroup that takes the whole process down. Every crash leaves files, and nobody is there to run the cleanup.
- Accumulation is slow and invisible: a nightly job leaking one 50 MB temp file per run fills a modest volume in weeks, and because the files are in `/tmp`, the monitoring that watches the data volume stays green while the root filesystem fills.
- The cleanup daemons that age out `/tmp` are themselves assumption-laden: deleting a file a running process still has open does not free space on Linux (the inode lives until the descriptor closes), and deleting a file the process *will* re-open by path breaks it — both directions of age-out mismatch have bitten production systems.
- Startup-time sweeps ("delete files older than my lock, on boot") inherit the same race the lockfile analysis in the scheduling chapter has: two instances sweeping concurrently can delete each other's live temp files.

### Counterexample

An image-processing service writes a 30 MB intermediate per request to `/tmp/proc-N/` and removes it in a `finally` block. During a dependency brownout, requests time out and are killed by the gateway's deadline; the process receives SIGKILL on a worker recycle; `finally` never runs. Over two weeks, 14,000 dead temp files (420 GB) fill the volume, the service starts failing on write, and the cleanup that finally runs must distinguish live files (held by in-flight requests) from dead ones — with no marker distinguishing them. The durable design: a sweep on startup that deletes only files older than the process's own boot, a marker file or naming scheme that identifies each generation's files, disk-usage alerting on the temp volume itself, and — the structural fix — an explicit temp-volume quota so leak growth degrades the service's own writes rather than the machine.

### What changes when the assumption is removed

Corrected statement: *cleanup code is best-effort for the process's lifetime; anything the process leaves behind must be discoverable (naming/marker scheme), reclaimable (startup sweep, age-out daemon), and bounded (quota) — because crashes guarantee leaks.* The leak-vs-age-out tension is the design crux: name files so the sweeper can tell dead from live, and prefer reclaiming too early (with retries) over filling the disk.

### Consequences

The interview probe "your disk filled but your data volume is fine — where do you look?" lands on temp leaks, log spinners, and orphaned sockets; the temp-file answer is this assumption plus a naming scheme. The GC-means-no-leaks misconception is the same shape one level up: a runtime reclaiming memory says nothing about reclaiming filesystem artifacts.

## Assumption 4: "Disk-Full Fails Loudly on Every Write"

### The taught rule

If the disk is full, the write fails with an error, the code handles it, and the user sees a clear message.

### The hidden assumptions

- Buffered writes do not touch the disk. A `write()` succeeds by copying into the page cache; the space is allocated later, so the ENOSPC error arrives at `fsync()` (or much later), if the code checks there at all — a program without `fsync` may see every write succeed and lose data silently at crash time.
- Partial writes are a state, not just an error: a multi-block write that hits ENOSPC mid-way leaves a truncated, structurally invalid file, and append-heavy workloads (logs) keep "succeeding" one page-cache page at a time while the volume is effectively full.
- Metadata needs space too: directory entries, inode tables, and journal space can exhaust independently, so a filesystem can refuse to create a new file while still accepting appends, which confuses code that tested "can I write?" by creating a probe file.
- Quotas and container limits convert ENOSPC into a per-user or per-cgroup condition with the same syscall result and a completely different remediation path.

### Counterexample

An export service streams a large CSV to a temp file, renames it into place, and returns a download URL. The volume crosses 100% mid-export. Every `write()` in the loop returns success (page cache); `close()` returns success; `fsync` is never called; the rename succeeds. The user downloads a 400 MB file whose tail is missing, and — worse — the crash-consistent directory entry means the file counts as complete in every listing. The failure is silent in both directions: no error surfaced at write time, and the artifact is corrupt without any error marker. The fix is the same fsync discipline from Assumption 1 plus explicit ENOSPC handling at `fsync`, pre-flight space checks treated as advisory (they race), and — for streamed artifacts — a footer or length so truncation is *detectable* by the consumer. The corruption-would-be-loud misconception chapter documents the general pattern: storage failures are quiet by default.

### What changes when the assumption is removed

Corrected statement: *ENOSPC is delivered asynchronously and partially; loud failure requires the program to check `fsync` results, design artifacts to be self-verifying, and monitor the volume — the filesystem will not do it.* Operational form: check every `fsync` and `close` return code (the SQLite documentation's error-handling posture is the reference), cap artifact size against free space, alert on the temp volume's usage trend (from Assumption 3), and make consumers validate length or checksum rather than trusting presence.

### Consequences

The interview probe "write() returned 0 bytes free — did it fail?" is the sharpest version of this assumption; the strong answer distinguishes the syscall's local success from the durable, allocated result. This chapter's fsync discipline and the filesystem-durability sibling's power-loss analysis are two halves of one contract, and the containers chapter supplies the quota dimension.

## Interview Questions

1. **You rename a new file over the old one and the power fails. What is on disk?** Potentially a zero-length target on delayed-allocation filesystems unless the sequence was write, fsync-file, rename, fsync-directory — atomicity and durability are separate guarantees with separate syscalls.
2. **Why is a predictable name in /tmp dangerous even in a single-user container?** Collision with other writers in shared volumes, and the symlink race on shared hosts; the fixes are `mkstemp`/`O_TMPFILE` (unguessable or nameless), per-writer directories, and sticky/noexec mount options.
3. **Your cleanup code never runs after a crash. How do you keep the volume from filling?** Discoverable naming or markers, a startup sweep scoped to pre-boot files, an age-out daemon tuned to the workload, usage alerting on the temp volume, and a quota so leaks degrade only their owner.
4. **Where does the ENOSPC error actually appear if you never fsync?** It may not appear at all before a crash silently truncates; buffered writes succeed into page cache, so loud failure requires checking fsync/close and building self-verifying artifacts.
5. **When does rename() fail, and what should the program do?** Cross-device rename returns EXDEV; the correct response is a configuration error (create the temp on the target's filesystem), never a silent copy fallback that reintroduces the non-atomic window.

## Key Takeaways

- Write-then-rename is atomic only within one filesystem and is not durable by itself: the complete pattern is write, fsync file, rename, fsync directory.
- `/tmp` is shared, policed, and limited: use unguessable or nameless temp files (`mkstemp`, `O_TMPFILE`), per-writer scopes, and never park rename-pairs on a different filesystem than the target.
- Cleanup code dies with the process; leaks are guaranteed by crashes, so discovery (naming), reclamation (sweeps and age-out), and bounding (quotas) must be designed, not assumed.
- ENOSPC is asynchronous and partial: `write()` can succeed into page cache on a full disk, so loud failure requires fsync checks, self-verifying artifacts, and volume monitoring.
- The unifying detection artifact is per-volume disk monitoring plus startup invariants (st_dev equality, temp-dir existence) that convert silent misbehavior into loud misconfiguration.

## Cross-References

- [Filesystem durability](filesystem-durability.md) — the sibling audit of fsync, rename, and power-loss semantics in full depth.
- [Containers and resources](containers-and-resources.md) — shared volumes, size limits, and quota-driven ENOSPC.
- [Corruption would be loud (misconception)](../misconceptions/corruption-would-be-loud.md) — storage failures are silent by default, the general pattern behind ENOSPC.
- [GC means no leaks (misconception)](../misconceptions/gc-means-no-leaks.md) — runtime reclamation versus filesystem artifacts the runtime never sees.
- [Build caches and reproducibility](../connection-atlas/build-caches-reproducibility.md) — cache stores built on the same temp-file and atomic-rename mechanics.
- [SQLite atomic commit documentation](https://www.sqlite.org/atomiccommit.html) — the reference account of what the filesystem promises across commit and crash.
- [Python tempfile module](https://docs.python.org/3/library/tempfile.html) — the safe-name API contract (`mkstemp`, `NamedTemporaryFile`) in reference form.
- [open(2) manual page](https://man7.org/linux/man-pages/man2/open.2.html) — `O_TMPFILE` semantics and the nameless-temp-file design.
