# Solid State Drives (SSD)

## Overview

Solid State Drives (SSDs) use NAND flash memory to store data persistently without moving parts. They revolutionized storage by eliminating mechanical latency, enabling random I/O operations that are 100-1000× faster than HDDs. Understanding SSD internals — NAND cells, FTL, wear leveling, and TRIM — is critical for systems design interviews.

## How SSDs Work

### NAND Flash Fundamentals

```mermaid
graph TD
    subgraph NAND[NAND Flash Cell]
        G[Gate] -->|controls| CH[Channel]
        FG[Floating Gate / Charge Trap] -->|stores charge| CH
        S[Source] --> CH --> D[Drain]
    end

    FG -->|High charge = 0| Z[Logical 0]
    FG -->|Low charge = 1| O[Logical 1]
```

Data is stored as electrical charge in floating gate transistors. The amount of charge determines the bit value.

### NAND Cell Types

| Type | Bits/Cell | Endurance (P/E Cycles) | Cost | Speed | Use Case |
|------|-----------|------------------------|------|-------|----------|
| SLC (Single-Level) | 1 | 50,000–100,000 | Highest | Fastest | Enterprise, cache |
| MLC (Multi-Level) | 2 | 3,000–10,000 | High | Fast | Enterprise |
| TLC (Triple-Level) | 3 | 1,000–3,000 | Moderate | Moderate | Consumer |
| QLC (Quad-Level) | 4 | 500–1,000 | Lowest | Slowest | Read-heavy, archival |

```mermaid
graph LR
    subgraph SLC[SLC: 1 bit/cell]
        S0[0] --- S1[1]
    end
    subgraph MLC[MLC: 2 bits/cell]
        M0[00] --- M1[01] --- M2[10] --- M3[11]
    end
    subgraph TLC[TLC: 3 bits/cell]
        T0[000] --- T1[001] --- T2[...] --- T8[111]
    end
```

More bits per cell = more capacity = slower writes = lower endurance (more charge levels to distinguish).

### SSD Architecture

```mermaid
graph TD
    subgraph SSD[SSD Internal Architecture]
        HOST[Host Interface SATA/NVMe] --> CTRL[SSD Controller]
        CTRL --> FTL[Flash Translation Layer]
        CTRL --> DRAM[DRAM Cache]
        FTL --> NAND1[NAND Channel 0]
        FTL --> NAND2[NAND Channel 1]
        FTL --> NAND3[NAND Channel N]
    end

    NAND1 --> PKG[Flash Packages]
    PKG --> DIE[Dies]
    DIE --> PLANE[Planes]
    PLANE --> BLOCK[Blocks]
    BLOCK --> PAGE[Pages]
```

**Hierarchy**: SSD → Channels → Packages → Dies → Planes → Blocks → Pages

- **Page**: Smallest read/write unit (4 KB, 8 KB, or 16 KB).
- **Block**: Smallest erase unit (256 KB–4 MB, containing 64–512 pages). You must erase an entire block before rewriting.
- **Plane**: Contains multiple blocks. Planes can operate in parallel.

### The Write Problem: Erase Before Write

```mermaid
sequenceDiagram
    participant Host
    participant FTL
    participant NAND

    Host->>FTL: Write 4KB to LBA 100
    FTL->>FTL: Map LBA 100 → new physical page
    FTL->>NAND: Write 4KB to new page (no erase needed if free)
    FTL->>FTL: Old page marked as stale

    Note over FTL,NAND: When block is full of stale pages...
    FTL->>NAND: Garbage Collection: read valid pages
    FTL->>NAND: Erase entire block
    FTL->>NAND: Rewrite valid pages to new block
```

This is **write amplification** — the SSD writes more data than the host requested.

## Flash Translation Layer (FTL)

The FTL is the SSD's "operating system." It translates logical block addresses (LBAs) from the host to physical NAND locations.

### Address Mapping

```mermaid
graph LR
    subgraph Host[Host View]
        LBA0[LBA 0] --- LBA1[LBA 1] --- LBA2[LBA 2]
    end
    subgraph FTL[FTL Mapping Table]
        M0[LBA 0 → Block 5, Page 12]
        M1[LBA 1 → Block 2, Page 7]
        M2[LBA 2 → Block 8, Page 3]
    end
    subgraph NAND[Physical NAND]
        B2[Block 2] --- B5[Block 5] --- B8[Block 8]
    end
```

- **Page-level mapping**: One entry per page. Flexible but requires large mapping table (1 GB DRAM per 1 TB SSD).
- **Block-level mapping**: One entry per block. Smaller table but requires reading entire block for small writes.
- **Hybrid mapping**: Uses both. Hot data uses page-level, cold data uses block-level.

### Wear Leveling

NAND cells degrade with each Program/Erase (P/E) cycle. Wear leveling distributes writes evenly:

```mermaid
graph TD
    A[Write Request] --> WL[Wear Leveling Algorithm]
    WL --> B{Block Wear Level}
    B -->|Low wear| C[Use this block]
    B -->|High wear| D[Skip, use lower-wear block]
    C --> E[Update FTL mapping]
    D --> E
```

- **Dynamic wear leveling**: Only moves data between blocks with different wear levels.
- **Static wear leveling**: Also moves cold data from low-wear blocks to high-wear blocks, freeing low-wear blocks for writes.

### Garbage Collection (GC)

