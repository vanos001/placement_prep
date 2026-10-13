# fsck.cramfs — integrity checker for cramfs (compressed ROM) images

## Overview

`fsck.cramfs` verifies the internal consistency of a cramfs filesystem image — the compressed, read-only filesystem Linux uses for initramfs payloads, embedded/rootf images, and installer rescue media. Because cramfs is read-only *by design*, this tool cannot repair anything: it validates the superblock, the compressed data pages, and (with `--extract`) decompresses the entire image to prove every zlib stream is intact. A failed check means "rebuild the image with `mkfs.cramfs`", not "repair in place".

It ships in the `util-linux` package at `/usr/sbin/fsck.cramfs`, alongside its builder `mkfs.cramfs`. It also plugs into the `fsck` front end, which dispatches `fsck -t cramfs <image>` to it. It is often confused with `fsck.minix` (also a util-linux checker, but for a writable legacy filesystem) and with generic `fsck` behavior — the "repair" mental model simply does not apply to cramfs.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/fsck.cramfs |
| First appeared | cramfs entered Linux 2.4 (early 2000s); checker ships with util-linux since then |
| Standards | None (Linux/embedded-specific) |

## Synopsis

```
fsck.cramfs [options] <file>
```

Common one-line forms:

```
fsck.cramfs rootfs.cramfs                     # verify structure and superblock
fsck.cramfs -v --extract /tmp/check initrd    # decompress-test everything
fsck.cramfs -b 4096 rootfs.cramfs             # image was built with 4 KiB pages
```

## How It Works

### The cramfs layout it validates

A cramfs image is a flat, page-oriented structure: a small superblock, then metadata (inodes, directory data) and file content pages compressed with zlib, each independently decompressable so the page cache can satisfy reads without touching neighbors.

```
offset 0                    page-aligned blocks
┌──────────────┬────────────────────────────┬──────────────────────────┐
│ superblock   │ directory + inode metadata │ compressed file data     │
│ magic,size,  │ (uncompressed, tree-       │ 4 KiB pages, zlib,       │
│ crc,flags,   │  ordered)                  │ each page standalone     │
│ page size... │                            │                          │
└──────────────┴────────────────────────────┴──────────────────────────┘
      ▲ checks here first                       ▲ checked page-by-page,
                                                 fully only with --extract
```

The checker validates the magic signature (`"Compressed ROMFS"`), the recorded size against the image/file size, the edition/CRC fields and flag bits, then walks the directory tree and inode table checking that every inode's offsets land inside the image. File data is only decompressed on demand during normal mount; `fsck.cramfs` therefore has two depths of verification, and the shallow one can miss corrupt pages.

### The structures it reads

The image is parsed against the kernel's on-disk types (`linux/cramfs_fs.h`). The superblock carries the magic `0x45cd`, the total image size, a flags word, the 16-byte signature string `"Compressed ROMFS"`, an image CRC and edition number in the `fsid` field, a volume name, and the root inode. Every inode that follows is a 12-byte bitfield-packed record:

```
word 0:  mode:16 | uid:16       permissions, owner
word 1:  size:24 | gid:8        file size in bytes; 2^24 caps files at 16 MiB
word 2:  namelen:8 | offset:24  name length; offset of this inode's data
```

Two consequences fall out of the field widths. First, cramfs *cannot represent* a file larger than 16 MiB — the 24-bit size field simply has no room — so `mkfs.cramfs` refuses such files at build time and the checker never sees one. Second, uid and gid are 16/8 bits wide: identities above those caps are truncated when the image is built, so a checked-clean image can still hold "wrong" ownership relative to the source tree. The checker validates internal consistency of what is recorded; it cannot know what was intended.

### Two depths of checking

1. **Structural check (default).** Superblock sanity, directory tree walk, inode/offset range validation. Fast, no output unless errors.
2. **Full decompression test (`--extract`).** Decompresses *every* data page of *every* file and optionally writes the results into a directory, proving the zlib streams are intact. This is the mode used before burning an image into firmware or shipping it in an installer.

Mechanically, the extract stage is one `zlib` `inflate()` per page: cramfs compresses each page as an independent, self-terminating stream so the page cache can decompress any single page without touching its neighbors, and the checker exploits the same property — every stream must end cleanly (`Z_STREAM_END`) inside its page. The design costs per-page compression overhead (worse ratio than one whole-file stream); the benefit is that verification is O(pages), a single corrupt page damns the image locally, and the model matches exactly what the kernel driver will do at runtime.

