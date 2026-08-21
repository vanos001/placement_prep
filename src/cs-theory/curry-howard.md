# The Curry–Howard Correspondence — Proofs as Programs, Propositions as Types

## Overview

The Curry–Howard correspondence is the observation that, under a suitable reading, intuitionistic logic and typed λ-calculus are *the same thing*: every proposition is a type, every proof is a program, proof normalization is computation, and the cut-elimination theorem of Gentzen corresponds to the β-reduction of the λ-calculus. The correspondence was first noticed implicitly by Haskell Curry in the 1930s (the *Curry* half) and made explicit by William Howard in a 1969 manuscript, finally published in 1980 as *The Formulae-as-Types Notion of Construction*. The cleanest statement is:

```
   Logic                     Programming
─────────────────────────────────────────────
   propositions              types
   proofs                    programs (terms)
   proof normalization       evaluation (β-reduction)
   hypothesis in context     free variable in scope
   implication A → B         function type A → B
   conjunction A ∧ B         product type A × B
   disjunction A ∨ B         sum type A + B
   truth ⊤                   unit type ()
   falsity ⊥                 empty type (no values)
   ∀x.P(x)                   polymorphic type ∀α. τ
   ∃x.P(x)                   dependent pair Σ(x:τ). P(x)
   cut (modus ponens)        application (→E)
   implication introduction  abstraction (→I)
```

The correspondence is not a coincidence or an analogy; it is an isomorphism in the precise sense that a proof in intuitionistic logic can be read as a typed program and vice versa. Different logics give different programming languages: STLC ↔ intuitionistic propositional logic; System F ↔ second-order propositional logic; the Calculus of Constructions ↔ higher-order logic; Martin-Löf type theory ↔ intuitionistic first-order logic with the propositions-as-types reading taken at face value. The correspondence also extends to classical logic via control operators (call/cc) and to linear logic via linear type systems.

> Related: [Lambda Calculus](./lambda-calculus.md), [Logic](./logic.md), [Proof Techniques](./proofs.md), [Programming Language Theory](./programming-language-theory.md), [Formal Methods](./formal-methods.md)

## STLC ↔ Intuitionistic Propositional Logic

The simply-typed λ-calculus has only implication as a connective, and its three typing rules correspond exactly to the three logical rules of intuitionistic implication:

```
Implication introduction (→I):       Implication elimination (→E, modus ponens):

 Γ, x : A ⊢ M : B                    Γ ⊢ M : A → B      Γ ⊢ N : A
──────────────────────              ──────────────────────────────
 Γ ⊢ λx. M : A → B                  Γ ⊢ M N : B
```

Read the introduction rule as: to prove `A → B`, assume A (introduce x : A into the context) and derive B (build M : B). Read the elimination rule as: from a proof of `A → B` and a proof of A, conclude B — modus ponens.

The Curry–Howard reading extends to all the other propositional connectives. Each connective has an introduction rule (construct a value of that type) and an elimination rule (use a value of that type), and these correspond exactly to natural-deduction rules in intuitionistic logic:

### Conjunction ∧ ↔ Product type ×

```
Γ ⊢ M : A      Γ ⊢ N : B              Γ ⊢ P : A ∧ B
───────────────────────── (∧I)        ──────────────── (∧E₁)
   Γ ⊢ (M, N) : A ∧ B                  Γ ⊢ π₁ P : A
                                      ──────────────── (∧E₂)
                                       Γ ⊢ π₂ P : B
```

A proof of `A ∧ B` is a pair `(M, N)` of proofs. Elimination extracts either component via `π₁` or `π₂`. In code: `fst (M, N) = M`, `snd (M, N) = N`.

### Disjunction ∨ ↔ Sum type +

```
        Γ ⊢ M : A                       Γ ⊢ N : B           Γ ⊢ P : A ∨ B    Γ, x:A ⊢ M₁ : C    Γ, y:B ⊢ M₂ : C
       ────────────── (∨I₁)            ────────────── (∨I₂) ────────────────────────────────────────────────────────── (∨E)
        Γ ⊢ inl M : A ∨ B              Γ ⊢ inr N : A ∨ B     Γ ⊢ case P of { inl x → M₁; inr y → M₂ } : C
```

