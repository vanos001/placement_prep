# Inline Caches & Hidden Classes

Every dynamic-language method call asks a question at runtime: what is the receiver, really? Answering it with a full lookup - hash the selector, walk the class hierarchy - is what naive interpreters do, and it dominates their profile. The inline cache, invented to kill exactly that cost, turned out to be one of the most consequential ideas in language-runtime engineering: the same mechanism that made Smalltalk-80 viable in 1984 powers property access in V8 today and property *specialization* in modern CPython. The [JIT optimization page](./jit-optimization.md) covers devirtualization and ICs at survey level; this page traces the mechanism from its papers to the interview-famous hidden-class question, and measures what CPython actually does.

## The 1984 origin: cache the lookup at the send site

Deutsch and Schiffman's "Efficient Implementation of the Smalltalk-80 System" (POPL 1984) attacked message-send cost head-on. The key observation: a given send site almost always sees receivers of the *same* class, so the result of the last lookup is a near-perfect prediction for the next call. Their send sequence embeds the cache in the code itself:

```text
  send site for:  anObject doThing
  +--------------------------------------+
  | cmp receiverClass, CACHED_CLASS      |   <- patched in by runtime
  | jne  .miss                           |     after first lookup
  | jmp  CACHED_METHOD                   |   <- direct, inlinable jump
  | .miss:                               |
  | call runtime_lookup_and_patch        |   <- slow path: full lookup,
  +--------------------------------------+    then rewrite the two immediates
```

The cache is "inline" because it lives in the generated code at the call site, not in a side table: on a hit, the send costs a compare and a jump. The runtime miss handler performs the ordinary lookup once and *rewrites the instruction stream* - the founding act of adaptive optimization. The paper's other contributions (activations on the stack, direct pointers instead of OOP indirection) mattered too, but the inline cache is what every engine since has inherited.

## Polymorphic inline caches: when the site sees several types

A monomorphic cache thrashes if a site alternates between two or three receiver classes. Holzle, Chambers, and Ungar's "Optimizing Dynamically-Typed Object-Oriented Languages With Polymorphic Inline Caches" (ECOOP 1991, the Self compiler) generalized the trick: grow a *linear chain* of guarded checks at the site, one per observed receiver type, each check falling through to the next and the last one falling to the runtime:

```text
  obj.foo() with three observed receiver maps:
  +--------------------------------------+
  | cmp obj.map, MAP_A  ; jne .next1     | -> A.foo      (hit 1)
  | .next1: cmp obj.map, MAP_B           | -> B.foo      (hit 2)
  |         ; jne .next2                 |
  | .next2: cmp obj.map, MAP_C           | -> C.foo      (hit 3)
  |         ; jne .miss                  |
  | .miss: call lookup_and_extend        |
  +--------------------------------------+
```

Two insights made PICs more than a lookup speedup. First, the checks are *unbiased*: unlike a single "last seen" cache, no observed type evicts another, so moderately polymorphic sites stay fast. Second - the part that shaped all later VMs - the PIC *records the receiver-type distribution* for free. When the optimizing compiler later compiles this site, it knows 94% of receivers are `MAP_A` and can speculatively inline `A.foo` behind a single guard, deoptimizing on the rare cases. PICs are simultaneously a dispatch mechanism and a profiling instrument; every modern feedback-vector design descends from this.

## The four states of a call site

Engines bookkeep this with per-site state machines. V8's feedback slots distinguish monomorphic (one map), polymorphic (a short map list plus per-map handlers), and megamorphic (the site gave up on lists); uninitialized is the virgin state. Two load-bearing details from V8's own source (`src/objects/feedback-vector.h`): the polymorphic list is bounded by a compile-time constant (`DEFAULT_MAX_POLYMORPHIC_MAP_COUNT`), and megamorphic is a real state backed by a global sentinel (`MegamorphicSentinel`) plus a process-wide stub cache - the site stops storing per-map data and falls back to a shared hash lookup keyed by (map, name).

| State | What runs at the site | After the fact |
| --- | --- | --- |
| Uninitialized | Nothing useful; trap to runtime | First execution performs full lookup |
| Monomorphic | 1 compare + direct action | Fastest steady state; goal of shape hygiene |
| Polymorphic | Short linear chain of map compares | Still inlines each arm; ~1 compare per map |
| Megamorphic | Global stub-cache lookup (hash on map+name) | No inlining; dispatch like a dictionary |

## Shapes: the data structure that makes caches cheap

An inline cache needs something cheap to *test* against the receiver. In class-based languages that is the class pointer. JavaScript has no classes, so engines synthesize the equivalent: a per-object descriptor of its property layout, called a **hidden class (Map)** in V8, **shape** in SpiderMonkey, and **structure** in JavaScriptCore. (Academia says "hidden classes"; the engines' naming is documented across V8, SpiderMonkey, JSC, and Chakra in Mathias Bynens' engine-fundamentals write-up.) Property access then compiles to exactly two operations:

