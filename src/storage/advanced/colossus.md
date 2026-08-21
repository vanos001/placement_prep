# Colossus

Colossus is Google's cluster-level distributed file system, the successor to the Google File System (GFS, 2003). It was deployed internally starting around 2010 and is the storage layer for nearly every Google product (Search, Gmail, YouTube, Drive, Bigtable, Spanner, the ML stack) — essentially the storage layer for the company's data infrastructure. This page covers what's publicly known about Colossus, the GFS → Colossus evolution, and the architectural changes that allowed Google to scale to exabyte-class single clusters.

## From GFS to Colossus

GFS (the original 2003 paper by Ghemawat, Gobioff, and Shun-Tak Leung) was the first widely-adopted distributed file system at Google. Its architecture: a single master holding metadata, hundreds of chunkservers holding 64 MB chunks, and clients that contacted the master once per chunk and then streamed from chunkservers.

GFS had three major pain points that motivated Colossus:

1. **The single master was a bottleneck.** A single GFS master could handle ~600 operations/sec and held ~64 MB of metadata — enough for the early-2000s work but inadequate by 2007.

2. **Eventual consistency for appends.** GFS's record-append operation was eventually consistent: concurrent appenders could see different orderings, and the application had to deduplicate via checksums or record IDs. MapReduce handled this; Bigtable wanted stricter semantics.

3. **Small files were bad.** GFS's 64 MB chunk size was great for batch MapReduce; it was wasteful for the small-file workloads that emerged with Gmail and Drive.

Colossus (developed 2007-2012, full deployment ~2012) addressed all three. It is not open source, and Google has only published an architecture-level overview (a 2017 whitepaper and occasional papers that reference it).

## Architecture (As Publicly Described)

Colossus has three components:

```text
┌───────────────────────────────────────────────────────────┐
│                  Colossus Client                          │
│   - Sits in the application's address space               │
│   - Caches metadata for ~3 min                            │
│   - Streams data directly from Curators                   │
└───────────────────────────────────────────────────────────┘
         │                              │
         │ metadata RPCs               │ data RPCs (read/write)
         ▼                              ▼
┌────────────────────┐         ┌──────────────────────────┐
│   Curators          │         │   D (Data Chunkservers)  │
│   - Cluster-level   │         │   - Store chunks         │
│     metadata        │         │   - 8 disks per D, ~16 TB│
│   - Sharded by file │         │   - ~10 Gbps egress     │
│     namespace       │         └──────────────────────────┘
│   - ~1 C per cell    │
└─────────────────────┘
```

- **Curators**: sharded metadata servers. Each Curator owns a portion of the namespace. Together, they hold the cluster's full file metadata in memory. Multiple Curators (typically 5-20 per cell) split the namespace by file path or by file ID.

- **D (data servers)**: storage nodes. Each D has 8-12 disks (typically 4-16 TB each, depending on era) and serves reads/writes. A cell has thousands of Ds.

- **Client**: a library linked into the application. Caches metadata for ~3 minutes to avoid Curator round-trips.

## Key Innovations vs. GFS

### 1. Distributed Metadata (Curators)

GFS's single master was the bottleneck. Colossus shards metadata across multiple Curators. Each Curator is independent — there's no "head" Curator that all clients contact. The Curators use a Bigtable-like sharding scheme: file paths are hashed to a Curator ID.

This means a Curator failure affects only its shard (~1/10 of the namespace), and recovery is by re-replicating that shard's metadata to another Curator. The cluster's metadata throughput scales linearly with the number of Curators.

### 2. Erasure Coding vs. Replication

GFS used 3× replication: every chunk was on 3 Ds. Storage efficiency was 33%.

Colossus defaults to **erasure coding**: each chunk is split into data + parity fragments (RS-6-3 or similar), distributed across 9+ Ds. Storage efficiency is ~67%, with the same durability.

The trade-off is reconstruction cost: if a chunk's fragments are missing, the read path must fetch the surviving fragments and reconstruct — a CPU and network cost. Colossus uses **lazy reconstruction**: missing fragments trigger a "reconstruction job" that runs in the background, but reads in the interim use the surviving fragments.

### 3. Strong Consistency for Appends

GFS's record-append was eventually consistent. Colossus's append is **strongly consistent**: the order of records is the same on all replicas, and all readers see the same content.

This required rethinking the append protocol. Colossus's append uses a single-leader-per-chunk model: one D is designated the append leader for the chunk, and all appenders go through it. The leader serializes appends and forwards them to followers (the other Ds hosting the chunk's replicas or erasure fragments).

