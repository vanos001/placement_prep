# Go Channels and `select` — Deep Dive

This page is the implementation view of Go channels: the `hchan` struct,
the send/receive fast paths (direct handoff), the buffered vs unbuffered
distinction, the `select` statement's scramble-and-lock algorithm, close
semantics, nil-channel blocking, `for-range`, and how the whole thing
compares to Rust's `mpsc`/`crossbeam-channel`. The sibling page
[channels](./channels.md) is the API tour; [concurrency-deep](./concurrency-deep.md)
is the scheduler view; this is the `runtime/chan.go` view.

## 1. The `hchan` struct

Every `chan T` value the program hands around is a pointer to a `hchan`
struct allocated on the heap by `makechan`. The struct lives in
[`runtime/chan.go`][chan-go] and looks (slightly simplified) like:

```go
type hchan struct {
    qcount   uint           // # elements currently in buf
    dataqsiz uint           // size of the ring buffer
    buf      unsafe.Pointer // pointer to a [dataqsiz]elemsize array
    elemsize uint16         // sizeof(T)
    closed   uint32         // 1 if close(ch) was called
    elemtype *_type         // element type descriptor (for memmove + GC)
    sendx    uint           // next send index in buf
    recvx    uint           // next recv index in buf
    recvq    waitq          // FIFO list of pending receivers (sudog)
    sendq    waitq          // FIFO list of pending senders (sudog)
    lock     mutex          // protects all the above
}

type waitq struct {
    first *sudog
    last  *sudog
}
```

Three regions of state live inside `hchan`:

```
                 ┌───────────────────────────────────────────┐
                 │ hchan                                      │
                 │                                            │
                 │  ┌──────────────────────────────────────┐ │
                 │  │ buf  (ring array, dataqsiz slots)     │ │
                 │  │ ┌──┬──┬──┬──┬──┬──┬──┬──┐              │ │
                 │  │ │  │  │  │  │  │  │  │  │  qcount = 3 │ │
                 │  │ └──┴──┴──┴──┴──┴──┴──┴──┘              │ │
                 │  │   ▲ recvx                sendx ▲        │ │
                 │  └──────────────────────────────────────┘ │
                 │                                            │
                 │  recvq: [sudog]→[sudog]→[sudog]→nil       │
                 │  sendq: [sudog]→nil                       │
                 │  lock : mutex                             │
                 └───────────────────────────────────────────┘
```

The `sudog` ("sync-user wait-group descriptor") is the per-goroutine
node used by the runtime to enqueue a `G` on a synchronization
primitive. It carries a pointer to the `G`, a data pointer for direct
handoff, and a `releasetime` for the scheduler's tracing.

## 2. Send and Receive — Fast Paths and Slow Paths

### 2.1 Send (`chansend`)

The send logic (`chansend1` → `chansend`) has three exit ramps:

```go
// pseudocode from runtime/chan.go
func chansend(c *hchan, ep unsafe.Pointer, block bool) bool {
    lock(&c.lock)
    if c.closed != 0 {
        unlock(&c.lock)
        panic("send on closed channel")
    }
    // FAST PATH 1: a receiver is waiting in recvq
    if sg := c.recvq.dequeue(); sg != nil {
        sendDirect(c.elemtype, sg, ep)  // copy ep → sg's stack slot
        goready(sg.g)                   // mark receiver runnable
        unlock(&c.lock)
        return true
    }
    // FAST PATH 2: the buffer has space
    if c.qcount < c.dataqsiz {
        qp := chanbuf(c, c.sendx)
        typedmemmove(c.elemtype, qp, ep)  // memcpy into buf
        c.sendx = (c.sendx + 1) % c.dataqsiz
        c.qcount++
        unlock(&c.lock)
        return true
    }
    // SLOW PATH: park this G on sendq
    gp := getg()
    sg := acquireSudog()
    sg.elem = ep                          // remember where the value lives
    c.sendq.enqueue(sg)
    gopark(commitChanSend, c, waitReasonChanSend, ...)
    // -- G is suspended here; resumed by a future recv --
    return true
}
```

**Direct handoff** (fast path 1) is the heart of the design: when a
sender meets a waiting receiver, the value is `memcpy`'d *directly from
the sender's stack to the receiver's stack* — no buffer is touched, no
copy is queued. This is why an unbuffered channel has near-zero overhead
beyond the mutex: the `buf` field is `nil`, and every successful send is
a direct handoff. This is also why the Go FAQ calls unbuffered channels
"synchronous" — the *receive completes the send*.

