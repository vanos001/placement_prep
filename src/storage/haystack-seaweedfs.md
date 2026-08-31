# The Small-Files Problem: Facebook Haystack and SeaweedFS

## The stat() storm behind a photo view

Every photo view on a large social network is a bet against the filesystem. When the Haystack team wrote their OSDI '10 paper, Facebook held over 65 billion user photos, each scaled to four sizes — 260 billion images, more than 20 petabytes — with one billion new photos (~60 TB) arriving weekly and over one million images served per second at peak. The previous design stored every image as one file on NAS appliances mounted over NFS, and the economics had collapsed: metadata, not data, consumed the disk arms.

The paper's diagnosis is the whole motivation for the system. With thousands of files per directory, the appliance's directory blockmap overflowed its cache and a single image read commonly cost **more than 10 disk operations**. Shrinking directories to hundreds of files still left **3 disk operations** per read: one to read directory metadata, one to load the inode, one to read the file. Photo Store servers then cached NFS filename-to-file-handle mappings in memcache and even added a custom `open by filehandle` syscall to the kernel, but the gain was minor — the long tail of unpopular photos misses caches by definition, and the appliance would still need all inodes resident in RAM ("each file requires at least one inode, which is hundreds of bytes large"). Content delivery networks absorb the hottest photos, so the traffic that reaches storage is precisely the long tail that misses — caching harder cannot fix it.

Haystack's answer was to attack the metadata itself: store many photos per file, shrink per-photo metadata until **all** of it fits in main memory, and accept at most one disk operation per read. The claimed payoff: each usable terabyte costs ~28% less and serves ~4x more reads per second than an equivalent NAS terabyte. The four stated goals were high throughput and low latency, fault tolerance (geographically distinct replicas), cost-effectiveness, and simplicity — the team built and deployed the production system in months.

## Three components: Directory, Cache, Store

```text
browser --1--> web server --2--> Directory
                        logical vol -> physical vols, cookie, CDN-or-Cache routing
URL:  http://<CDN>/<Cache>/<machine id>/<logical vol, photo>
browser --3--> CDN
                 | hit  -> serve image
                 | miss  4--> Cache (internal CDN; hash keyed by photo id)
                               | hit  -> 5 serve image
                               | miss  6--> Store machine: RAM index (key, alt key)
                                 7: seek + read whole needle (1 disk op)
                                 8: verify cookie + checksum   9: back to Cache  10: browser
```

The **Directory** is a replicated database (accessed via a PHP interface fronted by memcache) mapping logical volumes to physical volumes, load-balancing writes across logical volumes and reads across physical replicas, deciding per-photo whether requests route to the CDN or the internal Cache, and marking volumes read-only at machine granularity. New machines are write-enabled; when one fills, it flips read-only. The **Cache** caches a photo only if the request came from a user (not the CDN) and the photo lives on a write-enabled machine — recent photos are read and deleted most, so this shelters exactly the machines doing mixed reads and writes. Its hit rate ran near **80%**. The **Store** does one thing: given a logical volume id, key, alternate key, and cookie, return the photo bytes or an error.

## Volumes, needles, and the byte walk

A Store machine keeps its capacity as a handful of very large files — think a 100 GB `/hay/haystack_<logical volume id>` per physical volume — each a **superblock followed by a sequence of needles**, one needle per stored image. It holds an open file descriptor per volume plus an in-memory map from `(key, alternate key)` to the needle's flags, size, and file offset. XFS underneath keeps blockmaps small and RAM-resident (1 GB preallocated extents, 256 KB RAID stripes), so even filesystem-level metadata lookups avoid disk.

```text
volume file:  [ superblock ][ needle 1 ][ needle 2 ][ needle 3 ] ...   ~100 GB each
needle (paper Fig. 5 / Table 1):
+--------------+--------+-----------------+------------------+-------+------+
| header magic | cookie | key             | alternate key    | flags | size |
| (recovery)   | random | 64-bit photo id | 32-bit size id   | del   |      |
+--------------+--------+-----------------+------------------+-------+------+
| data (size bytes)                 | footer magic | data checksum        |
+-----------------------------------+--------------+----------------------+
| padding: total needle size aligned to 8 bytes                                 |
+-------------------------------------------------------------------------------+
```

