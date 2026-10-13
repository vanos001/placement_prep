# blkzone — report and reset zones on zoned block devices

## Overview

`blkzone` manages *zoned block devices* — disks whose address space is
divided into fixed-size zones that must mostly be written sequentially:
shingled magnetic recording (SMR) HDDs and NVMe ZNS (Zoned Namespace) SSDs.
It reports the zone layout and state (`report`, `capacity`), and drives the
zone state machine (`reset`, `open`, `close`, `finish`). It ships in the
`util-linux` package at `/usr/sbin/blkzone` and is essentially the only
generic, distribution-shipped command-line interface to the kernel's zoned
block ioctls.

You reach for it when working with SMR drives (many large nearline HDDs
since ~2014 are host-managed or host-aware SMR), with NVMe ZNS test
systems, with zoned filesystems (btrfs and f2fs have zoned modes, xfs in
recent kernels), or with `zonefs`, the filesystem that exposes zones as
files. It is often confused with `blkdiscard` (whole-device/range
unmapping, no zone semantics), with `nvme zns ...` (the NVMe-specific
equivalent with more vendor detail), and with `hdparm` (ATA-level, not
zone-aware).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/blkzone |
| First appeared | util-linux 2.30 (2017), for kernel 4.10 zoned support |
| Standards | Linux zoned-block-device ioctls (BLKREPORTZONE / BLKRESETZONE et al.) |

## Synopsis

```
blkzone <command> [options] <device>
```

Main one-line forms:

```
blkzone report /dev/nullb0         # dump zone map of the device
blkzone capacity /dev/nullb0       # total usable zone capacity
blkzone reset -o 0 -c 4 /dev/nullb0  # reset the first 4 zones
blkzone open|close|finish -o <sec> /dev/nullb0
```

All offsets and lengths are in **512-byte sectors**, even on 4K devices —
a deliberate contrast with `blkdiscard`, whose equivalents are bytes.

## How It Works

### The zoned device model

A zoned device is divided into zones of equal size (e.g. 256 MiB on many
SMR drives). Each zone is one of two types and walks a small state machine:

```
   zone type:  Conventional (random write allowed, like a small disk)
               Sequential-Write-Required (SWR):
                  must write at the write pointer, no rewrites in place

   SWR zone lifecycle:

     Empty ──write──► Implicit-open ──(explicit open)──► Explicit-open
        │                                                    │
        │              (zone fills up)                       ▼
        └──────────────────────────────────────────────►  Full
                                                           │
     reset ◄──── any non-empty state ──────────────── finish/close
        │
        ▼
      Empty again (write pointer back to zone start)
```

States visible in `report` output: `nm` (not modelled/empty in older
kernels), `eo`/`io` (explicitly/implicitly open), `cl` (closed), `fu`
(full), `ro` (read-only), `of` (offline).

### What report shows

```
$ blkzone report /dev/nullb0 | head -3
start: 0x000000000, len 0x02000, cap 0x02000, wptr 0x000000 reset:0 non-seq:0 zuc?:0, type:0x1 (SWR), cond:0x1 (imp-open)
...
#  start  zone start in 512-byte sectors (hex)
#  len    zone size in sectors            -> 0x2000 = 4096 sectors = 2 MiB
#  cap    usable capacity (may be < len on "zoned + capacity" drives)
#  wptr   write pointer: next sector to write (0 when empty)
#  type   0x1 = conventional, 0x2 = sequential-write-required
#  cond   zone condition/state (empty, imp-open, exp-open, closed, full...)
```

The exact field names have varied slightly across util-linux/kernel
versions; the semantics above are stable. `capacity` prints the sum of
zone capacities — the honest "how much can I store" number for drives
where `cap < len` (common on ZNS with padding).

### Reset is the zone equivalent of discard

`blkzone reset` returns zones to Empty: the write pointer goes back to the
zone start and the device may immediately reuse the space. It is the
fastest way to reclaim space on an SMR/ZNS device and is what filesystems
issue when a file is deleted on a zoned volume. All zone commands that
change state (`reset`, `open`, `close`, `finish`) refuse by default on
devices the kernel considers in use — `-f` overrides that guard, not the
device's own refusal (`EROFS`, `EIO`).

