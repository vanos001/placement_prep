# The Lambda Calculus — A Turing-Complete Minimal Language

## Overview

The λ-calculus is a formal system invented by Alonzo Church in 1932–35, intended as a foundation for mathematics that reduced all of logic to a single operation: the application of functions to arguments. Church's 1936 paper *An Unsolvable Problem of Elementary Number Theory* proved that a particular question about λ-terms — does a given term β-reduce to a normal form? — is undecidable, by a method (encoding functions as numerals, then diagonalizing) that paralleled Turing's simultaneous proof of the undecidability of the Halting Problem. The Church–Turing thesis, jointly formulated from these two results, asserts that the class of λ-definable functions, the class of Turing-computable functions, and the intuitively computable functions coincide.

The untyped λ-calculus has just three constructs — variables, abstraction (function definition), and application — yet it is Turing-complete. Every computable function can be encoded as a λ-term, and β-reduction provides an operational semantics in which computation = term rewriting. Adding types yields a hierarchy of stronger logics and languages: simply-typed λ-calculus (STLC) corresponds via Curry–Howard to propositional logic and is strongly normalizing (every term reaches a normal form — so STLC is *not* Turing-complete); System F adds polymorphism and corresponds to second-order propositional logic; System F-ω adds higher-kinded type operators and corresponds to higher-order logic. This page covers the untyped calculus, the Y combinator, the typed hierarchy, and the comparison to Turing machines.

> Related: [Turing Machines](./turing-machines.md), [Computability](./computability.md), [Curry–Howard Correspondence](./curry-howard.md), [Programming Language Theory](./programming-language-theory.md)

## Syntax

The grammar of untyped λ-terms is minimal:

```
M, N ::= x              variable
       | λx. M          abstraction  (the function of x returning M)
       | M N            application  (apply M to N)
```

Abstraction binds the variable x. Application is left-associative: `M N P` = `(M N) P`. The body of an abstraction extends as far right as possible: `λx. M N` = `λx. (M N)`, not `(λx. M) N`.

Two terms are syntactically equal up to renaming of bound variables — `λx. x` and `λy. y` are the *same* term. Formally we work modulo α-equivalence, which leads to the first of the three core rules.

## The Three Reduction Rules

### α-conversion (renaming)

`λx. M =α λy. M[x := y]`, provided y is fresh (not free in M). This rule says bound variables are interchangeable. It exists to avoid *variable capture* during β-reduction: when substituting N for x in `λy. M`, if y is free in N, naïve substitution would "capture" y, changing the term's meaning. The fix is to first α-rename the bound variable to a fresh name. The Barendregt convention — rename all bound variables to be distinct and disjoint from free variables — lets us work as if capture never occurs.

### β-reduction (the computation step)

`(λx. M) N →β M[x := N]` — apply the function to its argument by substitution. This is the operational meaning of the calculus. β-reduction is *confluent* (the Church–Rosser theorem): if `M →* M_1` and `M →* M_2`, then there exists N with `M_1 →* N` and `M_2 →* N`. In particular, normal forms, when they exist, are unique up to α.

A term is in **normal form** if no β-redex is a subterm. A term is **strongly normalizing** if every reduction order terminates. Untyped λ-calculus is *not* strongly normalizing — the term `Ω = (λx. x x) (λx. x x)` β-reduces to itself forever.

### η-reduction (extensionality)

`λx. (M x) →η M`, provided x is not free in M. This rule captures extensionality: a function equals its "eta expansion" because they agree on every input. η is a *definitional equality* rather than an operational step in most implementations — it doesn't reduce work, it just identifies terms. Combined with β, the resulting βη-equivalence is the maximal congruence compatible with the calculus.

## Church Numerals

Church's encoding represents the natural number n as the higher-order function that composes its first argument n times:

```
0  = λf. λx. x
1  = λf. λx. f x
2  = λf. λx. f (f x)
3  = λf. λx. f (f (f x))
n  = λf. λx. f^n x
```

The successor function, addition, multiplication, and a predecessor (tricky!) are definable:

```
SUCC   = λn. λf. λx. f (n f x)
PLUS   = λm. λn. λf. λx. m f (n f x)
MULT   = λm. λn. λf. m (n f)             -- or λm.λn.λf.λx. m (n f) x
PRED   = λn. λf. λx. n (λg. λh. h (g f)) (λu. x) (λu. u)
ISZERO = λn. n (λx. FALSE) TRUE
```

The predecessor is non-obvious — Kleene's trick uses a pair `(λu. x, λu. u)` and threads n applications of a function that rotates the pair, so after n steps the first component is `f^(n-1) x`. Every computable function on naturals can then be encoded; the **Church–Turing thesis** holds that this encoding captures exactly the intuitively computable functions.

Boolean values, pairs, lists, and arbitrary algebraic data types all have analogous encodings:

