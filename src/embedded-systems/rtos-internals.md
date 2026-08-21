# RTOS Internals: Scheduler, Ready List, Context Switch, IPC

A **real-time operating system** for a microcontroller is not Linux shrunk to fit. It is a different beast — typically a few thousand lines of portable C plus a thin layer of hand-written assembly per CPU architecture, no virtual memory, no driver framework by default, and a scheduler whose correctness is measured in nanoseconds rather than fairness. This page peels back the abstractions and walks through how the kernel actually decides who runs next, how it physically switches contexts on an ARM Cortex-M, how tasks talk to each other, and how that machinery compares to Linux's CFS.

It is the companion to [RTOS](./rtos.md) (concepts and FreeRTOS API overview), [Real-Time Systems](./real-time-systems.md) (scheduling theory and WCET), and [FreeRTOS Deep Dive](./freertos.md) (kernel internals in production code).

> **Interview one-liner:** "An RTOS keeps one linked-list per priority plus a bitmap of non-empty lists — the scheduler finds the next task with a CLZ instruction in O(1), the context switch is a Cortex-M PendSV that pushes R4–R11 in software after the CPU auto-stacks R0–R3/R12/LR/PC/xPSR, and IPC is just lists of blocked tasks sorted by priority."

## The Task Model

A **task** is a thread of execution with its own stack and a control block holding everything the kernel needs to schedule it. There is no process address space — every task shares the same flat memory map and sees every other task's globals. (Most Cortex-M cores have no MMU, and even the MPU is optional.) The boundary between tasks is therefore a software convention enforced by the kernel: the active stack pointer and the saved register state per task.

Each task lives in one of five states:

```
                 xTaskCreate / vTaskResume
                          |
                          v
                    +-----------+
        +---------->|  READY    |<--------+
        |           +-----------+         |
        |             ^     |             |
   preemption  yielded |     | unblocked  |
        |             |     v             |
        |           +-----------+         |
   +----+----+      |  RUNNING  |---+     |
   |  BLOCKED |<----+-----------+   |     |
   +---------+       wait queue    |     |
        ^                           |     |
        | wait                       |     |
        +----------------------------+     |
        v                                tick
   +---------+                            v
   |SUSPENDED|<-- vTaskSuspend        +---------+
   +---------+    ---vTaskResume ---> |DELETED  |
                                       +---------+
```

The transitions worth noting:

- **READY → RUNNING** is the scheduler pick; the kernel selects the highest-priority READY task.
- **RUNNING → BLOCKED** happens when the running task calls `xQueueReceive`, `xSemaphoreTake` with a timeout, or `vTaskDelay` — these move the TCB to a **wait list** attached to the synchronization object (or to the delayed-task list for delays).
- **BLOCKED → READY** is the unblock: either the tick handler advances time past the wake-up tick, or another task/ISR signals the synchronization object.
- **RUNNING → SUSPENDED** is explicit (`vTaskSuspend`); the task is parked indefinitely until `vTaskResume`. Blocked tasks can also be suspended; the suspend takes precedence.

## The Ready List

The heart of an RTOS is the **ready queue**. The classical data structure is *one doubly-linked list per priority level* plus a *bitmap of non-empty lists*. FreeRTOS literally does this:

```c
/* tasks.c — simplified */
PRIVILEGED_DATA TCB_t * volatile pxCurrentTCB = NULL;
PRIVILEGED_DATA List_t pxReadyTasksLists[ configMAX_PRIORITIES ];
PRIVILEGED_DATA List_t xDelayedTaskList1;          /* tick-relative  */
PRIVILEGED_DATA List_t xDelayedTaskList2;          /* overflow tick  */
PRIVILEGED_DATA List_t * volatile pxDelayedTaskList;
PRIVILEGED_DATA List_t * volatile pxOverflowDelayedTaskList;
PRIVILEGED_DATA List_t xPendingReadyList;          /* woken by ISR, not yet scheduled */
PRIVILEGED_DATA List_t xSuspendedTaskList;
PRIVILEGED_DATA List_t xTasksWaitingTermination;

/* Bitmap: bit n set if pxReadyTasksLists[n] is non-empty. */
PRIVILEGED_DATA volatile UBaseType_t uxTopReadyPriority = 0;
```

