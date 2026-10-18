# Floating-Point Assumptions: What "It's Just a Number" Silently Promises

## Overview

Two rules are taught together and quietly smuggle in each other's failures: "a double stores decimal numbers" and "a == b compares values". Neither is true as stated. An IEEE 754 binary double stores a rational number whose denominator is a power of two, and a decimal literal such as `0.1` is silently replaced by the nearest such fraction — which is not 0.1. Equality then compares those stored binary values, not the decimal numbers you intended, so `0.1 + 0.2 == 0.3` evaluates to false on every mainstream platform, while `NaN == NaN` is false by definition even for the NaN against itself.

This chapter audits the family of assumptions behind those two rules using the collection's five-step pattern. Everything numeric in the counterexamples below was verified against a real IEEE 754 implementation (Python 3.12, which exposes the exact stored values through `Decimal(float)` and hex bit patterns through `struct`), so every number quoted here is reproducible, not illustrative. The general reference for the mathematics is Goldberg's classic paper, "What Every Computer Scientist Should Know About Floating-Point Arithmetic", hosted by Oracle and linked in the ledger.

## Assumption 1: "The Double Stores the Number I Wrote"

### The taught rule

Assign `0.1` to a double; arithmetic and comparisons involving it behave as they would for the decimal number 0.1.

### The hidden assumptions

- Every decimal literal is rounded to the nearest representable binary fraction with a 53-bit significand. Decimal fractions whose denominators are not powers of two (0.1, 0.2, 0.3, 0.01, ...) are never exactly representable.
- The value you see printed is the *shortest string that round-trips back to the same double*, not the stored value. The display layer is doing you a favor the arithmetic does not honor.
- Parsing and printing are symmetric in practice, so the gap between stored value and printed value is invisible until two different computations produce doubles that print the same but differ by one unit in the last place (ulp), or until a stored value is serialized to a format that preserves full precision (hex, exact decimal) and compared with a decimal expectation.

### Counterexample

The double nearest to 0.1 has bit pattern `0x3FB999999999999A` and its exact value is 0.1000000000000000055511151231257827..., slightly *above* 0.1. The double for 0.3 is 0.29999999999999998889776975374843..., slightly *below* 0.3. Adding the stored 0.1 and 0.2 rounds again, producing bit pattern `0x3FD3333333333334` — one ulp above the double for 0.3, which is `0x3FD3333333333333`. Hence `0.1 + 0.2 == 0.3` is false, and the stored sum's exact value is 0.30000000000000004440892098500626..., which is why it prints as `0.30000000000000004`. Nothing in this chain is an error; every step is the correctly rounded result of a computation on correctly rounded inputs.

### What changes when the assumption is removed

Corrected statement: *a binary floating-point variable stores the nearest binary fraction to the number you wrote; the number itself is almost never stored.* When the decimal semantics are the point — money, contractual quantities, measurement units mandated in decimal — use a decimal type (`decimal.Decimal`, `BigDecimal`, SQL `DECIMAL`) or scaled integers, and let binary floats remain the domain of measurement and approximation.

### Consequences

This is the assumption behind the majority of "why is my total 0.30000000000000004" bugs. In interviews, walking an interviewer through *why* the sum rounds upward (0.1 stored high, 0.3 stored low, one final rounding) is a far stronger signal than reciting "floating point is imprecise".

## Assumption 2: "a == b Compares Values" (Equality, Epsilon, and NaN)

### The taught rule

Use `==` to compare numbers; two numbers that are equal will compare equal.

### The hidden assumptions

- `==` compares the stored binary values. Two results that are mathematically equal but computed by different routes can differ by an ulp or more.
- IEEE 754 mandates that NaN compares unequal to *everything*, including itself — so the invariant `x == x`, used by code that deduplicates, validates, or searches, is false for NaN.
- Language runtimes add their own subtleties on top of IEEE 754: Python's `dict` and `set` find an entry by identity first and equality second, so the *same* NaN object works as a key but a freshly created, bit-identical NaN does not; Java's `Double.equals` compares bit patterns, so NaN behaves in collections while raw `==` still fails.

### Counterexample

All of the following were executed and are reproducible. First, `abs((0.1 + 0.2) - 0.3)` is `5.551115123125783e-17` — tiny, but any code comparing with `==` fails, and any code comparing with a *fixed* absolute epsilon chosen too small (say `1e-18`) fails as well. Second, `float('nan') != float('nan')` is true, so `[1.0, float('nan'), 2.0].index(float('nan'))` raises `ValueError` — the value is right there in the list — and `d.get(float('nan'))` misses an entry stored under a different NaN object. In C++, `std::find` and `std::unordered_set<double>` on NaN have the same failure, since they delegate to `==`. A deduplication pass or a memoization cache keyed on floating-point results silently loses or duplicates NaN entries.

### What changes when the assumption is removed

Corrected statement: *floating-point equality is a relation on stored binary values, not on mathematical values; compare with a tolerance chosen relative to the magnitude involved, and treat NaN as a first-class case.* The standard idiom is `abs(a - b) <= eps * max(abs(a), abs(b))` (a relative tolerance) or a library predicate built for the purpose — Python's `math.isclose`, whose semantics were specified in PEP 485 and which deliberately compares relative differences, not absolute ones. For presence checks, use an explicit NaN test (`isnan`) rather than `x == x` self-comparisons, which compilers may optimize or readers may misread.

