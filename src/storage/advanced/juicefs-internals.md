# JuiceFS Internals: Metadata Engines over Object Storage

JuiceFS sits in this repo's [parallel filesystem survey](./parallel-filesystems.md) next to
Lustre and BeeGFS, but it is built from opposite parts: Lustre ships bespoke MDS/OSS daemons,
while JuiceFS ships no storage daemons at all. The [distributed-fs sketch](./distributed-fs.md)
gives the one-paragraph version; this page goes where an interviewer drills -- what the client
does on `write()` and `read()`, how a file becomes object-store keys, why the metadata engine's
transaction model *is* the filesystem's consistency model, and where the single-engine design
stops scaling. Data-plane semantics assume the S3 API covered in
[./s3-internals.md](./s3-internals.md) and [../object-storage.md](../object-storage.md). All
defaults were probed against juicefs.com/docs and github.com/juicedata/juicefs `main` in Aug 2026.

## One client, two databases

Everything JuiceFS-specific lives in the client. It speaks one database protocol upward and one
object-store protocol downward; the two backing services never talk to each other.

```text
        app I/O (POSIX)                    METADATA PATH
            |                              lookup, setattr, chunk->slice
            v                              map, slice refs, sessions,
  +---------------------+   SQL / RESP    quota, trash TTLs
  |   JuiceFS Client    |<--------------> +---------------------+
  | FUSE mount / CSI    |                 |  Metadata Engine    |
  | mount pod / S3 gtw  |                 |  Redis / TiKV /     |
  | / WebDAV / Java SDK |                 |  MySQL / Postgres / |
  +---------------------+                 |  SQLite / etcd /    |
       |            ^                      |  FoundationDB       |
       | GET/PUT    | GET/LIST             +---------------------+
       v LIST/DROP  |                     (never carries file data)
  +---------------------+
  |   Object Storage    |  S3, OSS, MinIO, Ceph RGW, COS, "file", ...
  +---------------------+
```

The consequence is blunt: the namespace is a *schema inside a database*, not a daemon's
in-memory tree. A Redis operator already knows how to back up, monitor, and fail over the
namespace tier; there is no private on-disk format to fsck. The cost lands in the client, which
rebuilds POSIX from read-modify cycles on that schema, and in the single place where every
client's metadata requests land.

## Chunk -> slice -> block: how a file becomes keys

| Level | Size | Nature | Owner |
|-------|------|--------|-------|
| Chunk | up to 64 MiB (`ChunkBits = 26`, pkg/meta/interface.go) | logical, fixed by byte offset for the file's lifetime | client addressing |
| Slice | one continuous write within a single chunk; never crosses chunks | logical, unit of persistence and of metadata commit | client buffer/flush |
| Block | up to 4 MiB (`--block-size` default `"4M"`, cmd/format.go) | physical object; also the unit of the local disk cache | object store + cache dir |

A slice is cut into blocks only at flush time, and blocks upload concurrently
(`--max-uploads`, default 20). Blocks are immutable -- most object stores cannot edit ranges --
so a random overwrite never downloads-modifies-reuploads: the new bytes go to a new (or
adjoining) slice whose blocks are fresh objects, and the chunk's slice list grows. A read is a
merge: per position, the most recently written slice covering that offset wins. The docs' own
telemetry example: one full-chunk flush = 1 metadata transaction + 16 PUTs of 4 MiB
(`meta.txn : object.put_c = 1 : 16`).

Object keys derive from the *slice id*, not the inode (`CalcObjects`, pkg/vfs/internal.go):

```text
default:     {volume}/chunks/{sid/1e6}/{sid/1e3}/{sid}_{index}_{size}
hash-prefix: {volume}/chunks/{sid%256, %02X}/{sid/1e6}/{sid}_{index}_{size}
example:     demo/chunks/0/0/1_15_4194304      (block 15 of slice 1, 4 MiB)
```

The numeric fan-out (`chunks/0/0/`, `chunks/0/1/`, ...) keeps S3 LIST prefixes small. Bucket
contents are never the "original" files; without the metadata engine the bucket is an
uninterpretable pile of blocks.

## Write path: buffer, upload, then commit

`write()` on the FUSE mount does not touch the network:

1. The write commits to the client's in-memory read/write buffer (`--buffer-size`, default
   300 MiB, shared by reads and writes) and returns in microseconds. File size grows locally
   even though nothing is persisted -- a preview, not a commit, as the docs put it.
