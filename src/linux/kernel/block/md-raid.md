# md/RAID Internals: Superblocks, Stripe Caches, and the Write Hole

> md is the kernel's software RAID driver — the `mdadm`-managed layer
> underneath millions of home servers, NAS appliances, and CI machines.
> Its internals are a masterclass in the constraints of crash
> consistency at the block layer: when a write spans disks and the
> machine dies halfway, what is on disk must still be *recoverable*.
> This page covers the on-disk superblock, the stripe cache, the write
> hole and the journal that fixes it, and the bitmap that turns
> crashes from full resyncs into minutes of patch-up.

## The On-Disk Superblock

Every member device carries an md superblock near (v0.90) or at
(v1.x, offset 4 KiB from start) the device start:

```text
 struct mdp_superblock_1 (key fields):
   magic / major_version     identifies the array metadata format
   set_uuid                  array identity (assembled by matching it)
   raid_disks, level, layout, chunk_sectors   geometry
   data_offset / data_size   where the array's data starts on this disk
   dev_roles[]               per-slot role: active / spare / faulty
   events (u64)              monotonically increasing event counter
   resync_offset             how far resync/recovery had progressed
   bitmap_offset             where the write-intent bitmap lives
```

Assembly (`mdadm --assemble`) is driven by the `events` counter: the
disk whose superblock has the *most events* is authoritative — stale
superblocks (a disk that missed writes) are detected by comparing
counters, which is how "this disk is 476 events behind" decisions get
made.

## RAID-5 Geometry and the Stripe Cache

A RAID-5 array of N disks with chunk size C stripes data as:

```text
 logical offset -> (stripe, column):
   stripe = offset / (C * (N-1))
   column = (offset % (C * (N-1))) / C
 parity column rotates per stripe (left-symmetric layout default)

 write to one chunk in a stripe:
   read old data + old parity, recompute, write both (read-modify-write)
   OR write full stripe if the write covers every data chunk
   (reconstruct-write)
```

The **stripe cache** (`/sys/block/md0/md/stripe_cache_size`, default
256 entries per stripe of 4 KiB pages) holds partially-filled stripes
so that read-modify-write can proceed without re-reading disk on
every small write. Sizing it is the classic md tuning knob: RAID-5
write workloads that exceed the cache thrash with repeated
reads of the same stripes — measurable directly in
`/proc/mdstat`-adjacent stats and in `iostat`'s read amplification.

## The Write Hole

RAID-5's atomicity problem: a stripe update writes data blocks and
parity across multiple disks; power loss mid-update can leave some
disks updated and others not. If a disk then *fails*, reconstruction
XORs the survivors — and one stale member silently produces wrong
data. That is the **write hole**: parity says the stripe is fine, but
its content is a torn mixture. RAID-5's parity cannot detect it
(unlike checksums, XOR validates nothing about history).

Three mitigations, in kernel history order:

1. **Write-intent bitmap**: a small on-disk bitmap of dirty stripes;
   after a crash, resync touches only marked stripes. This makes
   patch-up *faster* but does not fix the torn-stripe logic.
2. **RAID-5 journal (r5l)**: an NVM journal (a dedicated SSD device or
   journal region) to which data+parity are logged *before* being
   written to the array; after crash, the journal replays or discards
   stripes. Closes the hole at the cost of a journal write per stripe.
   Set with `mdadm --add --write-journal`.
3. **RAID-6 dual parity** narrows (not closes) the window: two failed
   members within one torn stripe still reconstructs wrong. PPL
   (Parity Persistence Log, md raid5-ppl) keeps parity consistent
   using the bitmap + partial parity instead of a separate device.

## Resync, Recovery, Reshape

- **Resync** (initial or scheduled): recompute parity across the whole
  array (`/proc/mdstat` shows completion). Read-modify-write per
  stripe; bitmap makes crash-resumed resyncs resume, not restart.
- **Recovery**: rebuild a *replacement disk* from surviving members
  (RAID-1: full copy; RAID-5: XOR reconstruct).
- **Reshape**: changing geometry (add a disk, grow chunk) online —
  the trickiest path; backup-file (`--backup-file`) protects the
  critical section where stripes are remapped mid-flight.

All three are checkpointed in the superblock's `resync_offset`, which
is why md arrays survive crash-during-rebuild.

## Worked Demo: Stripe Geometry and the Torn-Write Model

The demo maps a logical write to (stripe, column) for a given layout,
and simulates a torn write followed by reconstruction with and without
a journal, showing exactly which byte ranges the hole corrupts.

