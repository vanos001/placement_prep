# ZNS and Zoned Storage: Handing the Erase Block Back to the Host

Every SSD ships a fiction: a spinning-disk interface over flash that is physically
erase-block oriented. The Flash Translation Layer (FTL) maintains that fiction with
an out-of-place write log and garbage collection -- invisible machinery that costs
DRAM, firmware complexity, and write amplification the host can neither see nor
control. Zoned storage replaces the fiction with a contract: the device exposes its
large erase/append units as **zones** that accept sequential writes only, and the
host owns placement and reclamation. The contract started on shingled HDDs (where
there is no alternative) and arrived on NAND as NVMe Zoned Namespaces, where it
deletes most of the FTL's write amplification and gives LSM engines, filesystems,
and WALs the append-only interface they already wanted. This page covers the SMR
origin, the zone state machine, write-pointer and zone-append semantics, the GC math
with a runnable comparison, and the software stack as it stands in mid-2026.
For the generic NVMe command surface see [NVMe](../nvme.md) (which mentions ZNS only
in passing) and for FTL mechanics see [SSDs](../ssd.md).

## 1. Shingling Broke the Spinning-Disk Fiction

Conventional magnetic recording (CMR) leaves guard bands between tracks so any
track can be rewritten independently. Shingled magnetic recording (SMR) removes
those guard bands and overlaps tracks like roof shingles, buying roughly 15-20%
more areal density per generation with the same heads and platters:

```text
CMR: guard bands make every track independently rewriteable

  track n      ##########..............................
  track n+1    ....##########..........................
  track n+2    ........##########......................
  track n+3    ............##########..................
               ^ written by the same wide head, but spacing
                 keeps the neighbor track intact

SMR: tracks overlap; track n+1 overwrites track n's edge

  track n      #####################....
  track n+1    .....#####################....
  track n+2    ..........#####################....
  track n+3    ...............#####################....
               track n's edge exists only because track n+1 was
               written over it -> touching track n in place would
               corrupt track n+1 -> the whole band is append-only
```

A **band** (SMR's native zone, commonly 256 MiB on current drives; 32 MiB on
UltraSMR generations) must be rewritten as a unit. Random in-place updates are
physically impossible on shingled media, so the interface question became: who
absorbs the rewrites?

## 2. Four Ways to Sell a Shingled Drive

| Interface | Contract | Random writes | Who does GC | Where you meet it |
| --------- | -------- | ------------- | ----------- | ----------------- |
| DM-SMR (drive-managed) | Looks like a normal disk | Accepted, then slow | Hidden STL inside the drive | Consumer external HDDs (the 2014-2019 RAID/WAL corruption scandals) |
| HA-SMR (host-aware) | Zone layout exposed, writes still accepted anywhere | Accepted | Shared: drive tolerates, host should avoid | Rare transitional drives |
| HM-SMR (host-managed) | Sequential-within-zone only | Rejected by the drive | Host, via zone resets | Cloud nearline HDD fleets |
| ZNS (NVMe Zoned Namespace) | Sequential-within-zone only, power-of-two zones | Rejected | Host | ZNS SSDs (first shipping: WD ZN540, 2021) |

