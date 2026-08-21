# Dependent Types

Dependent types collapse the wall that the simply-typed lambda calculus (STLC) and Hindley-Milner maintain between *types* and *values*. A type may mention a value: `Vec A n` is the type of lists whose length is statically known to be `n`. Index into it and the bounds check happens at compile time. Append two such vectors and the result has length `m + n`, with the proof carried by the type itself.

This power is not free. Type checking becomes undecidable in general — it reduces to proof checking — so you typically have to write proofs alongside code, and inference is partial at best. The payoff is real: memory safety, security, and correctness properties migrate from runtime into the type system, with machine-checked guarantees.

## Pi types (∏) — dependent functions

A Pi type `∏ (x : A) → B(x)` is the type of functions whose *return type depends on the input value*. When `B` does not mention `x`, the type collapses to the ordinary arrow `A → B`. When it does, you get something like:

```idris
-- The return type Vec A n depends on the input value n.
replicate : (n : Nat) -> a -> Vec a n
replicate 0     _ = []
replicate (S k) x = x :: replicate k x
```

The function's type literally says: give me a length `n` and an element, and I'll return a vector of *exactly* length `n`. The checker verifies that the two branches return `Vec a 0` and `Vec a (S k)` respectively, which under definitional equality of `Nat` addition match the declared return type.

The dependent function space ∏ is the Curry–Howard twin of universal quantification `∀` over a domain — "for all `x : A`, `B(x)` holds." The non-dependent arrow `A → B` is the special case where the body of the `∀` does not mention the bound variable, just as implication `A ⇒ B` is the special case of `∀x:A. B` when `B` does not depend on `x`.

## Sigma types (∑) — dependent pairs

A Sigma type `∑ (x : A) × B(x)` is the type of pairs where the second component's *type* depends on the first component's *value*.

```agda
record Σ {A : Set} (B : A → Set) : Set where
  constructor _,_
  field
    fst : A
    snd : B fst
```

A canonical use is "a list paired with a proof that it is sorted":

```agda
data Sorted : List Nat → Set where
  sorted-[]   : Sorted []
  sorted-[_] : Sorted (x ∷ [])
  sorted-∷   : (x≤y : x ≤ y) → Sorted (y ∷ xs) → Sorted (x ∷ y ∷ xs)

sortedList : Σ (List Nat) Sorted
sortedList = (3 ∷ 5 ∷ 8 ∷ []) , sorted-∷ (s≤s z≤n) (sorted-∷ (s≤s z≤n) sorted-[_])
```

The pair fuses data with a proof about that data. This is impossible in non-dependent type systems, where the pair components must have independent types.

## The workhorse: Vec A n

`Vec` is the gateway example because it shows all three pillars (Pi, Sigma, definitional equality) at once:

```idris
data Vec : Nat -> Type -> Type where
  Nil  : Vec 0 a
  (::) : a -> Vec n a -> Vec (S n) a

head : Vec (S n) a -> a
head (x :: _) = x

tail : Vec (S n) a -> Vec n a
tail (_ :: xs) = xs

(++) : Vec m a -> Vec n a -> Vec (m + n) a
(++) []       ys = ys
(++) (x :: xs) ys = x :: (xs ++ ys)
```

Note that `head` has no `error` or `Maybe` branch for the empty vector — the type `Vec (S n) a` matches only the `(::)` constructor, so the empty case is not even writable. The compiler accepts the function as total.

The `++` case is subtler. In the recursive branch, `xs ++ ys` has type `Vec (m + n) a`, but the type checker must reduce `S m + n` to `S (m + n)` — definitional equality on `Nat`. In Idris 2 and Agda this works because `+` is defined by recursion on the *left* argument, so `S m + n` reduces to `S (m + n)` syntactically. In Lean 4 the same proof works, but if you index by `n + m` instead (recursion on the *right*), you must invoke `Nat.add_comm` because `n + S m` does not reduce.

