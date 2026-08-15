# Storage Internals: QoS, GC, Crash Consistency, and Checksums

> This file covers operational concerns that storage engine developers and SREs must understand: quality of service, garbage collection in storage engines, crash consistency mechanisms, torn write prevention, atomic writes, and end-to-end checksums.

## Storage Quality of Service (QoS)

### The Noisy Neighbor Problem

In multi-tenant storage systems (cloud block storage, shared Ceph cluster), one tenant's workload can degrade another's latency and throughput. This is the **noisy neighbor problem**.

```
Scenario: Ceph cluster shared between two tenants
  Tenant A: streaming reads, 2 GB/s sustained, low priority
  Tenant B: OLTP, 10K IOPS, requires P99 < 5 ms

  If both compete for the same OSDs:
    Tenant A's sequential I/O saturates the disk queue
    Tenant B's random I/Os wait behind large sequential reads
    Tenant B P99 latency spikes to 50+ ms
```

### QoS Mechanisms

**I/O throttling (Linux cgroups v2, blkio)**:

```
# Limit a cgroup to 1000 IOPS and 50 MB/s on /dev/sda

echo "1000 0" > /sys/fs/cgroup/tenant-b/io.max
  # format: "rbps wbps riops wiops"
  # 0 = unlimited for that dimension

# Ceph OSD-level QoS (per-OSD op throttle):
osd_op_threads = 2
osd_op_num_shards = 5
osd_client_op_priority = 63  # higher = more priority
```

**Proportional I/O scheduling (blk-mq)**:

The `bfq` (Budget Fair Queueing) I/O scheduler provides per-cgroup I/O bandwidth guarantees by assigning time budgets. Each cgroup gets a proportional share of the disk's time.

| Scheduler | Mechanism | Best For |
-----------|-----------|----------|
| none | FIFO | High-throughput sequential, NVMe (device handles queuing) |
| mq-deadline | Deadline + read/write FIFO | Avoiding starvation, predictable latency |
| bfq | Fair queueing by cgroup | Multi-tenant, QoS-sensitive |
| kyber | Adaptive budgeting | Predictable tail latency |

**Ceph QoS**: Ceph implements per-pool and per-client QoS using the `osd_mclock_scheduler` (Reef+). The mClock algorithm (Gulati et al., FAST 2010) assigns each I/O operation a reservation (minimum), limit (maximum), and weight (proportional share). This is more flexible than simple rate limiting.

```
Ceph mClock profiles:
  client_qos:
    # Per-client overrides
    client.12345:
      reservation: 100 IOPS
      limit: 500 IOPS
      weight: 2.0  (relative share when idle capacity available)
```

## Garbage Collection in Storage Engines

### LSM Garbage Collection (Compaction)

Compaction in LSM trees is the GC mechanism: old versions of keys and deleted keys are physically removed. As covered in [../lsm-compaction.md](../lsm-compaction.md), compaction is I/O-intensive and competes with foreground reads/writes.

### Compaction Scheduling

```
Compaction scheduling strategies:

1. Background-only (RocksDB default):
   - Compaction runs in background threads
   - Foreground writes write to memtable (no blocking)
   - If L0 grows too large, write stall triggers
   - Stall thresholds: L0 slow down at 8 files, stop at 12 files

2. Priority-based:
   - User-specified column families get priority compaction
   - RocksDB: compaction_priority = kHigh, kLow, kNormal

3. Rate-limited compaction:
   - RocksDB: compaction_read_size_limit, max_background_compactions
   - Limit compaction bytes/sec to leave I/O for foreground

4. Online compaction (TiKV/CockroachDB approach):
   - Compaction is scheduled across the cluster
   - Only one replica compacts at a time per range
   - Others serve traffic, then rotate
```

### SSD Internal GC

SSDs also have internal GC: when a block needs to be rewritten, valid pages are moved to a fresh block and the old block is erased. This is the FTL (Flash Translation Layer) garbage collector.

```
SSD GC interaction with LSM compaction:

  LSM writes 100 MB during compaction → SSD receives 100 MB
  SSD FTL may trigger GC internally → writes additional 50 MB
  Total write amplification: 1.5× at SSD level

  Combined WA = LSM WA × SSD WA
  Example: 20× (LSM leveled) × 1.5× (SSD) = 30× total
  This is why SSD endurance matters for write-heavy LSM workloads
```

**TRIM / DISCARD**: Filesystems can notify the SSD that a logical block is no longer used (`fstrim`, `BLKDISCARD`). The SSD can skip copying those blocks during GC, reducing SSD write amplification. Essential for LSM engines that delete data during compaction.

## Crash Consistency

### The Torn Write Problem

A torn write occurs when a power failure or crash leaves a write partially completed. For example, writing a 4 KB block on HDD: the sector may be written in multiple 512-byte sub-sectors. If power fails mid-write, some sub-sectors have new data and others have old data.

```
Torn write on 4 KB block (8 × 512B sectors):
  Before: [A][A][A][A][A][A][A][A]
  Writing: [B][B][B]...POWER FAIL
  After:  [B][B][B][A][A][A][A][A]  ← TORN! Neither old nor new state.
```

On SSDs, torn writes happen at the **page level** (typically 4-16 KB per NAND page). If the controller loses power during a multi-page program operation, some pages may contain garbage.

### Prevention Mechanisms

**Atomic writes (hardware)**:

