# Shenandoah: Concurrent Compaction with Forwarding Pointers

Shenandoah is a low-latency, region-based garbage collector for the HotSpot JVM, developed at Red Hat around one idea: let mutator threads keep running while the collector *compacts* the heap, by routing every reference through an indirection cell (a "Brooks pointer") that is updated when objects move. It entered OpenJDK as an experimental collector in JDK 12 and became production-grade in JDK 15. Alongside [G1](./g1gc.md) and [ZGC](./zgc.md) it forms the family of concurrent region collectors in HotSpot; this page covers what makes it mechanically different from both. The general collector landscape and vocabulary live in [garbage-collection.md](./garbage-collection.md).

## Position: the Third Concurrent-Region Collector

G1 and ZGC make opposite bets on the same problem:

- **G1** ([g1gc.md](./g1gc.md)) evacuates regions in stop-the-world pauses. It compacts (no fragmentation), but pause time grows with the amount of live data copied.
- **ZGC** ([zgc.md](./zgc.md)) moves evacuation entirely off the pause by encoding GC metadata in pointer bits and filtering every load through a load barrier. Pauses stay tiny regardless of heap size.

Shenandoah takes ZGC's goal -- pauses independent of heap size -- but reaches it by a different mechanism: instead of colored pointers, a per-object forwarding pointer, and instead of folding reference updates into load barriers alone, a dedicated concurrent **update references** phase that walks the heap after evacuation.

Version history:

- 2014: research project at Red Hat; JEP 189 filed ("Shenandoah: A Low-Pause-Time Garbage Collector (Experimental)").
- JDK 12: mainlined in OpenJDK as an experimental collector (`-XX:+UseShenandoahGC`).
- JDK 8u / 11u: backported into Red Hat's OpenJDK builds, so latency-sensitive users did not have to wait for the JDK 12+ train.
- JDK 15: production-grade via JEP 379.
- JDK 24: generational mode (young/old distinction under the same concurrent machinery) introduced experimentally.

## Brooks Pointers

Every object gets one extra header word: the **forwarding pointer**. In steady state it points to the object itself. References in the heap are references to that word, so when the collector copies an object it flips one word, and every stale reference to the old copy transparently lands on the new one:

```text
normal state                        during / after evacuation

   ref                                  ref (stale: old address)
    |                                    |
    v                                    v
 +--------+ fwd                    +--------+ fwd      +--------+
 | object |----> itself            | object |--------> | new    |
 +--------+                        +--------+          +--------+
                                   old copy            fwd == self
                                   (tombstone)
```

The mutator never stalls for the move: a load that lands on the old copy follows the forwarding word and returns the new address. Writes, CAS operations, and GC threads resolve the same way, which is what makes *concurrent* compaction safe: a mutator either acts on the old copy before the forwarding CAS or on the new copy after it, never on both.

Contrast with ZGC's colored pointers: ZGC stores mark/remap metadata *inside the 64-bit pointer* and costs zero per-object heap space, but needs reserved pointer bits (64-bit platforms only) and bit-masking on every load. Shenandoah spends 8 bytes of heap per object but works on any pointer width, and its barrier fast path is a plain two-word compare.

## Anatomy of a GC Cycle

One full concurrent cycle, with only two short pauses:

```text
time ----------------------------------------------------------------->
MUT |run......|SW|run.......|SW|run...........|run............|run...|
GC         |  |          |  |               |               |      |
        init    concurrent  final       concurrent       concurrent
        mark    marking     mark        evacuation       update refs
                                                             then conc.
                                                             cleanup
SW = STW pause, short: work scales with the root set, not with heap size
```

