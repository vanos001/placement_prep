# Memory Management

Memory management is one of the most critical subsystems of an operating system. It handles the allocation, tracking, and回收 of primary memory (RAM), ensuring efficient utilization while providing process isolation and protection.

## Why Memory Management Matters

Every program needs memory to store instructions, data, and stack frames. The OS must:

1. **Allocate** memory to processes when needed
2. **Protect** each process's memory from others
3. **Share** memory efficiently when appropriate
4. **Reclaim** memory when processes terminate
5. **Virtualize** limited physical memory across many processes

## Memory Hierarchy

```mermaid
graph TD
    A[CPU Registers] -->|~1 ns| B[L1 Cache]
    B -->|~2-4 ns| C[L2 Cache]
    C -->|~5-12 ns| D[L3 Cache]
    D -->|~50-100 ns| E[Main Memory - RAM]
    E -->|~5-10 ms| F[SSD / NVMe]
    F -->|~5-10 ms| G[HDD / Disk]
    
    style A fill:#ff6b6b,color:#fff
    style B fill:#ffa94d,color:#fff
    style C fill:#ffd43b,color:#000
    style D fill:#69db7c,color:#000
    style E fill:#4dabf7,color:#fff
    style F fill:#9775fa,color:#fff
    style G fill:#868e96,color:#fff
```

| Level | Size | Latency | Managed By |
|-------|------|---------|------------|
| Registers | ~1 KB | <1 ns | Compiler/CPU |
| L1 Cache | 32-64 KB | ~1 ns | Hardware |
| L2 Cache | 256 KB-1 MB | ~4 ns | Hardware |
| L3 Cache | 4-64 MB | ~12 ns | Hardware |
| RAM | 4-512 GB | ~100 ns | OS + Hardware |
| SSD | 256 GB-4 TB | ~100 μs | OS + Firmware |
| HDD | 1-20 TB | ~5-10 ms | OS + Firmware |

## Address Translation

The fundamental challenge: programs use **logical (virtual) addresses**, but hardware needs **physical addresses**. The Memory Management Unit (MMU) translates between them.

```mermaid
graph LR
    A[CPU] -->|Virtual Address| B[MMU]
    B -->|Physical Address| C[Physical Memory]
    B -.->|TLB Hit| D[TLB Cache]
    D -.->|Fast Lookup| B
    
    style A fill:#4dabf7,color:#fff
    style B fill:#ff6b6b,color:#fff
    style C fill:#69db7c,color:#000
    style D fill:#ffa94d,color:#fff
```

## Key Concepts Across This Section

### Allocation Strategies
- **[Contiguous Allocation](./contiguous.md)** — Simplest approach; processes get consecutive physical blocks
- **[Paging](./paging.md)** — Fixed-size blocks; eliminates external fragmentation
- **[Segmentation](./segmentation.md)** — Variable-size segments matching program structure

### Page Table Management
- **[Page Tables](./page-tables.md)** — Core data structures for address translation
- **[TLB](./tlb.md)** — Hardware cache for page table entries
- **[Multi-Level Page Tables](./multi-level-page-tables.md)** — Hierarchical tables to save space
- **[Inverted Page Tables](./inverted-page-tables.md)** — One entry per physical frame

### Advanced Techniques
- **[Huge Pages](./huge-pages.md)** — Larger page sizes for reduced TLB misses
- **[Swapping](./swapping.md)** — Moving pages to/from disk
- **[mmap](./mmap.md)** — Memory-mapped files and anonymous mappings
- **[NUMA](./numa.md)** — Non-Uniform Memory Access architectures

### Allocator Implementations
- **[Allocation Algorithms](./allocation-algorithms.md)** — First-fit, best-fit, worst-fit
- **[Buddy System](./buddy-system.md)** — Power-of-2 splitting/merging allocator
- **[Slab Allocator](./slab-allocator.md)** — Kernel object caching

## Linux Memory Architecture

```mermaid
graph TB
    subgraph "User Space"
        A[Process A - Virtual Memory]
        B[Process B - Virtual Memory]
        C[Process C - Virtual Memory]
    end
    
    subgraph "Kernel Space"
        D[Virtual Memory Manager]
        E[Page Frame Allocator]
        F[Slab Allocator]
        G[Buddy System]
        H[Swap Manager]
    end
    
    subgraph "Hardware"
        I[MMU + TLB]
        J[Physical RAM - Page Frames]
        K[Swap Space - Disk]
    end
    
    A --> D
    B --> D
    C --> D
    D --> E
    D --> F
    D --> H
    E --> G
    F --> G
    G --> J
    H --> K
    I -.-> D
    I -.-> J
    
    style A fill:#4dabf7,color:#fff
    style B fill:#4dabf7,color:#fff
    style C fill:#4dabf7,color:#fff
    style D fill:#ff6b6b,color:#fff
    style J fill:#69db7c,color:#000
    style K fill:#868e96,color:#fff
```

## Quick Reference: Key Terms

| Term | Definition |
|------|-----------|
| **Frame** | Fixed-size physical memory block |
| **Page** | Fixed-size virtual memory block |
| **Page Fault** | Accessing a page not in physical memory |
| **TLB** | Translation Lookaside Buffer (page table cache) |
| **MMU** | Memory Management Unit (hardware translator) |
| **Working Set** | Set of pages a process actively uses |
| **Thrashing** | Excessive page faults degrading performance |
| **COW** | Copy-on-Write — defer copying until modification |
| **NUMA** | Non-Uniform Memory Access architecture |
| **OOM** | Out of Memory — kernel kills processes |

## Interview Focus Areas

1. **Paging vs Segmentation** — trade-offs, why paging won
2. **Page fault handling** — step-by-step from trap to return
3. **TLB** — what happens on miss, TLB reach
4. **Thrashing** — causes, detection, solutions
5. **Virtual to physical translation** — walk through the hardware
6. **Linux `/proc/meminfo`** — understanding each field
7. **malloc vs mmap** — when the kernel uses each
8. **Copy-on-Write** — fork() optimization mechanics

## Study Path

```mermaid
graph LR
    A[Contiguous] --> B[Paging]
    B --> C[Page Tables]
    C --> D[Multi-Level PT]
    B --> E[Segmentation]
    C --> F[TLB]
    D --> G[Huge Pages]
    B --> H[Demand Paging]
    H --> I[Page Replacement]
    H --> J[Thrashing]
    B --> K[mmap]
    B --> L[Swapping]
    
    style A fill:#4dabf7,color:#fff
    style B fill:#ff6b6b,color:#fff
    style H fill:#ffa94d,color:#fff
```

Start with contiguous allocation (simplest), then paging (modern standard), then build up to advanced topics.


## Cross References

- [Virtual Memory](../os/virtual-memory/README.md)
- [Cache Hierarchy](../arch/memory-hierarchy/README.md)
- [Buffer Pool](../dbms/caching/buffer-pool.md)
- [DRAM](../arch/memory-tech/dram.md)
