# Alias Analysis

Alias analysis is a compiler analysis that determines whether two memory references can refer to the same memory location. The result is used by downstream optimizations: if two references cannot alias, they can be reordered; if they may alias, the compiler must be conservative. This page covers the alias categories, the analysis algorithm (intraprocedural vs. interprocedural), the points-to analysis foundation, and the production implementations in LLVM, GCC, and HotSpot.

## The Three Categories

For any two memory references `p` and `q`, alias analysis classifies their relationship as one of:

- **Must alias**: `p` and `q` definitely refer to the same memory location.
- **No alias**: `p` and `q` definitely refer to different locations.
- **May alias**: the analysis cannot prove either way (must be conservative).

Most analyses produce may-alias results conservatively (assuming alias unless proven otherwise).

```c
int x, y;
int *p = &x, *q = &y;
*p = 1; *q = 2;        // No alias: p and q point to different variables

int *r;
*r = 3;                // May alias with x or y — we don't know what r points to
```

The conservative may-alias result forces the compiler to treat `*r = 3` as potentially modifying `x` or `y`, preventing optimizations like moving the `*r = 3` after a `print(x)`.

## The Properties of Analysis

Alias analyses are classified along several dimensions:

- **Flow-sensitive vs. flow-insensitive**: flow-sensitive considers the order of statements; flow-insensitive treats the program as a set of statements. Flow-sensitive is more precise but more expensive.
- **Context-sensitive vs. context-insensitive**: context-sensitive distinguishes between different call sites of a function; context-insensitive doesn't.
- **Field-sensitive vs. field-insensitive**: field-sensitive distinguishes between fields of a struct; field-insensitive treats the whole struct as one location.
- **Unification-based vs. subset-based**: unification-based (Steensgaard) merges points-to sets aggressively; subset-based (Andersen) is more precise.

The trade-off is always precision vs. analysis time. The fastest analyses (Steensgaard, ~O(N)) are least precise; the most precise (subset-based context-sensitive, ~O(N^3)) are slow.

## Points-to Analysis

Points-to analysis is the foundation of alias analysis. It computes, for each pointer, the set of memory locations it may point to.

```text
For each statement in the program:
  p = &x;        → PointsTo(p) = {x}
  p = q;         → PointsTo(p) = PointsTo(q)
  p = *q;        → PointsTo(p) = union over v in PointsTo(q) of PointsTo(v)
  *p = q;        → For each v in PointsTo(p), PointsTo(v) = PointsTo(q)
```

Solved by fixed-point iteration. The points-to sets grow monotonically until they stabilize.

The alias relationship between two pointers `p` and `q`:
- **Must alias**: PointsTo(p) ∩ PointsTo(q) = PointsTo(p) (q points to all of what p points to, and more).
- **No alias**: PointsTo(p) ∩ PointsTo(q) = ∅ (no shared location).
- **May alias**: PointsTo(p) ∩ PointsTo(q) ≠ ∅ (at least one shared location).

## Andersen vs. Steensgaard

Two classic algorithms:

### Andersen (subset-based, 1994)

Constraints are subset constraints: `PointsTo(p) ⊆ PointsTo(q)` (where p = q).

```text
For p = &x:    PointsTo(p) ⊇ {x}     (p contains x)
For p = q:     PointsTo(p) ⊇ PointsTo(q)  (p contains everything q contains)
For p = *q:    For each v in PointsTo(q), PointsTo(p) ⊇ PointsTo(v)
For *p = q:    For each v in PointsTo(p), PointsTo(v) ⊇ PointsTo(q)
```

Solved by iterating to fixed point. Complexity: O(N^3) in the worst case, ~O(N^1.5) in practice.

Precision: Andersen is the standard for production compilers (LLVM's `pta` and HotSpot's `CHAP`).

### Steensgaard (unification-based, 1996)

Constraints are unification constraints: `PointsTo(p) = PointsTo(q)` (where p = q).

```text
For p = &x:    Unify PointsTo(p) with {x}
For p = q:     Unify PointsTo(p) and PointsTo(q)  ← both become the same set
For p = *q:    For each v in PointsTo(q), Unify PointsTo(p) and PointsTo(v)
For *p = q:    For each v in PointsTo(p), Unify PointsTo(v) and PointsTo(q)
```

Complexity: O(N α(N)) — near-linear. But unification is overly aggressive: once two pointers are unified, they remain unified even if their points-to sets would later diverge.

Steensgaard is used in fast JITs (V8, .NET) where analysis time matters more than precision.

## Field Sensitivity

A field-sensitive analysis distinguishes between fields of a struct:

```c
struct Point { int x; int y; };
struct Point p;
int *a = &p.x;
int *b = &p.y;
*a = 1; *b = 2;     // No alias: even though both point into p, they point to different fields
```

Field sensitivity adds the field name to the memory location: `p.x` is distinct from `p.y`. This is crucial for struct-heavy code (C, C++).

