# fincore — report which pages of a file are in the page cache

## Overview

`fincore` answers a deceptively simple question: *of this file's pages, how
many are currently resident in the page cache?* It walks the requested files,
calls `mincore(2)` on each, and prints the resident-page count, resident
bytes, file size, and path. The tool is the command-line equivalent of what
`vmtouch` (third-party) does, and the natural companion for anyone measuring
cache warmth before or after a workload.

Debian bookworm ships it in the `util-linux-extra` package at
`/usr/bin/fincore` (man section 1) — note the *extra* package: minimal
installations and slim containers often lack it while having the rest of
util-linux.

It reads only; it never pins, locks, warms, or evicts anything. Common uses:
checking whether a benchmark will measure disk or cache, verifying that a
backup job actually read a file, watching cache behavior during `drop_caches`
experiments, and estimating how much of a huge log or image is cached on a
production box.

| Field | Value |
| --- | --- |
| Package | util-linux-extra (Debian bookworm) |
| Section (man) | 1 |
| Path | /usr/bin/fincore |
| Lineage | util-linux original (built on mincore(2)) |
| Standards | None — mincore(2) is a Linux/BSD interface, not POSIX |

## Synopsis

```
fincore [options] <file>...
```

Common one-line forms:

```
fincore /var/log/syslog           # cache state of one file
fincore -b *.img                  # raw byte counts instead of human units
fincore -r /var/lib/docker/       # recurse into directories
fincore -J image.raw | jq .       # machine-readable output
```

## How It Works

### mincore(2) in one paragraph

The kernel maps file data into the **page cache** — page-sized (4 KiB) chunks
kept in RAM so subsequent reads avoid the device. `mincore(2)` takes a memory
mapping and returns a per-page vector saying whether each page is resident
(there is an associated page in the cache) or not. `fincore` opens the file,
mmaps it page by page (or in full), and aggregates that vector:

```
 file pages:    [p0][p1][p2][p3][p4][p5][p6][p7]
 page cache:        ✓       ✓   ✓   ✓
 mincore vector:  0   1   0   1   1   1   0   0
 fincore output:  RESIDENT=5 pages, human-readable bytes, SIZE, FILE
```

Two properties follow directly: granularity is **pages, not bytes** (a 1-byte
read caches a 4 KiB page), and residency is **volatile** — the kernel may
reclaim any clean page at any moment under memory pressure.

### Reading the output

Default columns: `RESIDENT PAGES SIZE FILE` — resident bytes (human units),
resident page count, file size, and the path:

```bash
$ fincore /tmp/fa.bin
  RESIDENT  PAGES  SIZE FILE
     100.0M  25600 100.0M /tmp/fa.bin      # fully cached after a read
```

`-b/--bytes` switches RESIDENT/SIZE to raw byte counts (script-friendly);
`-o/--output` reorders/adds columns; `-J/--json` emits objects per file;
`-r/--recursive` descends directories given as arguments. As with other
util-linux listing tools, `--output` accepts column names and `-n` suppresses
the header, so the output can be shaped for `awk`/`sort` pipelines without
parsing the human units.

### Verified behavior on this system

```bash
$ fallocate -l 100M /tmp/fa.bin
$ fincore /tmp/fa.bin              # allocated but never read
  RESIDENT  PAGES  SIZE FILE
       0B        0 100.0M /tmp/fa.bin
$ cat /tmp/fa.bin > /dev/null      # force it through the page cache
$ fincore /tmp/fa.bin
  RESIDENT  PAGES  SIZE FILE
     100.0M  25600 100.0M /tmp/fa.bin
```

This read-warmup-then-verify loop is the tool's core idiom.

### Cache eviction experiments

```bash
$ sync && echo 3 | sudo tee /proc/sys/vm/drop_caches   # drop clean cache
$ fincore /tmp/fa.bin
  RESIDENT  PAGES  SIZE FILE
       0B        0 100.0M /tmp/fa.bin
```

