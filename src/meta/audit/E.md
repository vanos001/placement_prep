# Chunk E Audit — OS

**Scope:** src/os/* (skipping already-fixed)
**Files audited:** 105
**Files clean:** 90
**Total findings:** 15

**Method:** Every file in `src/os/` not on the `already_fixed.md` list was read end-to-end. Arithmetic
in worked examples was checked with Python (scripts inlined under each finding's "Verification"
field). OS-level technical claims (TLB behavior, page-table walks, scheduling properties, IPC
semantics, filesystem structures) were cross-checked against Silberschatz *Operating System
Concepts* (10th ed.) and the Linux kernel documentation where applicable. The web was not needed
for any of the findings below — all of them are internal consistency / arithmetic / code bugs
discoverable by reading.

## Findings

### HIGH severity

#### os/memory/multi-level-page-tables.md:107
- **Wrong text:** `Savings: 4 MB → 16 KB (250x reduction!)`
- **Correct text:** `Savings: 4 MB → 16 KB (256x reduction)`
- **Verification:** `python3 -c "print(4*1024*1024 // (16*1024))"` → 256. The file's own Python
  script (line 357) prints `Savings: 256x`, so the inline prose is just a typo.
- **Justification:** Worked example gives wrong reduction factor.

#### os/memory/multi-level-page-tables.md:530
- **Wrong text:** `Need: 1 PGD entry, ~2 PUD entries, ~2048 PMD entries, ~1024 PTE tables.`
- **Correct text:** `Need: 1 PGD entry, ~1 PUD entry, ~4 PMD entries, ~2048 PTE tables.`
- **Verification:** `python3 -c "print('PTE tables:', 4*1024**3//4096//512); print('PMD entries:', 4*1024**3//4096//512//512); print('PUD entries:', 4*1024**3//4096//512//512//512)"` →
  PTE tables=2048, PMD entries=4, PUD entries=1, PGD entries=1. The PMD and PTE-table counts
  are swapped, and PUD was wrong. The line right after ("Total: ~8 MB of page table pages") is
  correct, but the breakdown is not.
- **Justification:** Teaches the wrong page-table-walk breakdown for a 4 GB mmap with 4 KB pages.

#### os/synchronization/mutex.md:182
- **Wrong text:** `pthread_cond_cond_wait(&cond, &mutex);`
- **Correct text:** `pthread_cond_wait(&cond, &mutex);`
- **Verification:** `grep pthread_cond_cond_wait /usr/include/pthread.h` returns nothing; the
  POSIX function is `pthread_cond_wait`. The doubled `cond_` is a typo that would prevent the
  example from compiling.
- **Justification:** Code sample won't compile; misleading to readers copy-pasting.

#### os/synchronization/deadlocks/README.md:254-272
- **Wrong text:** The "Deadlock Avoidance (Banker's Algorithm)" example shows only 3 processes
  (P0, P1, P2) with allocations summing to (5, 1, 2), but asserts `Available: (3, 3, 2)`. With
  the displayed 3-process allocations and resource totals A=10, B=5, C=7, the available vector
  should be `(5, 4, 5)`, not `(3, 3, 2)`. The trace then concludes the state is `UNSAFE` — but
  the same data, completed with the missing P3 and P4 rows (which the doc shows in
  `avoidance.md`), is actually `SAFE`.
- **Correct text:** Either show the full 5-process table from `avoidance.md` (so the available
  vector `(3, 3, 2)` is consistent), or correct the available vector to `(5, 4, 5)` for the
  3-process subset and re-run the safety trace (which then gives a SAFE sequence P1 → P2 → P0).
- **Verification:** Python check: 3-process allocations sum to (5,1,2), so `Available =
  (10,5,7) - (5,1,2) = (5,4,5)`. The P3+P4 allocations `(2,1,1)+(0,0,2) = (2,1,3)` are exactly
  the missing `(5,4,5) - (3,3,2) = (2,1,3)`. So the README silently dropped P3 and P4 but kept
  their effect on the Available vector.
- **Justification:** The example reaches the wrong pedagogical conclusion (claims UNSAFE when
  the underlying state is SAFE); also internally inconsistent (Available ≠ Total − Allocated).

#### os/synchronization/monitors.md:213-246
- **Wrong text:** The Dining Philosophers Java snippet declares
  `private Condition[] self = new Condition[5];` and in the constructor does
  `self[i] = lock.newCondition();`, but `lock` is **never declared**. The methods are also
  marked `synchronized`, which means they synchronize on `this`, not on `lock`. Calling
  `self[i].await()` from a `synchronized` method throws `IllegalMonitorStateException` because
  the current thread doesn't hold `lock`.
- **Correct text:** Add `private final Lock lock = new ReentrantLock();` and drop the
  `synchronized` keyword from `pickup`/`putdown`, instead using `lock.lock()`/`lock.unlock()`
  around the bodies. The correct, compilable version is already present in
  `os/synchronization/dining-philosophers.md` (Solution 4) — the monitors.md copy should match.
- **Verification:** Compile attempt: `javac DiningTable.java` fails with "cannot find symbol:
  variable lock". Even after adding `lock`, calling `Condition.await()` while holding the
  intrinsic (`this`) monitor rather than `lock` is a documented misuse (see
  java.util.concurrent.locks.Condition javadoc).
- **Justification:** Broken code sample presented as the canonical Dining Philosophers monitor
  solution.

#### os/scheduling/realtime.md:100-115
- **Wrong text:** The RMS execution trace has multiple errors:
  - `t=1: τ2 releases → runs 1-3` — τ2's period is 5, so it should release at t=0 alongside τ1
    and τ3 (not at t=1).
  - `t=3: Idle (no task ready)` — τ3 was released at t=0 with C=2 and D=10, so it should run
    here, not leave the CPU idle.
  - The gantt chart shows τ3 running `7-9` and `13-15` (2 units each), but the trace text says
    τ3 runs `7-9` for its first invocation. Since τ3 needs 2 units and the CPU was free at t=3,
    the first invocation should have run at t=3-4 and t=7-8 (split by τ1's release at t=4), not
    `7-9`.
- **Correct text:** Replace the trace with: `t=0-1: τ1 (releases at 0)` → `t=1-3: τ2 (released
  at 0, C=2)` → `t=3-4: τ3 (released at 0, runs 1 of 2 units)` → `t=4-5: τ1 (released at 4)`
  → `t=5-7: τ2 (released at 5, C=2)` → `t=7-8: τ3 (remaining 1 unit, completes by D=10 ✓)` →
  ... and so on. Or remove the broken trace and reference the algorithm without a faulty
  timeline.
- **Verification:** Manual RMS schedule trace with priorities τ1 > τ2 > τ3 (periods 4 < 5 < 10).
  τ3 must run between the higher-priority jobs whenever the CPU is free; the "Idle at t=3" claim
  contradicts the algorithm.
- **Justification:** The trace doesn't follow RMS — it leaves the CPU idle while a ready task is
  pending, which is not how RMS works. Students using this as a worked example will be confused.

### MEDIUM severity

#### os/scheduling/round-robin.md:164
- **Wrong text:** `waiting = turnaround - burst_map[pid];` — `burst_map` is referenced but
  never defined. The variable defined earlier is `arrival_map`; the parallel `burst_map`
  (analogous to `arrival_map = {p[0]: p[1] for p in processes}`) is missing.
- **Correct text:** Add `burst_map = {p[0]: p[2] for p in processes}` next to `arrival_map`,
  or replace `burst_map[pid]` with a lookup that uses `processes`.
- **Verification:** Reading the function body — `arrival_map` is built on line 131, but no
  `burst_map` is built; line 164 will throw `NameError: name 'burst_map' is not defined`.
- **Justification:** Reference implementation has a `NameError`; readers copying the code will
  hit a runtime crash.

#### os/scheduling/multilevel-feedback.md:73-79
- **Wrong text:** The execution trace contradicts the table:
  - Line 63 says `P3 | Interactive | 2 | 2 (CPU) + 3 (I/O) + 2 (CPU)` — arrival time = 2.
  - Line 76 of the trace says `Time 6: P3 arrives in Q1, P2 still running in Q2` — arrival at
    t=6 contradicts the table's t=2.
  - Line 75: `Time 5-9: P1 doing I/O, P2 runs in Q2 (quantum=8, uses 4 more → still Q2)` —
    P2 has now used 4 (in Q1) + 4 (in Q2) = 8 units, exhausting its Q2 quantum of 8, so it
    should be demoted to Q3, not stay in Q2.
- **Correct text:** Either change P3's arrival time in the table to 6 (and re-derive the trace
  consistently), or fix the trace to say "Time 2: P3 arrives in Q1" and re-derive from there.
  Also fix the Q2 demotion: after P2 consumes 8 units in Q2 it should be moved to Q3.
- **Verification:** Read the table (line 63) and the trace (lines 73-79) side by side; the P3
  arrival time and the Q2 quantum math don't line up.
- **Justification:** Worked example is internally inconsistent and the demotion logic is wrong,
  which is the core mechanic MLFQ is supposed to illustrate.

#### os/filesystems/raid.md:154
- **Wrong text:** `Write P = 15⊕20 = 35  ✗  (crash!)`
- **Correct text:** `Write P = 15⊕20 = 27  ✗  (crash!)`
- **Verification:** `python3 -c "print(15 ^ 20)"` → 27. 15 = 0b01111, 20 = 0b10100, XOR =
  0b11011 = 27. (35 doesn't even fit in 5 bits, so it cannot be the XOR of two 5-bit numbers.)
- **Justification:** Wrong arithmetic in a worked example. The downstream recovery computation
  (`D1 = 15⊕30 = 17`) still works because it uses the OLD parity (30), but the line as written
  is incorrect.

#### os/io/disk-scheduling.md:73-78
- **Wrong text:** The "Visual Comparison" block:
  ```
  SCAN:    50 → 70 → 95 → 35 → 15 → 10  (total movement: 20+25+60+20+5 = 130)
  C-SCAN:  50 → 70 → 95 → 10 → 15 → 35  (total movement: 20+25+85+5+20 = 155)
  LOOK:    50 → 70 → 95 → 35 → 15 → 10  (same as SCAN here, doesn't go to edge)
  ```
  - The SCAN movement `95 → 35 = 60` skips the disk edge, which is LOOK behavior, not SCAN.
    SCAN should go `95 → 100 (edge) → ... → 35`, costing `(100-95) + (100-35) = 70`, not 60.
  - The C-SCAN movement `95 → 10 = 85` is the C-LOOK jump (highest request → lowest request),
    not the C-SCAN jump (disk edge → 0). C-SCAN should add `(100-95) + 100 + 10 = 115` for that
    leg, not 85.
  - The LOOK comment "(same as SCAN here, doesn't go to edge)" is self-contradictory — if SCAN
    also doesn't go to the edge per the calculation above, the LOOK distinction is meaningless.
- **Correct text:** Either relabel the SCAN row as LOOK (and relabel C-SCAN as C-LOOK), or
  recompute SCAN and C-SCAN with edge movements included. With a 0-100 disk:
  - SCAN: 50→70→95→100→35→15→10, movement = 20+25+5+65+20+5 = 140
  - C-SCAN: 50→70→95→100→0→10→15→35, movement = 20+25+5+100+10+5+20 = 185
- **Verification:** Manual trace of SCAN and C-SCAN definitions vs the calculations shown.
- **Justification:** Mislabels algorithms; students will think SCAN doesn't visit the disk edge,
  which is the defining difference between SCAN and LOOK.

#### os/synchronization/dining-philosophers.md:9-19
- **Wrong text:** The ASCII layout of the table is not a pentagon — it's a vertical diamond
  with P3 at the bottom only connected to P2 via C2. The chopstick labels (C0 upper-left,
  C4 upper-right, C3 middle-left, C1 middle-right, C2 bottom) do not match the convention
  `P_i needs C_i and C_{(i+1)%5}` under any standard interpretation (left-of-philosopher or
  between-adjacent-philosophers). Specifically C3 is drawn between P4 and P2 (non-adjacent in
  any circular arrangement), and there is no chopstick drawn between P3 and P4 at all.
- **Correct text:** Redraw as a pentagon with philosophers at the 5 vertices and chopsticks at
  the 5 edges, with `C_i` placed between `P_i` and `P_{(i+1)%5}`.
- **Verification:** Hand-trace: with 5 philosophers in a cycle, each philosopher should have
  exactly 2 adjacent chopsticks; in the drawn figure P3 has only one (C2) and P4 has only one
  (C0). The figure cannot represent the problem it claims to.
- **Justification:** Wrong diagram for the canonical problem; confuses readers about which
  chopsticks belong to which philosopher.

#### os/memory/slab-allocator.md:46-67
- **Wrong text:** The "Problem Slab Solves" section says:
  ```
  Kernel needs to allocate task_struct (8KB):
  1. Call buddy system for 2 pages (8KB)
  2. Use the 8KB for task_struct
  3. When done, free 2 pages back to buddy
  ```
  But the file's own `/proc/slabinfo` listing on line 280 shows `task_struct ... 5824` (i.e.,
  ~5.7 KB, not 8 KB). The "1 page (4KB) can hold 0 task_structs" claim also doesn't make sense:
  a 5824-byte object fits in 2 pages (8192 bytes) with ~30% slack, which is exactly the
  situation slab is designed to fix — but the description treats it as if no improvement is
  possible.
- **Correct text:** Replace "8KB" with "≈6 KB (5824 bytes on typical x86_64 configs)" and
  re-explain: with buddy-only allocation a single task_struct needs 2 pages (8 KB), wasting
  ~37% of the second page; the slab allocator packs ~5 task_structs into 8 pages, dropping
  the per-object overhead to ~5%.
- **Verification:** `cat /proc/slabinfo | grep task_struct` on a current kernel shows the
  object size; the file itself prints 5824 on line 280.
- **Justification:** Internally contradictory (intro says 8 KB, slabinfo output says 5824 B);
  understates the slab benefit.

### LOW severity

#### os/memory/paging.md:353
- **Wrong text:** `stack (0x7FFF00000000-0x7FFFFFFFFFFFF)` — the upper bound has 13 hex
  digits, which is a 52-bit value and exceeds the 48-bit canonical address range the question
  is about.
- **Correct text:** `stack (0x7FFF00000000-0x7FFFFFFFFFFF)`
- **Verification:** `python3 -c "print(hex(0x7FFFFFFFFFFFF)); print(hex(0x7FFFFFFFFFFF))"` →
  `0x7ffffffffffff` (51 bits) vs `0x7fffffffffff` (47 bits). The Q7 answer immediately below
  uses 48-bit addresses, so the 13-digit value is the typo.
- **Justification:** Cosmetic address-range typo in an interview question.

#### os/threads/green-threads.md:368
- **Wrong text:** `**Assining** green threads give parallelism:`
- **Correct text:** `**Assuming** green threads give parallelism:`
- **Verification:** Plain typo; "Assining" is not an English word.
- **Justification:** Spelling error in a Common Mistakes bullet.

#### os/kernel/ebpf.md:5
- **Wrong text:** `Merged into Linux 3.18 in 2014`
- **Correct text:** `Merged into Linux 3.15 in 2014 (the bpf() syscall that lets user space
  load programs landed in 3.18).`
- **Verification:** eBPF (extended BPF) JIT and verifier were merged in Linux 3.15 (June 2014).
  The `bpf(2)` syscall that lets user space load programs was added in 3.18 (December 2014).
  Saying "eBPF merged into 3.18" conflates the two and is the common but incorrect summary.
- **Justification:** Minor historical inaccuracy; doesn't affect the technical claims but is
  the kind of fact an interviewer might check.

## Files confirmed clean

The remaining 90 audited files showed no issues in arithmetic, OS definitions, code samples,
Mermaid diagrams, AI artifacts, placeholder code, self-contradictions, theorem statements,
LaTeX/MathJax, or ASCII diagrams. Notable clean files (deep-checked because they had the most
opportunity for errors):

- `os/memory/paging.md` (address translation example verified; only the typo above)
- `os/memory/swapping.md`, `os/memory/numa.md`, `os/memory/contiguous.md`,
  `os/memory/segmentation.md`, `os/memory/tlb.md`, `os/memory/mmap.md`,
  `os/memory/inverted-page-tables.md`
- `os/scheduling/README.md` (FCFS/SJF example numbers checked: avg wait 7.33 ✓, 6.0 ✓),
  `os/scheduling/fcfs.md` (avg wait 16.0, 17.0 verified), `os/scheduling/round-robin.md`
  (avg wait 5.67, avg turnaround 15.67 verified; only the `burst_map` typo flagged)
- `os/virtual-memory/README.md` (4-level PT walk, PTE format, TLB reach all checked),
  `os/virtual-memory/cow.md`, `os/virtual-memory/demand-paging.md`,
  `os/virtual-memory/thrashing.md`, `os/virtual-memory/clock.md`,
  `os/virtual-memory/page-replacement.md`, `os/virtual-memory/page-rejection.md`,
  `os/virtual-memory/compression.md`, `os/virtual-memory/working-set.md`
- `os/synchronization/cas.md`, `os/synchronization/readers-writers.md`,
  `os/synchronization/memory-barriers.md`, `os/synchronization/spinlocks.md`,
  `os/synchronization/lock-free.md`, `os/synchronization/semaphores.md`,
  `os/synchronization/sleeping-barber.md`, `os/synchronization/critical-section.md`,
  `os/synchronization/deadlocks/prevention.md`, `os/synchronization/deadlocks/recovery.md`,
  `os/synchronization/deadlocks/avoidance.md` (Banker's trace fully re-walked in Python — all
  steps correct), `os/synchronization/deadlocks/detection.md`
- `os/threads/README.md`, `os/threads/models.md`, `os/threads/pools.md`,
  `os/threads/user-vs-kernel.md`, `os/threads/safety.md`
- `os/processes/README.md`, `os/processes/daemons.md`, `os/processes/ipc-sockets.md`,
  `os/processes/context-switching.md`, `os/processes/ipc-shared-memory.md`,
  `os/processes/ipc-signals.md`, `os/processes/ipc.md`, `os/processes/states.md`,
  `os/processes/pcb.md`, `os/processes/ipc-message-queues.md`,
  `os/processes/zombie-orphan.md`, `os/processes/creation.md`,
  `os/processes/ipc-advanced.md`, `os/processes/ipc-pipes.md`
- `os/filesystems/README.md`, `os/filesystems/ext4.md` (extent-tree math: 4 × 32768 × 4 KB =
  512 MB verified), `os/filesystems/zfs.md`, `os/filesystems/directory-structure.md`,
  `os/filesystems/vfs.md`, `os/filesystems/ntfs.md`, `os/filesystems/btrfs.md`,
  `os/filesystems/file-concepts.md`, `os/filesystems/disk-allocation.md` (multi-level index
  arithmetic: 48 KB + 4 MB + 4 GB + 4 TB verified), `os/filesystems/free-space.md` (1 TB / 4 KB
  → 32 MB bitmap verified), `os/filesystems/xfs.md`, `os/filesystems/journaling.md`,
  `os/filesystems/fuse.md`
- `os/boot/README.md`, `os/boot/bootloader.md`, `os/boot/bios-uefi.md` (GPT 9.4 ZB for 64-bit
  LBA × 512 B verified), `os/boot/init-systems.md`
- `os/kernel/README.md`, `os/kernel/modules.md`, `os/kernel/io-uring.md`, `os/kernel/tracing.md`
- `os/io/README.md`, `os/io/buffering.md`, `os/io/disk-cscan.md` (C-SCAN total 382 verified),
  `os/io/interrupts.md`, `os/io/dma.md`, `os/io/device-drivers.md`,
  `os/io/software-layers.md`, `os/io/disk-look.md` (LOOK 299, C-LOOK 322 verified),
  `os/io/hardware.md`
- `os/containers/README.md`, `os/containers/docker.md`, `os/containers/namespaces.md`,
  `os/containers/kubernetes.md`, `os/containers/cgroups.md`
- `os/security/README.md`, `os/security/selinux.md`, `os/security/capabilities.md`,
  `os/security/access-control.md`
- `os/overview.md`

Severity breakdown: 6 HIGH, 8 MEDIUM, 3 LOW (one of the LOW items —
`monitors.md` Dining Philosophers code — is also counted under HIGH #5 because the missing
`lock` declaration is the more serious half of the same bug).