```text
  load obj.x:
    1. check:  obj.map == expected_map ?     (the inline cache's guard)
    2. load:   [obj + offset_of_x]           (a C-struct-speed field load)
```

The map does not store property values; it stores the *shape* - for each property name, its offset and attributes - plus a link to the map that results from adding a property. Objects built the same way share one map and are interchangeable to the IC. V8's [fast-properties write-up](https://v8.dev/blog/fast-properties) details the accompanying storage modes (in-object slots, then out-of-object property stores, then dictionary mode).

## Transition trees, and the interview question hiding inside

Adding a property does not mutate the object's map in place - the object *transitions* to a successor map. The engine's maps thus form a transition tree rooted at the empty map:

```text
                     M0 {}                          empty map (root)
                    /    \
             add x /      \ add y
                 /        \
          M1 {x:off0}    M2 {y:off0}          sibling shapes
              |              |
        add y /              \ add x
             /                \
   M3 {x:off0, y:off1}   M4 {y:off0, x:off1}
            (same keys, different offsets - different maps)
```

Which yields the classic V8 interview question: *these two objects have identical keys - why don't they share a hidden class?*

```javascript
const a = { x: 1, y: 2 };   // transitions M0 -> M1 -> M3
const b = { y: 2, x: 1 };   // transitions M0 -> M2 -> M4
// a.map !== b.map : same key set, different property ORDER,
// therefore different offsets and different IC guards
```

The answer: the map encodes the *layout* (offsets), and insertion order determines layout; the two objects would thrash each other's monomorphic caches, silently pushing sites toward polymorphic or megamorphic states. Performance-sensitive code constructs objects of the same "kind" with the same property order - or uses classes/factory functions so all instances walk one transition path. The related degradation is **dictionary mode**: heavy mutation (`delete`, many properties added) pushes an object to a hash-table-backed map where shape checks buy nothing and every access is a real lookup. Engines do this reluctantly - it forfeits everything the shape system bought.

## The JVM's version of the same idea

Java's dispatch is already cheap (a vtable index), so the JVM's problem is one level up: making a virtual call *inlineable*. HotSpot attacks it from two sides. Statically, class hierarchy analysis (CHA) proves a method has exactly one implementation and devirtualizes outright (until class loading invalidates the assumption). Dynamically, HotSpot's interpreter keeps per-call-site receiver profiles - the method-data structure - and the optimizing compiler uses them exactly like PIC distribution data: emit a guarded direct call for the hot receiver (monomorphic/bimorphic sites), fall back to vtable/itable dispatch otherwise. Interface calls use itable lookup patched per site in the interpreter. So the Smalltalk lineage is intact - cache, observe, speculatively specialize - just layered under a static type system instead of replacing one. The [JIT optimization page](./jit-optimization.md) shows the CHA/devirtualization example in Java.

## Megamorphic escape hatches

When a site legitimately sees dozens of types (a logging framework, a serializer dispatching on any input), no per-site cache helps. Engines converge on: a **global stub cache** (V8) hashing (map, name) pairs process-wide, so megamorphic sites at least skip selector hashing; and honest fallback to the general lookup path. There is no trick that recovers inlining at a truly polymorphic site - which is why the standard engineering fixes are architectural: split the site into per-kind paths, sort dispatch by measured frequency, or take the speculative route (profile-guided guards plus deoptimization) that tiered JITs use.

## CPython reality check: no inline caches - but specialization

CPython's attribute access is, honestly, a dictionary operation: `obj.x` compiles to `LOAD_ATTR`, which consults the instance's `__dict__` (a key-sharing dictionary whose key layout comes from the class - a distant cousin of shapes). CPython has no JIT and no inline caches, so there is no map-guarded offset load. What it does have since 3.11 is PEP 659's **specializing adaptive interpreter**: each bytecode executes in a quickened form, and hot instructions specialize themselves to the observed case - `LOAD_ATTR` over an instance dict becomes `LOAD_ATTR_INSTANCE_VALUE`, and over a `__slots__` attribute it becomes `LOAD_ATTR_SLOT`, which reads the slot directly instead of routing through the descriptor protocol. You can watch it happen:

```python
import dis, sys

class Vec:
    __slots__ = ("x", "y")
    def __init__(self, x, y):
        self.x, self.y = x, y

v = Vec(1, 2)

def get_x(vec):
    return vec.x

for _ in range(1000):          # warm-up: let the specializing interpreter adapt
    get_x(v)

print(f"python {sys.version.split()[0]}")
print("get_x bytecode after specialization:")
dis.dis(get_x, adaptive=True)
```

