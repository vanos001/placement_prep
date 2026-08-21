# Go Concurrency Deep Dive — Scheduler, Channels, Memory Model

## Overview

Go's concurrency model is the most production-tested of any mainstream
language: it has shipped in every Go binary since Go 1.0 (2012) and powers
the entire Go ecosystem, from Docker and Kubernetes to the database
internals of CockroachDB and TiKV. Three layers compose it:

1. **The GMP scheduler** — an M:N scheduler multiplexing goroutines onto OS
   threads, with per-P local run queues and work stealing.
2. **Channels** — `chan` is a built-in type implemented by the runtime's
   `hchan` struct, with a ring buffer and a `sudog` wait queue.
3. **The memory model** — a happens-before relation defined over channel
   sends and receives, `sync.Mutex`, `sync/atomic`, and `sync.WaitGroup`.

This page covers the scheduler internals, the `hchan` struct, the `select`
statement, the Go memory model, and how Go compares with Kotlin, Swift, and
Rust concurrency.

## 1. The GMP Scheduler

### G, M, P

| Symbol | What it is | Lifetime |
|--------|-----------|----------|
| **G** (Goroutine) | The user-level "thread of control"; a `g` struct holding stack pointer, instruction pointer, and a run state | Created by `go f()`; dies when `f` returns |
| **M** (Machine) | An OS thread; an `m` struct wrapping `pthread_create` | Created by the runtime as needed; capped at 10,000 by default (`runtime/debug.SetMaxThreads`) |
| **P** (Processor) | A logical CPU that holds scheduling context — the per-P local run queue, deferred funcs, the heap cache, and a free-list of `g` structs | Count = `GOMAXPROCS` (default: `runtime.NumCPU`) |

```
       ┌─────────────────────────────────────────────────────────┐
       │                  Go runtime scheduler                  │
       │                                                         │
       │  ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐               │
       │  │ P0  │    │ P1  │    │ P2  │    │ P3  │    (P = CPU)  │
       │  │     │    │     │    │     │    │     │               │
       │  │ LQ: │    │ LQ: │    │ LQ: │    │ LQ: │  (256 each)   │
       │  │ G G │    │ G G │    │ G G │    │ G G │               │
       │  │  G G│    │  G G│    │  G G│    │  G G│               │
       │  └──┬──┘    └──┬──┘    └──┬──┘    └──┬──┘               │
       │     │          │          │          │                  │
       │     ▼          ▼          ▼          ▼                  │
       │  ┌────┐     ┌────┐     ┌────┐     ┌────┐               │
       │  │ M0 │     │ M1 │     │ M2 │     │ M3 │   (M = thread)│
       │  └────┘     └────┘     └────┘     └────┘               │
       └─────┬────────┬─────────────┬───────────┬───────────────┘
             │        │             │           │
             ▼        ▼             ▼           ▼
       ┌──────────────────────────────────────────┐
       │      Global run queue (GRQ)               │
       │      [G] [G] [G] [G] [G] [G]  ...         │
       └──────────────────────────────────────────┘
                          │
                          ▼
       ┌──────────────────────────────────────────┐
       │    Network poller (epoll/kqueue/IOCP)    │
       │      (a separate M, off-GOMAXPROCS)      │
       └──────────────────────────────────────────┘
```

### The scheduling loop

Every M that has a P runs `runtime.schedule` repeatedly. The pseudocode is:

```go
func schedule() {
    // 1. Run a goroutine from a preemption request, if any.
    // 2. Try local run queue (FIFO head, ~60% of the time).
    // 3. Every 61 ticks, try the global run queue (fairness across P's).
    // 4. Try the netpoller (non-blocking): any ready G's?
    // 5. Try stealing half from another P's local queue.
    // 6. Block on netpoller with a timeout; if anything arrives, run it.
    // 7. If all else fails, M gives up its P and parks.
    gp := findRunnable()
    execute(gp)
}
```

