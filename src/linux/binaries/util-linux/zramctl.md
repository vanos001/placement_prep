# zramctl — set up, control, and inspect zram devices

## Overview

`zramctl` is the management CLI for **zram** — kernel block devices (`/dev/zram0`, `/dev/zram1`, ...) that perform RAM-backed storage with transparent compression: everything written to a zram disk is compressed in memory, typically reaching 2-4x density, at the cost of CPU cycles. The tool queries current zram state, initializes a device (size, algorithm, stream count), finds a free device node, and resets devices back to zero-size. It ships in the Debian `util-linux` package at `/usr/sbin/zramctl`.

You reach for it when provisioning a compressed swap (`zramctl` + `mkswap` + `swapon`) on low-RAM boxes and laptops, building fast RAMdisks (`zramctl` + `mkfs` + `mount`) for `/tmp` or build caches, or answering "is our zram swap actually compressing?" by reading the DATA/COMPR columns. It is often confused with `lsblk` (lists *all* block devices including zram, but cannot configure them), `ramdisk`-style tmpfs (tmpfs compresses nothing; zram does), and the sysfs knobs under `/sys/block/zramN/` that zramctl drives for you.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/zramctl |
| First appeared | early-2010s util-linux; zram itself mainlined in kernel 3.14 after years in staging |
| Standards | none; Linux zram sysfs ABI |

## Synopsis

```
zramctl [options] <device>                 # query/status one device
zramctl [options] -f                       # find and reserve a free device
zramctl [options] -f | <device> -s <size>  # initialize size/algorithm/streams
zramctl -r <device>...                     # reset device(s)
```

Main one-line forms:

```
zramctl                        # show all active (nonzero-size) zram devices
zramctl -f -s 2G -a zstd       # take a free device, 2 GiB, zstd compression
zramctl /dev/zram0             # status of one device
zramctl -r /dev/zram0          # reset it back to zero-size
```

## How It Works

### Choosing an algorithm

The `-a` choice is a CPU-for-RAM trade; the kernel exposes the supported set per device:

```
algorithm   speed        ratio        when to pick
----------  -----------  -----------  ---------------------------------
lzo         fast         modest       default-ish, low-CPU boxes
lz4         fastest      modest       build caches, /tmp scratch
lz4hc       medium       better       latency-tolerant, hotter ratio
deflate     slow         good         archival-ish scratch (rare)
842         hardware     modest       platforms with hw assist (s390x)
zstd        medium       best         the modern default for swap
```

The ground truth for a given kernel is `/sys/block/zram0/comp_algorithm` — the active algorithm is shown in brackets, and that file is also where availability is checked before zramctl errors out. Newer kernels add tunable parameters (`-p`) such as zstd level.

### Limits and writeback

Beyond plain compression, recent kernels expose knobs zramctl surfaces as columns:

- **`mem_limit`** (`MEM-LIMIT`): cap the real RAM a device may consume; writes beyond it fail or trigger writeback, turning zram into a bounded cache rather than an unbounded consumer.
- **`mem_used_max`** (`MEM-USED`): a peak watermark you can reset — the number capacity planners actually want, since TOTAL oscillates.
- **Writeback** (idle page export to a backing block device) exists in the kernel and in `zram-generator` configs but has no zramctl flag — automation for it lives in the generator/systemd layer.

### The lifecycle of a zram device

A freshly available `/dev/zramN` exists but has **zero size** — invisible to `zramctl`'s default listing and unusable until initialized. The kernel-adjacent dance:

```
modprobe zram num_devices=4        # (or built-in) create /dev/zram[0..3]
zramctl -f -s 2G -a zstd           # pick free node; write disksize + algorithm
mkswap /dev/zram0 && swapon -p 100 /dev/zram0
    ... or ...
mkfs.ext4 /dev/zram0 && mount /dev/zram0 /tmp
zramctl                            # observe DATA vs COMPR, ratio
swapoff /dev/zram0 && zramctl -r /dev/zram0   # drain and reset
```

