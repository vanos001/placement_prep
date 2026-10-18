# Memory Model Assumptions: What Your Program Believes About Memory

## Overview

Most code is written against a phantom machine: one where memory starts zeroed, pointers stay valid, structures occupy exactly their members' size, the stack never runs out, and every write is seen by every reader immediately, in order. Real machines and real language standards promise far less. This chapter walks through the beliefs that C, C++, Java, and Go programs silently hold about memory, shows where each one fails, and states what the standards actually guarantee.

The stakes are unusually high here because memory-model violations do not fail politely. In C and C++ they are undefined behavior: the compiler may assume they never happen and optimize accordingly, so the symptom appears far from the cause, often only in optimized builds. In concurrent code the gap between what the hardware does and what the programmer assumes is the single most common source of "impossible" bugs.

## Assumption 1: "Memory Is Zeroed"

### The taught rule

Declare a buffer, use it. `malloc` gives you memory; the object at the start of your program has its fields.

### The hidden assumptions

- Dynamically allocated memory arrives zeroed. In C, `malloc` returns memory with *indeterminate* contents; only `calloc` (and `memset`) zero it. Fresh anonymous pages from the OS are zero-filled by the kernel (on Linux, first-touch of anonymous `mmap` memory), but `malloc` reuses freed blocks, so the *second* allocation of a given size contains your previous data.
- Class instances in managed languages arrive zeroed (true for Java and Go: `new` gives zero values), which trains habits that leak into systems code.

### Counterexample

```c
char *p = malloc(128);
strcpy(p, "s3cr3t-api-key");
free(p);
char *q = malloc(128);      /* likely the same block, contents unchanged */
```

`q` now very likely contains the old string, because glibc returns the recently freed block first. Two failure modes follow: correctness (the program reads garbage and produces wrong results, often only after the first run of some other code path) and security (uninitialized or freed memory leaks prior contents — the historical basis for a long list of information-disclosure advisories).

### What changes when the assumption is removed

The corrected statement: *only memory you explicitly initialize is defined; memory from `malloc` is indeterminate; memory from `calloc` or fresh OS pages is zero; managed runtimes zero by language rule.* Tools that find violations: Valgrind's memcheck tracks undefined values, MemorySanitizer does the same at compile time, and `-Wuninitialized`-class warnings catch many cases statically.

### Consequences

Interviewers probe this with "difference between `malloc(n)` and `calloc(n, 1)`" and with "why does my program read zeros in this build but garbage in that one". The systems answer covers allocator reuse, not luck.

## Assumption 2: "Pointers Are Always Valid"

### The taught rule

A pointer points at an object; dereference it to get the object.

### The hidden assumptions

- The pointee is still alive (no use-after-free, no dangling pointer to a stack frame that returned).
- The pointer is not null, not misaligned for its target type, and not past the end of its allocation.
- Aliasing has not invalidated the pointer (realloc moves blocks; container growth invalidates iterators and references).

In C and C++ every violation is undefined behavior — not "crash", but license for the optimizer to delete the checks you wrote around the dereference. The undefined-behavior chapter in the DSA track catalogs how far this reaches.

### Counterexample and corrected statement

