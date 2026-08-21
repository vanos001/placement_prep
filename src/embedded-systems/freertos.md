# FreeRTOS Deep Dive: TCB, Lists, port.c, and the Rest

FreeRTOS is the most widely deployed real-time operating system on the planet — running on billions of devices from smart watches to satellites. The codebase is small enough (under 10 KLOC of portable C plus a thin per-architecture port layer) to read end-to-end in an afternoon, and it should be read that way by anyone who works with it in production. This page walks through the kernel's internal structures and APIs: the Task Control Block (TCB), the ready/blocked/suspended lists, the most-used API calls, the architecture-specific `port.c` layer, tickless idle, stack-overflow detection, MPU support, and how FreeRTOS compares to Zephyr.

For scheduling theory and the kernel-agnostic view, see [RTOS Internals](./rtos-internals.md). For the high-level API tour, see [RTOS](./rtos.md).

> **Interview one-liner:** "A FreeRTOS TCB carries two ListItem_t nodes — one for ready/blocked/suspended membership, one for queue/semaphore wait-list membership — so a blocked task is in O(1) lists simultaneously; the context switch is a Cortex-M PendSV that pushes R4–R11 in software after the CPU auto-stacks R0–R3/R12/LR/PC/xPSR; and `port.c` is the ~500-line per-architecture shim between the portable kernel and the silicon."

## The Task Control Block (TCB)

Everything the kernel needs to know about a task lives in a `TCB_t`. The actual struct in `tasks.c` is dense; here is a stripped version with the portable-core fields annotated:

```c
typedef struct tskTaskControlBlock {
    volatile StackType_t *pxTopOfStack;  /* current SP, saved by PendSV  */
    ListItem_t xStateListItem;            /* node in ready/blocked/suspended */
    ListItem_t xEventListItem;            /* node in a queue/semaphore wait list */
    UBaseType_t uxPriority;               /* 0 = idle, up to configMAX_PRIORITIES-1 */
    StackType_t *pxStack;                 /* base of stack allocation (for free) */
    char pcTaskName[configMAX_TASK_NAME_LEN];
    UBaseType_t uxTCBNumber;              /* monotonic ID, for trace + SMP       */
    UBaseType_t uxTaskNumber;             /* user-set, used by trace macros      */

#if ( configUSE_MUTEXES == 1 )
    UBaseType_t uxBasePriority;            /* for priority-inheritance restore   */
    UBaseType_t uxMutexesHeld;             /* count of held mutexes              */
#endif
#if ( configUSE_TASK_NOTIFICATIONS == 1 )
    volatile uint32_t ulNotifiedValue[configTASK_NOTIFICATION_ARRAY_ENTRIES];
    volatile uint8_t  ucNotifyState[configTASK_NOTIFICATION_ARRAY_ENTRIES];
#endif
#if ( configUSE_NEWLIB_REENTRANT == 1 )
    struct _reent *pxNewLib_reent;          /* newlib thread-safety struct         */
#endif
#if ( portUSING_MPU_WRAPPERS == 1 )
    xMPU_SETTINGS xMPUSettings;             /* per-task MPU region config         */
#endif
#if ( configSUPPORT_STATIC_ALLOCATION == 1 )
    uint8_t ucStaticAllocationFlags;       /* who owns the TCB + stack buffers   */
#endif
} tskTCB;
typedef tskTCB TCB_t;
```

Two design choices are non-obvious and worth flagging:

1. **Two `ListItem_t` nodes per TCB.** A task is always in exactly one of the *state* lists (ready, blocked-on-queue-A, suspended, delayed) and may simultaneously be in an *event* list (the queue's wait list, the mutex's wait list). Two nodes make both insertions and both removals O(1) — there's no "find the task in the wait list" scan.
2. **`pxTopOfStack` is the first field by design.** On Cortex-M the PendSV handler reads `pxCurrentTCB` (a `TCB_t *`), dereferences it to get the top-of-stack, and pops registers from there. By placing `pxTopOfStack` at offset 0, the assembly avoids an offset load: `ldr r2, [r3]` (TCB at r3) yields `pxTopOfStack` directly.

