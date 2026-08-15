# Tiered Storage, Persistent Memory, and Disaggregated Architectures

> Builds on [../tiered-storage.md](../tiered-storage.md), [../nvme.md](../nvme.md), and [../nvmeof.md](../nvmeof.md). This file covers storage-class memory (SCM), persistent memory programming (PMem, DAX), NVMe over Fabrics internals, RDMA storage access, disaggregated and computational storage, and smart NIC storage offload.

## Storage-Class Memory and Persistent Memory

### The Memory-Storage Gap

```
Latency spectrum (2024):
  L1 cache:       1 ns
  L2 cache:       4 ns
  L3 cache:      10 ns
  DRAM:         100 ns     ← volatile, byte-addressable
  ──── gap ────
  Optane PMem:  300 ns     ← persistent, byte-addressable
  NVMe SSD:   25,000 ns (25 µs)
  SATA SSD:  100,000 ns (100 µs)
  HDD:     5,000,000 ns (5 ms)
```

Persistent memory (PMem, formerly known as NVDIMM) sits between DRAM and SSDs: persistent like a disk but byte-addressable like memory. Intel Optane DC Persistent Memory was the first mainstream PMem product (now discontinued, but the architecture is widely studied).

### PMem Programming Models

**Mode 1: Memory-mapped (DAX)**

```
Direct Access (DAX) bypasses the page cache:
  1. Map PMem file with mmap(MAP_SYNC)
  2. Direct load/store to the mapped address
  3. No system calls for reads or writes
  4. Persistence requires explicit clwb / sfence / clflushopt

C example:
  int *arr = mmap(NULL, size, PROT_READ|PROT_WRITE,
                  MAP_SHARED|MAP_SYNC, fd, 0);
  arr[42] = 100;
  _mm_clwb(&arr[42]);   // flush cache line to PMem
  _mm_sfence();         // ensure ordering
  // Now arr[42] == 100 is persistent across power loss
```

**Mode 2: App-direct (filesystem on PMem)**

PMem is used as a block device via a DAX-enabled filesystem (ext4-DAX, XFS-DAX). Applications get the benefit of persistence through `fsync()` and standard file I/O, plus low latency for page-cache hits. The DAX flag eliminates double-caching (page cache + PMem).

### PMem Libraries

- **libpmemobj**: C library providing a persistent heap with transactions (TXN begin/commit/abort). Allocates persistent objects via `pmemobj_alloc()`. Provides snapshots for undo logging within a transaction.
- **libpmem**: Low-level C library for `pmem_memcpy_persist()`, `pmem_memset_persist()`, which combine memcpy/memset with cache-line flushes.
- **PMDK (Persistent Memory Development Kit)**: Intel's open-source library suite. Includes libpmem, libpmemobj, libpmemblk, libpmemlog.

### Transactional Persistence

```
PMDK Transaction Example:
  TX_BEGIN(pop):
    old_val = *ptr;
    TX_ADD(ptr);  // register for undo log
    *ptr = new_val;
    other_ptr = pmemobj_alloc(...);  // auto-rolled back on abort
  TX_END

  On crash between TX_ADD and TX_END:
    Recovery: undo log restores *ptr to old_val
    other_ptr allocation is rolled back
```

> **Interview Angle**: "Why did Intel Optane DC PMem fail commercially?" (1) Price per GB was still 3-5× DRAM. (2) Performance gap vs DRAM was significant (~3× latency). (3) Most workloads could use DRAM caching to get 90% of the benefit. (4) Required application rewrite (DAX, clwb, MAP_SYNC). (5) CXL memory expansion provides a cheaper alternative for capacity. The technology is still used in specialized HPC and database workloads (e.g., SAP HANA on PMem).

## NVMe over Fabrics (NVMe-oF) Deep Dive

### Protocol Architecture

```
NVMe-oF transports NVMe commands over a network fabric:

  Application
      │
  NVMe driver (host)
      │  NVMe queue pair (SQ/CQ)
  ──── fabric boundary ────
  NVMe-oF transport (RDMA, TCP, FC)
      │  Capsule (NVMe cmd + optional data)
  ──── fabric boundary ────
  NVMe controller (target)
      │  Converts to local NVMe or emulated
  Storage device
```