### Where cramfs lives

cramfs trades features for footprint: no journal, no free-block accounting, no writable state, everything compressed with zlib page-by-page so the page cache can serve any 4 KiB independently. That profile made it the initramfs and firmware image of its era, and it persists in older/minimal embedded systems and installer rescue media. Knowing the deployment explains the tool: a corrupt page in a shipped image is a *build* defect, discovered either at boot (mount failure) or at runtime (EIO on one file) — hence a checker whose job is to catch it before shipping.

### The checking loop, step by step

With `-v`, the checker narrates its walk, which is the best way to see what it validates:

```bash
$ fsck.cramfs -v rootfs.cramfs
```

In order: the superblock is parsed (magic signature, size fields, flags, page size) and cross-checked against the actual file size; the directory tree is walked, inode by inode, verifying that every recorded offset/size lands inside the image and names conform; without further flags, that is all — data pages are trusted. With `--extract=<dir>`, a third stage decompresses every data page of every file (writing results to `<dir>`), which is the only stage that exercises the zlib streams. The progression explains the option set: structural soundness is cheap and always on; payload verification costs CPU and disk proportional to image size.

### A build-QA gate script

The two-stage check composes into a few lines of CI shell — fail fast on structure, then pay for full verification:

```bash
#!/bin/sh
# cramfs-qa.sh <image> — structural gate, full decompress gate, content diff
set -eu
img="$1"
fsck.cramfs "$img"                          # 1: superblock/structure, fast
out="$(mktemp -d)"
fsck.cramfs --extract="$out" "$img"          # 2: every zlib stream verified
diff -r --brief rootfs/ "$out"               # 3: content matches source tree
rm -rf "$out"
```

Stage 2 catches build-toolchain corruption (a bad libz, a truncated source file); stage 3 catches logic errors (wrong source tree). Both exit nonzero and abort under `set -e`, which is the whole point.

### Choosing -b correctly

The page/block size is fixed when `mkfs.cramfs` builds the image (`-b`, multiples of the machine page size, 4 KiB default). The checker can usually read the recorded value, but images built by other toolchains, round-tripped through editors, or checked with explicit `-b` need the builder's value to parse correctly. Rule of thumb: scripts that build images should check them with the same `-b` they built with — a mismatch surfaces as bogus structural errors that look like corruption but are misparses.

There is no repair path because there is no writable state to reconcile — no journal, no bitmaps, no free-block accounting. The recovery procedure for a bad image is always: fix the source tree, re-run `mkfs.cramfs`, re-verify with `fsck.cramfs`, redeploy. `fsck`'s "corrected errors" exit codes can therefore never originate from this helper.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-v, --verbose` | Progress and detail while checking (files, pages) |
| `-b, --blocksize <size>` | Page/block size to assume (must match the `mkfs.cramfs -b` used to build; multiples of page size) |
| `--extract[=<dir>]` | Test-uncompress the whole filesystem; with `<dir>`, write contents there for full verification |
| `-h, --help` | Usage |
| `-V, --version` | Version |

The `--extract` destination defaults to the current directory if omitted — a classic footgun on a full workdir; always pass an explicit directory.

## Usage Patterns

```bash
# Sanity-check an initramfs image before shipping it
fsck.cramfs /boot/initrd.img-6.1.0

# Verbose structural check during build QA
fsck.cramfs -v rootfs.cramfs

# Full integrity test: decompress every page, write results out
mkdir /tmp/extract && fsck.cramfs --extract=/tmp/extract rootfs.cramfs

# Verify an image built with a non-default page size
mkfs.cramfs -b 8192 -r rootfs/ rootfs.cramfs
fsck.cramfs -b 8192 rootfs.cramfs

# Mount it read-only afterwards to eyeball the tree
mount -t cramfs -o loop rootfs.cramfs /mnt/cram

# Through the generic front end (same dispatch as fsck -A would use)
fsck -t cramfs /srv/images/rootfs.cramfs

# Compare extracted tree against the source directory (build regression)
diff -r --brief rootfs/ /tmp/extract/
```

```bash
# CI gate with a hard ceiling (extract is CPU- and disk-proportional to image size)
timeout 300 fsck.cramfs --extract="$WORK/extract" rootfs.cramfs || echo "image failed QA"
```

