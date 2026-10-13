# swapoff — disable devices and files for paging and swapping

## Overview

`swapoff` deactivates a swap area: it tells the kernel to stop using the
given device or file and to pull every swapped-out page back into RAM
(or push it to another swap area). It is the counterpart of `swapon` and
the standard preamble for touching a swap device — partition resizing,
disk removal, filesystem work on the volume holding a swapfile. It ships
with the `mount` package (Debian bookworm) at `/usr/sbin/swapoff` and
requires root.

`swapoff` is often confused with `swapon` (activates; note the
asymmetry: `swapoff -a` reads `/proc/swaps`, `swapon -a` reads
`/etc/fstab`), with `mkswap` (writes the header, activates nothing), and
with deleting the swapfile (which is only safe after a successful
swapoff).

| Field | Value |
| --- | --- |
| Package | mount (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/swapoff |
| First appeared / lineage | AT&T/4BSD heritage; Linux swapon/swapoff pair since the earliest kernels |
| Standards | None — kernel `swapoff(2)` specific |

## Synopsis

```
swapoff [options] [<spec>...]
```

Common one-line forms:

```
swapoff /dev/sda2                   # disable one partition
swapoff /swapfile                   # disable a swapfile
swapoff -a                          # disable everything in /proc/swaps
swapoff -v LABEL=swap1              # by label, with progress messages
```

## How It Works

### The drain-back operation

`swapoff` wraps the `swapoff(2)` syscall. The kernel must *unswap*: every
page of the area currently in use is read back into memory — if RAM (plus
remaining swap) cannot hold them, the syscall fails rather than losing
data:

```
 swap area (inactive target)          RAM
 ┌─────────────────────────┐      ┌──────────────┐
 │ pages of process images │ ───► │ pages land   │
 │ marked "in swap on X"   │      │ in RAM /     │
 └─────────────────────────┘      │ other swap   │
        kernel clears the         └──────────────┘
        swap map for X, then
        removes X from /proc/swaps
```

This is why swapoff is *slow* on a busy system (it moves potentially
gigabytes synchronously) and why it can fail with "Cannot allocate
memory" on a loaded box — the classic operational trap.

### Reading /proc/swaps like swapoff -a does

Each line of `/proc/swaps` is one active area; `-a` iterates exactly
this list, so the file is both the source of truth and the progress
indicator during a long drain-back (`Used` should fall toward 0):

```
Filename                Type       Size     Used  Priority
/dev/sda2               partition  4194300  1024  -2
/swapfile               file       2097148  0     100
```

`Type` distinguishes partitions from files, `Priority` reflects `-p`/
fstab `pri=` values (negative = kernel default), and an area disappears
from the file the moment its `swapoff(2)` completes.

### Specs: device, file, label, UUID

An explicit target may be given as a device path, a swapfile path, or a
`LABEL=`/`UUID=` reference (also bare `-L label` / `-U uuid` forms) —
resolved through blkid, mirroring fstab conventions. With `-a` it
disables *everything the kernel currently has active*, enumerated from
`/proc/swaps` — not from fstab.

```bash
$ cat /proc/swaps
Filename    Type    Size   Used   Priority
/dev/sda2   partition 4194300 0    -2
```

### systemd-managed swap

On modern systems swap units are generated for fstab entries and device
units appear for block devices. A manual `swapoff` succeeds, but the
*activation method* matters for what happens next: a `systemctl swapoff
<unit>`-style view (or editing fstab) is what prevents the area from
coming back at the next activation pass or reboot. Simply swapoff-ing a
device that a unit still references invites reactivation.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-a, --all` | Disable all swap areas listed in `/proc/swaps`. |
| `-v, --verbose` | Print per-target progress/notices. |
| `LABEL=<label>` / `-L <label>` | Resolve the area by its swap label (see `swaplabel`). |
| `UUID=<uuid>` / `-U <uuid>` | Resolve by swap UUID. |
| `<device>` / `<file>` | Deactivate this partition or swapfile directly. |

The option surface is deliberately small — the complexity lives in the
kernel's drain-back, not in flags.

## Usage Patterns

```bash
# Shrink or remove a swap partition: deactivate first (root)
swapoff /dev/sda2
```

```bash
# Disable everything currently active (reads /proc/swaps)
swapoff -a
```

```bash
# Remove a swapfile safely — deactivate, then delete
swapoff /swapfile && rm /swapfile
```

```bash
# By label or UUID, as fstab would reference it
swapoff -L swap1
swapoff UUID=7a3f1c2e-1111-4e5f-8a9b-001122334455
```

```bash
# Refresh all swap with new priorities from fstab
swapoff -a && swapon -a
```

```bash
# Watch progress on a large area (verbose; can take minutes)
swapoff -v /dev/sdb2
```

```bash
# Before resizing the volume that holds swap (LVM)
swapoff /dev/vg0/swap && lvreduce -r -L 2G /dev/vg0/swap && swapon /dev/vg0/swap
```

```bash
# Check what is (still) active afterwards
cat /proc/swaps; swapon --show
```

## Nuances and Gotchas

- **It can simply fail under memory pressure.** Drain-back needs RAM (or
  other swap) for every resident swapped page; on a loaded system you
  get `swapoff failed: Cannot allocate memory`. Free memory first,
  reduce load, or lower the area's priority so pages migrate to other
  swap.
- **It can take a long time, synchronously.** No progress bar, no
  timeout; a multi-GiB swapoff holds your shell. Run it in `tmux`/under
  `nohup` for big boxes and monitor `/proc/swaps` `Used` dropping.
- **`-a` reads `/proc/swaps`, not fstab.** `swapoff -a` disables what is
  *actually on*; `swapon -a` enables what *should be on* per fstab. The
  asymmetry is intentional and frequently mistaken.
- **Root only.** A non-root caller is refused up front with
  `swapoff: Not superuser.` (observed exit status 16 on recent
  util-linux) — an early check, distinct from a syscall failure.
- **Deleting a swapfile without swapoff corrupts nothing immediately but
  leaves pages pointed at a missing file**; the kernel holds the inode,
  so disk space is not reclaimed until swapoff — and `swapon` on the
  path later creates a fresh, unrelated area.
- **systemd will bring swap back.** fstab-generated `.swap` units and
  device units reactivate areas; persist changes by editing fstab (or
  masking units), not by swapoff alone.
- **Hibernation images live in swap.** Swapoff on the resume device
  destroys a pending hibernation image; expect a cold boot instead.
- **Disabling an inactive area is an error.** The kernel's `swapoff(2)`
  returns EINVAL for a target that is not currently active, so retry
  loops should re-check `/proc/swaps` rather than blindly re-running
  the command.
- **`swapoff -a` during performance testing** is a legitimate move (show
  pure-RAM behavior) — but re-enable afterwards; a swapless box OOM-kills
  under pressure that swap would have absorbed.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All requested areas deactivated (`-a` with nothing active also succeeds). |
| non-zero | Failure: not superuser (observed 16), unknown/unresolvable spec, kernel refused (insufficient memory), area already off. |

The man page documents no code table; script against 0 vs non-zero and
read stderr for the cause.

## Related Commands

- [`swapon`](./swapon.md) — the activating counterpart; note the fstab vs /proc/swaps asymmetry.
- [`mkswap`](./mkswap.md) — writes the header that makes an area swappable in the first place.
- [`swaplabel`](./swaplabel.md) — edit the label/UUID used to reference the area.
- [`lsblk`](./lsblk.md) — identify swap partitions when planning removals.
- [systemd](../../admin/systemd.md) — generated `.swap` units decide whether an area comes back.
- [util-linux overview](./overview.md) — collection hub for the other util-linux pages.

## Interview Questions

### Q: Why does swapoff fail with "Cannot allocate memory" on a loaded system?

swapoff must read every in-use swapped page back into RAM (or push it to
another swap area). If `MemAvailable` plus other swap cannot hold them,
the kernel refuses rather than evicting or losing data. Remedies: free
memory (drop caches won't help much — drop load instead), activate other
swap first so pages have somewhere to go, or reduce the working set.

### Q: swapoff -a ran on a system where /etc/fstab lists two swap areas but only one was active. What happened?

Exactly one area — the active one — was disabled: `swapoff -a` iterates
`/proc/swaps`, the kernel's live table, not fstab. The inactive fstab
entry is untouched (and still configured for future `swapon -a`). This
asymmetry with `swapon -a` (which reads fstab) is a favorite gotcha.

### Q: You deleted an in-use swapfile with rm. What is the state of the system?

The kernel keeps the inode and its pages; `/proc/swaps` still shows the
entry and `df` does not reclaim the space. The system works but the
storage is leaked until `swapoff` completes on that area. Correct
sequence is always `swapoff /swapfile && rm /swapfile`, then update
fstab.

### Q: How do you safely shrink the LVM logical volume that holds swap?

`swapoff /dev/vg0/swap`, perform the `lvreduce` (with `-r` to shrink the
*file* layer if it is a swapfile on a filesystem — for a raw swap LV,
just the LV), then re-run `mkswap` if the size changed in a way that
invalidates the header (or rely on swapon's checks), and `swapon` again.
Touching the volume while swap is active risks kernel panics or I/O
errors, which is why swapoff is the mandatory first step.

### Q: What is the difference in outcome between swapoff -a and disabling the fstab entry?

`swapoff -a` changes only the running system: the next boot (or the next
systemd activation pass) re-enables everything fstab still lists.
Persisting the change requires editing fstab (or masking the generated
`.swap` unit). Use both: swapoff for now, fstab edit for forever.

### Q: A pending hibernation image exists and someone runs swapoff -a. Consequences?

The hibernation image is stored in swap; deactivating the area destroys
it. The machine will cold-boot instead of resuming, losing the suspended
session. Anything that manipulates swap on a laptop/server with
hibernation enabled must check for a pending image first — one of the
less obvious operational risks of swapoff.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/mount/swapoff.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