### Transport Comparison

| Transport | Max Latency | Max Throughput | RDMA? | Uses |
-----------|------------|----------------|-------|------|
| NVMe/RDMA (RoCEv2) | 5-15 µs | 200 Gbps+ | Yes | On-prem HPC, AI clusters |
| NVMe/RDMA (iWARP) | 10-20 µs | 100 Gbps | Yes | Legacy data centers |
| NVMe/TCP | 20-50 µs | 100 Gbps | No | Cloud, commodity networks |
| NVMe/FC | 10-20 µs | 128 Gbps | No | Enterprise SANs |

### RDMA Storage Access

RDMA (Remote Direct Memory Access) allows a host to read/write memory on a remote machine without involving the remote CPU. Three RDMA operations are relevant for storage:

```
1. SEND/RECV: Like TCP but kernel-bypass. Used for NVMe command submission.

2. RDMA READ: Initiator reads from responder's memory.
   Used for: NVMe data transfer (read command response).
   Initiator posts RDMA Read with remote addr/key → NIC fetches data directly.

3. RDMA WRITE: Initiator writes to responder's memory.
   Used for: NVMe data transfer (write command data).
   Initiator posts RDMA Write with data + remote addr/key → NIC pushes data.

NVMe-oF with RDMA (no RDMA READ for write data):
  1. Host constructs NVMe cmd (WRITE)
  2. Host posts RDMA WRITE of data to target's buffer (specified in SGL)
  3. Host posts SEND of NVMe cmd capsule
  4. Target processes: data already in buffer (RDMA WRITE arrived)
  5. Target writes data to local storage
  6. Target posts SEND of completion capsule
```

Key advantage of RDMA: **zero-copy I/O**. Data moves directly between host memory and target memory via NIC DMA, never touching the target's CPU caches. This reduces latency and CPU utilization dramatically compared to iSCSI or NFS.

### In-Capsule vs SGL Data

```
In-capsule data (small I/Os, ≤ ~16 KB):
  NVMe command capsule contains both the command AND the data.
  One RDMA SEND. No separate RDMA WRITE needed.
  Latency: ~5 µs (one round trip for command + data).

SGL-based data (large I/Os):
  NVMe command specifies Scatter-Gather List with remote memory addresses.
  Host issues RDMA WRITE for data, then SEND for command.
  Latency: ~10-15 µs (RDMA WRITE + SEND).
```

## Disaggregated Storage

### What is Disaggregation?

Traditional rack: each server has local CPU + memory + storage. **Disaggregation** separates these into independent resource pools connected by a high-speed fabric (CXL, NVMe-oF, RDMA).

```
Traditional:          Disaggregated:
┌──────────┐         ┌──────────┐  ┌──────────┐  ┌──────────┐
│ CPU      │         │  CPU     │  │  Memory  │  │  Storage  │
│ Memory   │         │  Pool    │  │  Pool    │  │  Pool     │
│ Storage  │         └────┬─────┘  └────┬─────┘  └────┬─────┘
└──────────┘              │              │              │
                         └──────────┬───┘──────────────┘
                              CXL / NVMe-oF / RDMA Fabric
```

### CXL (Compute Express Link) for Memory and Storage

CXL 3.0 enables a shared memory fabric where multiple CPUs can access the same memory expansion modules coherently. For storage:

- **CXL.mem**: Memory expansion. A CXL-attached memory device acts as additional DRAM or PMem accessible from any CXL host. Much lower latency than NVMe-oF (100s of ns vs 10s of µs).
- **CXL.io**: PCIe-like I/O. NVMe devices can be accessed over CXL.
- **Storage use case**: A "memory box" in the rack provides 2 TB of CXL-attached memory. A database uses this as a large buffer pool, reducing NVMe reads. On failure, data is lost (volatile) — must be flushed to NVMe.

### Disaggregated Storage Architectures

