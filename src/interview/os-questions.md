# Operating Systems Interview Questions

> Comprehensive OS questions with detailed answers, follow-ups, and common mistakes.

---

## Q1: What is the difference between a process and a thread?

**Answer:**

| Aspect | Process | Thread |
|--------|---------|--------|
| Definition | An instance of a program in execution | A lightweight unit within a process |
| Memory | Separate address space | Shared address space with other threads |
| Creation | Heavyweight (fork/exec) | Lightweight (clone) |
| Communication | IPC (pipes, sockets, shared memory) | Direct shared memory |
| Context Switch | Expensive (TLB flush, cache invalidation) | Cheap (same address space) |
| Failure | One process crash doesn't affect others | One thread crash can kill entire process |
| Examples | Chrome tabs (each is a process) | Web server handling requests |

```
Process A                    Process B
┌──────────────────┐        ┌──────────────────┐
│  Thread 1        │        │  Thread 1        │
│  Thread 2        │        │  Thread 2        │
│  Thread 3        │        │                  │
│                  │        │                  │
│  [Code]          │        │  [Code]          │
│  [Data]          │        │  [Data]          │
│  [Heap]          │        │  [Heap]          │
│  [Stack T1]      │        │  [Stack T1]      │
│  [Stack T2]      │        │  [Stack T2]      │
│  [Stack T3]      │        │                  │
└──────────────────┘        └──────────────────┘
   Separate Memory            Separate Memory
```

**Follow-up questions:**
- "When would you use processes vs threads?"
- "What is the cost of creating a new process?"
- "How do threads share memory?"

**Common mistakes:**
- Confusing threads with processes
- Saying threads are always faster (not true for CPU-bound tasks on multi-core)
- Not mentioning shared memory as the key difference

---

## Q2: Explain process scheduling algorithms.

**Answer:**

```
┌─────────────────────────────────────────────────────────┐
│              SCHEDULING ALGORITHMS                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. FCFS (First Come First Served)                      │
│     ├── Simple, non-preemptive                          │
│     ├── Problem: Convoy effect (short jobs wait)        │
│     └── Example: [P1:24ms][P2:3ms][P3:3ms]             │
│         Avg wait = (0+24+27)/3 = 17ms                  │
│                                                         │
│  2. SJF (Shortest Job First)                            │
│     ├── Optimal for avg wait time                       │
│     ├── Non-preemptive version                          │
│     ├── Problem: Starvation of long jobs                │
│     └── Example: [P2:3ms][P3:3ms][P1:24ms]             │
│         Avg wait = (0+3+6)/3 = 3ms                     │
│                                                         │
│  3. SRTF (Shortest Remaining Time First)                │
│     ├── Preemptive version of SJF                       │
│     ├── Better for interactive systems                  │
│     └── Problem: Starvation, high context switches      │
│                                                         │
│  4. Round Robin (RR)                                    │
│     ├── Each process gets time quantum                  │
│     ├── Fair, good for interactive systems              │
│     ├── Quantum too small → high overhead               │
│     └── Quantum too large → degenerates to FCFS         │
│                                                         │
│  5. Priority Scheduling                                 │
│     ├── Each process has priority                       │
│     ├── Preemptive or non-preemptive                    │
│     └── Problem: Starvation (solution: aging)           │
│                                                         │
│  6. Multilevel Queue                                    │
│     ├── Multiple queues with different priorities       │
│     ├── Foreground (RR) + Background (FCFS)             │
│     └── Processes permanently assigned to queue         │
│                                                         │
│  7. Multilevel Feedback Queue                           │
│     ├── Processes can move between queues               │
│     ├── CPU-bound → lower priority queue                │
│     ├── I/O-bound → higher priority queue               │
│     └── Most general, used in real OS                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Follow-up questions:**
- "What scheduling algorithm does Linux use?" (CFS - Completely Fair Scheduler)
- "How does aging prevent starvation?"
- "What is the convoy effect?"

---

## Q3: What is a deadlock? How do you prevent it?

**Answer:**

**Deadlock** occurs when two or more processes are waiting for each other to release resources, forming a circular dependency.

**Four Necessary Conditions (Coffman Conditions):**
1. **Mutual Exclusion** — Resource can only be held by one process
2. **Hold and Wait** — Process holds resource while waiting for another
3. **No Preemption** — Resources cannot be forcibly taken
4. **Circular Wait** — Circular chain of processes waiting for each other

```
Deadlock Example:
Process A holds Resource 1, waits for Resource 2
Process B holds Resource 2, waits for Resource 1

  P1 ──holds──→ R1
  ↑              │
  │ waits        │ waits
  │              ↓
  R2 ←──holds── P2