Field insensitivity treats the whole struct as one location; `*a` and `*b` may alias.

## Heap Sensitivity

Heap sensitivity distinguishes between heap allocations:

```c
int *p = malloc(sizeof(int));
int *q = malloc(sizeof(int));
*p = 1; *q = 2;    // No alias: p and q point to different heap objects
```

- **Heap-insensitive**: all `malloc` calls return the same abstract location. `*p` and `*q` may alias.
- **Heap-sensitive (per-allocation-site)**: each `malloc` call site returns a distinct abstract location. Different call sites = different locations.
- **Heap-sensitive (per-allocation-instance)**: each runtime allocation is a distinct location. Precise but unbounded.

Per-allocation-site is the standard precision for production analyses (LLVM's `dsa`).

## Type-based Alias Analysis (TBAA)

For C and C++, the language standard says accessing a `int*` and a `float*` to the same memory is undefined behavior (strict aliasing). Compilers exploit this:

```c
int *ip = ...;
float *fp = ...;
*ip = 1;       // writes int
*fp = 2.0;     // reads float — but TBAA says this is no-alias, so *ip is unchanged
```

GCC and Clang implement TBAA via type metadata in LLVM IR. The metadata says "this load is reading a float"; the alias analysis trusts the metadata.

The catch: TBAA is unsafe with `union` types and casts. Compilers have flags to disable it (`-fno-strict-aliasing` in GCC).

## Production Implementations

### LLVM

LLVM's alias analysis is in the `AliasAnalysis` interface, with several implementations:
- `BasicAA`: local, intraprocedural, uses type-based rules.
- `ScopedNoAliasAA`: respects `noalias` annotations.
- `TBAA`: type-based rules.
- `CFLAA`: context-free-language-based interprocedural analysis (Andersen-like).

The default is `BasicAA + TBAA + ScopedNoAliasAA`. Interprocedural analyses are run via LTO.

### GCC

GCC's alias analysis (`alias.c`) is intraprocedural with type-based rules. Interprocedural analysis is done at LTO time.

### HotSpot

HotSpot's escape analysis includes alias analysis for objects. The C2 compiler's alias analysis is conservative but supports synchronization elimination (objects that don't escape can't be aliased by other threads).

## The Optimizations that Use Alias Analysis

- **Dead store elimination**: a store that's overwritten before any read is dead. Alias analysis proves no read happens (because of no alias).
- **Common subexpression elimination**: a load that follows a store of the same value can be replaced with the stored value (must-alias).
- **Loop invariant code motion**: a load inside a loop can be hoisted out if the analysis proves nothing in the loop modifies the memory location (no alias).
- **Vectorization**: SIMD requires no dependencies between iterations. Alias analysis proves this.
- **Reorder stores**: `*a = 1; *b = 2;` can be reordered if `a` and `b` don't alias.

## Common Pitfalls

1. **Forgetting that C/C++ type-based aliasing is unsafe with `union`.** A `union` of `int` and `float` has the standard say "undefined behavior to access the wrong type". Compilers may optimize as if you don't do this; if you do, the behavior is unspecified.

2. **Confusing escape analysis with alias analysis.** Escape analysis tracks object lifetime; alias analysis tracks which pointers may refer to which objects. They're related but distinct.

3. **Assuming no-alias when the analysis says may-alias.** The compiler must be conservative — may-alias means "we don't know", treated as "they may alias" for safety.

4. **Forgetting that interprocedural analysis requires LTO.** Without LTO, the compiler can't see the called function's internals; it must assume the worst (e.g., the callee may store the pointer globally).

5. **Expecting perfect precision.** Real-world analyses are conservative. The compiler may miss 20-30% of no-alias opportunities because the analysis can't prove them.

## References

- Andersen, "[Program Analysis and Specialization for the C Programming Language](https://users.au.dk/anders/06b586b697d78e9c3b37.pdf)" (PhD thesis, 1994)
- Steensgaard, "[Points-to Analysis in Almost Linear Time](https://www.cs.utexas.edu/~spec/papers/p32-steensgaard.pdf)" (POPL 1996)
- [LLVM Alias Analysis documentation](https://llvm.org/docs/AliasAnalysis.html)
- [LLVM's Type-based Alias Analysis (TBAA)](https://llvm.org/docs/LangRef.html#tbaa-metadata)
- [GCC alias analysis source](https://github.com/gcc-mirror/gcc/blob/master/gcc/alias.c)
- [Clang and strict aliasing](https://clang.llvm.org/docs/LanguageExtensions.html#strict-aliasing)
- Hind & Pioli, "[Which Pointer Analysis Should I Use?](https://www.cs.cornell.edu/courses/cs711/2005fa/papers/hind-pioli.pdf)" (ICSE 2000)
- [LWN: Alias analysis in modern compilers (2020)](https://lwn.net/Articles/817835/)
