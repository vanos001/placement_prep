# Integer Overflow Assumptions: What "Numbers Just Work" Silently Promises

## Overview

Integers are the type everyone stops thinking about first, and that is precisely where the assumptions pile up: that arithmetic is mathematical and overflow at least wraps around harmlessly, that unsigned types are safe because they are defined, that the chosen type is big enough for any value the domain produces, and that a modern language's safety guarantees cover the arithmetic it compiles. Each assumption breaks with production consequences — an overflow guard deleted by the optimizer, an allocation size computed as zero, a duration counter that dies after 24.8 days, a check that panics in tests and silently wraps in release builds.

A boundary note positions this chapter against its sibling: [floating-point assumptions](floating-point.md) audits IEEE 754 precision, rounding, and the `0.1 + 0.2` family. This chapter stays entirely with fixed-width integers — wraparound, promotion traps, and overflow-check elimination — the world where values are exact until the type runs out of bits, and then either explode, wrap, or (in C and C++) hand the optimizer a license. The catalogue name for the family is [CWE-190](https://cwe.mitre.org/data/definitions/190.html), integer overflow or wraparound, and it persists because every assumption above is true *in the demo, in the unit test, and on the developer's machine*. The audited failures below follow the collection's five-step pattern.

## Assumption 1: "Overflow Wraps Around Predictably"

### The taught rule

Signed integers wrap on overflow: add one to the maximum and it becomes the minimum, like an odometer — so code can be written assuming wraparound and can even *check* for overflow after the fact by testing whether the sum is smaller than an operand.

### The hidden assumptions

- The rule assumes C-style wraparound semantics. In C and C++, signed integer overflow is *undefined behavior* — the C11 standard's expression evaluation clause (section 6.5 of the [N1570 draft](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf)) defines the result of an unrepresentable signed operation as undefined — so the compiler is free to assume it never happens and to optimize accordingly.
- The optimizer's use of that freedom is the invisible part: `a + 10 > a` folds to `true` (an overflow-capable add is treated as non-wrapping), a guard written *after* the addition can be deleted as provably false, and a loop whose counter could overflow may be transformed because "the counter never overflows". Whole classes of overflow checks are, to the compiler, proofs about impossible states.
- Where wrapping *is* defined — Java and most two's-complement languages — nothing signals it: the failure mode is a plausible wrong number, not an exception.
- Tooling exists but is opt-in: compilers expose `-fwrapv` (define wrapping), sanitizers expose signed-overflow detection (the [UndefinedBehaviorSanitizer](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html) `signed-integer-overflow` check), and neither is on by default in most build pipelines.

### Counterexample

A parser computes a frame length as `len + header` and guards the allocation with `if (len + header < 0) reject;` — written by a developer who believed signed overflow wraps. Under an optimizing compiler the guard compares `len + header` (which cannot overflow, per the optimizer's assumption) with zero, the impossible-negative branch is deleted, and the check protects nothing; a request with `len` near `INT_MAX` then computes a wrapped or otherwise unrepresentable size and reaches the allocator. The guard existed, was reviewed, and did nothing — the failure is in the assumption that the written code is the executed code. Defenses: compute overflow checks *before* the operation (`if (len > MAX - header)`) so no unrepresentable value is ever produced, use checked intrinsics or `__builtin_add_overflow`-style primitives, build with `-fwrapv` where wraparound semantics are genuinely intended, and enable the sanitizer in CI to catch the instances the review missed.

### What changes when the assumption is removed

Corrected statement: *in C and C++, signed overflow is not a value but undefined behavior, so any check that observes the overflowed value is checking a state the compiler may have assumed away; overflow safety must be established by pre-checks or checked-arithmetic primitives, not by post-hoc inspection.* In languages that define wrapping, the corrected statement is quieter but equally binding: wrapping is defined and silent, so nothing about it will ever interrupt the request path.

### Consequences

The interview probe "why is `if (a + b < 0)` not a valid overflow check?" is this assumption in one line, and the senior answer cites the UB clause, the optimizer's reasoning, and the pre-check form. The general lesson — never compute a value you cannot represent, then test it — generalizes across this chapter.

## Assumption 2: "Unsigned Arithmetic Is Safe Because It Wraps"

### The taught rule

Unsigned integers have defined wraparound modulo 2^N, so they are the "safe" type: no undefined behavior, no exceptions, and counts and sizes are naturally unsigned anyway.

### The hidden assumptions

- *Promotion happens before your arithmetic.* In C, a `uint8_t` or `uint16_t` operand is promoted to `int` first, so `a + a` with `a = 200` evaluates as `int` 400 — no wrap — while bitwise complements and other operations reintroduce signed results (`~a` is `-201`); the type you declared is not the type your expression ran in.
- *Mixed comparisons flip direction.* In C and similar systems languages, comparing `int` with `unsigned` converts the signed operand: `-1 > 1u` is true, because `-1` becomes `UINT_MAX`. Loop conditions written as `i < v.size() - 1` are the canonical casualty: for an empty container, `size() - 1` wraps to the maximum, and the "skip last element" loop iterates essentially forever.
- *Size arithmetic overflows before allocation.* `malloc(n * sizeof(T))` computed in a 32-bit width wraps: `n = 536,870,912` (2^29) elements of 8 bytes is exactly 2^32, which wraps to 0 — the allocator happily returns a zero-byte block and the caller writes 4 GiB into it. On 64-bit `size_t` the same expression can still be computed in 32-bit `int` by an intermediate, producing a negative value that converts to an astronomically large request instead.
- *Defined wrapping still schedules the failure:* a wrapping counter is not a correct counter, and downstream comparisons (the guard from Assumption 1, a saturation check, a monotonicity assertion) inherit whichever wrong value the wrap produced.

### Counterexample

An image decoder allocates `width * height * 4` bytes for RGBA output, computed in `int` because all inputs arrived as `int`. A crafted header declares `width = 65,536` and `height = 16,384`: the product is 2^32, which overflows the 32-bit computation to 0, allocation "succeeds" with a zero-length buffer, and the decoder writes 4 GiB of pixel data past its heap allocation. Every operand was individually reasonable; the type of the multiplication was wrong. The defenses are mechanical and testable: compute sizes in the widest unsigned type (`size_t`), use checked multiplication (`__builtin_mul_overflow`, Java's [`Math.multiplyExact`](https://docs.oracle.com/javase/8/docs/api/java/lang/Math.html), Rust's `checked_mul`), validate `width * height` against a declared budget *before* multiplying, and fuzz decoders with boundary headers — 2^16, 2^29, and values that make products land exactly on 2^32.

### What changes when the assumption is removed

Corrected statement: *unsigned arithmetic is defined but not safe: integer promotion, signed-unsigned comparisons, and intermediate width all act before the declared type does, so the fix is to control the type of the computation (widest type, checked primitives, pre-validation) rather than to trust the declared type of the variables.* "It wraps" describes the outcome, not a safety property.

### Consequences

"Why does `-1 > 1u` evaluate to true?" is the promotion-rules interview probe, and the allocation-size story is the code-review check for any expression that multiplies user-controlled dimensions.

## Assumption 3: "The Type Is Big Enough for Real Data"

### The taught rule

A 32-bit integer holds over two billion values; no counter, timestamp, or duration in a normal system comes near that, so `int` is the default type and the choice never needs revisiting.

### The hidden assumptions

- *The unit multiplies the epoch.* Seconds since 1970 fit in `int32` until 2,147,483,647 seconds — 03:14:07 UTC on 19 January 2038, the Y2038 limit — but *milliseconds* overflow 2^31 after about 24.8 days, so any code storing epoch-millis or long uptimes in an `int32` was wrong from February 1970 onward; the type was never big enough for its unit.
- *Counters at line rate exhaust 32 bits in seconds.* A 32-bit octet counter like SNMP's `ifInOctets` wraps every 2^32 bytes: at 1 Gb/s (125 MB/s) that is roughly 34 seconds; at 10 Gb/s, about 3.4. Monitoring that reads absolute values and computes `current - previous` sees a negative or astronomically spurious delta once per wrap — a classic source of phantom traffic spikes.
- *Aggregations inherit the widest operand's width:* summing many `int32` values into an `int32` accumulator fails on principle — total revenue, total bytes, total events — and the failure arrives the day the business succeeds, which is the worst possible time.
- *Boundaries are invisible in tests:* a value near 2^31 behaves identically to any other large value in a functional test; only arithmetic near the boundary distinguishes correct from broken, and no ordinary fixture lands there by accident.

### Counterexample

A fleet dashboard stores per-host uptime and epoch-millisecond event timestamps in an `int32` column. After an infrastructure change, one host with a long-running kernel posts an uptime of 2,147,483,648 milliseconds (24.85 days); the value overflows to `-2,147,483,648`, the dashboard's anomaly detector flags the fleet's "most stable" host as rebooting every ten minutes, and the on-call engineer spends the night chasing a negative number. Separately, the 10 Gb/s routers' byte counters wrap every ~3.4 seconds, so the capacity-planning report built from absolute counter reads over-reports traffic. Defenses: size types by unit and horizon (epoch-millis needs 64 bits from day one; byte counters need 64-bit reads or wrap-aware delta logic), accumulate in the widest type, and add boundary fixtures — 2^31 − 1, 2^31, 2^32 − 1 — to the test matrix.

### What changes when the assumption is removed

Corrected statement: *type width is a function of unit and time horizon, not of how the value feels: multiply the maximum plausible rate or epoch by the retention horizon and pick the type whose limit is beyond it — and treat "two billion" as reachable the moment the unit is small (milliseconds) or the rate is high (line-rate counters).* The corrected habit is writing the horizon next to the declaration: `int64` "holds epoch millis until the year 292 million" — a comment that documents an assumption rather than hiding one.

### Consequences

In interviews, "when will a 32-bit seconds-since-epoch counter overflow, and what about milliseconds?" has the two answers above (2038 and 24.8 days) and reliably separates memorized Y2038 knowledge from actual width reasoning. The incident for the conversion cousin of this family — a 64-bit float forced into a 16-bit signed integer, exploding 37 seconds after lift-off — is the [Ariane 5 casebook chapter](../failure-casebook/ariane-5-1996.md), linked rather than retold here.

## Assumption 4: "My Language Protects Me"

### The taught rule

Modern languages handle overflow: Java defines wraparound, Rust panics on overflow in debug builds, and managed runtimes catch the pathologies C is famous for — so overflow is a C problem, not a problem.

### The hidden assumptions

- *Defined is not detected.* Java's `int` wraps silently by the language specification; the value is deterministic garbage, and `Math.addExact`/`multiplyExact` exist precisely because the default does not interrupt anyone — the developer must opt into the exception at every site that needs it.
- *Safety can be build-mode-dependent.* Rust's documented semantics (the [operator reference](https://doc.rust-lang.org/reference/expressions/operator-expr.html)) are panic-on-overflow in debug builds and two's-complement wrapping in release builds unless `overflow-checks` is enabled — so the test suite exercises stricter arithmetic than production, and a check that "passes in tests" can wrap in the shipped binary.
- *The default is often unchecked.* C# arithmetic is unchecked by default (a `checked` block or project flag opts in), Go's `int` is platform-sized (32-bit on 32-bit platforms), and scripting runtimes demote integers to doubles past 2^53 — the boundary the [serialization-compatibility](serialization-compatibility.md) chapter works through JSON.
- *The boundary is where protection stops:* FFI calls, unsafe blocks, and hardware registers do not carry the language's checks across, so the "safe" language delegates exactly at the interfaces where firmware, drivers, and protocol parsers live.

### Counterexample

A Rust service computes a rolling window of request counts as `total += count` with `count` parsed from a partner API. All tests pass: the debug build panics on any overflow, and the fixtures stay small. In the release build, overflow-checks default off, a partner misconfiguration sends `count = 2,147,483,647` for each of several categories, the accumulator wraps into negative territory, and the window logic — which assumes non-negative counts — starts rejecting all traffic for that tenant. The corrected contract: enable `overflow-checks = true` in release profiles for arithmetic touching external input, use `checked_*`/`saturating_*` operators at parse boundaries, and treat "the language defines the behavior" as a debugging aid, not a correctness guarantee.

### What changes when the assumption is removed

Corrected statement: *a language defines what overflow does — wrap, panic, or nothing detectable — but none of the defaults detect it in production paths unless enabled; the engineer's job is to choose detection per site (checked primitives, sanitizers, release-mode overflow checks) and to remember that the testing build and the shipping build may run different arithmetic.* "It compiles" and "it passes tests" are statements about the test build, and Assumption 4 is the reminder that those are different programs.

### Consequences

"Is overflow a bug in Java/Rust/Go?" is a trick question with a useful answer: the behavior is defined, the detection is optional, and the correctness requirement is the developer's. The chapter's four assumptions compose into a checklist — pre-check instead of post-check, control the computation's type, size types by unit and horizon, enable detection in the shipping build — that maps directly onto any code-review pass over arithmetic that aggregates, multiplies, or timestamps.

## Interview Questions

1. **Why is `if (a + b < 0)` not a valid signed-overflow check in C?** Signed overflow is undefined behavior, so the compiler may assume it never happens and eliminate the impossible-negative branch; the check observes a state the optimizer was told cannot exist. Valid forms: pre-check operands before the operation, or use checked-arithmetic builtins.
2. **Walk through how `width * height * 4` can allocate zero bytes.** In 32-bit arithmetic, 65,536 × 16,384 × 4 is exactly 2^32, which wraps to 0; the allocator returns a zero-length block and writes overrun it. Fix: compute in the widest type with checked multiplication and validate the product against a budget before allocating.
3. **A monitoring dashboard reports impossible traffic spikes every ~34 seconds on a 1 Gb/s link. Diagnose.** A 32-bit octet counter wrapping every 2^32 bytes — about 34 s at 125 MB/s — with delta logic that does not handle wrap. Fix: 64-bit counters or wrap-aware deltas with a wrap-configuration flag.
4. **Java defines wraparound and Rust panics in debug — so is overflow handled?** Defined behavior is not detection: Java wraps silently unless `addExact`/`multiplyExact` are used at each site; Rust's release build wraps unless `overflow-checks` is on. Handled means detected in the shipping build, which is an opt-in engineering decision.

## Key Takeaways

- Signed overflow in C and C++ is undefined behavior, not wraparound; post-hoc overflow checks are deletable, so safety must come from pre-checks and checked-arithmetic primitives.
- Unsigned is defined, not safe: promotion, signed-unsigned comparison conversion, and intermediate width act before the declared type; `-1 > 1u` is true and `size() - 1` on an empty container is a trap.
- Type width follows unit and horizon: epoch-millis exhausted `int32` in 24.8 days, seconds-since-epoch dies in 2038, and line-rate byte counters wrap in seconds — none of which a functional test notices.
- Language defaults define but rarely detect overflow; release builds can run looser arithmetic than test builds, so detection must be enabled where input is untrusted.
- The composing checklist: pre-check, widest-type computation with checked primitives, width chosen by unit-and-horizon arithmetic, and sanitizer or overflow-check enforcement in CI and release.

## Cross-References

- [Floating-point assumptions](floating-point.md) — the neighboring numerics audit: IEEE 754 precision and rounding, the deliberate boundary of this chapter.
- [Input constraints](input-constraints.md) — the overflow-safe midpoint and int-sized sums of algorithm code, the original member of this assumption family.
- [Memory model](memory-model.md) — undefined behavior as a language-semantics concept, the mechanism that turns overflow into an optimizer license.
- [Serialization and compatibility](serialization-compatibility.md) — the 2^53 double-precision boundary where JavaScript demotes integers arriving over JSON.
- [Failure casebook: Ariane 5, 1996](../failure-casebook/ariane-5-1996.md) — the canonical conversion-overflow incident, linked rather than retold.
- The C11 [N1570 draft](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf) (expression evaluation and undefined behavior), the [Java Math API](https://docs.oracle.com/javase/8/docs/api/java/lang/Math.html) (`addExact`/`multiplyExact`), the [Rust operator reference](https://doc.rust-lang.org/reference/expressions/operator-expr.html) (overflow semantics by build mode), [CWE-190](https://cwe.mitre.org/data/definitions/190.html), and the [UndefinedBehaviorSanitizer](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html) documentation are the primary sources above; all were fetched and verified this session.