```
TRUE    = λx. λy. x              (the K combinator)
FALSE   = λx. λy. y              (the K-composed-with-I / "KI" combinator)
IF      = λb. λt. λe. b t e       (or just the identity: IF = λb. b)
PAIR    = λa. λb. λf. f a b
FST     = λp. p (λa. λb. a)
SND     = λp. p (λa. λb. b)
```

## The Y Combinator (Fixed-Point)

To define recursive functions without native recursion, we need a term that, given F, returns a fixed point — a term X such that `F X = X`. Turing's `Θ` and Church's `Y` both achieve this. The standard Y combinator:

```
Y  = λf. (λx. f (x x)) (λx. f (x x))
```

Reduction: `Y F →β (λx. F (x x)) (λx. F (x x)) →β F ((λx. F (x x)) (λx. F (x x))) = F (Y F)`. So `Y F = F (Y F) = F (F (Y F)) = …`, unrolling the recursion.

The catch: under **call-by-value** evaluation (eager), `Y F` diverges, because `x x` is evaluated before being passed to `f`. Call-by-need or call-by-name (Haskell, lazy evaluation) terminates correctly. For strict evaluation languages, **Turing's Θ** works:

```
Θ  = (λx. λf. f (x x f)) (λx. λf. f (x x f))
   = λf. f ((λx. f (x x f)) (λx. f (x x f)))
   reduces to: f (Θ f)
```

Or simply use a recursive value via the Z combinator (eta-expanded Y):

```
Z  = λf. (λx. f (λv. x x v)) (λx. f (λv. x x v))
```

These combinators are the theoretical heart of recursion in functional languages. The factorial function, written as a λ-term:

```
FACT   = Y (λfact. λn. IF (ISZERO n) 1 (MULT n (fact (PRED n))))
```

## Simply-Typed λ-Calculus (STLC)

Church's typed calculus (1940) introduces simple types built from base types (ι, o) and the arrow constructor `→`:

```
τ ::= ι           base type
    | τ → τ'      function type
```

The typing judgement `Γ ⊢ M : τ` reads "in context Γ (a set of variable:type bindings), term M has type τ". The rules:

```
(x : τ) ∈ Γ                         (Var)
─────────────────                    Γ, x : τ₁ ⊢ M : τ₂
Γ ⊢ x : τ                            ─────────────────────  (→I)
                                     Γ ⊢ λx. M : τ₁ → τ₂
Γ ⊢ M : τ₁ → τ₂    Γ ⊢ N : τ₁
─────────────────────────────────    (→E)
        Γ ⊢ M N : τ₂
```

The (→I) rule introduces (creates) a function type; (→E) eliminates (uses) it. This is the Curry–Howard correspondence for implication — see the [dedicated page](./curry-howard.md). The **subject reduction** theorem says typing is preserved under β-reduction; **strong normalization** says every well-typed term has a normal form. Consequently STLC is **not** Turing-complete — non-terminating terms like Ω cannot be typed.

The typed Y combinator is forbidden too: it would require `μ α. α → α`, a recursive type, which simple types do not provide. Recursive types and recursion are added to STLC in languages like ML via special constructs (`let rec`, `datatype`) and a value-restriction check.

## System F (Polymorphic λ-Calculus)

Girard (1972) and Reynolds (1974) independently introduced System F (also called the polymorphic λ-calculus), which adds **universal types** quantifying over types:

```
τ ::= ... | ∀α. τ
M ::= ... | Λα. M          type abstraction
        | M [τ]             type application
```

The new rules:

```
Γ ⊢ M : τ                  (α not free in Γ)
──────────────────         ──────────────────   (∀E)
Γ ⊢ Λα. M : ∀α. τ         Γ ⊢ M [τ'] : τ[α:=τ']
───────────── (∀I)
```

A System F identity function: `id = Λα. λx:α. x : ∀α. α → α`. Apply it: `id [Int] 5` instantiates α to Int and then applies. Polymorphic data types follow:

```
length : ∀α. List α → Int
```

System F is extremely expressive: **Girard's theorem** says the functions on naturals representable in System F are exactly the *provably total* functions of second-order Peano arithmetic — far more than primitive recursion. Strong normalization holds. Yet System F's type inference is **undecidable** (Wells 1999): given an untyped term, no algorithm can determine whether it is typable in System F. Haskell implements a conservative, decidable fragment called *Hindley–Milner-Damas* (let-polymorphism).

## System F-ω (Higher-Kinded)

System F-ω adds **type operators** — functions from types to types. The syntax gains a type-level λ:

```
κ ::= *                the kind of types
    | κ → κ'           the kind of type operators
τ ::= ... | λ(α:κ). τ   type-level abstraction
        | τ [τ']        type-level application
```

A type of kind `* → *` is a unary type constructor: `List : * → *` takes a type and returns the list-of-that-type. A type of kind `* → * → *` is binary: `Map : * → * → *` takes key and value types and returns the map type. The general construction permits arbitrarily high kinds; the type system itself is a simply-typed λ-calculus over kinds.