Note item 3 — the global queue is checked **every 61 ticks**. This prevents
starvation: without it, a P with a hot local queue would never look at the
global queue and goroutines spawned on a long-idle P would starve.

### Work stealing

When `P0`'s local queue is empty, `P0` calls `stealWork`, which picks a
random `P` and steals **half** of its runnables. Stealing half (rather than
one) amortizes the cost of the lock-protected steal and ensures the stealee
still has work.

The local run queue is a **bounded, lock-free ring of 256 `g` pointers**
implemented with a `guintptr` array and double-buffered indices. The
`runnext` slot is a special slot for the goroutine that was just made
runnable *by the running goroutine itself* (e.g., `go f()` immediately
followed by `f()` being needed). `runnext` is always run before the queue,
capturing producer-consumer locality — much like the LIFO side of a
chase-lev deque.

### Network poller

The network poller is a *separate* M, off-GOMAXPROCS, dedicated to calling
`epoll_wait`/`kevent`/`GetQueuedCompletionStatus`. When a goroutine does a
non-blocking socket read, the runtime parks it and registers the FD with the
poller. When `epoll_wait` returns readiness, the poller M wakes the relevant
goroutine by injecting it into some P's local run queue.

Without the poller, a goroutine reading from a socket would have to spin
or block an OS thread — neither acceptable. The poller is what makes
"goroutines that wait on I/O" essentially free.

### Syscall hand-off

A blocking syscall (`read` on a file, `cgo`) blocks its M. The runtime
handles this by **hand-off**: when an M enters a syscall, the runtime detects
that the M is no longer usable and hands its P off to another (or fresh) M.
The original M stays in the syscall until it returns; the P stays scheduled.

This is the asymmetry: **network I/O is poller-driven (no M held)**;
**file I/O and cgo are syscall-driven (M held, P handed off)**.

### Goroutine stacks

Each `g` starts with a 2 KB stack. When it overflows, the runtime calls
`runtime.newstack`, which allocates a larger stack, copies the old contents
over (fixing up interior pointers), and resumes. Stacks can grow to 1 GB
by default (`runtime/debug.SetMaxStack` adjusts this).

This growable stack is what makes `go f()` cheap: 2 KB at start, and the
runtime pays for growth only if the goroutine actually recurses deeply.

## 2. Channel Internals — `hchan`

A channel value is a `*hchan` (a pointer to a `runtime.hchan` struct on the
heap). The struct (abridged from `runtime/chan.go`):

```go
type hchan struct {
    qcount   uint           // number of elements in the buffer
    dataqsiz uint           // size of the ring buffer
    buf      unsafe.Pointer // pointer to the ring buffer
    elemsize uint16
    closed   uint32
    elemtype *_type
    sendx    uint           // send index in buf
    recvx    uint           // receive index in buf
    recvq    waitq          // list of recv waiters
    sendq    waitq          // list of send waiters
    lock     mutex          // protects the whole struct
}

type waitq struct {
    first *sudog
    last  *sudog
}
```

A `sudog` ("pseudo-goroutine") is a node in a wait queue that represents a
goroutine blocked on a channel operation, plus the value it's sending or
where to receive into:

```go
type sudog struct {
    g          *g           // the goroutine waiting
    elem       unsafe.Pointer // data element (may point into g's stack)
    next, prev *sudog       // doubly-linked list in waitq
    acquiretime int64
    releasetime int64
    ticket     uint32       // for select
    isSelect   bool
    // ... more fields
}
```

### The ring buffer

For a buffered channel `make(chan int, 4)`, the runtime allocates a 4-slot
ring. `sendx` and `recvx` are indices into the ring; `qcount` is the current
count.

```
sendx=2, recvx=0, qcount=2

buf: [ . . . . ]    index: 0  1  2  3
              ^sendx           ^recvx (well, recvx wraps)
```

