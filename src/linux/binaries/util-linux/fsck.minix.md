# fsck.minix — checker/repairer for Minix filesystems

## Overview

`fsck.minix` performs consistency checks — and repairs — on Minix filesystems, the tiny filesystem from Andy Tanenbaum's MINIX teaching OS that Linux 0.x initially used. It is a self-contained checker in util-linux (`/usr/sbin/fsck.minix`) with no external dependencies, capable of listing filenames, dumping superblock state, and repairing interactively or automatically. Today its practical role is educational (watch a real filesystem checker work at a readable scale), plus niche uses: floppy/embdedded images, OS-course assignments, and initrd archaeology.

It ships in the `util-linux` package and plugs into the `fsck` front end (`fsck -t minix <dev>`). It is often confused with `fsck.cramfs` (the other util-linux-internal checker — but cramfs is read-only, while minix is writable and this tool genuinely repairs), and with `fsck.ext4`'s machinery, whose pass structure it predates in miniature.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/fsck.minix |
| First appeared | Minix filesystem 1987; checker present in Linux userspace since the early 1990s |
| Standards | None (legacy/teaching filesystem) |

## Synopsis

```
fsck.minix [options] <device>
```

Common one-line forms:

```
fsck.minix -l /dev/fd0          # list all filenames on the filesystem
fsck.minix -a /dev/fd0          # auto-repair everything non-interactively
fsck.minix -r /dev/fd0          # interactive repair, prompt per fix
fsck.minix -s /dev/fd0          # print superblock information
```

## How It Works

### The on-disk structures it reconciles

A Minix filesystem is a textbook layout: everything is accounted by two bitmaps and an inode table, which is why it is the standard vehicle for teaching filesystem internals — and why a checker can be a few thousand lines instead of a hundred thousand.

```
Block:  1             2                3               4..N          N+1..
      ┌─────────┬─────────────────┬────────────────┬─────────────┬──────────┐
      │ super   │ inode bitmap    │ zone bitmap    │ inode table │ data     │
      │ block   │ (which inodes   │ (which data    │ (mode,uid,  │ zones    │
      │         │  are in use)    │  blocks free)  │  size,zone[])│          │
      └─────────┴─────────────────┴────────────────┴─────────────┴──────────┘
```

`fsck.minix` cross-checks these redundant records against each other and against the actual trees:

- every zone referenced by an inode is marked in the zone bitmap, exactly once;
- every inode is reachable from the root directory (no orphans) and its link count matches the directory references;
- directory entries `.` and `..` exist and point where they should;
- block sizes, file sizes, and mode fields are sane; duplicate zone references are flagged;
- filenames conform to Minix rules (V1: 14 characters, later versions: 30).

### Check, then repair — in three modes

The tool distinguishes checking from repairing, and repairing has two temperaments:

```
-l / --list      print all filenames; no modification
   (default)     check only: report inconsistencies, exit status counts them
-a / --auto      repair automatically, no prompts (implies list-style output)
-r / --repair    repair interactively, prompting for each fix
-f / --force     check even if the superblock claims the fs is clean
```

Repairs include clearing unreferenced inodes/zones (the classic `Free inode ...` / `Connect lost ...` output of fsck lore), fixing link counts, rebuilding `.`/`..` entries, and marking freed zones in the bitmap. Like all checkers, it must run on an *unmounted* device; checking a live filesystem races the kernel and manufactures the very corruption it hunts.

### The structures it reads, field by field

`fsck.minix` never asks the kernel for help — it opens the device and reconstructs the filesystem picture with plain `pread(2)`/`pwrite(2)`, exactly the picture the kernel's `fs/minix` driver would build at mount time. The superblock it validates carries (v1 layout, 16-bit fields unless noted):

```
s_ninodes        inodes provisioned at mkfs time
s_nzones         device size in zones (16-bit here -> the ~64 MiB v1 ceiling)
s_imap_blocks    inode bitmap size, in blocks
s_zmap_blocks    zone bitmap size, in blocks
s_firstdatazone  first zone usable for file data
s_log_zone_size  log2 of the zone/block ratio
s_max_size       maximum file size the format can express
s_magic          selects version AND name-length dialect
s_state          state flags: bit 0 = cleanly unmounted, bit 1 = errors seen
```