```
      Pi  (∏)                          Sigma (∑)
      dependent function              dependent pair
  ┌──────────────────────┐         ┌──────────────────────┐
  │ input value influences │         │ first value infl.    │
  │ output type            │         │ second component type│
  │                        │         │                       │
  │ (n : Nat) -> Vec a n   │         │ (xs : List A) × ...   │
  └──────────────────────┘         └──────────────────────┘
```

## Curry–Howard: proofs as programs

The Curry–Howard correspondence identifies logical propositions with types, and proofs with programs. In the non-dependent world:

```
  A ∧ B     ↔   (A, B)            -- product type
  A ∨ B     ↔   Either A B        -- sum type
  A ⇒ B     ↔   A → B             -- function type
  ⊥         ↔   Void              -- empty type
  ⊤         ↔   Unit              -- unit type
  ¬A        ↔   A → Void          -- function into Void
```

Dependent types extend the correspondence to **first-order and higher-order logic**. The proposition "for all `n`, `n + 0 = n`" is the Pi type `∀ (n : Nat), n + 0 = n`. Proving it is writing a program that inhabits the type:

```lean
plus_zero : ∀ (n : Nat), n + 0 = n
plus_zero 0     = rfl
plus_zero (S k) = cong S (plus_zero k)
```

A single artifact serves as both code and proof. The boundary between "library" and "verification system" dissolves — which is why Coq, Agda, Lean, and Idris can be used to formalize mathematics. Lean's `mathlib` is the largest corpus of machine-checked mathematics in existence (>1.5M lines), covering everything from category theory to the four-color theorem prerequisites. The HoTT book formalizes homotopy theory inside dependent type theory, with univalence as a primitive.

## Languages

| Language | Foundation | Era | Distinctive trait |
|----------|------------|-----|-------------------|
| **Coq** | Calculus of Inductive Constructions (CIC) | 1989 | Tactical proof language; `Ltac`/`Ltac2` |
| **Agda** | Martin-Löf type theory (extensional) | 1993 | Direct dependently-typed programming; no tactics |
| **Idris 2** | Quantitative Type Theory (QTT) | 2020 | Multiplicities (0/1/ω) baked into the theory |
| **Lean 4** | CIC + quotient types | 2014 | Best-in-class metaprogramming; large `mathlib` |
| **F\*** | Refinement calculus + dependent types | 2011 | SMT-aided verification; aimed at crypto code |

Quantitative Type Theory (Idris 2) is interesting because it tracks the **multiplicity of variable use** in the type itself, unifying dependent types with linear types. A function with type `(1 x : A) → B` uses `x` exactly once (linear); `(0 x : A) → B` does not use it at all (relevant for proof erasure); `(ω x : A) → B` uses it unrestricted. This subsumes Linear Haskell's `A ⊸ B` and lets you express "this proof must erase to nothing at runtime," which is critical for performance — dependent types without erasure generate enormous proof terms that ship to production.

## Comparison to non-dependent type systems

| Feature | HM / let-poly | Rank-N (GHC) | GADTs | Dependent |
|---------|---------------|---------------|-------|-----------|
| Type depends on value? | No | No | Partially | **Yes** |
| Decidable inference? | Yes (PSPACE) | Rank-2 yes; Rank-ω no | With annotations | **No** (in general) |
| Universe of indices | None | None | `Nat`, `Bool`, finite | Any type |
| Erasure | Trivial | Trivial | Trivial | Requires explicit erasure |
| Practical use | Industry standard | Industry (Haskell) | Haskell, Scala 3 | Math, verified systems |

GADTs (Generalized Algebraic Datatypes, a GHC extension) are the "training wheels" version of dependent types — they let the return type of a constructor vary based on a type index, so `Vec Z a` and `Vec (S n) a` are distinct types, but `n` lives at the *type* level and is not a runtime value. Dependent types collapse this: `n` is a runtime value that the type system can read.

