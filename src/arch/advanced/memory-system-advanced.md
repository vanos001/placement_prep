# Advanced Memory Systems

## Overview

The memory subsystem is the primary bottleneck in most workloads. This chapter covers the advanced techniques that modern processors use to predict and prefetch data, make intelligent cache replacement decisions, schedule DRAM commands optimally, and handle the physical reliability challenges of modern DRAM including RowHammer and refresh management.

## Hardware Prefetching

### Why Hardware Prefetching Matters

```
Memory latency hierarchy:
  L1 hit:           ~4 cycles
  L2 hit:           ~12 cycles
  L3 hit:           ~40 cycles
  DRAM access:      ~200-400 cycles
  NVM (Optane):     ~1000+ cycles
  Network (remote): ~10000+ cycles

OoO windows hide ~100-600 cycles of latency.
Hardware prefetching can hide the remaining gap.

On SPECint2017:  prefetching contributes 15-30% of total performance.
On server workloads (graph, databases): up to 50%.
```

### Stream Prefetcher (Next-Line / Sequential)

The simplest and most universal prefetcher detects sequential access patterns:

```
Stream Prefetcher:
  On cache miss to address A:
    Start tracking stream: A, A+64, A+128, A+192, ...
    Prefetch A+64 on next miss to same region
    Prefetch A+128 after that
    Degree: 4-16 lines ahead (configurable per Intel microcode)
    Stop on: branch misprediction, TLB miss, eviction of tracked stream

Accuracy: ~90% (most code has sequential hot paths)
Coverage: ~60% of all misses (many patterns aren't sequential)
```

### Stride Prefetcher

Detects fixed-stride (but non-unit-stride) patterns common in structured data access:

```
Stride detection:
  Track last N miss addresses per PC
  Compute differences: delta[i] = addr[i] - addr[i-1]
  If delta is consistent (e.g., always +256): stride = 256
  
  Example:
    for (i = 0; i < N; i++)
      sum += array[i].field;  // stride = sizeof(struct)
    
    Misses: &array[0].field, &array[1].field, &array[2].field
    Deltas: 64, 64, 64 → stride = 64
    Prefetch: &array[3].field, &array[4].field, ...
```

Intel's implementation uses a **stride detection table** indexed by load PC, storing the last access address and stride.

### Markov Prefetcher

Learns **address correlation** — when access A is followed by access B, learn this transition and prefetch B when A is seen again:

```
Markov Prefetch Table:
  Key: current miss address (or page+offset)
  Value: list of next addresses seen after this key, with confidence

Example (linked list traversal):
  Access pattern: A → B → C → D → E → ...
  Table learns: A→{B, confidence=5}, B→{C, confidence=5}, ...
  When A is accessed again, prefetch B, then when B arrives, prefetch C.

Accuracy: ~40-60% (many false correlations)
Coverage: captures pointer-chasing patterns that stride/stream miss
```

### Next-Page Prefetcher

Optimizes for page-table-walk latency by prefetching the next page's PTEs:

```
On TLB miss for page P:
  Walk page table: PML4 → PDPT → PD → PT → PTE
  Prefetch: PTE for page P+1 (and P+2, P+3)
  Saves: 4 memory accesses (the page table walk) on subsequent page crossings

Intel's implementation: "PDE Prefetcher" in L2
AMD: "Page Access Miss (PAM) prefetcher"
```

### Prefetcher Hierarchy in Modern CPUs

| Processor | L2 Prefetcher | L3/LLC Prefetcher | Notes |
-----------|--------------|-------------------|-------|
| Intel Golden Cove | Stream + stride + ML-based | Stream + stride | ML prefetcher learns patterns | 
| AMD Zen 4 | Stream + stride + spatial | Stream | Spatial prefetcher prefetches within page |
| Apple M2 | Stream + stride | Stream + ML-based | Aggressive prefetching contributes to high single-thread |
| ARM Cortex-X3 | Stream + stride | Stream | Configurable via system registers |

### Software Prefetching

Compilers and programmers can insert explicit prefetch instructions:

```c
// x86 intrinsics
__builtin_prefetch(&array[i + 16], 0, 3);  // read prefetch, high temporal locality
__builtin_prefetch(&array[i + 16], 1, 0);  // write prefetch, no temporal locality

// ARM
__builtin_prefetch(&data[i + 8]);
```

| Factor | Guidance |
--------|----------|
 **Distance ahead** | Enough to hide memory latency but not so far the line is evicted before use. Typically 16-64 cache lines ahead for sequential access. |
 **Write vs read** | Prefetch for read (into cache) for most cases. Write-prefetch only when you'll overwrite the entire line (avoids read-for-ownership). |
 **When to use** | When hardware prefetcher fails (irregular patterns, pointer chasing with known structure). Avoid over-prefetching (pollutes cache, wastes bandwidth). |