The **key** is the 64-bit photo id; the **alternate key** is a 32-bit supplemental id distinguishing the four generated sizes (in decreasing order 'n', 'a', 's', 't'). The **cookie** is a random number assigned and stored by the Directory at upload time and embedded in the URL, so attackers cannot guess valid photo URLs by enumerating keys. The flags field carries the deleted status, and a data checksum guards integrity. The paper specifies exact widths for the key (64 bits), alternate key (32 bits), and the 8-byte alignment rule; Table 1 names the remaining fields without fixing their byte widths.

## All metadata in RAM, one disk op per read

A cache-miss read is: hash-lookup `(key, alternate key)` in RAM; if the entry says deleted, fail without touching disk; otherwise seek and read the entire needle in one operation (its size is computable ahead of time); verify the cookie and checksum after the read; return the data. The design target is "at most one disk operation per read," and the paper is honest about the corner case — a photo straddling an extent or RAID-stripe boundary costs a second op, made rare by the 1 GB extents and 256 KB stripes.

The RAM budget is the paper's most quoted math. Each uploaded image becomes four needles sharing one 64-bit key with four 32-bit alternate keys and four data sizes; the paper counts **32 bytes** of index state for the four, plus hash-table overhead, for **40 bytes per image** — and states Haystack uses on average **10 bytes of main memory per photo**. Two optimizations buy the last 20%: deleted photos are marked by setting offset to 0 (dropping the in-RAM flags entirely), and cookies are not kept in RAM at all — they are checked after the needle is read. The comparison point is an `xfs inode_t`: **536 bytes**. That ratio is why "buy enough RAM to cache all metadata" is impossible for per-file designs and trivial for Haystack.

| Metric                      | NFS-per-file design            | Haystack                    |
|-----------------------------|--------------------------------|-----------------------------|
| Disk ops per long-tail read | 3 (10+ with fat directories)   | 1 (0 for deleted/missing)   |
| Metadata in RAM per photo   | inode, hundreds of bytes (536) | 10 bytes average            |
| Metadata source             | filesystem inode + dirent      | checkpointed index file     |
| Where URL guessing is stopped| n/a                           | 32-bit+ cookie per photo    |

The **index file** makes restarts fast: it checkpoints the in-memory map as fixed records (64-bit key, 32-bit alternate key, currently unused flags, offset, size) appended asynchronously so writes and deletes stay fast. Needles can exist without index records ("orphans") — on boot the machine replays past the last checkpoint, appends records for orphans, then initializes its map from the index files. A deleted-but-stale index record is caught because the needle's flag is inspected after it is read.

## Write path, delete, compaction

Writes are append-only: each Store machine synchronously appends the needle and asynchronously appends its index record. Needles are never overwritten — a rotation writes a new needle with the same key, and the copy at the highest offset wins. Uploads are batched into **multi-writes** (users upload whole albums; production averaged 9.27 images per multi-write), which improved throughput by 30% at 4 images and 78% at 16. Each Store machine's RAID controller has an NVRAM write-back cache reserved entirely for writes: needles are written asynchronously and flushed with a single fsync per multi-write, holding write latency at a flat 1–2 ms. Disk caches are disabled so consistency survives crashes.

Deletes set a flag synchronously in both the in-memory map and the volume file; the space is reclaimed only by **compaction**, an online pass that copies live needles into a new file — skipping deleted and duplicate needles, applying deletes to both files — then blocks writes and atomically swaps files and in-memory structures. Deletes track views in shape: young photos are deleted far more often, and about **25% of photos** are deleted within a year. A background "pitchfork" task probes every Store machine (connectivity, volume availability, test reads) and read-onlys the volumes of bad ones; replacements are repaired via bulk sync from a replica — rare (a few per month) but slow, hours-long, and NIC-bound.

## RAID-6 plus replication, and what the traffic looked like

