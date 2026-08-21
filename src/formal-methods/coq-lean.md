# Coq and Lean: Interactive Theorem Provers

## Overview

Coq and Lean are **interactive theorem provers** (also called proof assistants). They sit at the rigorous end of the formal-methods spectrum: a Coq or Lean proof is a fully machine-checked construction in a typed λ-calculus, and the type checker is small enough to be trusted. Unlike model checkers (which enumerate finite state spaces) or SMT solvers (which decide fragments of first-order logic), proof assistants let you reason about *unbounded* structures — arbitrary-length lists, infinite trees, real numbers, programming-language semantics — because the proof is a piece of syntax that is checked for type-correctness, not a search that terminates.

This page covers: the **Calculus of Inductive Constructions** (CIC), the **tactic** system, the **proof state**, **Gallina** (Coq's programming language), **extraction** to OCaml/Haskell, **Lean 4's** dependent type theory and **mathlib**, and the comparative position of the two systems.

## The Calculus of Inductive Constructions

Coq's foundational logic is the **Calculus of Inductive Constructions** (CIC), a dependent type theory. "Dependent" means types can depend on values: the type `Vec A n` of length-`n` vectors of `A`s is well-formed, and `concat : Vec A n -> Vec A m -> Vec A (n + m)` is a function whose return type contains a *computation* on its arguments (`n + m`). This is dramatically more expressive than the type systems of ML or Haskell, where types cannot mention values.

The three core ingredients of CIC:

1. **Dependent products** `∀ x : A, B(x)` (written `forall x : A, B x` in Coq). These generalize both function types `A -> B` (when `B` doesn't depend on `x`) and logical universal quantification (under the Curry-Howard correspondence, `∀` *is* `Π`).
2. **Dependent sums** `Σ x : A, B(x)` — pairs where the second component's type depends on the first's value. Under Curry-Howard this is existential quantification.
3. **Inductive definitions** — strictly positive recursive definitions of types, à la ML but generalized to indexed families. `nat`, `list`, `vec`, and the syntax trees of an embedded programming language are all defined inductively.

```
Inductive nat : Set :=
| O  : nat
| S  : nat -> nat.

Inductive vec (A : Type) : nat -> Type :=
| vnil  : vec A 0
| vcons : A -> forall n, vec A n -> vec A (S n).
```

Crucially, in `vec A n` the `n` is an *index*, not a parameter — the constructors produce vectors of *different* lengths, so the type family `vec A` ranges over length-indexed types. Pattern-matching on a `vec A (S n)` lets Coq's dependent elimination refine the type: matching `vcons x m xs` gives you a value `xs : vec A m`, and matching `vnil` is impossible (since `vnil : vec A 0` ≠ `vec A (S n)` by type-checking alone).

Soundness of CIC rests on two properties: **normalization** (every well-typed term reduces to a normal form — this guarantees that type-checking terminates) and **consistency** (no term inhabits the empty type `False`, equivalently no proof of `False` exists). These are non-trivial metatheorems; Coq's kernel (the small type checker that is the trusted computing base) has been verified by extraction to OCaml and re-checking, and is the subject of ongoing work in projects like MetaCoq.

## The Proof State and the Tactic System

A Coq proof is constructed by *tactics* that operate on the **proof state**. The proof state is a stack of goals, where each goal is a triple `(hypotheses : context, conclusion : type)`. At any point during a proof you see something like:

```
1 subgoal (ID 47)

n, m : nat
IHn : n + 0 = n
============================
n + S m = S (n + m)
```

The top horizontal line separates the **context** (locally bound variables and hypotheses) from the **conclusion** (the type you must construct a term of). Tactics transform the proof state; some close goals, some create new ones.

### The core tactic vocabulary

| Tactic | Effect |
|--------|--------|
| `intro x` | Moves the leading `∀` quantifier (or `->` antecedent) into the context as hypothesis `x` |
| `apply H` | Uses `H : A -> B` against a goal `B`; produces a new subgoal `A` |
| `exact t` | Closes the goal by providing the term `t` of the right type |
| `simpl` | Performs definitional unfolding and iota reduction |
| `induction x` | Performs induction on `x`; produces one subgoal per constructor of its type |
| `rewrite H` | Uses an equation `H : a = b` to replace `a` with `b` in the goal |
| `destruct x` | Case-splits on `x` (non-recursive; useful on booleans, finite enums) |
| `reflexivity` | Closes a goal of the form `t = t` after definitional reduction |
| `inversion H` | Derives consequences from the constructor shape of an inductive hypothesis |
| `ring` / `lia` / `nia` | Closes goals over commutative rings / linear / nonlinear integer arithmetic by reflection to decision procedures |

A complete proof of addition commutativity in Coq:

```coq
Lemma plus_comm : forall n m : nat, n + m = m + n.
Proof.
  intros n m. revert n. induction m as [| m' IHm'].
  - simpl. intros n. rewrite Nat.add_0_r. reflexivity.
  - intros n. simpl. rewrite IHm'. rewrite Nat.add_succ_r. reflexivity.
Qed.
```

The proof produces, behind the scenes, a *proof term* of type `forall n m : nat, n + m = m + n`. You can inspect this term with `Print plus_comm.` — it is a several-hundred-character λ-term in Gallina. The crucial property is that **the proof script is just a way to build a term; the term itself is the proof**, and the kernel checks it independently of any tactic. If a tactic has a bug, the kernel will reject the term it produced.

### Declarative proof style

Coq also supports a more declarative style via the `SSR` (Small Scale Reflection) extension and the `proof`/`qed` mode in MathComp. Lean 4 pushes this further with a tactic monad and proof terms in tactic mode. The trend across both systems is toward readable, scripted proofs with strong automation.

## Gallina: The Programming Language of Coq

**Gallina** is Coq's pure, total functional language. It's the term-language of CIC. You can write ordinary functions:

```coq
Fixpoint length {A : Type} (l : list A) : nat :=
  match l with
  | nil    => O
  | _ :: t => S (length t)
  end.

Definition append {A : Type} (xs ys : list A) : list A :=
  match xs with
  | nil    => ys
  | x :: t => x :: append t ys
  end.
```

A `Fixpoint` must terminate on all inputs — this is enforced by a syntactic check requiring that one argument decreases structurally on every recursive call. Coq's termination checker is conservative; functions that terminate by well-founded recursion (e.g., quicksort with its `length l` measure) must be defined via the `well_founded_fixpoint` machinery or via the `Program Fixpoint`/`Function` commands.

The payoff: every Gallina function is a total mathematical object, and you can prove theorems about it directly. The `length` function above has type `forall A, list A -> nat`, and you can `Theorem length_append : forall A (xs ys : list A), length (append xs ys) = length xs + length ys.` and prove it by induction.

## Extraction to OCaml and Haskell

Because Gallina is total and terminating, it can be *erased* to a pure functional program. Coq's **extraction** mechanism produces OCaml, Haskell, or Scheme code from any Gallina definition. The non-computational parts (proofs, propositions-as-types) are erased; only computational contents survive.

```coq
From Coq Require Extraction.
Extraction Language OCaml.
Extraction "quicksort.ml" quicksort partition.
```

This is the engine behind **CompCert** — the verified C compiler: the compiler is a Gallina function, the correctness theorem is the spec, and extraction produces the executable OCaml that INRIA distributes. Similarly, **CertiCoq** compiles Coq to a verified executable, and the **Verdi** framework for distributed systems (University of Washington) extracts verified Raft and Paxos implementations.

Extraction is not perfect: extracted code can be slow (proofs erase, but the recursion structure is sometimes not tail-call-optimized), and a verified spec is only as good as the spec itself — CompCert's correctness theorem says "the generated assembly has the same observable behavior as the source C," where "observable behavior" is the operational semantics Coq defines for C. Bugs in that semantics would defeat the proof.

## Lean 4 and Mathlib

**Lean** is a newer proof assistant originally developed by Leonardo de Moura at Microsoft Research (2015+). Lean 4 (released 2021+) is a substantial rewrite: Lean is now *self-hosted* (the Lean compiler is itself written in Lean 4), and Lean 4 functions compile to efficient C via LLVM. This makes Lean usable as a general-purpose programming language as well as a theorem prover — a deliberate design goal.

The foundational logic is **dependent type theory** (DTT), similar in spirit to CIC but with several differences:

- **Universes** are handled with non-cumulative, explicitly controlled hierarchy (`Type u`); Lean allows `universe` inference with `max`/`imax` operators.
- **Quotient types** are primitive, which means function extensionality follows for free.
- **Propositional irrelevance**: all proofs of a proposition are definitionally equal — this differs from Coq, where proofs of `x = y` may differ computationally.

```lean
-- A typical Lean 4 proof
theorem List.length_append {α : Type} (xs ys : List α) :
    (xs ++ ys).length = xs.length + ys.length := by
  induction xs with
  | nil => simp
  | cons x xs ih => simp [List.length, Nat.add_comm]; exact ih
```

Lean's killer app is **mathlib4**, a community-driven formalization of mathematics that has grown past 1.5 million lines of Lean code and contains definitions and theorems from analysis, algebra, topology, category theory, number theory, and beyond. Notable milestones:

- **Liquid Tensor Experiment** (2021): Peter Scholze challenged the formalization community to verify a foundational theorem from condensed mathematics; the Lean team completed it in ~6 months, with Scholze confirming the proof matched his intent. https://github.com/leanprover-community/lean-liquid
- **Polynomial Freiman-Ruzman conjecture** (2023+): A big conjecture in additive combinatorics was formalized as part of the Fréchet-proofs effort. https://github.com/teorth/PFR
- **Fermat's Last Theorem** (2024–): An ongoing effort to formalize the Wiles/Taylor-Wiles proof.

Mathlib's strength is that it is *not* a research artifact but a working library: every pull request is automatically verified by continuous-integration, and definitions get refactored and unified as the library grows. This is rare in formal methods — most theorem-prover projects are monolithic.

Lean also has a powerful **tactic monad** and metaprogramming facility: you can write tactics *in Lean itself* (Coq requires Ltac, a separate tactic language, or the separate MetaCoq framework). This has produced a generation of more powerful automation: `aesop` (auto-encoder for search), `polyrith` (polynomial reflection), `mvrcases` (advanced case analysis).

## Coq vs. Lean: Where They Diverge

| Dimension | Coq | Lean 4 |
|-----------|-----|--------|
| **Foundations** | CIC (Calculus of Inductive Constructions); propositions-are-types but proofs can differ computationally | DTT (Dependent Type Theory) with quotient types, propositional irrelevance |
| **Maturity** | 1989+ (Coq V5); CompCert, Iris, VST, MathComp | 2013+ (Lean 1); 2021+ for Lean 4 |
| **Standard library** | Coq stdlib + MathComp; MathComp is mature, well-curated | mathlib4; massive, fast-moving, community-driven |
| **Metaprogramming** | Ltac + ML via OCaml plugins; MetaCoq for quoting | Native — tactics are Lean functions, can be written in Lean |
| **Code generation** | Extraction to OCaml/Haskell/Scheme | Native compiled to C; production-grade performance |
| **UX** | Heavy use of `;` and chained tacticals; reading is hard without practice | Similar style but better tooling (VS Code extension is excellent), better error messages |
| **Industrial users** | Coq (CompCert, VST for C), Meta (FStar derives from Coq's tradition) | Lean used by AWS for s2n, by Veridise for smart contracts, and heavily in formalization research |

A pragmatic heuristic: if your goal is *program verification* (a specific verified artifact — a compiler, an OS kernel, a C library) Coq's 30+ year track record, MathComp's mature library, and VST/Iris mean you should probably use Coq. If your goal is *formalization of mathematics* (proving theorems from a research math paper, building a library of math) Lean 4 + mathlib is currently the strongest platform. If your goal is *teaching* a one-semester course on theorem proving, both work; Software Foundations (Coq) and Theorem Proving in Lean 4 are both excellent starting points.

## Pedagogy: Software Foundations and TPIL

The two canonical textbooks define the standard paths into the systems:

- **Software Foundations** (Benjamin Pierce et al., Penn) is a multi-volume series: *Logical Foundations* (basic Coq), *Programming Language Foundations* (operational semantics, Hoare logic), *Verified Functional Algorithms*, *QuickChick* (property-based testing in Coq), and *Separation Logic Foundations* (using the Iris framework). The pedagogical style is "do every proof yourself"; the books are themselves Coq files that compile. https://softwarefoundations.cis.upenn.edu/
- **Theorem Proving in Lean 4** (Avigad, de Moura, Kong) is the standard Lean entry point, with a focus on dependent type theory and how mathlib is structured. https://lean-lang.org/theorem_proving_in_lean4/

Both texts are free and online, and both are interactive — every example is a checked proof.

## When to Use a Proof Assistant

- You need to reason about an *unbounded* domain — arbitrary-size data, real numbers, programming-language syntax.
- The cost of a bug is extreme (compiler correctness, cryptographic protocol proofs, kernel verification).
- You want an *artifact*: a machine-checked proof term that survives refactoring and reviewer scrutiny.
- You can afford the proof effort (days to weeks for a non-trivial theorem; months for a full system).

You probably should not reach for a proof assistant when: the property can be expressed as a finite-state invariant (use TLA+ or a model checker), or the property is decidable by an SMT theory (use Z3/CVC5), or the team has no theorem-proving expertise and the timeline is months not years.

## References

- Benjamin Pierce et al. *Software Foundations* series. https://softwarefoundations.cis.upenn.edu/
- The Coq Development Team. *The Coq Reference Manual*. https://coq.inria.fr/doc/
- Yves Bertot and Pierre Castéran. *Interactive Theorem Proving and Program Development — Coq'Art*. Springer, 2004. The classical textbook; https://www.labri.fr/perso/casteran/CoqArt/
- The Coq standard library and MathComp documentation. https://math-comp.github.io/docs/
- Leonardo de Moura, Jeremy Avigad, et al. *Theorem Proving in Lean 4*. https://lean-lang.org/theorem_proving_in_lean4/
- The mathlib4 documentation and community pages. https://leanprover-community.github.io/ and https://leanprover-community.github.io/mathlib4_docs/
- The Liquid Tensor Experiment — Peter Scholze's challenge problem and the formalization account. https://xenaproject.wordpress.com/
- Lean 4 reference and source. https://github.com/leanprover/lean4
