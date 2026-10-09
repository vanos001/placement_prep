# lsmem — list ranges of available memory with online status

## Overview

`lsmem` lists the system's physical memory blocks — the kernel memory-hotplug granularity — grouped into contiguous ranges, showing each range's size, online/offline state, removability, NUMA node, and overlapping zones. It is the read-side of Linux memory hotplug: add or remove memory (in VMs and on hot-pluggable servers) and `lsmem` shows the effect, while sibling `chmem` performs the online/offline changes.

It ships in the `util-linux` package at `/usr/bin/lsmem`. The tool originated in s390 memory-hotplug tooling before being absorbed into util-linux in the mid-2010s. It is often confused with `free` (RAM *usage*, not layout), with `lscpu` (CPU topology), and with `chmem` (which changes what lsmem displays).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/lsmem |
| First appeared | s390 tooling, merged into util-linux mid-2010s |
| Standards | None — Linux sysfs memory-hotplug specific |

## Synopsis

```
lsmem [options]
```

Common one-line forms:

```
lsmem                        # grouped ranges + summary
lsmem -a                     # every individual memory block
lsmem --summary=only         # just the totals
lsmem -J                     # JSON output
```

## How It Works

### Memory blocks and how they group

The kernel exposes hotplug state as fixed-size blocks under `/sys/devices/system/memory/memoryN`, one directory per block, with the block size in `block_size_bytes` (commonly 128 MiB on x86_64, but it is a kernel/platform property, not tunable at runtime). `lsmem` reads those block states and merges runs of adjacent blocks that share the same attributes into `RANGE` rows:

```
/sys/devices/system/memory/
  block_size_bytes ──▶ 0x8000000 (128M)
  memory0  online ┐
  memory1  online ├─ merge contiguous, same-state ─▶ RANGE row
  memory2  online ┘
  ...
```

A real run on a small VM — note the address hole, so total memory appears as two ranges:

```
$ lsmem
RANGE                                  SIZE  STATE REMOVABLE BLOCK
0x0000000000000000-0x0000000017ffffff  384M online       yes   0-2
0x0000000100000000-0x00000001ffffffff    4G online       yes 32-63

Memory block size:                128M
Total online memory:              4.4G
Total offline memory:               0B
```

The gap between `0x18000000` and `0x100000000` is the classic x86 MMIO hole — `lsmem` shows physical layout, not just a capacity number.

### What the columns mean

- `RANGE` — start–end physical addresses of the merged run.
- `STATE` — `online` (usable by the kernel) or `offline` (present but not managed).
- `REMOVABLE` — whether the block can be offlined (no unmovable kernel allocations pinned inside); critical for memory hot-remove and ballooning.
- `BLOCK` — the block numbers covered (`0-2`, `32-63`).
- `NODE` — NUMA node; `ZONES` (visible via `-o`/`--output-all`) names the overlapping zone types (`DMA`, `DMA32`, `Normal`, `Movable`).

### Grouping is the point

The default merge hides noise on machines with hundreds of blocks. `-a` disables merging and lists each block — needed when scripting exact offline operations. `-S, --split <columns>` changes the merge key (e.g. group only by `STATE`), and `--summary` controls the footer (`never`, `always`, `only`). Output formats follow the util-linux family: `-J` JSON, `-P` key="value" pairs, `-r` raw, `-n` no headings, `-b` byte sizes.

### lsmem vs chmem

`lsmem` never changes state. `chmem` is the setter: `chmem =online` / `=offline` for ranges, or sized requests. The two are designed as a pair — list with `lsmem`, act with `chmem`, verify with `lsmem`.

### A complete hot-add cycle

The tools earn their keep in VMs, where memory is added while the guest runs:

```
hypervisor: attach 8G to the running VM
   guest: lsmem -a            # new blocks appear, STATE offline
   guest: chmem =online 0x0000000200000000-0x00000003ffffffff
   guest: lsmem               # range now online; free reflects the new GiB
```

The reverse (hot-remove) is harder and depends on `REMOVABLE`: the kernel must migrate or drop every page in the block before it can offline it. Unmovable pins (page tables, dma-buf, drivers that ignore migration) are why a "removable-looking" block refuses to go offline — the operation fails per block and `lsmem` afterwards shows which range survived.

### Zones and why they appear in the columns