The loop `while (p) p = p->next;` assumes the list cannot contain a cycle — a validity assumption about structure, not memory. A cycle sends it into an infinite loop, which is why cycle detection (Floyd's tortoise and hare) exists. Corrected statement: *a pointer is valid only within a region of program time and a set of operations you can prove; borrow-checking languages (Rust), GC languages, and disciplined C idioms (ownership tables, arenas) are all attempts to make that proof mechanical.*

### Consequences

The DSA questions "detect a cycle in a linked list" and "merge two lists without aliasing bugs" are validity assumptions wearing a costume. In systems interviews, use-after-free and iterator invalidation are the standard probes.

## Assumption 3: "Arrays Are Contiguous and Structures Are Not Padded"

### The taught rule

`arr[i]` lives at `base + i × sizeof(elem)`; a struct's size is the sum of its fields.

### The hidden assumptions

- Contiguity: true for C arrays by definition, but *layout* breaks silently for pointer structures (`std::vector<std::string>` has contiguous string *objects*, each pointing to heap-allocated character data elsewhere). `sizeof(vec)` does not tell you the bytes of text inside it.
- No padding: false. Compilers insert padding to satisfy alignment. On typical 64-bit ABIs, `struct { char c; int i; }` is 8 bytes, not 5 — the three bytes between `c` and `i` are padding.
- Padding bytes are anything in particular. They are not, so `memcmp`-comparing two structs for equality is wrong even when every field is equal — the padding can differ.

### Counterexample

Serialize `struct Record { char tag; int64_t ts; char name[9]; }` by `fwrite(&rec, sizeof rec, 1, f)` and read it back on a different compiler or architecture. Padding and endianness differ, so the bytes do not line up, and the file "corrupts itself". Similarly, hashing a struct by treating it as a byte array folds padding into the hash, making the result depend on uninitialized bytes.

### What changes when the assumption is removed

Serialization must be field-by-field with explicit endianness (or use a schema), equality must be field-by-field, and memory-estimation exercises must account for alignment (`sizeof` and `offsetof` are the honest measurement tools). The corrected claim: *C arrays are contiguous; structs are aligned, padded, and opaque in their slack bytes; "the memory layout of X" is a property of the ABI, not the language*.

### Consequences

"This struct is 24 bytes" questions in interviews are padding questions. Cache-line discussion (see [complexity claims](complexity-claims.md)) assumes you can predict field placement; padding is where the prediction fails.

## Assumption 4: "The Stack Is Unbounded and Uninitialized Reads Are Deterministic"

### The taught rule

Recursion is the natural expression of tree-shaped problems; deep recursion is fine, and debugging works because values keep their values.

### The hidden assumptions

- The stack is large enough. Typical defaults: 8 MB for the main thread on Linux, 1 MB on Windows, and smaller for secondary threads on some platforms. A recursion depth of a million frames at, say, 100+ bytes per frame overflows all of them.
- Interpreted runtimes add their own limits: CPython's default recursion limit is about 1000 frames, enforced precisely to protect the C stack underneath.
- Uninitialized reads give the *same* garbage every run. They give indeterminate values; debug builds often fill fresh memory with recognizable patterns (which is why "it works in the debugger"), release builds reuse whatever was there.

### Counterexample

Naive recursive `sum(list)` over a 10^7-element list overflows any default stack — depth 10^7 is the killer, not total work. The same algorithm restructured to recurse on the smaller half and iterate on the larger (or made iterative with an explicit heap-allocated stack) has depth O(log n) and runs comfortably. This is exactly why quicksort implementations recurse into the smaller partition first, even though the recursion count is the same asymptotically — the corrected claim is about *depth*, not work.

### What changes when the assumption is removed

The corrected statement: *recursion depth is a resource with a hard, environment-dependent bound; state depth as part of complexity claims (O(n) work can still be O(depth) stack), and convert deep linear recursion to iteration or explicit stacks.* Debug/release differences in uninitialized values are the classic reason a bug "disappears when you add a print statement" — the print shifts the garbage.

### Consequences

Interview questions of the form "your recursive solution — what's the stack depth?" expect this reasoning, and contest judges enforce it by segfaulting exactly the solutions that ignore it.

## Assumption 5: "Signed Overflow Wraps Around"

### The taught rule

Integers overflow and wrap to negative; that's what two's complement does.

### The hidden assumptions

- That the *hardware* wraps is true. That the *language defines the wrap* is not universal. In C and C++, signed integer overflow is undefined behavior (C11 6.5: an expression whose result is not representable has undefined behavior, and Annex J.2 lists signed integer overflow explicitly). The compiler may assume `x + 1 > x`, assume loop counters never wrap, and delete or reorder code accordingly.
- Java defines wrap (JLS: the result of integer arithmetic overflow is the low-order bits — defined two's-complement wrap), which is why Java habits migrate badly into C.

### Counterexample

```c
int total = 0;
for (int i = 0; i < n; i++)
    if (a[i] > 0) total += a[i];      /* signed overflow: UB */
```

With large enough values, the compiler may legally transform overflow-sensitive comparisons (`x + 1 < x` folds to false at compile time) or vectorize the loop assuming no wrap, so the same source produces different results at `-O0` and `-O2`. Corrected statement: *in C/C++ either keep arithmetic in unsigned types (wrap is defined), use checked/saturating intrinsics, or prove the ranges; in Java and Go wrap is defined and two's complement semantics hold.*

### Consequences

This is the quiet twin of the midpoint bug from [input constraints](input-constraints.md): there the arithmetic produced a bad *index* deterministically, here the compiler is entitled to produce anything. Interviewers at systems companies explicitly test whether candidates know UB is not "implementation-defined" — it is unbounded.

## Assumption 6: "A Data Race Is Undefined Behavior — Everywhere"

### The taught rule

Two threads accessing the same memory without synchronization is a data race, and data races are undefined behavior.

### The hidden assumptions

The sentence hides a *language-by-language* table that most engineers have never seen assembled:

| Language | Semantics of a data race | Source of truth |
|----------|--------------------------|-----------------|
| C11 | Undefined behavior: "any such data race ... results in undefined behavior" | C11 5.1.2.4p25 (N1570 draft) |
| C++11 and later | Undefined behavior | the standard's [intro.races] section |
| Java | *Defined but weak*: racy reads must observe some write via "happens-before consistency"; no UB, but no sequential consistency either | JLS §17.4 (docs.oracle.com) |
| Go | An error with *limited outcomes*: racy word-sized reads observe some written value (or a zero value), not arbitrary memory corruption; tools may report the race | go.dev/ref/mem |

The Go memory model states the contrast explicitly: the constraints "make Go more like Java or JavaScript, in that most races have a limited number of outcomes, and less like C and C++, where the meaning of any program with a race is entirely undefined, and the compiler may do anything at all" — while still "insisting that races are errors". Treating all four languages as identical is itself a hidden assumption.

### Counterexample

A racy flag check in C++ can be optimized into a check of a register cached across the loop (hoisted load), producing an infinite loop the race never "caused" directly — the UB license did. The same code in Java is not UB: the read is guaranteed to return some previously written value, but without `volatile`/synchronization there is no happens-before edge, so seeing a stale value forever remains legal. Same symptom, different guarantees, different fixes.

### What changes when the assumption is removed

The corrected statement: *in C/C++ the only acceptable number of data races is zero, and the compiler enforces nothing for you; in Java races are legal but unsequenced — synchronize to get happens-before edges; in Go races are bugs that tooling can catch and the runtime constrains, not licenses.* The practical defense is identical everywhere: protect shared mutable state with the language's synchronization primitives (see [concurrency and scheduling](concurrency-and-scheduling.md)) or use the `atomic` facilities.

### Consequences

This is the deepest interview differentiator in the chapter: candidates who can explain *why* the JMM chose defined-but-weak semantics (to forbid out-of-thin-air values while keeping aggressive JIT optimization) are demonstrating memory-model literacy, not trivia recall.

## Assumption 7: "Reordering Does Not Happen, and volatile Means the Same Thing Everywhere"

### The taught rule

Programs execute in program order; `volatile` makes a variable "thread-safe".

### The hidden assumptions

- Neither the compiler nor the CPU preserves program order across threads. Compilers reorder to optimize; CPUs execute out of order and buffer stores.
- In Java, `volatile` establishes ordering and visibility: a volatile write *synchronizes-with* subsequent volatile reads of the same variable, and volatile accesses behave as if sequentially consistent among themselves (JLS §17.4; the JSR-133 Cookbook tabulates the equivalent barriers).
- In C/C++, `volatile` does none of that. It only tells the compiler not to elide or reorder the access relative to *other volatile accesses* in ways that would break the abstract machine — it provides no atomicity, no inter-thread visibility, and no happens-before edges. It exists for memory-mapped I/O and signal handlers.

### Counterexample: Dekker's litmus test

```c
/* Thread A */            /* Thread B */
x = 1;                    y = 1;
r1 = y;                   r2 = x;
```

With `x` and `y` declared plain `volatile int` in C, running on x86, both `r1` and `r2` can be 0: each core's store sits in its store buffer while the load executes, and x86-TSO permits exactly this store-load reordering. The same litmus test with two Java `volatile int` fields *cannot* produce `r1 == r2 == 0` — the JMM forbids it, and the JIT emits the necessary fences. Identical keywords, opposite outcomes.

### What changes when the assumption is removed

The corrected statement: *C's `volatile` is about the compiler, Java's `volatile` is about threads; inter-thread ordering in C/C++ requires `std::atomic` (with explicit memory orders) or fences; in Java it requires `volatile`, `synchronized`, or `java.util.concurrent` primitives.* The JSR-133 Cookbook is the standard rosetta stone translating "what I want" into "which barrier I need".

### Consequences

The question "is volatile enough to publish this flag?" is a real code-review question, and the answer differs by language. The deeper lesson matches the whole chapter: memory-model keywords are contracts, and the contracts differ more between languages than intuitions expect.

## Interview Questions

1. **What does `malloc` guarantee about the contents of the memory it returns?** Nothing — the bytes are indeterminate. `calloc` zeroes (and may get zero pages from the OS for free), fresh anonymous mappings are zero-filled by the kernel, and `malloc` commonly reuses freed blocks with their old contents. Security-sensitive code must zero on free and initialize on allocation.
2. **Why is `memcmp` on structs wrong, and what is the right way?** Padding bytes between members are indeterminate, so byte-comparison can report inequality for logically equal structs. Compare field by field (or use generated equality); if hashing a struct's bytes, zero the padding first.
3. **Is a data race undefined behavior in Java?** No — that is the C/C++ rule. The JMM gives racy reads defined-but-weak semantics (happens-before consistency: you see some write, never garbage), which permits JIT optimization while forbidding out-of-thin-air values. C11 makes races UB outright; Go treats them as errors with constrained outcomes. The fix differs by language; the requirement to synchronize does not.
4. **Two threads run Dekker's pattern with plain `volatile int` in C on x86. Can both reads return 0? What if it were Java?** Yes in C — volatile does not order the store before the load across threads, and x86-TSO permits store-load reordering. No in Java — volatile accesses are ordered (synchronizes-with), so the JMM forbids both-zero outcomes; the JVM emits fences. Same keyword, different contract.
5. **Why do quicksort implementations recurse into the smaller partition first?** To bound stack depth to O(log n) even in the worst case: the larger half is handled by iteration, so the recursion depth is capped by the smaller-side log, protecting the finite stack — an explicit acknowledgment that "the stack is unbounded" is a false assumption.

## Key Takeaways

- C and C++ make the strongest promises about *not* promising: uninitialized memory, invalid pointers, signed overflow, and data races are all undefined behavior, and UB is an optimizer license, not a crash.
- Java defines wrap-around and defines (but weakens) racy reads; Go constrains race outcomes and treats races as reportable errors; C/C++ do neither. "Data races are UB" is a C/C++ sentence, not a universal one.
- `volatile` is a per-language contract: thread-ordering in Java, compiler-elision prevention in C. Confusing them produces failures only under real hardware concurrency.
- Stack depth, padding, and allocator reuse are finite resources and layout facts that complexity claims silently assume away.
- Every corrected statement in this chapter is verifiable against primary sources: the C11 draft, the JLS, and the Go memory model — read the sources, not summaries of summaries.

## Cross-References

- [Undefined behavior](../../dsa/chapters/ch92-undefined-behavior.md) — the catalog of UB that this chapter's assumptions terminate in.
- [Concurrency memory model](../../concurrency/memory-model.md) — the repo's dedicated page on happens-before and the JMM.
- [Atomic primitives](../../concurrency/atomic-primitives.md) — the synchronization tools that replace the false assumptions here.
- [Memory hardware](../../dsa/chapters/ch52-memory-hardware.md) — caches, TLBs, and the physical layer under these semantics.
- [Concurrency and scheduling](concurrency-and-scheduling.md) — sibling chapter: assumptions about atomicity, timing, and scheduling.
- [Input constraints](input-constraints.md) — sibling chapter: signed overflow and midpoint arithmetic at the input boundary.
- [Go memory model](https://go.dev/ref/mem) — primary source for Go's race semantics (verified).
- [JLS chapter 17](https://docs.oracle.com/javase/specs/jls/se8/html/jls-17.html) — primary source for Java threads, locks, and volatile (verified).
- [C11 draft N1570](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf) — primary source for C UB and data-race wording (verified).