2. A slice uploads when it crosses a chunk border, ages out of the buffer, exceeds slice
   limits, or the app forces it via `close()` / `fsync()`; at flush it splits into 4 MiB
   blocks and PUTs in parallel.
3. Only after the upload succeeds does the client commit the new slice mapping to the engine
   ("upload first, then commit"). Crash before commit = no visible change, not corruption.

Backpressure is explicit: buffer usage over the threshold adds a 10 ms delay to every write;
past twice the threshold, writes suspend until the buffer drains. The fixes are more
`--buffer-size` and/or more `--max-uploads`.

The disk "staging" area is *not* the default path. It exists only under `--writeback` (client
write cache), which inverts step 3: write to `/var/jfsCache/<UUID>/rawstaging/`, commit metadata
immediately, upload asynchronously (`--upload-delay`, `--upload-hours`, since v1.4
`--writeback-threshold-size`). Fast small-file creates, but local disk loss before upload
destroys those objects permanently -- the docs recommend it for bursts like extracting archives
of small files. Separately, `-o writeback_cache` is a *kernel* FUSE mode (Linux 3.15+) that
coalesces small writes in page cache and turns sequential writes into random ones; it is
unrelated to client writeback.

Fragmentation is the write path's shadow cost: overwrites and short appends spray small slices.
The client schedules background compaction (merging a chunk's slices into one) when the slice
count per chunk exceeds its limit, and `juicefs gc` forces it. Stale blocks linger until Trash
expiration -- hence object-store usage running *above* `df` on overwrite-heavy workloads.

## Read path: four places a byte can come from

Checked in order; a miss fills each level asynchronously for next time:

| Order | Source | Guard rails |
|-------|--------|-------------|
| 1 | kernel page cache | invalidated on next `open` if mtime changed; repeat reads reach microseconds |
| 2 | client buffer (readahead window) | sequential readahead gets 1/4 to 1/2 of `--buffer-size` |
| 3 | local disk cache (`--cache-dir`) | default `/var/jfsCache` on Linux; `--cache-size` 102400 MiB; `--free-space-ratio` 0.1; eviction 2-random |
| 4 | object storage | GET or S3 Range read of the block |

Two distinct ahead-of-time behaviors (cache guide + command reference): **readahead** grows a
client-side window on sequential reads, downloading ahead of the offset (`--max-readahead`, MiB,
v1.3; set 0 for random I/O); **prefetch** schedules the *whole* block for async download when
only part of it was read (`--prefetch`, default 1) -- right for adjacency-friendly workloads,
read amplification for sparse random access, hence `--prefetch=0`. Blocks smaller than one
block -- every small file -- are also cached at write time, so small-file rereads never leave
the node.

Metadata consistency is close-to-open by default: kernel attr/entry/dir-entry caches default to
1 s (`--attr-cache=1`, `--entry-cache=1`, `--dir-entry-cache=1`) and `open()` always consults
the engine. `--open-cache` (default 0) caches open-file slice maps in client memory and weakens
close-to-open; the docs note the Enterprise edition adds active invalidation for that cache.
`--verify-cache-checksum` (default `extend` since v1.3) detects tampered cache blocks.

## The metadata engine is the filesystem

The Redis schema (comment block atop pkg/meta/redis.go) is the cleanest way to see it:

| Key pattern | Holds |
|-------------|-------|
| `i$inode` | attribute struct (mode, uid/gid, times, nlink, length) |
| `d$inode` | directory entries: name -> {inode, type} |
| `c$inode_$indx` | chunk $indx's slice list: Slice{pos, id, length, off, len} |
| `p$inode` / `s$inode` / `x$inode` | parents (hard links) / symlink target / xattrs |
| `lockf$inode`, `lockp$inode`, `sessions` | flock, POSIX locks, live client sessions |
| `sliceRef`, `delfiles`, `detachedNodes` | refcounts, deferred deletes, detached trees |

Atomicity is inherited, not implemented: every namespace operation is a transaction on the
engine. The Redis driver wraps each method in an optimistic `WATCH`/`MULTI`/`EXEC` with up to
50 retries and quadratic backoff (the `txn` wrapper in pkg/meta/redis.go); the KV driver
(`kvMeta.txn`, pkg/meta/tkv.go) does the same over TiKV's/etcd's txn interface. The source
documents the Redis feature floor: Transaction 2.2+, Scripting 2.6+, Hash 4.0+, Scan 2.8+.
Three operational facts interviewers like. Redis Cluster works because JuiceFS hash-tags every
key with `{DB}` so the whole keyspace lands in one hash slot -- transactions keep working, but
one shard carries all metadata. Redis metadata costs roughly 300 bytes per file (docs' figure),
so 100M files want ~30 GiB; at `maxmemory`, even *deletes* fail (they are writes too), which is
why the best-practices page suggests a pre-planted placeholder key to buy escape room. With AOF
`everysec`, a Redis crash can lose up to ~1 s of namespace mutations -- the docs pair AOF+RDB
with `--backup-meta` (default 3600 s), which continuously dumps engine state into the bucket.

## What the trade buys, and where it stops

The design buys durability and consistency from battle-tested databases, elasticity from the
object store, and a data plane that bypasses metadata entirely once a client holds a chunk's
slice list. The ceiling is equally legible: every `lookup`, `stat`, and slice commit from every
client serializes through one engine cluster, while Lustre's DNE and CephFS's subtree
partitioning (compared in the [parallel filesystems survey](./parallel-filesystems.md))
*distribute* metadata as they scale. JuiceFS 1.x re-sizes one engine instead; engine choice just
moves the ceiling -- Redis for sub-ms latency, TiKV/PostgreSQL/MySQL for durability and
footprint at multiple-of-network-RTT cost per op. Two vendor claims stated precisely because the
docs state them: distributed (cross-client) caching is "supported in our enterprise edition"
(FAQ), and richer memory-metadata caching with active invalidation is Enterprise-only. Everything
else above is Community Edition behavior; broader Enterprise/Cloud numbers are marketing, not
documented internals.

## Admin surfaces interviewers probe

- **Trash** -- on by default. Deleted files flatten into
  `.trash/YYYY-MM-DD-HH/[parent-ino]-[ino]-[name]` for `--trash-days` (set via `format`/`config`;
  0 disables; v1.1 `juicefs restore` rebuilds directory structure). Expiration runs in the client
  background job hourly, so at least one live mount is required (`--no-bgjob` suspends it; note
  `--read-only` implies `--no-bgjob`). Stale slices age out the same way, visible only via
  `juicefs status --more` ("Trash Slices").
- **Quota** -- volume-wide `--capacity`/`--inodes` at format time; directory quotas since v1.1
  via `juicefs quota set/get/ls`. Clients refresh quota settings on the `--heartbeat` interval
  (12 s), so enforcement lags by up to one heartbeat.
- **Clone** -- `juicefs clone` copies metadata only, redirect-on-write: both trees reference the
  same blocks until one side rewrites a range. Atomic per file, not per directory; interrupted
  clones leak inodes that `juicefs gc --delete` reclaims. On kernels with `copy_file_range`,
  plain `cp` rides the same mechanism.
- **Tiered storage (v1.4)** -- tiers 0-3 map to object-store storage classes
  (`juicefs config --tier 1 --storage-class STANDARD_IA`, then `juicefs tier set` per file/dir),
  with `--tag key=value` tags designed to combine with provider lifecycle rules. Bucket-level
  lifecycle rules that expire JuiceFS objects directly would break reads: the engine still
  references those block ids. The docs' FAQ attributes df-vs-bucket divergence to trash and
  stale slices, not to a lifecycle-friendly layout.

## Kubernetes: CSI mount pods and FUSE mount modes

The CSI driver runs a controller StatefulSet plus a node DaemonSet and, by default, spawns a
dedicated **Mount Pod** per PVC per node: pods sharing a PV share one refcounted mount pod, and
the volume bind-mounts at `/var/lib/juicefs/volume/[pv-name]`. Where DaemonSets are forbidden
(some serverless Kubernetes), **sidecar mode** injects the client into each pod and drops the
node component. Provisioning is static (admin-made PV mounting the volume root or a subdir) or
dynamic (each PVC becomes a PV backed by a fresh subdirectory). FUSE-side mount modes map onto
Kubernetes via `mountOptions`: foreground vs `-d` daemon, `--read-only` (implies `--no-bgjob`),
`--subdir` to fence a PV to one directory, `--writeback` for staging writes, plus kernel options
like `-o allow_other`/`allow_root` and `-o writeback_cache`. The non-FUSE access routes -- Python
SDK (fsspec), Java SDK, S3 gateway, WebDAV -- matter in-cluster because they skip the mount pod
entirely.

## Worked example: layout calculator

One dependency-free script ties the numbers together: object counts per write pattern, real key
shapes, and how much of a 10 GiB sequential read lands in a given cache size. The append row
shows straddled appends splitting into two slices and 7 MiB slices becoming 4 MiB + 3 MiB
blocks; the overwrite row shows the 1:1 txn-to-object blowup and ~19.5 MiB of stale objects.

```python
#!/usr/bin/env python3
"""JuiceFS layout calculator. Defaults probed Aug 2026: chunk 64 MiB
(ChunkBits=26, pkg/meta/interface.go), block 4 MiB ("--block-size 4M",
cmd/format.go), cache 100 GiB (--cache-size 102400 MiB, command reference)."""
MI = 1024 * 1024
CHUNK, BLOCK = 64 * MI, 4 * MI
CACHE_DEFAULT, FILE = 102400 * MI, 10 * 1024 * MI

def object_key(vol, sid, indx, size, hashed=False):
    """Key shape from CalcObjects (pkg/vfs/internal.go)."""
    mid = ("%02X/%d" % (sid % 256, sid // 1000000)) if hashed else ("%d/%d" % (sid // 1000000, sid // 1000))
    return "%s/chunks/%s/%d_%d_%d" % (vol, mid, sid, indx, size)

def sequential(size):
    """One growing slice per chunk, flushed at the chunk border (1 txn : 16 PUTs)."""
    s = (size + CHUNK - 1) // CHUNK
    return s, (size + BLOCK - 1) // BLOCK, s

def appended(size, append_len):
    """fsync per append: one slice per append; slices never cross chunk borders."""
    slices = blocks = pos = 0
    while pos < size:
        step = min(append_len, size - pos)
        room = CHUNK - (pos % CHUNK)
        for piece in (min(step, room),) + ((step - room,) if step > room else ()):
            if piece > 0:
                slices += 1
                blocks += (piece + BLOCK - 1) // BLOCK
        pos += step
    return slices, blocks, slices

def overwrites(count, wsize=4 * 1024):
    """Each overwrite: new slice + small object; stale block ages out via trash/gc."""
    return count, count, count, count * wsize

def cache_fill(size, cache_size):
    blocks = (size + BLOCK - 1) // BLOCK
    return min(blocks, cache_size // BLOCK), blocks, min(size, cache_size) / cache_size

print("JuiceFS layout calculator -- chunk %d MiB, block %d MiB" % (CHUNK // MI, BLOCK // MI))
print("file: 10 GiB (10240 MiB) = %d chunks = %d max-size blocks" % (
    (FILE + CHUNK - 1) // CHUNK, (FILE + BLOCK - 1) // BLOCK))
print()
print("%-38s %8s %9s %10s" % ("write pattern", "slices", "objects", "meta.txns"))
for label, (s, b, t) in (("single sequential stream", sequential(FILE)),
                         ("1463 x 7 MiB appends, fsync each", appended(FILE, 7 * MI)),
                         ("5000 x 4 KiB random overwrites", overwrites(5000)[:3])):
    print("%-38s %8d %9d %10d" % (label, s, b, t))
print()
print("sample object keys (slice id 1, first chunk): %s, %s, %s" % (
    object_key("demo", 1, 0, BLOCK), object_key("demo", 1, 1, BLOCK), object_key("demo", 1, 15, BLOCK)))
print("tail block, 130 MiB file (chunks of 64+64+2 MiB): %s" % object_key("demo", 1, 32, 2 * MI))
print("hash-prefix volume, slice id 123456789: %s" % object_key("demo", 123456789, 0, BLOCK, hashed=True))
stale = overwrites(5000)[3]
print("5000 random overwrites leave %d KiB (~%.1f MiB) of stale objects" % (stale // 1024, stale / MI))
print()
print("cache fill, sequential read of 10 GiB (2560 x 4 MiB blocks):")
for cs, label in ((CACHE_DEFAULT, "--cache-size=102400 MiB (default)"), (8192 * MI, "--cache-size=8192 MiB")):
    got, total, frac = cache_fill(FILE, cs)
    print("  %-36s %4d/%d blocks, %4.1f%% of cache" % (label, got, total, frac * 100))
print("readahead window bounded by buffer: 1/4..1/2 of --buffer-size=300 MiB -> 75..150 MiB")
```

Output (verbatim from a run of the script above):

```text
JuiceFS layout calculator -- chunk 64 MiB, block 4 MiB
file: 10 GiB (10240 MiB) = 160 chunks = 2560 max-size blocks

write pattern                            slices   objects  meta.txns
single sequential stream                    160      2560        160
1463 x 7 MiB appends, fsync each           1600      3017       1600
5000 x 4 KiB random overwrites             5000      5000       5000

sample object keys (slice id 1, first chunk): demo/chunks/0/0/1_0_4194304, demo/chunks/0/0/1_1_4194304, demo/chunks/0/0/1_15_4194304
tail block, 130 MiB file (chunks of 64+64+2 MiB): demo/chunks/0/0/1_32_2097152
hash-prefix volume, slice id 123456789: demo/chunks/15/123/123456789_0_4194304
5000 random overwrites leave 20000 KiB (~19.5 MiB) of stale objects

cache fill, sequential read of 10 GiB (2560 x 4 MiB blocks):
  --cache-size=102400 MiB (default)    2560/2560 blocks, 10.0% of cache
  --cache-size=8192 MiB                2048/2560 blocks, 100.0% of cache
readahead window bounded by buffer: 1/4..1/2 of --buffer-size=300 MiB -> 75..150 MiB
```

Interview takeaway from the table: a sequential stream pays 1 metadata txn per 64 MiB and emits
uniform 4 MiB objects; fsync-per-append pays one txn and one small object per append; random
overwrites multiply txns, objects, and stale-data GC pressure simultaneously -- which is exactly
why the client compacts, why small-file bursts want `--writeback`, and why object-store request
pricing dominates small-file bills.

## References

1. [JuiceFS docs: Architecture](https://juicefs.com/docs/community/architecture/) -- three-component split, chunk/slice/block definitions, metadata engine list (page last updated Nov 6, 2025; probed Aug 2026).
2. [JuiceFS docs: Data Processing Workflow](https://juicefs.com/docs/community/internals/io_processing) -- flush mechanics, the 1:16 metadata-to-object ratio, buffer backpressure, writeback mode.
3. [JuiceFS docs: Cache](https://juicefs.com/docs/community/guide/cache) -- metadata vs data caching, readahead vs prefetch, cache-dir defaults, close-to-open consistency.
4. [JuiceFS docs: Command Reference](https://juicefs.com/docs/community/command_reference) -- source of the mount/format defaults quoted throughout.
5. [JuiceFS docs: Metadata Engine Best Practices - Redis](https://juicefs.com/docs/community/redis_best_practices) -- 300 B/file estimate, OOM recovery, Sentinel/Cluster, AOF trade-offs.
6. [JuiceFS docs: Trash](https://juicefs.com/docs/community/security/trash) -- trash layout, `--trash-days`, stale slices.
7. [JuiceFS docs: Clone Files or Directories](https://juicefs.com/docs/community/guide/clone) -- ROW semantics and consistency bounds.
8. [JuiceFS docs: Tiered Storage](https://juicefs.com/docs/community/guide/tiered-storage) -- tiers 0-3, storage classes, tags for lifecycle rules.
9. [JuiceFS docs: CSI Driver Introduction](https://juicefs.com/docs/csi/introduction) -- Mount Pod mode, sidecar mode, static/dynamic provisioning.
10. [JuiceFS docs: FAQ](https://juicefs.com/docs/community/faq) -- random-write data flow; "Distributed cache is supported in our enterprise edition."
11. [github.com/juicedata/juicefs source](https://github.com/juicedata/juicefs/blob/main/pkg/meta/interface.go) -- `ChunkBits = 26`; see also [pkg/vfs/internal.go](https://github.com/juicedata/juicefs/blob/main/pkg/vfs/internal.go) (`CalcObjects` key format), [pkg/meta/redis.go](https://github.com/juicedata/juicefs/blob/main/pkg/meta/redis.go) (keyspace comment, WATCH/txn wrapper), and [cmd/format.go](https://github.com/juicedata/juicefs/blob/main/cmd/format.go) (`--block-size` default "4M").