### 2.2 Receive (`chanrecv`)

Symmetric three-exit-ramp structure:

```go
func chanrecv(c *hchan, ep unsafe.Pointer, block bool) (selected, received bool) {
    lock(&c.lock)
    // FAST PATH 1: a sender is waiting AND buffer is empty
    //              (i.e., unbuffered or fully drained)
    if c.qcount == 0 && c.sendq.first != nil {
        sg := c.sendq.dequeue()
        recvDirect(c.elemtype, sg, ep)   // copy from sender's slot → ep
        goready(sg.g)
        unlock(&c.lock)
        return true, true
    }
    // FAST PATH 2: buffer has data
    if c.qcount > 0 {
        qp := chanbuf(c, c.recvx)
        typedmemmove(c.elemtype, ep, qp)
        c.recvx = (c.recvx + 1) % c.dataqsiz
        c.qcount--
        // If a sender is waiting (because buffer was full), pull its
        // value into the freed slot and wake the sender.
        if c.sendq.first != nil {
            sg := c.sendq.dequeue()
            entercgwait_m(gp, sg, c)
        }
        unlock(&c.lock)
        return true, true
    }
    // FAST PATH 3: channel closed AND empty
    if c.closed != 0 {
        unlock(&c.lock)
        if ep != nil { typedmemclr(c.elemtype, ep) }  // zero value
        return true, false                            // ok = false
    }
    // SLOW PATH: park on recvq
    ...
}
```

The asymmetry to send: receive has *four* exits (direct handoff,
buffered read, closed-drained, and slow-path). The "closed-drained"
case is what makes `v, ok := <-ch` work — `ok` is `received` from the
last branch above.

### 2.3 Direct handoff on a *buffered* channel

A subtle case: a buffered channel of capacity N, full with N items, has
senders parked on `sendq`. When a receiver drains one slot from the
buffer, the runtime immediately copies the head sender's value into the
freed slot and wakes the sender. From the receiver's view, it got an
older buffered value; from the sender's view, its send completed without
parking again. This is what makes `sendq` non-empty on a buffered channel
**not** equivalent to "buffer overflow" — it means the buffer is exactly
full and senders are queued.

## 3. Buffered vs Unbuffered

| Property | `make(chan T)` (cap 0) | `make(chan T, N)` (cap N>0) |
|----------|------------------------|------------------------------|
| `dataqsiz` | 0 | N |
| `buf` pointer | `nil` | non-nil heap array |
| Send completes when… | a receiver is parked (direct handoff) | buffer has space |
| Receive completes when… | a sender is parked (direct handoff) | buffer has data |
| `cap()` returns | 0 | N |
| Initial sender of an unbuffered send | Blocks until receiver appears | Inserts into buf |

The Go memory model establishes happens-before edges around both:

- **Unbuffered:** a receive *happens-before* the corresponding send *completes*.
  Equivalently, "the send completes only because of the receive."
- **Buffered:** the *Nth send completes happens-before the (N-cap)th receive*
  — i.e., the buffer's overflow boundary, not each individual send.

This asymmetry is what makes unbuffered channels the synchronization
primitive of choice for "wait until the other side is ready" — the
knight's-move handshake. Buffered channels are a *decoupling* primitive,
not a synchronization one.

## 4. The `select` Statement

`select` has the syntax of a `switch` over channel operations, but the
runtime semantics are quite different. The compiler lowers
`select { case <-a: ...; case b <- x: ...; default: ... }` into a call
to [`runtime.selectgo`][chan-go] with an array of `scase` structs:

```go
type scase struct {
    c        *hchan   // the channel
    elem     unsafe.Pointer  // for send: the value ptr; for recv: the dest
    kind     uint16   // CaseRecv | CaseSend | CaseDefault
}
```

### 4.1 The algorithm — scramble + lock all

The implementation (simplified) is:

