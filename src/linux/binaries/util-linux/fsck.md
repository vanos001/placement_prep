# fsck — front end for filesystem consistency checkers

## Overview

`fsck` is the front end for the per-filesystem checkers (`fsck.ext4`, `fsck.xfs`, `fsck.minix`, ...) that verify and optionally repair filesystem structures. You rarely invoke `fsck.ext4` directly in system bookkeeping because `fsck` adds the operationally important layer: it maps a device to the right checker by type, walks `/etc/fstab` in `fs_passno` order with `-A`, serializes or parallelizes checks sensibly, refuses mounted filesystems, and aggregates helper exit codes into the well-known fsck code table.

It ships in the `util-linux` package at `/usr/sbin/fsck`; the actual checkers come from the filesystem packages (`e2fsprogs` provides `fsck.ext2/3/4`, `xfsprogs` provides `fsck.xfs`, util-linux itself provides `fsck.minix` and `fsck.cramfs`). Reach for it after unclean shutdowns, on filesystems flagged dirty, or during scheduled maintenance windows — always on unmounted or read-only-mounted volumes. It is often confused with the helpers it calls (whose flags like `-y`/`-f` pass straight through) and with `badblocks` (surface scan, not structural repair).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/fsck |
| First appeared | AT&T/BSD heritage; present in Linux distributions since the early 1990s |
| Standards | LSB defines the fsck front-end contract |

## Synopsis

```
fsck [options] -- [fs-options] [<filesystem> ...]
```

Common one-line forms:

```
fsck /dev/sdb1                 # check one filesystem (type inferred/asked)
fsck -A                        # check everything per /etc/fstab pass numbers
fsck -AR                       # fstab sweep, skip the root filesystem
fsck -t ext4 -y /dev/sdb1      # limit type; -y falls through to fsck.ext4
fsck -N -A                     # dry run: print the command plan, touch nothing
```

## How It Works

### Dispatcher, not checker

`fsck` contains no filesystem logic. For each operand it determines the filesystem type (explicit `-t`, the fstab entry, or the type suffix of the device argument) and searches for a checker named `fsck.<type>`, trying `PATH` first and then `/sbin`. If no checker exists for a type, fsck reports `fsck.<type> not found` and continues with the remaining operands.

```
                    ┌────────────────────────────┐
   fsck -A ───────► │ read /etc/fstab            │
                    │ order by fs_passno         │
                    └─────────┬──────────────────┘
              passno 1        │        passno ≥ 2
         (root, serial)       │    (rest, parallel)
                    ┌─────────▼──────────┐
                    │ for each entry:    │
                    │  mounted? -M skip  │
                    │  type in -t list?  │
                    └─────────┬──────────┘
                              ▼
              exec /sbin/fsck.<fstype> dev [fs-options]
                              │
              exit codes OR'ed into fsck's own status
```

### The fstab contract

The fifth field of `/etc/fstab`, `fs_passno`, drives `-A`:

```
0    never checked by fsck -A
1    checked first, serially — normally only the root filesystem
2+   checked after pass 1, in parallel with each other
```

At boot this contract is honored by systemd (`systemd-fsck-root.service`, then `systemd-fsck@.service` for pass-2 entries), which is why a fstab with all-1 pass numbers serializes your boot.

### Options fall through

Flags that fsck itself does not know are passed verbatim to the helper after the device. That is how `fsck -y /dev/sdb1` reaches `e2fsck -y`, and why `fsck` understands `--` to separate its own flags from helper flags (`fsck -a -- -f /dev/sdb1`).

```bash
$ fsck -N /dev/null
fsck from util-linux 2.38.1
[/usr/sbin/fsck.ext2 (1) -- /dev/null] fsck.ext2 /dev/null
$ fsck /dev/null
fsck from util-linux 2.38.1
fsck: error 2 (No such file or directory) while executing fsck.ext2 for /dev/null
```

The `-N` run shows the exact helper line fsck would execute; the second shows a helper resolution failing (this container has no `fsck.ext2`) — fsck continues with other operands and encodes the failure in its exit status.

With `-V` the same bracketed plan line is printed while the check actually runs:

```
[/usr/sbin/fsck.ext4 (1) -- /dev/sdb1] fsck.ext4 -y /dev/sdb1
│                     │  │             │
│                     │  └─ fstab pass number
│                     └─ device as fsck resolved it
└─ helper fsck resolved from PATH, then /sbin
```

The parenthesized number is the fstab pass — the same ordering `-A` uses. Reading one `-V` line tells you everything about how the dispatcher saw your setup: helper path, pass, device, and the fall-through flags.

### What the helpers do (ext-family sketch)

`e2fsck` walks the inode table in passes — inode/block/sizes, directory structure, connectivity, reference counts, group summaries — replaying the journal first if needed. Journaling filesystems make routine fsck rare: an unclean ext4 is usually fixed by journal replay at mount time, and fsck is for detected inconsistencies. XFS's `fsck.xfs` is deliberately a no-op stub so that fstab pass fields do not break; real XFS repair is `xfs_repair`.

### fsck in the boot chain

