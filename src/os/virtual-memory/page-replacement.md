# Page Replacement Algorithms

## Overview

When a page fault occurs and physical memory is full, the OS must choose which page to evict. Page replacement algorithms determine this selection, significantly impacting system performance.

## Why It Matters

- **Performance**: Wrong choices cause thrashing (excessive page faults)
- **Every OS uses one**: Linux uses a variant of LRU (clock), Windows uses working set-based
- **Interview favorite**: Common question in OS interviews
- **Applies beyond OS**: Cache replacement (CPU, CDN, browser) uses same algorithms

## Algorithms Comparison

| Algorithm | Principle | Optimal? | Implementable? | Key Issue |
|-----------|-----------|----------|----------------|-----------|
| FIFO | Evict oldest page | No | Yes | Belady's anomaly |
| LRU | Evict least recently used | No (close) | Expensive | High overhead |
| Optimal (MIN) | Evict page used farthest in future | Yes | No (needs future) | Theoretical best |
| Clock (Second Chance) | FIFO + reference bit | No | Yes | Good approximation |
| LFU | Evict least frequently used | No | Yes | Stale pages |
| MFU | Evict most frequently used | No | Yes | Counter-intuitive |

## FIFO (First-In, First-Out)

**Concept**: Evict the page that has been in memory the longest.

```
Reference String: 7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1
Frames: 3

Page Faults: 15 (with 3 frames)
```

### Belady's Anomaly
Increasing the number of frames can **increase** page faults with FIFO:
- 3 frames: 9 faults
- 4 frames: 10 faults (!!)

This anomaly doesn't occur with stack-based algorithms (LRU, Optimal).

## LRU (Least Recently Used)

**Concept**: Evict the page that hasn't been used for the longest time.

### Implementation Methods

#### 1. Counter-based
```
Each page has a timestamp of last access
On page fault: evict page with smallest timestamp
Problem: Need to update timestamp on every memory access
```

#### 2. Stack-based (Doubly Linked List)
```
On access: move page to top of stack
On page fault: evict page at bottom of stack
Operations: O(1) with hash table + linked list
```

#### 3. Matrix-based
```
n×n matrix for n pages
On reference to page i: set row i to 1, column i to 0
Page with smallest binary value is LRU
```

### LRU Approximation: Clock Algorithm
Most OS use clock (second-chance) as a practical LRU approximation.

## Optimal (MIN) Algorithm

**Concept**: Evict the page that won't be used for the longest time in the future.

```
Reference: 7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2, 1, 2, 0, 1, 7, 0, 1
Frames: 3

Page Faults: 9 (minimum possible)
```

- Provably optimal (lowest page fault rate)
- **Not implementable** (requires future knowledge)
- Used as benchmark to evaluate other algorithms

## Clock Algorithm (Second Chance)

**Concept**: FIFO with a second chance — if reference bit is set, give it another chance.

```
Circular buffer with clock hand

On page fault:
1. Check page at clock hand
2. If reference bit = 0 → evict this page
3. If reference bit = 1 → clear bit, advance hand, repeat
```

### Enhanced Clock Algorithm
Uses two bits: reference bit + modify (dirty) bit

| Reference | Modify | Priority | Action |
|-----------|--------|----------|--------|
| 0 | 0 | Highest | Evict (clean, unused) |
| 0 | 1 | High | Evict (dirty, but unused) |
| 1 | 0 | Low | Clear reference bit |
| 1 | 1 | Lowest | Clear reference bit |

## LFU (Least Frequently Used)

**Concept**: Evict the page with the lowest access count.

### Problems
- **Stale pages**: A page used heavily in the past but not recently keeps high count
- **Frequency explosion**: Counts grow unbounded

### Solutions
- **Aging**: Periodically halve all counters
- **Combined LRU-LFU**: Use frequency + recency

## Performance Comparison

### With 3 Frames (Reference: 1,2,3,4,1,2,5,1,2,3,4,5)

| Algorithm | Page Faults | Notes |
|-----------|-------------|-------|
| FIFO | 9 | Simple but suboptimal |
| LRU | 10 | Close to optimal |
| Optimal | 7 | Theoretical minimum |
| Clock | 8-9 | Practical LRU approximation |

### With More Frames
- All stack-based algorithms (LRU, Optimal) never show Belady's anomaly
- FIFO may show Belady's anomaly

## Linux Page Replacement

Linux uses a **multi-generational LRU** (MGLRU):
- Pages organized in generations (young to old)
- On access: promote to youngest generation
- On memory pressure: evict from oldest generation
- Uses hardware accessed bits + periodic scanning
- Much better than the old active/inactive list approach

## Interview Questions

### Q1: Why is Optimal not implementable?
**Answer:** It requires knowing future page references, which is impossible. It's used as a theoretical benchmark — any real algorithm will have ≥ Optimal's page fault count.

### Q2: Explain Belady's anomaly.
**Answer:** With FIFO, increasing the number of page frames can increase page faults. Example: reference string 1,2,3,4,1,2,5,1,2,3,4,5 with 3 frames → 9 faults, with 4 frames → 10 faults. This happens because FIFO doesn't respect the "stack property" — the set of pages in n frames isn't a subset of pages in n+1 frames.

### Q3: How does the Clock algorithm approximate LRU?
**Answer:** Clock uses a reference bit set by hardware on each access. When evicting, it scans circularly: pages with reference bit=1 get a second chance (bit cleared), pages with bit=0 are evicted. This approximates LRU because recently accessed pages are more likely to have their reference bit set.

### Q4: What's the difference between global and local replacement?
**Answer:** **Global**: any page from any process can be evicted (better overall throughput, but one process can steal frames from another). **Local**: only pages from the faulting process can be evicted (more predictable per-process performance). Most OS use global with some protections.

### Q5: How would you implement LRU in O(1)?
**Answer:** Combine a hash map (page → node) with a doubly linked list. On access: move node to head (O(1) with hash + pointer update). On fault: evict tail node (O(1)). Total: O(1) per access.

## Common Mistakes

1. Confusing FIFO with LRU — FIFO ignores recency of use
2. Thinking Optimal is implementable
3. Not considering Belady's anomaly in interview questions
4. Forgetting that clock algorithm clears reference bits (it's not pure LRU)
5. Assuming LFU and LRU are the same — frequency ≠ recency

## Summary

| Use Case | Best Algorithm |
|----------|---------------|
| Theoretical minimum faults | Optimal (MIN) |
| Practical, good performance | Clock / LRU approximations |
| Simple to implement | FIFO (but has anomalies) |
| Modern OS | Multi-generational LRU (Linux) |
| CPU cache | Pseudo-LRU or true LRU (small caches) |

## Cross References

- [Virtual Memory](./README.md)
- [Demand Paging](./demand-paging.md)
- [Thrashing](./thrashing.md)
- [Working Set](./working-set.md)
- [Cache Replacement](../../arch/memory-hierarchy/replacement.md)
