# isosize — print the size of an ISO 9660 filesystem

## Overview

`isosize` reports the size of an ISO 9660 filesystem — the format used by CD/DVD images (`*.iso`), optical media, and many bootable images. It reads the filesystem's own volume descriptors, so its answer is the *declared* ISO size, which can differ from the file size on disk or the block device capacity. Ships in the `util-linux` package (Debian bookworm) at `/usr/sbin/isosize`.

Reach for it in scripts that verify whether an image fits a target medium (CD-R capacity checks), that want the payload size of an ISO rather than the container file size, or that need sector math (total sectors × sector size) for image slicing. It is often confused with `stat -c %s` (byte length of the file, including any trailing padding) and `blockdev --getsize64` (whole-device capacity). `isosize` answers "how big does this filesystem say it is".

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/isosize |
| First appeared | long-standing util-linux tool |
| Standards | ISO 9660 / ECMA-119 volume structure; no command standard |

## Synopsis

```
isosize [options] <iso9660_image_file>...
```

Common one-line forms:

```
isosize /dev/sr0            # size in bytes of the mounted/at-hand media
isosize -x image.iso        # sector count and sector size
isosize -d 1024 image.iso   # bytes divided by 1024 -> KiB
isosize a.iso b.iso         # sums the sizes of several images
```

## How It Works

### Reading the declared size from the volume descriptors

An ISO 9660 filesystem reserves sector 16 (each sector is 2048 bytes by default) for the Primary Volume Descriptor (PVD). That descriptor contains the Volume Space Size — the total extent of the filesystem in logical blocks. `isosize` reads exactly those fields; it does not scan the file:

```
 image file / block device
 ┌───────────────────────────┬──────────────────────────┬──────────┐
 │ system area (32 KiB)      │ PVD @ sector 16          │ data ... │
 │                           │  └─ Volume Space Size ───┼──► N × blockSize
 └───────────────────────────┴──────────────────────────┴──────────┘
 isosize  = N * blockSize                (default output, bytes)
 isosize -x = "sector count: N, sector size: blockSize"
```

Because it consults the metadata, `isosize` works identically on a regular image file, on an optical block device (`/dev/sr0`), or on a loop-mounted image — and its answer is authoritative for the ISO payload even when the container file has been padded.

### Why the answer differs from the file size

Image builders and burning pipelines pad to block boundaries or session sizes, so `stat` on the file often reports more bytes than the ISO structure actually uses. Optical drives may also expose more capacity than the written session. `isosize` cuts through all of that by trusting the PVD.

### Anatomy of the volume area

```
byte offset (default geometry)
0        ┌───────────────────────────────┐
         │ System area: 32 KiB           │  boot code lives here on hybrids
32768    ├───────────────────────────────┤
         │ sector 16: Volume Descriptors │
         │   VD 0: Primary (PVD)         │  ◄─ Volume Space Size reads here
         │   VD 1: Supplementary (Joliet)│
         │   ... terminating descriptor  │
         ├───────────────────────────────┤
         │ Path tables, root directory,  │
         │ file extents ...              │
N*blk    └───────────────────────────────┘  Volume Space Size end
```

The PVD's *Volume Space Size* field counts logical blocks; multiply by the *Logical Block Size* field (2048 for virtually everything modern) and you have the byte total `isosize` prints. Both fields are little- and big-endian duplicates inside the descriptor — the tool picks the right endianness, sparing you the classic byte-swap bug of hand parsers.

### Size probes compared

| Probe | Answers | On an ISO file it reports |
| --- | --- | --- |
| `isosize` | the filesystem's declared extent | payload size from the PVD |
| `stat -c %s` | container length | file bytes, padding included |
| `du -B1` | allocated bytes | padded file rounded to fs blocks |
| `blockdev --getsize64` | device capacity | block-device size (whole medium) |
| `df` on the mount | filesystem usage on the image | mounted-fs free/used |

Choose by question: fitting a medium → container/device size; extracting the payload → `isosize`; free-space math → the filesystem on the *mounted* image (`df`).

### Multiple operands

With more than one image argument, `isosize` prints each size on its own line and (without `-x`) the *sum* in the same byte unit — a convenience for multi-session/merged images. With `-x`, each operand is reported individually as sectors.

### Sector math

`-x` shows the two numbers that multiply to the byte size:

```bash
$ isosize -x mini.iso
sector count: 143360, sector size: 2048
```

`-d <n>` divides the byte total by `<n>`, giving KiB (`-d 1024`) or MiB (`-d 1048576`) without spawning `awk`. The division is integer; combine with `stat` when you need remainders.