`uxTopReadyPriority` is a bit-array of `configMAX_PRIORITIES` bits. The scheduler finds the next task in **O(1)**:

```c
/* Find the highest-priority task that is ready. */
UBaseType_t uxTopPriority = uxTopReadyPriority;
while (listLIST_IS_EMPTY(&(pxReadyTasksLists[uxTopPriority])))
    --uxTopPriority;
TCB_t *pxNewTCB = listGET_OWNER_OF_HEAD_ENTRY(
    &pxReadyTasksLists[uxTopPriority]);
```

On Cortex-M3/M4/M7, FreeRTOS maps `uxTopReadyPriority` to a sequence of word-aligned bits and uses the CPU's **`CLZ` (Count Leading Zeros)** instruction to find the top set bit in a single cycle. The 56-priority maximum on Cortex-M ports comes from this trick fitting in two 32-bit words.

Why per-priority lists rather than a single sorted list? Because insertion into a sorted list of N tasks is O(N); insertion into a per-priority bucket is O(1) (head insert), and the round-robin time slice needs O(1) head rotation anyway. By contrast, Linux's CFS uses a red-black tree keyed on `vruntime` because it has hundreds of tasks and proportional fairness, not fixed priorities.

## Priority-Based Preemptive Scheduling

At every scheduling point the kernel compares the priority of the currently running task against `uxTopReadyPriority`. If the latter is higher, a context switch is requested. Three things trigger a check:

1. **Tick interrupt** — every 1 ms (typical), `xTaskIncrementTick` advances time, unblocks tasks whose wake tick has arrived, then checks whether the running task's time slice has expired and whether a higher-priority task is now ready.
2. **ISR exit (`portYIELD_FROM_ISR`)** — when an ISR signals a queue or semaphore that unblocks a task, it sets the PendSV bit so the scheduler runs as the ISR exits.
3. **API calls inside a task** — `xTaskDelay`, `xQueueSend`, `xSemaphoreTake` may all cause the current task to block, immediately yielding.

Round-robin time slicing within a priority is optional (`configUSE_TIME_SLICING`). When enabled, the head of the priority-N ready list rotates to the tail each tick the running task stays at priority N. When disabled, a task runs until it blocks or a higher-priority task preempts — useful when intra-priority jitter must be eliminated.

## Context Switching: Stack Save and Restore

The hard part. On Cortex-M the design is exquisitely tuned to the hardware. The trick relies on three features of the architecture:

- **Two stack pointers**: `MSP` (handler mode, ISRs) and `PSP` (thread mode, tasks). The kernel can swap PSP and "return" into a different stack frame.
- **Hardware auto-stacking on exception entry/exit**: when an exception fires, the CPU pushes R0–R3, R12, LR, PC, xPSR onto the active stack in 12 cycles. On exception return it pops them.
- **`EXC_RETURN` values**: writing `0xFFFFFFF9` to LR on `BX LR` returns to MSP, `0xFFFFFFFD` returns to PSP — the CPU takes this as "switch stack pointer and pop the auto-saved frame."

`PendSV` is a configurable-priority exception that FreeRTOS sets to the **lowest priority**. This guarantees it never interrupts an ISR — it always fires after all higher-priority ISRs have completed. That makes it the safe place to do the context switch.

The simplified `PendSV` handler (FreeRTOS `portable/GCC/ARM_CM3/port.c`), annotated:

