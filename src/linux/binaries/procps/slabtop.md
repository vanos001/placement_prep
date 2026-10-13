# slabtop — display kernel slab allocator cache statistics live

## Overview

`slabtop` is `top` for the kernel's slab allocator: a refreshing, sortable display of the kernel's object caches — dentries, inodes, `task_struct`s, `kmalloc-*` buckets — with object counts, per-object sizes, and per-cache memory. It ships in the `procps` package (Debian bookworm: procps-ng 2:4.0.4) at `/usr/bin/slabtop` and reads a single file, `/proc/slabinfo`, once per refresh.

The slab allocator is how the kernel hands out fixed-size, frequently reused objects (directory entries, inodes, task structures) without paying kmalloc/memcpy costs each time. Each *cache* holds objects of one type, organized into *slabs* (one or more pages each). `slabtop` shows you which of these caches hold your RAM — the answer to "where did 6 GB of my memory go that neither processes nor page cache seem to account for" is usually visible in slabtop's first screen.

`slabtop` is often confused with `free`: the `Slab` line in `free -h` (from `/proc/meminfo`) is the system-wide total, while slabtop breaks that total down per cache. It is also confused with per-process memory tools — slab memory belongs to the kernel, no process owns it, so nothing in `ps`/`top` will ever show it.

| Field | Value |
| --- | --- |
| Package | procps (Debian bookworm: procps-ng 2:4.0.4) |
| Man section | 1 |
| Path | /usr/bin/slabtop |
| First appeared | procps 3.x era (early 2000s), by Chris Rivera and Robert Love, inspired by Martin Bligh's perl `vmtop` |
| Standards | None; Linux procfs-specific (`/proc/slabinfo` v1.1+) |

## Synopsis

```
slabtop [options]
```

Common one-line forms:

```
slabtop                  # live view, refresh every 3 s, sorted by object count
slabtop -o               # one shot, then exit (the scriptable mode)
slabtop -o -s c          # one shot, sorted by cache size
slabtop -s n -d 10       # live, alphabetical by cache name, 10 s refresh
```

## How It Works

### From slabinfo to the screen

```
/proc/slabinfo  (0400, root on modern kernels)
   <cache>  active_objs  num_objs  objsize  objperslab  pagesperslab
            : tunables (limit batchcount sharedfactor)
            : slabdata (active_slabs num_slabs sharedavail)
        │
        ▼   parsed once per refresh (default every 3 s)
┌──────────────────────────────────────────────────────────────────┐
│ OBJS ACTIVE  USE OBJ SIZE  SLABS OBJ/SLAB CACHE SIZE NAME        │
│ ...sorted by the chosen criterion, paged to the terminal...      │
└──────────────────────────────────────────────────────────────────┘
```

Each output row is one slab cache. The columns:

- **OBJS / ACTIVE / USE** — total allocated objects, how many are in use, and the ratio as a percentage. A cache with huge OBJS but low USE is holding memory for objects nothing is using (usually fine: that is caching).
- **OBJ SIZE** — bytes per object (dentry-class objects are on the order of a couple hundred bytes; `kmalloc-4K` is 4096).
- **SLABS / OBJ/SLAB** — how many slabs (page groups) back the cache and how many objects fit per slab. Under memory pressure the kernel's SLUB allocator can fall back to smaller slabs, so OBJ/SLAB for the same cache varies between systems and moments.
- **CACHE SIZE** — the cache's memory footprint. The man page warns this is an *upper bound estimate*, computed from pages-per-slab assumptions; under SLUB fallback it overstates. For accounting truth, cross-check the `Slab`/`SReclaimable`/`SUnreclaim` lines of `/proc/meminfo`.

The two caches you will see huge on any file server:

- **dentry** — one object per directory entry the kernel has looked up. A `find /` or a build can push it into the millions of objects. It is reclaimable: the kernel shrinks it under pressure or via `drop_caches`.
- **inode_cache** — one object per cached VFS in-memory inode. Grows with distinct files touched; also reclaimable.

