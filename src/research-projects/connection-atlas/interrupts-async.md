# Reacting Instead of Polling: Interrupts, Signals, epoll, and Event Loops

## Overview

Four mechanisms, four layers of the same stack, all solving one problem: *thousands of things can wait, only a few are ready, and the waiter's thread is too valuable to spend blocking.* A NIC asserts an interrupt line and the CPU drops what it was doing to run a handler. The kernel raises a signal and a process drops what it was doing to run a handler. epoll reports that a socket is readable and the event loop drops what it was doing to run a callback. A future resolves and the runtime schedules its continuation. Each layer is the one above its "hardware": the device interrupts the kernel, the kernel interrupts the process, the runtime interrupts the task. And each layer inherits the same two commandments — handle fast, then defer — which reappear in userland as "don't block the event loop."

This page explains each layer independently, names the shared principle, traces one blocked database call through a Node-style event loop as a worked example with a timeline, and marks where the analogy breaks: priorities, preemption, and who is allowed to wait.

## The Concepts, Independently

**Hardware interrupts.** Devices cannot wait for the CPU to poll them, so they signal: a line assertion or a message (MSI/MSI-X) reaches the interrupt controller, and the CPU saves minimal context and vectors to the driver's interrupt service routine (ISR) ([../../os/io/interrupts.md](../../os/io/interrupts.md)). Two design facts shape everything downstream. First, the ISR runs *with parts of the system preempted* — on Linux, a hard IRQ handler runs with interrupts (mostly) disabled on that CPU — so handlers are deliberately minimal, deferring the rest to softirqs, tasklets, or threaded IRQs: the top-half/bottom-half split. Second, interrupt cost is real: at high packet rates, per-packet interrupts burn the CPU, which is why NAPI switches the NIC path to *polling under load* — the acknowledgment that event-driven beats polling only while events are sparse. DMA completes the picture: the device writes the payload to memory itself and the interrupt merely announces completion ([../../os/io/dma.md](../../os/io/dma.md)).

**Signals.** The kernel-to-process version of the same push: SIGIO, SIGCHLD, SIGSEGV arrive asynchronously; the process registers a handler and the kernel interrupts a thread to run it at an arbitrary instruction boundary ([../../os/processes/ipc-signals.md](../../os/processes/ipc-signals.md)). The constraint list reads like a hardware datasheet: handlers must be *async-signal-safe* (no malloc, no locks, no stdio), because they can interrupt code that was mid-way through those operations. Signals are rarely used for I/O readiness (SIGIO lost to epoll for good reasons), but they are the cleanest demonstration that "interrupt a running computation and run a handler" is a general OS mechanism, not a device fact.

**Readiness APIs: select/poll/epoll/kqueue.** The C10K generation of servers replaced "one thread per blocking socket" with "register interest, wake when ready": epoll (Linux) and kqueue (BSD/macOS) maintain a kernel-side interest set and return only the ready subset, making the cost per wakeup O(ready) rather than O(total) ([../../network-programming/advanced-io.md](../../network-programming/advanced-io.md), [../../networks/sockets/io-multiplexing.md](../../networks/sockets/io-multiplexing.md)). This is the kernel pushing readiness to the process: the fd set with registered interest is the IRQ line, epoll_wait is the interrupt, and the process's event loop is the ISR. io_uring extends the same arc from *readiness* to *completion*: submit asynchronous operations, reap completions ([../../os/kernel/io-uring.md](../../os/kernel/io-uring.md)).

**Async runtimes: event loops and futures.** Userland copies the kernel's design. A single-threaded event loop calls epoll_wait, dispatches each ready fd to its callback, and loops. Async/await languages compile each future into a state machine; the runtime polls futures that the reactor marked ready ([../../concurrency/async-await.md](../../concurrency/async-await.md), [../../concurrency/futures.md](../../concurrency/futures.md), [../../languages/rust/async-runtimes.md](../../languages/rust/async-runtimes.md)). The correspondence is exact: the future's saved state is the ISR's saved context; the waker is the interrupt controller; `await` is "yield until the device (socket, timer, channel) raises your line." Runtime schedulers like Tokio's add work-stealing thread pools because some handlers are CPU-heavy — the userland re-invention of top-half/bottom-half.

## The Shared Principle

**Invert control from polling to push: register interest in an event, yield the resource (CPU, thread, stack), and be resumed by a notification when the event fires.** The polling alternative spends a scarce resource (a thread, a core) on waiting; the push design multiplexes thousands of waiters onto one dispatcher. Every layer implements the same three-part recipe: an *interest-registration* structure (driver ISR vector table, signal handler table, epoll interest set, future waker registry), a *resumption point* (saved context, signal frame, ready-callback, compiled state machine), and a *dispatch rule for ordering concurrent events* (IRQ priority, signal masking, edge/level semantics, readiness queue order).