Physical memory participates in kernel zones: `DMA`/`DMA32` (legacy low-address devices), `Normal`, and `Movable` (pages the kernel promises to migrate for compaction/hot-remove). A range can straddle zones, which is why `ZONES` is a list, not a value. Hot-remove planning prefers blocks that can be placed in `Movable` — some platforms only allow *movable* onlining (`online_movable` state in sysfs), pinning all hot-added memory to movable pages so it can later leave again. This is the deep reason `REMOVABLE` is a first-class column rather than an afterthought.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-a, --all` | List each individual memory block (no range merging) |
| `-S, --split <list>` | Split ranges by the given columns instead of defaults |
| `-s, --sysroot <dir>` | Operate on an alternate system root (image analysis) |
| `-b, --bytes` | Print sizes in bytes, not human-readable |
| `-n, --noheadings` | Omit header row |
| `-o, --output <list>` | Column selection (adds ZONES, NODE etc.) |
| `--output-all` | All available columns |
| `-J, --json` | JSON output |
| `-P, --pairs` | key="value" output format |
| `-r, --raw` | Raw unpadded output |
| `--summary[=<when>]` | Summary footer: `never`, `always` or `only` |
| `-H, --list-columns` | Print available column names |

## Usage Patterns

```bash
# How much memory, where, and is any of it offline?
lsmem
```

```bash
# Totals only — quick capacity check in scripts
lsmem --summary=only
```

```bash
# Enumerate every block (e.g. to plan a chmem operation)
lsmem -a | head -20
```

```bash
# Machine-readable snapshot
lsmem -J > mem-layout.json
```

```bash
# Which blocks are removable? (hot-remove / ballooning feasibility)
lsmem -a -o BLOCK,STATE,REMOVABLE | grep -v online
```

```bash
# Sizes in exact bytes for arithmetic
lsmem -b --summary=only
```

```bash
# Inspect an OS image's memory layout from a mounted sysfs copy
lsmem -s /mnt/imgroot
```

```bash
# After hot-adding memory in the hypervisor, verify the kernel sees it
lsmem --summary=only
```

```bash
# Raw parseable columns for a monitoring agent
lsmem -n -r -o RANGE,SIZE,STATE
```

```bash
# Group ranges purely by state to spot offline holes quickly
lsmem -S STATE
```

```bash
# Read the granularity straight from the kernel
lsmem --summary=only; cat /sys/devices/system/memory/block_size_bytes
```

```bash
# Track a hot-add event: capture layout before and after the hypervisor action
lsmem -J > before.json; sleep 60; lsmem -J > after.json; diff before.json after.json
```

```bash
# Capacity report line for an inventory script
lsmem --summary=only | awk '/Total online/ {print $4}'
```

```bash
# Bytes-exact totals for capacity math (no display rounding)
lsmem -b --summary=only
```

```bash
# JSON with every column for a datacenter inventory agent
lsmem -J --output-all
```

## Nuances and Gotchas

- **Memory block size is platform-fixed.** 128 MiB is common on x86_64 but not guaranteed; firmware, kernel config, and `memory_hotplug` settings decide it. Scripts must read `block_size_bytes` (or `lsmem`'s footer) instead of assuming.
- **`REMOVABLE` is advisory.** It reflects current pinning (unmovable pages, page tables). A block marked removable can still fail to offline moments later if allocations change; the authoritative test is attempting the `chmem`/sysfs offline.
- **Desktops and small VMs may have no hotplug sysfs.** If the kernel lacks memory-hotplug support, `/sys/devices/system/memory` is absent and `lsmem` fails — that is a platform property, not a broken install.
- **Offline ≠ absent.** Offline blocks still occupy physical slots (and power domains on real hardware); `Total offline memory` is kernel-invisible memory, not "free".
- **`-a` output scales.** A terabyte-class host at 128 MiB blocks has thousands of rows; use `-o`/`-r`/`--summary` rather than eyeballing.
- **State changes belong to chmem/sysfs, not lsmem.** Interviewers probe exactly this boundary: `lsmem` is pure observation; `echo online > /sys/devices/system/memory/memoryN/state` or `chmem` do the work.
- **Human sizes round.** `4.4G` is display rounding; use `-b` when the number feeds arithmetic.
- **Ranges can straddle NUMA nodes and zones.** The default merge only groups blocks that agree on *all* default keys; if a range looks odd, check `-S` grouping or list blocks with `-a` before concluding the hardware is lying.
- **Guest vs host view differs.** Inside a VM, `lsmem` shows the guest's physical map — hot-plugged host memory only appears after the guest's kernel notices (ACPI notify). Debugging "memory missing" means checking both sides.
- **Some states have more than online/offline.** sysfs accepts `online_movable` (and on some platforms `online_kernel`) — two ways to be online with different migration guarantees. lsmem's STATE column may reflect them; scripts matching strictly `online|offline` will be surprised.

## Exit Status

- `0` — success.
- `1` — failure: memory-hotplug sysfs unavailable, unreadable, or invalid options/columns.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`chmem`](./chmem.md) — the setter: online/offline the ranges lsmem displays.
- [`internals`](../../internals.md) — physical memory layout, zones and NUMA context.

## Interview Questions

### Q: What does lsmem show that free does not?

`free` reports usage of memory the kernel currently manages. `lsmem` reports physical layout: address ranges, block granularity, online/offline state, removability, NUMA node. A VM can show 4.4G in `free` while `lsmem` reveals the address hole, block size, and which blocks could be hot-removed — orthogonal information needed for hotplug and capacity work.

### Q: What is the difference between memory marked offline and memory that was never present?

Offline blocks exist in the physical map (a DIMM/slot is there) but the kernel declines to manage them; never-present ranges simply do not appear as blocks. `lsmem -a` shows offline blocks and the footer's `Total offline memory` quantifies them. The distinction matters in ballooning and failure analysis: offline-but-present memory can usually be onlined; absent memory cannot — no sysfs block exists to online.

### Q: Why does lsmem merge blocks into ranges, and how do you stop it?

Adjacent blocks sharing state/node/removability are merged so operators read dozens of GiB as one line instead of hundreds of block rows. `-a` lists every block; `-S` changes the grouping key. The merge is presentation-only — the underlying sysfs blocks are unchanged.

### Q: You hot-add 8 GiB to a VM, but free still shows the old size. Where does lsmem fit?

Hot-added DIMMs/ballooned memory typically come up offline. `lsmem` will show the new blocks as offline (visible with `-a`), after which `chmem =online` (or per-block sysfs writes) brings them online; then `free` reflects the new capacity. lsmem is the verification step between hypervisor action and kernel availability.

### Q: What does the REMOVABLE column actually promise?

Only that, right now, the block looks unpinned by unmovable allocations — a precondition for offline. It is a snapshot heuristic, not a guarantee: offline attempts can fail later. Real hot-remove planning treats REMOVABLE as a filter, then tries the offline and handles failure.

### Q: Where does the 128M memory block size come from, and can you change it?

It is exported by the kernel (`/sys/devices/system/memory/block_size_bytes`) and derives from platform/kernel configuration — it is not a runtime tunable. It sets the hotplug granularity: you online/offline in whole blocks, so oversized blocks waste granular control and tiny blocks cost sysfs overhead. lsmem's footer surfaces it so scripts can compute block counts.

### Q: Why would a platform only allow onlining hot-added memory as movable?

Because hot-remove must be possible later: movable pages can be migrated elsewhere by compaction, letting the block drain and go offline. `online_movable` therefore pins all hot-added pages to the movable zone — the standard pattern for balloon-style memory management in virtualized fleets, at the cost of reducing the kernel's non-movable allocation space. lsmem's REMOVABLE/ZONES columns are how you audit that policy took effect.

### Q: A chmem offline operation fails on one block of a large range. What does lsmem show afterwards and what do you do?

The range splits: blocks that drained are offline, the blocked one stays online — visible as a new RANGE boundary in lsmem (or with `-a`, the individual culprit block). The usual cause is an unmovable pin (page tables, driver allocations, dma buffers). Mitigations: retry after memory pressure/compaction, migrate workloads, or accept partial removal and update the balloon plan. The failure is per-block by design; nothing is corrupted.

### Q: How does lsmem behave in a container?

It reads sysfs, which containers see mostly read-through, so the output matches the host's physical layout. That makes it a useful "am I on a hotplug-enabled VM?" probe, but state changes are not namespaced — attempting them from inside an unprivileged container fails at sysfs write permission. The interview point: procfs/sysfs observability inside containers is broad; mutability is what the boundary controls.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/lsmem.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
