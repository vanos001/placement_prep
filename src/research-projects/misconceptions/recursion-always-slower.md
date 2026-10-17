# "Recursion is always slower than iteration"

## Overview

This claim circulates with genuine evidence behind it: naive recursive
Fibonacci is catastrophic, Python crashes on deep recursion, and call stacks
are not free. But "always" is doing illegitimate work. Some languages
guarantee that tail recursion *becomes* a loop; some compilers transform it
at optimization levels; and for divide-and-conquer algorithms the recursive
form is the natural formulation with identical asymptotics. This page gives
the precise cost model, the language-by-language guarantees, and the worked
numbers on both sides.

## The Claim, Stated Fairly

The strongest common form: "Every recursive call costs a stack push, so
recursion always pays overhead iteration never pays; and deep recursion
crashes. Therefore any recursive function can and should be rewritten as a
loop for performance." The fairness is real: the overhead claim is true for
non-tail recursion without optimization, and the crash claim is true in
Python by default. The overreach is the word "always" and the assumption that
the rewrite is both possible and profitable.

## Verdict

**Context-dependent.** Without tail-call optimization, non-tail deep recursion
pays real frame costs and overflows; with TCO, tail recursion compiles to a
loop with zero frames; and for divide-and-conquer problems, recursion and
iteration have the same asymptotic cost with different readability.

## Why People Believe It

The kernel of truth is threefold. First, the stack-frame cost is real: each
call typically stores a return address, saved registers, and locals — dozens
of bytes and a few nanoseconds, which matters in hot loops. Second, the
catastrophic case is memorable: naive `fib(30)` makes 2,692,537 calls
(2·F(31) − 1, with F(31) = 1,346,269) where a 30-iteration loop makes 30 —
an exponential-versus-linear gap that has nothing to do with recursion's
overhead but everything to do with how the claim is remembered. Third, Python
really does crash: the interpreter has no tail-call optimization and enforces
a recursion limit of about 1,000 by default (`sys.getrecursionlimit()`), so
deep recursion is a `RecursionError`, not a slowdown.

What the claim ignores is that "recursion" is not one thing: tail recursion in
a TCO language *is* iteration after compilation, and divide-and-conquer
recursion (merge sort) carries the algorithm's structure in a way that
iterative rewrites only replicate with an explicit stack — the same frames,
managed by hand.

## The Correct Formulation

| Case | Reality |
|---|---|
| Tail recursion in Scheme, Racket, and other languages with mandated proper tail calls | Guaranteed constant stack space — the specification requires it; this *is* iteration |
| Tail recursion in C/C++/Rust at optimizing levels | Commonly compiled to a loop (GCC/Clang with `-O2`), but the standards do not guarantee it — treat as an optimization, not a contract |
| Non-tail recursion, no TCO | One frame per pending call: real memory and call cost; depth is bounded by stack size or runtime limit |
| Divide-and-conquer (merge sort) | Depth is O(log n): 10,000,000 elements → about 24 frames; overhead is a rounding error and the recursive form is the clear one |
| Naive exponential recursion (fib) | The problem is recomputation, not recursion; memoization or DP tables fix the asymptotics |
| Python specifically | No TCO, default limit ~1,000 frames: deep recursion is a correctness bug, convert to iteration or raise the limit knowingly |

The precise cost statement: recursion adds per-frame overhead only for calls
that remain on the stack simultaneously. Its depth, not its call count, is
the cost driver. A recursive algorithm whose depth is O(log n) (mergesort) or
whose TCO applies (tail-recursive accumulation) pays essentially nothing over
the iterative equivalent; an O(n)-depth non-tail recursion in Python pays a
crash; an exponential recursion pays asymptotics that no iteration strategy
would have saved without memoization.

## Where It Breaks

**TCO languages.** A tail-recursive accumulator in Scheme is specified to run
in constant stack space — R5RS/R7RS require implementations to support proper
tail recursion. Rewriting it as a loop in a Scheme codebase is ceremony, not
optimization; the claim "always slower" is simply false in this world.

**C++ at `-O2`.** GCC and Clang routinely transform tail calls into jumps,
and the frame disappears. The honest caveat: the C and C++ standards do not
*require* this, so production code must not bet correctness on it — but the
"always slower" claim is now an empirical falsehood for the common toolchain.

**Merge sort.** Recursion depth for 10,000,000 elements is
ceil(log2(10,000,000)) = 24 frames — negligible. The iterative rewrite needs
an explicit stack or bottom-up merge passes, which is more code for the same
comparisons. Here recursion is the idiomatic form, and "iterating it for
speed" trades clarity for nothing. Recursion is also the *natural* form for
every tree traversal: an iterative in-order traversal is an explicit stack of
pending nodes — the same frames, hand-managed.