```mermaid
graph TD
    B1[Block with mix of valid and stale pages] --> GC[Garbage Collector]
    GC --> R[Read valid pages from block]
    R --> W[Write valid pages to new block]
    W --> E[Erase original block]
    E --> F[Block now free for new writes]
```

GC is triggered when free blocks are low. It causes:
- **Write amplification**: Extra reads and writes.
- **Performance degradation**: GC competes with host I/O.
- **Over-provisioning**: SSDs reserve 7-28% extra capacity for GC workspace.

### TRIM Command

```mermaid
sequenceDiagram
    participant OS
    participant SSD

    OS->>SSD: Delete file (TRIM LBA range)
    SSD->>FTL: Mark pages as invalid
    Note over FTL: GC can now skip these pages
    Note over SSD: Reduces write amplification
```

Without TRIM, the SSD doesn't know which pages are no longer needed by the OS, leading to unnecessary garbage collection.

## SSD Performance Characteristics

### Latency Breakdown

| Operation | HDD | SATA SSD | NVMe SSD |
|-----------|-----|----------|----------|
| Random Read (4K) | 5-15 ms | 0.05-0.1 ms | 0.02-0.05 ms |
| Random Write (4K) | 5-15 ms | 0.02-0.1 ms | 0.01-0.03 ms |
| Sequential Read | 100-250 MB/s | 500-560 MB/s | 3,000-7,000 MB/s |
| Sequential Write | 100-250 MB/s | 400-530 MB/s | 2,000-5,000 MB/s |
| Random Read IOPS | 75-200 | 90,000-100,000 | 500,000-1,000,000 |

### Performance Degradation Factors

1. **Write Amplification**: GC causes extra writes. Typical ratio: 2-5×.
2. **GC Pauses**: Periodic stalls when GC runs. Can cause latency spikes.
3. **Full Drive**: Performance drops as free blocks decrease. Keep 10-20% free.
4. **Sustained Writes**: After SLC cache fills, TLC/QLC write speed drops dramatically.

```mermaid
graph LR
    A[Sustained Write Speed] --> B[SLC Cache Phase]
    B --> C[TLC Direct Write Phase]
    C --> D[GC Affected Phase]

    B -.->|2000-3000 MB/s| B1[Fast]
    C -.->|300-800 MB/s| C1[Moderate]
    D -.->|50-200 MB/s| D1[Slow]
```

## SSD vs HDD Decision Framework

```mermaid
graph TD
    Q1{Random I/O heavy?}
    Q1 -->|Yes| SSD[Use SSD]
    Q1 -->|No| Q2{Latency sensitive?}
    Q2 -->|Yes| SSD
    Q2 -->|No| Q3{Cost per TB critical?}
    Q3 -->|Yes| HDD[Use HDD]
    Q3 -->|No| Q4{Sequential bulk storage?}
    Q4 -->|Yes| HDD
    Q4 -->|No| SSD
```

## Interview Questions

1. **Q: Why can't you overwrite data in place on an SSD?**
   A: NAND flash requires erasing before writing, and erase operations work on entire blocks (256 KB–4 MB), not individual pages (4–16 KB). The FTL handles this by writing new data to a different page and updating the mapping, then erasing blocks during garbage collection.

2. **Q: What is write amplification and how do SSDs mitigate it?**
   A: Write amplification is the ratio of actual NAND writes to host writes. It occurs because GC must copy valid pages before erasing blocks. Mitigations include over-provisioning (extra free space), TRIM (OS tells SSD which pages are unused), and improved GC algorithms.

3. **Q: Explain the SSD performance cliff during sustained writes.**
   A: Consumer SSDs use a portion of NAND in SLC mode as a write cache. When this fills (typically 5-50 GB), writes go directly to TLC/QLC NAND, which is 3-10× slower. Some drives also trigger aggressive GC, further reducing speed.

4. **Q: Why does SSD performance degrade as the drive fills up?**
   A: Fewer free blocks mean GC must run more frequently and copy more valid data per erase cycle. This increases write amplification and GC pauses. Keeping 10-20% of the drive free maintains performance.

5. **Q: What is wear leveling and why is it necessary?**
   A: NAND cells have limited P/E cycles (500-100K depending on type). Without wear leveling, frequently written blocks would fail quickly while others remain fresh. Wear leveling distributes writes evenly across all blocks, maximizing drive lifespan.

## Common Mistakes

- Assuming SSDs never wear out — NAND has limited write endurance (TBW rating).
- Ignoring TRIM support — without it, SSDs can't efficiently reclaim deleted space.
- Not accounting for write amplification in capacity planning.
- Using consumer SSDs for write-heavy enterprise workloads.
- Assuming all SSDs have similar performance — controller, NAND type, and over-provisioning vary dramatically.

## Summary

SSDs store data in NAND flash cells using trapped charge. The FTL translates logical addresses to physical locations and handles wear leveling and garbage collection. Key trade-offs: more bits per cell = higher density but lower endurance and speed. Performance is affected by write amplification, GC, and drive fullness. For interviews, understand the erase-before-write constraint, the FTL's role, and why SSDs are 100-1000× faster than HDDs for random I/O.

## Cross-References

- [HDD](./hdd.md) — Mechanical alternative
- [NVMe](./nvme.md) — High-performance SSD interface
- [Erasure Coding](./erasure-coding.md) — Redundancy for SSD arrays
- [Storage Overview](./overview.md) — Storage hierarchy
- [Latency Numbers](../interview/system-design/latency-numbers.md)