The recipe's corollary is the shared engineering law: **handler cost is paid by everyone sharing the dispatcher.** A slow ISR delays other interrupts on that line/CPU; a slow signal handler delays the interrupted thread; a slow callback delays every connection on the event loop. Hence, at every layer, the same two-phase discipline: acknowledge and enqueue fast (top half), process later (bottom half). "Don't block the event loop" is not a Node.js quirk — it is the userland restatement of "don't disable interrupts" and "keep the ISR short."

## Where the Analogy HOLDS and BREAKS

| Property | HOLDS (interrupts → signals → epoll → event loops) | BREAKS |
|---|---|---|
| Push over poll | Register interest, get woken — all four layers | Under event storms every layer re-discovers polling: NAPI polls the NIC; busy event loops spin; batched syscalls (io_uring) trade wakeups for latency |
| Fast-handler discipline | Top/bottom half ≈ async-signal-safe ≈ don't block the loop | Hardware enforces brevity with silence (missed deadlines = dropped packets); the event loop enforces nothing — a slow handler is silently tolerated until users notice p99 |
| Priorities | IRQ priority levels; real-time signal ordering | General-purpose event loops have no priority scheme: one slow request causes head-of-line blocking for every request queued behind it — the problem hardware solved with NVIC priority levels is unsolved at the userland layer |
| Preemption | The CPU can always interrupt an ISR chain; the kernel can preempt threads | The runtime *cannot* preempt a running callback or a stuck future: scheduling is cooperative. An infinite loop in a handler is unkillable from inside the process — the "interrupt" is now the polite kind |
| Bounded queues | NIC ring buffers, IRQ affinity, and kernel queues are finite; overflow drops packets | Userland event loops happily grow unbounded queues of pending work unless the programmer adds bounds — see [./backpressure.md](./backpressure.md) for why that matters |
| Latency budget | ISR budgets are microseconds; miss them and hardware drops data | Event-loop budgets are p99s in milliseconds; the "budget" is an SLO, negotiated with users rather than wired into the controller |

The deepest break: **hardware interrupts can nest and preempt; event loops cannot.** The entire hardware design assumes the dispatcher can be interrupted at any point to handle something more urgent, and the code is written to be correct under that assumption (reentrancy, interrupt-safe structures). The entire userland design assumes the opposite — a callback runs to completion, alone, on its thread — which is why reentrancy bugs are rare there but head-of-line blocking is endemic, and why CPU-bound work must be shipped to a worker pool rather than handled inline.

## A Concrete Worked Example

**One blocked DB call freezes 1,000 connections. Trace the events.**

```text
t=0     Event loop dispatches callback for connection #1.
        Handler calls a SYNCHRONOUS database driver: db.query(sql) blocks.
        The single event-loop thread is now stopped inside the handler.
t=0+    Kernel still delivers readiness for connections #2..#1000:
        epoll_wait would return them — but nobody is calling epoll_wait.
        New SYNs complete in the kernel's accept queue; responses for #2..#1000
        sit in kernel socket buffers, unsent.
t=200ms db.query returns (typical query). Handler finishes. Loop resumes,
        drains the ready set: ~999 handlers run in ~µs each.
t=200ms Every one of the 999 interrupted connections has p99 >= 200 ms
        even though its own work took microseconds.
t=10s   If the query had taken 10 s instead: health checks time out, the load
        balancer pulls the process from rotation, TCP clients retry elsewhere,
        and the retry storm lands on the surviving processes.
```

The diagnosis writes itself in stack vocabulary: the *bottom half ran in the top half*. A 200 ms storage call is bottom-half work (defer it: async driver, worker thread, queue); it ran in the ISR slot, and the dispatcher's other 999 clients paid for it. The kernel-side mirror case is identical in shape: an ISR that grabs a spinlock and delays → soft lockup ("CPU#1 stuck for 23s"), watchdog reset. Fix at each layer: threaded IRQs and NAPI polling below; non-blocking drivers plus bounded worker pools above ([../../concurrency/thread-pools.md](../../concurrency/thread-pools.md)).

**The numbers that motivate the whole design.** With 10,000 open connections and 50 ready per wake cycle, `poll()`/`select()` scan all 10,000 descriptors per call while epoll returns 50: the readiness-push design turns an O(total) scan into an O(ready) dispatch — that gap is why the C10K problem was a cliff rather than a slope. The event-loop choice trades that scan for serialization: one thread, no locking, cache-hot state — and the 200 ms invoice above is the price of forgetting the trade's one rule.

## When This Connection Is Useful

