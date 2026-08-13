# Memory Models — C++, Java, Go, Rust

## Overview

Hardware reorders memory accesses, compiler reorders too. **Memory model** defines what reorderings are allowed and what synchronization ensures visibility across threads. All modern languages guarantee **DRF-SC**: data-race-free programs behave as if sequentially consistent (interleaved without reordering). Understanding acquire/release, seq_cst, happens-before is essential for lock-free interviews and for avoiding subtle bugs.

> Related: [Lock-free](./lock-free.md), [RCU](./rcu.md), [Memory Barriers](../os/synchronization/memory-barriers.md), [Go Memory Model](../languages/go/memory-model.md), [C++ Memory Model](../languages/cpp/memory-model.md), [Java Memory Model](../languages/java/jvm.md)

## Hardware Reality

| Arch | Store-Load reorder? | Store-Store? | Load-Load? | Notes |
|------|---------------------|--------------|------------|-------|
| x86_64 | Yes (store remains in store buffer) | No | No | TSO — relatively strong |
| ARMv8 | Yes | Yes | Yes | Weak, needs explicit barriers |
| RISC-V | Yes | Yes | Yes | Weak, needs fences |
| POWER | Yes | Yes | Yes | Very weak |

Even x86 (TSO) allows later loads to be reordered before earlier stores — classic store buffering.

### Store Buffering Litmus

```c
// Initially x=y=0
// Thread1: x=1; r1=y;
// Thread2: y=1; r2=x;
// Can r1=0 && r2=0? On x86 YES (store buffer), on SC NO
```

## DRF-SC & Happens-Before

**Data race**: concurrent access to same non-atomic location, at least one write, no synchronization.

- If program has data race → **undefined behavior** in C++/Rust, may show weird values (Go may crash, Java may show non-SC values but not crash).
- If **data-race-free** (all shared accesses via atomics/locks) → guaranteed **sequential consistency**: operations appear interleaved in some global order preserving program order per thread.

`happens-before` is partial order: `A happens-before B` means B sees A's effects.

```
Program order within thread → happens-before
Unlock(m) happens-before Lock(m) of same mutex (mutex provides release-acquire)
Atomic store_release happens-before atomic load_acquire that reads that value
```

## C++11 Memory Model (Most Comprehensive)

First comprehensive model 2011, defines atomics + 6 memory orders:

```cpp
enum memory_order {
  memory_order_relaxed,
  memory_order_consume, // deprecated, similar to acquire via dependency
  memory_order_acquire,
  memory_order_release,
  memory_order_acq_rel, // RMW
  memory_order_seq_cst // strongest
};
```

- **relaxed**: no ordering, only atomicity + modification order per location. Use for counters where ordering not needed.
- **acquire**: load — subsequent operations cannot reorder before it. Pairs with release.
- **release**: store — prior operations cannot reorder after it. `release` synchronizes with `acquire` that reads same value → happens-before.
- **acq_rel**: RMW (fetch_add) both acquire and release.
- **seq_cst**: global total order for all seq_cst ops, plus acquire/release semantics. Default, safest, slowest (requires full fence on x86 `MFENCE` or `XCHG`).

Example:

```cpp
std::atomic<int> x{0}, y{0};
int n=0;

// Thread1
n=23; // non-atomic
x.store(1, std::memory_order_release); // release: n=23 visible before x=1

// Thread2
while(!x.load(std::memory_order_acquire)); // acquire: sees x=1 → n==23 guaranteed
int y=n; // safe
```

Without release/acquire, compiler/CPU could reorder `n=23` after `x=1` or `int y=n` before load of x.

**Modification order**: each atomic location has total order of modifications consistent across all threads, even relaxed.

**SC-DRF**: If all atomics seq_cst and no data races, program SC.

### Consume — Dependency Ordering

`memory_order_consume` was for dependency chains (pointer → field) on Alpha where address dependency preserved even without barrier. Deprecated due to compiler difficulty implementing. Use `acquire` now.

## Java Memory Model

- `volatile` variable → seq_cst? Actually Java volatile is sequential consistency-ish (total order for volatiles). Since Java 5, volatile provides happens-before: write to volatile happens-before subsequent read of same volatile.
- `synchronized`: unlock happens-before lock of same monitor.
- `final` fields: special semantics, visible after constructor completes without synchronization.
- VarHandle (Java 9+) adds Acquire/Release modes similar to C++ for performance, but most code uses `volatile` (seq_cst).

## Go Memory Model