> **Interview Angle**: "When would you use software prefetching instead of relying on hardware?" Hardware prefetchers handle sequential and stride patterns well. Software prefetching is needed for: (1) irregular access patterns the hardware can't detect, (2) latency-critical code where you know the access pattern at compile time, (3) when the hardware prefetcher is causing cache pollution that you want to avoid.

## Cache Replacement Policies

### Beyond LRU

Classic LRU is too expensive to implement exactly for large associativities (needs O(ways) bits of state and comparison per access). Modern CPUs use approximations:

#### PLRU (Pseudo-LRU)

```
Tree-based PLRU for 8-way associative:
  Bit tree: 7 bits per set (log2(8) × (8-1) / 1... actually log2(8!) ≈ 15 bits... simplified to 7)
  
  Each internal node remembers which subtree was accessed last.
  On access: walk tree, flipping bits toward the accessed way.
  On eviction: walk tree in opposite direction to find victim.
  
  Approximation quality: ~10% miss rate increase vs. true LRU
  Hardware cost: (ways - 1) bits per set
```

#### DRRIP (Dynamic Re-Reference Interval Prediction)

Intel uses DRRIP in the L3 cache. The key insight: **not all lines should be treated the same**. Lines that are accessed once (streaming data) should be evicted quickly; lines accessed multiple times (working set) should be protected.

```
DRRIP uses 3-bit saturating counters (RRPV values) per cache line:

  Initial insertion: RRPV = 2^N - 1 (e.g., 7 for 3-bit counter)
    → For "bimodal" lines, start at 7 (near eviction)
    → For lines predicted to be reused, start at 3 (protected)

  On access (hit):  RRPV = 0  (most recently used)
  On miss (no 0s):  increment all RRPVs (aging)
  Evict: line with highest RRPV

Bimodal Insertion Policy (BIP):
  With probability p (e.g., 1/32): insert at high RRPV (will be evicted soon)
  With probability (1-p): insert at RRPV = 0 (protected)
  This gives streaming data a chance to be evicted quickly.

Set Duplication (SDP):
  On some misses, duplicate the line into a nearby set
  Provides a second chance without extra metadata.
```

#### LRU vs. PLRU vs. DRRIP Comparison

| Policy | Miss Rate (relative to optimal) | Storage | Used by |
--------|-------------------------------|---------|---------|
 True LRU | 1.0× (baseline) | O(ways!) per set | Theoretical |
 PLRU | 1.1–1.2× | (ways-1) bits | Some embedded |
 DRRIP | 0.95–1.05× | 3 bits per line | Intel L3, AMD L3 |
 SRRIP | 1.0× | 3 bits per line | AMD Zen 2+ L2 |
 Hawkeye | 0.90× | 3 bits + PC | Research |

## DRAM Scheduling

### The DRAM Command Problem

DRAM has strict timing constraints between commands:

```
DRAM Timing Parameters (DDR5 example):
  tRCD:  Activate → Read/Write       ~14 ns (e.g., 32 clocks at 2400 MT/s)
  tCL:   CAS latency                  ~14 ns
  tRP:   Precharge → Activate         ~14 ns
  tRAS:  Activate → Precharge         ~33 ns
  tRC:   Full row cycle (tRCD + tRP)  ~47 ns
  tFAW:  4-bank activate window       ~27 ns

A single DDR5 chip: 8 banks, 32K rows per bank
Access to same row (row buffer hit):  just CAS (~14 ns)
Access to different row (row buffer miss): ACT + CAS (~28 ns)
Access to different bank: can pipeline (overlap ACT and CAS)
```

### Row-Buffer Locality

```
DRAM Row Buffer (per bank):
  When a row is opened (ACTIVATE), the entire row is loaded into the row buffer
  Subsequent accesses to the same row: row buffer HIT (just CAS, ~14 ns)
  Access to a different row: row buffer MISS (PRECHARGE + ACTIVATE + CAS, ~47 ns)

Row buffer hit rate is THE most important DRAM performance metric:
  100% row buffer hits:  bandwidth = 1/tCL = ~71 GB/s per channel
  0% row buffer hits:   bandwidth = 1/tRC = ~21 GB/s per channel
  
  3.4× bandwidth difference!
```

### Memory Controller Scheduling Policies

