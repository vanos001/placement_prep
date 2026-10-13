# swapon — enable devices and files for paging and swapping

## Overview

`swapon` activates a swap area — a partition or file previously prepared
with `mkswap` — telling the kernel to use it for paging. It can activate
one explicit target or everything listed in `/etc/fstab` (`-a`), and its
`--show` mode is the modern way to inspect what is active. It ships with
the `mount` package (Debian bookworm) at `/usr/sbin/swapon` and requires
root for activation.

`swapon` is often confused with `mkswap` (prepares the signature;
activates nothing), with `swapoff` (deactivates — and reads
`/proc/swaps` for `-a` while swapon reads fstab), and with reading
`/proc/swaps` directly (works, but `--show` adds UUID/label columns and
deprecates the old `-s`).

| Field | Value |
| --- | --- |
| Package | mount (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/swapon |
| First appeared / lineage | AT&T/4BSD heritage; Linux swapon/swapoff pair since the earliest kernels |
| Standards | None — kernel `swapon(2)` specific |

## Synopsis

```
swapon [options] [<spec>...]
swapon -a
```

Common one-line forms:

```
swapon /swapfile                     # activate one swapfile
swapon -a                            # activate all fstab swap entries
swapon --show                        # tabular status (NAME TYPE SIZE USED PRIO)
swapon -p 10 /dev/sdb2               # activate with high priority
```

## How It Works

### Validation, then the syscall

For each target `swapon` resolves the spec (device path, swapfile,
`LABEL=`/`UUID=`/`PARTUUID=` reference), checks the swap signature
`mkswap` wrote, and issues `swapon(2)`. The kernel verifies the header
(swap version 1, page-size match), reserves the area, and adds it to
`/proc/swaps`:

```bash
$ cat /proc/swaps
Filename    Type       Size     Used  Priority
/dev/sda2   partition  4194300  0     -2
```

Problems surface with precise messages (both observed on this system):

```bash
$ swapon /dev/null
swapon: /dev/null: insecure permissions 0666, 0600 suggested.
swapon: /dev/null: read swap header failed
$ echo $?
255
```

### Priorities and striping

Multiple active areas are used by priority (`-p`, or `pri=` in fstab):
the kernel fills higher-priority areas first; equal priorities are
striped round-robin, which spreads I/O across devices. Unconfigured
areas share a default low priority. Use this to keep swap on the fast
device preferred while a slower fallback exists.

### Where the targets come from

| Source | Used by | Notes |
| --- | --- | --- |
| explicit spec | `swapon /dev/sda2`, `swapon -L swap1` | immediate, one area |
| `/etc/fstab` | `swapon -a` | honors `sw`, `pri=`, `discard`, `noauto` is respected, `-T` picks another file |
| systemd | `.swap` units generated from fstab | what actually runs at boot on modern systems |

`swapon -a` skips entries marked `noauto` and can be pointed at an
alternate fstab with `-T` — handy in chroots and rescue environments.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-a, --all` | Activate every swap entry from `/etc/fstab`. |
| `-p, --priority <prio>` | Priority of the area(s) activated in this call (higher wins). |
| `-d, --discard[=policy]` | Enable swap discards (TRIM) on SSDs: `once` at swapon-time, `pages` on free, both by default. |
| `-e, --ifexists` | Silently skip targets that do not exist (fstab robustness for optional devices). |
| `-f, --fixpgsz` | Re-initialize the area if its page size does not match the running kernel. |
| `--show[=<cols>]` | Tabular listing; columns: NAME, TYPE, SIZE, USED, PRIO, UUID, LABEL. |
| `--noheadings`, `--raw`, `--bytes` | Formatting switches for `--show` output. |
| `-s, --summary` | Old one-line-per-area summary — deprecated for `--show`. |
| `-T, --fstab <path>` | Use this file instead of `/etc/fstab` for `-a`. |
| `-o, --options <list>` | Apply a comma-separated option list as if from fstab. |
| `-L <label>` / `-U <uuid>` | Shorthand specs (same as `LABEL=`/`UUID=`). |

## Usage Patterns

```bash
# First-time setup of a swapfile (root)
dd if=/dev/zero of=/swapfile bs=1M count=4096 status=none
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
```

```bash
# Activate everything fstab promises (after editing it, or in rescue)
swapon -a
```

```bash
# Inspect active areas with the modern interface
swapon --show
swapon --show=NAME,SIZE,USED,PRIO --noheadings
```

```bash
# Fast device gets high priority, slow fallback stays low
swapon -p 100 /dev/nvme0n1p2
swapon -p 10  /dev/sdb2
```

```bash
# Enable TRIM for swap on an SSD (or fstab: options "discard")
swapon -d /dev/sda2
```

```bash
# fstab with optional swap that may be absent (e.g. removable/cloud)
# /swapfile none swap sw,ifexists 0 0
swapon -e -a
```

```bash
# Test a candidate fstab in a chroot without touching the real one
swapon -T /mnt/newroot/etc/fstab -a
```

```bash
# Kernel reports a page-size mismatch after migrating an image cross-arch
swapon -f /dev/sdb2
```

```bash
# Machine-readable status for monitoring scripts
swapon --show=NAME,USED --raw --noheadings
```

## Nuances and Gotchas

- **Swapfiles must be contiguous enough and hole-free.** The classic
  failure `swapon: /swapfile: swapfile has holes` comes from allocating
  with `fallocate` on filesystems/kernels that produce sparse files.
  Prefer `dd` for portability; on btrfs a swapfile additionally needs
  NOCOW (`chattr +C`) and a sufficiently new kernel.
- **Permissions matter.** The kernel refuses world-readable areas;
  `chmod 600` is the standard (observed: `insecure permissions 0666,
  0600 suggested.`).
- **`-a` reads fstab; `swapoff -a` reads `/proc/swaps`.** The
  asymmetry trips up scripts that "restart" swap with
  `swapoff -a && swapon -a` — that pair is actually the standard way to
  re-apply fstab priorities.
- **`-s` is deprecated.** Use `swapon --show` (or `cat /proc/swaps`
  for the raw view); `-s` output lacks UUID/LABEL and ignores fstab
  niceties.
- **Priorities decide locality, not capacity.** Higher-priority areas
  fill completely before lower ones are touched; if you expected
  proportional use, you wanted equal priorities (striping) instead.
- **discard is off unless asked.** Without `-d`/fstab `discard`, swap on
  an SSD never issues TRIMs (except periodic ones if fstrim covers it —
  it does not cover swap); on thin-provisioned storage the area never
  returns blocks.
- **Hibernation wants enough swap.** Suspend-to-disk stores a RAM-sized
  image; swap smaller than RAM plus a configured `resume=` means
  hibernate silently unavailable — check before "optimizing" swap away.
- **Activation needs root and a valid header.** `swapon` on an
  unformatted target exits 255 (observed) with `read swap header
  failed`; the fix is `mkswap`, not retrying.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All requested areas activated (and success for `--show`). |
| 255 | Activation failure observed on recent util-linux: bad/missing header, missing device, permission problems. |
| other non-zero | fstab-level problems with `-a` (unparseable file) — script against 0 vs non-zero. |

The man page documents no detailed code table; capture stderr for the
reason.

## Related Commands

- [`mkswap`](./mkswap.md) — writes the header swapon validates; no header, no activation.
- [`swapoff`](./swapoff.md) — deactivation, with its own /proc/swaps-based `-a`.
- [`swaplabel`](./swaplabel.md) — the label/UUID that `LABEL=`/`UUID=` specs resolve to.
- [`lsblk`](./lsblk.md) — see which partitions are swap candidates.
- [systemd](../../admin/systemd.md) — generated `.swap` units are what actually activate swap at boot.
- [util-linux overview](./overview.md) — collection hub for the other util-linux pages.

## Interview Questions

### Q: Walk through creating a 4G swapfile that will actually activate.

`dd if=/dev/zero of=/swapfile bs=1M count=4096` (preallocate real
blocks — avoids the "swapfile has holes" failure that `fallocate` can
produce), `chmod 600 /swapfile` (the kernel refuses loose permissions),
`mkswap /swapfile` (write the header), `swapon /swapfile`, then add the
fstab line for persistence. On btrfs add NOCOW handling and mind kernel
version support.

### Q: What do swap priorities do when you have multiple swap devices?

Each area has a priority (`-p`/fstab `pri=`). The kernel exhausts
higher-priority areas first; areas with equal priority are striped
round-robin for parallelism. So `-p 100` on NVMe plus `-p 10` on a disk
gives a hot device with a cold fallback — while two equal-priority
devices spread the I/O. Unspecified areas share a low default priority.

### Q: Why does swapoff -a followed by swapon -a matter on a system with fstab priorities?

`swapoff -a` deactivates what the kernel has (from `/proc/swaps`);
`swapon -a` re-activates per fstab, re-reading current `pri=` values.
Runtime priority changes from the command line are undone by this
cycle — it is the standard way to converge a running system onto the
intended fstab configuration.

### Q: What is the -e/--ifexists option for?

Fstab entries for swap on optional hardware (USB, cloud-attached
volumes) would make `swapon -a` fail loudly when the device is absent.
`ifexists` (fstab option or `-e` flag) skips missing targets silently,
so boot-time activation stays green — at the cost of hiding
configuration mistakes, so pair it with monitoring of actual swap size.

### Q: swapon reports "read swap header failed". What are the likely causes and fixes?

The target has no valid swap signature: never formatted (run `mkswap`),
wrong device node, or a page-size mismatch from a cross-architecture
image (fixable with `-f/--fixpgsz`). Also check you are not pointing at
a filesystem *containing* the swapfile instead of the file itself.

### Q: Why is swapon -s deprecated and what replaced it?

`-s` just dumps `/proc/swaps`-style lines with fixed columns. `swapon
--show` provides selectable columns (including UUID and LABEL),
`--raw`/`--noheadings`/`--bytes` for scripts, and consistent formatting
with the rest of util-linux's table output. New scripts should use
`--show=NAME,SIZE,USED,PRIO` and stop parsing the legacy format.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/mount/swapon.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