Wait — actually the convention is: `recvx` is the next slot to read from,
`sendx` is the next slot to write to. With `dataqsiz=4`, after two sends
(`sendx` advances to 2, `qcount=2`), the ring has data at slots 0 and 1.
After a receive, `recvx` advances to 1 and `qcount` becomes 1.

### Send path

`runtime.chansend1(c, ep)` is the implementation of `c <- v`. In pseudocode:

```go
func chansend(c *hchan, ep unsafe.Pointer, block bool) bool {
    lock(&c.lock)
    if c.closed != 0 {
        unlock(&c.lock)
        panic("send on closed channel")
    }
    // 1. Is there a waiting receiver? Hand the value directly.
    if sg := recvq.dequeue(); sg != nil {
        memmove(sg.elem, ep, c.elemsize)
        goready(sg.g)         // mark receiver runnable
        unlock(&c.lock)
        return true
    }
    // 2. Is there buffer space? Put the value in the ring.
    if c.qcount < c.dataqsiz {
        qp := chanbuf(c, c.sendx)
        memmove(qp, ep, c.elemsize)
        c.sendx = (c.sendx + 1) % c.dataqsiz
        c.qcount++
        unlock(&c.lock)
        return true
    }
    // 3. Otherwise, enqueue self as a sender sudog and park.
    gp := getg()
    sg := acquireSudog()
    sg.g = gp
    sg.elem = ep
    c.sendq.enqueue(sg)
    gopark(...)               // suspend; unlock is done by gopark
    // resumes when someone receives
    return true
}
```

Notice step 1 — a direct hand-off. If a receiver is parked, the value
**never enters the buffer**. This is the "synchronous" feel of unbuffered
channels: the receiver gets the value directly from the sender's stack via
`memmove`.

### Receive path

`runtime.chanrecv` mirrors `chansend`:

1. If the channel is closed and the buffer is empty, return the zero value.
2. If a sender is parked (only possible for full buffered or unbuffered
   channels), take the value from the head of the buffer or directly from
   the sender, mark the sender runnable.
3. Else if the buffer has data, take from `recvx`.
4. Else enqueue self as a receiver sudog and park.

### Close

`close(c)` runs through both `recvq` and `sendq`, marking each waiting
goroutine runnable. Senders that were parked will panic when they wake —
"send on closed channel" is checked at resume time, not at send.

## 3. The `select` Statement

A `select` with N cases is implemented by `runtime.selectgo`. The mechanics:

1. **Scramble the case order.** A pseudo-random permutation is applied so
   that no case is consistently preferred — this is the language-level rule
   that `select` "picks a random ready case".
2. **Lock all the channels** in the permuted order (this is the "scramble +
   lock" phrase). Acquiring locks in a consistent order prevents deadlock
   when two `select`s lock the same channels.
3. **Try each case** in permuted order:
   - For a send case: try direct hand-off to a parked receiver, then try
     buffer space.
   - For a recv case: try direct hand-off from a parked sender, then try
     buffer, then closed-state.
4. If no case is ready, **enqueue self on every channel's wait queue** as
   a `sudog` with `isSelect=true`, unlock all locks, and park.
5. When any channel becomes ready, the runtime **dequeues the goroutine from
   every other channel's wait queue** (using the doubly-linked-list pointers
   in `sudog`) and resumes it. The case that fired is the one whose value
   is consumed.

The `ticket` field on `sudog` is a small accounting token used to make sure
that when two channels become ready simultaneously, only one's value is
consumed and the other is left for the next waiter.

The `default` case short-circuits step 4 — if no case is ready and a
`default` exists, that case fires immediately. This is what makes
`select { case x := <-c: ... default: ... }` a non-blocking receive.

## 4. The Go Memory Model

The Go memory model is a happens-before relation over memory operations. It
is defined at https://go.dev/ref/mem and is the **specification** the runtime
and compiler promise not to violate.

### The two rules