On a systemd system the fstab contract is executed by units, not a shell script: `systemd-fsck-root.service` handles the pass-1 root check before it is remounted writable, and `systemd-fsck@.service` instances run for each pass-2 device. Consequences worth knowing:

- a failed boot-time fsck drops the system to emergency mode rather than "fixing" interactively;
- `fsck.mode=force` / `fsck.repair=yes` on the kernel command line ask the boot-time check to run forced/automatic repairs;
- filesystems with `passno 0` are skipped entirely by both fsck -A and the boot units.

So the same fstab field drives three behaviors: `fsck -A` sweeps, systemd's boot checks, and the serial/parallel split.

## Options That Matter

### Front-end options

| Option | Effect |
| --- | --- |
| `-A` | Check all filesystems in `/etc/fstab`, ordered by `fs_passno` |
| `-R` | With `-A`: skip the root filesystem |
| `-P` | With `-A`: check the root filesystem in parallel too (legacy/dangerous) |
| `-s` | Serialize checking (one helper at a time) |
| `-M` | Skip filesystems that are currently mounted |
| `-l` | Lock the device with an exclusive flock(2) to bar concurrent fsck runs |
| `-t <list>` | Restrict types, comma-separated; `no` prefix negates (`-t noext4`) |
| `-C [<fd>]` | Show progress bar (helper must support the progress-fd protocol) |
| `-N` | Dry run: print what would be executed, run nothing |
| `-r [<fd>]` | Report per-device statistics |
| `-T` | Omit the `fsck from util-linux ...` title |
| `-V` | Verbose: explain what is being done |
| `--` | Separator: everything after goes to the filesystem-specific checker |

### Commonly passed-through helper options

| Option | Effect (ext-family/e2fsck semantics) |
| --- | --- |
| `-y` | Answer yes to every repair prompt |
| `-n` | Read-only check: report, repair nothing |
| `-f` | Force a full check even if the superblock says clean |
| `-p` | "Preen": fix trivially-safe errors non-interactively, else exit |
| `-b <blk>` | Use the given superblock copy (e.g. `-b 32768` when primary is gone) |
| `-B <size>` | Override block size when probing |

## Usage Patterns

```bash
# Check one unmounted data disk non-interactively
fsck -y /dev/sdb1

# Dry run: see exactly which helpers would run for the whole fstab
fsck -N -A

# Full fstab sweep during maintenance, but leave the root fs alone
fsck -AR

# Only ext-family filesystems, forced full check, auto-yes
fsck -t ext2,ext3,ext4 -y -- -f /dev/sdb1 /dev/sdc1

# A filesystem the kernel flagged dirty (dmesg: "EXT4-fs error ...")
umount /dev/sdc1 && fsck -f /dev/sdc1

# Progress bar on a big volume
fsck -C0 -y /dev/sdb2

# Check a filesystem image file (loop-mounted later)
fsck -t ext4 /srv/images/rootfs.img

# Skip anything already mounted (scripted safety)
fsck -AM

# Find the alternate superblock when the primary is trashed
mke2fs -n /dev/sdb1        # prints where backups WOULD be (no writes)
fsck -b 32768 /dev/sdb1

# Lock the device so two operators cannot fsck at once
fsck -l /dev/sdb1

# See exactly which helpers a full -A sweep would run, per pass
fsck -NV

# ext4: answer 'no' to everything — pure diagnosis, zero mutation
fsck -t ext4 -n /dev/sdb1

# Root-fs style repair from a rescue image (fs unmounted there)
fsck -y /dev/vg0/root

# Verify an ext4 image before loop-mounting it
fsck -t ext4 /srv/images/disk.img && mount -o loop /srv/images/disk.img /mnt
```

## Nuances and Gotchas