Each inode holds seven direct zone pointers plus an indirect chain (v1: single + double indirect; v2/v3 add a triple), which is how the format reaches its per-file size ceiling. The check walk is therefore pure bookkeeping reconciliation: read the inode table, mark zone-bitmap bits as inodes claim zones (flagging doubles), follow indirect blocks, count directory references against link counts, and finally compare the rebuilt bitmaps with the on-disk ones. Every mismatch is one "error" toward the exit count.

### Who guards against mounted filesystems

Not the helper: `fsck.minix` performs no mounted-check itself. The front end offers `fsck -M` (skip mounted devices, return 0 for them) and takes a whole-disk `flock(2)` (`/run/fsck/<disk>.lock`) so parallel front-end runs don't collide — but that lock is the front end's, not the helper's. A direct `fsck.minix -a` on a live device sails straight through; scripts must enforce their own unmounted precondition.

### The pass order

```
read superblock ──► sanity: magic? counts consistent? sizes in range?
      │                     │ bad ──► report, exit (8/16)
      ▼ ok
walk inode table ──► per inode: zone refs ──► mark zone bitmap
      │                     │ double claim ──► "already used" error
      │                     │ out of range ──► error, zone dropped
      ▼
follow directories ─► count refs per inode, verify . and ..
      │                     │ unreachable inode ──► "lost" (repair: clear)
      ▼
compare rebuilt bitmaps vs on-disk ──► fix counts/flags (repair modes)
      ▼
exit = number of unresolved errors (0..7, 8, 16)
```

Reading the flow top-down explains the repair vocabulary: a zone claimed twice is a *cross-link*; an inode no directory references is a *lost* inode; a link count that disagrees with the reference count is the third classic class. All three come from the same reconciliation, just reported at different checkpoints.

### Generation semantics worth knowing

Minix V1 limits names to 14 characters and the filesystem to a few dozen MiB; V2/V3 raise name length (30 chars) and size into the low GiB range, but all versions remain tiny compared to modern filesystems. The `-m` flag enables extra Minix-specific warnings (e.g. about portability of filenames/modes), and `-s` dumps the superblock: inode/zone counts, block size, and state flags — the first thing to read when a check reports a "clean" fs that misbehaves.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-l, --list` | List all filenames found on the filesystem |
| `-a, --auto` | Perform automatic (non-interactive) repairs |
| `-r, --repair` | Perform interactive repairs, prompting per inconsistency |
| `-v, --version` | Show version |
| `-m` | Activate Minix-specific "warn mode" (extra warnings) |
| `-s, --super` | Output super-block information (block size, inode/zone counts, state) |
| `-f, --force` | Force checking even if the filesystem is marked clean |

Note the inversion trap versus the ext-family helpers: here `-r` means interactive *repair*, while e2fsck's repair-everything flag is `-y`; and `-a` here is auto-repair, not "check all".

## Usage Patterns

```bash
# Create a Minix fs on a floppy image and inspect it (classic lab exercise)
dd if=/dev/zero of=minix.img bs=1024 count=1440
mkfs.minix minix.img
mount -o loop minix.img /mnt/m && cp notes.txt /mnt/m/ && umount /mnt/m

# List every filename on the image without touching it
fsck.minix -l minix.img

# Read-only consistency check; exit status = unrepaired errors
fsck.minix minix.img; echo "status=$?"

# Superblock state: sizes, counts, dirty flag
fsck.minix -s minix.img

# Interactive repair of a deliberately corrupted image
dd if=/dev/urandom of=minix.img bs=1 count=64 seek=1024 conv=notrunc
fsck.minix -r minix.img

# Non-interactive repair for scripts/embedded init
fsck.minix -a /dev/mtdblock3

# Force a check even though the superblock says clean
fsck.minix -f minix.img

# Through the generic front end
fsck -t minix minix.img
```

```bash
# Snapshot-then-repair: never auto-repair the only copy
cp minix.img minix.img.bak && fsck.minix -a minix.img