1. A read `r` may observe the value of a write `w` if `r` does not happen
   before `w` and there is no other write `w'` such that `w` happens before
   `w'` and `w'` happens before `r`.
2. To synchronise, you need an explicit happens-before edge.

In the absence of an explicit edge, reads and writes on different goroutines
are unrelated, and you may observe any prior value, including the initial
zero value.

### Channel synchronization edges

| Operation | Happens-before |
|-----------|----------------|
| `c <- v` (send) | happens-before the corresponding `v := <-c` (receive) that consumes the value |
| `close(c)` | happens-before a receive that returns the zero value due to the close |
| `v := <-c` (unbuffered receive) | happens-before the send that fills it (so the receive of an unbuffered channel synchronizes with the send) |
| The `k`-th send on a buffered channel of capacity `N` | happens-before the `(k+N)`-th receive from that channel |

So:

```go
var done = make(chan struct{})
var data int

go func() {
    data = compute()       // (a)
    done <- struct{}{}     // (b)
}()

<-done                     // (c)
fmt.Println(data)          // (d)
```

Here, `(a) happens-before (b) happens-before (c) happens-before (d)`, so
the `Println` sees the assigned `data`. Without the channel, you'd have a
data race — Go's `race detector` would flag it.

### `sync.Mutex` and `sync.RWMutex`