Guarantees: if goroutine A writes before synchronizing event (channel send, mutex unlock, atomic store, `sync.Once`), and goroutine B's synchronizing event (channel recv, mutex lock, atomic load, `WaitGroup.Wait`) happens after, then B sees A's write.

Channel is strongest synchronization:

```go
var a string
done := make(chan bool)
go func(){
    a = "hello"
    done <- true // send happens-before recv
}()
<-done
fmt.Println(a) // guaranteed "hello"
```

Go race detector (`go run -race`) finds data races at runtime — use in tests.

Go does not define relaxed atomics beyond `sync/atomic` with seq_cst-like guarantees.

## Rust Memory Model

Rust's model builds on C++11: `std::sync::atomic` with `Ordering::{Relaxed, Acquire, Release, AcqRel, SeqCst}`. Ownership prevents data races at compile time: `Send` and `Sync` traits ensure only thread-safe types cross threads. If safe Rust, data races impossible (except via `unsafe` + atomics).

Rust also has `std::sync::Mutex` which provides lock-based happens-before.

## Acquire/Release vs Seq_Cst Weakness

Research article Programming Language Memory Models [research.swtch.com] explains:

SC atomics require global interleaving total order. Acquire/release atomics require coherence per location only — allows `r1=0,r2=0` in store buffering example even with acquire/release, while seq_cst disallows.

Example:

```
Thread1: x.store(1, release); r1 = y.load(acquire);
Thread2: y.store(1, release); r2 = x.load(acquire);
Can r1=0 && r2=0? With acquire/release YES on ARM, with seq_cst NO.
```

Thus acq/rel is cheaper but less intuitive — use seq_cst unless proven bottleneck.

## Fences

Explicit fences: `std::atomic_thread_fence(order)` — no memory access but ordering. `fence(acquire)` ensures prior loads complete, `fence(release)` ensures prior stores visible.

## Interview Checklist

- Always define data race first.
- Claim DRF-SC.
- Explain acquire pairs with release to create happens-before.
- Give Go channel / Java volatile / C++ release-acquire example.
- Mention TSO vs weak, store buffering litmus, and why x86 still can reorder store-load.
- Warn about relaxed — only for counters, not for publication.

## Interview Questions

**Q: What is sequential consistency?**
Result of any execution same as if operations of all threads interleaved in some order, each thread's program order preserved. Intuitive but expensive to implement.

**Q: What is happens-before?**
Partial order: A happens-before B if B guaranteed to see A's effects. Created via program order, unlock→lock, release→acquire, etc. If no happens-before between conflicting accesses → data race.

**Q: Why does C++ say data race = UB?**
Allows compiler to assume no races and aggressively optimize (e.g., hoist loads out of loops). If race exists, compiler assumptions break, program can do anything.

**Q: Difference between acquire and seq_cst?**
Acquire only orders with paired release on same location and creates happens-before. Seq_cst additionally creates global total order across all seq_cst ops, preventing store buffering anomaly (r1=0,r2=0). Seq_cst needs full fence, slower.

**Q: How does Go ensure visibility?**
Via synchronization: channel send happens-before recv, mutex unlock happens-before lock, atomic store happens-before load that observes it, WaitGroup, Once. Without sync, no guarantee and race detector may flag.

## Cross-References

- [Lock-free](./lock-free.md) — ABA, hazard pointers
- [RCU](./rcu.md) — publish-subscribe via release/acquire
- [Memory Barriers](../os/synchronization/memory-barriers.md) — smp_mb, acquire, release, seq_cst
- [Go Memory Model](../languages/go/memory-model.md) — channel happens-before
- [C++ Memory Model](../languages/cpp/memory-model.md) — templates, atomics
- [Java Memory Model](../languages/java/jvm.md) — volatile, final, VarHandle

## References

- Grokipedia — Memory Model (programming): relaxed, release consistency, acquire/release, TSO, DRF [Grokipedia]
- Russ Cox — Programming Language Memory Models: DRF-SC, C++11 three kinds atomics strong/medium/weak, acquire/release vs seq_cst weakness example Notify/Wait, VarHandle [research.swtch.com]
- Modernes C++ — Synchronization and Ordering Constraints: six memory_orders, read/write/RMW types, sequential consistency vs acquire-release vs relaxed [Modernes C++]
- Boehm — Sequential Consistency for Race-Free Programs proof
- Think-Cell Talk — C++ Memory Model: data race = UB, SC-DRF, locks, atomic
