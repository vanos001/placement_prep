# Crash Consistency: fsync, Journal Modes, and the Durability Ladder

Every "persistent" write survives only if a chain of caches and journals agrees
at the instant power dies. This page follows one durable append from `write()`
down to the platter, enumerates the crash windows ext4's journal modes leave
open, dissects the atomic-replace protocol, and closes with power-loss tooling
and the 2018 PostgreSQL fsync-gate incident.

Prerequisites: [the WAL pattern](../wal.md), [ext4 internals](../../linux/kernel/filesystems/ext4.md),
[filesystem journaling](../../linux/kernel/filesystems/journaling.md),
[the page cache](../../linux/kernel/memory/page-cache.md).

## The five questions `fsync` actually answers

`int fsync(int fd)` looks like one syscall; it is five separate promises
bundled together, and reading the [open(2) man page](https://man7.org/linux/man-pages/man2/open.2.html)
carefully shows where the edges are:

1. **Per-file, not per-directory.** fsync flushes that file's *data* and
   *inode* — nothing about the directory entry that makes it reachable.
   A freshly created, fsynced file can still vanish after a crash because the
   dirent was only in the page cache. Hence the directory fsync below.
2. **Per-file, not per-device.** Other files' dirty pages are untouched, and
   "the device quiesced" is not implied. In `data=journal` mode unrelated
   blocks sharing a transaction may get dragged along.
3. **`fdatasync` skips metadata when it can.** It forces data plus only the
   metadata needed to retrieve it (size, block map). Appending still persists
   the size update; in-place overwrite usually skips metadata entirely — which
   is why WAL writers (PostgreSQL, InnoDB, etcd) call `fdatasync`.
4. **`O_DSYNC`/`O_SYNC` fold the flush into each `write`** — same durability,
   fewer syscalls, useful for O_DIRECT device files, wasteful for buffered
   streams.
5. **fsync does not name the medium.** Success means flush/FUA commands were
   issued and the device ACKed. What that ACK is worth depends on the device's
   power-loss protection — a cache-less-capacitor SSD can ACK and still lose
   data (see *Device caches, barriers, FUA*).

```text
the durability ladder: what each rung guarantees

 rung          syscall/API          protects against
 ------------  -------------------  -------------------------------------
 page cache    write()              nothing (app crash only)
 dirty pages   msync(MS_SYNC)       process death, not power loss
 file data     fdatasync(fd)        power loss, for bytes + size
 file+meta     fsync(fd)            power loss, for bytes + all inode meta
 dirent        fsync(dirfd)         the file becoming unreachable
 whole device  syncfs(fd)           power loss, everything (slow, blunt)
 kernel VM     sync(2)              nothing about device cache ACKs
 device cache  BLKFLSBUF / SG_IO    device-vendor-specific; PFL GPUs lie
```

The gap between "fsync returned" and "bytes are on platter" is rung eight —
and it is where power-loss testing (below) earns its keep.

## ext4's three journal modes and their crash windows

ext4 ([mount-option reference](https://www.kernel.org/doc/html/latest/filesystems/ext4/journal.html))
runs one journal (JBD2) with three policies for *file data*:

| Mode               | What the journal writes        | Data blocks reach disk...         | Crash-window artifact                                  |
|--------------------|--------------------------------|-----------------------------------|--------------------------------------------------------|
| `data=journal`     | metadata **and** data          | via the journal, before commit    | After replay: old size + old data, or new + new. Slow (double write). |
| `data=ordered` (default) | metadata only            | **before** the commit record      | Replay shows old size + orphan new blocks, or new + new. No stale-data exposure. |
| `data=writeback`   | metadata only                  | any time, order not enforced      | Replay can show **new size + stale garbage** in the tail of the file. |

`data=ordered` enforces one invariant: data blocks are on stable storage before
the journal commits the metadata that points at them. `data=writeback` drops
it for throughput — the classic trade studied in
[Pillai et al., OSDI 2014](https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai),
whose Alice tool showed that even correct `fsync` protocols behave differently
across modes and filesystems, so applications must re-test on every target.

```text
crash windows for a one-block append (S = stale, N = new, - = old)

 device time -->>
 ordered:    [data N][j-commit][checkpoint]      window 1     window 2
                ^         ^                       ^            ^
 crash here:    |         |   => OLD size, orphan N   NEW size + NEW data

 writeback:  [j-commit][data N?][checkpoint]      window 1
                ^         ^                       ^
 crash here:    |         |   => OLD size ... or NEW size + STALE data  <-- the
                                                        only window where a
                                                        file "grows" garbage
```

Two ext4-specific wrinkles matter in interviews:

- **Delayed allocation** means blocks may not even be allocated until
  writeback. A crash before allocation+commit leaves a file the app *closed*
  minutes ago at **zero length** — no fsync, no data. Heuristic
  `auto_da_alloc` detects the write-close-rename pattern and forces allocation
  early, papering over the most common offender.
- **`data=ordered` still allows torn appends *within* one write()**: fsync
  orders data before metadata, but a 2 MiB write can persist half its pages if
  the machine dies mid-writeback. Only the fsync boundary is atomic, never the
  write itself.

## The atomic-replace protocol

The only portable way to publish a new version of a file on POSIX:

```c
int fd = open("config.tmp", O_WRONLY|O_CREAT|O_TRUNC, 0644);
write(fd, buf, len);            /* 1: data into page cache          */
fsync(fd);                      /* 2: data + inode of tmp durable   */
close(fd);
rename("config.tmp", "config"); /* 3: dirent swap, atomic in cache  */
int dfd = open(dirname, O_RDONLY | O_DIRECTORY);
fsync(dfd);                     /* 4: dirent swap durable           */
close(dfd);
```

The four steps are not decorations — the simulation below walks every crash
point. `rename()` is atomic *within the kernel's view*, but the rename itself
is a dirty dirent until the parent directory is fsynced. `O_DIRECTORY` in
step 4 is a guard, not a durability flag: it fails the open if `dirname` is
not a directory, catching path bugs that would otherwise fsync a regular file
and silently persist nothing useful. `O_TMPFILE` (create an unnamed inode,
write, fsync, then `linkat` into place) achieves the same with no window
where a half-written temp name is visible.

A state machine over the whole protocol (executable below):

| Crash after              | State on reboot                                                     |
|--------------------------|---------------------------------------------------------------------|
| `write(tmp)`             | No `final`. tmp may even be **zero-length** thanks to auto_da_alloc heuristics |
| `fsync(tmp)`             | No `final`; tmp has full content                                    |
| `rename` (before dir fsync) | **Undefined**: old or new content, or no `final` at all          |
| `fsync(dir)`             | `final` guaranteed to hold the new content                          |

Windows offers no dirent-fsync equivalent — `FlushFileBuffers` covers data,
not metadata renames — which is why config-management tools treat
cross-platform durable replace as its own problem.

## Device caches, barriers, and FUA

Between the filesystem and the platter sit two write caches:

- **Volatile device write cache** (HDDs, cheap SSDs): ACKs writes at DRAM
  speed. A flush command (`FLUSH CACHE`/NVMe flush, or FUA-flagged writes)
  forces it to media.
- **Volatile host/controller caches** (RAID cards): the drive's flush means
  nothing if the RAID card caches too — a barrier must traverse the whole
  stack, which is why `bs=...` benchmarks on RAID without battery-backed
  cache historically lied about fsync latency.

Historically Linux used **write barriers** — tagged requests meaning
"everything before this must be durable before anything after". Legacy
hardware barriers had subtle multi-device problems and were retired in kernel
4.10 in favor of explicit **preflush/FUA** bio flags (see the
[writeback cache control docs](https://docs.kernel.org/block/writeback_cache_control.html),
plus [block devices](../../linux/kernel/block/devices.md) and
[bio](../../linux/kernel/block/bio.md)): `blk-mq` issues `REQ_PREFLUSH |
REQ_FUA` sequences, and ext4 composes flush-FUA pairs around each journal
commit record. So an `fsync` compiles to: write dirty pages → flush (or FUA)
at the commit → proceed. On NVMe the flush is a real command ([NVMe](../nvme.md));
the [T10 protection model](./t10-pi-data-integrity.md) then guards those
blocks in flight. Devices with **power-loss protection** (pl capacitors) honor
flushes even on sudden power cut; without it, "fsync returned" only means *the
device promised* — and fsync-gate (below) showed even the promise can fail.

## Power-loss testing: dm-flakey, ALICE, CrashMonkey, and fsync-gate

You cannot unit-test a power cut in CI; you emulate it at the device layer:

| Tool                     | Layer        | What it does                                                        |
|--------------------------|--------------|---------------------------------------------------------------------|
| `dm-flakey`              | device-mapper| Drops the device offline for N seconds of every M — simulates clean-ish loss |
| `dm-log-writes` + `replay_log` | device-mapper | Records every bio, then replays the log up to any point: a *crash fuzzer* |
| ALICE                    | syscall-level| Systematically explores fsync orderings per OSDI'14                  |
| CrashMonkey / Hydrate    | kernel eBPF  | Captures write sets per syscall and replays them onto ext4/btrfs/xfs images |

A minimal dm-log-writes session (as root, on a scratch loop device):

```bash
dmsetup create logdev --table "0 $(blockdev --getsz /dev/loop0) log-writes /dev/loop0 /dev/loop1"
mkfs.ext4 -F /dev/mapper/logdev           # test fs on the logging target
mount /dev/mapper/logdev /mnt && ./run_workload.sh
dmsetup message logdev 0 mark "after-fsync"   # tag the log
# replay up to the mark into a second device, then fsck + inspect:
dmsetup create replay --table "0 $(blockdev --getsz /dev/loop1) flakey /dev/loop1 0 0 0"
dmsetup message replay 0 drop_writes; e2fsck -f /dev/mapper/replay
```

The deepest lesson of 2018 was that even the *flush* path can fail. PostgreSQL
had treated `EIO` from fsync as retryable-safe; the [kernel discussion](https://lwn.net/Articles/752063/)
and [PostgreSQL wiki postmortem](https://wiki.postgresql.org/wiki/Fsync_Errors)
(coverage at [danluu.com/fsyncgate](https://danluu.com/fsyncgate)) established
that after an fsync error the kernel may have *dropped* the dirty pages —
retrying is useless; the only safe response is to panic or re-write from a
trusted source. PostgreSQL now panics on fsync failure, and the event is why
kernels grew `syncfs` error reporting (5.8+): late errors must not be
silently discarded.

The failure-mode taxonomy used by crash testers — lost write, torn write,
stale block read, mis-ordered commit — maps cleanly onto the recovery-side
checks in [log-based recovery](../../dbms/transactions/log-recovery.md) and the
doublewrite/blurry-boundary defenses in [InnoDB internals](./innodb-internals.md).

## A crash-window state machine (runnable)

The simulator enumerates every device-op boundary for both journal modes, plus
the rename protocol, and reports what reboot+replay yields. It is pure
enumeration — no randomness, same output every run:

```python
"""Crash-window state machine.

Part A: ext4 data=ordered vs data=writeback for a one-block append.
Part B: write -> fsync -> rename -> fsync(dir), every crash point.

Device ops are enumerated in the order each journal mode may issue them;
a "crash after op k" replay shows what an app sees after reboot + journal
replay. No RNG: every crash point is enumerated, output is deterministic.
"""
OLD = {"data": "old", "inode": "old", "jcommit": False}
OPS = {
    "ordered": [
        ("write data block", {"data": "new"}),
        ("journal commit (inode update)", {"jcommit": True, "inode": "new"}),
        ("journal checkpoint", {"jcommit": False, "inode": "new"}),
    ],
    "writeback": [
        ("journal commit (inode update)", {"jcommit": True, "inode": "new"}),
        ("write data block (whenever)", {"data": "new"}),
        ("journal checkpoint", {"jcommit": False, "inode": "new"}),
    ],
}

def replay(state):
    """App view after fsck replays the journal from `state`."""
    inode = state["inode"] if (state["jcommit"] or state["inode"] == "new") \
        else "old"                     # committed txn is replayed on mount
    if inode == "old":
        return "OLD file (size unchanged); new data blocks are orphans"
    return ("NEW file + NEW data" if state["data"] == "new"
            else "NEW file + STALE/GARBAGE data in its last block")

print("Part A: ext4 append, crash after each device op")
for mode, ops in OPS.items():
    st = dict(OLD)
    print(f"-- data={mode}")
    print(f"  crash before any op                          -> {replay(OLD)}")
    for label, patch in ops:
        st.update(patch)
        print(f"  crash after {label:<33} -> {replay(st)}")

print()
print("Part B: atomic-replace protocol, crash after each step")
steps = [("write(tmp)", "tmp pages dirty in page cache"),
         ("fsync(tmp)", "tmp data+inode on storage"),
         ("rename(tmp, final)", "dirent swap in page cache"),
         ("fsync(dir)", "dirent swap durable")]
outcome = ["final absent; tmp may survive as ZERO-LENGTH (auto_da_alloc)",
           "final absent; tmp holds full content",
           "undefined: final shows old OR new content OR is absent",
           "final guaranteed NEW content"]
for i, ((op, dur), out) in enumerate(zip(steps, outcome), 1):
    print(f"  crash after step {i} ({op:<20} = {dur})")
    print(f"      -> {out}")
```

```text
Part A: ext4 append, crash after each device op
-- data=ordered
  crash before any op                          -> OLD file (size unchanged); new data blocks are orphans
  crash after write data block                  -> OLD file (size unchanged); new data blocks are orphans
  crash after journal commit (inode update)     -> NEW file + NEW data
  crash after journal checkpoint                -> NEW file + NEW data
-- data=writeback
  crash before any op                          -> OLD file (size unchanged); new data blocks are orphans
  crash after journal commit (inode update)     -> NEW file + STALE/GARBAGE data in its last block
  crash after write data block (whenever)       -> NEW file + NEW data
  crash after journal checkpoint                -> NEW file + NEW data

Part B: atomic-replace protocol, crash after each step
  crash after step 1 (write(tmp)           = tmp pages dirty in page cache)
      -> final absent; tmp may survive as ZERO-LENGTH (auto_da_alloc)
  crash after step 2 (fsync(tmp)           = tmp data+inode on storage)
      -> final absent; tmp holds full content
  crash after step 3 (rename(tmp, final)   = dirent swap in page cache)
      -> undefined: final shows old OR new content OR is absent
  crash after step 4 (fsync(dir)           = dirent swap durable)
      -> final guaranteed NEW content
```

Read the two tables together: `data=ordered` never shows new-size-with-stale-
data, `data=writeback` does exactly once — that is the crash window that
corrupts user files. And in Part B the only *undefined* row is the one without
the directory fsync, which is the step lazy code omits.

## Interview lens

- **Why does `fsync(dir)` exist if rename is atomic?** Atomicity is a cache
  coherence property; durability needs the parent-dirent flush. The two are
  orthogonal.
- **Why do WALs call `fdatasync`?** The inode size changes on append, so
  fdatasync still persists it, but skips atime/mtime noise — fewer metadata
  IOs per commit ([WAL deep-dive](../../dbms/advanced/wal-internals.md)).
- **Why is `data=writeback` still an option?** Some workloads prefer
  throughput and can tolerate a rare torn file. Know the artifact, choose
  deliberately.
- **What does the OS guarantee about a file you never fsynced?** Nothing at
  crash time — ext4's heuristics (auto_da_alloc, 5-second commit intervals)
  make it "usually survives". The gap between specification and folklore is
  the interview trap.
- **Crash-consistent vs crash-atomic?** Journal replay recovers the
  filesystem's own metadata (consistent, fsck-able); *your* record's
  all-or-nothing requires an application protocol.

## Where this connects

- [WAL](../wal.md) — the application-side mirror of journaling; [InnoDB
  internals](./innodb-internals.md) for doublewrite defenses; [checkpointing](../../dbms/transactions/checkpointing.md)
  for when journal work is retired.
- [SQLite internals](../../dbms/internals/sqlite-internals.md) — a complete
  fsync protocol (rollback journal) in one codebase.
- [Writeback](../../linux/kernel/memory/writeback.md) — who decides when
  dirty pages move, before any fsync.
- [Device mapper](../../linux/embedded/device-mapper.md) — the layer
  dm-flakey and dm-log-writes live on.

## References

1. Pillai et al., "All File Systems Are Not Created Equal: On the Complexity
   of Crafting Crash Consistent Applications", OSDI 2014 —
   <https://www.usenix.org/conference/osdi14/technical-sessions/presentation/pillai>
   (PDF: <https://research.cs.wisc.edu/wind/Publications/alice-osdi14.pdf>)
2. ext4 kernel docs, journal options / data modes — <https://www.kernel.org/doc/html/latest/filesystems/ext4/journal.html>
3. Corbet, "Don't fear the fsync", LWN, Feb 2018 — <https://lwn.net/Articles/752063/>
4. PostgreSQL wiki, "Fsync Errors" (the fsyncgate postmortem) — <https://wiki.postgresql.org/wiki/Fsync_Errors>
5. `open(2)` man page (`O_DSYNC`, `O_SYNC`, `O_DIRECTORY`, `O_TMPFILE`) — <https://man7.org/linux/man-pages/man2/open.2.html>