```

**Prevention (break one condition):**
| Condition | Prevention Strategy |
|-----------|-------------------|
| Mutual Exclusion | Use sharable resources (not always possible) |
| Hold and Wait | Request all resources at once |
| No Preemption | Allow OS to forcibly take resources |
| Circular Wait | Order resources, always request in order |

**Avoidance (Banker's Algorithm):**
- Before granting resource, check if system remains in safe state
- Safe state: exists a sequence where all processes can complete
- Expensive: O(m × n²) per request

**Detection and Recovery:**
- Build resource allocation graph, detect cycles
- Recovery: Kill process, rollback, or preempt resource

**Follow-up questions:**
- "What is the difference between deadlock prevention and avoidance?"
- "Can you explain the Banker's algorithm?"
- "How does Linux handle deadlocks?"

**Common mistakes:**
- Confusing deadlock with starvation
- Not mentioning all four conditions
- Saying prevention and avoidance are the same

---

## Q4: Explain virtual memory and paging.

**Answer:**

**Virtual Memory** gives each process the illusion of having its own contiguous address space, larger than physical memory.

```
Virtual Address Space              Physical Memory
┌──────────────────┐              ┌──────────────────┐
│  Kernel Space    │              │  Frame 0         │
│  (inaccessible)  │              │  Frame 1         │
├──────────────────┤              │  Frame 2         │
│  Stack           │ ─────────┐   │  Frame 3         │
│  ↓               │          │   │  Frame 4         │
│                  │          │   │  Frame 5         │
│  ↑               │          │   │  ...             │
│  Heap            │ ──────┐  │   │                  │
├──────────────────┤       │  │   └──────────────────┘
│  BSS (uninit)    │       │  │
├──────────────────┤       │  │   Page Table
│  Data (init)     │       │  │   ┌────────┬───────┐
├──────────────────┤       │  │   │ VPN    │ PFN   │
│  Text (code)     │       │  │   ├────────┼───────┤
└──────────────────┘       │  │   │ 0x0001 │ 0x003 │
                           │  │   │ 0x0002 │ 0x007 │
                           │  └──→│ 0x0003 │ 0x001 │
                           └────→│ 0x0004 │ 0x005 │
                                 └────────┴───────┘
```

**Paging:**
- Virtual address space divided into fixed-size **pages** (typically 4 KB)
- Physical memory divided into **frames** (same size as pages)
- **Page table** maps virtual page numbers to physical frame numbers

**Address Translation:**
```
Virtual Address: [VPN | Offset]
Physical Address: [PFN | Offset]

Example (4 KB pages, 32-bit address):
  VPN = upper 20 bits
  Offset = lower 12 bits (4096 = 2^12)