- **Never check a mounted read-write filesystem.** Concurrent repair against kernel writes corrupts data. Helpers usually refuse; `-M` makes the front end skip mounted entries; do it from rescue/initramfs for the root fs.
- **`-A` exit codes are OR'ed, not summed.** With several filesystems checked, fsck's status is the bitwise OR of helper codes. `1|4 = 5` means "some fs corrected, some left uncorrected" — a single number can encode multiple facts, and scripts must test bits, not equality.
- **`fsck.xfs` does nothing on purpose.** XFS relies on journal replay at mount and `xfs_repair` offline; the stub exists only so fstab pass-2 entries don't error. Interviewers like this one.
- **"Clean" short-circuits.** Journaling filesystems mark themselves clean; a plain `fsck` on a clean ext4 exits almost instantly without deep checking. `-f` (passed to the helper) forces the full pass structure — needed after suspicious behavior even when the flag says clean.
- **Parallelism is by fstab design, not accident.** Pass-1 entries (root) run first and serially; pass-2+ run concurrently. A fstab where every fs has passno 1 turns your boot and `-A` sweeps into a serial crawl.
- **The root filesystem cannot be repaired live.** Boot-time checking (systemd) or an initramfs/rescue environment handles it; `-R` exists for exactly the "fix all data disks, skip root" sweep.
- **Flag namespace is shared with helpers.** `fsck -y`, `-n`, `-a`, `-p` are not fsck options — they fall through. If you pass a helper flag fsck *does* define (e.g. `-s` = serialize, not e2fsck's old swap-metadata mode), you get fsck's meaning. Use `--` for clarity.
- **Btrfs has no offline fsck.** `fsck.btrfs` is another stub; online scrub (`btrfs scrub`) is the integrity mechanism. "Which filesystems cannot be fscked?" is a standard systems-interview question.
- **Progress needs cooperation.** `-C` only shows a bar if the helper speaks the progress-fd protocol (e2fsck does). On other filesystems the option is silently useless.
- **Type inference has fallbacks.** With no `-t` and no fstab entry, fsck guesses from the device name suffix (e.g. `.ext4` in the devnode) and finally asks or defaults — an fstab with correct `fstype` values removes the guesswork entirely.
- **fsck is not badblocks.** Surface-level media defects are the domain of `badblocks -sv` or e2fsck's `-c` (which runs badblocks and records results); a "clean" fsck says nothing about failing flash or pending SMART sectors. Pair both in maintenance runbooks.

## Exit Status

Documented for the front end; per-filesystem codes are OR'ed under `-A`:

| Code | Meaning |
| --- | --- |
| 0 | No errors |
| 1 | Filesystem errors corrected |
| 2 | System should be rebooted |
| 4 | Filesystem errors left uncorrected |
| 8 | Operational error (fsck itself failed, e.g. can't run helper) |
| 16 | Usage or syntax error |
| 32 | Canceled by user request |
| 128 | Shared-library error |

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`fsck.cramfs`](./fsck.cramfs.md) — the read-only cramfs checker dispatches through this front end.
- [`fsck.minix`](./fsck.minix.md) — util-linux's own checker for Minix filesystems.
- [`fsfreeze`](./fsfreeze.md) — quiesce writes for a consistent snapshot instead of a repair run.
- [`mkfs`](./mkfs.md) — builds the filesystems fsck then polices.
- [`mount`](./mount.md) — journal replay and the clean flag make live checks unnecessary.
- [`losetup`](./losetup.md) — attach image files before `fsck -t ext4 image.img`.
- [`flock`](./flock.md) — the syscall behind `fsck -l` device locking.
- [`systemd`](../../admin/systemd.md) — boot-time fsck units and the fs_passno contract.
- [`internals`](../../internals.md) — superblocks, journals, and bitmaps being verified.

## Interview Questions

### Q: What do the fstab fields tell fsck, and what does pass number 0, 1, and 2 mean?

The sixth field, fs_passno: 0 means never fsck'd by `-A`; 1 means check first and serially (reserved for root); 2 and higher are checked after pass 1 and in parallel with each other. systemd honors the same contract at boot via its fsck units, so pass numbering affects both `fsck -A` maintenance runs and startup latency.

### Q: fsck -A returns 5. What happened?

Bitwise OR of helper exit codes: 5 = 1 | 4, so at least one filesystem had errors corrected and at least one had errors left uncorrected. You must look at the logs to see which volume needs a second, probably interactive, pass — the number alone encodes multiple conditions.

### Q: Why does fsck.xfs exist if it checks nothing?

XFS repairs metadata with `xfs_repair` when unmounted and replays its journal at mount time; there is no fsck-style checker. The `fsck.xfs` stub exists so that `/etc/fstab` entries with a nonzero pass number and generic tooling that invokes `fsck <dev>` do not fail on XFS volumes. Btrfs follows the same pattern with `fsck.btrfs` plus online `btrfs scrub`.

### Q: A filesystem is flagged dirty after a crash but mounts fine. Do you still fsck?

Usually the journal replay at mount time fixed the metadata, and fsck is unnecessary. But if dmesg showed filesystem errors, applications see corruption, or you want certainty, unmount (or remount read-only) and run a forced check (`fsck -f`) — the clean flag alone is not proof of integrity, only that the journal replay completed.

### Q: How would you check the root filesystem of a running server?

You cannot repair a mounted read-write root; options are: schedule a boot-time check (touch /forcefsck-style mechanisms, systemd-fsck-root, or fstab passno 1), boot a rescue image/initramfs and run fsck there, or remount read-only if the environment permits it. The answer interviewers want: repair of the root fs happens before it is mounted rw, always.

### Q: What is the role of the `-l` flag and how does it relate to the flock tool?

`fsck -l` takes an exclusive `flock(2)` lock on the device so that two concurrent fsck runs (two admins, a script and an operator) cannot repair simultaneously — the same advisory-lock mechanism the `flock` command exposes for shell scripts. It is whole-device serialization for exactly the hazard fsck poses.

### Q: You inherit a fstab where every filesystem has pass number 1. What are the operational consequences and your fix?

Both `fsck -A` and the systemd boot units will check every filesystem serially, first — turning boot and maintenance sweeps into the sum of all check times instead of the max. The fix is the documented contract: root gets pass 1, everything else 2 (pass 0 only for special cases that must never be checked), letting the checker parallelize pass-2 volumes. Then `fsck -NV` to verify the plan before the next maintenance window.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/fsck.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