Each 2U storage blade packed 2 hyper-threaded quad-core Xeons, 48 GB RAM, a hardware RAID controller with 256–512 MB NVRAM, and 12 x 1 TB SATA drives giving ~9 TB usable as a RAID-6 partition. The paper's redundancy reasoning is worth quoting precisely: RAID-6 gives "adequate redundancy and excellent read performance while keeping storage costs down," with NVRAM absorbing the write penalty, while end-to-end durability comes from each photo being written to all physical volumes of its logical volume (three locations in production) in geographically distinct sites. On the synthetic benchmark (Randomio, random 64 KB direct-I/O reads) the device sustained 902.3 images/s; a fully loaded read-only Store machine (workload A, 201 volumes of 64 KB images) sustained 770.6 images/s — 85% of raw device throughput at only 17% higher latency, with whole-needle reads slightly larger than 64 KB and CPU idle between 92–96%.

The traffic table explains every design choice. News Feed and albums drive 98% of photo requests; popularity spikes for ~2 days, then collapses into the long tail. Daily: ~120M uploads become ~1.44B Haystack writes (4 sizes x 3 locations = 12x), 80–100B photo views, and only **10B Store reads — roughly 10% of all photo requests**, the rest absorbed by CDNs and the Cache. Small sizes dominate views (small 84.4%, thumbnails 10.2%, large 5.2%, medium 0.2%), so per-photo overhead multiplies across billions of tiny reads.

## SeaweedFS: the open-source descendant

SeaweedFS (Apache-licensed, Go, ~34k GitHub stars in August 2026) states its lineage directly: it "started by implementing Facebook's Haystack design paper," later adding erasure coding with ideas from Facebook's f4 paper. It keeps the two load-bearing ideas — needles packed into large append-only volume files, and metadata kept out of the read path — and re-scales the architecture: the central master manages only volumes, while volume servers own files and their metadata, yielding the README's claim of "faster file access (O(1), usually just one disk read operation)" with "only 40 bytes of disk storage overhead for each file's metadata."

```text
  client (app / S3 SDK / FUSE / Hadoop / WebDAV)
     | 1. POST /dir/assign -> fid + volume url        | 3. /dir/lookup?volumeId=3
     v                                                v    -> locations (cacheable)
  weed master :9333  <--register--  weed volume :8080   weed volume :8081
  assigns fids, tracks volumes,       /dir/1.dat + 1.idx     (needles, 8-byte pad)
  auto-failover between masters       in-memory/leveldb index modes
     |
     v optional layer
  weed filer :8888 -- directories + POSIX attrs in a pluggable store
     |                 (MySQL, Postgres, Redis, Cassandra, etcd, LevelDB, ...)
     |-- weed s3 :8333 (S3-compatible API)   |-- FUSE mount   |-- WebDAV
```

The file id is the read path. A fid like `3,01637037d6` splits into an unsigned **32-bit volume id**, an unsigned **64-bit file key**, and an unsigned **32-bit file cookie** ("used to prevent URL guessing"), both hex-encoded — 33 bytes as a string (`8+1+16+8`), or 16 bytes binary (`4+8+4`). Writing is two calls: `/dir/assign` returns a fid and a volume server URL, then the client POSTs the blob there; reading is a cacheable `/dir/lookup` by volume id (volumes rarely move) followed by a direct HTTP GET to the volume server. On disk each volume is a `.dat` data file plus a `.idx` checkpoint — the Haystack index-file idea — whose 8-byte superblock carries version, replication placement, TTL, and a compaction revision counter; the in-source constants match the heritage: a 16-byte needle header (cookie + 64-bit id + 32-bit size), 8-byte padding between files, and deletion as a negative-size tombstone reclaimed by automatic compaction.

What SeaweedFS adds beyond the paper is everything Haystack left to surrounding systems. The optional **filer** layers directories and POSIX attributes over the blob store using pluggable metadata stores, enabling FUSE mounts, an S3-compatible API, Hadoop compatibility, WebDAV, and a Kubernetes CSI driver; replication levels are rack- and datacenter-aware with automatic master failover (no single point of failure); TTLs expire files; tiered storage moves volumes across NVMe/SSD/HDD and a cloud tier with O(1) access; and warm volumes are erasure-coded with **RS(10,4)** — a 30 GB volume becomes 14 shards spread across disks, servers, and racks — after f4's insight that cold blobs want EC while hot blobs want replication.