```text
python 3.12.14
get_x bytecode after specialization:
 10           0 RESUME                   0

 11           2 LOAD_FAST                0 (vec)
              4 LOAD_ATTR_SLOT           0 (x)
             24 RETURN_VALUE
```

What `__slots__` buys in CPython is measurable without any JIT: slotted objects store fields in a fixed trailing array with no per-instance dict at all. The benchmark below compares footprint and warm attribute-read time (note this is interpreter-loop time, so the delta is diluted by bytecode dispatch - the honest reading is "smaller and slightly faster", not "10x"):

```python
"""Attribute access + footprint: instance __dict__ vs __slots__ (CPython)."""
import sys, timeit

class PointDict:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class PointSlots:
    __slots__ = ("x", "y")
    def __init__(self, x, y):
        self.x = x
        self.y = y

pd, ps = PointDict(3, 4), PointSlots(3, 4)

def footprint(obj):
    total = obj.__sizeof__()                  # object body
    d = getattr(obj, "__dict__", None)
    if d is not None:
        total += sys.getsizeof(d)             # + attribute dict
    return total

print(f"python {sys.version.split()[0]}")
print(f"instance with __dict__  : {footprint(pd):>4} bytes/object")
print(f"instance with __slots__ : {footprint(ps):>4} bytes/object")

N = 1_000_000
def read_dict():
    x = 0
    for _ in range(N):
        x = pd.x
    return x

def read_slots():
    x = 0
    for _ in range(N):
        x = ps.x
    return x

for label, fn in (("__dict__", read_dict), ("__slots__", read_slots)):
    best = min(timeit.repeat(fn, number=1, repeat=5))
    print(f"attr read ({label}): {best / N * 1e9:6.1f} ns/op   (best of 5 x {N:,})")
```

```text
python 3.12.14
instance with __dict__  :  312 bytes/object
instance with __slots__ :   32 bytes/object
attr read (__dict__):   41.1 ns/op   (best of 5 x 1,000,000)
attr read (__slots__):   33.9 ns/op   (best of 5 x 1,000,000)
```

The arithmetic behind the footprint line: the dict-based object is a 16-byte body plus a 296-byte values dict (312 total); the slotted object is a 16-byte body plus two 8-byte slot pointers (32 total). At container scale that is the difference between fitting a working set in cache and not. The time delta (~18% here; timings wander a few percent between runs, the ratio holds) comes from skipping the dict lookup entirely; under a real JIT with inline caches (V8, or the experimental copy-and-patch JIT CPython 3.13 ships per PEP 744), the shape-guarded path closes the remaining gap toward C-struct speed - which is the whole point of shapes.

## Failure modes

| Symptom | Likely cause | Remedy |
| --- | --- | --- |
| Hot method call site is megamorphic | Site fed many receiver types | Split by kind, or reorder dispatch; check with engine tracing flags |
| Property reads slower than expected | Objects shaped differently (construction order) | Single factory/class per object "kind"; never `delete` properties |
| JVM deoptimizes repeatedly | Speculated receiver type keeps invalidating | Widen types at the boundary; check `-XX:+PrintInlining` output |
| Slotted class still slow in CPython | Hot loop un-specialized (cold), or slot shadowing | Ensure the loop warms up; avoid `__dict__` in `__slots__` classes |

## Interview angle

- *Why can't two objects with the same keys share a hidden class?* Offsets depend on insertion order; a map is a layout, not a key set (transition tree above).
- *What does an inline cache cache?* The (receiver shape -> handler) pair at one site - plus, in PIC form, the observed type distribution used for speculative optimization.
- *Where do PGO and ICs meet?* Both are feedback loops: offline PGO feeds measured frequencies to a static optimizer; ICs/feedback vectors feed measured receiver types to a JIT. HotSpot and AutoFDO are the same idea at two different timescales.

## References

- Deutsch, L. P. & Schiffman, A. M., "Efficient Implementation of the Smalltalk-80 System," POPL 1984: <https://doi.org/10.1145/800017.800542>
- Holzle, U., Chambers, C., & Ungar, D., "Optimizing Dynamically-Typed Object-Oriented Languages With Polymorphic Inline Caches," ECOOP 1991: <https://doi.org/10.1007/BFb0057013>
- Bynens, M., "JavaScript engine fundamentals: Shapes and Inline Caches": <https://mathiasbynens.be/notes/shapes-ics>
- V8 blog, "Fast Properties in V8": <https://v8.dev/blog/fast-properties>
- Shannon, M., "PEP 659 - Specializing Adaptive Interpreter": <https://peps.python.org/pep-0659/>
