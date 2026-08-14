# Real-Time Operating Systems (RTOS)

## Bare-Metal vs RTOS

**Bare-metal** programming uses a superloop (infinite `while(1)`) with interrupt-driven I/O. It is simple and deterministic, but becomes unwieldy as application complexity grows. State machines, task scheduling, and inter-task communication must all be hand-implemented.

An **RTOS** provides these primitives out of the box:

| Feature | Bare-Metal | RTOS |
|---------|-----------|------|
| Task management | Manual state machines | Kernel-managed tasks/threads |
| Scheduling | Round-robin or hand-coded | Priority-based preemptive |
| Inter-task comm | Global variables, flags | Queues, semaphores, event groups |
| Timing | `delay()` blocks everything | `vTaskDelay()` yields to other tasks |
| Code organization | Monolithic main loop | Modular tasks with clear responsibilities |

## FreeRTOS Core Concepts

FreeRTOS is the most widely deployed RTOS, running on billions of devices. It is open-source (MIT license) and supports ARM Cortex-M, RISC-V, and many other architectures.

### Tasks

A task is an independent thread of execution with its own stack and priority. FreeRTOS uses a **ready list** per priority level. Tasks can be in one of four states: **Running**, **Ready**, **Blocked** (waiting on a timeout or synchronization object), or **Suspended**.

```c
void vSensorTask(void *pvParameters) {
    for (;;) {
        uint16_t reading = read_adc();
        xQueueSend(sensorQueue, &reading, pdMS_TO_TICKS(100));
        vTaskDelay(pdMS_TO_TICKS(50)); // Yield for 50 ms
    }
}

// In main:
xTaskCreate(vSensorTask, "Sensor", 256, NULL, tskIDLE_PRIORITY + 1, NULL);
vTaskStartScheduler(); // Starts the RTOS — never returns
```

### Queues

Queues provide thread-safe, first-in-first-out (FIFO) data passing between tasks and ISRs. They use a copy-by-value semantics—the sender copies data into the queue, and the receiver copies it out. FreeRTOS queues support blocking sends and receives with optional timeouts.

### Semaphores

- **Binary semaphores**: Synchronize two tasks or a task with an ISR (equivalent to a flag with blocking)
- **Counting semaphores**: Manage a pool of resources (e.g., N buffer slots)
- **Mutexes**: Protect shared resources with **priority inheritance** to prevent priority inversion

### Software Timers

FreeRTOS provides one-shot and auto-reload timers that execute a callback when they expire. Timer callbacks run in a dedicated **timer daemon task** (lower priority than most application tasks), so they should not block.

## Scheduling

### Preemptive Scheduling

The default FreeRTOS scheduler is **priority-based preemptive with round-robin within the same priority**. A higher-priority task that becomes ready immediately preempts the currently running lower-priority task. This provides deterministic response for high-priority work.

### Cooperative Scheduling

In cooperative mode, tasks must explicitly yield (via `taskYIELD()` or blocking on a synchronization object). This is useful when:
- You need strict control over context switch points
- You want to avoid stack overflow from unexpected preemption
- You are porting from a cooperative environment

## Priority Inversion and Inheritance

**Priority inversion** occurs when a high-priority task is blocked waiting for a resource held by a low-priority task, and a medium-priority task preempts the low-priority task, extending the high-priority task's wait time indefinitely.

```
High-priority task → needs mutex held by Low-priority task
Medium-priority task → preempts Low-priority task
Result: High-priority task waits as long as Medium-priority task runs
```

**Priority inheritance** solves this: when the low-priority task holds a mutex needed by a high-priority task, the low-priority task temporarily inherits the high priority until it releases the mutex. FreeRTOS mutexes implement priority inheritance by default.

**Priority ceiling** is an alternative: each mutex has a pre-assigned ceiling priority. Any task acquiring the mutex has its priority elevated to the ceiling. This prevents inversion from occurring in the first place.

## Deadlock in RTOS

Deadlock occurs when two or more tasks each hold a resource the other needs and neither will release:

```
Task A: holds Mutex 1, waits for Mutex 2
Task B: holds Mutex 2, waits for Mutex 1
→ Both block forever
```

Prevention strategies:
- **Always acquire locks in a fixed global order** (the most practical approach)
- Use `xSemaphoreTake` with a timeout (FreeRTOS supports this)
- Implement a lock hierarchy with compile-time enforcement
- Use a single mutex for a group of related resources

## Memory Constraints

FreeRTOS offers five memory allocation schemes, each with different trade-offs:

| Scheme | Fragmentation | Determinism | Best For |
|--------|--------------|-------------|----------|
| `heap_1` | None (alloc only) | Very high | Static systems, no frees |
| `heap_2` | High | Low | Deprecated — avoid |
| `heap_3` | High | Low | Wraps `malloc`/`free` |
| `heap_4` | Low (coalescence) | High | General-purpose use |
| `heap_5` | Low | High | Multiple non-contiguous memory regions |

For safety-critical systems, static allocation (compile-time stack sizing) is preferred. MISRA C guidelines discourage dynamic allocation entirely.

## References

- [FreeRTOS Official Documentation](https://www.freertos.org/Documentation/RTOS_book.html)
- [FreeRTOS Kernel Developer Docs](https://www.freertos.org/kernel.html)
- [Zephyr RTOS Documentation](https://docs.zephyrproject.org/)
- [The Engineering of Real-Time Embedded Systems](https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/)

## Interview Questions

1. What is the difference between a semaphore and a mutex in FreeRTOS?
2. Explain priority inversion with a concrete example. How does priority inheritance solve it?
3. What happens when two tasks of equal priority are both ready in FreeRTOS?
4. Why is `vTaskDelay` preferred over a busy-wait loop?
5. What is the minimum stack size for a FreeRTOS task and how do you determine it?
6. Explain how a FreeRTOS queue differs from a simple ring buffer shared via a mutex.
7. How would you communicate data from an ISR to a task? Why can't you use a mutex in an ISR?
8. What is priority ceiling protocol and when is it preferable to priority inheritance?
9. Describe a scenario where `heap_4` allocation could still lead to failure in an embedded system.
10. How does FreeRTOS handle interrupt nesting? What is the `configMAX_SYSCALL_INTERRUPT_PRIORITY`?