- **Debugging latency incidents.** "All requests slow down together, CPU is not saturated, no DB saturation" is the signature of head-of-line blocking on a shared dispatcher. Knowing the interrupt analogy tells you where to look: what shares the loop/pool/queue with the slow operation, and what the top-half budget for a handler is on this layer.
- **Interview: "explain epoll and why Node is fast."** The senior-shaped answer is the stack, not the API: interrupts → kernel readiness push → userland event loop is one mechanism at three layers; epoll's O(ready) dispatch is the enabling primitive; the cost is cooperative scheduling, hence "don't block the loop," hence worker pools — at which point you can explain the design's failure mode before the interviewer asks.
- **Engineering decisions.** Classify every operation that runs on a dispatcher as top-half (µs: parse, route, enqueue) or bottom-half (ms: storage, network calls, crypto) and give bottom-half work a different queue with bounds. Never assume the runtime will preempt a stuck handler — it will not; design the process's watchdog externally. When event rates are high and uniform, revisit the poll-vs-push choice on purpose (busy-polling, adaptive interrupt coalescing, io_uring batching) rather than inheriting it.

## Interview Questions

1. Trace what happens between a NIC receiving a packet and the application reading the bytes, naming top-half/bottom-half work at each step — then map each step onto its Node.js event-loop equivalent.
2. Why does epoll scale to 10,000 sockets where `select()` does not? State the complexity difference precisely and the structure (interest set) that makes it possible.
3. A single handler performs a synchronous 200 ms DB call on an event loop serving 1,000 connections. Give the latency invoice for the other 999 connections, the kernel-side evidence you would see, and two fixes with different trade-offs.
4. "Don't block the event loop" is the userland version of which two kernel rules? Explain the mechanism-level reason all three exist.
5. Why can hardware interrupts preempt each other by priority while an async/await runtime cannot preempt a running future? What concurrency-safety property do userland handlers gain, and what liveness property do they lose?

## Key Takeaways

- Interrupts, signals, readiness APIs, and async runtimes are one mechanism — push-based dispatch over polling — implemented at four layers, each treating the layer below as its hardware.
- Every layer shares the three-part recipe: interest registration, resumption point, dispatch ordering — and the shared law that handler cost is paid by all co-tenants of the dispatcher.
- The top-half/bottom-half discipline (ISR brevity, async-signal-safety, "don't block the loop") is one rule wearing three uniforms: defer expensive work out of the dispatch path.
- Hardware preempts by priority; userland scheduling is cooperative: head-of-line blocking and unstoppable handlers are the userland's characteristic failures, bounded queues and worker pools its characteristic fixes.
- The poll-vs-push choice is a workload decision, not a dogma: NAPI, interrupt coalescing, and io_uring batching all exist because push loses under dense, uniform event storms.

## Cross-References

- [./backpressure.md](./backpressure.md) — Backpressure — what happens when the dispatcher's queues are unbounded.
- [./scheduling-queueing.md](./scheduling-queueing.md) — Scheduling and Queueing — queueing effects of head-of-line blocking.
- [../../os/io/interrupts.md](../../os/io/interrupts.md) — Interrupts — IRQ handling, top/bottom halves, and NAPI.
- [../../os/io/dma.md](../../os/io/dma.md) — DMA — why completion, not data transfer, needs the interrupt.
- [../../os/processes/ipc-signals.md](../../os/processes/ipc-signals.md) — Signals — the process-facing interrupt mechanism.
- [../../network-programming/advanced-io.md](../../network-programming/advanced-io.md) — Advanced I/O — select/poll/epoll/kqueue and nonblocking I/O.
- [../../networks/sockets/io-multiplexing.md](../../networks/sockets/io-multiplexing.md) — I/O Multiplexing — readiness APIs in the socket context.
- [../../os/kernel/io-uring.md](../../os/kernel/io-uring.md) — io_uring — completion-based async as the next step of the arc.
- [../../concurrency/async-await.md](../../concurrency/async-await.md) — Async/Await — state machines, wakers, and executors.
- [../../concurrency/futures.md](../../concurrency/futures.md) — Futures and Promises — continuation scheduling mechanics.
- [../../languages/rust/async-runtimes.md](../../languages/rust/async-runtimes.md) — Rust Async Runtimes — reactor/executor split in a real runtime.
- [../../concurrency/thread-pools.md](../../concurrency/thread-pools.md) — Thread Pools — sizing the bottom half.
- [../../os/threads/green-threads.md](../../os/threads/green-threads.md) — Green Threads — the preemptive-vs-cooperative contrast.
- Kegel, D., "The C10K Problem," <https://kegel.com/c10k.html>.
- man7.org, epoll(7) — <https://man7.org/linux/man-pages/man7/epoll.7.html>; signal(7) — <https://man7.org/linux/man-pages/man7/signal.7.html>.
