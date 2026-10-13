# fdisk — interactive partition table manipulator (MBR/GPT)

## Overview

`fdisk` is the classic partition table editor: an interactive, menu-driven tool
that creates, deletes, resizes, renames, lists and type-codes disk partitions,
writing MBR (MS-DOS) or GPT (UEFI) tables. It is a *dialog*, not a hammer: every
edit happens in an in-memory copy of the table, nothing touches the disk until
you answer `w`, and `q` discards everything — a safety model every Linux admin
is expected to be able to recite.

Debian bookworm ships it in the `fdisk` package at `/usr/sbin/fdisk`
(man section 8). It is part of the util-linux family alongside `sfdisk` (the
scriptable/ dumpable twin), `cfdisk` (curses UI on the same engine), and the
libfdisk library underneath — the same engine also powers `blkid`-adjacent
tooling. Modern `fdisk` handles both MBR and GPT natively (the `g`/`o`
commands), aligns partitions to 1 MiB by default, and can wipe stale
filesystem signatures when re-partitioning.

It is often confused with `gdisk`/`sgdisk` (the GPT-specialist tools), with
`parted` (GNU, scriptable, live-resize oriented), and — critically — with its
own kernel-side effects: writing the table is not the same as the kernel
re-reading it.

| Field | Value |
| --- | --- |
| Package | fdisk (Debian bookworm) |
| Section (man) | 8 |
| Path | /usr/sbin/fdisk |
| Lineage | MS-DOS FDISK heritage; Linux version since the early 1990s (util-linux, libfdisk rewrite) |
| Standards | None — implements de-facto on-disk formats (MBR spec, UEFI GPT spec) |

## Synopsis

```
fdisk [options] <disk>
fdisk -l [<disk>...]
```

The two everyday shapes:

```
fdisk -l                       # list partition tables of all disks
fdisk /dev/sdb                 # open interactive editor on /dev/sdb
fdisk -x /dev/sdb              # list including detailed (expert) info
```

## How It Works

### What a partition table is

For MBR, the first sector (LBA 0) of the disk holds 512 bytes: bootstrap code
(446 bytes), four 16-byte partition entries, and the `0x55AA` signature:

```
MBR sector (LBA 0), 512 bytes
┌───────────────────────────────────────────────┐
│ 446 B bootstrap code (grub stage1, ...)       │
│ 16 B entry 1  (boot flag, CHS, type, LBA, sz) │
│ 16 B entry 2                                  │
│ 16 B entry 3                                  │
│ 16 B entry 4                                  │
│ 2 B signature 0x55AA                          │
└───────────────────────────────────────────────┘
   primary partitions: max 4 → one may be *extended*,
   containing a chain of *logical* partitions (numbered 5+)
```

GPT replaces this with a protective MBR (so legacy firmware sees one huge
"unknown" partition), a header with disk/partition UUIDs, and 128 default
partition entries — plus a **full backup copy** of header and entries at the
end of the disk, protected by CRC32 checksums.

### The fdisk interaction model

`fdisk <disk>` loads the on-disk table into memory and presents a
single-letter command prompt. Every command edits the *copy*; the disk is
written only by `w`:

```
in-memory table ──(d,n,t,a,...)──► in-memory table ──w──► disk + kernel sync
                          │                                    │
                          q = discard ──────────► (nothing written)
```

On `w`, fdisk writes the table and asks the kernel to re-read it
(`BLKRRPART`). If any partition of the disk is in use, the kernel may refuse —
fdisk tells you to reboot (or, smarter, run `partx -u`).

### The interactive command set

| Command | Action |
| --- | --- |
| `m` | Help — the full menu |
| `p` | Print the in-memory table |
| `n` | New partition (prompts: type, number, first/last sector) |
| `d` | Delete a partition (by number) |
| `t` | Change a partition's type (sysid; `L` lists all) |
| `a` | Toggle the bootable flag (MBR only) |
| `o` | Create a new empty **MBR/DOS** table |
| `g` | Create a new empty **GPT** table |
| `G` | Create a new empty SGI table; `s` Sun; `e`? (platform variants) |
| `i` | Change a GPT partition's name/UUID (`c` changes GPT name) |
| `u` | Toggle units (modern fdisk defaults to sectors) |
| `x` | Expert menu (extra attributes, geometry) |
| `v` | Verify the table (overlap/consistency checks) |
| `w` | Write table to disk and exit |
| `q` | Quit without writing |
| `F` | List free (unpartitioned) space |

Creating a partition is a four-question dialog: partition type (primary /
extended / logical), number, first sector (accept the alignment default!), and
size (sectors, or `+size{K,M,G,T,P}` syntax, or `Enter` for the rest).

### Alignment and the 1 MiB rule

Modern fdisk starts the first partition at sector **2048** (= 1 MiB with
512-byte sectors), not sector 63 as the old tools did. This aligns to SSD
erase-block boundaries, RAID stripe widths, and 4K-sector emulation, and
removes write-amplification penalties. When you answer "first sector" with
Enter, you are accepting this alignment — overriding it manually is one of the
classic self-inflicted performance wounds.

