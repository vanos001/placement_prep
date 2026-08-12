# Sets, Relations & Functions

## Sets

A set is an unordered collection of distinct elements.

### Set Operations

```
A = {1, 2, 3, 4}
B = {3, 4, 5, 6}

Union:        A ∪ B = {1, 2, 3, 4, 5, 6}
Intersection: A ∩ B = {3, 4}
Difference:   A \ B = {1, 2}
Complement:   A' (everything not in A)
Symmetric:    A △ B = (A\B) ∪ (B\A) = {1, 2, 5, 6}
Cartesian:    A × B = {(1,3), (1,4), ..., (4,6)}
Power set:    P(A) = all subsets of A, |P(A)| = 2^n
```

### Set Laws

- **De Morgan's**: (A∪B)' = A'∩B', (A∩B)' = A'∪B'
- **Distributive**: A∩(B∪C) = (A∩B)∪(A∩C)
- **Absorption**: A∪(A∩B) = A

## Relations

A relation R from A to B is a subset of A × B.

### Properties of Relations on a Set A

| Property | Definition | Example |
|---|---|---|
| Reflexive | ∀a: (a,a) ∈ R | "≤" on integers |
| Symmetric | (a,b) ∈ R → (b,a) ∈ R | "is friend of" |
| Transitive | (a,b)∈R ∧ (b,c)∈R → (a,c)∈R | "is ancestor of" |
| Antisymmetric | (a,b)∈R ∧ (b,a)∈R → a=b | "≤" on integers |
| Equivalence | Reflexive + Symmetric + Transitive | "≡ mod n" |
| Partial Order | Reflexive + Antisymmetric + Transitive | "⊆" on sets |

### Equivalence Classes

If R is an equivalence relation on A, then A is partitioned into equivalence classes:
- [a] = {x ∈ A : (a,x) ∈ R}
- Example: "≡ mod 3" on {0,1,2,3,4,5} → {[0]={0,3}, [1]={1,4}, [2]={2,5}}

## Functions

A function f: A → B maps each element of A to exactly one element of B.

### Function Types

| Type | Definition | Example |
|---|---|---|
| Injective (one-to-one) | f(a)=f(b) → a=b | f(x)=2x on integers |
| Surjective (onto) | ∀b∈B, ∃a: f(a)=b | f(x)=x³ on reals |
| Bijective | Injective + Surjective | f(x)=x+1 on integers |

### Composition

If f: A→B and g: B→C, then g∘f: A→C defined by (g∘f)(x) = g(f(x)).

### Cardinality

- |A| = |B| if there exists a bijection between A and B
- **Countable**: |A| ≤ |ℕ| (integers, rationals are countable)
- **Uncountable**: |A| > |ℕ| (reals are uncountable — Cantor's diagonal argument)

## Interview Questions

**Q: What is an equivalence relation? Give an example.**
A: A relation that is reflexive, symmetric, and transitive. Example: "has the same birthday as" — everyone has their own birthday (reflexive), if A shares B's birthday then B shares A's (symmetric), and it's transitive.

**Q: What is the difference between injective, surjective, and bijective?**
A: Injective: different inputs → different outputs (no collisions). Surjective: every output is hit by some input (no gaps). Bijective: both — a perfect one-to-one correspondence.

## References

- [Discrete Mathematics — Rosen](https://www.mheducation.com/highered/product/discrete-mathematics-applications-rosen/M9780073383095.html)
- [MIT OCW 6.042J — Mathematics for CS](https://ocw.mit.edu/courses/6-042j-mathematics-for-computer-science-fall-2010/)