```asm
PendSV_Handler:
    mrs   r0, psp                  @ r0 = current task stack
    ldr   r3, =pxCurrentTCB        @ r3 = &pxCurrentTCB
    ldr   r2, [r3]                 @ r2 = *pxCurrentTCB (current TCB)
    stmdb r0!, {r4-r11}            @ push callee-saved regs to PSP stack
    str   r0, [r2]                 @ save new top-of-stack into TCB

    push  {r3, lr}                 @ preserve pxCurrentTCB ptr + EXC_RETURN
    bl    vTaskSwitchContext       @ pick next task; pxCurrentTCB updated
    pop   {r3, lr}                 @ restore pxCurrentTCB ptr + EXC_RETURN

    ldr   r2, [r3]                 @ r2 = *pxCurrentTCB (new TCB)
    ldr   r0, [r2]                 @ r0 = new task's saved top-of-stack
    ldmia r0!, {r4-r11}            @ pop callee-saved regs
    msr   psp, r0                  @ set PSP to new task's stack
    bx    lr                       @ EXC_RETURN → CPU pops auto-stacked frame
```

What is happening:

1. The CPU has *already* pushed R0–R3, R12, LR, PC, xPSR to PSP on exception entry. `mrs r0, psp` reads where.
2. `stmdb r0!, {r4-r11}` saves the 8 callee-saved registers that the AAPCS requires across calls — the CPU didn't auto-stack these because they're called-callee-saved.
3. We store the new top-of-stack in the current TCB so resuming this task can find its state.
4. `vTaskSwitchContext` is portable C: it walks the ready lists and updates `pxCurrentTCB` to point to the next task.
5. We read the new TCB's saved top-of-stack, pop the 8 callee-saved registers into the right place, set PSP to the new task's stack.
6. `bx lr` with `lr = EXC_RETURN` (e.g. `0xFFFFFFFD`) tells the CPU: "you're returning to thread mode using PSP" — it pops the auto-stacked frame from the *new* PSP, restoring R0–R3/R12/LR/PC/xPSR. The PC restoration is what actually transfers control to the new task's code.

The whole switch is ~20 cycles of ISR code plus 12 cycles of hardware restore, on the order of 30–40 cycles — well under a microsecond on a 100 MHz Cortex-M4.

## Inter-Task Communication

The kernel exposes synchronization primitives that are all variations on "list of tasks waiting for a thing, sorted by priority." Once you see this pattern, all the primitives collapse into a single idea.

### Semaphores

A **binary semaphore** is a counter (0 or 1) plus a `List_t` of waiters. `xSemaphoreTake` decrements; if zero, the caller's TCB is moved from the ready list to the semaphore's wait list, sorted by priority (insertion uses `listINSERT_IN_PRIORITY_ORDER`), and the scheduler runs. `xSemaphoreGive` increments and, if waiters exist, removes the highest-priority one from the wait list and moves it back to the ready list (specifically, `xPendingReadyList` if called from an ISR — the actual ready-list move happens when the kernel re-enters task context).

A **counting semaphore** is the same with `uxCount` (an N-element pool). Used for resource counting (buffer slots, DMA channels).

### Mutexes

A **mutex** is a binary semaphore plus an owner pointer and the **priority-inheritance protocol**. When a high-priority task tries to take a mutex held by a low-priority task, the holder's effective priority is raised to the blocker's priority. On release, the original priority is restored. This bounds the worst-case blocking time of any task to a single critical section per mutex — essential for the RTA proof (see [Real-Time Systems](./real-time-systems.md)).

Why can't you use a mutex from an ISR? Because priority inheritance requires a "holder" task to boost. ISRs have no TCB. For ISR-to-task signaling, use a binary or counting semaphore.

### Message Queues