```

**TLB (Translation Lookaside Buffer):**
- Cache of recent page table entries
- TLB hit → 1 memory access
- TLB miss → walk page table (multiple memory accesses)

**Page Replacement Algorithms:**
| Algorithm | Description | Problem |
|-----------|-------------|---------|
| FIFO | Replace oldest page | Belady's anomaly |
| LRU | Replace least recently used | Expensive to implement |
| Optimal | Replace page used farthest in future | Not implementable |
| Clock | Approximation of LRU | Practical, used in real OS |

**Follow-up questions:**
- "What is thrashing?"
- "How does demand paging work?"
- "What is the difference between page and segment?"

---

## Q5: What is the difference between user mode and kernel mode?

**Answer:**

```
┌─────────────────────────────────────────────────┐
│              MODES OF OPERATION                 │
├─────────────────────────────────────────────────┤
│                                                 │
│  User Mode (Ring 3)                             │
│  ├── Restricted access to hardware              │
│  ├── Cannot execute privileged instructions     │
│  ├── Cannot directly access I/O devices         │
│  ├── Each process has its own address space     │
│  └── System calls required for OS services      │
│                                                 │
│  Kernel Mode (Ring 0)                           │
│  ├── Full access to hardware                    │
│  ├── Can execute all instructions               │
│  ├── Direct I/O access                          │
│  ├── Shared kernel address space                │
│  └── Handles interrupts, system calls           │
│                                                 │
│  Transition: User → Kernel                      │
│  ├── System call (int 0x80 / syscall)           │
│  ├── Hardware interrupt                         │
│  └── Exception (page fault, divide by zero)     │
│                                                 │
└─────────────────────────────────────────────────┘
```

**System Call Flow:**
```
1. User process invokes system call (e.g., read())
2. CPU switches to kernel mode
3. Saves user process state
4. Executes kernel code for the system call
5. Returns result to user process
6. CPU switches back to user mode
```

**Follow-up questions:**
- "Why do we need two modes?"
- "What happens during a context switch?"
- "What is a system call?"

---

## Q6: Explain semaphores and mutexes.

**Answer:**

| Aspect | Mutex | Semaphore |
|--------|-------|-----------|
| Purpose | Mutual exclusion | Signaling/synchronization |
| Values | Binary (locked/unlocked) | Integer (0 to N) |
| Ownership | Yes (only owner can unlock) | No (any thread can signal) |
| Use case | Protect critical section | Limit concurrent access |

```python
# Mutex Example
mutex = Mutex()

def critical_section():
    mutex.lock()
    # Only one thread here at a time
    shared_resource += 1
    mutex.unlock()

# Binary Semaphore (similar to mutex, but no ownership)
sem = Semaphore(1)
sem.wait()  # Decrement (block if 0)
# Critical section
sem.signal()  # Increment

# Counting Semaphore (allow N concurrent access)
sem = Semaphore(5)  # Max 5 threads
# Useful: connection pool, bounded buffer
```

**Classic Problems:**
1. **Producer-Consumer** — Bounded buffer with semaphores
2. **Readers-Writers** — Multiple readers OR one writer
3. **Dining Philosophers** — Avoid deadlock with resource ordering

**Follow-up questions:**
- "What is a spinlock?"
- "When would you use a semaphore vs mutex?"
- "What is priority inversion?"

---

## Q7: What is a context switch?

**Answer:**

A **context switch** is the process of saving the state of a currently running process/thread and restoring the state of the next one to run.

```
Steps in Context Switch:
1. Save CPU registers of current process to PCB
2. Save program counter (PC)
3. Save stack pointer
4. Update process state (Running → Ready/Waiting)
5. Load PCB of next process
6. Restore registers, PC, stack pointer
7. Update process state (Ready → Running)
8. Resume execution

Costs:
├── Direct: CPU time to save/restore (~1-10 μs)
├── Indirect: Cache invalidation, TLB flush
├── Indirect: Pipeline flush, branch predictor reset
└── Total: Can be 10-100x more than direct cost
```

**Follow-up questions:**
- "When does a context switch occur?"
- "How to reduce context switches?"
- "What is the difference between context switch and mode switch?"

---

## Q8: Explain memory allocation strategies.

**Answer:**

```
┌─────────────────────────────────────────────────────────┐
│              MEMORY ALLOCATION STRATEGIES                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Contiguous Allocation                               │
│     ├── Fixed Partition: Equal-size regions              │
│     │   └── Problem: Internal fragmentation              │
│     ├── Variable Partition: Fit to process size          │
│     │   ├── First Fit: First hole that's big enough      │
│     │   ├── Best Fit: Smallest hole that's big enough    │
│     │   └── Worst Fit: Largest hole                      │
│     └── Problem: External fragmentation                  │
│                                                         │
│  2. Paging (most modern OS)                             │
│     ├── Fixed-size pages, no external fragmentation      │
│     ├── Small internal fragmentation (last page)         │
│     └── Page table overhead                              │
│                                                         │
│  3. Segmentation                                        │
│     ├── Variable-size segments (code, data, stack)       │
│     ├── Logical division matches programmer's view       │
│     └── Problem: External fragmentation                  │
│                                                         │
│  4. Buddy System                                        │
│     ├── Power-of-2 block sizes                          │
│     ├── Split blocks on allocation                      │
│     ├── Merge buddies on free                           │
│     └── Used in Linux kernel                            │
│                                                         │
│  5. Slab Allocation                                     │
│     ├── Pre-allocated caches for common objects          │
│     ├── No fragmentation for same-size objects           │
│     └── Used in Linux kernel for kernel objects          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Q9: What is thrashing?