| Policy | Description | Best For | |
--------|-------------|----------|---|
 **FCFS** | First-come, first-served | Fairness, simple | |
 **FR-FCFS** | Prioritize row buffer hits, then oldest-first | Balanced (default in most controllers) | |
 **PAR-BS** | Pair row buffer hits with opposite bank misses | Maximum row buffer hits | |
 **ATLAS** | Stall-time aware scheduling | QoS-sensitive workloads | |

```
FR-FCFS Example:
  Pending requests: [Bank0: row miss, Bank1: row hit, Bank2: row miss]
  
  FR-FCFS: Issue Bank1 (row hit) first, then Bank0 and Bank2
  (Row hits have higher priority regardless of arrival order)
```

### Bank-Level Parallelism

```
DDR5: 32 banks (8 bank groups × 4 banks per group)

Time: 0    10    20    30    40    50    60 (ns)
       |ACT  |CAS  |     |ACT  |CAS  |     |ACT  |CAS
  Bank 0: |---->|---->|     |---->|---->|     |---->|---->|
  Bank 1:      |---->|---->|     |---->|---->|     |---->|---->|
  Bank 2:           |---->|---->|     |---->|---->|     |---->|---->|

Staggered activates to different banks → pipelined access
Effective latency amortized across banks
```

## RowHammer

### The Problem

Repeatedly activating (opening) a DRAM row can cause bit flips in **adjacent rows** due to electromagnetic coupling between cells:

```
RowHammer mechanism:
  Repeatedly ACTIVATE row N:
  → Row N's wordline is charged/discharged thousands of times
  → Electromagnetic interference disturbs adjacent rows N-1 and N+1
  → Charge leaks from cells in N-1, N+1
  → After ~10K-1M activations (depending on DDR generation): bit flip!

DDR4:  vulnerable at ~140K activations per 64ms refresh interval
DDR5:  vulnerable at ~500K activations (improved, but still vulnerable)
LPDDR5: vulnerable at ~200K activations
HBM2e: vulnerable at ~1M activations (best, due to TSV structure)
```

### RowHammer Attack Patterns

```
Single-sided:  Hammer row N → disturbs N-1 and N+1
Double-sided:  Hammer rows N-1 and N+1 → disturbs row N (both sides)

Double-sided is ~2× more effective.

Attacker pseudocode:
  // Double-sided hammer
  addr_a = base + (target_row - 1) * row_size
  addr_b = base + (target_row + 1) * row_size
  for i in range(1_000_000):
    *addr_a  // ACTIVATE row target-1
    *addr_b  // ACTIVATE row target+1
  // Check target_row for bit flips
```

### Mitigations

| Mitigation | Mechanism | Performance Impact | Used by |
-----------|-----------|-------------------|----------|
 **TRR (Target Row Refresh)** | Controller tracks activation counts; refreshes adjacent rows when threshold approached | ~1-3% | Intel/AMD platforms with DDR4/5 |
 **ECO (Error Check Offset)** | ECC-like per-row checksums | ~2% area | Some DDR5 modules |
 **Counter-based** | Count activations per row; throttle or proactively refresh | ~2-5% | Modern DDR5 controllers |
 **Probabilistic Row Activation** | Randomly skip some activations | Minimal | Research |
 **In-memory ECC** | Detect and correct single-bit flips | 6.25% DRAM overhead | Server DDR5 (ECC DIMMs) |

> **Interview Angle**: "What is RowHammer and how is it mitigated?" RowHammer is a DRAM vulnerability where repeatedly activating a row causes bit flips in physically adjacent rows due to charge leakage. Mitigations include Target Row Refresh (the controller tracks activation counts and proactively refreshes nearby rows), in-DRAM ECC, and reduced activation rates. It's relevant for cloud providers and security-critical applications.

## DRAM Refresh Mechanisms

### Why DRAM Needs Refreshing

```
DRAM cell: one transistor + one capacitor
  Capacitor holds charge representing 0 or 1
  Charge leaks over time (thermal noise, radiation)
  Must be read and rewritten (refreshed) before charge decays below threshold

Retention time:
  DDR4:  64 ms at 85°C (guaranteed minimum)
  DDR5:  64 ms at 85°C (same, but some cells degrade faster)
  LPDDR5X: 32 ms at 85°C (mobile, more aggressive)
  HBM3:  32 ms at 85°C
```

### Refresh Overhead

```
For 8Gb DDR4 (128K rows, 8 banks):
  Refresh interval: 64 ms
  Rows to refresh per interval: 128K rows
  Refresh command takes: ~350 ns (tRFC)
  Commands needed: 128K / 8192 (rows per refresh burst) = ~8 refresh bursts
  Time spent refreshing: 8 × 350 ns = 2.8 μs per 64 ms
  Overhead: 2.8 μs / 64 ms = 0.004% — sounds tiny!

But: during refresh, the entire bank is unavailable for ~350 ns
  With 8 banks refreshed sequentially: total unavailable time is 8 × 350 ns
  Any request to a refreshing bank must wait → latency spike
```

