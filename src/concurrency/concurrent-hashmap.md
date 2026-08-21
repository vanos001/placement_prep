# Concurrent Hash Maps — Striping, Lock-Free Reads, Tree Bins, Copy-on-Write

A concurrent hash map is the workhorse of server-side code. A naive
`HashMap` wrapped in `Collections.synchronizedMap` has a single lock
and serializes every operation; under any real contention it falls over
at the lock. Production designs reduce contention by *narrowing* the
lock scope: a fixed array of locks (striping), a lock per bin
(striping's natural endpoint), or no lock at all for reads
(lock-free reads). The most heavily tuned implementation, Java's
`ConcurrentHashMap`, has gone through three distinct generations of
this narrowing. Go's `sync.Map` makes a different bet — it optimizes
for read-heavy workloads with copy-on-write. Rust's `DashMap` is the
pragmatic third option: shard the map and call it a day.

This chapter compares the three and explains why each is right for its
workload.

## Java's ConcurrentHashMap — three generations

### Generation 1 (Java 5-7): segments

Doug Lea's original `ConcurrentHashMap` (JSR-166, Java 5) split the map
into `Segment[]`. Each segment was a mini hash table with its own
`ReentrantLock`. A key hashes twice — once to pick a segment, then
again to pick a bin inside that segment. Writes lock the segment.

```
+--------+--------+--------+--------+   Segment[] (16 by default)
|  S0    |  S1    |  S2    |  ...   |   each Segment: a mini HashMap
| LK     |  LK    |  LK    |        |   with its own ReentrantLock
| bins.. | bins.. | bins.. |        |
+--------+--------+--------+--------+
```

The concurrency level (16 by default) is the maximum number of
simultaneous writers. On a 256-core machine, that 16-cap is a real
limit. The plus side: reads are lock-free — they walk the bucket chain
using volatile reads, so a `get()` contends with nothing. The
downside: segments can't be added or removed at runtime, and resizing
happens per-segment, not globally, leading to uneven capacity.

### Generation 2 (Java 8+): striped per-bin locks

Java 8 threw out the segments. The table is now `Node[]`, and each
`Node` in the chain can be `synchronized` on directly. A write acquires
the lock on the bin's head node (`synchronized (first)`) and operates
on the chain under that lock.

```
table (Node[])
+--------+--------+--------+--------+
|  bin0  |  bin1  |  bin2  |  ...   |
+--------+--------+--------+--------+
   |
   v
  head -> n1 -> n2 -> n3
        ^
        synchronized (head) for any structural modification
```

Reads still take no lock — they use volatile reads of the bucket slot
and walk the chain. Writes to different bins proceed in parallel. This
scales linearly with the number of bins, not with a fixed concurrency
level.

There is a wrinkle: the first time you write to an empty bin, you use
a CAS (`casTabAt`) instead of a `synchronized` block, because there is
no node to lock. The CAS establishes the head; subsequent writes to
that bin take the synchronized lock.

### Generation 3 (Java 8+): tree bins

The "hash collision DoS" — submit a request with many keys that hash
to the same bucket, then watch a hashmap degrade from O(1) to O(n) per
operation — was a real problem. Java 8 added tree bins: when a single
bucket's linked list exceeds `TREEIFY_THRESHOLD` (=8), it is converted
into a red-black tree. Lookups in that bin drop from O(n) to O(log n).

```
bin (after treeify):
   head (TreeBin)
    |
    r-b tree of 8+ entries, ordered by Comparable/hashCode
```

`TreeBin` carries a special lock protocol: a write lock for structural
modifications, a read lock that allows multiple concurrent readers, and
a `WAITER` field that lets readers queue if a writer is active. Below
`UNTREEIFY_THRESHOLD` (=6) on resize, the tree degrades back to a list.

## Lock-free read

A `get(k)` does the following, with no locks taken:

```
get(k):
  h = spread(k.hashCode)               // high bit XOR'd in
  tab = table                           // volatile read of the array ref
  if tab == null return null
  i = (n-1) & h                         // bin index, n = tab.length
  e = tabAt(tab, i)                     // volatile read of the bin slot
  if e == null return null
  if e.hash == MOVED                    // ForwardingNode during resize
      tab = e.nextTable                 // follow the forward pointer
      retry with new tab
  ... walk e.next chain, volatile reads, compare keys ...
```

The Node fields are either `final` (key, hash) or `volatile` (val,
next). Java's final-field memory model guarantees that a fully
constructed Node is visible to any reader that observes the volatile
read of the bucket slot — never a half-constructed node. This is the
same publish-via-volatile trick the Disruptor uses for slot
publication.

The `ForwardingNode` redirect is what makes the resize *non-disruptive*
— a `get` racing a resize either reads the old bin (if not yet moved)
or follows the forward pointer to the new table. Readers never block;
they just may take one extra hop.

## The resize protocol

When the table needs to grow (load factor exceeded), `transfer()`
walks the old table in *strides* — chunks of bins a thread grabs and
moves. For each bin in the stride:

1. Acquire `synchronized (head)`.
2. Split the chain into two new chains based on the new high bit of
   each key's hash: one stays in the old bin position in the new
   table; the other goes to `old_pos + old_capacity` (the bit it just
   gained).
3. Atomically install a `ForwardingNode` at the old bin slot — it
   carries a pointer to the new table.

```
old table (16 bins):       new table (32 bins):
[ ][ ][F][s][ ][ ]         [ ][ ][ ][L][ ][H][ ]...
        |                    ^
        +-> ForwardingNode --+   (readers follow; helpers continue)
[ ][s][ ][ ][ ][ ]   <-- s = a bin still being moved; new table
                          has two chains: L (low bit) and H (high bit)
```

A thread arriving to find an `F` in its stride *helps* the next
stride. The protocol self-balances: the more contention, the more
helpers; the transfer usually completes in `O(log N)` wall-clock time
across `N` threads instead of `O(N)` for one thread doing all the
work.

## Count accounting

A naive `AtomicLong` for the size is a bottleneck: every `put`
increments the same counter. Java uses `CounterCell[]` (a striped
counter, the same idea as `LongAdder`). Each thread picks a cell based
on a thread-local hash and increments only that cell. `size()` sums
all cells — slower, but `size()` is rare (diagnostics); the put-path
is fast.

This is the same pattern as `java.util.concurrent.atomic.LongAdder`,
and the same idea Linux uses for per-CPU counters (`percpu_counter`).

## Comparison to Go's sync.Map

Go's `sync.Map` makes a different bet. The documentation is explicit:
it is for "write-heavy traffic outnumbers read-heavy traffic by a
certain ratio," actually — let me quote precisely. The Go docs say it
is optimized for two cases:

1. The map is written once and read many times (cache population).
2. Multiple goroutines are reading, writing, and overwriting disjoint
   sets of keys.

The implementation: two maps.

```
sync.Map
  read  atomic.Value  -> map[interface{}]*entry   (read-only, COW)
  dirty map (mutex-guarded) -> map[interface{}]*entry   (full map)
  misses int   (count of read misses since last promote)
```

- `read` is an `atomic.Value` — a pointer to a struct of read-only
  `map[k]*entry`. Reads hit this with no lock.
- `dirty` is a `Mutex`-guarded full map. Every read that misses in
  `read` falls through to `dirty` (taking the lock).
- When `misses` exceeds a threshold (the dirty map's length), `dirty`
  is promoted to `read` (an atomic pointer swap), and the new `dirty`
  starts empty. The promote is also when the new `read` loses
  "logically deleted" entries (those with `nil` value pointer, a
  copy-on-write tombstone).

Write path: take the mutex, look up the entry, copy-on-write the
`*entry` (atomic swap of the pointer inside the entry), update dirty.
Deletes set the entry pointer to `nil` (tombstone); actual removal
happens at next promote.

This is **not** a general ConcurrentHashMap replacement. The Go docs
are explicit: "Before using a Map, consider whether your program would
be just as correct using a plain `map` with a separate `Mutex` or
`RWMutex`." The right workload is a config cache, a TLS session
ticket store, a routing table — read-heavy, mostly disjoint keys, rare
bulk invalidation.

Where Java's CHM is great for general mixed workloads, Go's `sync.Map`
is great for the specific case the Go authors had in mind.

## Rust's DashMap

DashMap is the pragmatic Rust answer: shard the map into `N`
independent `RwLock<HashMap<K, V>>`, where `N` defaults to
`4 * available_cpus`. Operations on different shards never block each
other. Reads take a read lock on the shard; writes take a write lock
on the shard.

```rust
use dashmap::DashMap;

let map = DashMap::new();
map.insert("alpha", 1);             // write lock on shard 3
let _ = map.get("alpha").unwrap();  // read lock on shard 3
let _ = map.get("beta").unwrap();   // different shard, no contention
```

Trade-offs vs Java's CHM:

- **Simpler design.** Each shard is a `HashMap`; reads take an `RwLock`
  read; writes take the write lock. No volatile reads, no per-bin
  lock, no `ForwardingNode` shuffle. Easy to reason about.
- **Sharding is fixed at creation.** If a workload's hot keys all
  hash to the same shard, that shard becomes the bottleneck, while
  other shards sit idle. Java's per-bin locking spreads the
  contention more evenly.
- **No tree bins.** Adversarial collisions fall back to `HashMap`'s
  linked list (O(n) per op). Java's tree bins keep it O(log n). For
  security-sensitive code, this matters.
- **Iteration is per-shard, weakly consistent.** A snapshot of the
  map is taken per shard; writes during iteration may or may not be
  visible.

DashMap is the right pick for "I just need a concurrent hashmap in
Rust" — most workloads do fine. For pathological key distributions or
adversarial inputs, you want per-bin locking (a custom design or a
bindings wrapper around `folly::ConcurrentHashMap`).

## When to use which

| Workload | Pick |
|---|---|
| Java, general mixed read/write | `ConcurrentHashMap` |
| Java, very high read contention on hot keys | `ConcurrentHashMap` (read is lock-free) |
| Go, read-heavy config cache | `sync.Map` |
| Go, write-heavy | `map` + `RWMutex` (sync.Map's promote hurts) |
| Rust, general | `DashMap` |
| Rust, adversarial key distribution | custom per-bin-locked map |
| C++, high throughput | Folly's `ConcurrentHashMap` (also sharded, with SIMD hashing) |
| Linux kernel | `hashtable` + RCU + per-bucket spinlock, or `rhashtable` (resizable, RCU-friendly) |

## Cross-references

- [Java Concurrency](./java.md) — the broader JDK concurrency story
- [Go Channels](./go-channels.md) — Go's synchronization primitives, of which `sync.Map` is one
- [Rust Ownership](./rust-ownership.md) — how Rust's lifetime model relates to DashMap's shards
- [Lock-Free Structures](./lock-free-structures.md) — the underlying lock-free machinery in CHM
- [Readers-Writers](./readers-writers.md) — RwLock semantics
- [RCU](./rcu.md) — Linux's resizable RCU-friendly hash table (`rhashtable`)

## References

- OpenJDK `ConcurrentHashMap` source: [java.util.concurrent.ConcurrentHashMap](https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/concurrent/ConcurrentHashMap.java) — segments (legacy), `casTabAt`, `ForwardingNode`, `transfer`, `CounterCell`, `TreeBin`
- Go `sync.Map` documentation: [pkg.go.dev/sync#Map](https://pkg.go.dev/sync#Map) — explicit intended workloads and caveats
- DashMap crate: [docs.rs/dashmap](https://docs.rs/dashmap/latest/dashmap/) — Rust's sharded concurrent map
- Brian Goetz et al., *Java Concurrency in Practice*, ch 5 "Building Blocks" — `ConcurrentHashMap` design rationale and the lock-striping motivation
- Doug Lea's `ConcurrentHashMap` writeup: [OSWEGO util.concurrent](http://gee.cs.oswego.edu/dl/jsr166/dist/docs/) — the original JSR-166 documentation
- Aleksey Shipilev, [JEP 8163371 analysis and "HashMap performance" posts](https://shipilev.net/) — covers tree bins and resize performance
- Folly `ConcurrentHashMap`: [github.com/facebook/folly](https://github.com/facebook/folly/blob/main/folly/concurrency/ConcurrentHashMap.h) — SIMD hashing, striping