T10 standardized the SCSI flavor (ZBC, 2015) and T13 the ATA flavor (ZAC); NVMe
ratified the Zoned Command Set (ZNS) 1.0 in June 2020 and added the Zone Append
command in ZNS 1.1 (August 2021, alongside the NVMe 2.0 spec reorganization that
split NVMe into a base plus command-set family -- see
[NVM Express specifications](https://nvmexpress.org/specifications/)). DM-SMR is the
cautionary tale: a hidden translation layer doing GC under a block interface
produces multi-second latency spikes whenever its internal log fills -- the exact
pathology ZNS exists to eliminate. Large cloud operators now run HM-SMR HDD fleets
at exabyte scale and publish the operational lessons (e.g., ElastiSMR, FAST 2024).

## 3. The Zone Model and Its State Machine

A zone is a contiguous LBA range with an explicit lifecycle. On ZNS, zone size is a
power of two (ZBC allows arbitrary sizes) and every zone descriptor carries: type
(sequential-write-required vs conventional), state, zone size, **zone capacity**
(the writable limit, possibly below the size), start LBA (ZSLBA), and the **write
pointer**. Reads are random-access everywhere, always. Writes and lifecycle
commands move the zone through a fixed machine:

```text
              write (first data)         write until pointer = capacity
    EMPTY -----------------> OPENED --------------------------------> FULL
     ^   OPEN ZONE cmd /       |   ^                                    ^
     |          ^  CLOSE ZONE  |   | write re-opens                      |
     |          |              v   |                                     |
     |          +------------> CLOSED ---------------------------------+
     |                  FINISH ZONE (also legal from OPENED)
     +--- RESET ZONE, from any writable state: pointer := 0, data destroyed
     READ ONLY / OFFLINE: drive-declared fault states, no host exit
```

| Operation | State effect | Write pointer | Notes |
| --------- | ------------ | ------------- | ----- |
| WRITE (regular) | EMPTY -> implicitly opened; closed -> opened | Must equal ZSLBA + current pointer offset | Violations fail (see rules below) |
| OPEN ZONE | EMPTY/closed -> explicitly opened | Unchanged | Pins a drive open-zone resource |
| CLOSE ZONE | Opened -> closed | Unchanged | Frees the open-zone resource, keeps data |
| FINISH ZONE | Any writable state -> full | Set to capacity | Seals the zone; makes reset cheap |
| RESET ZONE | Any state -> empty | Set to ZSLBA | Destructive, asymmetric-fast; the "erase" |
| APPEND (ZNS 1.1) | Same as write | Controller assigns the slot | See section 5 |

Two drive-declared resource limits shape scheduling: **maximum open zones** and
**maximum active zones** (open + closed), reported in identify data and sysfs
([kernel zoned sysfs ABI](https://www.kernel.org/doc/html/latest/admin-guide/abi-testing.html#sysfs-block-zoned)).
Exceeding the open limit fails writes or stalls them in the block layer, so
concurrent writers (WAL, compactor, checkpoint) must be budgeted against it.

## 4. Zone Size vs Zone Capacity, and the Write Pointer

```text
 zone size (power of two, e.g. 1 GiB) -- the LBA span
 +------------------------------------------------------+-----------+
 |        writable area = zone capacity                 |  unusable |
 |        (capacity <= size, reported per zone)         |   slack   |
 +------------------------------------------------------+-----------+
 ^ ZSLBA                                                ^           ^
 pointer starts here      pointer advances per write; stops at capacity
```

Zone capacity exists because internal NAND layout (parity grouping, die sizing)
rarely matches a power-of-two span exactly; the drive reports the usable count per
zone and everything past it rejects writes. The distinction trips up naive code
that assumes `capacity == size`.

The write pointer is the whole behavioral difference from a block device:

| Rule | Enforced by | What a violation looks like |
| ---- | ----------- | --------------------------- |
| Writes start exactly at the pointer | Drive + kernel block layer | `Zone Boundary Error` / `Zone Write Pointer Misaligned` |
| One write may not cross into the next zone | Drive | Error; host must split at the boundary |
| Writes past capacity fail | Drive | `Zone Is Full` until reset |
| Out-of-order writes to one zone fail | Drive | The interface has no insert-before-the-pointer |
| Reads at any LBA, any time | -- | Random reads are untouched |
| Rewriting live data requires append + reset | Host | Conventional update-in-place is unrepresentable |

Consequence: a zoned device cannot serve a random-overwrite workload **without**
host-side GC. That is not a bug but the point -- the host now pays for, and can
optimize, the copying the FTL used to hide.

## 5. Zone Append: Parallelism Without Breaking Sequentiality

Regular writes race: two queues writing to the same zone have no defined order, and
the pointer makes serialization mandatory. The Zone Append command (opcode `0x7D`,
ZNS 1.1) removes the coordination. The host submits appends addressed to the **zone
start LBA** rather than a target LBA; the controller atomically places each buffer
at the current pointer at execution time and returns the actual assigned LBA in the
completion queue entry. Many appends can be in flight to one zone from many queues;
the device weaves them into the only valid order.

This one command is why zoned filesystems stay parallel. btrfs's zoned mode issues
zone appends so metadata and data writers never serialize on a shared pointer, and
ZenFS uses them for RocksDB memtable flushes landing in shared zones. The host pays
a small price: block mappings are only known at completion time, so checksums and
metadata that reference LBAs must be written after the placement is known.

## 6. The GC Math, Simulated

For uniform random overwrites at full occupancy with greedy victim selection, the
steady-state media-write amplification of a log-structured FTL tends toward
`P/U = 1/(1 - OP)` (physical pages over user pages; 25% spare space implies a
1.33x floor). Real controllers land above the floor. The question ZNS answers is
not "can GC go away" -- for hostile workloads it cannot -- but "who runs it and
what does placement knowledge buy". The simulation below runs the **same op
stream** against two 16 MiB models: a conventional FTL (one shared append log,
greedy 256 KiB block GC) and a ZNS device (per-zone pointers, host-driven zone GC).
Workload A is pure random overwrite. Workload B interleaves a hot WAL (random
4 KiB rewrites of 32 slots) with an SST ring whose files die oldest-first -- an
LSM shape, where lifetimes are known at write time.

```python
"""Same host write streams, two interfaces: a conventional FTL SSD vs ZNS."""
import random
import sys

BLOCK = 64                       # pages per erase block / per zone (256 KiB)
NBLOCKS = 256                    # 16 MiB model: 16384 physical pages
PAGES = NBLOCKS * BLOCK
USER = int(PAGES * 0.75)         # 12288 pages exposed (25% spare space)
WAL_SLOTS = 32                   # logical pages of the hot WAL stream
FILE = 64                        # one SST file = one zone (64 pages)
RING = 186                       # live SST pages = 186 * 64 = 11904 <= USER

class FtlSSD:
    """Log-structured FTL: one shared append log, greedy block-level GC."""

    def __init__(self):
        self.map = {}                        # logical -> physical page
        self.state = [None] * PAGES          # physical -> logical or None
        self.valid = [0] * NBLOCKS           # live pages per block
        self.free = list(range(NBLOCKS))     # fully-free blocks
        self.open_blk = self.open_off = None
        self.host = self.media = self.copied = self.copies_wal = 0

    def place(self, l, stream=0, copy=False):
        if l in self.map:                    # invalidate previous version
            old = self.map[l]
            self.state[old] = None
            self.valid[old // BLOCK] -= 1
        while not self.free:
            self.gc()
        if self.open_blk is None or self.open_off == BLOCK:
            self.open_blk, self.open_off = self.free.pop(), 0
        p = self.open_blk * BLOCK + self.open_off
        self.open_off += 1
        self.state[p] = l
        self.map[l] = p
        self.valid[self.open_blk] += 1
        self.host += 0 if copy else 1
        self.media += 1

    def gc(self):
        victim = min((b for b in range(NBLOCKS) if b != self.open_blk),
                     key=lambda b: self.valid[b])
        live = []
        for p in range(victim * BLOCK, victim * BLOCK + BLOCK):
            l = self.state[p]
            if l is not None:
                self.state[p] = None
                del self.map[l]
                live.append(l)
        self.valid[victim] = 0
        self.copied += len(live)
        self.copies_wal += sum(1 for l in live if l < WAL_SLOTS)
        self.media += len(live)
        self.free.append(victim)
        for l in live:
            self.place(l, copy=True)         # survivors rewritten to the log

class ZonedSSD:
    """Host-managed: append-only zones, host-driven zone GC on reset."""

    def __init__(self):
        self.loc = {}                        # logical -> (zone, offset)
        self.data = [dict() for _ in range(NBLOCKS)]
        self.wp = [0] * NBLOCKS              # monotonic write pointer
        self.valid = [0] * NBLOCKS           # live pages per zone
        self.active = [None, None]           # one open zone per stream
        self.host = self.media = self.copied = self.copies_wal = 0
        self.free = list(range(NBLOCKS))

    def place(self, l, stream, copy=False):
        if l in self.loc:                    # append a newer version
            z, o = self.loc[l]
            del self.data[z][o]
            self.valid[z] -= 1
        if self.active[stream] is None:
            while not self.free:             # need a fresh zone: GC if none
                self.zone_gc()
            self.active[stream] = self.free.pop()
        z = self.active[stream]
        o = self.wp[z]                       # append strictly at the pointer
        self.wp[z] += 1
        self.data[z][o] = l
        self.loc[l] = (z, o)
        self.valid[z] += 1
        self.host += 0 if copy else 1
        self.media += 1
        if o + 1 == BLOCK:                   # zone full: seal it
            self.active[stream] = None

    def zone_gc(self):
        victim = min((z for z in range(NBLOCKS)
                      if z not in (self.active[0], self.active[1])),
                     key=lambda z: self.valid[z])
        live = sorted(self.data[victim].items())
        for _, l in live:
            del self.loc[l]
        self.data[victim].clear()
        self.wp[victim] = 0                  # reset: pointer back to zero
        self.valid[victim] = 0
        self.copied += len(live)
        self.copies_wal += sum(1 for _, l in live if l < WAL_SLOTS)
        self.media += len(live)
        self.free.append(victim)
        for _, l in live:
            self.place(l, 0 if l < WAL_SLOTS else 1, copy=True)

rng = random.Random(42)
sys.setrecursionlimit(50000)
print(f"geometry: {NBLOCKS} blocks/zones x {BLOCK} pages, "
      f"USER={USER} pages exposed (spare {100 * (1 - USER / PAGES):.0f}%)")
ops = [rng.randrange(USER) for _ in range(40000)]
print("\nworkload A: 40000 random 4 KiB overwrites of the whole keyspace")
for name, dev in (("FTL SSD", FtlSSD()), ("ZNS SSD", ZonedSSD())):
    for l in ops:
        dev.place(l, 0)
    print(f"  {name}: host={dev.host} media={dev.media} "
          f"GC copies={dev.copied} -> WAF={dev.media / dev.host:.2f}x")
print(f"  theory floor, zero-copy GC: P/U = {PAGES / USER:.2f}x")
ops = []
files = 0
for i in range(60000):                       # WAL overwrite + periodic flush
    ops.append((0, rng.randrange(WAL_SLOTS)))
    if i % 128 == 0:                         # one SST file = one zone
        f = files % RING                     # oldest file dies
        ops.extend((1, WAL_SLOTS + f * FILE + o) for o in range(FILE))
        files += 1
print(f"\nworkload B: {sum(1 for s, _ in ops if s == 0)} WAL overwrites "
      f"interleaved with {sum(1 for s, _ in ops if s == 1)} SST pages")
for name, dev in (("FTL SSD", FtlSSD()), ("ZNS SSD", ZonedSSD())):
    for s, l in ops:
        dev.place(l, s)
    print(f"  {name}: host={dev.host} media={dev.media} "
          f"GC copies={dev.copied} (WAL {dev.copies_wal}, "
          f"SST {dev.copied - dev.copies_wal}) -> "
          f"WAF={dev.media / dev.host:.2f}x")
```

Real output from this environment:

```text
geometry: 256 blocks/zones x 64 pages, USER=12288 pages exposed (spare 25%)

workload A: 40000 random 4 KiB overwrites of the whole keyspace
  FTL SSD: host=40000 media=70564 GC copies=15282 -> WAF=1.76x
  ZNS SSD: host=40000 media=76400 GC copies=18200 -> WAF=1.91x
  theory floor, zero-copy GC: P/U = 1.33x

workload B: 60000 WAL overwrites interleaved with 30016 SST pages
  FTL SSD: host=90016 media=125636 GC copies=17810 (WAL 2655, SST 15155) -> WAF=1.40x
  ZNS SSD: host=90016 media=90016 GC copies=0 (WAL 0, SST 0) -> WAF=1.00x
```

Read the numbers the way an architect should:

- **Workload A: zones are not magic.** The ZNS host GC lands *worse* than the FTL
  (1.91x vs 1.76x) because zone-granular GC copies coarser units than an FTL's
  block-granular log. On a workload where lifetimes are unknowable, ZNS buys you
  nothing and can cost slightly more. An FTL's hardware-managed GC also gets
  help the model denies both sides (interleaving across dies, read-disturb-aware
  victim choice, better caching).
- **Workload B: placement is the win.** The FTL still pays 1.40x, and 15,155 of
  its 17,810 GC copies are long-lived SST pages churned by WAL invalidations
  landing in shared blocks. The ZNS device -- same bytes, same volume -- does
  **zero** GC copies: the WAL stream is isolated in its own zones, and each SST
  file maps to one zone that dies completely when the file is compacted away, so
  "GC" degenerates into a free Reset Zone. The 1.33x "floor" applies to overwrite
  workloads; append-heavy streams with aligned lifetimes bypass it entirely.
- The lever was never the device; it is **lifetime-aware grouping**. ZNS forces
  the host to make that decision explicitly, which is exactly what an LSM engine,
  a WAL, or an append-only filesystem is capable of doing. (Multi-stream NVMe
  offered a hint of this earlier by labeling writes -- ZNS makes the contract
  enforceable.)

## 7. The Zoned Software Stack

| Layer | Project | Zoned strategy | Notes |
| ----- | ------- | -------------- | ----- |
| Raw exposure | [zonefs](https://www.kernel.org/doc/html/latest/filesystems/zonefs.html) (kernel 5.6) | Each zone becomes one append-only file sized to its capacity | Simplest way to use a zoned device; used by HSM-style backends |
| POSIX filesystem | F2FS ([kernel doc](https://www.kernel.org/doc/html/latest/filesystems/f2fs.html)) | Data + node writes forced sequential into zones; metadata lives in conventional zones (or a separate conventional device); handles `capacity < size` by masking segments | The general-purpose zoned filesystem; `mkfs.f2fs` marks the device zoned |
| POSIX filesystem | btrfs ([zoned mode, kernel 5.12](https://btrfs.readthedocs.io/en/latest/btrfs-man5.html)) | Zone-aligned extent allocation, sequential writes via zone append, superblock log in dedicated conventional zones | Copy-on-write maps naturally onto zones; `zoned=on` mount option |
| KV store | [ZenFS](https://github.com/westerndigitalcorporation/zenfs) (Western Digital) | RocksDB FileSystem plugin: one zone per SST file, WAL zones, zone-append flushes, online `gc` subcommand | Often cited result: substantially better tail latency and near-flat WAF vs ext4-on-FTL for LSM workloads |
| Legacy bridge | dm-zoned (kernel 4.12, reworked as v2) | Hides a zoned device behind a random-write block device using conventional zones as a cache | Useful for unmodified software; reintroduces a mini-FTL, so it reintroduces some GC |

The layering principle across all of them: **map allocation units to zones so that
data with one lifetime lives in one zone**, and free space becomes Reset Zone
instead of garbage collection. F2FS and btrfs handle metadata either in
conventional zones or via careful append logs; engines like RocksDB simply have
fewer random-write obligations than a POSIX filesystem does.

## 8. Ops Realities

- **Zone size is a hard allocation unit.** 1-2 GiB zones on ZNS SSDs and ~256 MiB
  zones on HM-SMR HDDs mean a 4 KiB record that lands alone in a zone wastes the
  rest. Packing by lifetime is mandatory design work, not an optimization.
- **Budget open zones.** Every implicitly-opened zone consumes a drive resource.
  A 50-writer service can exhaust a double-digit open-zone limit and start eating
  errors; cap concurrent writers per device or pre-open zones explicitly.
- **Capacity is not size.** Anything reading geometry must use per-zone capacity;
  early tooling assumed equality and wrote into the slack.
- **Reset Zone is your TRIM, and it is destructive.** There is no undelete; trim
  and snapshot-expiry paths map to resets. Plan replication for the durability
  you just gave up.
- **Random-write dependencies break.** No swap, no dm-raid, no in-place-editing
  tools (`dd conv=notrunc` returns EINVAL), no RAID5/6 parity shuffling. Device-
  mapper layers that preserve sector identity (dm-crypt, dm-linear) are fine;
  newer 6.x kernels add zone write plugging to make more stacks zone-safe.
- **Instrument before you commit.** `/sys/block/<dev>/queue/zoned`, `chunk_sectors`,
  `max_open_zones`, `max_active_zones`; `blkzone report`, `nvme zns report-zones`,
  and the libnvme/libzbd libraries. For testing, `null_blk` with zoned support,
  QEMU's zoned device emulation, and tcmu-runner-backed drives cover CI without
  real hardware.
- **HDD vs SSD flavor differs.** On HM-SMR HDDs the win is density at nearline
  cost with sequential rebuilds; on ZNS SSDs the win is tail latency and the
  removal of FTL DRAM/write-amplification. UltraSMR (32 MiB zones) required
  custom host stacks -- evidence that the contract, not the medium, is the
  technology.

Questions worth being able to answer cold: why can a zoned device skip most FTL
DRAM? (No random-write remap table; mappings are the host's.) Why does zone append
exist if writes are sequential anyway? (Cross-queue parallelism without pointer
races.) Why did DM-SMR earn its reputation? (A hidden STL behind a fake block
interface -- the pathology ZNS makes impossible to hide.) When is ZNS the wrong
choice? (Workload A: lifetime-unknowable random overwrites on a small footprint.)

## Related Pages

- [NVMe](../nvme.md) -- command-set basics; ZNS rides on the NVMe 2.0 command-set family.
- [SSDs and the FTL](../ssd.md) -- the in-device GC machinery that zones push into the host.
- [Storage Engine Internals](./storage-internals.md) -- how engines consume raw devices.
- [LSM Trees](./lsm-tree-deep.md) -- the workload shape ZenFS was built for.
- [F2FS](../../linux/kernel/filesystems/f2fs.md) -- the filesystem side of sequential allocation.

## References

1. ZonedStorage.io, "Zoned Namespace (ZNS) SSDs" -- <https://zonedstorage.io/docs/introduction/zns>
2. NVM Express, "NVM Express Specifications" (Zoned Command Set 1.0/1.1, NVMe 2.0 family) -- <https://nvmexpress.org/specifications/>
3. Linux Kernel Organization, "Sysfs block zoned attributes" (zoned block device ABI) -- <https://www.kernel.org/doc/html/latest/admin-guide/abi-testing.html#sysfs-block-zoned>
4. Western Digital, "ZenFS: FileSystem for zoned block devices" (RocksDB plugin) -- <https://github.com/westerndigitalcorporation/zenfs>
5. Linux Kernel Organization, "zonefs - zone filesystem" -- <https://www.kernel.org/doc/html/latest/filesystems/zonefs.html>