The practical rule of thumb:
- **HM** is what you want for 95% of programs. Decidable inference, fast, predictable.
- **GADTs + TypeFamilies** get you ~80% of dependent typing's expressiveness for inductive invariants (length-indexed lists, typed ASTs, session-typed channels) without losing inference.
- **Full dependent types** are the right tool when you are writing a proof, a verified compiler (CompCert), a verified crypto primitive (HACL\*, libcrux), or a math library (`mathlib`). The overhead is high; reserve it for when the safety guarantee justifies it.

## The tradeoff: definitional vs propositional equality

A subtle but central point is the distinction between **definitional equality** (`≡` by computation; the checker reduces both sides and checks they are syntactically identical) and **propositional equality** (`=` as a type you prove).

```lean
-- Definitional: the type checker reduces both sides.
example : 2 + 2 = 4 := rfl

-- Propositional: requires induction because + recurses on the left.
example : ∀ n, n + 0 = n :=
  by intros n; induction n; ...
```

`2 + 2` reduces to `4` definitionally, so `rfl` works. But `n + 0` does not reduce to `n` because `+` is defined by recursion on the left argument — `n + 0` is stuck when `n` is a variable. So an explicit inductive proof is required. This is the central ergonomic pain of dependent types: the proof burden often falls on what feel like "obvious" facts, because the equation is true but not definitionally true.

Different languages handle this differently:
- **Agda** uses rewrite rules (`--rewrite`) to extend definitional equality beyond the strict definition.
- **Lean** lets you register `simp` lemmas that the elaborator applies during unification, so common algebraic identities are auto-applied.
- **Coq** has `Set Asymmetric Patterns` and `Hint Rewrite`, plus a huge `Lia` decision procedure for arithmetic.
- **Idris 2** lets you mark lemmas as `rewrite` to extend the checker.

## Universe policing: Russell's paradox

Dependent type theory has *types of types*, called universes: `Type 0 : Type 1 : Type 2 : ...`. Without cumulativity or with naive `Type : Type`, you get Girard's paradox (the type-theoretic analogue of Russell's). Every system therefore chooses a universe discipline:

- **Coq/Lean**: `Prop` and `Type` are separate hierarchies; `Type i : Type (i+1)`.
- **Agda**: `Set ℓ : Set (ℓ+1)` with universe levels as first-class; the user writes `Set ℓ` and the checker infers `ℓ`.
- **Idris 2**: Universe levels are implicit; the system inserts fresh universe variables.

Universe inconsistency is the most common source of "this looks like it should type-check, but doesn't" errors in practice.

## Conclusion

Dependent types are the strongest static guarantee mainstream-adjacent type theory offers. They let you write `Vec A n` and get bounds checking for free, `Sorted xs` and get sorted-ness for free, or `n + 0 = n` and get a machine-checked proof. The cost is undecidable inference and frequent explicit proofs of "obvious" facts.

For industry, dependent types are still mostly a research/pre-production tool, used where the math or the security matters more than developer ergonomics — CompCert, seL4's proofs, AWS s2n's verified crypto. GADTs and refinement types cover 80% of practical needs at lower cost. But the `mathlib`-style adoption of Lean shows the curve is bending: more projects are discovering that the proof overhead is acceptable when correctness is non-negotiable.

## References

- The Univalent Foundations Program, *Homotopy Type Theory: Univalent Foundations of Mathematics* (HoTT book), 2013 — https://homotopytypetheory.org/book/
- Idris 2 documentation (Quantitative Type Theory) — https://idris2.readthedocs.io/
- Agda documentation (Martin-Löf type theory, universe levels) — https://agda.readthedocs.io/
- Lean 4 documentation and `mathlib` — https://leanprover.github.io/ and https://leanprover-community.github.io/mathlib4_docs/
- F\* language and tutorial — https://www.fstar-lang.org/
- Coq reference and the Calculus of Inductive Constructions — https://coq.inria.fr/doc/
- A. Chlipala, *Certified Programming with Dependent Types* — https://adam.chlipala.net/cpdt/
- P. Martin-Löf, *Intuitionistic Type Theory* (the original foundation, 1984)
