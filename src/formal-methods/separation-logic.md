# Separation Logic: Reasoning about Pointer Programs

## Overview

Hoare logic, the foundation of program verification since 1969, struggles badly with **mutable heap**. The standard Hoare rule for sequential composition requires the precondition of the second command to mention *all* the heap cells the first command might touch, even when those cells are conceptually irrelevant to the second command. The verifier is forced to either (a) write preconditions listing every cell in the program, making modular verification impossible, or (b) abandon frame reasoning altogether and inline everything. Both choices fail on real C: a function `free_node(p)` shouldn't have to know about the entire heap that exists when it's called — it should only need to know that `p` points to a node.

**Separation logic** (O'Hearn, Pym, Yang 2001; Ishtiaq and O'Hearn 2001; Reynolds 2002) fixes this by extending Hoare logic with a new connective, the **separating conjunction** `*`, and a corresponding **frame rule** that lets you carry reasoning about untouched heap from one command to the next. The result is a logic where local, modular reasoning about pointer programs becomes tractable: a `list_reverse` function can be specified and verified in 30 lines of separation logic instead of 300 lines of explicit heap enumeration.

This page covers the separating conjunction, the frame rule, the proof calculus (axiomatic and symbolic), **Iris** (the modern separation-logic framework), and production uses (**VST** for C, **RustBelt** for Rust).

## The Separating Conjunction `*`

Separation logic predicates describe *portions of heap*, not the global heap. A heap is a partial function from locations to values, `h : Loc ⇀ Val`. Predicates `P`, `Q` range over heaps. The key connectives:

| Connective | Meaning |
|------------|---------|
| `emp` | the empty heap (domain is `∅`) |
| `l ↦ v` | a singleton heap with exactly one cell at `l` holding `v` |
| `P * Q` (separating conjunction) | `h` satisfies `P * Q` iff `h` can be split into disjoint parts `h1 ⊎ h2` with `h1 ⊨ P` and `h2 ⊨ Q` |
| `P -* Q` (separating implication / magic wand) | `h ⊨ P -* Q` iff for any `h'` disjoint from `h` with `h' ⊨ P`, `h ⊎ h' ⊨ Q` |

The crucial point of `*` is the **disjointness** — `l ↦ v * l ↦ w` is *unsatisfiable* (you cannot split the singleton heap at `l` into two disjoint parts both containing `l`). This gives separation logic its natural way of saying "two pointers don't alias": `x ↦ a * y ↦ b` means `x` and `y` are distinct locations.

This is a profound difference from classical conjunction. With classical `∧`, `x ↦ a ∧ y ↦ b` doesn't tell you whether `x = y` (both might point at the same cell). With `*`, the disjointness is *baked in*: the same formula is a statement that the two cells are at different addresses. Aliasing — the bane of every C verifier since the language was invented — becomes a structural concern of the formula rather than a global invariant the verifier must constantly re-establish.

## The Frame Rule

The frame rule is the heart of separation logic's modularity:

```
{ P } C { Q }
─────────────────────  (FRAME)
{ P * R } C { Q * R }
```

Read: if command `C` takes a heap satisfying `P` to one satisfying `Q`, and you have additional disjoint heap satisfying `R` "in the background", then `C` takes the *combined* heap to one satisfying `Q * R` — because `C` couldn't have touched `R` (the heap was disjoint, and we're assuming `C` only touches what its precondition mentions).

