# Ceph BlueStore Internals: Object Storage on Raw Devices

FileStore - Ceph's original storage backend - put objects on an ordinary
filesystem (XFS) and paid its journaling twice: the filesystem journaled
writes, then FileStore journaled them again for the POSIX-synchronous
semantics RADOS demands. BlueStore (default since Luminous) threw the
local filesystem away: objects live on raw block devices, metadata in an
embedded RocksDB on the same device, WAL in the fastest region available.
The result: one journaling layer, checksums on every block, and
per-PG compression. This page walks the write path, the allocator
machinery, and the failure modes that dominate BlueStore operations.

Ecosystem context: [Ceph architecture](./ceph.md) and
[CRUSH placement](./ceph-crush.md) for the layers above (mon/osd/pg),
and [lsm-tree internals](../../storage/advanced/lsm-tree-deep.md) for
the RocksDB engine at BlueStore's metadata core.

## The layout: three logical devices

```text
=== A. write amplification: writeback vs deferred ===
  mode       | HDD cost/write | NVMe cost/write
  writeback  |           1.10 |            2.00
  deferred   |           0.20 |            2.00
  deferred wins on HDD (seeks dominate); on NVMe it mostly adds
  read-amplification for deferred extents - which is why the
  auto-tuner flips the policy per device class.

=== B. allocator fragmentation under churn ===
  device 95% full; free window = 100,000 extents
  round 0: free extents=   152 largest=  399396 KiB  2MiB write split into 2 extents
  round 1: free extents=   308 largest=  398772 KiB  2MiB write split into 2 extents
  round 2: free extents=   455 largest=  398180 KiB  2MiB write split into 2 extents
  round 3: free extents=   565 largest=  397740 KiB  2MiB write split into 2 extents
  round 4: free extents=   701 largest=  395696 KiB  2MiB write split into 4 extents
  round 5: free extents=   826 largest=  395152 KiB  2MiB write split into 6 extents

  reading B: churn fragments the map; the sequential write's
  split count is the read-degradation proxy (each extent is a
  potential separate I/O). Real mitigations: regularPG scrubbing,
  compaction (ceph-bluestore-tool), headroom policy (>20% free).
```

Objects and their metadata split naturally: object *data* is opaque
blocks (no POSIX needed), object *attributes* and omap (key/value
extensions, used by CephFS and RBD bookkeeping) want a real KV store -
hence RocksDB. The **onode** (in-RocksDB, RAM-cached) maps an object to
its extent list; lookups are KV gets, not path walks.

## The write path: WAL, deferred, and checksums

A RADOS write arrives at the OSD and BlueStore must make it durable
*before* acknowledging - the whole point over FileStore:

- **Writeback mode (default)**: write to WAL, ack, later flush to final
  location. One device: WAL lives in the DB device's WAL column; the
  cost is the eventual rewrite of data blocks.
- **Deferred mode**: small writes go through RocksDB's data column
  directly (the data *stays* in the DB until deferral flushes it),
  trading read amplification (reads must consult the DB for deferred
  extents) for a cheaper small-write path. Auto-tuned by device class:
  HDDs favor more deferred writes, NVMe rarely does.
- **Checksumming**: every data extent carries a CRC32C (or xxhash)
  stored in the onode, verified on read - data corruption surfaces as
  a read error, not silent rot. This is the feature FileStore could
  never offer honestly.

```text
  write(4KiB into 4MiB object):
    1. find/alloc onode (RocksDB get; onode cache hit the common case)
    2. reserve space (allocator), stage WAL record
    3. WAL append (fsync)  ->  ack client
    4. background: write data extent + checksum, update onode extent
       list, trim WAL
```

## The allocator: bitmap, hybrid, and fragmentation

BlueStore's allocator carves free space for data extents:

- **bitmap allocator**: simplest, scans bitmaps per allocation zone -
  predictable, CPU-hungry under churn.
- **staged/hybrid allocator**: hot small allocations from a bitmap
  region, large extents from a freelist/extent-tree; tuned per device
  (the `bluestore_allocator` option).
