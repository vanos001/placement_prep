# ZGC (Z Garbage Collector)

ZGC (Z Garbage Collector) is a low-latency garbage collector for the Java HotSpot VM, introduced as an experimental feature in Java 11 (2018) and production-ready in Java 15 (2020). It targets pause times < 10 ms for heaps from 8 MB to 16 TB, regardless of heap size. This page covers the design (concurrent marking, concurrent relocation, colored pointers), the trade-offs vs. G1GC, and the production tuning.

## The Goal

A garbage collector must balance three goals:
- **Throughput**: minimize total CPU time spent on GC.
- **Latency**: minimize pause time.
- **Footprint**: minimize memory overhead.

HotSpot's collectors trade these differently:
- **Serial GC**: best footprint, worst throughput (single-threaded), bad latency.
- **Parallel GC**: good throughput, bad latency (full-heap pauses).
- **G1GC**: tunable latency (default 200 ms pauses), moderate throughput.
- **ZGC**: best latency (< 10 ms pauses), moderate throughput, moderate footprint.

For applications where pause time is critical (real-time trading, interactive UIs, microservices), ZGC is the choice.

## The Algorithm

ZGC's core operations are concurrent (run alongside application threads):

1. **Mark start** (STW): a brief pause (~1 ms) initializes the marking phase.
2. **Concurrent mark**: application threads continue; GC threads walk the object graph, marking reachable objects.
3. **Mark end** (STW): a brief pause finalizes the marking.
4. **Concurrent relocate**: live objects are moved to free space (compaction), concurrently with application threads.
5. **Remap** (STW): a brief pause updates references to relocated objects.

Each STW pause is < 1 ms on modern hardware. The concurrent phases can run for many seconds without stopping the application.

## Colored Pointers

ZGC's most innovative feature: **colored pointers**. Each object pointer in the heap has multiple bits reserved for GC metadata:

```text
Standard 64-bit pointer:
  [ unused 16 bits | address 48 bits ]

ZGC pointer (64-bit):
  [ 4 metadata bits | unused 12 bits | address 48 bits ]
   ↑
   mark_0, mark_1, remapped, finalized
```

The metadata bits indicate the object's state:
- `mark_0`, `mark_1`: the marking phase (which marking pass is active).
- `remapped`: the object has been relocated; the pointer is stale.
- `finalized`: the object can be finalized (special finalization).

When the GC marks an object, it flips the mark bits in the pointer. When the GC relocates an object, it sets the `remapped` bit; subsequent reads of the pointer trigger a "barrier" that updates the pointer to the new address.

## Load Barriers

The colored pointer requires a "load barrier" — code that runs whenever the application reads an object reference:

```text
T reads pointer P:
  if P.colored_bits are stale (mark or remap needed):
    apply the GC's correction:
      - If P points to a relocated object, update P to the new address.
      - If P needs to be marked, mark the object.
  return P
```

The barrier adds ~5% overhead to pointer loads. For most applications, this is unmeasurable (most loads are not on the hot path). For pointer-heavy workloads (linked lists, tree traversals), the overhead can be 10-20%.

## Heap Organization

ZGC organizes the heap into "ZPages" of three sizes:
- **Small**: 2 MB, holds objects < 256 KB.
- **Medium**: 32 MB, holds objects 256 KB - 4 MB.
- **Large**: 1+ MB per object, single object per page.