```go
func selectgo(cas0 []scase, ...) (int, bool) {
    // 1. Build list of non-nil cases.
    // 2. SCRAMBLE: produce a uniform random permutation of case indices.
    //    (This is why "multiple ready cases → pick uniformly at random" holds.)
    //
    // 3. PASS 1 — try the fast non-blocking path on each case in scramble order:
    //    for each case in perm {
    //        lock(case.c)
    //        if case fits without blocking (send fits buf / recv gets buf or closed) {
    //            do the op; unlock(case.c); return case.index
    //        }
    //        unlock(case.c)
    //    }
    //
    // 4. PASS 2 — if there's a default case, take it.
    //
    // 5. SLOW PATH — enqueue this G on every channel's wait queue, then gopark.
    //
    // 6. RESUME — exactly one sudog got dequeued by another G.
    //    For all OTHER cases, dequeue this G's sudog and release.
    //    return the index of the case that fired.
}
```

Three observations:

- **Scramble first.** The random permutation is computed *before* any
  lock is taken, so the choice is fair even if some channels are
  permanently hot. The cost is `O(n log n)` per select.
- **Lock-each-channel-once.** Each case lock is taken individually
  during the fast-path scan. A select does not atomically lock all
  channels — there is a window where the select holds lock A and
  another select holds lock B. The Go runtime avoids deadlock by
  releasing locks before sleeping (no two held simultaneously at
  slow-path entry).
- **Single-wakeup invariant.** When a `select` is parked on N
  channels, exactly one of them will dequeue it. The runtime checks
  each `sudog`'s state on wake: if already selected by another case,
  the others are rolled back. This is the trick that makes
  `for { select { case <-a: ... case <-b: ... } }` fair and
  deadlock-free.

### 4.2 `case` ordering is *not* preserved

Go's spec says "if multiple cases can proceed, one is chosen uniformly at
random." Implementation reality: the scramble pass randomizes the scan
order, so even with two always-ready cases the selection is uniform.
This is *unlike* a `switch` statement where the first matching case wins.
A `switch`-like `select` is impossible to write without explicit ordering
state, because the language *forbids* it — this is a deliberate
anti-starvation design.

### 4.3 The `default` case

`default` converts `select` from blocking to non-blocking. The compiler
treats `default` as a `CaseDefault` entry that, if no fast-path case
fires in pass 1, immediately fires in pass 2 — the slow path (parking)
is never reached. This is why `select { case ch <- v: ...; default: }`
is the idiomatic "try to send without blocking" — it is cheap (one
mutex acquisition) and never parks.

## 5. Close Semantics

`close(ch)` (`closechan` in [chan.go][chan-go]):

1. Acquires `c.lock`. Sets `c.closed = 1`.
2. Walks `recvq` and `sendq`, dequeues every `sudog`, marks each with
   `closed = true`, and `goready`s each waiting `G` (in bulk — one
   scheduler call for all of them).
3. Releases `c.lock`.

Then the runtime returns to the woken `G`s, each of which sees the
closed flag in its `sudog` and:

- A waiting **receiver** returns `(zero-value, ok=false)`.
- A waiting **sender** panics (`send on closed channel`).

So `close(ch)` is *safe for receivers* (they wake up and drain) but
*panics the senders* waiting in `sendq`. This asymmetry is why closing
channels in Go is such a foot-gun: the rule of thumb is "the *producer*
closes the channel; consumers never close it" — exactly because
consumers cannot know whether some other producer is about to send.

## 6. Nil Channels

A nil channel is the zero value of `chan T`. It is *not* a no-op: it
blocks forever on every operation except `len` and `cap`, which return 0.

```go
var ch chan int          // nil
ch <- 1                  // blocks forever
v := <-ch                // blocks forever
close(ch)                // panics: close of nil channel
```

This sounds like a bug; it is a feature. A nil case in `select` is
*never selected*, which makes nil-channel injection a way to disable a
case dynamically:

```go
var incoming <-chan int = originalIncoming
for {
    select {
    case v, ok := <-incoming:
        if !ok { incoming = nil }  // disable this case permanently
    case <-done:
        return
    }
}
```

Once `incoming` becomes nil, the case is structurally skipped by
`selectgo`'s pass 1 (the fast path tests `case.c == nil` and continues),
and never blocks on the slow path either. This is the Go idiom for
"phase out a stage of a pipeline."

## 7. `for range` over a Channel

The compiler lowers:

```go
for v := range ch {
    body(v)
}
```

to roughly:

```go
for {
    v, ok := <-ch
    if !ok { break }
    body(v)
}
```

