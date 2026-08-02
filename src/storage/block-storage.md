# Block Storage

## Overview

Block storage divides data into fixed-size blocks, each with a unique address, and presents them as raw volumes to the operating system. The OS manages these blocks using a filesystem (ext4, NTFS, XFS) or uses them directly (databases with O_DIRECT). Block storage is the foundation of traditional storage systems and cloud services like AWS EBS, Azure Managed Disks, and OpenStack Cinder.

## How Block Storage Works

### Block Device Abstraction

```mermaid
graph TD
    APP[Application] --> FS[Filesystem ext4/XFS/NTFS]
    FS --> BLK[Block Layer]
    BLK --> ELEVATOR[I/O Scheduler]
    ELEVATOR --> DRIVER[Device Driver]
    DRIVER --> DEVICE[Block Device]

    DEVICE --> HDD[HDD]
    DEVICE --> SSD[SSD]
    DEVICE --> SAN[SAN LUN]
    DEVICE --> CLOUD[Cloud Volume EBS]
```

- **Block Size**: Typically 512 bytes or 4 KB. The filesystem organizes blocks into files.
- **Block Address**: Each block has a Logical Block Address (LBA). LBAs are sequential integers starting from 0.
- **I/O Operations**: Read/write operations target specific LBAs with specific sizes.

### Block Storage vs Other Types

```mermaid
graph TD
    subgraph Block[Block Storage]
        B1[Raw blocks] --> B2[OS manages filesystem]
        B2 --> B3[Low latency, high performance]
    end
    subgraph File[File Storage]
        F1[Files in directories] --> F2[Server manages filesystem]
        F2 --> F3[Shared access, POSIX semantics]
    end
    subgraph Object[Object Storage]
        O1[Objects with metadata] --> O2[HTTP API access]
        O2 --> O3[Massive scale, eventual consistency]
    end
```

## Cloud Block Storage

### AWS Elastic Block Store (EBS)

```mermaid
graph TD
    EC2[EC2 Instance] -->|Attach| VOL[EBS Volume]
    VOL --> GP3[gp3: General Purpose SSD]
    VOL --> IO2[io2: Provisioned IOPS SSD]
    VOL --> ST1[st1: Throughput HDD]
    VOL --> SC1[sc1: Cold HDD]
```

| Volume Type | Max IOPS | Max Throughput | Latency | Cost | Use Case |
|-------------|----------|----------------|---------|------|----------|
| gp3 | 16,000 | 1,000 MB/s | ~1 ms | $0.08/GB/mo | Most workloads |
| io2 Block Express | 256,000 | 4,000 MB/s | ~0.5 ms | $0.125/GB/mo | Databases, critical apps |
| st1 | 500 | 500 MB/s | ~10 ms | $0.045/GB/mo | Big data, logs |
| sc1 | 250 | 250 MB/s | ~15 ms | $0.015/GB/mo | Cold data |

### EBS Snapshots

```mermaid
sequenceDiagram
    participant EC2
    participant EBS
    participant S3

    EC2->>EBS: Write data blocks
    EBS->>S3: Incremental snapshot (only changed blocks)
    Note over S3: Stored in S3 (compressed, encrypted)
    EBS->>S3: Next snapshot (incremental)
    Note over S3: Only new/changed blocks since last snapshot
```

- **Incremental**: Only changed blocks are copied, reducing time and storage cost.
- **Point-in-time**: Each snapshot is a consistent point-in-time copy.
- **Cross-region**: Snapshots can be copied to other regions for DR.

### OpenStack Cinder

```mermaid
graph TD
    VM[VM / Nova] -->|API| CINDER[Cinder Volume Service]
    CINDER --> DRIVER[Volume Driver]
    DRIVER --> LVM[LVM - Local]
    DRIVER --> CEPH[Ceph RBD]
    DRIVER --> NETAPP[NetApp ONTAP]
    DRIVER --> NFS[NFS Backend]
```

Cinder is OpenStack's block storage service. It provides a vendor-agnostic API for creating and managing block volumes.

## Volume Management

### Logical Volume Manager (LVM)

```mermaid
graph TD
    subgraph LVM[Linux LVM Architecture]
        PV1[Physical Volume: /dev/sda1] --> VG[Volume Group: my_vg]
        PV2[Physical Volume: /dev/sdb1] --> VG
        VG --> LV1[Logical Volume: /dev/my_vg/data - 100GB]
        VG --> LV2[Logical Volume: /dev/my_vg/logs - 50GB]
    end

    LV1 --> FS1[ext4 mounted at /data]
    LV2 --> FS2[XFS mounted at /logs]
```

LVM provides:
- **Striping**: Spread data across multiple physical volumes for performance.
- **Mirroring**: Duplicate data across physical volumes for redundancy.
- **Snapshots**: Copy-on-write snapshots of logical volumes.
- **Online resize**: Grow or shrink volumes without unmounting.