### Refresh Techniques

| Technique | Description | Benefit |
-----------|-------------|---------|
 **Auto-Refresh** | Controller issues REF commands at fixed intervals | Standard, simple |
 **Self-Refresh** | DRAM handles its own refresh (low-power mode) | Saves power during idle |
 **Fine-Grained Refresh** | Refresh fewer rows per command, spread across time | Reduces per-bank unavailability |
 **Refresh Management (RFM)** | Intel's technique: schedule refreshes during idle periods | Minimizes impact on active workloads |
 **Read-Level Tracking** | Some DDR5 chips track which rows are weakest | Only refresh weak rows more frequently | 

## Interview Questions

### Q1: How does a hardware stride prefetcher work?
**A**: The prefetcher maintains a table indexed by the load instruction's PC. Each entry stores the last address accessed and a detected stride (difference between consecutive accesses). When a load misses, the prefetcher computes the stride from the last two addresses. If the stride is consistent, it prefetches `current_address + stride` (and possibly further ahead). Intel's implementation uses a history of the last 3-4 deltas to confirm the stride before prefetching aggressively.

### Q2: Why is FR-FCFS better than simple FCFS for DRAM scheduling?
**A**: FR-FCFS (First-Ready, First-Come, First-Served) prioritizes row buffer hits over row buffer misses, even if the miss arrived earlier. A row buffer hit only needs a CAS command (~14 ns), while a miss needs ACTIVATE+PRECHARGE+CAS (~47 ns). Serving the hit first frees the bus sooner, and the miss can proceed in parallel on a different bank. This improves row buffer hit rate and overall throughput by 10-30% compared to strict FCFS.

### Q3: What is DRRIP and why does it outperform LRU for last-level caches?
**A**: DRRIP (Dynamic Re-Reference Interval Prediction) inserts new lines with a high "age" counter (bimodal throttling) so that streaming/one-time-access lines are quickly evicted, while lines that get a second access are promoted (RRPV set to 0). LRU treats all new lines equally, so streaming data evicts useful working-set lines. DRRIP's bimodal insertion policy achieves ~5-10% lower miss rates than LRU on workloads with mixed temporal and streaming access patterns.

### Q4: Explain RowHammer and its impact on system design.
**A**: RowHammer exploits DRAM's physical structure: repeatedly activating a row causes charge leakage in adjacent rows, eventually causing bit flips. This breaks the security assumption that DRAM reliably stores data. Mitigations include Target Row Refresh (proactively refreshing adjacent rows), in-DRAM ECC, and activation throttling. The impact extends to system design: memory controllers must track activation counts, adding complexity and some performance overhead.

### Q5: What is row buffer locality and why does it matter?
**A**: DRAM accesses the entire row into a row buffer on ACTIVATE. Subsequent accesses to the same row (row buffer hits) only need a CAS command (~14 ns) versus a full ACTIVATE+PRECHARGE+CAS sequence (~47 ns) for different rows. Row buffer hit rate can vary from 0% (random access) to 100% (sequential column access), creating a 3.4× bandwidth difference. Memory controllers and data layout should maximize row buffer hits for performance-critical workloads.

## Summary

| Topic | Key Idea |
-------|----------|
 Hardware Prefetching | Stream, stride, Markov, and ML-based prefetchers hide memory latency |
 DRRIP Replacement | Bimodal insertion + re-reference prediction outperforms LRU |
 DRAM Scheduling | FR-FCFS prioritizes row buffer hits for 3.4× bandwidth improvement |
 Row-Buffer Locality | Same-row access is 3.4× faster than different-row access |
 RowHammer | Repeated row activation causes adjacent row bit flips; mitigated by TRR |
 DRAM Refresh | 64ms refresh interval; fine-grained refresh reduces availability impact |

## Cross-References

- [Cache Basics](../memory-hierarchy/cache-basics.md) — Foundation for replacement policies
- [Prefetching Basics](../memory-hierarchy/prefetching.md) — Introduction to prefetching concepts
- [Replacement Policies](../memory-hierarchy/replacement.md) — LRU, FIFO, random basics
- [DRAM Technology](../memory-tech/dram.md) — DRAM cell structure and timing
- [DDR](../memory-tech/ddr.md) — DDR generations and bandwidth
- [HBM](../memory-tech/hbm.md) — High-bandwidth memory architecture
- [Modern Interconnects](./modern-interconnects.md) — CXL, memory pooling