1. **Init mark (STW, short):** scan roots (threads, stacks, handles) to seed the mark queues.
2. **Concurrent marking:** GC threads walk the object graph while mutators run. Mutator stores pay a SATB pre-write barrier (same Yuasa family as G1's -- see [gc-write-barriers.md](./gc-write-barriers.md)) so overwritten references are snapshotted.
3. **Final mark (STW, short):** drain the mark queues, update root references that point at already-evacuated objects, and select the evacuation set.
4. **Concurrent evacuation:** GC threads copy live objects out of the evacuation set into fresh regions, CASing each forwarding pointer as the copy completes. Mutator accesses in flight resolve through the forwarding word.
5. **Concurrent update references:** the distinctive phase -- GC threads walk the live heap and rewrite every reference field that still points at an old copy. G1 does this inside its STW pause (remembered sets tell it exactly where the incoming references are); Shenandoah defers it so no pause grows with the pointer graph.
6. **Concurrent cleanup:** regions left with zero live objects are reclaimed wholesale.

## Update References: Why a Separate Pass

The forwarding pointer heals references *lazily*: a mutator load that touches an old copy resolves through it, but the healed value lives in the mutator's register -- the field that held the stale address is not rewritten. Left alone, stale references would accumulate. The update-refs phase closes the gap eagerly: one traversal of the live heap that makes every field point at the current copy again. After it completes, old copies are unreachable and forwarding words return to steady state.

The cost is a second pass over the heap per cycle (in non-generational mode). That is the price of not needing remembered sets and of keeping evacuation pause-free. Generational Shenandoah attacks exactly this cost by confining most cycles to young regions, so the full-heap update pass becomes the exception instead of the rule.

## Load Reference Barriers vs Write Barriers

What the JIT emits for Shenandoah:

- **On every reference load** -- a *load reference barrier* (LRB): load the forwarding word, compare it against the object address, fall through if equal. The fast path is one extra load, one compare, and a never-taken branch in steady state; the slow path calls into the runtime, which resolves and self-heals the reference, and additionally marks the object while concurrent marking is active. The barrier is emitted *always*, even between cycles -- it must be correct for the moment a cycle starts -- and the fast path keeps it cheap when nothing is happening.
- **On reference stores during marking only** -- a SATB pre-write barrier: if marking is active, push the overwritten value into a buffer. This is the same mechanism G1 uses for marking ([gc-write-barriers.md](./gc-write-barriers.md)).
- **Nothing else.** No post-store card barrier, no remembered sets, no cross-region check on stores. Finding references *into* an evacuated region does not require recording them at store time, because the LRB plus the update-refs pass make stale references self-correcting.

The contrast with G1 is stark: G1 pays a two-part write barrier on every store (SATB during marking, card-table marking always) to maintain per-region remembered sets, and its load path is barrier-free. Shenandoah moves that cost from stores to loads. ZGC also taxes loads, but with pointer bit tests instead of a forwarding indirection.

| Aspect | G1 | Shenandoah | ZGC |
|--------|----|------------|-----|
| Barrier fires on | every ref store | every ref load | every ref load |
| Store barrier | SATB + card table | SATB (marking only) | none |
| Load barrier | none | forwarding check | color-bit check |
| Remembered sets | per-region RSets | none | none |

## Heuristics: Pacing, Degenerated GC, Full GC

Concurrent collectors fail differently from STW ones: the failure mode is *falling behind* the allocation rate, not one long pause. Shenandoah escalates in steps:

1. **Adaptive cycle trigger (IHOP-like).** The default heuristics track the observed allocation rate and the durations of past cycle phases, then start a cycle early enough to finish before the free pool is exhausted -- the same learn-the-threshold idea as G1's adaptive IHOP ([g1gc.md](./g1gc.md)).
2. **Pacing.** If the collector is behind, the *mutator* is throttled: allocation requests park briefly until the GC makes progress, trading small latency spikes for keeping the cycle concurrent.
3. **Degenerated GC.** If free memory runs out while a cycle is still running, the remaining concurrent work (typically evacuation) is finished stop-the-world in one more pause -- the cycle degrades instead of failing.
4. **Full GC.** If even the degenerated mode cannot complete (rare), a parallel STW mark-compact runs as the last resort. Emergency conditions (memory critically low, class-unloading pressure) force the most thorough cycle configuration.

Operationally: enable with `-XX:+UseShenandoahGC` and resist tuning further. The pacing and degeneration counters in GC logs are the health signals to watch; a cycle that repeatedly degenerates means the concurrent budget (threads, heap headroom) is too small for the allocation rate.

## Regions and Evacuation Set Selection

The heap layout is G1-style: fixed-size regions (256 KB floor, count chosen from heap size), with a per-cycle evacuation set chosen greedily -- regions with the most garbage first, until enough free space is reclaimed to survive the next cycle. The difference is what happens after selection: G1 evacuates its set in a pause, Shenandoah concurrently via forwarding pointers. This shared region vocabulary is why moving between G1 and Shenandoah needs no mental-model change, only a barrier-profile change.

## Shenandoah vs ZGC vs G1

| Aspect | G1 | ZGC | Shenandoah |
|--------|----|-----|------------|
| Pointer encoding | plain pointers | metadata bits in 64-bit ptr | forwarding word per object |
| Space overhead | RSets, card table | reserved pointer bits | +1 word per object |
| Store barrier | SATB + card (always) | none | SATB (marking only) |
| Load barrier | none | always-on color check | always-on forwarding check |
| Stale refs fixed | during STW evacuation | on load (remap) | on load + update-refs pass |
| Pause profile | scales with copied live set | near-constant | near-constant |
| Generational | yes (young/old) | JDK 21+ | JDK 24+ (experimental) |
| Availability | JDK 7+, default 9+ | experimental 11, prod 15 | experimental 12, prod 15 |

Rule of thumb: G1 when throughput dominates and 100-200 ms pauses are acceptable; ZGC or Shenandoah when they are not. Between the two low-latency collectors, steady-state overhead differences are workload-dependent -- measure rather than assume. The sibling pages' comparisons ([zgc.md](./zgc.md), [g1gc.md](./g1gc.md)) use the same table shape, so these rows line up with theirs; generational ZGC is covered in [zgc.md](./zgc.md).

## Demo: Evacuation Through Forwarding Pointers

The simulation below models the forwarding-pointer world deterministically: each tick interleaves one GC step with one mutator step, a stand-in for a real concurrent schedule. Objects form a linked chain; a cycle marks, evacuates a region, then updates references. Watch the mutator read that lands mid-evacuation: it resolves through the forwarding word with zero STW involvement, and the stats separate barrier slow-path hits from direct hits. (Simplifications: one field per object, and a healed reference is modeled as a variable updated in place.)

```python
"""Shenandoah model: Brooks forwarding pointers + load reference barrier."""
from collections import Counter

def r(v):                              # render a reference for the timeline
    return "None" if v is None else "obj" + str(v)

class Heap:
    def __init__(self, cap):
        self.fwd, self.body = {}, {}   # fwd: handle -> location (Brooks word)
        self.free, self.nid, self.stw = cap, 0, 0
        self.marking, self.dead, self.s = False, set(), Counter()

    def alloc(self):
        h = self.nid; self.nid += 1
        self.fwd[h] = h                # forwarding word points to self
        self.body[h] = [None]; self.free -= 1
        return h

    def use(self, h):                  # load reference barrier
        self.s["uses"] += 1
        loc = self.fwd[h]
        if loc == h:
            self.s["direct"] += 1      # fast path: fwd == self
        else:
            self.s["barrier"] += 1     # slow path: follow and self-heal
            self.fwd[h] = loc
        return loc

    def read(self, h):
        v = self.body[self.use(h)][0]
        print("    MUT read    obj%d.next -> %s" % (h, r(v)))

    def write(self, h, val):
        old = self.body[self.fwd[h]][0]
        if self.marking and old is not None:
            self.s["satb"] += 1        # SATB: snapshot overwritten value
        self.body[self.use(h)][0] = val
        print("    MUT write   obj%d.next = %s" % (h, r(val)))

    def copy(self, h):                 # one concurrent evacuation step
        new = self.nid; self.nid += 1
        self.body[new] = list(self.body[self.fwd[h]])
        self.fwd[h] = new              # the CAS of the Brooks pointer
        self.dead.add(h); self.free -= 1; self.s["copies"] += 1
        print("    GC  copy    obj%d -> obj%d (fwd set)" % (h, new))

    def update_refs(self):             # the distinctive concurrent pass
        print("    GC  update-refs: walking live objects")
        for loc in sorted(self.body):
            if loc in self.dead:
                continue               # old copies are not walked
            f = self.body[loc][0]
            if f is not None and self.fwd[f] != f:
                self.body[loc][0] = self.fwd[f]; self.s["upd"] += 1
                print("        obj%d.next: %s -> %s" % (loc, r(f),
                                                        r(self.fwd[f])))

    def cleanup(self):
        for loc in self.dead:
            del self.body[loc]; self.free += 1
        print("    GC  cleanup: %d old copies freed" % len(self.dead))

h = Heap(12)
objs, prev = [], None
for _ in range(6):                     # bootstrap: chain obj0 -> ... -> obj5
    o = h.alloc()
    if prev is not None:
        h.body[prev][0] = o
    objs.append(o); prev = o
print("== full cycle: mark, evacuate {obj1 obj2 obj3}, update, cleanup")
h.stw += 1; h.marking = True           # init mark
print("    STW init mark (roots scanned)")
h.read(objs[4])                        # direct hit
h.write(objs[2], None)                 # SATB snapshots obj3
h.write(objs[2], objs[5])              # SATB sees None: filtered
h.marking = False
h.stw += 1                             # final mark
print("    STW final mark (roots compacted; evacuation set: obj1 obj2 obj3)")
evac = [objs[1], objs[2], objs[3]]     # concurrent evacuation + mutator ops
for i, e in enumerate(evac):
    h.copy(e)
    if i == 0:
        h.read(objs[1])                # stale handle: slow path, no STW
    elif i == 1:
        h.read(objs[0])                # never evacuated: fast path
    else:
        h.write(objs[5], None)         # untouched region: fast path
h.update_refs()
h.cleanup()
s = h.s
print("stats: ref uses=%d (barrier slow hits=%d, direct hits=%d), "
      "SATB snapshots=%d, copies=%d, refs updated=%d, STW ticks=%d"
      % (s["uses"], s["barrier"], s["direct"], s["satb"],
         s["copies"], s["upd"], h.stw))
```

Output (real run, identical across repeated executions):

```text
== full cycle: mark, evacuate {obj1 obj2 obj3}, update, cleanup
    STW init mark (roots scanned)
    MUT read    obj4.next -> obj5
    MUT write   obj2.next = None
    MUT write   obj2.next = obj5
    STW final mark (roots compacted; evacuation set: obj1 obj2 obj3)
    GC  copy    obj1 -> obj6 (fwd set)
    MUT read    obj1.next -> obj2
    GC  copy    obj2 -> obj7 (fwd set)
    MUT read    obj0.next -> obj1
    GC  copy    obj3 -> obj8 (fwd set)
    MUT write   obj5.next = None
    GC  update-refs: walking live objects
        obj0.next: obj1 -> obj6
        obj6.next: obj2 -> obj7
    GC  cleanup: 3 old copies freed
stats: ref uses=6 (barrier slow hits=1, direct hits=5), SATB snapshots=1, copies=3, refs updated=2, STW ticks=2
```

Three details carry the design: the mutator read during evacuation returns without any pause (1 slow-path hit out of 6 uses); the SATB snapshot preserved the one non-null overwritten reference during marking; and the update-refs pass is what repairs `obj0.next` and the stale field copied into `obj6` -- the mutator's own heal only fixed its local variable. When a real cycle cannot keep this pace up, the same collector escalates exactly as described above: pacing first, then a degenerated STW finish, then full GC.

## Where It Fits

- Latency-critical services on distributions where Shenandoah is the mature option (Red Hat OpenJDK builds, 8u/11u backports) -- often the only low-pause choice before JDK 15.
- Pointer-dense large heaps where one extra word per object plus a predictable compare is an acceptable rent for pause-free compaction.
- Throughput-dominated jobs with loose latency targets should stay on [G1](./g1gc.md); tight-latency budgets on very large heaps should benchmark Shenandoah against [ZGC](./zgc.md) under production traces.

## References

- [Shenandoah wiki (OpenJDK)](https://wiki.openjdk.org/display/shenandoah/Main) -- project home: design docs, options, GC log reading.
- [JEP 189: Shenandoah: A Low-Pause-Time Garbage Collector (Experimental)](https://openjdk.org/jeps/189) -- original JEP; mainlined in JDK 12.
- [JEP 379: Shenandoah: A Low-Pause-Time Garbage Collector (Production)](https://openjdk.org/jeps/379) -- production status in JDK 15.
- Flood, Kennke, Shipilev, Ramakrishna, Zalewski, "[Shenandoah: an open-source concurrent compaction garbage collector for OpenJDK](https://dl.acm.org/doi/10.1145/2972206.2972210)", PPPJ 2016 -- the design paper, including the Brooks-pointer mechanics.
- [JEP 439: Generational ZGC](https://openjdk.org/jeps/439) -- the generational direction on the ZGC side, context for the comparison table.
- [Shenandoah source in OpenJDK](https://github.com/openjdk/jdk/tree/master/src/hotspot/share/gc/shenandoah) -- the phases, barriers, and pacing machinery as implemented.