## The Ready / Blocked / Suspended Lists

The kernel declares exactly these global lists in `tasks.c`:

```c
PRIVILEGED_DATA TCB_t * volatile pxCurrentTCB;                          /* running task */
PRIVILEGED_DATA List_t pxReadyTasksLists[ configMAX_PRIORITIES ];      /* one per prio */
PRIVILEGED_DATA List_t xDelayedTaskList1;                              /* current-tick delayed */
PRIVILEGED_DATA List_t xDelayedTaskList2;                              /* overflow-tick delayed */
PRIVILEGED_DATA List_t * volatile pxDelayedTaskList;                   /* points at list1 */
PRIVILEGED_DATA List_t * volatile pxOverflowDelayedTaskList;           /* points at list2 */
PRIVILEGED_DATA List_t xPendingReadyList;                              /* woken by ISR */
PRIVILEGED_DATA List_t xSuspendedTaskList;                             /* vTaskSuspend'd */
PRIVILEGED_DATA List_t xTasksWaitingTermination;                       /* deleted, idle reaps */
PRIVILEGED_DATA volatile UBaseType_t uxTopReadyPriority;               /* bitmap of non-empty lists */
PRIVILEGED_DATA volatile TickType_t xTickCount;                        /* monotonically increases */
PRIVILEGED_DATA volatile TickType_t uxTopUsedPriority;                 /* for trace */
```

The two `DelayedTaskList` lists implement a clever tick-overflow handling scheme. When you call `vTaskDelay(100)`, the kernel computes `wakeTick = xTickCount + 100`. If that addition overflows the 32-bit (or 16-bit) `TickType_t`, the task goes into the *overflow* list — otherwise into the *current* list. At every tick, the kernel walks the current list from the head (sorted by wake-tick) until it sees a future wake-tick. When `xTickCount` itself overflows to 0, the kernel **swaps** the two list pointers (`pxDelayedTaskList` and `pxOverflowDelayedTaskList`) — that swap is O(1), and the new "current" list is exactly the previously-overflow list, which is already sorted by absolute wake-tick (relative to the new overflow epoch). No re-sorting, no O(N) scan. This is one of the elegant parts of `tasks.c`.

`xPendingReadyList` solves an ISR-safety problem. When an ISR calls `xQueueSendFromISR` and unblocks a task, that task cannot be moved directly to a `pxReadyTasksLists[]` entry — the kernel might be in the middle of manipulating ready lists when interrupted. Instead, the task is moved to `xPendingReadyList`. On the next scheduler unlock (in `xTaskResumeAll` or `vTaskExitCritical`), the kernel drains `xPendingReadyList`, moving each task to its proper ready list. This is the trick that makes `FromISR` variants safe without disabling interrupts for long stretches.

## Creating and Managing Tasks

`xTaskCreate` is the entry point. It is essentially six steps wrapped in a critical section:

```c
BaseType_t xTaskCreate(TaskFunction_t pxTaskCode,
                       const char * const pcName,
                       const configSTACK_DEPTH_TYPE usStackDepth,
                       void * const pvParameters,
                       UBaseType_t uxPriority,
                       TaskHandle_t * const pxCreatedTask) {
    TCB_t *pxNewTCB;
    StackType_t *pxStack;
    /* 1. Allocate TCB + stack (heap_4 scheme). */
    pxNewTCB = pvPortMalloc(sizeof(TCB_t));
    pxStack  = pvPortMalloc(usStackDepth * sizeof(StackType_t));
    /* 2. Initialise list nodes and store stack base. */
    prvInitialiseTCBVariables(pxNewTCB, pcName, uxPriority, ...);
    pxNewTCB->pxStack = pxStack;
    /* 3. Paint the stack with 0xA5A5A5A5 for overflow detection. */
    (void)memset(pxStack, (int)tskSTACK_FILL_BYTE, usStackDepth * sizeof(StackType_t));
    /* 4. Build the initial stack frame so first switch "returns" into the task. */
    pxNewTCB->pxTopOfStack = pxPortInitialiseStack(pxStack + usStackDepth - 1,
                                                   pxTaskCode, pvParameters);
    /* 5. Critical section: insert into ready list, update bitmap. */
    taskENTER_CRITICAL();
    {
        prvAddTaskToReadyList(pxNewTCB);
    }
    taskEXIT_CRITICAL();
    /* 6. If running, yield to the new task if higher priority. */
    if (xSchedulerRunning != pdFALSE && pxNewTCB->uxPriority > uxCurrentPriority)
        taskYIELD_IF_USING_PREEMPTION();
    return pdPASS;
}
```

`pxPortInitialiseStack` is the **architecture-specific** initial stack painter. On Cortex-M it pushes the auto-stacked register set onto the new task's stack with PC set to the task entry function and LR set to `prvTaskExitError` (so a task that returns crashes predictably). The remaining callee-saved registers R4–R11 are pushed with placeholder values. When the scheduler first switches to this task, PendSV pops R4–R11, then `BX LR` with `EXC_RETURN = 0xFFFFFFFD` causes the hardware to pop R0–R3/R12/LR/PC/xPSR — transferring control to the task entry point with R0 set to `pvParameters`.

### Static allocation

`xTaskCreateStatic` is identical except the caller provides the TCB buffer and stack buffer:

```c
TaskHandle_t xTaskCreateStatic(TaskFunction_t pxTaskCode,
                               const char * const pcName,
                               const configSTACK_DEPTH_TYPE uxStackDepth,
                               void * const pvParameters,
                               UBaseType_t uxPriority,
                               StackType_t * const puxStackBuffer,
                               StaticTask_t * const pxTaskBuffer);
```

For safety-critical systems (DO-178C, ISO 26262) static allocation is the only acceptable option because the heap is forbidden after `vTaskStartScheduler`. Set `configSUPPORT_STATIC_ALLOCATION = 1` and provide `vApplicationGetIdleTaskMemory` and `vApplicationGetTimerTaskMemory` hooks to give the kernel static TCBs for the idle and timer tasks.

### `vTaskDelay` and `vTaskDelayUntil`

`vTaskDelay(n)` blocks the calling task for *n* ticks starting **now**. The wake tick drifts because the call overhead and any preemption during the delay add to the next "now." For periodic work, use `vTaskDelayUntil(&lastWake, period)`:

```c
void vSensorTask(void *pv) {
    TickType_t lastWake = xTaskGetTickCount();
    for (;;) {
        read_and_publish();
        vTaskDelayUntil(&lastWake, pdMS_TO_TICKS(10));   /* 100 Hz, drift-free */
    }
}
```

`vTaskDelayUntil` computes the next wake tick as `lastWake + period` (not `now + period`), so jitter from `read_and_publish()` does not accumulate over cycles. The task's period is anchored to its start time.

## Queues: `xQueueSend` and `xQueueReceive`

A FreeRTOS queue is a circular byte buffer plus two wait lists:

```c
typedef struct QueueDefinition {
    int8_t *pcHead;                  /* start of storage area               */
    int8_t *pcTail;                  /* end of storage area                 */
    int8_t *pcWriteTo;               /* next free slot                      */
    int8_t *pcReadFrom;              /* next slot to read                   */
    List_t xTasksWaitingToSend;      /* blocked senders (queue full)        */
    List_t xTasksWaitingToReceive;   /* blocked receivers (queue empty)     */
    volatile UBaseType_t uxMessagesWaiting;
    UBaseType_t uxLength;            /* capacity in items                   */
    UBaseType_t uxItemSize;          /* bytes per item                      */
    volatile signed char cTxLock;    /* deferred ISR-wake counter (send)    */
    volatile signed char cRxLock;    /* deferred ISR-wake counter (recv)     */
    uint8_t ucQueueType;             /* queue/semaphore/mutex discriminator */
} Queue_t;
```