`fincore` is the *measurement* half of the experiment; `drop_caches` is the
*manipulation* half. Together they make cache behavior observable instead of
folklore.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-b, --bytes` | Print RESIDENT/SIZE in bytes, not human units |
| `-J, --json` | JSON output (pair with jq for scripts) |
| `-r, --recursive` | Recurse into directories |
| `-o, --output <list>` | Select/reorder output columns |
| `-n, --noheadings` | Suppress the header line (with `-o` for scripts) |
| `-h, --help` / `-V, --version` | Help / version |

## Usage Patterns

```bash
# Is the DB file cached before I benchmark queries?
fincore /var/lib/postgresql/16/main/base/16384/24576
```

```bash
# Did the backup actually read this file? (RESIDENT > 0 right after)
fincore -b /srv/big/volume.img
```

```bash
# Warm a file, then prove it is warm
cat /srv/dataset/chunk-*.bin > /dev/null && fincore /srv/dataset/chunk-*.bin
```

```bash
# Script-friendly: byte counts, no header
fincore -b -n /var/lib/mysql/ibdata1
```

```bash
# Whole directory tree cache census, largest resident first
fincore -r /var/lib/docker/overlay2/ | sort -k1 -rh | head
```

```bash
# JSON for monitoring pipelines
fincore -J /var/log/journal/*/*.journal | jq -r '.[] | [.resident,.file] | @tsv' 2>/dev/null \
  || fincore -J /var/log/journal/ | jq .
```

```bash
# Before/after drop_caches in a controlled experiment
sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; fincore big.file
```

```bash
# Compare cache warmth of two candidate log files before deletion
fincore /var/log/old-app.log /var/log/app.log
```

## Nuances and Gotchas

- **Residency is a snapshot, not a guarantee.** Clean pages can be reclaimed
  any moment; a warm `fincore` result at t0 says nothing about t1 under
  pressure. Dirty pages stay until written back, which is a different axis.
- **Page granularity.** Anything below 4 KiB rounds up; reading one byte of a
  1 TiB file caches one page — RESIDENT counts are pages × 4 KiB (or the
  system's page size), not "bytes actually touched".
- **You need read access.** `fincore` opens the files; permission errors on
  root-only files are normal for unprivileged runs (no special capability
  needed otherwise).
- **tmpfs counts too.** tmpfs files live *in* the page cache by construction —
  `fincore` on `/dev/shm/*` shows near-total residency, which surprises people
  expecting disk-cache semantics.
- **Overlays and virtual filesystems can mislead.** On overlayfs (containers)
  or FUSE, residency reflects the upper/lower layer the mapping resolves to;
  interpret per-layer, not "the file".
- **Not in the base util-linux package.** `util-linux-extra` is an easy miss in
  Dockerfiles and images — the first `fincore: command not found` usually
  happens mid-incident.
- **It cannot warm or lock.** Warming is `cat file > /dev/null` (or
  `vmtouch -t`); *locking* into memory is `vmtouch -l` or `mlock` — fincore
  only observes.
- **Interpret RESIDENT relative to SIZE, not to "used RAM".** A file fully
  resident is charged to the cache, but shared mappings, readahead windows and
  per-NUMA duplicates make fincore numbers a *view*, not an accounting report.
  Pair it with `free -h`/`/proc/meminfo` context when presenting findings.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success (all files processed) |
| 1 | Failure — unreadable file, bad arguments, or allocation error |

## Related Commands

- [`fallocate`](./fallocate.md) — manipulates the other half of the story: which blocks are allocated
- [`overview`](./overview.md) — index of all util-linux collection pages
- [internals](../../internals.md) — page cache, reclaim and mmap machinery behind mincore(2)

## Interview Questions

### Q: What syscall does fincore rely on and what does it tell you?

`mincore(2)`: given a memory mapping, it returns a vector with one flag per
page indicating whether that page is resident in the page cache. fincore
aggregates this per file into resident pages/bytes. The data is a live
snapshot — clean pages can be evicted at any time.

### Q: How would you prove that a performance test measured cache instead of disk?

Record `fincore file` before the test: nonzero RESIDENT means the read path is
already warm. To be rigorous, `sync; echo 3 > /proc/sys/vm/drop_caches`, verify
RESIDENT dropped to 0, run the benchmark, then re-check. fincore is the
before/after measurement; drop_caches is the reset.

### Q: Why can fincore show 100% resident for a file on tmpfs?

tmpfs stores its data in the page cache by definition — there is no backing
device. mincore therefore reports essentially all pages resident. The same
reasoning explains why fincore is still useful there: it measures RAM occupancy
of tmpfs content.

### Q: A 1-byte read makes fincore report 4 KiB resident. Why?

Residency is page-granular: the kernel caches whole pages (4 KiB on most
systems). Any read touches and caches the containing page, and fincore counts
pages, not bytes transferred. Access-pattern analysis must account for this
rounding.

### Q: What are fincore's limits compared to vmtouch?

fincore only reports; it cannot warm (`vmtouch -t`) or lock (`vmtouch -l`)
files, and it is packaged in util-linux-extra rather than the base package.
Its advantage is being part of util-linux with JSON/column support. For
"lock this hot dataset in RAM" workflows you need vmtouch or your own mmap +
mlock code; for observation, fincore suffices.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux-extra/fincore.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
