# Escape Analysis

Escape analysis is a compiler optimization that determines whether an object's lifetime stays within the function that created it, or "escapes" to the outside (returned, stored in a global, passed to a function that may keep it). Objects that don't escape can be stack-allocated instead of heap-allocated, avoiding garbage collection overhead. This page covers the analysis algorithm, the use cases (stack allocation, scalar replacement, synchronization elimination), and the production implementations in Go, Java HotSpot, and Scala's GraalVM.

## Why Escape Analysis Matters

Heap allocation has costs:
- Allocation: ~100 ns for a small object (a malloc + bump pointer, often optimized).
- Garbage collection: a per-object cost paid during GC pauses. For Go's mark-sweep GC, this is ~10 ns per live object per collection.
- Cache locality: heap-allocated objects may be far from each other, causing cache misses.

Stack allocation avoids these:
- Allocation: ~1 ns (a stack pointer bump).
- No GC: the object is freed automatically when the function returns.
- Cache locality: stack-allocated objects are contiguous in the cache.

For a function that allocates 1000 short-lived objects, stack allocation saves ~100 µs per call. For a hot function called 1 million times per second, that's 100 seconds per second — well, 10% of the CPU.

## The Analysis

Escape analysis is a **interprocedural data-flow analysis** that tracks which objects' references "escape" the function. The key abstraction: every object reference is classified as:

- **No escape**: the reference stays within the current function.
- **Arg escape**: the reference is passed to another function but doesn't escape further (the callee escapes locally).
- **Global escape**: the reference is stored in a global, returned, or stored in an object that escapes.

The analysis is flow-insensitive (ignores order of statements) and context-sensitive (different callers see different escaping behavior).

```text
function foo() {
    p = new Object();     // p is "no escape" initially
    bar(p);               // p may escape through bar — depends on bar's analysis
    return p;             // p escapes (returned to caller)
}

function bar(q) {
    q.x = 1;              // q doesn't escape here
                          // (only the field is set, the reference stays local)
}
```

The analysis is conservative: if it can't prove an object doesn't escape, it assumes it does. False positives (claiming escape when there is none) lose optimization opportunities; false negatives (missing escapes) cause correctness bugs (stack-allocated object is accessed after the function returns).

## The Optimization: Stack Allocation