The send path:

```c
BaseType_t xQueueGenericSend(QueueHandle_t xQueue, const void *pvItemToQueue,
                              TickType_t xTicksToWait, BaseType_t eAction) {
    BaseType_t xYieldRequired = pdFALSE;
    /* Lock the queue: cTxLock-- means "we're inside a critical section
       that defers unblock calls until the queue is unlocked". */
    vTaskSuspendAll();
    prvLockQueue(pxQueue);
    if (queue is full) {
        if (xTicksToWait > 0) {
            /* Move current task to xTasksWaitingToSend, sorted by priority. */
            vTaskPlaceOnEventList(&(pxQueue->xTasksWaitingToSend), xTicksToWait);
            prvUnlockQueue(pxQueue);
            if (xSchedulerRunning != pdFALSE) taskYIELD();
        }
    } else {
        /* Copy item in, advance write pointer. */
        prvCopyDataToQueue(pxQueue, pvItemToQueue, eAction);
        /* If receivers are waiting, unblock the highest-prio one. */
        if (listLIST_IS_NOT_EMPTY(&(pxQueue->xTasksWaitingToReceive))) {
            if (xTaskRemoveFromEventList(&(pxQueue->xTasksWaitingToReceive)))
                xYieldRequired = pdTRUE;   /* receiver prio > current */
        }
        prvUnlockQueue(pxQueue);
        if (xYieldRequired) taskYIELD();
    }
    return pdPASS;
}
```

`FromISR` variants look similar but never block. Instead of moving the calling task to a wait list, they return `pdFAIL` (queue full) and let the caller decide. Crucially, when unblocking a task, the `FromISR` variant *does not* call `prvAddTaskToReadyList` directly — it calls `vTaskNotifyGiveFromISR` semantics by appending to `xPendingReadyList` and bumping `cTxLock`/`cRxLock`. The drain happens when the scheduler resumes (`xTaskResumeAll`).

The standard ISR-to-task producer/consumer:

```c
QueueHandle_t xIsrQueue;
volatile uint32_t ulAdcValue;

void vAdcHandler(void) {                            /* in ISR context  */
    BaseType_t xHigherPrioTaskWoken = pdFALSE;
    uint32_t v = ADC->DR;
    xQueueSendFromISR(xIsrQueue, &v, &xHigherPrioTaskWoken);   /* never blocks   */
    portYIELD_FROM_ISR(xHigherPrioTaskWoken);                 /* Pend PendSV     */
}

void vConsumerTask(void *pv) {
    uint32_t v;
    for (;;) {
        if (xQueueReceive(xIsrQueue, &v, portMAX_DELAY) == pdPASS) {
            process(v);
        }
    }
}
```

The `xHigherPrioTaskWoken` out-parameter is the kernel's way of saying "the task I just unblocked has higher priority than whatever was running — please Pend a context switch as you exit the ISR." `portYIELD_FROM_ISR(pdTRUE)` sets the PendSV bit; the actual switch happens after all higher-priority ISRs have drained.

## The `port.c` Layer

FreeRTOS splits cleanly into:

- **Portable kernel** — `tasks.c`, `queue.c`, `list.c`, `timers.c`, `event_groups.c`. Pure C, OS-agnostic, run anywhere.
- **Per-architecture port** — `portable/<compiler>/<arch>/port.c` + `portmacro.h`. This is where the rubber meets the silicon.

Each `port.c` implements the same contract:

| Symbol | Purpose |
|---|---|
| `pxPortInitialiseStack` | Paint initial stack frame so first context switch "returns" into the task entry. |
| `vPortStartScheduler` | Configure SysTick + pend priority + start first task. |
| `vPortYield` / `vPortYieldFromISR` | Pend PendSV to trigger a context switch. |
| `vPortSVCHandler` | SVC handler — used at start to switch into the first task. |
| `xPortPendSVHandler` (or `xPortPendSVHandler` aliased to `PendSV_Handler`) | The actual context switch. |
| `xPortSysTickHandler` (or aliased to `SysTick_Handler`) | Tick handler — increment, unblock, yield. |
| `portSAVE_CONTEXT` / `portRESTORE_CONTEXT` (some ports) | Macros expanded inside the PendSV handler. |
| `portENTER_CRITICAL` / `portEXIT_CRITICAL` | Wrap a critical section; on Cortex-M uses `BASEPRI` to mask only below `configMAX_SYSCALL_INTERRUPT_PRIORITY`, leaving fast ISRs running. |
| `portDISABLE_INTERRUPTS` / `portENABLE_INTERRUPTS` | Hard `cpsid i` / `cpsie i` — used rarely, mostly inside critical inner loops. |

The Cortex-M3/M4/M7 PendSV handler is small enough to reproduce here. This is the kernel of the kernel:

```asm
PendSV_Handler:
    mrs   r0, psp                   @ r0 = task's PSP
    ldr   r3, =pxCurrentTCB        @ r3 = &pxCurrentTCB
    ldr   r2, [r3]                 @ r2 = *pxCurrentTCB (cur TCB*)
    stmdb r0!, {r4-r11}            @ push callee-saved regs to PSP
    str   r0, [r2]                 @ save new top-of-stack into TCB

    push  {r3, lr}                 @ save pxCurrentTCB ptr + EXC_RETURN
    bl    vTaskSwitchContext       @ updates pxCurrentTCB to next task
    pop   {r3, lr}

    ldr   r2, [r3]                 @ r2 = *pxCurrentTCB (new TCB*)
    ldr   r0, [r2]                 @ r0 = new task's saved top-of-stack
    ldmia r0!, {r4-r11}            @ pop callee-saved regs
    msr   psp, r0                  @ PSP now points at new task's stack
    bx    lr                       @ EXC_RETURN (0xFFFFFFFD) — CPU pops auto-frame
```

Why `BASEPRI` rather than `cpsid i` for critical sections? Cortex-M's `configMAX_SYSCALL_INTERRUPT_PRIORITY` lets the kernel block only "FromISR-safe" interrupts while leaving higher-priority (and never-kernel-touching) interrupts running — e.g. a motor-control PWM ISR at priority 0 can preempt the kernel's critical section. `BASEPRI` masks only priorities ≥ `configMAX_SYSCALL_INTERRUPT_PRIORITY`, leaving the highest-priority interrupts unblocked. `cpsid i` would block *everything*, including the safety-critical PWM loop.

## Tickless Idle

The default tick fires every 1 ms. If the only ready task is the idle task, the CPU wakes 1000 times per second to do nothing — burning power. **Tickless idle** stops the SysTick and reprograms it (or a separate low-power timer) for the next meaningful wake-up.

Implementation skeleton:

```c
void vPortSuppressTicksAndSleep(TickType_t xExpectedIdleTime) {
    /* xExpectedIdleTime = ticks until next task becomes ready. */
    /* 1. Configure a one-shot low-power timer for that many ticks. */
    /* 2. Set the new timer's interrupt to wake us. */
    /* 3. Enter WFI (or DSB + WFI + ISR) — CPU halts until interrupt. */
    /* 4. On wake, count how many ticks have elapsed. */
    /* 5. Call vTaskStepTicks(elapsed) to advance xTickCount + unblock. */
}
```

FreeRTOS's Cortex-M port uses SysTick's LOAD value reload trick: it reprograms the SysTick to fire after `xExpectedIdleTime` ticks, then `__WFI`s. On wake, it reads the SysTick VAL register to compute how many ticks actually elapsed (if an interrupt other than SysTick woke us, fewer ticks have passed than expected). It then adjusts `xTickCount` and reprograms SysTick for 1 ms. The contract is `configUSE_TICKLESS_IDLE = 1` + `portSUPPRESS_TICKS_AND_SLEEP(xExpectedIdleTime)`.