- NVMe **Compare-and-Write** command: Writes two disjoint ranges atomically. The device verifies a compare pattern before writing. Useful for implementing lock-free metadata updates.
- SCSI **Atomic Write (16)**: Writes up to 512 KB atomically on devices that support it.
- Linux **`O_DIRECT` + `fallocate(FALLOC_FL_KEEP_SIZE)`**: Not hardware atomic, but the filesystem journal ensures consistency.

**Journaling / WAL (software)**:

Write the intent (metadata change) to a journal/WAL first, then apply to the data structure. On crash, replay the journal. See [../wal.md](../wal.md) for full details.

**Copy-on-Write (ZFS, Btrfs)**:

Never modify in place. Write new blocks, then atomically update the root pointer. The old blocks are valid until the root switches, so no torn state is possible (at the cost of write amplification).

```
Crash consistency comparison:

  Mechanism       | Overhead      | Torn-write safe? | Recovery cost
  --------------- | ------------- | ---------------- | --------------
  None (raw disk) | None          | No               | Data loss
  Journaling      | 2× write (meta)| Yes              | Replay journal
  WAL (DB-level)  | 1-2× write    | Yes              | Replay WAL
  Copy-on-Write   | 1.5-3× write  | Yes              | No replay needed
  Shadow paging   | 1× write      | Yes              | No replay needed
```

### Power-Loss Protection (PLP)

Enterprise SSDs include PLP hardware: a capacitor or tantalum capacitor that provides enough power (~10-50 ms) for the SSD controller to flush its DRAM cache to NAND on power loss. Without PLP, a sudden power loss can corrupt the FTL mapping table (stored in DRAM).

```
PLP sequence on power loss:
  1. Power loss detected (voltage drop below threshold)
  2. SSD controller switches to PLP capacitor power
  3. Flush DRAM write cache to NAND (FDIR — Flash Device Internal Rebuild)
  4. Flush FTL mapping table to NAND
  5. Capacitor drains → safe shutdown

Consumer SSDs often lack PLP → risk of data loss on power failure.
Always use PLP-equipped SSDs for databases and critical workloads.
```

## End-to-End Checksums

### Why End-to-End?

Checksums must be verified at **every layer** to detect corruption at any point in the I/O path:

```
Application data
  → application-level checksum (e.g., PostgreSQL page checksum)
  → WAL checksum (WAL record integrity)
  → filesystem checksum (ZFS fletcher4, Btrfs crc32c)
  → block device checksum (NVMe end-to-end data protection, T10 DIF)
  → network checksum (TCP, RDMA)
  → storage device checksum (SSD ECC, HDD CRC)
```

### T10 DIF (Data Integrity Field)

T10 DIF adds a 8-byte protection information tag to each 512-byte logical block:

```
512 bytes data + 8 bytes DIF:
  +----+----+----+----+----+----+----+----+
  | Guard Tag (2B) | App Tag (2B) | Ref Tag (4B) |
  +----+----+----+----+----+----+----+----+

  Guard Tag: CRC-16 or CRC-64 over the 512B data block
  App Tag: application-defined (can be PostgreSQL page LSN)
  Ref Tag: logical block reference (detects misdirected writes)
```

T10 DIF can operate in three modes:
- **DIF Type 1**: Guard + Ref Tag (LBA). Detects misdirected writes.
- **DIF Type 2**: Guard + App Tag. Application controls the tag.
- **DIF Type 3**: Guard only. Minimal overhead.

NVMe supports **End-to-End Data Protection** (similar to DIF): the host attaches a protection information field to each command, and the controller verifies it on read and computes it on write.

### Ceph Checksums

Ceph BlueStore stores a checksum (crc32c by default, optional xxHash) for every 4 KB – 16 KB block of each object. The checksum is stored in the onode's extent map (in RocksDB).

```
BlueStore read path with checksum:
  1. Client requests object range
  2. BlueStore looks up extent in onode (RocksDB)
  3. Read physical blocks from block device
  4. Compute checksum of each block
  5. Compare with stored checksum
  6. If mismatch: report I/O error, trigger scrub/snap repair
```

Ceph's scrubbing process (weekly by default) reads all objects and verifies checksums. Deep scrub also verifies that replicas have identical data content.

### Bitrot Detection

Bitrot is the gradual, silent corruption of data on storage media (cosmic rays, NAND charge leakage, HDD surface degradation). It is distinct from total device failure — the device appears healthy but returns wrong data.

| System | Checksum Algorithm | Check Frequency | Detection Scope |
--------|-------------------|-----------------|-----------------|
| ZFS | fletcher4, SHA-256 | On every read + periodic scrub | Per-block |
| Btrfs | crc32c | On every read + periodic scrub | Per-block |
| Ceph BlueStore | crc32c, xxHash | On read + scrub | Per-object block |
| MinIO | HighwayHash | On every read | Per-object |
| ext4 (metadata) | crc32c | On journal replay | Metadata only |

> **Interview Angle**: "How would you detect and handle silent data corruption in a distributed storage system?" (1) Per-block checksums stored alongside data (not in the data block itself). (2) Verify on every read (detect at access time). (3) Periodic scrub reads all data and verifies checksums (detect before access). (4) On detection: reconstruct from replica or parity (erasure coding). (5) Log the event and alert. (6) Optionally verify cross-replica consistency (deep scrub). ZFS does this natively. For cloud storage, compute checksum client-side and verify on read-back.