```
$ blkzone reset -o 0x0 -l 0x02000 /dev/nullb0
#                  └── one zone: offset = zone start, length = zone size
$ blkzone reset -c 8 /dev/nullb0
#                  └── reset 8 consecutive zones starting at -o (default 0)
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `report` | Print the zone map (start/len/cap/wptr/type/cond per zone) |
| `capacity` | Print the sum of zone capacities in 512-byte sectors |
| `reset` | Return the selected zones to Empty (destructive, like discard) |
| `open` | Explicitly open zones (transition Empty/Full → open) |
| `close` | Close explicitly opened zones (frees device open-zone resources) |
| `finish` | Seal zones as Full (write pointer = end; readable, not writable) |
| `-o, --offset <sec>` | Start sector of the range (512-byte units) |
| `-l, --length <sec>` | Maximum range length in sectors |
| `-c, --count <num>` | Maximum number of zones to act on |
| `-f, --force` | Act even if the device is mounted/in use (use with care) |
| `-v, --verbose` | More detail in report output |

## Usage Patterns

```bash
# Discover whether a disk is zoned at all
lsblk -z /dev/sdb                 # zone size column (newer lsblk)
cat /sys/block/sdb/queue/zoned    # host-managed | host-aware | none
```

```bash
# Dump the whole zone map of a test device
blkzone report /dev/nullb0 | head -16
```

```bash
# How many zones, how big, how much real capacity?
blkzone report /dev/nullb0 | wc -l
blkzone capacity /dev/nullb0
```

```bash
# Reset the entire device: the zoned equivalent of blkdiscard
blkzone reset /dev/nullb0
```

```bash
# Reset one specific zone containing a deleted file's extent
blkzone reset -o 0x40000000 -l 0x20000 /dev/nullb0
```

```bash
# Drive the state machine by hand (test harness work)
blkzone open   -o 0x0 /dev/nullb0
blkzone finish -o 0x0 /dev/nullb0
blkzone report -o 0x0 /dev/nullb0 | head -1
```

```bash
# Script guard: only reset when the device is not mounted
mountpoint -q /mnt/zns || blkzone reset /dev/nullb0
```

```bash
# Watch the write pointer advance while a sequential writer runs
dd if=/dev/zero of=/dev/nullb0 bs=1M count=64 conv=notrunc &
watch -n1 "blkzone report -o 0x0 /dev/nullb0 | head -1"
```

## Nuances and Gotchas

- **Sector units, not bytes.** `-o`/`-l` count 512-byte sectors here;
  `blkdiscard` uses bytes for the same-named options. This inconsistency
  inside one package is a documented trap.
- **Zones must be addressed at zone boundaries.** Offsets that are not a
  zone start fail or truncate the range; derive boundaries from `report`
  output or `/sys/block/<dev>/queue/chunk_sectors`.
- **reset is destructive and instant.** There is no confirmation, and on a
  zoned filesystem the result is equivalent to deleting everything in
  those zones — the filesystem then sees stale/zeroed pointers.
- **Host-aware vs host-managed.** Host-*managed* devices enforce the zone
  rules in hardware (writes out of order fail); host-*aware* tolerate them
  with catastrophic performance. `blkzone` matters most for host-managed
  and ZNS; on host-aware drives the kernel may already be managing zones
  behind your back.
- **Open-zone limits.** Devices allow a limited number of simultaneously
  open zones; `open` beyond the limit fails. `close` returns those
  resources; `finish` seals a zone as Full permanently (until reset).
- **Device support is niche.** Regular SSDs/HDDs return `ENOTTY`/`EINVAL`
  for all blkzone commands — `zoned: none` in sysfs is your first check.
  The `nullb` (null_blk) test module with `zb=1` is the standard way to
  get a zoned device for experiments.
- **cap vs len.** On drives where zone capacity is smaller than zone size
  (ZNS padding), free space math must use `cap`, not `len`; `capacity`
  command and the report's `cap` field reflect this.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Command succeeded (report printed, zones reset/opened/closed/finished) |
| 1 | Usage error, device not zoned, unsupported command, or I/O error |

## Related Commands

- [`blkdiscard`](./blkdiscard.md) — the non-zoned unmapping sibling; byte-based offsets
- [`blockdev`](./blockdev.md) — `--getzonesz` reports the zone size from the queue limits
- [`blkid`](./blkid.md) — identify zoned filesystems (zonefs, btrfs zoned) on the device
- [util-linux overview](./overview.md) — the rest of the block-device toolset

## Interview Questions

### Q: What is a zoned block device and why does it exist?

The address space is partitioned into zones; sequential-write-required
zones must be written from their write pointer onward and rewritten only
after a reset. The model comes from shingled magnetic recording (tracks
overlap, so a write disturbs neighbors) and carries over to NVMe ZNS,
where it removes write-amplification and mapping-table costs. It trades
random-write freedom for predictable performance and much cheaper media.

### Q: How is blkzone reset related to blkdiscard?

Both invalidate content and make space reusable, but through different
mechanisms with different granularity: discard unmaps arbitrary
byte-aligned ranges and is a hint, while reset returns whole zones to the
Empty state, moves the write pointer to the zone start, and is the
*defined* way to reclaim space on a zoned device. On an SMR drive, a
discard of a partial zone may accomplish nothing, while reset always does.

### Q: A write to a zoned device fails with "write pointer" errors — what does that mean and how do you inspect it?

SWR zones only accept writes starting exactly at the write pointer; a
write to an already-written offset or an unaligned position fails. `blkzone
report` shows `wptr` per zone; the fix is to write sequentially from wptr,
`reset` the zone to restart it, or use a zoned-aware filesystem that
manages pointers for you (btrfs/f2fs zoned modes, xfs, or zonefs).

### Q: What is the difference between zone len and cap, and why should an admin care?

`len` is the zone size (addressable span), `cap` is how many of those
sectors actually store data — on some ZNS devices the tail of the zone is
padding with no capacity. Capacity planning and filesystem sizing must use
`cap` (or `blkzone capacity`), or the volume will appear larger than the
media can actually hold.

### Q: How would you experiment with zoned tooling without special hardware?

Load the `null_blk` module with zoned support (`modprobe null_blk zb=1
zone_size=... `) to get `/dev/nullb0`, a RAM-backed host-managed zoned
device, then use `blkzone report/reset` against it. This is also how the
kernel's zoned code is tested; it gives full zone state machines with no
hardware risk.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/blkzone.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