### Consequences

The epsilon question is a staple interview follow-up ("how would you compare two floats?") precisely because the naive answer — pick a constant like `1e-9` — fails for both very large values (where the rounding error exceeds any fixed constant) and very small ones (where a fixed epsilon declares genuinely different values equal). Explaining *relative* tolerance is the differentiated answer.

## Assumption 3: "Arithmetic Behaves Like School Math" (Associativity and Distribution)

### The taught rule

Reordering or regrouping a sum does not change its value; `(a + b) + c` equals `a + (b + c)`, so compilers, parallel reductions, and hand refactorings may regroup freely.

### The hidden assumptions

- Every floating-point operation rounds its result. Regrouping changes which values get rounded to what, so addition is *not* associative — the algebraic manipulations that make school math (and optimizing compilers, and parallel map-reduce frameworks) correct over the rationals are unsound over floats.
- Numeric literals and accumulators interact with magnitude: adding a small number to a very large one absorbs the small number entirely when it is below half an ulp of the large one.
- Money examples inherit this: three deposits of $0.10 computed in doubles do not equal $0.30 in comparisons, and rounding at display time (`round(x, 2)`) rounds the *stored* value, not the intended one.

### Counterexample

With `a = 1e16`, `b = -1e16`, `c = 1.0`: the left grouping `(a + b) + c` gives `1.0`, while the right grouping `a + (b + c)` gives `0.0` — verified directly. The inner sum `b + c` absorbs the 1 because `ulp(1e16)` is 2.0, so adding 1 to −1e16 rounds back to −1e16. This is the same mechanism that makes parallel reductions non-reproducible: a sum over 10 million values produces different results depending on thread count and partition boundaries, which breaks both bit-exact regression tests and financial reconciliation. On the money side: `0.1 + 0.1 + 0.1` is `0.30000000000000004`, and `round(2.675, 2)` returns `2.67`, not `2.68`, because the stored value of 2.675 is 2.67499999999999982236431605997495353221893310546875 — the half-cent you meant to round up was already gone at parse time.

### What changes when the assumption is removed

Corrected statement: *floating-point addition is neither associative nor distributive; any refactor, compiler optimization, or parallelization that regroups floating-point arithmetic may change results bit-for-bit.* Defenses, in order of strength: use integers or decimals when the arithmetic is really decimal or exact (money in minor units); pin a deterministic evaluation order where reproducibility matters (fixed reduction trees, `-ffp-contract=off`-style flags, sorted accumulation); and treat "the sum came out one ulp different" as an explanation, not a mystery.

### Consequences

Two recurring production shapes: financial reconciliation fails by a rounding error across services that computed the same total with different summation orders, and numerical regression tests flip intermittently after a compiler upgrade or a move to multithreaded BLAS. Both are this assumption failing. In interviews, "is `(a+b)+c == a+(b+c)` for floats?" with a worked example cleanly separates candidates who have been burned (or taught) from those who have only read the syntax.

## Assumption 4: "Precision Is Fine Until It Isn't" (Cancellation, Accumulation, and 2^53)

### The taught rule

Doubles give about 15–16 significant decimal digits, which is "plenty" — so sums of large arrays, roots of quadratic equations, and integer identifiers are all safely within precision.

### The hidden assumptions

- 15–16 significant digits is a statement about *relative* precision. Subtraction of nearly equal quantities (catastrophic cancellation) wipes out leading digits, leaving only the few digits of noise that survived earlier roundings.
- Accumulation is a random walk of rounding errors: summing N terms naively accumulates error that grows with N, and a single term much larger than the rest permanently swallows contributions below its ulp.
- A double's 53-bit significand holds integers exactly only up to 2^53. JSON APIs that ship 64-bit identifiers as numbers deliver doubles to JavaScript clients, and identifiers above 2^53 silently change value.

### Counterexamples

All verified. *Cancellation:* the equation x² − 10⁸x + 1 = 0 has two real roots whose product is 1, so the small root is ≈ 10⁻⁸. The textbook formula computes the small root as `(B - sqrt(B*B - 4)) / 2` with B = 10⁸: the discriminant is `9999999999999996.0` (exactly representable), but its square root rounds to `99999999.99999999` — the double immediately below 10⁸ — and the subtraction of two nearly equal numbers leaves 7.450580596923828e-09, a 25% error on a value computed "exactly". The stable form divides by the large root (`1 / r1`), which returns 1e-08 exactly, exploiting the product-of-roots identity instead of the cancellation. *Accumulation:* summing 10 million copies of 0.1 naively gives 999999.9998389754 (off by 1.6×10⁻⁴); Kahan compensation gives 1000000.0; Python's `math.fsum` gives 1000000.0. But compensation has limits: for the three-element array `[1e20, 1.0, -1e20]`, naive summation gives 0.0, *Kahan also gives 0.0* (the correction term is itself absorbed, since `ulp(1e20)` is 16384), and only full-precision accumulation (`fsum`) returns the correct 1.0. *Integers in doubles:* `float(2**53 + 1)` equals `float(2**53)` — both have bit pattern `0x4340000000000000` — so a JSON response shipping the identifier 9007199254740993 as a number is read by any JavaScript client as 9007199254740992, and no error is raised anywhere.