**Answer:**

**Thrashing** occurs when a system spends more time swapping pages in and out of memory than executing actual processes.

```
Cause: Process's working set > available frames

Symptoms:
├── High CPU utilization drops (paradoxically)
├── High disk I/O (constant page faults)
├── System becomes unresponsive
└── Throughput collapses

Working Set Model:
├── Working set: Set of pages actively used in last Δ time units
├── If total working sets > physical frames → thrashing
└── Solution: Reduce degree of multiprogramming

Prevention:
├── Working set model (track per-process page usage)
├── Page fault frequency (adjust frames based on fault rate)
├── Swap out processes when memory pressure high
└── Limit number of concurrent processes
```

---

## Q10: Explain inter-process communication (IPC) mechanisms.

**Answer:**

| Mechanism | Description | Speed | Use Case |
|-----------|-------------|-------|----------|
| **Pipes** | Unidirectional byte stream | Fast | Parent-child communication |
| **Named Pipes (FIFO)** | Bidirectional, filesystem entry | Fast | Unrelated processes |
| **Message Queues** | Structured messages | Medium | Async communication |
| **Shared Memory** | Same physical page mapped to multiple processes | Fastest | High-performance data sharing |
| **Semaphores** | Synchronization primitive | Fast | Mutual exclusion |
| **Sockets** | Network-capable IPC | Medium | Network communication, different machines |
| **Signals** | Asynchronous notifications | Fast | Event notification (SIGTERM, SIGKILL) |

```
Shared Memory Example:
Process A                    Process B
┌──────────┐                ┌──────────┐
│ Virtual  │                │ Virtual  │
│ Memory   │                │ Memory   │
│          │                │          │
│ Shared   │────────┐ ┌────│ Shared   │
│ Region   │        │ │    │ Region   │
└──────────┘        │ │    └──────────┘
                    │ │
              ┌─────▼─▼─────┐
              │   Physical   │
              │   Memory     │
              │   (Shared)   │
              └──────────────┘
```

---

## Q11: What is the difference between preemptive and non-preemptive scheduling?

**Answer:**

| Aspect | Preemptive | Non-Preemptive |
|--------|-----------|----------------|
| Definition | OS can interrupt running process | Process runs until completion or block |
| Context Switch | Can happen anytime | Only when process yields/blocks |
| Response Time | Better for interactive | Better for batch |
| Complexity | More complex | Simpler |
| Examples | Round Robin, SRTF | FCFS, SJF |
| Starvation | Possible | Possible |

---

## Q12: Explain the producer-consumer problem.

**Answer:**

```python
# Solution using semaphores
import threading

BUFFER_SIZE = 10
buffer = []
mutex = threading.Semaphore(1)      # Mutual exclusion
empty = threading.Semaphore(BUFFER_SIZE)  # Empty slots
full = threading.Semaphore(0)       # Filled slots

def producer():
    while True:
        item = produce_item()
        empty.acquire()    # Wait for empty slot
        mutex.acquire()    # Enter critical section
        buffer.append(item)
        mutex.release()    # Exit critical section
        full.release()     # Signal item available

def consumer():
    while True:
        full.acquire()     # Wait for item
        mutex.acquire()    # Enter critical section
        item = buffer.pop()
        mutex.release()    # Exit critical section
        empty.release()    # Signal empty slot
        consume_item(item)
```