```bash
# Catch a truncated transfer cheaply: the superblock records the image size,
# so an incomplete scp/curl download fails the default check immediately
fsck.cramfs initrd.img || echo "truncated or corrupt"
```

```bash
# Keep extract output off small tmpfs roots: it needs ~uncompressed-size capacity
df -h /var/tmp   # check headroom first (/tmp is often RAM-backed)
fsck.cramfs --extract=/var/tmp/extract rootfs.cramfs
```

```bash
# Firmware pre-flash gate: full decompress check, then checksum what you ship
fsck.cramfs --extract=/tmp/x rootfs.cramfs && sha256sum rootfs.cramfs > SHA256SUMS
```

```bash
# Verify a cramfs that lives directly on a block device (cramfs mounts from
# block devices too, not just image files) — read-only check, no --extract
sudo fsck.cramfs -v /dev/mmcblk0p1
```

```bash
# Sanity-check the initramfs of a running system (read-only, always safe)
fsck.cramfs /boot/initrd.img-"$(uname -r)" && echo "initramfs intact"
```

## Nuances and Gotchas

- **It cannot repair — ever.** The usual fsck flow ("run with `-y`, mount, hope") is meaningless here. If `fsck.cramfs` reports corruption, the only fix is rebuilding the image; plan your CI to fail on a nonzero status.
- **Default check can miss bad data.** Without `--extract`, corrupt *data* pages may pass if metadata offsets are consistent. Firmware/installer pipelines must use `--extract` to genuinely test decompression of everything.
- **`--extract` without a directory writes into `.`** — potentially gigabytes of decompressed payload into your cwd. Always pass an explicit, empty directory.
- **`-b` must match the build.** cramfs records its page size, but tooling differences make an explicit `-b` the reliable way to check images built with unusual `mkfs.cramfs -b` values; a mismatch produces misleading structural errors.
- **Kernel constraints shadow the tool.** The cramfs *driver* has hard limits (page-cache-oriented page size, size caps, filename length limits) independent of what fsck.cramfs accepts; an image can verify cleanly yet fail to mount if it exceeds driver limits.
- **Loop-mounting needs the module.** `mount -t cramfs` requires the `cramfs` kernel module; many minimal distros ship it disabled or as a module — the checker works without it, the mount does not.
- **Success is silent.** A clean check prints nothing (or progress with `-v`) and exits 0. Scripts should test the exit status, not grep output.
- **Front-end exit codes apply.** When invoked through `fsck` (e.g. `fsck -t cramfs image`), the fsck(8) aggregate code table is what callers see; invoked directly, it simply exits nonzero on any detected problem.
- **Superblock size is the cheapest gate.** The superblock records the full image size and the checker cross-checks it against the actual file, so a truncated upload fails immediately with no decompression work. Run the default check before any expensive `--extract` stage.
- **`--extract` needs output capacity.** The written contents are the *uncompressed* payload — budget roughly the compression ratio (commonly 2-3×) of the image size in free space, and remember `/tmp` is frequently tmpfs (RAM-backed), so a big extract can OOM or fill your tmpfs.
- **Single-threaded, CPU-bound.** zlib inflate runs on one core; verify time scales linearly with image size. Multi-image pipelines should parallelize across images, not expect the checker itself to speed up.
- **Clean ≠ intended.** Internal consistency is all the checker can assert: an image built from the *wrong* source tree verifies perfectly. Pair it with a content diff against the build input, or a checksum of that input recorded at build time.
- **The checker reads, the kernel decides.** An image can pass `fsck.cramfs` and still fail `mount` — kernel-side constraints (module absent, driver limits, mount options) are outside the checker's view. Verify with a real loop-mount in staging before rollout.
- **No pipes, no compressed input.** The checker operates on a seekable path — there is no stdin mode, so `zcat image.cramfs.gz | fsck.cramfs -` is not a thing; decompress to a temp file first. Budget that temp space in CI.
- **`-v` output is narration, not a report format.** Verbose lines aid humans mid-build; scripts must gate on exit status (the file's success signal is silence plus exit 0), because the narration format is not a stable interface.

## Exit Status

- `0` — the image passed the requested level of checking (with or without `--extract`).
- Nonzero — corruption was detected (superblock, metadata, or a decompression failure), or an operational failure occurred (unreadable image, bad options). When driven by the `fsck` front end, the aggregated fsck(8) codes apply.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`fsck`](./fsck.md) — the front end that dispatches to this helper for `-t cramfs`.
- [`fsck.minix`](./fsck.minix.md) — the other util-linux-built checker; writable, so it *can* repair.
- [`mkfs.cramfs`](./mkfs.cramfs.md) — builds the images this tool verifies; the rebuild step of recovery.
- [`losetup`](./losetup.md) — loop-attach images for mount-based spot checks.
- [`mount`](./mount.md) — mounts the verified image read-only (`-t cramfs -o loop`).
- [`internals`](../../internals.md) — page cache behavior that cramfs was designed around.

