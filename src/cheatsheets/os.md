# Operating Systems Cheatsheet

## 🧠 Process vs Thread

| | Process | Thread |
|---|---------|--------|
| Memory | Separate address space | Shared address space |
| Creation | Heavy (fork) | Light (clone) |
| IPC | Pipes, sockets, shared memory | Direct shared memory |
| Context Switch | Expensive (TLB flush) | Cheap |
| Crash | Isolated | Can kill entire process |

## 📋 Scheduling Algorithms

| Algorithm | Preemptive | Starvation | Convoy | Best For |
|-----------|-----------|------------|--------|----------|
| FCFS | No | No | Yes | Batch |
| SJF | No | Yes | No | Min avg wait |
| SRTF | Yes | Yes | No | Interactive |
| Round Robin | Yes | No | No | Time-sharing |
| Priority | Both | Yes | No | Real-time |
| MLFQ | Yes | No | No | General OS |

## 🔒 Synchronization

```
Mutex: Binary lock, owner must unlock
Semaphore: Counter, any thread can signal
  - Binary: like mutex (0 or 1)
  - Counting: 0 to N (resource pool)

Critical Section Requirements:
  1. Mutual Exclusion
  2. Progress
  3. Bounded Waiting
```

## 💀 Deadlock

```
Four Conditions (ALL must hold):
  1. Mutual Exclusion
  2. Hold and Wait
  3. No Preemption
  4. Circular Wait

Prevention: Break one condition
Avoidance: Banker's Algorithm (safe state)
Detection: Resource Allocation Graph (cycle)
Recovery: Kill process / rollback / preempt
```

## 📦 Memory Management

```
Paging:
  - Fixed-size pages (4KB typical)
  - No external fragmentation
  - Page table maps VPN → PFN
  - TLB caches translations

Segmentation:
  - Variable-size segments
  - Matches programmer's view
  - External fragmentation possible

Page Replacement:
  FIFO: Simple, Belady's anomaly
  LRU: Optimal approximation, expensive
  Clock: Practical LRU approximation
  Optimal: Theoretical best, not implementable
```

## 🔗 Virtual Memory

```
Address Translation:
  Virtual [VPN | Offset] → Physical [PFN | Offset]

Page Fault:
  1. Process accesses page not in memory
  2. OS finds page on disk
  3. Load page into free frame
  4. Update page table
  5. Restart instruction

Thrashing: Working set > available frames
Solution: Reduce multiprogramming / add memory
```

## 📁 File Systems

```
Inode: Metadata structure for files
  - Direct pointers (12): → data blocks
  - Single indirect: → block of pointers
  - Double indirect: → block → block of pointers
  - Triple indirect: → block → block → block of pointers

Hard Link: Same inode, different name
Soft Link: Different inode, stores path

Journaling: WAL for crash recovery
  - Write intent to journal
  - Write data
  - Mark journal complete
```

## 🔄 IPC Mechanisms

| Mechanism | Speed | Use Case |
|-----------|-------|----------|
| Pipes | Fast | Parent-child |
| Named Pipes | Fast | Unrelated processes |
| Message Queue | Medium | Structured messages |
| Shared Memory | Fastest | High-performance data |
| Sockets | Medium | Network-capable |
| Signals | Fast | Async notification |

## ⚡ Quick Facts

- **Context switch**: Save PCB, load next PCB (~1-10 μs direct cost)
- **System call**: User mode → Kernel mode transition
- **Copy-on-write**: fork() shares pages, copies on modification
- **Zombie process**: Terminated but not waited on by parent
- **Orphan process**: Parent terminated, adopted by init (PID 1)
- **DMA**: Direct Memory Access, bypasses CPU for I/O
- **Race condition**: Non-deterministic result from concurrent access
- **Priority inversion**: High-priority waits on low-priority resource

## 🔗 Cross-References

- [OS Interview Questions](../interview/os-questions.md) — Detailed answers
- [OS Revision](../revision/os.md) — Quick summary
- [DBMS Cheatsheet](./dbms.md) — Concurrency concepts
