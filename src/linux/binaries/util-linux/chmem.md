# chmem — set memory online or offline

## Overview

`chmem` drives Linux memory hotplug: it brings a given size or physical
address range of memory online (usable by the kernel) or offline (removed
from use), translating friendly operands into writes under
`/sys/devices/system/memory/`. It ships in the `util-linux` package at
`/usr/sbin/chmem` and pairs with `lsmem`, which displays the same memory
blocks and their state.

You reach for it in virtualization (ballooning memory into and out of a
guest), on big iron with ACPI hot-pluggable memory slots, and when tuning
which memory zone newly added RAM lands in — `-z Movable` is the standard
way to make hot-added memory removable again later. It is often confused
with `madvise`-style per-process memory hints (unrelated), with `swapon`
(disk-backed memory, different layer), and with `numactl` (NUMA policy for
allocations, not presence).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/chmem |
| First appeared | util-linux 2.25 (2014) |
| Standards | Linux sysfs memory-hotplug interface |

## Synopsis

```
chmem [options] [SIZE|RANGE|BLOCKRANGE]
```

Main one-line forms:

```
chmem -e 1G                 # bring 1 GiB online
chmem -e -z Movable 2G      # online 2 GiB, zone: Movable (removable later)
chmem -d 0x100000000-0x17fffffff   # offline one address range
chmem -b -d 8-16            # offline memory blocks 8 through 16
```

- `SIZE` — a quantity like `1G`, rounded to block granularity.
- `RANGE` — physical addresses, hex or decimal, `start-end`.
- `BLOCKRANGE` — block numbers as shown by `lsmem` (needs `-b`).

## How It Works

### The sysfs machinery

The kernel carves hot-pluggable memory into blocks of
`block_size_bytes` (commonly 128 MiB on x86_64, 256 MiB on ppc64):

```
$ cat /sys/devices/system/memory/block_size_bytes
8000000                          # 0x8000000 = 128 MiB
$ lsmem
RANGE                                 SIZE  STATE REMOVABLE BLOCK
0x0000000000000000-0x000000007fffffff   2G  online       yes     0-15
0x0000000100000000-0x000000017fffffff   2G  offline      -      32-39
...
$ chmem -e 2G
Memory auto-discovered... 2G online
```

For each affected block `chmem` writes to `memoryN/state`:

```
echo online         -> state: online            (zone: kernel-chosen)
echo online_movable -> state: online, zone Movable   (-z Movable)
echo online_kernel  -> state: online, kernel zones    (-z Normal/DMA...)
echo offline        -> state: offline                 (-d)
```

`/sys/devices/system/memory/probe` is the inverse hook: writing a
physical address there tells a system without automatic notification
("probe" interfaces, s390 standby memory) that the range exists and
should be added — chmem's enable path covers this automatically when
needed.

### Zones and why -z matters

```
DMA / DMA32 / Normal   kernel memory: page tables, slab, kernel text data
Highmem                32-bit legacy high memory
Movable                pages the kernel will migrate on request
Device                 ZONE_DEVICE (pmem/DAX special-purpose memory)
```

Memory onlined as `Movable` contains only migratable pages (page cache,
anonymous pages under migration), so the kernel can empty it later —
the prerequisite for hot-removing memory from a running guest or host.
Memory onlined as `Normal` is cheaper for the kernel to use but may
become unmovable (pinned page tables, slab), making later offline fail.
`chmem -e -z Movable` is therefore the default recommendation for
dynamically added memory, and `lsmem`'s REMOVABLE column reflects it.

### Enable vs disable flows

```
enable:  chmem -e 2G
            for each needed block:
              absent? -> write address to /sys/.../probe (if supported)
              write online[_movable|_kernel] to memoryN/state
              kernel: add zones, build page tables, udev fires add event

disable: chmem -d 0x100000000-0x1ffffffff
            kernel: try to migrate/evict pages out of the blocks
            all free? -> blocks go offline; else partial failure
```