| System | Architecture | Fabric | Notable Feature |
--------|-------------|--------|-----------------|
| AWS Nitro | EBS storage offload via Nitro card | PCIe (card) | Separates control plane from data plane |
| Azure Phantom | Disaggregated compute + storage | Proprietary | Local SSDs act as cache, remote NVMe-oF for capacity |
| Google | Colossus (disaggregated FS) | Jupiter fabric | Separate metadata and data servers |
| Ceph + NVMe-oF | OSDs with NVMe-oF backend | RDMA | Disaggregated OSD from compute |
| Meta Tectonic | Disaggregated storage | RDMA | Separated caching, metadata, capacity tiers |

## Computational Storage

### The Problem

For analytics on large datasets, the traditional approach is: read all data from storage → transfer over network → process on CPU. The bottleneck is often the **data movement**, not the computation.

### Computational Storage Architecture

```
Traditional:                          Computational:
 Storage → Network → CPU             Storage + compute unit
  10 TB read over 100 Gbps:            Process in-place, output 1 GB:
  100s / (100 × 10^9 / 8) ≈ 800 s      Avoids 99.9% of data transfer
```

**Computational Storage Drive (CSD)**: An SSD with an embedded ARM/FPGA processor that can execute compute kernels directly on the drive. The host sends a filter/predicate, and the drive returns only matching data.

```
SQL: SELECT count(*) FROM events WHERE region='us-east' AND year=2024

With CSD:
  1. Host sends: {region='us-east', year=2024, aggregate=COUNT}
  2. CSD scans NVMe NAND, applies filter locally
  3. CSD returns: count=42 (a few bytes, not 10 TB)
```

**Computational Storage Processor (CSP)**: A separate compute unit attached to storage (not inside the drive). Can be an FPGA or smart NIC. More flexible than CSD (standard Linux environment) but higher latency.

### NVMe Computational Storage Command Set

SNIA defines the **NVMe Computational Programs** specification. NVMe commands are extended with:

- **Submit Command**: Host sends a compute program (bytecode) + input/output buffer descriptors to the CSD.
- **Fetch Results**: Host retrieves output buffers after completion.

### Real-World Examples

| System | Type | Use Case |
--------|------|----------|
| Samsung SmartSSD | CSD (ARM) | Video transcoding, DB filtering |
| ScaleFlux CSD | CSD | Real-time compression, dedup |
| NGD Systems | CSD (FPGA) | AI inference on stored data |
| Vigilant (Microsoft) | CSP | Byzantine storage verification |

### Challenges

- **Programming model**: No standard API. Developers must write kernels for specific hardware.
- **Data movement to/from CSD**: Small I/Os may not benefit if the overhead of shipping code exceeds data savings.
- **Ecosystem**: Limited tooling, no widespread framework support (unlike GPU compute).
- **Cost**: CSDs are more expensive than equivalent-capacity SSDs.

## Smart NIC Storage Offload

Smart NICs (BlueField DPU, AWS Nitro, Intel IPU) can offload storage protocol processing from the host CPU:

```
Offloaded operations:
  - NVMe-oF target (DPU acts as NVMe initiator/target)
  - iSCSI target
  - RDMA transport handling
  - Compression/decompression
  - Encryption (AES-XTS for data at rest)
  - CRC/checksum verification
  - O fencing and access control

Benefit: Host CPU saves ~1-2 cores worth of cycles on storage I/O processing.
In a rack with 40 servers, this saves 40-80 cores.
```

> **Interview Angle**: "How would you reduce storage I/O latency for a distributed database in a data center?" (1) Use NVMe-oF with RDMA (RoCEv2) for remote storage access at ~10 µs. (2) Deploy persistent memory (CXL-attached) as the write buffer / WAL tier — 300 ns writes. (3) Use computational storage for index scans and filter pushdown. (4) Smart NIC (DPU) offloads NVMe-oF and encryption. The stack becomes: DRAM (hot rows) → CXL PMem (WAL, indexes) → NVMe-oF (warm data) → object store (cold data). Each tier adds ~10× latency but 10× capacity.