Large objects get their own pages (no compaction needed — they don't move). Small and medium objects are placed in pages that get compacted.

The page-level organization enables concurrent relocation: the GC can move one page's contents while the application reads another page.

## Comparison to G1GC

| Aspect | G1GC | ZGC |
|--------|------|-----|
| Pause time | 200 ms (default), tunable | < 10 ms |
| Heap size | Up to 64 GB typical | Up to 16 TB |
| Throughput | High | Medium (load barrier overhead) |
| Footprint | Medium (region-based) | Medium (ZPage-based) |
| Best for | Default heap < 32 GB | Large heap or latency-critical |
| Java version | 7+ | 15+ |

G1GC is the default in Java 9+; ZGC is opt-in (`-XX:+UseZGC`).

## Production Tuning

ZGC is largely self-tuning; the recommended JVM flags are minimal:

```bash
java -XX:+UseZGC -Xmx64g -jar myapp.jar
```

Additional tuning:
- `-XX:ConcGCThreads=N`: number of concurrent GC threads (default = ~25% of CPUs).
- `-XX:ParallelGCThreads=N`: number of STW GC threads (default = ~100% of CPUs).
- `-XX:ZUncommitDelay=N`: delay before uncommitted memory is freed (default 300s).

ZGC logs include pause time, concurrent phase duration, and live set size. Monitor the pause time; if it exceeds 10 ms consistently, increase `ConcGCThreads` (more concurrent work means smaller pauses).

## When to Use ZGC

Use ZGC when:
- Heap > 32 GB and G1GC pauses exceed your SLO.
- Application is interactive (latency-sensitive user-facing API).
- You can trade ~5% throughput for 10× lower latency.

Don't use ZGC when:
- Heap < 8 GB (Serial or G1GC is fine).
- Throughput is the only metric (use Parallel GC).
- Application is batch (pauses don't matter; use Parallel GC for throughput).
- Running on Java < 15 (use Shenandoah instead — see below).

## Generational ZGC (Java 21+)

Java 21 (Sept 2023) introduced **Generational ZGC** as a JEP-enhancement experiment. The generational hypothesis (most objects die young) lets ZGC focus its work on the "young generation" — newly-allocated objects — rather than scanning the whole heap every cycle.

Generational ZGC reduces:
- Concurrent mark time (only scan young gen).
- Concurrent relocate time (only relocate young gen).
- Overall CPU usage (don't reprocess old objects every cycle).

Generational ZGC became production in Java 21 (Sept 2023) with `-XX:+ZGenerational` flag (default in some Java distributions).

## Comparison to Shenandoah

Shenandoah is Red Hat's competing low-latency GC, available since Java 12. The two are very similar:

| Aspect | ZGC | Shenandoah |
|--------|-----|------------|
| Pause time | < 10 ms | < 10 ms |
| Algorithm | Colored pointers + load barriers | Brooks pointers + write barriers |
| Heap size | Up to 16 TB | Up to 64 GB (designed for less) |
| Java version | 15+ | 12+ |
| Load overhead | ~5% | ~10% (more barriers) |
| Best for | Large heaps | Smaller heaps, broader OS support |

For most workloads, either works. ZGC is the more recent and more optimized for large heaps.

## Common Pitfalls

1. **Using ZGC on a small heap.** ZGC's overhead is constant; on a small heap (<8 GB), the overhead is more visible relative to the savings. Use G1GC for small heaps.

2. **Forgetting to set `-Xmx`.** ZGC can grow the heap dynamically (default is up to 80% of system memory). Set an explicit max to avoid OOM kills.

3. **Expecting 0 ms pauses.** ZGC's pauses are <10 ms, not 0. The pause is for STW coordination, not for actual GC work. Plan for <10 ms pauses, not zero.

4. **Trusting that ZGC works with all JVM features.** Older JVM features (e.g.,JVMTI, certain bytecode instruments) may not interact well with ZGC's colored pointers. Test before relying on ZGC for production.

5. **Forgetting the load barrier overhead.** ZGC adds ~5% overhead to pointer loads. For pointer-heavy workloads, this can be significant. Profile before adopting.

6. **Forgetting that "concurrent" doesn't mean "free".** Concurrent GC still uses CPU. ZGC's concurrent phases can use 25-50% of available CPU. Plan capacity.

## References

- [ZGC documentation](https://openjdk.org/jeps/377) (JEP 377, production in Java 15)
- [Generational ZGC (JEP 439)](https://openjdk.org/jeps/439) (Java 21)
- [ZGC source code](https://github.com/openjdk/jdk/tree/master/src/hotspot/share/gc/z)
- Per Liden, "[ZGC: The Z Garbage Collector](https://cr.openjdk.org/~pliden/slides/ZGC-DevTrack-JavaOne-2018.pdf)" (JavaOne 2018)
- [Shenandoah documentation (Red Hat)](https://wiki.openjdk.org/display/shenandoah/Main)
- [Aleksey Shipilev: Java GC comparison](https://shipilev.net/jvm/anatomy-quark/3-gc-pause/)
- [LWN: ZGC for Java (2020)](https://lwn.net/Articles/816455/)