Haskell's type system is roughly System F-ω extended with type classes (Wadler–Blott 1989) and constrained quantification. Higher-rank polymorphism (`RankNTypes`) lets a function ask for polymorphic arguments, e.g. `∀a. [a] → [a] → Bool`.

## The λ-Calculus vs. Turing Machines

The equivalence is by mutual simulation. The untyped λ-calculus is Turing-complete: Kleene proved every recursive function is λ-definable, and Church proved every λ-definable function is recursive. Conversely, a TM can be encoded as a λ-term and β-reduction can simulate a single TM step in polynomial time (via a term-level encoding of the tape as a pair of lists).

But the two models differ in style and emphasis:

| Aspect | λ-Calculus | Turing Machine |
|---|---|---|
| Foundation | Functions, substitution | State, memory tape |
| Computation | Rewriting terms | Moving a head on a tape |
| Equivalence | Turing-complete (untyped) | Turing-complete |
| Typing | Natural type systems (STLC, F, F-ω) | No native typing |
| Implementation | Directly inspired LISP, ML, Haskell | Inspired von Neumann architecture |
| Confluence | Church–Rosser holds | Determinism is built in |
| Strong normalization | Holds for typed variants | Not applicable |

The practical lineage is clear: the λ-calculus inspired LISP (McCarthy 1958), ML (Milner 1973), Scheme, Haskell, OCaml, and the modern functional core of TypeScript, Rust, and Scala. Turing machines inspired the stored-program von Neumann machine and the entire imperative tradition (C, Fortran, the IBM 360). Modern languages blend both: Haskell is λ-calculus with lazy evaluation and type classes; Rust is STLC with affine (ownership) types and an ML-like module system.

## Interview Questions

**Q: What are the three reductions of the λ-calculus?**
A: α (rename bound variables to avoid capture), β (apply a function: `(λx. M) N → M[x:=N]`), η (extensionality: `λx. M x → M` when x not free in M). β is the operational rule; α is bookkeeping; η is a definitional equality.

**Q: Why does the Y combinator work, and what's its limitation?**
A: `Y F → F (Y F)` unrolls the recursion by exploiting self-application. Under call-by-value evaluation, `Y F` diverges because `x x` is evaluated before being passed; lazy languages (Haskell) or the call-by-name variant terminate. For strict languages, Turing's Θ or the Z combinator (eta-expansion) avoids this.

**Q: What's the difference between STLC, System F, and System F-ω?**
A: STLC has only base types and arrows `τ → τ'`; it corresponds to propositional logic and is strongly normalizing (not Turing-complete). System F adds universal quantification over types `∀α. τ`, enabling polymorphism — corresponds to second-order logic. System F-ω adds type-level functions (`* → *`), enabling higher-kinded types like `List`. Each is strictly more expressive than the last.

**Q: Why is untyped λ-calculus Turing-complete but STLC not?**
A: Untyped λ-calculus admits self-application (`x x`), which enables recursion via Y. STLC's typing rules forbid self-application (a term cannot have both type `τ` and `τ → τ'` simultaneously), and strong normalization (proved by Tait's reducibility method) ensures every well-typed term reaches a normal form — precluding non-terminating recursion.

## References

- [Barendregt, *The Lambda Calculus: Its Syntax and Semantics* (1984)](https://www.sciencedirect.com/bookseries/studies-in-logic-and-the-foundations-of-mathematics/vol/103) — the reference monograph; contains Church–Rosser, standardization, and the typed hierarchy.
- [Pierce, *Types and Programming Languages* (MIT Press, 2002)](https://www.cis.upenn.edu/~bcpierce/tapl/) — the standard introduction to STLC, System F, and subtyping.
- [Church, *An Unsolvable Problem of Elementary Number Theory* (1936)](https://www.jstor.org/stable/2371045) — the original undecidability proof via λ-definability.
- [Turing, *On Computable Numbers* (1936)](https://www.cs.virginia.edu/~robins/Turing_Paper_1936.pdf) — the parallel proof, with reference to Church's paper.
- [Girard, Taylor, & Silva, *Proofs and Types* (1989)](http://www.paultaylor.eu/stable/Proofs+Types.html) — System F, F-ω, and the strong normalization theorem.
- [Wadler & Blott, *Type Classes* (1989)](https://doi.org/10.1145/99370.99395) — making ad-hoc polymorphism practical in System F-ω.
- [Sørensen & Urzyczyn, *Lectures on the Curry–Howard Isomorphism*](https://www.cambridge.org/core/books/lectures-on-the-curryhoward-isomorphism/) — connects untyped, typed, and polymorphic calculi to logics.
- See also: [Turing Machines](./turing-machines.md), [Computability](./computability.md), [Curry–Howard Correspondence](./curry-howard.md), [Programming Language Theory](./programming-language-theory.md)