| Symptom | Underlying assumption broken | Standard defense |
|---|---|---|
| `0.1 + 0.2 != 0.3` | literals stored exactly | decimal types for decimal semantics |
| equality tests flake at extreme magnitudes | `==` on stored bits | relative tolerance (`math.isclose`-style) |
| parallel reduction not bit-reproducible | associativity | fixed reduction order / integers |
| small root of quadratic wrong by 25% | cancellation in subtraction | restructure formula (Goldberg) |
| long-sum error grows with N | naive accumulation | Kahan / pairwise / `fsum` |
| JS reads ID 9007199254740993 as ...992 | integers exact in doubles | serialize IDs as strings |

### What changes when the assumption is removed

Corrected statement: *double precision bounds relative error per operation; error compounds with the computation's condition number, not with naive intuition about "15 digits" — so large sums, ill-conditioned subtraction, and 64-bit identifiers all need a deliberate strategy.* For summation the ladder is: naive (fastest, least accurate), pairwise (what most BLAS libraries do), compensated/Kahan (cheap, fixes accumulation but not single giant swallows), and full-precision accumulation like `fsum` (exact but slower). A telling detail: CPython's built-in `sum()` silently switched to Neumaier compensated summation for floats in 3.12 (per the official What's New in Python 3.12 notes) — the "obvious" one-liner now returns different bits than in 3.11, which is itself a live demonstration that numeric behavior is an API contract that can change under you.

### Consequences

The catastrophic-cancellation quadratic is the canonical numerical-analysis interview question; the 2^53 identifier issue is a standard API-design interview trap (the fix — serialize 64-bit IDs as strings — belongs to the API contract chapter as much as to this one). In production, the accumulation issue most often surfaces as "the same computation gives different results on different machines or thread counts", and the Kahan-also-fails case above is worth remembering: partial fixes have their own boundaries.

## Interview Questions

1. **Why is `0.1 + 0.2 != 0.3`, bit for bit?** 0.1 stores as the double above 0.1 (0x3FB999999999999A), 0.3 stores as the double below 0.3 (0x3FD3333333333333); the correctly rounded sum lands one ulp above the double for 0.3 (0x3FD3333333333334). The exact error is about 5.55×10⁻¹⁷.
2. **How would you compare floating-point results for equality, and why is a fixed epsilon wrong?** Compare relative difference (`abs(a-b) <= eps * max(|a|,|b|)` or a library predicate like `math.isclose`). A fixed epsilon fails both for large magnitudes (error grows with scale) and small ones (distinct values declared equal).
3. **Give a case where Kahan summation still fails.** When one addend is so much larger than the running sum and correction that they are absorbed by rounding: for `[1e20, 1.0, -1e20]` naive and Kahan both give 0.0, while exact accumulation gives 1.0. Compensation fixes error accumulation, not information destroyed below an ulp.
4. **Why do JavaScript clients see corrupted 64-bit IDs from JSON APIs?** JSON numbers parse to doubles; a double holds integers exactly only to 2^53, so 9007199254740993 arrives as 9007199254740992. Fix: transmit IDs as strings or use big-integer parsing.
5. **Your parallel sum is not bit-reproducible across thread counts. Root cause and two fixes?** Floating-point addition is not associative, and different partitions regroup it. Fixes: pin a deterministic reduction order (fixed tree, or accumulate serially), or compute in exact/integer arithmetic where the semantics demand it.

## Key Takeaways

- A binary double stores the nearest power-of-two fraction to your decimal literal — the stored value is almost never the number you wrote, and printing hides the difference.
- `==` compares stored bits: results equal in math can differ by an ulp, and NaN is unequal to itself, breaking equality-based search, dedup, and validation.
- Floating-point addition is not associative; regrouping by compilers, refactorings, or parallel reductions changes results bit-for-bit.
- Relative precision, not absolute: cancellation destroys leading digits, accumulation errors grow with N, and Kahan has boundaries — `[1e20, 1, -1e20]` defeats it.
- Integers above 2^53 do not survive a trip through doubles; serialize 64-bit identifiers as strings.
- For money and other decimal semantics, the fix is representational (integers in minor units, decimal types), not computational care with floats.

## Cross-References

- [Input constraints](input-constraints.md) — the integer-arithmetic cousin: overflow in the midpoint, in-memory inputs, and bounds.
- [Complexity claims](complexity-claims.md) — the RAM model that pretends all these numeric details away.
- [Undefined behavior in C](../../languages/c/undefined-behavior.md) — what the language standard does and does not promise about numeric operations.
- [Computer architecture reference](../../references/computer-architecture.md) — where the 53-bit significand and the FPU live in the hardware stack.
- [API contracts](api-contracts.md) — the 2^53 identifier problem as a contract question, plus pagination and compatibility assumptions.
