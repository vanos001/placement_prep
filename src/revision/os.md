# Operating Systems - Quick Revision

> 📌 Last-minute revision before interviews. Scan these points quickly.

---

## Process & Thread

- **Process**: Instance of program, separate memory space, heavyweight
- **Thread**: Lightweight unit within process, shared memory, cheap context switch
- **Context switch**: Save/restore PCB, expensive (TLB flush, cache invalidation)
- **fork()**: Creates child process (copy-on-write), **exec()**: Replaces process image
- **Zombie**: Terminated, not waited on. **Orphan**: Parent terminated, adopted by init

## Scheduling

- **FCFS**: Simple, convoy effect
- **SJF**: Optimal avg wait, starvation possible
- **Round Robin**: Fair, time quantum matters (too small = overhead, too large = FCFS)
- **Priority**: Starvation solution = aging
- **MLFQ**: Processes move between queues, most general

## Synchronization

- **Mutex**: Binary lock, owner must unlock
- **Semaphore**: Counter (binary or counting), any thread can signal
- **Spinlock**: Busy-wait lock, good for short critical sections
- **Critical Section**: Code accessing shared resource, needs mutual exclusion

## Deadlock

- **Four conditions**: Mutual exclusion, Hold & wait, No preemption, Circular wait
- **Prevention**: Break one condition
- **Avoidance**: Banker's algorithm (safe state check)
- **Detection**: Resource allocation graph, cycle = deadlock

## Memory Management

- **Paging**: Fixed-size pages (4KB), no external fragmentation, page table maps VPN→PFN
- **Segmentation**: Variable-size, matches programmer's view, external fragmentation
- **TLB**: Cache of page table entries, TLB miss = walk page table
- **Page replacement**: FIFO (Belady's anomaly), LRU (expensive), Clock (practical)
- **Thrashing**: Working set > frames, solution: reduce multiprogramming

## Virtual Memory

- **Demand paging**: Load pages on demand, page fault if not in memory
- **Page fault**: Expensive (~10ms), load from disk
- **Working set**: Pages actively used in time window Δ

## File System

- **Inode**: Metadata (permissions, size, pointers to data blocks)
- **Hard link**: Same inode, different name. **Soft link**: Different inode, stores path
- **Journaling**: WAL for crash recovery

## IPC

- **Pipes**: Unidirectional, parent-child
- **Shared memory**: Fastest, needs synchronization
- **Message queues**: Structured messages
- **Sockets**: Network-capable
- **Signals**: Async notifications (SIGTERM, SIGKILL)

## Key Concepts

- **User mode vs Kernel mode**: Restricted vs full access, system calls transition
- **DMA**: Direct Memory Access, bypasses CPU for I/O
- **Race condition**: Non-deterministic from concurrent access
- **Priority inversion**: High-priority waits on low-priority, solution: priority inheritance
- **Copy-on-write**: fork() shares pages, copies on modification
- **Real-time OS**: Hard (deadline = failure) vs Soft (degraded performance)

## 🔗 Cross-References

- [OS Cheatsheet](../cheatsheets/os.md) — Detailed reference
- [OS Interview Questions](../interview/os-questions.md) — Full Q&A