Watch for the **maximum suppress count** — on Cortex-M the 24-bit SysTick counter limits tickless to `(2^24-1)/configCPU_CLOCK_HZ` seconds. At a 100 MHz core, that's ~167 ms maximum idle sleep per cycle. Beyond that you need a separate low-power timer (RTCs, LPITIM on NXP, LPTIM on STM32).

## Stack Overflow Detection

FreeRTOS offers `configCHECK_FOR_STACK_SIZE` with three values:

| Value | Method | Cost | Detects |
|---|---|---|---|
| 0 | Off | 0 cycles | Nothing |
| 1 | Stack-painting | One comparison per context switch | Stack grew into the canary (0xA5A5A5A5) pattern at the bottom of the stack |
| 2 | Stack-painting + SP-in-bounds | A few cycles per context switch | Method 1 *plus* SP overflow past the stack top (post-increment bug, recursion) |

Method 1 paints `0xA5A5A5A5` into the entire stack at `xTaskCreate` time and checks the last `uint32_t` of the stack at every switch. If it has been overwritten, the stack grew at least to the bottom. Method 2 additionally checks that the current `pxTopOfStack` is within the stack's allocated range, catching the rare case where the task overflows past the top in a single deep call.

The hook:

```c
void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName) {
    /* Log the task name, then reboot. */
    log_error("Stack overflow in %s\n", pcTaskName);
    NVIC_SystemReset();
}
```

These methods are *runtime* detection, not formal proof. For DO-178C / ISO 26262 certification you must additionally perform **static stack analysis** (e.g. StackAnalyzer, aiT stack) to prove that the sum of worst-case call-depth stacks across all tasks fits in the allocated RAM. Method 2 is good engineering hygiene; it is not a substitute for analysis.

## MPU Support

Cortex-M3/M4/M7 cores ship with an optional **Memory Protection Unit (MPU)** — typically 8 or 16 regions, no virtual memory, no remap. FreeRTOS's MPU port (`portable/GCC/ARM_CM3_MPU/port.c`) wraps task switches with MPU region reconfiguration:

```c
typedef struct xMPU_SETTINGS {
    xMPU_REGION xRegion[ portNUM_CONFIGURABLE_REGIONS ];
    /* per-task: region base, size, access bits */
} xMPU_SETTINGS;

typedef struct xTASK_PARAMETERS {
    TaskFunction_t pvTaskCode;
    const char *pcName;
    uint16_t usStackDepth;
    void *pvParameters;
    UBaseType_t uxPriority;
    StackType_t *puxStackBuffer;
    MemoryRegion_t xRegions[ portNUM_CONFIGURABLE_REGIONS ];
} TaskParameters_t;
```

A task can run **unprivileged** — its priority bit is set so the CPU drops to unprivileged thread mode after the SVC syscall that creates it. The MPU regions bound what addresses it can read/write/execute. Any access outside the configured regions faults (MemManage exception).

The cost is significant:

- System calls (`SVC`) are required for every kernel API — unprivileged code cannot touch kernel data directly.
- Region count is tiny (8 typical); you cannot carve per-task per-object regions easily. Common pattern: one region for task stack, one for shared read-only data, one for kernel calls window.
- Switching tasks reloads all MPU regions; the per-switch cost rises by tens of cycles.

For mixed-criticality systems (e.g. a certified motor-control loop running alongside a third-party communication stack), MPU isolation is essential — a bug in the comm stack hard-faults instead of corrupting the safety loop's state.

## Comparison to Zephyr

