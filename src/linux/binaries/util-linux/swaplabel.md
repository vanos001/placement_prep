# swaplabel — display or change the label and UUID of a swap area

## Overview

`swaplabel` edits the metadata of an existing swap area: it prints the
volume label and UUID stored in the swap header, and with `-L`/`-U` it
rewrites either field *in place* — no `mkswap` re-run, no reformat. The
point is keeping `/etc/fstab` entries (`LABEL=swap1`, `UUID=...`)
accurate when devices move, disks are cloned, or a swap area needs a
distinguishable name. It ships with the `util-linux` package (Debian
bookworm) at `/usr/sbin/swaplabel`.

`swaplabel` is often confused with `mkswap` (creates the whole swap
header — label and UUID are side effects), with `blkid`/`lsblk -f`
(read the same metadata for *all* filesystem types), and with
`e2label`/`xfs_admin` (label editors for filesystems, not swap).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/swaplabel |
| First appeared / lineage | util-linux addition of the early 2010s (2.18 era) |
| Standards | None — Linux swap signature specific |

## Synopsis

```
swaplabel [options] <device>
```

Common one-line forms:

```
swaplabel /dev/sda2                   # show current label/UUID
swaplabel -L swap1 /dev/sda2          # set the label
swaplabel -U $(uuidgen) /swapfile     # set a fresh UUID
swaplabel -U clear /dev/sda2          # blank the UUID out
```

## How It Works

### Where label and UUID live

A swap area is identified by a header in its first page. The layout
(`swap_header_v1`) reserves fixed offsets for the identity fields:

```
 offset 0            1 KiB             ~4 KiB (one page)
 ┌──────────────────┬───────────────────────────────┬─────┐
 │ boot bits (1024) │ version, last_page, badpages, │ ... │
 │ (label/UUIID live│ uuid[16], volume_name[16],    │     │
 │  right after the │ padding ...                   │     │
 │  header fields)  │                  "SWAPSPACE2" │magic│
 └──────────────────┴───────────────────────────────┴─────┘
```

`swaplabel` probes the device, validates the signature, and rewrites
only the 16-byte UUID and the 16-byte label — the kernel's swap
accounting data (`last_page`, `nr_badpages`) is untouched. The kernel
reads the header at `swapon` time only, so renaming an *inactive* area
is trivially safe; the tool does not require the area to be off, but
doing it while inactive keeps on-disk state and fstab references
unambiguous.

### Showing and setting

With no options it prints the current values; with `-L`/`-U` it updates
them. On a target without a valid swap signature it fails cleanly
(observed on a non-swap/missing device):

```bash
$ swaplabel /tmp/sw
swaplabel: /tmp/sw: unable to probe device: No such file or directory
$ echo $?
1
```

### Who consumes the metadata

- `/etc/fstab` and `swapon` accept `LABEL=...` and `UUID=...` specs, so
  a stable label survives device renumbering (`/dev/sdb3` becoming
  `/dev/sdc3`).
- `blkid` and `lsblk -f` display swap labels/UUIDs alongside filesystems
  — the usual way to *find* the current values.
- `mkswap -L`/`-U` sets the same fields at creation time; reaching for
  `mkswap` later just to rename is overkill and rewrites the header.

### Working through a rename end to end

A label change is a three-coordinate update: the on-disk field, whatever
references it (fstab, systemd, `resume=`), and the running kernel's view
(which does not track labels at all):

```bash
# 1. record the current identity before changing anything
blkid /dev/sda2            # shows the swap signature's UUID/LABEL

# 2. (recommended) deactivate so disk and fstab can't disagree mid-flight
swapoff /dev/sda2

# 3. rewrite the identity fields only
swaplabel -L swap1 -U 7a3f1c2e-1111-4e5f-8a9b-001122334455 /dev/sda2

# 4. keep references in step, then reactivate
#    /etc/fstab:  LABEL=swap1 none swap sw 0 0
swapon LABEL=swap1
```

Note that step 4 uses the *new* label: `swapon` resolves the spec through
blkid at activation time, so the fstab line and the on-disk label must
agree before `swapon -a` runs at boot.

## Options That Matter

| Option | Effect |
| --- | --- |
| *(none)* | Print the current label and UUID of the device. |
| `-L, --label <label>` | Set the volume label (maximum 16 characters — the on-disk field is 16 bytes). |
| `-U, --uuid <uuid>` | Set the UUID; accepts a literal UUID, or `clear` to remove it (generate fresh values with `uuidgen`). |

That is the complete option surface (plus `-h`/`-V`): one metadata
structure, two editable fields.

## Usage Patterns

```bash
# Show the identity of an existing swap partition
swaplabel /dev/sda2
```

```bash
# Give the swap area a stable name for fstab
swaplabel -L swap1 /dev/sda2
# fstab:  LABEL=swap1 none swap sw 0 0
```

```bash
# Fix a duplicated UUID after dd-cloning a disk (both copies are identical!)
swaplabel -U $(uuidgen) /dev/sdb2
```

```bash
# Set a specific UUID so an fstab entry keeps working across reformat
swaplabel -U 7a3f1c2e-1111-4e5f-8a9b-001122334455 /dev/sda2
```

```bash
# Rename the swapfile's area instead of re-running mkswap on it
swaplabel -L swapfile-main /swapfile
```

```bash
# Verify what tooling will report afterwards
lsblk -f /dev/sda2
blkid /dev/sda2
```