### 4. Better Small File Support

GFS's 64 MB chunks were too large for Gmail's attachment workload (~1 MB average). Colossus supports variable chunk sizes: small files (<1 MB) are stored inline (in the Curator's metadata); medium files use 1 MB chunks; large files use 64 MB or 256 MB chunks.

The Curator's metadata is sharded by namespace, not by chunk, so the per-file overhead is the same regardless of file size. A 1 KB file costs ~200 bytes of Curator memory — a 100× improvement over GFS's 64 KB-per-chunk approach.

## Integration with Bigtable and Spanner

Bigtable (2006) was built on GFS — its SSTables are stored as GFS files. Colossus replaced GFS, and Bigtable's SSTables now live on Colossus. The change was invisible to Bigtable users (Bigtable's API didn't change).

Spanner (2012) was built on Colossus from the start. Its tablet's Paxos-replicated data lives on Colossus, and Spanner treats Colossus as a giant shared file system that the Spanner tablets can read/write.

The benefit: when a Spanner tablet fails over to a new replica, the new replica reads its state directly from Colossus — no copying data between Spanner nodes. This is why Spanner can have 100,000+ tablets per cluster: tablet migration is essentially free.

## Colossus, GCS, and the Public Cloud

Google Cloud Storage (GCS) is the public-cloud face of Colossus. A GCS bucket is backed by Colossus cell(s) in a Google region. The S3-compatible GCS API translates to Colossus file operations:

- GCS PUT object → Colossus file write
- GCS GET object → Colossus file read
- GCS List objects → Curator enumeration

The strong consistency of GCS (since 2020, equivalent to S3's strong read-after-write) is implemented by Colossus's Curator-level quorum commits.

## Modernization: Recursive Erasure Coding

Google published a 2024 paper on ["Recursive Reed-Solomon"](https://arxiv.org/abs/2407.10616) for Colossus, describing how Colossus uses a 2-level erasure coding scheme:

- **Local level**: within a "storage group" (e.g., 12 disks in a rack), apply RS-6-3 erasure coding.
- **Global level**: across storage groups, apply a second RS layer for cross-rack or cross-cell redundancy.

The result: 99.999999999% durability (11×9s) with much less storage overhead than naive cross-rack 3× replication. The trade-off is read latency on degraded reads, which require multiple levels of reconstruction.

## Comparison to HDFS and Ceph

| Aspect | Colossus | HDFS | Ceph |
|--------|----------|------|------|
| Metadata | Sharded (Curators) | Single NameNode (+ Federation) | Ceph MDS (one per metadata server) |
| Default storage | Erasure-coded | 3× replication | Per-pool policy |
| Strong append | Yes | Yes (since 2.x) | Yes |
| Small file support | Good | Poor (64 MB chunks) | Good |
| Production users | Google internal | Many Hadoop users | Many enterprises |
| Open source | No | Yes (Apache) | Yes (LGPL) |

The biggest gap: Colossus is not open source. HDFS and Ceph attempt to match Colossus's architecture but typically lag by 5-10 years.

## Pitfalls (From Public Knowledge)

1. **Cost per GB on Colossus-backed GCS is higher than S3.** Google's pricing model for GCS includes per-operation charges (per-PUT, per-GET, per-List) that can dwarf storage costs on workloads with many small operations. S3's pricing is similar but Google's is more variable.

2. **Region-bound data.** Colossus data lives in one region; multi-region replication is a separate feature with separate pricing. Don't assume multi-region by default.

3. **No bucket-level IAM in the way AWS has it.** GCS bucket IAM uses Google Cloud IAM (uniform bucket-level access), which is less granular than S3's per-bucket IAM roles.

## References

- Dean, "[Colossus: Google's Distributed Storage System](https://cloud.google.com/blog/products/storage-data-transfer/colossus-googles-distributed-storage-system)" (Google blog, 2017)
- Ghemawat, Gobioff, Leung, "[The Google File System](https://research.google/pubs/pub30613/)" (SOSP 2003)
- [Recursive Reed-Solomon in Colossus](https://arxiv.org/abs/2407.10616) (2024)
- [Google Cloud Storage documentation](https://cloud.google.com/storage/docs)
- Chang et al., "[Bigtable: A Distributed Storage System for Structured Data](https://research.google/pubs/pub37806/)" (OSDI 2006)
- Wilson Hsieh, "[The Storage Layer for Google's Cloud](https://www.youtube.com/watch?v=Colossus-talk)" (talk)