Order matters and is the classic exam question: **size and algorithm can only be set on a zero-size device**; to change them you must reset first. Disksize is written *before* any other configuration sticks.

### Boot-time provisioning patterns

```
manual            /etc/rc or unit script: zramctl -f -s .. + mkswap + swapon
zram-generator   /etc/systemd/zram-generator.conf -> systemd-zram-setup@
initramfs tools   some distros ship mkinitcpio/dracut zram hooks
```

Pick one owner. The generator path is declarative (`zram-size = ram / 2`, `compression-algorithm = zstd`) and survives updates; hand-rolled scripts must handle node-existence, ordering, and conflicts with the generator (double-provisioning the same devices fails at boot). Diagnosing "our swap grew overnight" usually starts by finding which of these paths provisioned it.

### What the numbers mean

`zramctl` reads the sysfs statistics and renders:

```
NAME       ALGORITHM DISKSIZE  DATA   COMPR  TOTAL STREAMS MOUNTPOINT
/dev/zram0 zstd           2G  624.5M 173.9M 179.8M       2 [SWAP]
```

- **DISKSIZE** — the *limit on uncompressed* data: the device's apparent capacity, not a RAM reservation. Nothing is allocated until data is written.
- **DATA** — uncompressed size of stored data; **COMPR** — its compressed footprint; **TOTAL** — all memory including allocator overhead/fragmentation (the honest RAM cost).
- **ZERO-PAGES** — full zero pages stored for free; **MEM-LIMIT / MEM-USED** — optional memory cap and peak (`mem_limit`/`mem_used_max` knobs); **COMP-RATIO** — DATA/TOTAL.
- **STREAMS** — per-device concurrent compression workqueues (defaults to CPU count; `tune -t` can lower it for power saving).

Setting `-s 2G` reserves *nothing*; it declares how much uncompressed data the device may hold. This is why zram swap sizing is heuristic — the real memory cost is DISKSIZE divided by the achieved ratio, discovered live in the COMPR/TOTAL columns.

### sysfs mapping