Offline is the only slow, best-effort direction: it can fail on
unmovable pages (long-lived kernel allocations), and the kernel reports
which blocks refused.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-e, --enable` | Online the memory (default zone unless `-z`) |
| `-d, --disable` | Offline the memory |
| `-z, --zone <name>` | Zone for enable: DMA, DMA32, Normal, Highmem, Movable, Device |
| `-b, --blocks` | Interpret the operand as block numbers (lsmem numbering) |
| `-v, --verbose` | Print per-block details |
| (operand) | `SIZE` (`1G`), `RANGE` (`0x1000-0x2000`), or `BLOCKRANGE` (`8-16`) |

## Usage Patterns

```bash
# Add 4 GiB to a running guest whose hypervisor just ballooned it in
chmem -e 4G
```

```bash
# Hot-add memory that must be removable later (the standard choice)
chmem -e -z Movable 2G
```

```bash
# What does the memory map look like before/after?
lsmem
```

```bash
# Remove one specific range (the VM needs less memory now)
chmem -d 0x180000000-0x1bfffffff
```

```bash
# Operate by block numbers exactly as lsmem lists them
chmem -b -d 32-39
```

```bash
# Force new memory into the Normal zone for kernel-heavy workloads
chmem -e -z Normal 1G
```

```bash
# Verify removability of what you just added
lsmem | awk '$0 ~ /online/ {print}'
```

```bash
# Verbose run to see per-block decisions
chmem -v -e -z Movable 1G
```

```bash
# Free-memory guard before shrinking a guest
free -g && chmem -d 0x1c0000000-0x1ffffffff
```

```bash
# Check the block size your arithmetic must respect
cat /sys/devices/system/memory/block_size_bytes
```

## Nuances and Gotchas

- **Sizes round up to block granularity.** On a 128 MiB-granularity
  system, `chmem -e 50M` still touches one block (128 MiB). All operand
  math must use `block_size_bytes`; "half a block" does not exist.
- **Offline fails on unmovable memory.** Page tables, pinned pages, and
  slab objects in a block prevent offlining it. This is why hot-added
  memory should be `-z Movable` — you choose removability at enable time,
  not at remove time.
- **Not all memory is hotpluggable.** The firmware/ACPI tables (or the
  hypervisor) define which ranges may appear or disappear;
  `lsmem`'s REMOVABLE column and `/sys/devices/system/memory/.../valid_zones`
  are the ground truth. chmem cannot conjure slots that don't exist.
- **Requires root** — the sysfs files are root-writable; in containers
  the operation fails with permission errors (and usually isn't wanted).
- **Boot-memory vs hotplug-memory asymmetry.** Memory present at boot
  often lives in kernel zones and is not removable; only the ranges the
  platform marked hotpluggable behave as the docs promise.
- **Zone choice is constrained.** `valid_zones` per block limits what
  `-z` can request; asking for Movable on a block that cannot support it
  fails. On 32-bit/iommu-odd systems the DMA zones may not accept new
  blocks at all.
- **Device-memory (pmem/DAX).** `-z Device` targets ZONE_DEVICE setups;
  mixing pmem ranges into normal RAM math is a classic mistake.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All requested memory operations succeeded |
| 1 | Usage error, bad range/block, or the kernel refused (offline failed, zone invalid, no hotplug support) |

## Related Commands

- [`chcpu`](./chcpu.md) — the CPU-side twin of this sysfs hotplug wrapper
- [`choom`](./choom.md) — another small /proc-facing util-linux tool
- [util-linux overview](./overview.md) — the rest of the system-configuration toolset

## Interview Questions

### Q: What does it mean to online memory, and what does chmem actually write?

Onlining makes a physical memory range part of the running kernel's page
allocator: chmem writes `online` (optionally `online_movable`) to each
affected `/sys/devices/system/memory/memoryN/state`, and the kernel
constructs the memmap, adds pages to zones, and notifies udev. The
inverse, `offline`, migrates pages away and removes the range from the
allocator.

### Q: Why does chmem have a -z Movable option, and what breaks without it?

Movable-zone memory contains only pages the kernel can migrate, which is
the prerequisite for later hot-removal. Memory onlined into Normal may
accumulate unmovable kernel allocations (page tables, slab), after which
offline attempts fail and the guest/host is stuck with the memory. You
choose removability at enable time; that choice is effectively permanent
for those blocks.

### Q: A script does chmem -d on 1 GiB but only half a GiB goes offline. Why?

Offline is best-effort per block: blocks containing unmovable or pinned
pages refuse, the rest succeed, and chmem reports partial progress. The
usual culprits are kernel allocations in Normal-zone blocks. The fixes
are to offline Movable-zoned blocks only, retry after activity drains
page cache, or accept that boot-time memory in kernel zones rarely
releases.

### Q: How does lsmem relate to chmem?

They are the read and write halves of one sysfs view: `lsmem` lists
ranges with SIZE, STATE, REMOVABLE, and block numbers; `chmem -b` accepts
exactly those block numbers as operands, and chmem's output mirrors
lsmem's range representation. Any script should read lsmem (plus
block_size_bytes) before computing chmem operands.

### Q: Where does memory hotplug actually get used in production?

Two big cases: virtualization (memory ballooning with virtio-mem or
ACPI-based hotplug, resizing guests without rebooting) and large NUMA
servers with hot-pluggable memory drawers (ppc64, some x86/ARM
platforms). It is also the mechanism behind standby memory on s390. The
interview follow-up is always zone selection and the offline-failure
mode above.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/chmem.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