The frame rule is sound only because of the **locality** of commands: a command can only read or write the cells mentioned in its precondition. This is enforced by the operational semantics (in C parlance, `free(p)` doesn't touch `q` when `p ≠ q`), and separation logic is the logic whose frame rule captures it precisely.

A concrete example, the `free_node` function mentioned earlier:

```
{ p ↦ node(v, n) }  free_node(p)  { emp }
                                  (* p is no longer allocated *)
                                  (* but everything else is preserved *)


{ p ↦ node(v, n)  *  q ↦ node(w, m)  *  rest }
   free_node(p)
{ emp  *  q ↦ node(w, m)  *  rest }
```

The `rest` of the heap is carried across unchanged by the frame rule — even though `free_node`'s own specification didn't mention it at all. This is what makes modular verification possible.

## The Proof Calculus

### Axiomatic Separation Logic

The axiomatic presentation extends Hoare logic with the new connectives and rules. The key rules, in addition to standard Hoare (assignment, sequence, conditional, while-with-invariant), are:

```
{ emp } skip { emp }                             (SKIP)

{ l ↦ v } l := [l] { l ↦ v }                    (LOAD — read into a register)

{ l ↦ _ } [l] := v { l ↦ v }                    (STORE — write a value)

{ l ↦ v } dispose(l) { emp }                    (FREE)

{ l ↦ _ } l := cons(v) { l ↦ v }                (MALLOC)

{x = l ∧ l ↦ v} x := [l] {x = v ∧ l ↦ v}         (READ into x, fresh l)
```

The MALLOC rule produces a *fresh* location — formally, separation logic operates over a heap with infinitely many locations, and `cons` picks one not in the current domain. (Soundness of this requires either a countably-infinite set of locations with newness side-conditions, or a categorical treatment via "permission-slots" — see O'Hearn's *Insights from Separation Logic*, 2019.)

These rules, combined with the FRAME rule, let you verify small pointer-manipulating programs compositionally — the proof of `list_reverse` walks the list cell by cell, and at each step the frame rule carries the untouched tail of the list forward without re-stating it.

### Symbolic Execution and Bi-Abduction

The axiomatic calculus is mathematically clean but operationally painful: you have to find the right precondition for every command (often via *backward* reasoning). **Symbolic execution** in separation logic turns this around: the verifier maintains a *symbolic heap* (a conjunction of `l ↦ v` facts plus pure arithmetic facts) and steps forward through the program, applying the small-axiom rules directly.

The harder problem: *what is the precondition for a function call in the first place?* If your function `foo` is called at a call site where the caller's symbolic heap is `x ↦ 1 * y ↦ 2 * z ↦ 3`, and `foo`'s spec is `{ a ↦ 1 } foo { b ↦ 2 }`, the caller must figure out that `a := x` and `b := y`, frame out `z ↦ 3`, and apply the spec. This is **bi-abduction** (O'Hearn et al. 2009): given a symbolic state `H` and a postcondition-relevant heap fragment `P`, find `A` (anti-frame — what the call needs) and `X` (frame — what's left over) such that `H ⊨ A * X` and `P ⊨ A`.

```
Bi-abduction problem:
  Given:    current heap H, "needed" fragment P
  Find:     A, X such that  H = A * X  and  P "fits in" A

  H = x ↦ 1 * y ↦ 2 * z ↦ 3
  P = a ↦ 1
  → A = x ↦ 1, X = y ↦ 2 * z ↦ 3   (with a := x)
```

Bi-abduction is what makes **Infer** (Facebook/Meta's static analyzer, originally developed by O'Hearn's group) practical at scale: Infer walks millions of lines of C/C++/Objective-C, computing a per-function spec via forward symbolic execution and bi-abductive inference, then composing specs at call sites. The result is the analyzer that found thousands of memory-leak bugs in Facebook's mobile apps before deployment.

## Iris: The Modern Framework

**Iris** (Jung et al., 2015; Krebbers et al., 2017) is the modern separation-logic framework, implemented in Coq. It generalizes earlier separation logics in several directions:

1. **Concurrent separation logic** with **invariants** as first-class resources. An invariant `I` is a heap assertion that is *stable* across concurrent accesses; Iris models `I` as a resource token (you own the "right to break `I` momentarily to access protected cells") and uses fractional permissions to share read access safely.
2. **Higher-order** specifications: predicates range over predicates, allowing quantification over invariants, ghost-state views, and protocols.
3. **Step-indexed** model: the semantics is stratified by a "step index" that bounds how many steps into the future you have to look; this gives a model to recursive predicates that would otherwise be unsound in plain separation logic.
4. **Ghost state**: the logic admits "ghost" variables that exist only in the proof, not in the program — used for tracking protocol phases, version numbers, resource tokens.

A typical Iris-style spec for a concurrent lock:

```coq
Lemma lock_spec γ P R :
  inv γ P →                       (* lock invariant, wrapped as resource *)
  is_lock γ R →                   (* a "logical" lock token *)
  {{ R }} acquire R               (* caller must give up some resource R to enter CS *)
  {{ P * R }}.                    (* caller now also owns the lock invariant P *)

Lemma release_spec γ R :
  is_lock γ R →
  {{ P * R }} release R
  {{ R }}.                         (* lock released; P goes back to invariant state *)
```

The invariant `I` is opened by `acquire` and closed by `release`, and the step-indexed model ensures that two threads can't both have `I` open at the same time. Iris proves this is sound via a step-indexed model construction.

Iris's soundness proof is mechanized in Coq; the framework is the basis for **Iris Proof Mode** (IPM), a Coq tactic language that lets you write separation-logic proofs in a natural style — the tactics `iIntros`, `iApply`, `iDestruct`, `iFrame` are direct analogs of the paper proof rules.

## VST: Verified Software Toolchain for C

**VST** (Verified Software Toolchain, Andrew Appel et al., Princeton) is a separation logic for the C programming language, mechanized in Coq, that connects directly to **CompCert**'s formal C semantics. The pipeline:

```
  C source
      |
      | (CompCert's Clight AST, imported into Coq)
      v
  VST separation-logic rules, proved sound against Clight operational semantics
      |
      v
  Coq proof: for every Clight program P, VST proves  {Pre} P {Post}
      |
      v
  Theorem: the executable code CompCert generates from P satisfies the same spec
  (by CompCert's correctness theorem)
```

This composition is what makes VST compelling: it gives you an end-to-end theorem from C source all the way to assembly, with the only trusted components being Coq's kernel, CompCert's C semantics, and VST's separation-logic rules.

VST has been used to verify crypto primitives (the **HAACL** library's Curve25519 implementation), networking code, parsers, and the **Libsnark-prover** for zk-SNARKs. The cost is real: verifying a single cryptographic primitive in VST is typically weeks of expert work for a few thousand lines of code.

## RustBelt: Soundness of Rust's Type System

**RustBelt** (Jung et al., 2017+) is the separation-logic framework for Rust. Rust's type system promises memory safety without garbage collection, via *ownership*, *borrowing*, and *lifetimes*. The question: is the type system actually sound? Are `unsafe` blocks that escape the type checker's scrutiny still safe if they observe Rust's programmer-facing aliasing rules?

RustBelt answers this by modeling Rust as a **lambda calculus with lifetimes** (`λ_Rust`) and giving an operational semantics with first-class "lifetimes" that delimit regions of program execution. A separation logic over `λ_Rust` models *borrowing* as a resource: `&mut T` is modeled as a permission token whose lifetime is bounded by a step-index, and `unsafe` code is sound iff it satisfies the separation-logic spec.

RustBelt has verified the soundness of:

- `Rc<T>` and `Arc<T>` (reference-counted pointers)
- `Mutex<T>` and `RwLock<T>` from the standard library
- The `Cell` and `RefCell` types' interior mutability
- Several unsafe primitives from `libcore` including `mem::replace`, `mem::swap`, and `ManuallyDrop`

The key result: every type-system rule in Rust, plus every `unsafe` block in the standard library that the RustBelt team checked, is sound. This is the strongest semantic justification of any mainstream language's type system.

## When to Use Separation Logic

- You're verifying pointer-manipulating code in C, C++, or Rust.
- The key invariants are about *ownership* and *disjointness* of heap regions.
- You want *modular* proofs (a function's spec should not have to enumerate the whole heap).
- You're willing to pay the proof-engineering cost: even with Iris Proof Mode, a non-trivial module is days of work.

For languages with managed memory (Java, Go, Python), pure separation logic is overkill — the aliasing concerns are subsumed by the runtime's invariants, and a type system + model checker is usually more cost-effective. The win is in languages where the programmer controls memory layout, and that means C, C++, Rust, and (in specialized contexts) assembly.

For "find as many bugs as possible in a million-line codebase" — use **Infer** (a bi-abductive analyzer). For "prove this 5K-line crypto primitive correct down to the assembly" — use **VST**. For "verify that Rust's unsafe primitives actually satisfy their specs" — use **RustBelt**. The techniques are the same; the deployment scenarios differ in the strictness of soundness you can afford.

## References

- Peter O'Hearn, David Pym. **The Logic of Bunched Implications**. Bulletin of Symbolic Logic 1999. The precursor; introduces BI, the substructural logic whose model makes separation logic work. https://www.cs.ucl.ac.uk/staff/d.pym/BI-sept-99.pdf
- Samin Ishtiaq and Peter O'Hearn. **BI as an Assertion Language for Mutable Data Structures**. POPL 2001. The paper that introduces Hoare logic + BI = separation logic. https://dl.acm.org/doi/10.1145/374783.375105
- John Reynolds. **Separation Logic: A Logic for Shared Mutable Data Structures**. LICS 2002. The polished foundational paper; standard citation. https://www.cs.cmu.edu/~jcr/seplogic.pdf
- Ralf Jung, David Swase, et al. **Iris from the ground up: A modular foundation for higher-order concurrent separation logic**. JFP 2018. The foundational Iris paper. https://iris-project.org/pdfs/2018-jfp-final.pdf
- The Iris documentation, including the Coq development and proof mode. https://iris-project.org/ and https://gitlab.mpi-sws.org/iris/iris
- Andrew Appel et al. *Program Logics for Certified Compilers* (VST book). Cambridge 2014. The VST reference. https://vst.cs.princeton.edu/
- Derek Dreyer et al. **RustBelt: Securing the Foundations of the Rust Programming Language**. POPL 2018. The RustBelt foundational paper. https://plv.mpi-sws.org/rustbelt/popl18/
- Peter O'Hearn. **Bi-Abduction (and Related Problems) in Separation Logic**. BICT 2019. The bi-abduction paper behind Infer. https://www.cs.ucl.edu/compmedphys/physonly/webonly/lect/2011-12/oxford/extra-OHearn.pdf and the original 2009 paper https://dl.acm.org/doi/10.1145/1542476.1542486
- Cristiano Calcagno and Dino Distefano. **Infer: an automatic program verifier for memory safety**. Microsoft Research / Meta. The production-scale bi-abductive analyzer. https://fbinfer.com/