Beyond those: `anon_vma`, `radix_tree_node`/`xa_node` (page-cache radix trees), `task_struct`, `mm_struct`, `kmalloc-<size>` buckets (unreclaimable general kernel memory), and filesystem-private caches (`ext4_inode_cache`, `nfs_inode_cache`, ...). The NAME column tells you which subsystem to blame.

### What slabinfo's three sections actually say

`/proc/slabinfo` (and thus slabtop's inputs) is one line per cache with three colon-separated sections:

```
dentry  512000  509900  192  8  1 : tunables    0    0    0 : slabdata  16000  16000      0
 <name> <active> <objs> <size> <objperslab> <pagesperslab> : tunables <limit> <batchcount> <sharedfactor> : slabdata <active_slabs> <num_slabs> <sharedavail>
```

- The first section is everything slabtop displays: live object counts, object size, objects per slab, pages per slab.
- The **tunables** section (`limit batchcount sharedfactor`) belongs to the legacy SLAB allocator's per-CPU cache management; under SLUB — the default allocator on every current distribution — it reads zeros, and slabtop's display ignores it.
- The **slabdata** section counts slabs: active vs total (the gap is partially-empty slabs the kernel can reclaim or refill) and, on NUMA SLAB, shared-allocator availability. The `v` (active slabs) and `p` (pages per slab) sort criteria read this section, which is why they are flagged "not displayed" in the header mapping — they rank caches without their own column.

### Reconciling with /proc/meminfo

The sanity check for every slabtop session is meminfo's slab lines:

```bash
$ grep -E '^(Slab|SReclaimable|SUnreclaim):' /proc/meminfo
Slab:             534964 kB
SReclaimable:     491524 kB
SUnreclaim:        43440 kB
```

`Slab` is the whole kernel slab heap. `SReclaimable` is the part the kernel can drop under pressure — dominated by the dentry, inode, and filesystem caches; `SUnreclaim` is pinned kernel memory — `kmalloc-*` buckets, `task_struct`s, buffers that cannot just be evicted. The mapping to slabtop is approximate (CACHE SIZE overestimates as described above), but the workflow stands: if `SUnreclaim` is the big number, slabtop sorted by size pointing at `kmalloc-*` tells you which size class to suspect; if `SReclaimable` dominates, dentry/inode caches are your answer and `vm.vfs_cache_pressure` is the knob.

Note also what slabtop is *not*: it cannot tell you which process drove a cache's growth. Slab objects belong to the kernel; attribution to workloads is inference (from timing, from cgroup `memory.stat`, or from knowing what just ran).

### Sorting and interaction

The default sort is object count (`o`). While slabtop runs, pressing any sort character re-sorts immediately; `q` or `Q` quits; spacebar forces a refresh.

| Char | Sorts by | Header |
| --- | --- | --- |
| `o` (default) | number of objects | OBJS |
| `a` | number of active objects | ACTIVE |
| `u` | cache utilization | USE |
| `s` | object size | OBJ SIZE |
| `b` | objects per slab | OBJ/SLAB |
| `c` | cache size | CACHE SIZE |
| `l` | number of slabs | SLABS |
| `n` | cache name | NAME |
| `v` | number of active slabs | (not displayed) |
| `p` | pages per slab | (not displayed) |

The top of the display also carries a summary header of total slabs/objects and bytes across all caches — a live counterpart of meminfo's `Slab` line.

### Permissions

On modern kernels `/proc/slabinfo` is `0400 root:root`, so slabtop needs root (or `sudo`):

```bash
$ slabtop -o
slabtop: Unable to create slabinfo structure: Permission denied
$ echo $?
1
$ sudo slabtop -o | head -3
```

Older systems allowed world-readable slabinfo; hardened kernels and most current distributions do not. This makes `slabtop` one of the few procps tools that routinely requires sudo.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-d, --delay <secs>` | Refresh interval; default 3 s. Not combinable with `-o` |
| `-o, --once` | Print one snapshot and exit — the scriptable/CI mode |
| `-s, --sort <char>` | Initial sort criterion (see table above); default `o` |
| `-h`, `-V` | Help / version |

## Usage Patterns

```bash
# What is eating kernel memory right now? (biggest caches by size)
sudo slabtop -o -s c | head -12

# Baseline before a workload, for comparison afterwards
sudo slabtop -o -s c > /tmp/slab-before.txt
./run_workload.sh
sudo slabtop -o -s c > /tmp/slab-after.txt
diff /tmp/slab-before.txt /tmp/slab-after.txt

# Dentry cache under a metadata-heavy workload (watch it balloon)
sudo slabtop -o -s n | grep -E '^(dentry|inode_cache)'

# Watch slab shrink when you ask the kernel to drop caches
sudo slabtop -o -s c | head -3
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
sudo slabtop -o -s c | head -3

# Log slab growth every 5 minutes for a leak investigation
* * * * * root slabtop -o -s c | head -6 >> /var/log/slab-history.log

# Sort by utilization to spot half-dead caches (allocated, unused)
sudo slabtop -o -s u | head

# Distinguish reclaimable caches from pinned kernel allocations
sudo slabtop -o -s n | grep -E 'kmalloc'   # generally SUnreclaim
sudo grep -E 'Slab|Reclaim' /proc/meminfo

# Per-fileserver triage: NFS client caches
sudo slabtop -o -s c | grep -E 'nfs|rpc'

# Confirm the memory came back after the workload ends (plateau, not growth)
sudo slabtop -o -s c | head -4 ; sleep 300 ; sudo slabtop -o -s c | head -4

# Correlate slabtop's biggest cache with meminfo's reclaimable pool
sudo slabtop -o -s c | head -3
grep -E '^(Slab|SReclaimable|SUnreclaim):' /proc/meminfo

# Spot half-empty slabs: high OBJS but low USE means cached-not-used
sudo slabtop -o -s a | head -8

# After tuning vm.vfs_cache_pressure, confirm dentry actually shrank
sysctl vm.vfs_cache_pressure
sudo slabtop -o -s n | grep -E '^(dentry|inode_cache)'

# Feed a log parser: dump name and size columns for charting
sudo slabtop -o -s c | awk 'NR>1 {print $NF, $(NF-1)}' | head -20
```

## Nuances and Gotchas

- **Needs root on current kernels.** `/proc/slabinfo` is 0400; slabtop without privileges exits 1 with "Unable to create slabinfo structure: Permission denied". In containers, even root may be denied by the runtime masking procfs.
- **Slab is host-global, not namespaced.** `/proc/slabinfo` has no per-container view (unless lxcfs-style fakery is in place): slabtop inside a container shows the host's kernel caches, so do not attribute them to the container's workload.
- **CACHE SIZE lies a little.** It assumes constant pages-per-slab, but SLUB's order fallbacks under memory pressure shrink slabs, so the column overestimates. The man page says this explicitly — quote it back when someone "finds" more slab than RAM.
- **Big dentry/inode caches are usually healthy.** They are reclaimable caches; the kernel will evict under pressure. Alarm is warranted only when they grow without bound, keep the machine in direct reclaim, or stay pinned after the workload ends (leak or mounts/fds pinning objects).
- **`-o` and `-d` are mutually exclusive** (documented); `-o` is one snapshot by definition.
- **Sort characters change live output mid-run** — a stray keypress in an interactive session silently re-sorts; harmless but confusing when pasting from a scrollback.
- **Kernel-version drift.** Cache names come and go (`radix_tree_node` became `radix_tree_node`+`xa_node`, SLAB vs SLUB tunables changed); scripts should match on well-known names like `dentry`, `inode_cache`, `kmalloc-` prefixes and tolerate new rows.
- **slabtop cannot show per-cgroup slab.** Kernel memory accounting per cgroup (`memory.kmem` / cgroup v2 `memory.stat` `slab` field) lives in the cgroupfs, not slabinfo.
- **The refresh reads the whole file every tick.** `/proc/slabinfo` is regenerated on each read (not cached), so a 1-second `-d` on a box with thousands of caches costs real kernel time; `-d 3` default and `-o` for cron samples are the polite choices.
- **Numbers move even when idle.** The kernel regularly drains partial slabs, so OBJS/CACHE SIZE wobble a few percent between refreshes even on a quiet system — alarm on trends, not on single readings.

## Exit Status

- `0` — snapshot (or refreshed session) produced successfully.
- `1` — failure; in practice seen when `/proc/slabinfo` is unreadable: `slabtop: Unable to create slabinfo structure: Permission denied` (non-root on modern kernels).

## Related Commands

- [`free`](./free.md) — the `Slab`/`SReclaimable` totals slabtop decomposes.
- [`vmstat`](./vmstat.md) — system-wide trends including memory pressure over time.
- [`top`](./top.md) — per-process memory; deliberately blind to slab, which belongs to the kernel.
- [`sysctl`](./sysctl.md) — tunables around reclaim behavior (`vm.vfs_cache_pressure`, `vm.drop_caches`).
- [`ps`](./ps.md) — confirms the memory is *not* in any process.
- [`overview`](./overview.md) — procps collection hub.
- [Process management](../../admin/process-management.md) — kernel memory vs process memory in context.

## Interview Questions

### Q: What is the slab allocator, and why does the kernel need per-object caches?

The kernel constantly allocates small fixed-size objects — dentries, inodes, task_structs, buffers. Constructing and tearing these down one page at a time via the page allocator would dominate runtime and fragment memory. Slab caches pre-construct (SLAB) or size-class-manage (SLUB, the modern default) objects of one type per cache, so allocation is a freelist pop and reuse keeps hot objects warm. `slabtop` exposes those caches because they are the kernel's own heap, invisible to per-process tools.

### Q: You have 6 GB of unexplained memory usage: processes sum to 2 GB, page cache doesn't cover the rest. What do you do?

Check the slab. `free -h` shows `Slab` (with `SReclaimable`/`SUnreclaim` breakdown in `/proc/meminfo`); `sudo slabtop -o -s c` names the caches. A multi-million-object dentry or inode_cache after a metadata-heavy batch is normal reclaimable cache; endless growth of something like `kmalloc-*` or a filesystem cache points at a kernel leak or at pinned objects (mounts, open fds). The fix for the benign case is letting reclaim work or tuning `vm.vfs_cache_pressure`; for the leak case, capture `slabinfo` history and take it to the kernel/filesystem maintainers.

### Q: What do the dentry and inode_cache entries actually represent, and why does a `find /` inflate them?

A dentry is the kernel's record of one path component lookup (name → inode association); the dentry cache makes repeated path traversal cheap. inode_cache holds in-core VFS inode structs for files the kernel has touched. `find /` walks every directory in the tree, so every component of every path becomes a dentry and every file an inode — both caches grow to reflect the whole filesystem. They shrink on their own under memory pressure (or via `echo 2/3 > /proc/sys/vm/drop_caches`), which is why a big dentry cache on a healthy system is a feature, not a leak.

### Q: Why is slabtop's CACHE SIZE column not the same as the Slab field in /proc/meminfo?

slabtop computes per-cache size from object counts, object size, and an assumed pages-per-slab — an upper-bound estimate, and the man page notes SLUB order fallbacks under pressure make it overestimate. meminfo's `Slab` counts actual pages charged. For system truth use meminfo; use slabtop for attribution across caches and for trend watching. The discrepancy itself is a favorite gotcha because 10–20% inflation is enough to make someone "discover" memory that does not exist.

### Q: Why does slabtop require root, and what does that imply for monitoring in containers?

`/proc/slabinfo` is 0400 root on modern kernels because it exposes kernel internals that have historically been information leaks. In containers, unprivileged users cannot read it at all, and even root sees the host-wide (non-namespaced) numbers — so a container-side slabtop cannot answer "how much slab does my container use". For per-container kernel memory you need cgroup memory accounting (`memory.stat`'s `slab` line), not slabinfo.

### Q: How would you catch a dentry leak versus healthy cache growth?

Sample `sudo slabtop -o -s n | grep dentry` on a schedule and correlate with workload. Healthy growth plateaus (bounded by distinct paths touched) and drops after reclaim events or cache drops; a leak grows monotonically across workloads and survives `drop_caches` (objects can't be freed if refcounts are stuck). Long-lived growth pinned by specific mounts or open files is the middle case — trace which mount is being held via `mounts` and `/proc/*/fd` before declaring a kernel bug.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/procps/slabtop.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/procps/)