| Aspect            | Haystack (OSDI '10)                    | SeaweedFS (docs + master branch)            |
|-------------------|----------------------------------------|---------------------------------------------|
| Read claim        | at most 1 disk op per photo read       | O(1) disk read, usually one disk read        |
| Metadata per file | 10 B in RAM (40 B per image)           | 40 bytes disk overhead per file              |
| Id                | logical vol + 64-bit key + 32-bit alt  | fid: 32-bit vol id + 64-bit key + 32-bit cookie |
| Anti-guessing     | random cookie, checked post-read       | 32-bit cookie in the fid                     |
| Index             | in-RAM map + async index file          | in-memory or LevelDB maps + .idx checkpoint  |
| POSIX / API       | none; Directory DB + app URLs          | filer, FUSE, S3, Hadoop, WebDAV, CSI         |
| Warm storage      | 3x replication only                    | replication on hot, RS(10,4) EC on warm      |
| Scaling           | Directory DB, read-only volume flips   | master group failover, pluggable filer store |

## Demo: pack needles, count disk ops, budget RAM

```python
# Deterministic Haystack-style needle store simulator (toy, not the real system).
# Field widths marked "paper" come from the OSDI'10 paper (64-bit key, 32-bit
# alternate key, 8-byte alignment). Fields the paper describes but does not
# give byte widths for are marked "demo width" -- illustrative only.
import random

rng = random.Random(2026)

FIELDS = [
    ("header magic", 2, "demo width"),
    ("cookie",       4, "demo width"),
    ("key",          8, "paper: 64-bit photo id"),
    ("alternate key",4, "paper: 32-bit supplemental id"),
    ("flags",        1, "demo width"),
    ("size",         4, "demo width"),
    ("data",         0, "variable (size bytes)"),
    ("footer magic", 2, "demo width"),
    ("checksum",     4, "demo width"),
    ("padding",      0, "paper: needle aligned to 8 bytes"),
]

FIXED = sum(w for _, w, _ in FIELDS)            # 29 B of fixed fields in this demo

def needle_bytes(data):
    fixed = FIXED + len(data)
    pad = (-fixed) % 8                          # align to 8 bytes (paper)
    return fixed + pad, pad

# 6 needles: 4 small (8 KB, thumbnails/small -- 84.4% of paper's views)
# and 2 large (64 KB, album views). Sizes per paper Section 4.4.2.
photos = []
for i in range(6):
    data = rng.randbytes(8192 if i < 4 else 65536)
    photos.append({"key": 0xA100 + i, "alt": 0x6E + i, "cookie": rng.getrandbits(32),
                   "data": data, "deleted": False})

volume = bytearray(b"\0" * 8)   # superblock (width not given in paper; demo 8 B)
index = {}                       # (key, alt) -> [offset, size]  (paper Table 2 fields)
total_overhead = 0
total_padding = 0
for p in photos:
    n, pad = needle_bytes(p["data"])
    index[(p["key"], p["alt"])] = [len(volume), n]
    volume += bytes([0xC1]) * n
    total_overhead += n - len(p["data"])
    total_padding += pad

print("=== Needle on-disk layout (paper Fig.5 + Table 1) ===")
for name, w, src in FIELDS:
    print(f"  {name:<13} {w:>2} B   {src}")
print(f"  fixed fields: {FIXED} B + data + padding-to-8 (key/alt key widths per Table 1)")

print("\n=== Volume pack ===")
print(f"  needles={len(photos)}  data={sum(len(p['data']) for p in photos)} B  "
      f"overhead={total_overhead} B  padding={total_padding} B  volume={len(volume)} B")

# Cache-miss read path. Haystack: RAM index lookup, then ONE disk op (whole
# needle); cookie + checksum verified after the read (paper 3.4.1/3.6.2).
# NFS baseline (paper Section 2.2): dir metadata + inode + file = 3 disk ops
# for a hit; misses still pay dir + inode = 2.
queries = [0, 1, 4, 99, 2]           # 2 will be deleted; 99 is missing
photos[2]["deleted"] = True          # paper 3.4.3: set flag in RAM + volume file
index[(photos[2]["key"], photos[2]["alt"])][0] = 0   # paper 3.6.2: offset 0 = deleted
print("\n=== Simulated CDN-miss reads (long tail) ===")
print("  query         haystack                        NFS baseline")
hs_ops = nfs_ops = 0
for q in queries:
    if q >= len(photos):
        h, note, n_ops, tag = 0, "hash miss, no disk op", 2, "miss"
    else:
        p = photos[q]
        off, n = index[(p["key"], p["alt"])]
        if off == 0:
            h, note, n_ops, tag = 0, "deleted flag in RAM, no disk op", 2, "miss"
        else:
            h, note, n_ops, tag = 1, "read whole needle once", 3, "hit"
    hs_ops += h
    nfs_ops += n_ops
    print(f"  photo-{q:<3} {tag:<5} {h} disk op, {note:<31}  {n_ops} disk ops")
print(f"  TOTALS: haystack={hs_ops}  nfs={nfs_ops}  ratio={nfs_ops / hs_ops:.1f}x")

print("\n=== Metadata RAM budget (paper Section 3.6.2 numbers) ===")
images = 260_000_000_000          # paper: 260B images = 65B photos x 4 sizes
per_photo, inode = 10, 536        # paper: 10 B/photo average; xfs inode_t = 536 B
hay, xfs = images * per_photo, images * inode
ram = 48 * 10**9                  # paper: 48 GB store-machine RAM (decimal)
print(f"  per image (4 needles): haystack 40 B vs xfs inode 536 B = {536 / 40:.1f}x")
print(f"  {images // 10**9}B images: index RAM {hay / 10**12:.2f} TB vs inode RAM {xfs / 10**12:.2f} TB")
print(f"  48 GB machines to hold ALL metadata in RAM: "
      f"{-(-hay // ram):.0f} (haystack) vs {-(-xfs // ram):.0f} (xfs inodes)")

print("\n=== Compaction (paper 3.4.3/3.6.1) ===")
del_bytes = sum(index[(p["key"], p["alt"])][1] for p in photos if p["deleted"])
print(f"  deleted needles hold {del_bytes} B -> online copy skips them, atomic swap")
print(f"  volume {len(volume)} -> {len(volume) - del_bytes} B  "
      f"(reclaim {del_bytes / len(volume) * 100:.1f}%; paper: about 25% of photos deleted per year)")
```

Real output (executed with python3):

```text
=== Needle on-disk layout (paper Fig.5 + Table 1) ===
  header magic   2 B   demo width
  cookie         4 B   demo width
  key            8 B   paper: 64-bit photo id
  alternate key  4 B   paper: 32-bit supplemental id
  flags          1 B   demo width
  size           4 B   demo width
  data           0 B   variable (size bytes)
  footer magic   2 B   demo width
  checksum       4 B   demo width
  padding        0 B   paper: needle aligned to 8 bytes
  fixed fields: 29 B + data + padding-to-8 (key/alt key widths per Table 1)

=== Volume pack ===
  needles=6  data=163840 B  overhead=192 B  padding=18 B  volume=164040 B

=== Simulated CDN-miss reads (long tail) ===
  query         haystack                        NFS baseline
  photo-0   hit   1 disk op, read whole needle once           3 disk ops
  photo-1   hit   1 disk op, read whole needle once           3 disk ops
  photo-4   hit   1 disk op, read whole needle once           3 disk ops
  photo-99  miss  0 disk op, hash miss, no disk op            2 disk ops
  photo-2   miss  0 disk op, deleted flag in RAM, no disk op  2 disk ops
  TOTALS: haystack=3  nfs=13  ratio=4.3x

=== Metadata RAM budget (paper Section 3.6.2 numbers) ===
  per image (4 needles): haystack 40 B vs xfs inode 536 B = 13.4x
  260B images: index RAM 2.60 TB vs inode RAM 139.36 TB
  48 GB machines to hold ALL metadata in RAM: 55 (haystack) vs 2904 (xfs inodes)

=== Compaction (paper 3.4.3/3.6.1) ===
  deleted needles hold 8224 B -> online copy skips them, atomic swap
  volume 164040 -> 155816 B  (reclaim 5.0%; paper: about 25% of photos deleted per year)
```

The three numbers to retain: one RAM hash lookup replaces all per-file metadata lookups (55 machines of RAM cover the whole 2010-era corpus for Haystack, versus thousands if each image paid inode rent); the needle read is one disk operation sized exactly to the data plus ~30 bytes; and deletion is O(1) with amortized reclamation — the same log-plus-index-and-compact pattern as [Bitcask](./bitcask.md) and LSM compaction (see [LSM Compaction](./lsm-compaction.md)), and the reason sorted-file layouts like the [SSTable](./sstable.md) are unnecessary when access is point-get-only.

## Interview questions

1. Why did one-file-per-photo fail at Facebook scale even with large caches, and what specifically did Haystack remove? — Per-file inodes/dirents cost hundreds of bytes of RAM and disk ops on the miss path; Haystack collapsed four sizes per image into needles sharing one 64-bit key inside one volume file, cutting metadata to 10 B/photo.
2. Walk the cache-miss read path. When can a "one disk operation" read cost more? — RAM lookup, whole-needle read, post-read cookie/checksum; it exceeds one op when a needle crosses extent or RAID-stripe boundaries (rare due to 1 GB extents), or when a stale index record hides a deleted needle.
3. Why is the cookie verified after reading from disk instead of stored in RAM? — It saves ~20% of index memory (together with the offset-0 delete trick); a wrong cookie wastes one read but cannot leak another user's photo, since cookies are random, Directory-assigned, and unguessable.
4. Why append-only volumes plus compaction instead of in-place updates? — Photos are write-once; appends turn random writes into sequential ones amortized by NVRAM and one fsync per multi-write, and deleted/overwritten needles are reclaimed by an online copy-and-swap compaction (~25% of photos die within a year).
5. In SeaweedFS, why can volume-server locations be cached aggressively by clients, and what does the fid encode? — The master maps volume id to locations and volumes rarely move, so lookups cache well; the fid encodes 32-bit volume id + 64-bit file key + 32-bit cookie, so no per-file metadata is needed until the volume server resolves key to offset in RAM.

## References

1. D. Beaver, S. Kumar, H. C. Li, J. Sobel, P. Vajgel. "Finding a Needle in Haystack: Facebook's Photo Storage." USENIX OSDI '10. <https://www.usenix.org/legacy/event/osdi10/tech/full_papers/Beaver.pdf> (PDF fetched; all paper numbers above from this text)
2. DBLP record conf/osdi/BeaverKLSV10 (venue, authors, year). <https://dblp.org/rec/conf/osdi/BeaverKLSV10.html>
3. SeaweedFS repository and README (architecture, O(1) claim, fid format, features). <https://github.com/seaweedfs/seaweedfs>
4. SeaweedFS wiki: Directories and Files (filer architecture). <https://github.com/seaweedfs/seaweedfs/wiki/Directories-and-Files>
5. SeaweedFS wiki: Erasure Coding for Warm Storage (RS(10,4), shard placement). <https://github.com/seaweedfs/seaweedfs/wiki/Erasure-coding-for-warm-storage>
6. SeaweedFS wiki: Tiered Storage (disk types, .idx placement, cloud tier). <https://github.com/seaweedfs/seaweedfs/wiki/Tiered-Storage>
7. SeaweedFS wiki: Amazon S3 API. <https://github.com/seaweedfs/seaweedfs/wiki/Amazon-S3-API>
8. S. Muralidhar et al. "f4: Facebook's Warm BLOB Storage System." USENIX OSDI '14 (basis for SeaweedFS warm-data EC). <https://www.usenix.org/system/files/conference/osdi14/osdi14-paper-muralidhar.pdf>
9. SeaweedFS wiki documentation index. <https://github.com/seaweedfs/seaweedfs/wiki>

> Related: [Object Storage](./object-storage.md), [Bitcask](./bitcask.md), [SSTable Format](./sstable.md), [Distributed Storage](./distributed.md), [LSM Compaction](./lsm-compaction.md).