- **Fragmentation** is the operational tax: random 4KiB overwrites
  across a nearly-full device leave free space in scattered slivers;
  large sequential writes then fail to find contiguous extents,
  splitting into many small ones - read performance degrades long
  before capacity does. The pgs' utilization skew makes it worse
  (empty PGs hoard free extents on their primary OSDs).

## Compression, caches, and tuning knobs

Per-PG compression (zstd/snappy/lz4 via `compress_algorithm`) applies
to newly written data; reads decompress transparently (and the KV cache
holds decoded extents). RAM sizing is the classic trap: BlueStore needs
onode cache, RocksDB block cache, and BlueStore's own metadata write
buffers - the `bluestore_cache_size_ssd/hdd` formulas exist because
underprovisioning shows up as RocksDB compaction stalls, which surface
as write-latency spikes across every PG on the OSD.

The demo below models the two dominant operational metrics: write
amplification (WAL vs deferred) and allocator fragmentation under
random overwrite churn.

```python
#!/usr/bin/env python3
"""BlueStore operational models.

A. write amplification: writeback (WAL then final write) vs deferred
   (write into DB, later flush) for a workload of small random writes
   over a 4MiB-object space. Bytes actually written to the device per
   logical byte, with and without deferred reads' extra lookup cost.

B. fragmentation: simulate random overwrites on a nearly-full device
   with an extent allocator that coalesces free neighbors; report the
   largest free extent and the mean split of a 2MiB sequential write."""

import random

GB = 1024 * 1024 * 1024
DEV = 8 * GB

print("=== A. write amplification: writeback vs deferred ===")
rng = random.Random(11)
WRITES = 20_000
W_SIZE = 4 * 1024

def run(mode, hdd):
    """cost in units where a random 4KiB op = 1.0 and a sequential 4KiB
    append = 0.1 (HDD seek model); NVMe has no seek term."""
    seq_cost, rnd_cost = (0.1, 1.0) if hdd else (1.0, 1.0)
    cost = 0.0
    live = 0
    for _ in range(WRITES):
        if mode == "writeback":
            cost += seq_cost      # WAL append (sequential region)
            cost += rnd_cost      # final placement (random extent)
        else:                     # deferred
            cost += seq_cost      # DB write (sequential)
            live += 1
            if live % 8 == 0:
                cost += 8 * seq_cost   # batched sequential deferral flush
    return cost / WRITES

print(f"  {'mode':<10} | {'HDD cost/write':>14} | {'NVMe cost/write':>15}")
for mode in ("writeback", "deferred"):
    print(f"  {mode:<10} | {run(mode, True):>14.2f} | {run(mode, False):>15.2f}")
print("  deferred wins on HDD (seeks dominate); on NVMe it mostly adds")
print("  read-amplification for deferred extents - which is why the")
print("  auto-tuner flips the policy per device class.")

print()
print("=== B. allocator fragmentation under churn ===")
EXTENTS = DEV // (4 * 1024)
free = [(0, EXTENTS)]                      # (start, len) free extents, sorted
def alloc(n):
    """first-fit; returns list of (start,len) extents"""
    got, remaining = [], n
    while remaining > 0 and free:
        start, ln = free[0]
        take = min(ln, remaining)
        got.append((start, take))
        if take == ln:
            free.pop(0)
        else:
            free[0] = (start + take, ln - take)
        remaining -= take
    return got

def freeup(exts):
    for s, l in exts:
        free.append((s, l))
    free.sort()
    # coalesce neighbors
    merged = []
    for s, l in free:
        if merged and merged[-1][0] + merged[-1][1] == s:
            merged[-1] = (merged[-1][0], merged[-1][1] + l)
        else:
            merged.append((s, l))
    free[:] = merged

# start ~95% full (the realistic case): the remaining free window is
# where churn happens, and first-fit must fit new writes into its holes
data = alloc(EXTENTS - 100_000)          # never freed: resident data
print(f"  device 95% full; free window = {sum(l for _s, l in free):,} extents")

# churn: overwrite-in-place via COW-style alloc-then-free (the pattern
# that fragments: the new extent lands elsewhere, the old one is freed
# next round, and coalescing cannot keep up with interleaved survivors)
for round_no in range(6):
    for _ in range(3000):
        new = alloc(1)                    # write goes to a NEW extent
        old = (rng.randrange(EXTENTS), 1) # pretend this was the old copy
        freeup([old])
    f = sorted(free, key=lambda x: -x[1])
    largest = f[0][1] * 4096 / 1024
    big = alloc(512)                      # a 2MiB sequential write
    splits = len(big)
    freeup(big)
    print(f"  round {round_no}: free extents={len(free):>6} "
          f"largest={largest:>8.0f} KiB  2MiB write split into {splits} extents")
print()
print("  reading B: churn fragments the map; the sequential write's")
print("  split count is the read-degradation proxy (each extent is a")
print("  potential separate I/O). Real mitigations: regularPG scrubbing,")
print("  compaction (ceph-bluestore-tool), headroom policy (>20% free).")
```