A **queue** is a FIFO of fixed-size items plus two wait lists (senders blocked because the queue is full, receivers blocked because it's empty). Crucially, FreeRTOS queues use **copy-by-value** semantics — `xQueueSend` `memcpy`s the item into the queue, `xQueueReceive` copies it out. This sidesteps shared-memory races at the cost of a copy.

```
   Producer Task              +----------------+            Consumer Task
   ------------               | [item][item]   |            ------------
   xQueueSend(q,&v,0) ----->  |   wait list    | <-----     xQueueReceive(q,&v,0)
   if full: block here       |  (senders)     |            if empty: block here
                              |   wait list    |
                              |  (receivers)   |
                              +----------------+
```

`FromISR` variants exist for queue use in ISRs; they never block, and they use a **lock count** (`cTxLock`, `cRxLock`) to defer the wake-up of unblocked tasks until the kernel re-enters task context. This avoids corrupting list structures while inside an ISR.

### Event Flags / Event Groups

An **event group** is a 24-bit flag set (configurable to 8/24 bits via `configUSE_16_BIT_TICKS`). A task can wait on an arbitrary boolean combination of bits — "bit 0 OR (bit 1 AND bit 2)" — using `xEventGroupWaitBits(eg, mask, clearOnExit, waitAll, timeout)`. The kernel checks the condition atomically when bits are set by any task or ISR. This is the cleanest primitive for fan-in synchronization: "wait until either the network is up or the user has pressed cancel."

### Direct Task Notifications (v8.2+)

A **task notification** is a 32-bit value + state in the TCB itself — no separate object. `xTaskNotifyGive(handle)` increments the target's notification value and unblocks it; `ulTaskNotifyTake(...)` blocks on it. This is **~45% faster than a semaphore** and uses no RAM beyond the TCB. The catch: a task can wait on only one notification at a time, and there's no queue of waiters. For one-to-one ISR→task signaling, this is the right primitive today.

## The Tick Interrupt

The **SysTick** peripheral on Cortex-M is a 24-bit down-counter driven from the CPU clock (or an external reference). FreeRTOS programs it to fire every 1 ms by default (`configTICK_RATE_HZ = 1000`). The tick handler does five things:

```c
void xPortSysTickHandler(void) {
    /* The CPU sets IPSR on exception entry; check we're not nesting. */
    portDISABLE_INTERRUPTS_FROM_ISR();
    {
        xTaskIncrementTick();          /* advance xTickCount, unblock delayed tasks */
        if (xYieldPending != pdFALSE)  /* time slice expired or higher prio ready */
            portYIELD_FROM_ISR();      /* Pend PendSV */
    }
    portENABLE_INTERRUPTS_FROM_ISR();
}
```

Inside `xTaskIncrementTick`: increment `xTickCount`; walk the delayed-task list (which is sorted by wake-tick), moving any task whose wake-tick has arrived back to its ready list; if the running task's time slice expired and another equal-priority task is ready, set `xYieldPending`. On the rare overflow tick (`xTickCount` wraps to 0), the two delayed-task lists swap (`pxDelayedTaskList` and `pxOverflowDelayedTaskList`) so the kernel doesn't have to re-sort anything.

A subtle but critical invariant: the delayed-task list is **sorted by wake-tick**, so the head is always the earliest wake-up. The tick handler can stop scanning the moment it sees a wake-tick in the future. Insertion is O(N) in the worst case but O(1) amortized for typical delayed-by-a-few-ticks workloads.

## Comparison to the Linux Scheduler

Linux's **CFS** (`kernel/sched/fair.c`, ~10 KLOC of core) and an RTOS scheduler (`tasks.c`, ~2 KLOC including all APIs) solve different problems:

| Property | RTOS scheduler | Linux CFS |
|---|---|---|
| **Pick algorithm** | O(1): bitmap + per-priority list | O(log N): leftmost in red-black tree by `vruntime` |
| **Fairness** | Strict priority — high prio starves low | Proportional fair by `vruntime` weight |
| **Preemption points** | Almost everywhere; critical sections ≤ µs | Limited by kernel preemption model (`PREEMPT_NONE` → `PREEMPT_RT`) |
| **RT priorities** | `configMAX_PRIORITIES` (typically 32–56) | 0–99 (`SCHED_FIFO`/`SCHED_RR`); CFS uses 100–139 |
| **Worst-case latency** | Sub-µs to a few µs on Cortex-M | ~10–100 µs with `PREEMPT_RT`, ms-class without |
| **Memory model** | Shared address space, no MMU required | Per-process address spaces, MMU required |
| **LOC + complexity** | ~5 KLOC total kernel | ~30 MLOC kernel |
| **SMP support** | Limited (FreeRTOS, Zephyr SMP) | First-class, scheduler domains, load balancing |

CFS is right for a server running ten thousand threads where fairness and throughput matter. An RTOS scheduler is right for a robot running eight tasks where the highest-priority task must run within 5 µs of an external event. Trying to use CFS for hard real-time requires `PREEMPT_RT` *plus* CPU isolation *plus* `mlockall` *plus* `SCHED_DEADLINE`, and you still can't certify it to DO-178C because the kernel is too large to analyze.

## FreeRTOS / Zephyr / ThreadX

| RTOS | License | Footprint | Scheduling | Notable feature |
|---|---|---|---|---|
| **FreeRTOS** | MIT | ~6 KB Flash / 1 KB RAM min | Fixed-priority preemptive + round-robin, priority inheritance on mutexes | De-facto standard, runs on billions of devices, AWS-maintained since 2017 |
| **Zephyr** | Apache 2.0 (Linux Foundation) | ~10 KB min, scalable to MB-class | Pluggable: preemptive, cooperative, EDF, SMP | Native devicetree, native Bluetooth/Thread/OpenThread, Kconfig-based |
| **ThreadX** (Eclipse OpenAD, formerly Azure RTOS) | MIT | ~2 KB min | Preemptive, priority inheritance, SMP preemption-threshold | "Preemption threshold" — a task can set its preempt floor, blocking preemption by lower-prio interrupts |
| **RIOT OS** | LGPL | ~1.5 KB min | Tickless, fixed priority | "Fire and forget" networking, native 6LoWPAN |
| **NuttX** | BSD | ~32 KB min | POSIX-compatible, SMP | Apache-licensed "small Linux" with VFS / fork() |

FreeRTOS dominates the MCU market by volume; Zephyr is the rising challenger with its Linux-style toolchain (Kconfig, devicetree, layered drivers). ThreadX dominates automotive (e.g. Renesas RH850, NXP S32) and was acquired by Microsoft in 2019 (rebranded Azure RTOS) then released to Eclipse in 2024. For new projects: pick Zephyr if you need a modern driver stack and devicetree; pick FreeRTOS if you need minimal footprint and maximal portability; pick ThreadX if you're in automotive or medical-certified paths.

## References

- [FreeRTOS Official Documentation](https://www.freertos.org/Documentation/RTOS_book.html) — task model, ready list, PendSV port notes.
- [FreeRTOS Kernel Source on GitHub](https://github.com/FreeRTOS/FreeRTOS-Kernel) — `tasks.c`, `queue.c`, `portable/GCC/ARM_CM3/port.c` for the actual context switch.
- [Zephyr Project Documentation](https://docs.zephyrproject.org/latest/) — scheduler concepts, EDF, SMP, devicetree.
- [ThreadX Documentation (Eclipse OpenAD)](https://github.com/eclipse-threadx/rtos) — preemption-threshold, thread control block.
- Jane W. S. Liu, *Real-Time Systems: Developer's Insight* (Prentice Hall, 2000), Chapters 5–8 — the canonical reference on fixed-priority scheduling and synchronization protocols.
- [ARM Cortex-M3 / Cortex-M4 / Cortex-M7 Processor Programming Manual (ARM DDI 0403 / 0553)](https://developer.arm.com/documentation/ddi0403/latest) — exception model, PSP/MSP, EXC_RETURN, PendSV, NVIC.
- [Embedded.com — "How to build a real-time scheduler" (Don Lecke, 2018)](https://www.embedded.com/how-to-build-a-real-time-scheduler/) — practical walk-through of the ready-list and tick-handler design.
- [Embedded.com — "Introduction to RTOS" series (D embedded staff)](https://www.embedded.com/category/rt-os/) — multi-part primer on context switching and IPC.
- See also: [RTOS](./rtos.md), [FreeRTOS Deep Dive](./freertos.md), [Real-Time Systems](./real-time-systems.md), [Firmware Boot & Watchdogs](./firmware.md).

## Interview Questions

1. **Walk through the data structure the FreeRTOS scheduler uses to find the next task to run. Why is it O(1)?**
   One doubly-linked list per priority plus a bitmap of non-empty lists. The scheduler finds the highest-set bit in the bitmap (using `CLZ` on Cortex-M) to index into the priority array, then takes the head of that list. Insertion/deletion are O(1) head ops. Total pick cost is constant regardless of task count.

2. **Why does FreeRTOS use PendSV for context switches instead of just doing the switch in the SysTick handler?**
   PendSV is configurable to the lowest exception priority, so it never interrupts another ISR. If the context switch ran in SysTick (typically higher priority), an interrupting higher-prio ISR would corrupt the partially-saved register state. PendSV waits until all ISRs complete, then fires once on the way out.

3. **What does `EXC_RETURN = 0xFFFFFFFD` mean to a Cortex-M CPU?**
   It's the magic value loaded into LR that tells the CPU on `BX LR`: "return to thread mode using PSP, pop the eight auto-stacked registers (R0–R3, R12, LR, PC, xPSR) from PSP." The kernel writes this to LR before the `BX` so the hardware does the heavy lifting of restoring the task's register state.

4. **Why are queues copy-by-value in FreeRTOS? What's the cost?**
   Copy-by-value sidesteps the lifetime and aliasing problem — the sender can return before the receiver reads, because the item lives in the queue. Cost: one `memcpy` of `uxItemSize` bytes per send and another per receive. For large items, use `xMessageBuffer` (variable-length, copy-by-value but efficient) or pass pointers and manage ownership explicitly.

5. **A task blocked on a queue is also in the queue's wait list. How does the kernel find and remove it from the ready list in O(1)?**
   Each TCB carries two `ListItem_t` nodes — `xStateListItem` (used for ready/blocked/suspended membership) and `xEventListItem` (used for queue/semaphore wait list membership). When the task blocks on a queue, the kernel does `listREMOVE_ITEM(&pxTCB->xStateListItem)` then `listINSERT_END(&pxQueue->xTasksWaitingToReceive, &pxTCB->xEventListItem)` — both O(1). The two-item design lets a task be in *exactly two* lists simultaneously without search.

6. **What's the worst-case blocking time for a task taking a mutex under priority inheritance?**
   Bounded to a single critical section of the lowest-priority holder: any medium-priority task that would normally preempt the holder is itself blocked from doing so because the holder has been boosted to the blocker's priority. RTA then uses this single-section bound as the interference term.

7. **Compare FreeRTOS to Linux CFS in one paragraph.**
   FreeRTOS picks the next task in O(1) from a bitmap-indexed per-priority list, allows preemption everywhere except a few critical-section boundaries measured in cycles, and assumes a single shared address space. CFS picks in O(log N) from a red-black tree ordered by `vruntime`, prioritizes fairness over strict priority, and assumes per-process address spaces with an MMU. FreeRTOS targets microsecond determinism on a 6 KB budget; CFS targets throughput fairness on megabytes of kernel.

8. **Why does the tick handler check `xYieldPending` and call `portYIELD_FROM_ISR` rather than context-switching inline?**
   Inline switch from the tick handler would corrupt the saved state if a higher-priority ISR fires *during* the switch. Setting `xYieldPending` and Pend-ing PendSV defers the actual switch to a point where all higher-priority ISRs have drained, guaranteeing atomicity of the swap.