### MBR vs GPT: what changes in practice

| Aspect | MBR | GPT |
| --- | --- | --- |
| Max partitions | 4 primary (or 3+1 extended + many logical) | 128 by default |
| Max disk (512B sectors) | 2 TiB (32-bit LBA × 512 B) | effectively unlimited (64-bit LBA) |
| Integrity | single copy, no checksums | CRC32, primary + backup header |
| Boot flag | `a` toggles 0x80 (legacy BIOS) | irrelevant (UEFI boots ESP, type `ef00` in gdisk terms / EFI System in fdisk) |
| Kernel type codes | numeric (83 Linux, 82 swap, 8e LVM, 7 NTFS, c FAT32, ef EFI) | GUIDs with friendly names |

The 2 TiB line is the interview staple: 32-bit starting-LBA/size × 512-byte
sectors = 2^32 × 2^9 = 2 TiB. Bigger disks (or 4Kn sectors) require GPT —
which is why `g` exists and why post-2010 installers default to it on UEFI.

### The kernel sync problem

After `w`, the kernel re-reads the table. If the disk is busy (mounted
partitions, active swap), the re-read fails and fdisk prints the historic
"re-read table failed ... you should reboot" warning. The correct modern fix:

```bash
sudo partx -u /dev/sdb     # or partprobe: re-read table into kernel
lsblk /dev/sdb             # verify the view
```

### Scriptability

`fdisk` accepts its dialog on stdin, which enables crude automation — but the
maintained interface for scripting is `sfdisk`:

```bash
# scripted MBR creation via heredoc (works, but sfdisk is the real tool)
sudo fdisk /dev/sdb <<'EOF'
o
n
p
1


t
8e
w
EOF
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-l, --list` | List partition tables (all disks, or the given ones) and exit |
| `-x, --list-details` | Like `-l` plus detailed/expert information per partition |
| `-o <cols>, --output` | Choose columns for `-l` output (e.g. `-o +UUID,NAME`) |
| `-u, --units` | Units for output (sectors default; C/H/S legacy) |
| `-b <size>, --sector-size` | Assume the given sector size (512/1024/2048/4096) |
| `-C/-H/-S <n>` | Override legacy C/H/S geometry (rarely useful today) |
| `-t <type>, --type` | Expect a specific label type (dos/gpt/...) instead of probing |
| `-c <mode>, --compatibility` | `dos` or `nondos` alignment/compat mode |
| `-w <mode>, --wipe` | How to handle old signatures: auto/always/off |
| `-W <mode>, --wipe-partitions` | Wipe stale signatures found in *new* partitions |
| `-L <when>, --color` | Colorize (auto/always/never) |
| `-s <part>, --size` | Print partition size in blocks (deprecated → `blockdev --getsize64`) |

## Usage Patterns

```bash
# Inventory all disks and their partition tables
sudo fdisk -l
```

```bash
# Detailed listing of one disk, chosen columns
sudo fdisk -l -o Device,Start,End,Sectors,Size,Type,Type-UUID /dev/sdb
```

```bash
# Start an interactive session (read-only until you answer w!)
sudo fdisk /dev/sdb
#   then: p → n → ... → w
```

```bash
# Convert a disk to GPT (interactive): 'g' then 'n' etc.
sudo fdisk /dev/sdb
#   Command: g   → new empty GPT
```

```bash
# Make a partition type Linux LVM (MBR code 8e)
sudo fdisk /dev/sdb
#   t → partition 1 → 8e → w
```

```bash
# Scripted creation of one primary partition using all space (MBR)
sudo fdisk /dev/sdb <<'EOF'
o
n
p
1


w
EOF
```

```bash
# Check for consistency problems before writing (overlap detection)
sudo fdisk /dev/sdb
#   v → verify; q → discard
```

```bash
# See unpartitioned gaps on the disk (F inside fdisk, or:)
sudo fdisk -l /dev/sdb && lsblk -f /dev/sdb
```

```bash
# Back up a table before touching it (restore with: sudo sfdisk /dev/sdb < bak)
sudo sfdisk -d /dev/sdb > sdb-table.bak
```

```bash
# After an external table edit, refresh the kernel view
sudo partx -u /dev/sdb && lsblk /dev/sdb
```

```bash
# Work on a disk image file (VM/container images are just files)
fdisk -l rootfs.img          # fdisk reads tables from image files fine
```

## Nuances and Gotchas

- **`w` is the point of no return — and `o`/`g` inside fdisk already ask about
  wiping signatures.** Creating a fresh label (`o`/`g`) prompts to remove
  existing signatures; careless "Y" answers have destroyed data long before
  any write to a "real" partition.
- **fdisk never creates filesystems.** It writes tables only; a partition with
  type `83` and no `mkfs` is just reserved space. Type codes are *labels*,
  not enforcement — a partition labeled swap can still hold ext4.
- **The bootable flag barely matters now.** Legacy BIOS boot needs the 0x80
  flag on the right disk; UEFI ignores it and boots the EFI System Partition.
  Toggling `a` on the wrong disk was a classic "system won't boot" cause.
