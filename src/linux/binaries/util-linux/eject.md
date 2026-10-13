# eject — eject removable media

## Overview

`eject` unmounts (if needed) and ejects removable media — CD/DVD/BD trays, tape
cartridges, ZIP/floppy drives, and SCSI-attached devices — with one command. It
accepts either a device node (`/dev/sr0`) or a **mountpoint** (`/media/cdrom`)
and resolves the backing device itself, which is what makes it ergonomic: you
almost never need to know which `/dev/` name the drive got.

Debian bookworm ships it in its own `eject` package (built from the util-linux
source tree, which absorbed the historical standalone `eject` by Jeff Tranter)
at `/usr/bin/eject`, man section 1. Besides opening the tray it can close it
(`-t`), toggle (`-T`), set auto-eject (`-a`), software-lock the door (`-i`),
select changer slots (`-c`), and set/list CD-ROM speeds (`-x`/`-X`).

It is often confused with `umount` (which only unmounts — the tray stays shut
and, for many devices, media stays powered) and with modern desktop tooling
(`udisksctl`, file-manager buttons) that wraps the same ioctls with session
policy on top.

| Field | Value |
| --- | --- |
| Package | eject (Debian bookworm) |
| Section (man) | 1 |
| Path | /usr/bin/eject |
| Lineage | standalone eject package; merged into util-linux (2.38, 2022) |
| Standards | None — device-specific ioctls (CDROMEJECT, SG_IO, …) |

## Synopsis

```
eject [options] [device|mountpoint]
```

Common one-line forms:

```
eject /dev/sr0          # open the tray of the first optical drive
eject /media/cdrom      # resolve mountpoint → device → unmount → eject
eject -T /dev/sr0       # toggle: close if open, open if closed
eject -n /media/cdrom   # show what would be ejected, do nothing
```

## How It Works

### Resolution, unmount, then the ioctl

`eject` runs a three-step decision pipeline:

```
 argument ──► resolve to a device ──► unmount if mounted ──► eject ioctl
   /dev/sr0    (mountpoint lookup      (unless -m)          CDROMEJECT /
   /media/x    via mount table,        (and sibling         SG_IO / tape
               -d shows default)        partitions)          offload
```

1. **Resolve.** A mountpoint is mapped to its device by scanning the kernel
   mount table; a bare name like `cdrom` is tried against `/dev`. Newer versions
   also handle multi-partition devices: if any partition of the device is
   mounted, all of them are unmounted (skippable with `-M`).
2. **Unmount.** Unless `-m` is given, mounted filesystems on the device are
   unmounted first — ejecting a mounted medium is what older systems refused
   outright, and even today a busy mount blocks the eject.
3. **Eject.** The appropriate low-level operation is attempted per device type:
   the CD-ROM eject ioctl for optical drives, SCSI commands via the generic
   layer for `-s` devices, tape unload for `-q`, floppy eject for `-f`.

### The -n dry run

`-n` (`--noop`) prints the resolved device and stops. In scripts this is the
safe way to turn a user-supplied mountpoint into a device name without side
effects:

```bash
$ eject -n /media/cdrom
eject: device is `/dev/sr0'
```

### Beyond opening the tray

- `-t` closes the tray (only on drives that support software tray close).
- `-T` toggles — handy for single-button workflows on drives whose buttons are
  inaccessible (slot-loaders, Mac Minis, racked chassis).
- `-a on` sets *auto-eject*: the medium pops out automatically when unmounted.
- `-i on` engages the software eject lock — the drive refuses manual button
  ejects too. Useful against accidental yanking of mounted media.
- `-c <slot>` addresses multi-disc changers; `-x <n>` caps drive speed
  (quieter/less vibration when reading), `-X` lists supported speeds.

## Options That Matter

### Selection and probing

| Option | Effect |
| --- | --- |
| `-n, --noop` | Show the resolved device; perform no action |
| `-d, --default` | Show the default device |
| `-v, --verbose` | Print each step as it happens |
| `-m, --no-unmount` | Do not unmount; attempt eject only |
| `-F, --force` | Override the removability check (dangerous) |

### Media type

| Option | Effect |
| --- | --- |
| `-r, --cdrom` | Eject via CD-ROM ioctl |
| `-s, --scsi` | Eject via SCSI commands |
| `-f, --floppy` | Eject a floppy drive |
| `-q, --tape` | Unload a tape cartridge |

### Drive control

| Option | Effect |
| --- | --- |
| `-t, --trayclose` | Close the tray |
| `-T, --traytoggle` | Toggle tray open/closed |
| `-a on|off, --auto` | Auto-eject on unmount |
| `-i on|off, --manualeject` | Software-lock the drive against manual eject |
| `-c <slot>, --changerslot` | Select slot in a multi-disc changer |
| `-x <speed>, --cdspeed` | Set max CD-ROM speed |
| `-X, --listspeed` | List supported speeds |

## Usage Patterns

```bash
# The everyday case: eject by mountpoint, no /dev name needed
eject /media/cdrom
```

```bash
# Script-safe resolution without side effects
dev=$(eject -n /media/cdrom 2>/dev/null); echo "$dev"
```

```bash
# Unmount and spin down a USB stick as a "safely remove" equivalent
eject /dev/sdb1
```

```bash
# Slot-loading drive with no button: toggle from the keyboard
eject -T /dev/sr0
```

```bash
# Prevent anyone pressing the physical button from yanking a mounted disc
sudo eject -i on /dev/sr0
```

```bash
# Pop the disc the moment it is unmounted (kiosk workflow)
sudo eject -a on /dev/sr0
```

```bash
# See every step while debugging a stubborn drive
eject -v /dev/sr0
```

```bash
# Cap the reading speed to quiet a noisy drive
sudo eject -x 8 /dev/sr0
```

```bash
# Changer: load disc 3
eject -c 3 /dev/sr0
```

```bash
# Unload a tape
eject -q /dev/st0
```

```bash
# What would happen, verbosely, on a multi-partition USB drive
eject -nv /media/user/USBDRIVE
```

## Nuances and Gotchas

- **"Device or resource busy" means consumers remain.** Any mounted partition,
  open file, running VM, or loop mapping blocks the unmount step. Find holders
  (`fuser -vm`, `lsof +D`, `findmnt`), close them, retry. `-m` skips the unmount
  and asks the drive directly — which usually fails on mounted media.
- **USB sticks: "eject" vs power-off.** On Linux, ejecting a USB mass-storage
  device spins it down/flushes it but the *device* may remain enumerated; the
  desktop "safely remove" additionally powers the port off (udisks `power-off`).
  Either way, data is flushed before the tray/eject step — but do not unplug
  while a filesystem is mounted.
- **Tray-less and exotic drives.** `-t` fails on slot-loaders; some cheap USB
  enclosures ignore eject ioctls entirely; `-X` returns nothing on drives that
  do not implement speed reporting.
- **Permissions.** Eject ioctls generally work for unprivileged users on drives
  with sane udev ACLs (the logged-in session), but tapes, changers and
  non-session devices usually need root.
- **`-i on` locks the hardware button too.** Forgetting it engaged is a classic
  support call ("the tray button stopped working") — `eject -i off` unlocks.
- **Resolution surprises.** A mountpoint argument resolves through the mount
  table; on automounted/autofs paths the mount may be indirect — verify with
  `-n` first.
- **Package provenance.** Debian splits it out of the main `util-linux` binary
  package; minimal containers often lack it while shipping `umount`.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success (including a successful `-n` display) |
| 1 | Failure — busy device, unknown device, unsupported ioctl, permission denied |

## Related Commands

- [`overview`](./overview.md) — index of all util-linux collection pages
- [permissions](../../admin/permissions.md) — who may issue device ioctls and why (udev ACLs, groups)

## Interview Questions

### Q: What is the difference between eject and umount on Linux?

`umount` only detaches the filesystem. `eject` resolves a mountpoint or device,
unmounts everything mounted from it (including sibling partitions), and then
issues the drive-level eject ioctl — tray opens, tape unloads, or the device
spins down. On USB media, desktop stacks go one step further and power off the
device after ejecting.

### Q: A user runs eject /dev/sdb1 and gets "device is busy". Walk through triage.

First list what is mounted from the device (`findmnt /dev/sdb1` and siblings),
then find processes holding files open (`fuser -vm <mountpoint>`,
`lsof +D <mountpoint>`), including non-obvious consumers: shells with cwd inside,
search indexers, VMs with the disk attached. Terminate or stop them, unmount,
retry. `eject -m` would bypass the unmount but typically cannot eject while a
filesystem is mounted, so closing consumers is the real fix.

### Q: What does eject -i on do, and when is it useful?

It engages the drive's software eject lock, which makes both the physical eject
button and software ejects fail until `-i off` is issued. It protects mounted
media from being yanked — e.g. museum/kiosk machines or racks where users press
tray buttons — at the cost of a support call when someone forgets it is set.

### Q: How does eject resolve a mountpoint argument to a device?

It consults the kernel's mount table (mountinfo) to find the device backing the
given path, then targets the whole drive. `eject -n` prints that resolution
without acting, which is why it doubles as a scripting helper for turning paths
into device names. Recent versions extend this to unmount all partitions of the
resolved device, not just the one named.

### Q: Where does the Debian eject binary come from and why does that matter for availability?

Bookworm builds it from the util-linux source tree into a separate `eject`
package (upstream merged the old standalone eject in 2.38). Practical
consequence: minimal images and slim containers frequently lack `eject` while
having `umount`, so scripts should fall back gracefully or use
`udisksctl power-off` in desktop contexts.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/eject/eject.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