### RAID and Block Storage

```mermaid
graph TD
    subgraph RAID10[RAID 10]
        subgraph Mirror1[Mirror Pair 1]
            D1[Disk 1] -.-> D2[Disk 2]
        end
        subgraph Mirror2[Mirror Pair 2]
            D3[Disk 3] -.-> D4[Disk 4]
        end
        M1 --- M2[Stripe across mirrors]
    end
```

RAID is implemented at the block storage layer, providing redundancy and/or performance without the application knowing.

## Performance Optimization

### I/O Schedulers

```mermaid
graph LR
    REQ[I/O Requests] --> SCHED{I/O Scheduler}
    SCHED --> NONE[None/Noop - for NVMe/SSD]
    SCHED --> MQ[MQ-Deadline - for SSD]
    SCHED --> BFQ[BFQ - for HDD, fairness]
```

- **None/Noop**: Minimal overhead. Best for NVMe where the device handles scheduling.
- **MQ-Deadline**: Ensures requests are served within a deadline. Good for SSDs.
- **BFQ (Budget Fair Queuing)**: Provides fairness among processes. Good for HDDs and interactive workloads.

### Direct I/O vs Buffered I/O

```mermaid
sequenceDiagram
    participant App
    participant PageCache as OS Page Cache
    participant Disk

    Note over App,Disk: Buffered I/O (default)
    App->>PageCache: Write data
    PageCache-->>App: Acknowledge immediately
    PageCache->>Disk: Flush later (write-back)

    Note over App,Disk: Direct I/O (O_DIRECT)
    App->>Disk: Write data directly
    Disk-->>App: Acknowledge after write
```

- **Buffered I/O**: Uses OS page cache. Good for general workloads. Writes are acknowledged before hitting disk.
- **Direct I/O**: Bypasses page cache. Good for databases that manage their own cache. Ensures data reaches device.

## Interview Questions

1. **Q: What is block storage and how does it differ from file and object storage?**
   A: Block storage provides raw, fixed-size blocks with unique addresses. The OS manages the filesystem on top. File storage provides hierarchical files over a network protocol. Object storage provides flat-namespace objects accessed via HTTP APIs. Block storage offers the lowest latency and highest performance.

2. **Q: How do EBS snapshots work and why are they incremental?**
   A: EBS snapshots copy changed blocks to S3. The first snapshot copies all blocks. Subsequent snapshots only copy blocks that changed since the last snapshot. This saves time and storage cost. Snapshots are crash-consistent (unless using application-consistent snapshots with flush).

3. **Q: When would you use O_DIRECT vs buffered I/O?**
   A: Use O_DIRECT when the application manages its own cache (databases like PostgreSQL, MySQL) to avoid double caching. Use buffered I/O for general applications that benefit from OS page cache. O_DIRECT requires aligned buffers and I/O sizes.

4. **Q: Explain LVM and its benefits for block storage management.**
   A: LVM (Logical Volume Manager) abstracts physical disks into volume groups, which are divided into logical volumes. Benefits: online resize, striping across multiple disks for performance, mirroring for redundancy, and copy-on-write snapshots. It decouples logical volumes from physical disk layout.

5. **Q: How does RAID 10 compare to RAID 5 for a database workload?**
   A: RAID 10 (mirror + stripe) provides better write performance (no parity calculation), faster rebuild times (just mirror), and consistent performance. RAID 5 has better usable capacity but slower writes (parity overhead) and dangerous rebuild times with large disks. For databases, RAID 10 is preferred.

## Common Mistakes

- Not provisioning enough IOPS for database workloads — EBS gp3 baseline is 3,000 IOPS; databases often need 10,000+.
- Using snapshots as backups without testing restores — snapshots are incremental and depend on the chain.
- Not aligning partitions to block boundaries — misalignment causes double writes.
- Using buffered I/O for databases — leads to double caching (OS cache + database buffer pool).
- Ignoring I/O scheduler choice — NVMe with BFQ adds unnecessary overhead.

## Summary

Block storage provides raw, addressable blocks that the OS organizes into files. It offers the lowest latency and highest performance of the three storage types. Cloud services like EBS provide managed block volumes with different performance tiers. Key concepts include LVM for volume management, RAID for redundancy, I/O schedulers for request ordering, and the buffered vs direct I/O trade-off.

## Cross-References

- [HDD](./hdd.md) — Mechanical block storage device
- [SSD](./ssd.md) — Flash-based block storage
- [NVMe](./nvme.md) — High-performance block interface
- [Object Storage](./object-storage.md) — Object-based alternative
- [File Storage](./file-storage.md) — File-based alternative
- [Storage Overview](./overview.md) — Storage hierarchy
- [Cloud EBS](../cloud/aws/s3.md)