```python
# RAID-5 left-symmetric geometry + write-hole simulation.
from functools import reduce

def locate(offset, chunk, n_disks):
    """logical byte offset -> (stripe, column, chunk_offset)"""
    per_stripe = chunk * (n_disks - 1)
    stripe = offset // per_stripe
    within = offset % per_stripe
    column = within // chunk
    return stripe, column, within % chunk

print("layout: 4 disks, 64 KiB chunks (3 data + 1 rotating parity)")
for off in (0, 64 << 10, 192 << 10, 200 << 10):
    st, col, co = locate(off, 64 << 10, 4)
    print(f"  offset {off >> 10:>4} KiB -> stripe {st}, col {col}, "
          f"in-chunk {co >> 10} KiB")

# stripe: disk0 holds d0, disk2 d1, disk3 d2, disk1 parity P = d0^d1^d2
d0, d1, d2 = 0xAAAA, 0xBBBB, 0xCCCC
P = d0 ^ d1 ^ d2
print(f"\nparity for stripe: {P:#06x}")

# torn write: the update to disk1 (parity) is lost in a crash
P_stale = 0x1234                          # old parity still on disk
# disk0 then fails; md reconstructs d0 = P ^ d1 ^ d2
rec_stale = P_stale ^ d1 ^ d2
rec_ok = P ^ d1 ^ d2
print(f"disk0 fails after torn write:")
print(f"  reconstruct with STALE parity: {rec_stale:#06x}  (real d0={d0:#06x}) -> SILENT CORRUPTION")
print(f"  reconstruct with JOURNALED parity: {rec_ok:#06x}  -> correct")
```

Real output:

```text
layout: 4 disks, 64 KiB chunks (3 data + 1 rotating parity)
  offset    0 KiB -> stripe 0, col 0, in-chunk 0 KiB
  offset   64 KiB -> stripe 0, col 1, in-chunk 0 KiB
  offset  192 KiB -> stripe 1, col 0, in-chunk 0 KiB
  offset  200 KiB -> stripe 1, col 0, in-chunk 8 KiB

parity for stripe: 0xdddd
disk0 fails after torn write:
  reconstruct with STALE parity: 0x6543  (real d0=0xaaaa) -> SILENT CORRUPTION
  reconstruct with JOURNALED parity: 0xaaaa  -> correct
```

The geometry rows confirm the left-symmetric mapping: with 3 data
columns per stripe, offset 192 KiB starts stripe 1 (not a wrapped
column of stripe 0). The write-hole rows are the whole story in four
lines: the parity word on disk 1 is torn (crash before its update
landed), and md cannot tell — XOR has no era information. When disk 0
then fails, reconstruction `P_stale ^ d1 ^ d2` produces a *plausible*
but wrong d0: silent corruption, discovered only if a checksum
somewhere else catches it. The journal (r5l) or PPL exists to make
the parity update survive the crash so reconstruction starts from
truth.

## Interview Questions

1. What does the `events` counter decide during assembly, and what
   breaks if two disks tie? (Authoritativeness of the newest view;
   a tie is ambiguous — md refuses or requires `--force`, since
   guessing can pick a stale member.)
2. Why does a write-intent bitmap speed up crash recovery but not fix
   the write hole? (It narrows *which* stripes need repair, not
   whether a repaired stripe is internally consistent.)
3. When does md choose reconstruct-write over read-modify-write?
   (When the write covers all data chunks of a stripe — no reads
   needed.)
4. What does `stripe_cache_size` trade? (RAM for fewer re-reads on
   small RAID-5/6 writes; too small = stripe-cache thrash.)
5. Why does RAID-6 not close the write hole? (Parity correctness is
   XOR-consistency, which torn multi-disk writes can still satisfy
   while being wrong; only journalling/PPL adds ordering.)

## References

- Kernel md documentation: https://docs.kernel.org/driver-api/md/index.html
  (probed 200)
- RAID wiki (kernel.org): https://raid.wiki.kernel.org/index.php/RAID_setup
  (probed 200)
- mdadm(8) manual: https://man7.org/linux/man-pages/man8/mdadm.8.html
  (probed 200)
- Kernel source: `drivers/md/raid5.c` (stripe cache, r5l journal in
  `drivers/md/raid5-log.h`):
  https://github.com/torvalds/linux/blob/master/drivers/md/raid5.c
  (probed 200)
- NeilBrown's r5l design note (write-hole journal):
  https://docs.kernel.org/driver-api/md/raid5-ppl.html
  (probed 200)

## Cross-References

- [blk-mq](./blk-mq.md) — the multi-queue layer md submits through.
- [Crash consistency](../../../storage/advanced/crash-consistency.md) — the
  file-system-level twin of the write-hole problem.
- [Device mapper](./device-mapper.md) — the other block-layer
  transformation stack md coexists with.