### Hybrid ISOs and boot images

Modern installer ISOs are *isohybrid*: an ISO 9660 filesystem whose first sectors double as an MBR so the image boots from both optical media and USB sticks. `isosize` still reads the PVD and reports the ISO extent; the device-level view (`lsblk`, `blockdev --getsize64` on the copied USB stick) can legitimately differ. Boot-record machinery (El Torito, boot catalogs) lives elsewhere in the volume structure and does not change the space-size answer.

### Where it fits in a verification pipeline

```
download image.iso
  ├─ sha256sum image.iso        # integrity (expensive)
  ├─ isosize -x image.iso       # cheap sanity: sane sector count/size
  ├─ isosize image.iso == stat? # padding audit
  └─ mount/loop for content spot-checks
```

`isosize` is the cheap structural check that runs before any expensive byte-level verification.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-x, --sectors` | Print sector count and sector size instead of byte total |
| `-d, --divisor=<n>` | Divide the byte total by `<n>` (e.g. `1024` for KiB) |
| `-h, --help` | Usage summary |
| `-V, --version` | Version string |

Only these exist; the tool deliberately stays tiny. Note `-x` and `-d` are mutually exclusive modes of presentation.

## Usage Patterns

```bash
# Byte size of an optical disc or its image
isosize /dev/sr0
isosize debian.iso

# Does the image fit a 700 MB CD-R? (byte compare, no unit games)
[ "$(isosize app.iso)" -le 737280000 ] && echo fits || echo too-big

# Show the underlying geometry
isosize -x app.iso
# sector count: 143360, sector size: 2048

# Size in KiB/MiB without awk
isosize -d 1024 app.iso
isosize -d 1048576 app.iso

# Sum several images in one call (multi-part payloads)
isosize part1.iso part2.iso

# Compare declared ISO size against container file size (detect padding)
echo "iso:  $(isosize app.iso)"; echo "file: $(stat -c %s app.iso)"

# Feed the byte size to dd to extract exactly the payload
dd if=app.iso of=payload.bin bs=$(isosize app.iso) count=1

# Loop-mount the image at its real extent for verification
losetup -f --show --read-only app.iso   # then mount and compare

# Compare all three probes on the same image (padding audit)
printf 'isosize: %s\nfile:    %s\n' "$(isosize app.iso)" "$(stat -c %s app.iso)"

# Extract exactly the ISO payload from a padded hybrid image
dd if=hybrid.iso of=payload.iso bs=$(isosize hybrid.iso) count=1 status=none

# Guard a build pipeline: refuse images below/above sane bounds
SIZE=$(isosize installer.iso)
[ "$SIZE" -ge 300000000 ] && [ "$SIZE" -le 900000000 ] || { echo bad size; exit 1; }

# Per-file sector geometry for a batch of images
for i in *.iso; do echo "$i: $(isosize -x "$i")"; done

# Convert to MiB for a report line
printf '%s MiB\n' "$(isosize -d 1048576 app.iso)"

# Check a real optical drive (needs read permission on the node)
isosize /dev/sr0 && echo "session readable"

# Sum multi-part images to see the merged total
isosize disc1.iso disc2.iso

# Verify a burned medium matches its source (size layer of a full check)
[ "$(isosize /dev/sr0)" = "$(isosize image.iso)" ] && echo size-ok

# Extract the 2 KiB sector holding the PVD for inspection (offset 32768)
dd if=app.iso bs=2048 skip=16 count=1 status=none | file -