**Follow-up questions:**
- "What if the buffer is unbounded?"
- "How does this relate to real systems?"
- "What is a race condition?"

---

## Q13: What is a file system? Explain inode.

**Answer:**

**File System** manages how data is stored and retrieved on storage devices.

**Inode (Index Node):**
```
Inode Structure:
┌────────────────────────────────┐
│ Inode #1234                    │
├────────────────────────────────┤
│ File type: Regular file        │
│ Permissions: rwxr-xr-x         │
│ Owner: user_id = 1000          │
│ Size: 1,048,576 bytes          │
│ Timestamps: create, modify, access │
│ Direct pointers: [0-11]        │
│ Single indirect pointer: [12]  │
│ Double indirect pointer: [13]  │
│ Triple indirect pointer: [14]  │
│ Reference count: 2             │
└────────────────────────────────┘

Direct pointers: Point directly to data blocks
Indirect pointers: Point to blocks of pointers

File access:
  Path "/home/user/file.txt"
  → Directory entry → Inode number → Inode → Data blocks
```

**Follow-up questions:**
- "What is the difference between hard link and soft link?"
- "What happens when you delete a file?"
- "How does journaling work?"

---

## Q14-30: Quick-Fire Questions

**Q14: What is a race condition?**
When multiple threads access shared data concurrently and the result depends on execution order. Solution: Use synchronization (mutex, semaphore).

**Q15: What is starvation?**
When a process is perpetually denied resources because higher-priority processes keep getting them. Solution: Aging.

**Q16: What is the difference between logical and physical addresses?**
Logical: Generated by CPU (virtual). Physical: Actual location in RAM. MMU translates logical → physical.

**Q17: What is demand paging?**
Pages loaded into memory only when accessed (on-demand). Reduces startup time and memory usage.

**Q18: What is a page fault?**
When a process accesses a page not in physical memory. OS loads page from disk → very expensive (~10ms).

**Q19: What is Belady's anomaly?**
FIFO page replacement may increase page faults when more frames are added. Doesn't occur with LRU or optimal.

**Q20: What is the difference between fork() and exec()?**
fork(): Creates child process (copy of parent). exec(): Replaces current process image with new program. Typically: fork() then exec().

**Q21: What is a zombie process?**
A terminated process whose exit status hasn't been collected by parent (wait()). Occupies process table entry. Solution: Parent calls wait().

**Q22: What is an orphan process?**
A process whose parent has terminated. Adopted by init (PID 1). Not harmful, automatically reaped.

**Q23: What is a real-time operating system?**
OS with strict timing guarantees. Hard real-time: Missing deadline = failure. Soft real-time: Missing deadline = degraded performance.

**Q24: What is the difference between symmetric and asymmetric multiprocessing?**
Symmetric (SMP): All processors equal, share memory. Asymmetric: One master, others slaves. SMP is standard today.

**Q25: What is a system call?**
Interface between user process and kernel. Examples: open(), read(), write(), fork(), exec().

**Q26: What is DMA (Direct Memory Access)?**
Allows I/O devices to transfer data directly to/from memory without CPU involvement. Reduces CPU overhead.

**Q27: What is the difference between multiprogramming and multitasking?**
Multiprogramming: Multiple programs in memory, CPU switches when one blocks. Multitasking: CPU switches between programs using time slices.

**Q28: What is a critical section?**
Code that accesses shared resources and must not be executed by more than one process/thread at a time.

**Q29: What is priority inversion?**
When a high-priority task waits for a low-priority task that holds a resource, but a medium-priority task preempts the low-priority one. Solution: Priority inheritance.

**Q30: What is copy-on-write (COW)?**
fork() initially shares parent's memory pages. Pages copied only when either process modifies them. Saves memory and time.

## 🔗 Cross-References

- [OS Cheatsheet](../cheatsheets/os.md) — Quick reference for all OS concepts
- [OS Revision](../revision/os.md) — Quick summary before interviews
- [DBMS Questions](./dbms-questions.md) — Database concurrency (similar to OS concurrency)
- [System Design](./system-design/README.md) — OS concepts in distributed systems
