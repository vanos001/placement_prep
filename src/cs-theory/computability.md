# Computability

## Decidable vs Undecidable

A language L is **decidable** if there exists a Turing machine that halts on every input and correctly accepts/rejects. L is **recognizable** (recursively enumerable) if a TM accepts all strings in L but may loop forever on strings not in L.

| Property | Decidable | Recognizable (but not decidable) | Not recognizable |
|----------|-----------|----------------------------------|-------------------|
| L | TM always halts | TM halts on yes, may loop on no | No TM recognizes L |
| Complement | Decidable | Not recognizable | Recognizable |
| Example | A_DFA | A_TM | ¬A_TM |

## The Halting Problem

**A_TM = { ⟨M, w⟩ | M is a TM that accepts input w }**

A_TM is recognizable but **undecidable**. Proof by diagonalization:

1. Assume A_TM is decidable by TM H.
2. Construct D that on input ⟨M⟩: run H on ⟨M, ⟨M⟩⟩; if H accepts, reject; if H rejects, accept.
3. Run D on ⟨D⟩: D accepts ⟨D⟩ iff D rejects ⟨D⟩ — contradiction.

```
D(⟨M⟩) =
  run H(⟨M, ⟨M⟩⟩)
  if H accepts → REJECT
  if H rejects → ACCEPT

D(⟨D⟩): accepts iff rejects → CONTRADICTION
```

## Reductions

A **mapping reduction** f: Σ* → Σ* is computable and w ∈ A₁ iff f(w) ∈ A₂. If A₁ ≤_m A₂:

- If A₂ is decidable → A₁ is decidable
- If A₁ is undecidable → A₂ is undecidable

Common reduction chain:

```
A_TM (known undecidable)
  ↓ reduce
HALT_TM = {⟨M, w⟩ | M halts on w}
  ↓ reduce
E_TM = {⟨M⟩ | L(M) = ∅}
  ↓ reduce
REGULAR_TM = {⟨M⟩ | L(M) is regular}
  ↓ reduce
EQ_TM = {⟨M₁, M₂⟩ | L(M₁) = L(M₂)}
```

## Rice's Theorem

> Any non-trivial property of the language recognized by a Turing machine is undecidable.

A property P is **non-trivial** if some TMs satisfy it and some don't. Rice's theorem means you cannot decide *anything* interesting about what a program computes: whether it accepts anything, whether it's equivalent to another program, whether it accepts a specific string, etc.

| Property | Decidable? | Reason |
|----------|-----------|--------|
| L(M) = ∅ | No | Rice's theorem |
| L(M) = Σ* | No | Rice's theorem |
| M accepts "hello" | No | Rice's theorem |
| M has ≥ 5 states | Yes | Property of M, not L(M) |
| M runs in O(n²) | Unknown | Open problem |

## Key Undecidable Problems

- **Post Correspondence Problem (PCP)**: Given dominoes with top/bottom strings, can you arrange a sequence where top = bottom?
- **Hilbert's Tenth Problem**: Does a Diophantine equation have integer solutions?
- **Word Problem for Groups**: Given a group presentation, does a word equal the identity?

## Interview Questions

**Q: Why is the halting problem undecidable?**
A: By diagonalization — if a decider H existed, we could build a machine D that contradicts itself when run on its own encoding. D(⟨D⟩) accepts iff it rejects, an impossibility.

**Q: What is Rice's theorem? Give an example.**
A: Rice's theorem states that any non-trivial semantic property of a TM's language is undecidable. Example: determining whether a program accepts any input at all is undecidable, because it's a property of the language, not the machine's syntax.

**Q: How do you use reductions to prove undecidability?**
A: To prove B is undecidable, reduce a known undecidable problem A to B: build a computable function f such that w ∈ A iff f(w) ∈ B. If B were decidable, A would be too — contradiction.

## References

- [Introduction to the Theory of Computation — Sipser](https://www.cengage.com/c/introduction-to-the-theory-of-computation-sipser-3e/)
- [Computability, Complexity, and Languages — Davis, Sigal, Weyuker](https://www.elsevier.com/books/computability-complexity-and-languages/davis/978-0-12-206382-0)
- See also: [Turing Machines](./turing-machines.md), [Complexity Classes](./complexity-classes.md), [Formal Languages](./formal-languages.md)