- **Extended/logical numbering.** Logical partitions start at 5 and consume a
  primary slot for their extended container; deleting the extended partition
  deletes all logical ones inside it.
- **Sector-size assumptions.** `-b` matters on 4Kn disks and some USB
  enclosures; misreading sector size misstates all sizes. Trust `-l`'s
  "Sector size" line.
- **Kernel re-read failures.** "Partition table changes will not be visible
  until reboot" is about the *kernel view*, not about fdisk failing to write.
  `partx -u`/`partprobe` usually avoids the reboot.
- **GPT backup header after cloning/shrinking.** `dd`ing a disk onto a smaller
  one truncates the backup GPT; fdisk will complain and offer to fix —
  understand what it is repairing before answering.
- **Stale signatures.** Re-partitioning over an old filesystem leaves
  superblock remnants; fdisk's `-w`/`-W` wipe logic (and `wipefs`) exist
  because the kernel or mkfs may otherwise detect the *old* signature.
- **In-use disks.** fdisk will happily edit a table for a disk whose
  partitions are mounted — the damage happens at `w` + `partx` time or,
  worse, works "fine" until reboot. Unmount first in production.
- **Root required.** Writing tables needs `CAP_SYS_ADMIN`; `fdisk -l` on
  modern systems can read as non-root, but the editor needs privileges.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success (including read-only listings) |
| 1 | Failure — cannot open the disk, permission denied, bad label type, or I/O error |

## Related Commands

- [`sfdisk`](./sfdisk.md) — the scriptable sibling; table dump/restore (`sfdisk -d | sfdisk`)
- [`cfdisk`](./cfdisk.md) — curses front-end to the same libfdisk engine
- [`lsblk`](./lsblk.md) — post-edit verification of the kernel's partition view
- [`blkid`](./blkid.md) — signature/UUID probing; reveals stale filesystem remnants
- [`delpart`](./delpart.md) — kernel-side partition surgery (BLKPG) without touching the table
- [`findfs`](./findfs.md) — resolve a filesystem by UUID/LABEL after repartitioning
- [`overview`](./overview.md) — index of all util-linux collection pages
- [permissions](../../admin/permissions.md) — root/CAP_SYS_ADMIN requirements for table writes
- [internals](../../internals.md) — how the block layer, sectors and kernel partition objects interact

## Interview Questions

### Q: Why does MBR cap disks at 2 TiB, and what is fdisk's answer?

MBR partition entries store start and size as 32-bit sector counts; with
512-byte sectors that is 2^32 × 512 B = 2 TiB. The fix is GPT: 64-bit LBAs,
UUIDs, checksummed primary+backup structures, and 128 default partitions.
Inside fdisk the choice is the `g` (GPT) versus `o` (MBR/DOS) command.

### Q: Explain the difference between primary, extended, and logical partitions.

MBR offers four primary slots. To get more, one slot becomes an *extended*
partition — a container whose on-disk chain of EBR sectors describes *logical*
partitions, numbered from 5. The extended slot itself holds no filesystem; a
disk typically has 3 primaries + 1 extended with N logicals. GPT abolishes the
distinction entirely.

### Q: What exactly happens when you press 'w' in fdisk?

fdisk serializes the in-memory table to the disk (MBR sector 0, or the GPT
header/entry blocks plus protective MBR), then issues a kernel re-read
(BLKRRPART). If the kernel refuses because partitions are in use, the disk
*is* re-partitioned on disk but the running system still shows the old view —
resolved with `partx -u`/`partprobe` or a reboot. Nothing is written before
`w`; `q` discards all edits.

### Q: How do you script fdisk, and what is the better tool?

fdisk reads its single-letter dialog from stdin (heredoc/echo), which works
but is brittle: prompts change with disk state. The maintained scriptable
interface is `sfdisk` — text-format table descriptions, `sfdisk -d` to dump a
table for backup, `sfdisk <table file>` to restore. For GPT scripting,
`sgdisk` is the specialist. fdisk itself is best treated as interactive.

### Q: Why do modern fdisk versions start the first partition at sector 2048?

1 MiB alignment: it guarantees alignment to SSD erase blocks, 4K-sector
emulation, and RAID stripes regardless of the underlying geometry, avoiding
read-modify-write amplification. Legacy tools started at sector 63 for CHS-era
reasons; the 1 MiB default (and Enter-accepts-alignment dialog) is the modern
convention.

### Q: You cloned a 2 TiB disk onto a 1 TiB disk with dd and fdisk now warns about the partition table. What happened?

GPT keeps a backup header and entry array in the *last* sectors of the disk;
the clone truncated them away. fdisk (and gdisk) detect the missing backup and
offer to rebuild it at the new end-of-disk — the fix is to let it repair, then
verify with `v` and adjust/keep partition sizes accordingly. This is why
table-aware cloning (sfdisk dump/restore, gdisk) beats raw dd for size changes.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/fdisk/fdisk.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