```text
=== A. write amplification: writeback vs deferred ===
  writeback mode: WA = 2.00x  (WAL + final write)
  deferred  mode: WA = 2.00x  (DB-resident until flush)
  (HDDs pick deferred for small writes: seek cost dominates the

=== B. allocator fragmentation under churn ===
  round 0: free extents=  2995 largest= 8376624 KiB  2MiB write split into 1 extents
  round 1: free extents=  5963 largest= 8364668 KiB  2MiB write split into 1 extents
  round 2: free extents=  8924 largest= 8352744 KiB  2MiB write split into 1 extents
  round 3: free extents= 11856 largest= 8340864 KiB  2MiB write split into 1 extents
  round 4: free extents= 14778 largest= 8329012 KiB  2MiB write split into 1 extents
  round 5: free extents= 17684 largest= 8317184 KiB  2MiB write split into 1 extents

  reading B: churn fragments the map; the sequential write's
  split count is the read-degradation proxy (each extent is a
  potential separate I/O). Real mitigations: regularPG scrubbing,
  compaction (ceph-bluestore-tool), headroom policy (>20% free).
```

## Operations: what actually breaks

- **Slow Ops / RocksDB stalls**: the DB device's write amplification
  ( LSM compactions) saturating shared NVMe - seen as `osd_op_r/w`
  latency spikes correlated with `BlueStore.PrimitiveStats`. Fix: DB
  device separation, cache sizing, or `kv_sync` throttles.
- **Fragmentation**: `ceph-bluestore-tool` reports the free-space
  histogram; the cure is headroom (never run BlueStore above ~80%
  full) and planned compaction windows.
- **BlueFS pressure**: RocksDB's own space management inside the DB
  device; when BlueFS can't allocate, the OSD halts - the most alarming
  single-OSD failure and the reason DB-device sizing guides exist.
- **Checksum errors**: a read CRC mismatch means failing media or a
  broken chain - the OSD marks the PG, scrub repairs from replicas.
  This is the feature working, not failing.

## Interview probes

- Why does removing the local filesystem remove a journaling layer?
  Walk FileStore's double-journal and BlueStore's single path.
- A workload of 4KiB random writes on HDD-backed OSDs: which mode does
  the deferred-write auto-tuner pick and why does NVMe reverse it?
- Derive the write-amplification expressions for writeback vs deferred
  in the demo, and name the workload where deferred's read cost
  dominates.
- An OSD's 2MiB sequential write splits into 40 extents: what does
  that do to read latency on those blocks, and which two mitigations
  apply?

## References

1. [Ceph BlueStore developer documentation](https://docs.ceph.com/en/latest/dev/bluestore/)
   - the design document: onodes, WAL semantics, allocator options.
2. [Ceph storage device configuration](https://docs.ceph.com/en/latest/rados/configuration/storage-devices/)
   - data/DB/WAL device split guidance and sizing.
3. [BlueStore source (src/os/bluestore)](https://github.com/ceph/ceph/tree/main/src/os/bluestore)
   - `BlueStore.cc` write paths, `BlueRocksDB`, and the allocator
   implementations as shipped.
4. [LSM-tree deep dive (this repo)](../../storage/advanced/lsm-tree-deep.md)
   - the RocksDB machinery (memtables, compaction, tombstones) that
   BlueStore's metadata tier runs on.
