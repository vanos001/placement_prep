# Proof Techniques

## Direct Proof

Assume P is true, prove Q is true.

**Example**: Prove "if n is even, then n² is even."
- Assume n is even: n = 2k for some integer k
- Then n² = (2k)² = 4k² = 2(2k²)
- Since 2k² is an integer, n² is even. ∎

## Proof by Contrapositive

To prove P→Q, prove the equivalent ¬Q→¬P.

**Example**: Prove "if n² is odd, then n is odd."
- Contrapositive: "if n is even, then n² is even"
- This is the direct proof above. ∎

## Proof by Contradiction

Assume the statement is false, derive a contradiction.

**Example**: Prove √2 is irrational.
- Assume √2 = p/q where p/q is in lowest terms
- Then 2 = p²/q², so p² = 2q²
- Thus p² is even, so p is even: p = 2k
- Then (2k)² = 2q² → 2k² = q² → q is even
- But then p/q is not in lowest terms — contradiction! ∎

## Mathematical Induction

Prove P(n) for all n ≥ n₀:

1. **Base case**: Prove P(n₀)
2. **Inductive step**: Assume P(k) (inductive hypothesis), prove P(k+1)

**Example**: Prove 1+2+...+n = n(n+1)/2
- Base: n=1: 1 = 1(2)/2 ✓
- Assume: 1+2+...+k = k(k+1)/2
- Prove: 1+2+...+k+(k+1) = (k+1)(k+2)/2
  - = k(k+1)/2 + (k+1)
  - = (k+1)(k/2 + 1)
  - = (k+1)(k+2)/2 ✓ ∎

## Strong Induction

Assume P(n₀), P(n₀+1), ..., P(k) are all true, prove P(k+1).

**Example**: Every integer ≥ 2 has a prime factor.
- Base: 2 is prime, so it has a prime factor (itself).
- Assume true for all integers from 2 to k.
- If k+1 is prime, done. If composite, k+1 = ab where 2 ≤ a,b ≤ k.
- By hypothesis, a has a prime factor. This divides k+1. ∎

## Pigeonhole Principle

If n items are placed into m containers and n > m, then at least one container has more than one item.

**Applications**:
- In any group of 13 people, at least 2 share a birth month
- If you pick 5 numbers from {1,2,3,4}, at least two are equal
- Hash collisions are guaranteed when |keys| > |buckets|

## Proof by Construction

Prove existence by constructing an example.

**Example**: Prove there exists an irrational number whose square is rational.
- Construct: x = √2 (irrational)
- x² = 2 (rational) ∎

## Common Mistakes in Induction

| Mistake | Example |
|---|---|
| Skipping base case | "Assume P(k), prove P(k+1)" without verifying P(0) |
| Circular reasoning | Using what you're trying to prove in the inductive step |
| Wrong base case | Proving for n=1 when the claim is for n≥0 |
| Weak hypothesis | Only assuming P(k) when you need strong induction |

## Interview Questions

**Q: When would you use strong induction vs regular induction?**
A: When the inductive step needs more than just P(k). Example: proving every integer ≥ 2 is a product of primes requires knowing the factorization of numbers smaller than k+1, not just k.

**Q: Use the pigeonhole principle to prove that in any group of 367 people, at least two share a birthday.**
A: There are 366 possible birthdays (including Feb 29). With 367 people and 366 possible birthdays, by the pigeonhole principle, at least two people must share a birthday.

## References

- [MIT OCW 6.042J — Mathematics for CS](https://ocw.mit.edu/courses/6-042j-mathematics-for-computer-science-fall-2010/)
- [How to Prove It — Velleman](https://www.cambridge.org/core/books/how-to-prove-it/50ED02D5B4D2B3B3B3B3B3B3B3B3B3B3)