| Aspect | FreeRTOS | Zephyr |
|---|---|---|
| License | MIT | Apache 2.0 |
| Min Flash / RAM | ~6 KB / 1 KB | ~10 KB / 4 KB (smallest config) |
| Build system | Make / CMake (loose) | CMake + Kconfig + devicetree (opinionated) |
| Driver model | "Bring your own HAL" — vendor SDK | Native driver tree with device instances from devicetree |
| Networking | Optional stack (FreeRTOS-Plus-TCP) | Native: TCP, BLE, OpenThread, 6LoWPAN, Wi-Fi |
| SMP | FreeRTOS-SMP branch (paid-tier historically; mainline 10.4+ has SMP core) | First-class multi-core scheduler from day one |
| Scheduling | Fixed-priority preemptive + round-robin | Pluggable: preemptive, cooperative, EDF, SMP |
| Memory mgmt | `heap_1`–`heap_5` schemes | `k_malloc` backed by sys_heap, multi-heap, memory domain isolation |
| Devicetree | Not used | Mandatory — describes all hardware |
| Tooling | CubeMX, vendor IDEs | West CLI, native VS Code integration, Kconfig menuconfig |

FreeRTOS wins on **portability and minimal footprint**: it's the right choice for a small Cortex-M0 sensor with 8 KB RAM. Zephyr wins on **developer experience and driver ecosystem**: if you need Bluetooth Mesh, OpenThread, or a driver stack for a complex SoC, Zephyr's repo already has it. For new products in 2024 with > 64 KB Flash and complex connectivity, Zephyr is increasingly the default. Forthcoming Zephyr-RTOS-profile work (POSIX profile, RT profile) is narrowing the gap further.

## References