# Watch the superblock state change across a repair
fsck.minix -s minix.img; fsck.minix -a minix.img; fsck.minix -s minix.img

# Front-end wrapper adds lock discipline for concurrent checks
fsck -t minix -l /dev/fd0        # -l: flock the whole disk while checking

# Distinguish "clean" from "consistent" and count what remains
fsck.minix -f minix.img; echo "unrepaired errors: $?"

# CI check: fail the job only on unresolved errors, not on usage accidents
out=$(fsck.minix -a image.img 2>&1); rc=$?
[ "$rc" -ge 1 ] && [ "$rc" -le 7 ] && { echo "$out"; exit 1; } || true

# Which dialect is this image? magic byte tells version before any check
fsck.minix -s image.img | head -5    # prints version, sizes, state
```

## Nuances and Gotchas

- **Unmounted only.** Same rule as every fsck: mounting a Minix fs while `fsck.minix -a` runs corrupts it. On images, `umount` before checking or check the image file directly while unmounted.
- **Flag collisions with fsck.ext-family muscle memory.** `-a` (auto-repair here) vs e2fsck's `-p` preen; `-r` (interactive repair here) vs e2fsck's... `-r` is statistics there. Scripts mixing helper conventions produce dangerous surprises — check the man page of the exact helper.
- **It can lose data when repairing.** Auto-repair frees inodes/zones it cannot reconnect; orphaned files are discarded rather than moved to `lost+found` (Minix filesystems have none). Snapshot the image before `-a`/`-r`.
- **Tiny limits are structural.** 14/30-char filenames, MiB-to-low-GiB ceilings, no journaling, no extent trees: any "modern" expectation (large files, long names, crash consistency) is out of scope. Don't deploy it beyond teaching/embedded.
- **"Clean" flag is advisory.** After a crash the state flag may still read clean if the crash window was benign; `-f` forces the full walk. Conversely a dirty flag does not mean data loss — it means "was not unmounted".
- **Exit status is the error count.** Unlike the fsck(8) front-end bit table, `fsck.minix` directly returns the number of *unrepaired* errors (mod 256) or the special operational/usage codes — so `status=3` means three unresolved inconsistencies, not a bitmask.
- **Busybox and other imitations.** Busybox ships a smaller `fsck.minix`; behavior/flags can differ subtly. For teaching material, use the util-linux version to match the man page.
- **No lost+found.** Unlike the ext family, recovered files are not re-linked anywhere; "connect lost" in repair mode either relinks them at a fixed name or drops them, depending on the fix — one more reason for image snapshots before repair.
- **Repair is not transactional.** Fixes are written in place with no undo log: a `-a`/`-r` run killed halfway can leave bitmaps and inode tables *more* inconsistent than before. The snapshot discipline above is not optional for anything you care about.
- **The state flags are the only crash record.** The superblock's state word (bit 0 = cleanly unmounted, bit 1 = errors seen while mounted) is all the format remembers between sessions; there is no journal to replay and no transaction metadata. `-a`/`-r` re-stamp a clean state on success, which is exactly why an interrupted repair can masquerade as a healthy filesystem afterwards.
- **Parallel checks need the front end.** Running two `fsck.minix` processes on devices of the same disk has no serialization at all; `fsck -l` (front-end flock) or your own lockfile is the only protection. Boot systems get this via fstab pass ordering instead.
- **`-v` is not "verbose" here.** On this helper `-v` means version; verbose-style output comes automatically with `-l`/`-a`/`-r`. Yet another case where the same letter means different things across the fsck family — verify per binary, never per family.
- **Image files are first-class devices.** Every example on this page works on a regular file because the helper only opens the path and reads/writes it; permissions of the *file* are the only gate. That makes lab workflows easy and also makes "I checked it while mounted" mistakes trivial — a loop-mounted image is a live filesystem even when the backing file is quiet.

## Exit Status

- `0` — no errors found (or all repaired).
- `1-7` — the count of errors that were found but *not* repaired (returned as-is, modulo 256 for larger counts).
- `8` — operational error (I/O failure, bad device, out of memory).
- `16` — usage or syntax error.

When invoked through the `fsck` front end, callers see the aggregated fsck(8) code table instead (`0/1/2/4/8/16/32/128`).

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`fsck`](./fsck.md) — the front end that dispatches `-t minix` devices here.
- [`fsck.cramfs`](./fsck.cramfs.md) — sibling util-linux checker; read-only, cannot repair.
- [`mkfs.minix`](./mkfs.minix.md) — builds Minix filesystems for this tool to police.
- [`mount`](./mount.md) — loop-mount images around the check → repair cycle.
- [`losetup`](./losetup.md) — attach raw image files as devices.
- [`internals`](../../internals.md) — bitmaps, inodes, and superblocks in their simplest real form.

## Interview Questions

### Q: Why teach filesystem internals with fsck.minix instead of fsck.ext4?

The Minix layout is the minimal redundant-accounting design: one superblock, an inode bitmap, a zone bitmap, an inode table, data zones. A checker that reconciles those five structures is small enough to read end-to-end, and every inconsistency class (lost inodes, cross-linked blocks, bad link counts, broken dot entries) appears at human scale. e2fsck implements the same concepts with a hundred-fold more code, extents, journals, and features.

### Q: What does exit status 3 from fsck.minix tell you, and how does that differ from fsck's front-end codes?

Directly, it means three errors were found and left unrepaired — the tool returns the unrepaired-error count. The `fsck` front end instead aggregates helpers into a documented bit table (0/1/2/4/8/16/32/128) and OR's multiple filesystems together. So the same underlying "three problems" surfaces as 3 from the helper and as 1 (errors corrected) or 4 (left uncorrected) style bits through fsck.

### Q: You found a "corrupted" minix.img in an archive. Walk through your handling.

Check it read-only first (`fsck.minix -s` for superblock state, then a plain check capturing the exit status), copy the image, repair the *copy* interactively with `-r` so each reconnect decision is human-reviewed, mount the repaired copy loop-mounted read-only to validate contents, and only then replace the original. Never auto-repair `-a` the only copy: Minix repair discards orphans rather than archiving them.

### Q: Why does fsck.minix have both -a and -r, and when would you choose each?

`-r` prompts per fix — appropriate when data is precious and an operator can judge each reconnect; `-a` applies the standard fixes without prompts — appropriate in embedded init scripts or lab grading where consistency of behavior beats per-case judgment. The tradeoff is exactly the one between interactive rescue tools and automated boot-time repair everywhere in Linux.

### Q: The superblock says the filesystem is clean, but users report missing files. What do you check?

Run `fsck.minix -f` — the clean flag only records that the fs was unmounted properly, not that content is consistent; a benign crash window or a prior buggy write can leave a clean-marked fs with lost zones. Also compare `-l` output against the expected file list, and inspect `-s` output for inode/zone counts that contradict the directory tree (e.g. files whose inodes were freed but directories never rewritten).

### Q: Why does fsck.minix return a raw error count instead of a bitmask like the fsck front end, and how do you normalize in scripts?

Because it checks exactly one filesystem, a scalar count is strictly more informative than bits: `3` says three unresolved inconsistencies, which a bitmask could not express. Normalization depends on the caller: treat `1-7` as "errors found" (specifics via stderr), `8`/`16` as operational failures, and if you route through the front end, switch to its bit tests (`status & 4` = uncorrected errors left) — a script that uses the same comparison for both paths misclassifies results.

### Q: Design question: what makes a filesystem checker small, and what features push the same problem to e2fsck's size?

A checker is small when the on-disk format is a small closed set of redundant structures: here, two bitmaps, an inode table, and directory trees that can all be recomputed from each other, with no journal to replay, no checksums to validate, and no dynamic features (extents, xattrs) whose invariants must also hold. Every feature that adds *another* thing that must agree with everything else — journal, extents, quotas, checksums, ACLs — multiplies the reconciliation passes. e2fsck is the same algorithm grown by feature count, not by conceptual complexity.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/fsck.minix.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