## Interview Questions

### Q: Why can't fsck.cramfs repair a filesystem?

Cramfs is read-only by design: there are no bitmaps, free lists, or a journal to reconcile — every structure is fixed at image-build time. "Repair" would mean rewriting the image, which is exactly what `mkfs.cramfs` does. The checker's job is reduced to validation, and the operational loop is check → rebuild → re-check.

### Q: An image passes fsck.cramfs but a device fails to decompress a file at runtime. What went wrong in your pipeline?

The structural check validated metadata and offsets but never decompressed the data pages. Full verification requires `--extract`, which test-uncompresses every page (and can write them out for diffing). This is why build pipelines for firmware and installer images must run the extract mode, not just the default check.

### Q: What is the `-b, --blocksize` option for, and when does getting it wrong matter?

cramfs pages are compressed independently at a fixed block size chosen at `mkfs.cramfs` time (multiples of the machine page size). The checker uses that size to walk data; checking an 8 KiB-built image with the 4 KiB default misparses structures and produces bogus errors. Pass the same `-b` the builder used whenever it is not the default.

### Q: How does cramfs differ from squashfs, and does that change the checking story?

cramfs is older and simpler: zlib-only, small size caps, fixed page orientation, root-in-superblock metadata; squashfs adds multiple compressors, larger limits, fragment blocks, xattrs, and its own unsquashfs-based verification tooling. Both are read-only, so both share the "verify then rebuild" model — the difference is that squashfs ships richer validation/extraction tools, while cramfs verification lives in fsck.cramfs `--extract`.

### Q: A truncated image hits the pipeline — what does the checker catch, and when?

The superblock records the total image size, and the default structural check compares that against the actual file size, so truncation fails immediately and cheaply. Corruption past that gate is a different story: bad *data* pages still require `--extract` (per-page zlib verification), because the default walk trusts data payloads as long as every inode offset is consistent. Layered pipelines use the default check as a fast fail-fast gate and extract as the thorough stage.

### Q: Why is each cramfs page compressed as an independent stream, and what does that trade away?

Because the consumer is the page cache: the kernel must read and decompress any single page without touching its neighbors, or random access degrades into sequential unpacking. Independent streams mean per-page zlib overhead (dictionary reset, no cross-page redundancy), so the ratio is worse than a whole-file compress — a deliberate price for page-granular random access. The checker reuses the property: `--extract` verifies page by page, and a single bad stream fails the image at that page rather than invalidating the rest.

### Q: In CI, how do you gate an initramfs image on integrity?

Build with mkfs.cramfs, run `fsck.cramfs --extract="$WORK/extract" image` against an empty directory, fail the job on nonzero exit, optionally `diff -r --brief source/ extract/` to catch content regressions, then loop-mount read-only for smoke tests. The extract step is the only stage that proves the compressed payload is intact.

### Q: The checker passed an image but mount fails. What is outside fsck.cramfs's view?

Everything kernel-side: whether the `cramfs` module is loaded at all, whether the driver's hard limits (page-size alignment, name lengths, total size) reject the image, and whether mount options/namespaces cooperate. The checker validates the *file*; the mount validates the *file plus kernel*. Debug order: checker exit status → `dmesg` after the failed mount (the driver logs why) → loop device/module availability. This split is also why CI should loop-mount a sampled image, not only run the checker.

### Q: How do you tell a `-b` misparse apart from real corruption?

Rerun with the builder's explicit `-b` first — misparses vanish when the page size matches. Corrupt images fail deterministically at the same offsets on re-checks, and often at the very first page after a truncation point; `-b` mismatches produce a burst of errors from the first data structures onward. The decisive test is rebuilding from the known-good source tree: if the rebuild verifies, the problem was build/transfer; if it reproduces, the source content itself is bad.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/fsck.cramfs.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