For `sync.Mutex`, the `k`-th call to `Unlock` happens-before the `(k+1)`-th
call to `Lock`. For `sync.RWMutex`, the `Unlock` of a write lock
happens-before the next `Lock` of any kind; an `RLock` happens-before the
next `Lock` (the constraint that lets readers observe a writer's release).

### `sync/atomic` and `sync.Once`

`sync/atomic` operations (`atomic.Load`, `atomic.Store`, `atomic.Add`,
`atomic.CompareAndSwap`, `LoadPointer`/`StorePointer` etc.) provide
sequentially-consistent semantics for the typed atomic operations.

`sync.Once.Do(f)` has the guarantee that the return of `Do` happens-before
the return of any other `Do` call. This is how `sync.Once` makes initialization
races impossible: a `Do(f)` either runs `f` itself or waits for the `f`-runner
to finish, and the happens-before edge ensures every observer sees `f`'s
writes.

### Race detector

`go test -race` instruments every memory access and every synchronization
operation, then runs the program under the **Thread Sanitizer** algorithm
to detect actual races observed during the run. It catches the
"un-synchronized concurrent read+write" pattern that the type system does
not forbid (Go's channels are a convention, not a type-system rule, unlike
Swift's actors).

## 5. Comparison with Kotlin, Swift, and Rust

| Aspect | Go | Kotlin | Swift | Rust |
|--------|----|--------|-------|------|
| Concurrency unit | goroutine (runtime) | coroutine (library on JVM) | Task (compiler + stdlib) | Future (compiler + library) |
| Scheduler location | Runtime (built into every Go binary) | `Dispatchers.Default` (JVM `ForkJoinPool`) | Cooperative pool (stdlib) | Tokio/async-std (library) |
| Stack model | Growable 2 KB stack | Continuation object + JVM stack | Continuation struct | State machine struct |
| Cancellation | `context.Done()` channel | `Job.cancel()` flag | `Task.cancel()` flag | `drop` the future |
| Data isolation | Channels (idiom, not enforced) | `Mutex`/`Channel` (manual) | `actor` (compiler-enforced) | `Send` (type system) |
| Static data-race safety | `-race` (runtime) | None | `Sendable` (compile-time) | `Send` (compile-time) |
| Memory model | Documented in https://go.dev/ref/mem | JMM (JVM) | C11 atomics subset | Rust memory model + `Send`/`Sync` |
| Channels | First-class (`chan`) | `kotlinx.coroutines.channels.Channel` | `AsyncStream`/`AsyncChannel` | `tokio::sync::mpsc` |
| Preemption | Async (Go 1.14+, signals at function prologue) | Cooperative (must hit suspend) | Priority-based (SE-0307) | Cooperative (must return `Pending`) |

### What Go shares with the others

All four have **cooperative scheduling at the language level** — the unit
of execution has explicit suspension points and the runtime is free to
switch to another unit between them. Go just adds **asynchronous preemption**
so that a goroutine in a tight `for {}` loop can still be descheduled.

### What is unique to Go

Go is the only one where the scheduler is **inseparable from the runtime**.
Every Go binary contains `runtime/proc.go`, `runtime/chan.go`, and
`runtime/netpoll_*.go`. You cannot choose a different scheduler; you cannot
swap the channel implementation. The trade-off is **uniformity**: every Go
program, regardless of who wrote it, behaves the same way under
concurrency, and tooling (`go test -race`, `pprof`, `runtime/trace`)
works on all of them.

Kotlin and Rust deliberately make the runtime pluggable — you can run
Kotlin coroutines on `Dispatchers.Unconfined` and Rust futures without any
executor at all. Swift sits in between: the cooperative pool is part of the
stdlib, but you can swap the executor with a global actor.

### What is unique to Swift and Rust (vs Go)

**Compile-time data-race safety.** Go has no way to forbid `var x int` being
mutated by two goroutines concurrently — you find out with `-race` at best,
silent corruption at worst. Swift's `actor` and Rust's `Sync`/`Send` make
the equivalent forbidden by the type checker. This is the single biggest
semantic gap between Go and the newer languages.

## 6. Pitfalls

1. **`GOMAXPROCS` is per-process, not per-container.** A Go binary in a
   container with CPU limits sees the host's CPU count and over-spawns P's.
   Set `GOMAXPROCS` from `runtime.NumCPU` or use `automaxprocs` library in
   Kubernetes.
2. **Channel close must come from the sender.** Closing from a receiver is
   a panic. Multiple senders need a coordinator channel ("nested-close"
   pattern).
3. **`select { case ... default: }` is a busy loop if misused.** A
   non-blocking select inside a `for` will spin; always add a `time.After`
   or a quit channel.
4. **`sync.Mutex` is not reentrant.** A goroutine that locks twice will
   deadlock. Go has no reentrant mutex in the standard library.
5. **Memory model surprises.** Reads and writes on different goroutines
   without synchronization are races even if you "feel" they shouldn't be.
   The race detector is your friend; run it in CI.

## References

- The Go Memory Model (official spec)
  https://go.dev/ref/mem
- Dmitry Vyukov, "Design document for Go's scheduler (NUMA-aware, work-stealing)"
  https://docs.google.com/document/d/1TTj4T-XJ7Tpg8U11vDpaxlzx7HOoF5VQQYsG2ixgyZ4/edit
- Dmitry Vyukov, "Scalable Go Scheduler Design Doc" presentation (Go 1.1 scheduler)
  https://golang.org/s/go11sched
- Go runtime source: `runtime/proc.go`, `runtime/chan.go`, `runtime/select.go`
  https://github.com/golang/go/tree/master/src/runtime
- Ardan Labs, "Scheduling In Go" series (William Kennedy)
  https://www.ardanlabs.com/blog/2018/08/scheduling-in-go-part1.html
- "Why does Go scheduler use a 256-element local run queue?"
  https://groups.google.com/g/golang-dev/c/VOI52yP3xt0
- `runtime.GOMAXPROCS`, `runtime/debug.SetMaxThreads`, `runtime/debug.SetGCPercent`
  https://pkg.go.dev/runtime
- Go data race detector documentation
  https://go.dev/doc/articles/race_detector
- Effective Go — "Share memory by communicating"
  https://go.dev/doc/effective_go#sharing
- "Blogging From the Go Runtime" (Dmitry Vyukov, async preemption in Go 1.14)
  https://go.dev/blog/