Every column has a file behind it (`/sys/block/zram0/disksize`, `comp_algorithm`, `mem_limit`, `mm_stat`...), and zramctl is essentially a formatter over them — which matters for automation (`echo 2G > disksize` needs the byte value; zramctl does the unit math) and for understanding error messages that bubble up from sysfs writes.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-f, --find` | Pick the first free (zero-size) zram device; with `-s`, initialize it in one step. |
| `-s, --size <size>` | Set the disksize (accepts KiB/MiB/GiB suffixes). Zero-size only. |
| `-a, --algorithm <alg>` | Select compression (lzo, lz4, lz4hc, deflate, 842, zstd — kernel-dependent). |
| `-p, --algorithm-params` | Algorithm-specific parameters (level etc., newer kernels). |
| `-t, --streams <number>` | Set the number of compression streams. Zero-size only. |
| `-r, --reset` | Reset the given device(s) to zero-size (must be unmounted/swapoff first). |
| `-b, --bytes` | Print sizes in raw bytes (stable output for scripts). |
| `-o, --output <list>` | Choose columns: NAME, DISKSIZE, DATA, COMPR, ALGORITHM, STREAMS, ZERO-PAGES, TOTAL, MEM-LIMIT, MEM-USED, MIGRATED, COMP-RATIO, MOUNTPOINT. |
| `-n, --noheadings` / `--raw` | Headerless / raw column output. |

## Usage Patterns

```bash
# See what zram devices are active right now
zramctl
```

```bash
# Create 2G of zram swap with zstd (then format+enable)
dev=$(zramctl -f -s 2G -a zstd | awk '{print $1}')
mkswap "$dev" && swapon -p 100 "$dev"
```

```bash
# Fast RAMdisk for a build directory
zramctl -f -s 8G -a lz4
mkfs.ext4 /dev/zram1 && mount /dev/zram1 /tmp/build
```

```bash
# Is compression earning its keep?
zramctl -o NAME,DATA,COMPR,COMP-RATIO,TOTAL /dev/zram0
```

```bash
# Raw byte figures for a monitoring script
zramctl -b -n -o NAME,DATA,COMPR,TOTAL
```

```bash
# Reset a device after tearing down its consumer
swapoff /dev/zram0 && zramctl -r /dev/zram0
```

```bash
# Lower streams on a battery-powered box
zramctl /dev/zram0 -t 1
```

```bash
# List every column, including limits and migration stats
zramctl --output-all
```

```bash
# Check algorithm support offered by the kernel
cat /sys/block/zram0/comp_algorithm
```

```bash
# Provision inside a container/VM boot script (idempotent-ish)
[ -z "$(zramctl -f 2>/dev/null)" ] || zramctl -f -s 1G -a lz4
```

```bash
# Compare algorithms empirically on your data (reset between tries)
zramctl -f -s 2G -a lz4 >/dev/null; fill /dev/zram2; zramctl /dev/zram2 -b -o DATA,COMPR,TOTAL
```

```bash
# Set a hard RAM budget for the swap device (kernel >= 5.6-ish)
echo 1G > /sys/block/zram0/mem_limit && zramctl -o NAME,MEM-LIMIT,TOTAL /dev/zram0
```

```bash
# Inventory all zram devices for a fleet report
zramctl --output-all -b -n | tee /tmp/zram-report.txt
```

```bash
# Clean teardown in a CI job's post-step
swapoff -a 2>/dev/null; for z in $(lsblk -rn -o NAME,TYPE | awk '$2=="zram"{print "/dev/"$1}'); do zramctl -r "$z" 2>/dev/null; done
```

## Nuances and Gotchas

- **Nodes may not exist after boot.** The man page is explicit: zram device nodes are commonly *not* created at boot; only `--find` will materialize a new `/dev/zramN`. A script that hardcodes `/dev/zram3` breaks when fewer devices exist — always use `-f`.
- **Cannot resize or re-algorithm a used device.** Size/streams/algorithm writes only work at zero size; you will get EBUSY/EBUSY-ish sysfs errors otherwise. Reset (after swapoff/umount) is the only path back.
- **DISKSIZE is not a memory reservation.** Setting 16G of zram swap on a 4G box is allowed and can be legitimate — but a bad compression workload (incompressible data: video, already-compressed archives) makes TOTAL balloon toward the real RAM, and the swap becomes the OOM itself.
- **Algorithm availability is kernel-dependent.** The list in `--help` is explicitly marked "may be inaccurate"; the truth is in `/sys/block/zram0/comp_algorithm` (also shows the *active* algorithm in brackets). zstd gives best ratio, lz4 best speed — the choice is a CPU-for-RAM trade.
- **Reset order.** `zramctl -r` on a mounted/swap-enabled device fails; and after swapoff, data still held by a mounted FS dies with the reset — zram storage is volatile by definition (gone on reset *and* on reboot).
- **`-b` for scripts.** Human-readable units (2G, 624.5M) round and change with sizes; machine consumers must use `-b` or fixed `-o` columns.
- **systemd/zram-generator.** Modern distros often provision zram via `zram-generator` reading `/etc/systemd/zram-generator.conf`; manual `zramctl` setups and generator setups can conflict on boot — pick one owner.
- **No fsync durability.** zram is RAM: power loss = content loss. Never put anything on it that must survive; it is swap scratch or cache space.
- **Streams default to CPUs.** On big machines the per-device stream count defaults to CPU count, multiplying memory overhead per stream; capping `-t` is a common fix for embedded and battery targets.
- **Idle pages don't leave.** zram holds cold pages forever unless writeback/`idle` machinery is configured; "swap" here has no hierarchy fallback by default. Watching MIGRATED (compaction) and COMP-RATIO over time is how you notice a stale-heavy workload.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Query/setup/reset succeeded. |
| nonzero | Failure: no free device, node missing, sysfs write rejected (busy/unsupported algorithm/insufficient rights), or usage error. |

## Related Commands

- [`lsblk`](./lsblk.md) — lists all block devices including zram nodes; the discovery complement.
- [`mkswap`](./mkswap.md) — formats a zram device as swap, the most common zram consumer.
- [`blkdiscard`](./blkdiscard.md) — the SSD-side analog of "give the space back" for block devices.
- [`mount`](./mount.md) — mounts zram devices formatted with a filesystem (RAMdisk pattern).
- [`./overview.md`](./overview.md) — util-linux collection hub.

## Interview Questions

### Q: What is zram and when is compressed swap preferable to disk swap?

zram is a RAM-backed block device that compresses pages in memory, trading CPU for capacity (typically 2-4x). It wins when disk swap is absent (many cloud VMs, embedded boards), slow (SD cards), or when latency-sensitive pages should never hit a spinning/plastic medium; the cost is CPU cycles and the risk that incompressible data consumes RAM. Low-RAM systems, laptops, and Android-style devices are the canonical deployments.

### Q: Explain the difference between DISKSIZE, DATA, COMPR, and TOTAL in zramctl output.

DISKSIZE is the configured cap on *uncompressed* data (a logical size, nothing allocated up front). DATA is how much uncompressed data is currently stored; COMPR is its compressed footprint; TOTAL adds allocator overhead and fragmentation — the real RAM cost. COMP-RATIO (DATA/TOTAL) tells you whether the setup is paying off, and it is the number to alert on, not DISKSIZE.

### Q: You want to change a zram device's algorithm from lzo to zstd. Why does it fail, and what is the procedure?

Size-related attributes (disksize, streams, algorithm) are only writable while the device has zero size. Procedure: drain consumers (`swapoff` or umount), `zramctl -r /dev/zramN` to reset, then reinitialize with `zramctl -f -s <size> -a zstd` and re-format. Note all stored data is destroyed — zram has no persistence anyway.

### Q: Why might `zramctl -s 16G` on a 4 GB machine be reasonable — and what is the risk?

Because DISKSIZE merely caps uncompressed capacity; actual allocation follows compressed demand. If your workload compresses 3:1, 16G of swap costs ~5.3G TOTAL — feasible. The risk is incompressible pages (media, already-zippped data): TOTAL then approaches 16G and zram itself becomes the memory hog, aggravating the OOM situation it was meant to relieve. Monitor COMP-RATIO and set MEM-LIMIT if supported.

### Q: A script hardcodes `/dev/zram2` and fails on some systems. What is the robust pattern?

Device nodes depend on `zram num_devices=` and may not even exist until materialized. Use `zramctl -f` to find (and on demand, create) a free node, capture its name from the output, and only then pass `-s/-a/-t` against that node — or combine everything into one call: `zramctl -f -s 2G -a zstd`. Never assume node numbering.

### Q: How does zram relate to tmpfs as a fast scratch store?

tmpfs stores pages uncompressed in RAM/page-cache and can spill to disk swap; zram is a block device whose pages are compressed in place — denser, at CPU cost, and it *is* the storage (so it needs a filesystem or swap on top). For /tmp with high redundancy (text, builds), zram often holds 3x more data in the same RAM; for data already compressed, zram wastes CPU and tmpfs behaves identically. On modern systems zram swap also accelerates tmpfs spill-through, which blurs the comparison in practice.

### Q: A fleet laptop reports swap usage at 90% of a 4G zram device but memory pressure is low. Is that a problem?

Probably not — with good compression the *real* RAM cost is the COMPR/TOTAL figure (perhaps ~1.2G), and Linux intentionally fills compressed swap before evicting page cache. The alarm-worthy signals are the inverse: TOTAL climbing toward DISKSIZE (poor ratio, incompressible pages), COMP-RATIO dropping over time (stale, unreclaimable pages), or mem_limit rejections. The lesson interviewers want: on zram, swap-percent is the least meaningful metric; read the compression columns.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/zramctl.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