- [FreeRTOS Official Documentation](https://www.freertos.org/Documentation/RTOS_book.html) — API reference, configuration options, port layer docs.
- [Mastering the FreeRTOS Kernel (PDF, 2024)](https://www.freertos.org/Documentation/161204_Mastering_the_FreeRTOS_Real_Time_Kernel-A_Hands-On_Tutorial_Guide.pdf) — the official hands-on book by Richard Barry, the FreeRTOS author.
- [FreeRTOS-Kernel on GitHub](https://github.com/FreeRTOS/FreeRTOS-Kernel) — the source. Read `tasks.c`, `queue.c`, `list.c`, and `portable/GCC/ARM_CM3/port.c` end-to-end.
- [FreeRTOS Community Forum](https://forums.FreeRTOS.org/) — active, maintained, real bug reports.
- [ARM Cortex-M3/M4/M7 Programming Manual (DDI 0403 / 0553)](https://developer.arm.com/documentation/ddi0403/latest) — exception model, NVIC, BASEPRI, EXC_RETURN, MPU.
- [AWS FreeRTOS Qualification Program](https://www.freertos.org/FreeRTOS-Plus/Qualification_AWS.html) — DO-178C / ISO 26262 qualification path for safety-critical FreeRTOS distributions.
- [Zephyr Project Documentation](https://docs.zephyrproject.org/latest/) — for direct comparison: scheduling, devicetree, SMP.
- [Embedded.com — "FreeRTOS from the ground up" (Jack Ganssle)](https://www.embedded.com/freertos-from-the-ground-up/) — historical and practical perspective from a long-time embedded columnist.
- See also: [RTOS Internals](./rtos-internals.md), [RTOS](./rtos.md), [Real-Time Systems](./real-time-systems.md).

## Interview Questions

1. **Why does each FreeRTOS TCB have two `ListItem_t` nodes?**
   A task is always in exactly one *state* list (ready, delayed, suspended, or one of the special lists) and may simultaneously be in an *event* list (the wait list of a queue or semaphore). Two nodes give O(1) membership in both lists without searching.

2. **Walk through what happens when `xTaskCreate` is called and the new task has higher priority than the running task.**
   TCB and stack are allocated; `pxPortInitialiseStack` paints the initial frame; the new TCB is pushed onto `pxReadyTasksLists[uxPriority]` and the corresponding bit in `uxTopReadyPriority` is set. `xTaskCreate` then sees the new priority exceeds the running task's priority and calls `taskYIELD_IF_USING_PREEMPTION`, which Pends PendSV. PendSV fires after the call returns, switches to the new task, and `BX LR` with `EXC_RETURN = 0xFFFFFFFD` causes the hardware to pop the new task's auto-stacked frame into R0–R3/R12/LR/PC/xPSR, transferring control to the task entry point.

3. **How do `xQueueSendFromISR` and `xQueueSend` differ in what they do to the wait lists?**
   `xQueueSend` may block: if the queue is full and a timeout is supplied, the calling task is moved to `xTasksWaitingToSend` and `xTaskResumeAll` is called to switch away. `xQueueSendFromISR` never blocks. When it unblocks a receiver, the receiver is appended to `xPendingReadyList` and `cTxLock`/`cRxLock` is incremented. The actual move to `pxReadyTasksLists[]` happens later, when the scheduler unlocks via `xTaskResumeAll` or `vTaskExitCritical` — because list mutation inside an ISR would race with the kernel.

4. **Why does FreeRTOS use `BASEPRI` rather than `cpsid i` for critical sections on Cortex-M?**
   `configMAX_SYSCALL_INTERRUPT_PRIORITY` lets the kernel mask only "kernel-touching" interrupts while leaving higher-priority (never-kernel-touching) interrupts unmasked. `BASEPRI` masks priorities ≥ the threshold; `cpsid i` masks everything. A safety-critical motor-control ISR running at priority 0 needs to fire even when the kernel is in a critical section; `BASEPRI` lets it, `cpsid i` would block it.

5. **Describe the tick-overflow handling in `tasks.c`. Why two delayed-task lists?**
   `vTaskDelay(n)` computes `wakeTick = xTickCount + n`; if that overflows the 32-bit `TickType_t`, the task is placed in the *overflow* list (sorted by absolute wake-tick relative to the next epoch). The *current* list is sorted by absolute wake-tick relative to the current epoch. When `xTickCount` itself overflows to 0, the kernel swaps the two list pointers in O(1); the new current list is exactly the previously-overflow list, which is already correctly sorted. No re-sorting, no O(N) scan.

6. **A 100 MHz Cortex-M4 with `configTICK_RATE_HZ = 1000` uses tickless idle. What is the maximum idle sleep, and why?**
   SysTick is a 24-bit down-counter. Max reload = `2^24 - 1 = 16,777,215` cycles. At 100 MHz that's ~167.8 ms. Beyond that, FreeRTOS needs a separate low-power timer (e.g. STM32 LPTIM, NXP LPITIM) driven from a 32 kHz LSE crystal.

7. **Compare `xTaskCreate` and `xTaskCreateStatic`. When would you use each?**
   `xTaskCreate` allocates TCB and stack from the heap (`pvPortMalloc`). `xTaskCreateStatic` takes caller-provided TCB and stack buffers — no heap use. Use static allocation for safety-critical systems (DO-178C, ISO 26262) where dynamic allocation is forbidden after boot, and where the heap scheme itself introduces unacceptable non-determinism.

8. **What does `configCHECK_FOR_STACK_SIZE = 2` detect that `= 1` does not?**
   Method 1 only checks that the bottom canary (0xA5A5A5A5) is intact, catching slow growth into the bottom. Method 2 also checks that the current `pxTopOfStack` lies within the stack's allocated range, catching the rare case where a task overflows past the *top* in a single deep call or recursion before any write hits the bottom canary. Neither is a substitute for static stack analysis in safety-critical code.

9. **When would you choose Zephyr over FreeRTOS for a new product?**
   When the device has > 64 KB Flash, complex connectivity needs (BLE, Thread, Wi-Fi), and benefits from a native driver tree — Zephyr's devicetree-based driver model and built-in networking stack accelerate development. When the device is a sub-32 KB Flash sensor, or when long-term portability across many MCUs is the priority, FreeRTOS remains the right choice.
