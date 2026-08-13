# Logic

## Propositional Logic

### Connectives

| Symbol | Name | Meaning |
|---|---|---|
| ∧ | AND | Both true |
| ∨ | OR | At least one true |
| ¬ | NOT | Negation |
| → | Implication | If P then Q |
| ↔ | Biconditional | P if and only if Q |

### Truth Tables

```
P | Q | P∧Q | P∨Q | P→Q | P↔Q | ¬P
T | T |  T  |  T  |  T  |  T  |  F
T | F |  F  |  T  |  F  |  F  |  F
F | T |  F  |  T  |  T  |  F  |  T
F | F |  F  |  F  |  T  |  T  |  T
```

**Key insight**: P→Q is false ONLY when P is true and Q is false.

### Logical Equivalences

| Name | Law |
|---|---|
| De Morgan's | ¬(P∧Q) = ¬P∨¬Q, ¬(P∨Q) = ¬P∧¬Q |
| Double negation | ¬¬P = P |
| Contrapositive | P→Q = ¬Q→¬P |
| Material conditional | P→Q = ¬P∨Q |
| Distributive | P∧(Q∨R) = (P∧Q)∨(P∧R) |
| Absorption | P∨(P∧Q) = P |

### Tautology, Contradiction, Contingency

- **Tautology**: Always true (e.g., P∨¬P)
- **Contradiction**: Always false (e.g., P∧¬P)
- **Contingency**: Sometimes true, sometimes false

## Predicate Logic

### Quantifiers

- **Universal** (∀): "For all x, P(x)" — ∀x P(x)
- **Existential** (∃): "There exists x such that P(x)" — ∃x P(x)

### Negation of Quantifiers

- ¬(∀x P(x)) = ∃x ¬P(x)
- ¬(∃x P(x)) = ∀x ¬P(x)

### Examples

```
∀x∃y (x + y = 0)     — True (every number has an additive inverse)
∃x∀y (x * y = y)     — True (x = 1, the multiplicative identity)
∀x∀y (x + y = y + x) — True (commutativity of addition)
```

## Interview Questions

**Q: What is the contrapositive of P→Q?**
A: ¬Q→¬P. It's logically equivalent to the original. Example: "If it rains, the ground is wet" has contrapositive "If the ground is not wet, it did not rain."

**Q: Apply De Morgan's law to ¬(A∧B).**
A: ¬A∨¬B. "It's not true that both A and B" means "either A is false or B is false (or both)."

**Q: What is the difference between ∀ and ∃?**
A: ∀ (for all) requires the property to hold for every element. ∃ (there exists) requires at least one element to satisfy the property. ¬∀xP(x) = ∃x¬P(x).

## References

- [Discrete Mathematics — Rosen](https://www.mheducation.com/highered/product/discrete-mathematics-applications-rosen/M9780073383095.html)