```bash
# Clear the UUID entirely (area becomes anonymous again)
swaplabel -U clear /dev/sda2
```

```bash
# Distinguish the copy in a migration script before it ever activates
swaplabel -L swap-migrated /dev/sdb2
```

```bash
# Confirm the change from the consumer side (what fstab tooling sees)
lsblk -no NAME,UUID,LABEL,FSTYPE /dev/sda2
```

## Nuances and Gotchas

- **The label is capped at 16 bytes.** Longer names are rejected (or
  truncated); swap labels are visibly shorter than ext4's 16-*char*
  labels feel in practice — plan names accordingly.
- **`mkswap` vs `swaplabel` mindset.** `mkswap` (re)initializes the
  header — running it on an *active* area is meaningless and on a
  hibernation image is destructive. For pure renaming, swaplabel is the
  surgical tool.
- **Changing the UUID of active swap is allowed but confusing.** The
  kernel does not re-read the header, so nothing breaks immediately —
  but fstab/`resume=` references now point at a UUID the *next* boot
  expects while this boot's swapon used the old one. Do identity edits
  with the area off.
- **Hibernation depends on the UUID.** `resume=` kernel parameters and
  systemd hibernate logic track the swap area by UUID; rewriting it
  casually breaks resume.
- **dd-cloned disks duplicate both label and UUID.** Two identical swap
  signatures on one system produce ambiguous `LABEL=`/`UUID=`
  resolution and noisy swapon behavior — re-stamp the copy with
  `swaplabel -U $(uuidgen)`.
- **Probing needs the device, not the mountpoint.** Swap areas have no
  mountpoint; pass `/dev/...` or the swapfile path, and expect a probe
  error (exit 1) for non-swap targets.
- **No JSON/machine output.** The show mode is two short lines meant for
  humans; scripts that need parseable metadata use `blkid -o value` or
  `lsblk -no UUID,LABEL`.
- **It cannot create or resize areas.** swaplabel only edits two header
  fields; sizing a swapfile or re-checking the area map is `mkswap`
  (and `dd`) work. A brand-new device still needs `mkswap` before
  `swapon` accepts it.
- **Filesystem label tools reject swap.** `e2label`/`xfs_admin` expect
  their own signatures and fail on a swap area; the reverse is equally
  true — swaplabel refuses non-swap devices. Match the tool to the
  signature.
- **Container/VM images clone identities.** Any workflow that ships
  pre-made images (cloud images, golden disks) ships duplicated swap
  UUIDs unless the build pipeline restamps them; bake a `swaplabel -U
  $(uuidgen)` first-boot step or blank the area in the image.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Show or set completed successfully. |
| 1 | Probe/validation failure: no swap signature, device missing or unreadable (observed `unable to probe device`). |

## Related Commands

- [`mkswap`](./mkswap.md) — creates the swap header that swaplabel edits in place.
- [`swapon`](./swapon.md) — activates areas by `LABEL=`/`UUID=` spec; reads the header once.
- [`swapoff`](./swapoff.md) — deactivates by the same spec forms.
- [`blkid`](./blkid.md) — displays the same label/UUID for all signature types.
- [`lsblk`](./lsblk.md) — tree view including swap partitions' UUID/label.
- [util-linux overview](./overview.md) — collection hub for the other util-linux pages.

## Interview Questions

### Q: When would you use swaplabel instead of mkswap?

When the area already exists and only its identity is wrong — e.g. a
dd-cloned disk duplicated the UUID, or you want fstab to reference a
stable label. `mkswap` rewrites the whole header (and is destructive to
a hibernation image); swaplabel touches only the UUID/label bytes, so
it is the surgical, lower-risk operation.

### Q: What breaks if two swap areas on one system have the same UUID?

`UUID=` and `LABEL=` lookups become ambiguous: fstab mounting, swapon -a
and resume logic may bind to the wrong device, and tooling reports
duplicates. The classic cause is `dd`-cloning a disk. Fix by restamping
one side: `swaplabel -U random /dev/<copy>`.

### Q: How do label and UUID actually reach the kernel?

They do not, at runtime: the kernel reads the swap header once during
`swapon(2)` to validate and size the area; afterwards it tracks the area
by its device/path in `/proc/swaps`. Labels and UUIDs are consumed by
userland — fstab parsing, swapon spec resolution, `blkid` — so editing
them is safe from the kernel's perspective but changes what the next
`swapon` (i.e. next boot) resolves.

### Q: How do you find the label and UUID of an active swap area from a script?

Not from `/proc/swaps` — that table carries only path, type, size, used
and priority. Use `blkid <device>` or `lsblk -no UUID,LABEL` (both read
the on-disk header via libblkid), or `swaplabel <device>` for the
human-readable two-line form. Scripts that must map `/proc/swaps`
entries to fstab references pipe the device through one of those.

### Q: Why is the swap label limited to 16 characters?

It is a fixed 16-byte field in the on-disk `swap_header_v1` structure —
no extension mechanism exists without changing the swap format, which
the kernel and hibernation resume code depend on. Filesystem labels can
be longer because their formats evolve independently.

### Q: A system stopped resuming from hibernation after you "renamed" its swap area. What did you actually break?

`resume=` (or systemd's hibernate resolution) locates the resume device
by UUID. `swaplabel -U ...` changed that UUID, so at boot the kernel
finds no matching swap area with a resume image and cold-boots. Restore
the original UUID with `swaplabel -U <old>` — or update the kernel
command line — and keep hibernation swap identity stable.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/swaplabel.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