**Where recursion genuinely hurts.** Python, depth 100,000: `RecursionError`
by default — and even with the limit raised, each frame costs real memory, so
an O(n)-depth recursion risks the real stack. This is the regime where the
belief is correct; the correction is to say so specifically (deep, non-tail,
no-TCO runtime) instead of "always".

**Memoized recursion versus DP tables.** Top-down memoization and bottom-up
tabulation are the same recurrence with opposite iteration order. In Python,
the memoized version pays function-call overhead the loop avoids — a real
constant-factor difference worth knowing — but the asymptotics are identical,
and the memoized version is often easier to prove correct.

## Practical Implications

- Ask "what is the depth?" before asking "is recursion slow?" — depth is the
  cost; call count is not.
- Know your runtime's contract: guaranteed TCO (Scheme), common but
  unguaranteed (C/C++/Rust), absent (Python, JVM until recently). JVM: no
  general TCO in HotSpot today; Scala offers `@tailrec` as a *compiler
  check* that the method is tail-recursive and rewrites it locally.
- In Python, treat deep recursion as a bug: convert to iteration or an
  explicit stack; do not ship `sys.setrecursionlimit(100000)` as a fix.
- Rewrite for clarity first: if the recursive form expresses divide-and-
  conquer structure, keep it; convert only measured hotspots with real depth.
- Exponential recursion is an algorithmic bug — memoize or tabulate; do not
  blame the calling convention.

## Interview Questions

### Is a tail-recursive function as fast as its loop equivalent?

In languages that guarantee proper tail calls (Scheme family), yes by
specification — the implementation must reuse the frame. In C/C++/Rust it is
commonly optimized to a jump at `-O2`/release, but the standard does not
guarantee it, so verify with your toolchain before relying on it.

### Why does naive recursive Fibonacci explode, and what fixes it?

Recomputation: `fib(n)` calls `fib(n-1)` and `fib(n-2)`, so the call count is
2·F(n+1) − 1 — for n = 30, that is 2,692,537 calls. Memoization or a
bottom-up table makes it O(n). The lesson: the blowup is from overlapping
subproblems, not from recursion's frame overhead.

### Your Python service hits `RecursionError` on a deep tree. Options and trade-offs?

Convert to iteration with an explicit stack (each frame becomes a heap node —
same traversal, unbounded depth), or restructure to a worklist. Raising
`sys.setrecursionlimit` risks a real stack overflow (segfault) because CPython
frames consume C stack; it is a mitigation for shallow overruns, not a fix.

## Key Takeaways

- The cost driver is recursion *depth*, not recursion itself: O(log n)-depth
  recursion is effectively free.
- Tail-call guarantees are a language property (Scheme: specified; C/C++:
  toolchain-dependent; Python/JVM: absent) — "recursion is slow" is a claim
  about runtimes, not algorithms.
- Divide-and-conquer and tree algorithms are clearest recursively; iterative
  versions re-implement the stack by hand for the same asymptotics.
- Exponential blowups are recomputation bugs; memoization, not iteration,
  is the fix.

## Cross-References

- [Assumptions Hunt: Complexity Claims](../assumptions-hunt/complexity-claims.md)
  — the general discipline of quantifying "always" claims about cost
- [Recursion](../../dsa/chapters/ch08-recursion.md) — base cases, call
  stacks, and the recursion tree method
- [Sorting Algorithms](../../dsa/chapters/ch05-sorting.md) — merge sort and
  quicksort as the divide-and-conquer case
- [Loop Optimizations](../../compilers/loop-optimizations-deep.md) — what
  optimizing compilers actually do to loops and tail calls
- [Average-Case Complexity](./average-case-complexity.md) — the sibling
  misconception about what complexity classes promise
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- Python documentation. *sys.getrecursionlimit* — "Return the current value
  of the recursion limit, the maximum depth of the Python interpreter stack"
  (default 1,000).
  <https://docs.python.org/3/library/sys.html#sys.getrecursionlimit>
- A. Shinn, J. Cowan, A. Gleckler (eds.). *Revised⁷ Report on the
  Algorithmic Language Scheme (R7RS-small)*, 2013 — requires implementations
  to support proper tail recursion, giving tail-recursive loops constant
  stack space by specification. (Available from scheme-reports.org.)
- H. Abelson, G. J. Sussman, J. Sussman. *Structure and Interpretation of
  Computer Programs*, 2nd ed., MIT Press, 1996 — Section 1.2 on linear
  recursion and iteration.