A proof of `A ∨ B` is either a proof of A (tagged `inl`) or a proof of B (tagged `inr`). Elimination is the case analysis: to use a disjunction to prove C, you must handle both branches.

### Truth ⊤ ↔ Unit type

`⊤` is the trivially provable proposition; the unit type has a single value `()`. The introduction rule has no premises; there is no elimination rule because `⊤` carries no information.

### Falsity ⊥ ↔ Empty type (Void)

`⊥` is the unprovable proposition; the empty type has no values. There is no introduction rule. The elimination rule — *ex falso quodlibet* — is the absurd case: from a proof of ⊥, conclude anything:

```
        Γ ⊢ M : ⊥
       ───────────── (⊥E)
        Γ ⊢ absurd C : C
```

Operationally, an empty type value can be matched against to produce any type — this is the `never` (Rust), `Bottom` (Scala), or `absurd` (OCaml) pattern.

### Negation ¬A ↔ Function type A → ⊥

Negation is *defined* as `¬A := A → ⊥`. To prove ¬A, assume A and derive a contradiction. To use a proof of ¬A, give it a proof of A and receive ⊥ (which can be eliminated to anything). The law of excluded middle `A ∨ ¬A` is *not* provable in intuitionistic logic — the corresponding inhabitant would require knowing which side of the disjunction holds, which is undecidable in general. Classical logic adds it as an axiom (Peirce's law, double-negation elimination); computationally this corresponds to a control operator like `call/cc` that captures the continuation.

## Extension to System F — Universal Quantifier

In second-order intuitionistic propositional logic, one can quantify over propositions: `∀α. P(α)`. Under Curry–Howard, this becomes the polymorphic type `∀α. τ`:

```
       Γ ⊢ M : P                  Γ ⊢ M : ∀α. P
      ─────────────── (∀I)        ───────────────────── (∀E, instantiation)
      Γ ⊢ Λα. M : ∀α. P           Γ ⊢ M [A] : P[α:=A]
```

The introduction rule says: if M proves P *for an arbitrary proposition α* (not appearing free in Γ), then `Λα. M` proves `∀α. P`. The elimination rule instantiates the quantifier at a specific proposition A, giving a proof of `P[α:=A]`.

Girard showed System F is strongly normalizing — every well-typed polymorphic program terminates. But polymorphism comes at a price: type reconstruction (deciding if an untyped term has a System F type) is **undecidable** (Wells 1999). Hindley–Milner-Damas is a conservative decidable fragment, the basis of ML and Haskell's `let`-polymorphism.

The polymorphic identity `Λα. λx:α. x : ∀α. α → α` is the proof of the tautology `∀α. α → α` — every proposition implies itself. The boolean values are expressible in pure System F (Church booleans), but the boolean *type* is not: `Bool` is defined as `∀α. α → α → α`, the parametricity result that any function of this type is either `Λα. λt. λe. t` or `Λα. λt. λe. e`. This is **Reynolds' parametricity** (1983), the basis of abstract interpretation and free theorems (Wadler 1989).

## Extension to Dependent Types — Proofs as First-Class

Dependent types are types that depend on values, not just other types. The three constructions of Martin-Löf type theory (1972) are:

```
Π-types (dependent functions):  Π(x:A). B(x)       -- like ∀ but A is a type, B depends on the value
Σ-types (dependent pairs):       Σ(x:A). B(x)       -- like ∃ but B depends on the value
Identity types:                  x =_A y            -- the proposition that x and y are equal
```

The Π-type generalizes both `∀` (when A is a universe of types) and the function arrow `A → B` (when B doesn't actually depend on x). A dependent function takes an argument x : A and returns a value of type B(x) — the return type can vary with the input value. The canonical example is `replicate : Π(n:Nat). A → Vec A n` — replicate n takes a value and returns a vector of length exactly n. The *length* is in the type.

Σ-types are dependent pairs: a value `(x, p)` where x : A and p : B(x). For instance, `(n : Nat, p : IsPrime n)` is a dependent pair — a number paired with a proof it's prime. Σ-types encode *existence*: `∃x:A. P(x)` is read as the type of pairs `(x, p)` with x : A and p : P(x); proving existence means constructing such a pair.

Identity types `x =_A y` turn equality into a type. To prove `x = y` is to inhabit the type `x =_A y`. The canonical proof is `refl : x =_A x` (reflexivity). Non-trivial proofs use congruence (`f x =_B f y` follows from `x =_A y`), symmetry, transitivity, and induction. In Homotopy Type Theory (Voevodsky et al. 2013), identity types are interpreted as paths in a space, and equality becomes equivalent to homotopy — the foundation of "univalent" foundations.

In **proof assistants** (Coq, Lean, Agda, Idris), the programmer writes proofs as ordinary code. A theorem is a type signature; a proof is an inhabitant. The compiler's type checker is the proof checker. Examples: CompCert (a verified C compiler, 100k lines of Coq), the C++ standard library's `std::sort` proof of correctness in Lean, and the `mathlib` library of formalized mathematics (Lean, 1.5M lines).

## The Link to Category Theory — Cartesian Closed Categories

The categorical semantics of STLC is a **Cartesian Closed Category** (CCC): a category C with finite products (for ∧, ×, ⊤) and exponentials (for →, implication). An exponential `B^A` (also written `A ⇒ B`) is, by the universal property, the type of morphisms A → B. Concretely:

- **Products** `A × B` model conjunction and pairing: morphisms `A → B` and `A → C` give `A → B × C` (universal property of the product).
- **Exponentials** `B^A` (or `[A, B]`) model implication and function spaces: morphisms `A × C → B` are in bijection with morphisms `C → B^A` (currying).
- **Terminal object** 1 models ⊤ and the unit type.

The Curry–Howard–Lambek correspondence is the三方 isomorphism: intuitionistic propositional logic ≡ STLC ≡ CCCs. Each side of the triangle — logic, programming, category — gives a different perspective on the same mathematical structure. Linear logic adds a different categorical structure (symmetric monoidal closed categories), and classical logic corresponds to control categories (Selinger 2001).

## Implications for Program Verification

The correspondence is not merely theoretical; it has reshaped how software correctness is approached.

**1. Type systems are lightweight proof systems.** Every type checker rejects programs that would fail a proof rule. The typed `λ` calculus' strong normalization theorem ensures typed programs terminate. ML, Haskell, Rust, OCaml, TypeScript all exploit this: a well-typed program cannot have a "void"-typed value, cannot apply a non-function, cannot confuse a string with an integer. Rust's affine types (ownership) prove *memory safety* — the absence of use-after-free, double-free, and data races — at type-checking time.

**2. Dependent types enable full specification.** A function `sort : List A → List A` has only a partial specification (output is a list of A). A dependent version `sort : (l : List A) → Σ(l' : List A). Permutation l l' ∧ Sorted l'` proves the output is a permutation of the input *and* is sorted. The type signature *is* the specification, and a value of that type is a verified implementation.

**3. Proof assistants are scalable.** The four color theorem (Gonthier 2005, Coq), the Feit–Thompson theorem (odd-order group classification, Gonthier et al. 2012, Coq, 170k lines), and the Kepler conjecture (Hales 2014, Flyspeck project, Coq+Isabelle/HOL) have all been mechanically verified. The RocketFleet verified distributed system (CompCertVM, AWS s2n-TLS's use of HOL Light) demonstrate that production code can carry machine-checked proofs. Microsoft's Everest project verified the cryptographic primitives in the HTTPS stack.

**4. The "logical relations" technique** (Tait 1967, Girard 1972) for proving strong normalization in typed λ-calculi is the basis of the abstraction theorem (Reynolds 1983), parametricity, and free theorems — tools that let us derive program properties from types alone. The classical example: any function `f : ∀α. α → α` is the identity, *proved from the type alone* — no inspection of the body is needed.

The flip side: the correspondence explains why total functional programming is hard. Turing-completeness requires either non-termination (untyped λ-calculus) or non-strongly-normalizing types (STLC + recursion, ML/Haskell). Strict totality (Idris 1, Agda) places hard limits on what can be expressed — unbounded recursion must be encoded with coinductive types or well-founded recursion.

## Interview Questions

**Q: State the Curry–Howard correspondence for implication.**
A: A proof of `A → B` (implication) is a program of type `A → B` (function). The introduction rule (assume A, derive B) is λ-abstraction; the elimination rule (modus ponens) is function application. The proof normalization (cut elimination) corresponds to β-reduction. The correspondence is an isomorphism: a proof is a program, and the program's evaluation is the proof's normalization.

**Q: How does Curry–Howard extend to conjunction and disjunction?**
A: Conjunction `A ∧ B` is the product type `A × B`; a proof is a pair `(M, N)` and elimination is projection. Disjunction `A ∨ B` is the sum type `A + B`; a proof is either `inl M` or `inr N` and elimination is case analysis. Falsity `⊥` is the empty type with no values, and ex falso quodlibet is the absurd case matching any return type.

**Q: What does System F add, and what's the catch?**
A: System F adds universal quantification over types `∀α. τ`, enabling polymorphism (e.g., `id : ∀α. α → α`). It corresponds to second-order propositional logic. It is strongly normalizing (every program terminates) but type reconstruction is undecidable (Wells 1999); Hindley–Milner-Damas is the practical, decidable fragment used by ML and Haskell.

**Q: What is a Cartesian Closed Category and why does it matter?**
A: A CCC is a category with finite products and exponentials — products model pairing/conjunction, exponentials model function spaces/implication. The Curry–Howard–Lambek correspondence says intuitionistic propositional logic, STLC, and CCCs are equivalent presentations of the same structure. Different categories give different logics (e.g., a topos is essentially a CCC with subobject classifier = a model of intuitionistic set theory).

## References

- [Wadler, *Proofs are Programs: 1933–1946* (2015)](https://homepages.inf.ed.ac.uk/wadler/papers/frege/frege.pdf) — Wadler's historical account of Curry, Howard, and the parallel development of logic and programming.
- [Girard, Taylor, & Silva, *Proofs and Types* (Cambridge UP, 1989)](http://www.paultaylor.eu/stable/Proofs+Types.html) — System F, strong normalization, the beginnings of linear logic.
- [Sørensen & Urzyczyn, *Lectures on the Curry–Howard Isomorphism* (Elsevier, 2006)](https://www.cambridge.org/core/books/lectures-on-the-curryhoward-isomorphism/) — the comprehensive textbook, covering classical, intuitionistic, and linear variants.
- [Pierce, *Types and Programming Languages* (MIT Press, 2002)](https://www.cis.upenn.edu/~bcpierce/tapl/) — introductory textbook; chapters 9–12 cover STLC + Curry–Howard.
- [Howard, *The Formulae-as-Types Notion of Construction* (1969, published 1980)](https://doi.org/10.1007/978-3-642-66200-5_8) — the founding paper of the explicit correspondence.
- [Lambek & Scott, *Introduction to Higher-Order Categorical Logic* (Cambridge UP, 1986)](https://www.cambridge.org/core/books/introduction-to-higherorder-categorical-logic/) — the categorical side of Curry–Howard–Lambek.
- [The HoTT Book, *Homotopy Type Theory: Univalent Foundations* (2013)](https://homotopytypetheory.org/book/) — extends identity types to homotopy; equality as path.
- See also: [Lambda Calculus](./lambda-calculus.md), [Logic](./logic.md), [Proof Techniques](./proofs.md), [Programming Language Theory](./programming-language-theory.md), [Formal Methods](./formal-methods.md)