If escape analysis proves an object doesn't escape, the compiler can:
1. Stack-allocate the object (in the function's stack frame).
2. Eliminate the GC write barrier for stores to the object (no GC interaction).
3. Eliminate the lock acquisition for synchronized methods on the object (no other thread can see it).

```go
// Go example
func makePoint(x, y int) *Point {
    p := &Point{x, y}    // p might escape... depends on usage
    return p             // p escapes (returned)
}

func usePoint(x, y int) int {
    p := &Point{x, y}    // p doesn't escape (stays local)
    return p.x + p.y     // p dies here
}
```

In `usePoint`, Go's escape analysis proves `p` doesn't escape. The compiler stack-allocates `p` (or even better, scalar-replaces it — see below).

## Scalar Replacement of Aggregates

A more aggressive optimization: if an object doesn't escape, replace its fields with separate local variables. The object's struct/record is never materialized in memory.

```text
// Before scalar replacement
function f() {
    p = new Point(1, 2);     // p has fields x=1, y=2
    return p.x + p.y;
}

// After scalar replacement
function f() {
    x = 1;
    y = 2;
    return x + y;
}
```

The `Point` object never exists in memory. This is the optimization that makes Java code that uses lots of small temporary objects competitive with hand-written C code.

## Synchronization Elimination

If escape analysis proves an object is local (doesn't escape, so only the current thread can see it), the compiler can eliminate the synchronization on the object's synchronized methods.

```java
// Before
synchronized void f() { ... }   // the lock acquisition is expensive

// After escape analysis (if 'this' doesn't escape)
void f() { ... }                // lock removed
```

Java's HotSpot JVM does this for objects that escape analysis proves are thread-local.

## Production Implementations

### Go

Go's escape analysis is in the `gc` compiler (cmd/compile/internal/escape). The algorithm is **intraprocedural with a 2-pass flow analysis**:

1. First pass: conservative — assume every reference passed to a function escapes.
2. Second pass: for each function, look at the actual usage and override the conservative assumption.

Output: per-allocation-site decision (heap or stack). The user can inspect with `go build -gcflags='-m'`:

```bash
$ go build -gcflags='-m' point.go
./point.go:5:9: &Point{...} escapes to heap (returned)
./point.go:10:9: &Point{...} does not escape (local use)
```

### Java HotSpot

HotSpot's escape analysis is in the C2 (Server) compiler. The algorithm is **interprocedural** with limited context sensitivity:

- **Arg escape**: tracked across one level of call.
- **Scalar replacement**: aggressive — replaces fields with separate variables.
- **Synchronization elimination**: removes `synchronized` blocks on thread-local objects.

HotSpot's escape analysis is fragile; many workloads see no benefit because the analysis can't prove escape-free for objects that look like they escape (e.g., passed to a method that's inlined later).

### GraalVM

GraalVM's escape analysis (in the Graal compiler) is more aggressive than HotSpot's. The algorithm is **partial escape analysis** — it can move allocations across control-flow edges:

```text
// Before
function f() {
    p = new Point();          // p allocated
    if (cond) {
        return p;             // p escapes (returned)
    }
    return p.x;
}

// After partial escape analysis
function f() {
    if (cond) {
        p = new Point();     // allocation moved here (only when needed)
        return p;
    }
    x = scalar_field;
    return x;
}
```

GraalVM can move the allocation to the branch where it's actually needed (the one that escapes), avoiding allocation on the other branch. This is the most advanced escape analysis in production.

### Scala (LPC)

Scala's compiler has escape analysis for closures. A closure that doesn't escape can be inlined, removing the closure object entirely.

## Common Pitfalls

1. **Forgetting that escape analysis is conservative.** A reference that might escape (the analysis can't prove otherwise) is heap-allocated. This is correct but suboptimal.

2. **Confusing escape analysis with liveness analysis.** Liveness analysis is about register allocation; escape analysis is about heap vs stack. They're related but distinct.

3. **Expecting escape analysis to eliminate all heap allocations.** Real-world code typically has 50-80% of allocations that escape. Escape analysis helps with the 20-50% that don't, not all of them.

4. **Forgetting that escape analysis is interprocedural.** The compiler needs to analyze called functions, which means whole-program analysis or inlining of all callers. JIT compilers can do this with profile-guided inlining; AOT compilers need LTO.

5. **Forgetting that escape analysis doesn't compose with reflection.** A function that uses reflection on an object can't be analyzed — the reflection API may keep the object alive in surprising ways.

6. **Expecting synchronization elimination to work for all `synchronized` blocks.** Only blocks on objects that don't escape the current thread can be eliminated. Cross-thread objects still need the lock.

## When Escape Analysis Doesn't Help

- Object is stored in a global or static field.
- Object is returned to a caller.
- Object is passed to an unknown function (e.g., a callback via reflection).
- Object's lifetime spans multiple threads.

In these cases, the object must be heap-allocated. The compiler's job is to recognize these cases and not falsely claim escape-free.

## Benchmarks

Production numbers for escape analysis impact:

- **Java HotSpot (DaCapo benchmark)**: ~5-15% speedup from escape analysis + scalar replacement.
- **Go**: ~5-10% speedup from escape analysis. Most allocations are already stack-allocated (Go's design favors stack allocation).
- **GraalVM**: ~20-30% speedup over HotSpot due to more aggressive escape analysis.

The big wins come from eliminating allocations in hot inner loops, not from one-off allocations.

## References

- Choi, Gupta, Serrano, "[Escape Analysis for Java](https://www.cs.cornell.edu/Courses/cs711/2005fa/papers/p921-choi.pdf)" (OOPSLA 1999)
- Kotzmann & Mössenböck, "[Run-time Object Detection and Run-time Object Merging](https://ssw.jku.at/Research/Papers/Moessenboeck05-TR/)" (2005)
- Stadler et al., "[Partial Escape Analysis and Scalar Replacement for Java](https://ssw.jku.at/Research/Papers/Stadler14Master/Stadler14Master.pdf)" (Master's thesis, 2014)
- [Go escape analysis source code](https://github.com/golang/go/blob/master/src/cmd/compile/internal/escape/)
- [HotSpot escape analysis documentation](https://docs.oracle.com/javase/8/docs/technotes/guides/vt/optimize/escape.html)
- [GraalVM escape analysis](https://www.graalvm.org/graalvm-features/escape-analysis/)
- [Go FAQ: When should I use pointers?](https://go.dev/doc/faq#references)
- [LWN: Escape analysis in modern compilers (2020)](https://lwn.net/Articles/815531/)