The range form is identical in performance to the explicit loop — it is
syntactic sugar. It terminates only when the channel is closed *and*
drained. A never-closed channel leaks the goroutine (common bug). The
[Go memory model][mem-model] guarantees that `close(ch)` is
*happens-before* the `range` termination: another goroutine's close is
observed without an explicit barrier.

## 8. Comparison with Rust's `mpsc` and `crossbeam-channel`

| Property | Go channels | Rust `std::sync::mpsc` | Rust `crossbeam-channel` |
|----------|-------------|------------------------|---------------------------|
| Language support | Built-in (`chan T`) | Library type, syntax sugar | Library type, no syntax sugar |
| Sender multiplicity | Multiple (no distinction) | `Sender` is `Clone` (mpsc) | `Sender` is `Clone` |
| Receiver multiplicity | Multiple | Single (`Receiver`) — mpsc | Single (multi-receiver is separate API) |
| Bounded | `make(chan T, N)` | `sync_channel(N)` | `bounded(N)` |
| Direct handoff | Yes (recv-waiting-sender path) | Yes (under the hood) | Yes (`bounded` uses LIFO buffer + direct handoff) |
| Select | Language: `select { case ... }` | Library: `crossbeam_channel::select!` macro | Same |
| Closing | Built-in `close` | `Sender` drop closes | `Sender` drop closes |
| Send on closed | Panic | Compile-time impossible (Rust's ownership: only the last `Sender` matters; dropping it closes) | Same |
| Backpressure | `chan` blocks when full | Bounded channels block; unbounded never block | Same |
| Allocation | Per `chan` (heap `hchan`) | Per channel (heap or stack if zero-sized) | Per channel (specialized allocator) |
| Zero-cost abstraction | No — runtime involvement per op | Yes for `unbounded` (list-based, lock-free) | Yes for `at` and bounded |

Three structural differences:

1. **Type-enforced SPSC in Rust's `mpsc`.** Rust's `Receiver` is *not*
   `Clone`, so the compiler rejects reading the same channel from two
   threads. Go channels have no equivalent type-level guarantee — multiple
   goroutines reading one channel is fine, but the programmer must arrange
   exclusive ownership manually. Rust mpsc is faster (no multi-consumer
   coordination); Go channels are more flexible.
2. **Closing is type-enforced in Rust, runtime-enforced in Go.** Rust's
   `Sender::drop` closes the channel when the last sender drops; receivers
   get `None`. Go's `close(ch)` is a runtime call anyone can make — double
   or premature close panics. The Go producer-closes convention is a
   workaround for the absence of RAII.
3. **`select` ergonomics.** Go's `select` is a first-class statement with
   random selection and single-wakeup invariants baked into the runtime.
   Rust's `select!` macro from `crossbeam` provides the same semantics via
   `Option<T>` returns per case — more expressiveness at the cost of more
   syntax.

The performance story: a hot-path Go send/recv pair runs in ~50–100 ns
(mutex + ring-buffer memmove). Rust's `crossbeam-channel` bounded runs in
~20–40 ns (lock-free with slot stealing); `std::sync::mpsc::unbounded` is
~10 ns, using a Michael-Scott queue with no contention. The Go tax is
the per-channel mutex — necessary because channels are *shared* by
default; Rust types are designed around ownership and elide the lock.

## References

- [Go source — `runtime/chan.go`][chan-go]
- [Go memory model][mem-model]
- [Go channel design — Dmitry Vyukov "Scheduler Scenarios" doc][vyukov]
- [*Concurrency in Go* — Katherine Cox-Buday, O'Reilly 2017](https://www.oreilly.com/library/view/concurrency-in-go/9781491941296/)
- [Go source — `runtime/select.go` (`selectgo`)](https://github.com/golang/go/blob/master/src/runtime/select.go)
- [Dave Cheney — "Channel Axioms"](https://dave.cheney.net/2014/03/19/channel-axioms)
- [Bryan C. Mills — "Rethinking the Go Channel"](https://github.com/golang/go/issues/40373) (long discussion of `select` semantics)

[chan-go]: https://github.com/golang/go/blob/master/src/runtime/chan.go
[mem-model]: https://go.dev/ref/mem
[vyukov]: https://docs.google.com/document/d/1VT43Je5CsDVNQ8yy9N-e275fu5NKeu5wXOTwB6w0Xk8/edit