# Watch for the classic SI-vs-binary unit trap in reports
isosize -d 1000000 app.iso    # "MB" in decimal
isosize -d 1048576 app.iso    # MiB in binary
```

## Nuances and Gotchas

- **ISO 9660 only.** Pure UDF images (some DVDs, Blu-ray) have no PVD at sector 16 and `isosize` fails or returns nonsense; use `blkid -o value -s SIZE /dev/sr0`-style probing or `dvd+rw-mediainfo` for those.
- **Trusted metadata, not truth.** A hand-edited or truncated image whose PVD lies will get matching (wrong) output; for sanity checks pair with `stat` and `md5sum` from the publisher.
- **Non-2048 sector sizes exist** (old media, some protection schemes); always take the size from `-x`'s pair rather than assuming 2048.
- **Multiple operands sum in byte mode** — `isosize a.iso b.iso` prints a total; use `-x` for per-file sectors. Scripts that loop over files should invoke `isosize` once per file.
- **Divisor is plain integer division** — `-d 1000000` gives "MB" in SI units but floors the result; there is no rounding control.
- **Read access is required, not root.** Pointing it at a block device needs read permission on the device node (membership in `cdrom`/`disk` typically), not CAP_SYS_ADMIN.
- **Not a capacity probe.** For "how much can this blank medium hold" use the burner tooling (`wodim`/`growisofs`); `isosize` reports an *existing* filesystem only.
- **Obsolete-adjacent, but stable.** The tool has not changed in decades; its value is precisely that it does one ioctl-free read and exits — ideal inside tight installers and initramfs scripts.
- **`-x` output format is prose, not columns.** `sector count: 143360, sector size: 2048` — parse with sed/awk on the words, or prefer the byte form and divide yourself; there is no machine mode.
- **Rock Ridge/Joliet extensions do not change the answer.** Those add name/time metadata; the space size is set once in the PVD. A mismatch between `isosize` and actual readable content usually means a truncated transfer, not an extension quirk.
- **DVDs can lie twice.** UDF-bridged DVDs expose an ISO layer whose PVD may describe only part of the disc; `isosize` reports that layer, not the UDF payload. For video DVDs use the UDF tooling.
- **Zero-byte or tiny images fail loudly** — no PVD at sector 16 means exit 1 with an error; a *corrupted* image whose first 32 KiB are intact may still pass, which is why the checksum stays mandatory.
- **Device permissions, not root.** `/dev/sr0` is typically group `cdrom`; add yourself to the group rather than scripting sudo for a read-only probe.
- **The 32 KiB system area is invisible to isosize.** Hybrid boot code lives before sector 16; an image can lose or gain bytes there without changing the PVD answer — another reason device-level probes disagree with `isosize` on purpose.

## Exit Status

- `0` — the size was read successfully (for multiple operands: all reads succeeded).
- `1` — failure: unreadable file/device, no ISO 9660 PVD found, or invalid options.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`lsblk`](./lsblk.md) — device sizes and topology for block devices, ISO images included once loop-attached.
- [`blkid`](./blkid.md) — filesystem probing (type, UUID, label) that complements size reporting.
- [`losetup`](./losetup.md) — attach an ISO to a loop device so it can be mounted read-only.
- [`mount`](./mount.md) — the tool that actually mounts the ISO 9660 filesystem for inspection.
- [`internals`](../../internals.md) — block layer and how image files become addressable block devices.

## Interview Questions

### Q: Why would a script prefer isosize over `stat -c %s` on an ISO file?

`stat` reports the container file length, which includes builder padding, trailing sessions, or read-ahead slack. `isosize` reads the Primary Volume Descriptor's Volume Space Size — the filesystem's own declaration of its extent — so capacity checks and payload extraction (`dd bs=$(isosize x.iso) count=1`) operate on the real payload size regardless of padding.

### Q: Where does isosize find the size, and what are the implications of that design?

It reads the PVD at sector 16 (offset 32768) and multiplies the volume space size by the logical block size. Implications: it needs only one short read (fast, works in initramfs), it works on both image files and optical devices, it cannot verify the data itself, and any non-ISO (e.g. UDF-only) image has no PVD and fails.

### Q: An image file is 734 MiB but `isosize` reports ~700 MiB. Explain.

The builder padded the file up to a boundary (session alignment, multicourse, or burn-at-once padding) after writing ~700 MiB of actual ISO structure. Both numbers are "correct" for their question; `isosize` answers the filesystem extent, `stat` answers container length. Choose per purpose: fitting a CD-R uses the file size; extracting the payload uses the ISO size.

### Q: How do you get the size in sectors, and why might a script want sectors instead of bytes?

`isosize -x` prints "sector count: N, sector size: S". Sector math matters when slicing images at structural boundaries, verifying against medium geometry (2352-byte raw CD sectors vs 2048-byte data sectors), or computing offsets for hybrid ISO layouts (e.g. isohybrid MBRs). Byte-only arithmetic hides those alignment relationships.

### Q: `isosize a.iso b.iso` prints one number — what is it, and how do you get per-file values?

Without `-x`, byte outputs of multiple operands are summed (a legacy convenience for merged/multi-part images). Per-file reporting requires either `-x` (sectors per operand) or invoking `isosize` once per file in a loop. Script authors should avoid the multi-operand byte form precisely because the summing behavior is easy to miss.

### Q: You need to check that a burned disc matches its ISO. Where does isosize fit?

`isosize /dev/sr0` should equal `isosize image.iso` — a size mismatch catches truncation immediately. It does not validate content; for that compare `sha256sum` of the extracted payload sized by `isosize` (or use the publisher's checksum of the whole image). Size check first (cheap), checksum second (expensive) is the standard order.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/isosize.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
