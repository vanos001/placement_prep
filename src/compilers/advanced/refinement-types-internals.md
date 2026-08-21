# Refinement Types Internals

Refinement types decorate a base type with a **logical predicate** the value must satisfy. Write `{ v : Int | v > 0 }` and you have described "positive integers" as a type. The predicate is discharged by an SMT solver (typically Z3) at compile time; if it cannot prove the predicate holds on every code path, the program is rejected. The result is a system lighter than full dependent types (decidable inference, embeddable inside existing languages) but stronger than ordinary types (it tracks arithmetic, inequalities, and array bounds).

The idea emerged from Freeman and Pfenning's 1991 work on ML refinements and was operationalized as **Liquid Types** by Rondon, Kawaguchi, and Jhala (PLDI 2008). The "liquid" comes from the inference algorithm: rather than require the programmer to annotate every site with a predicate, the system **infers** refinements by propagating constraints through a Horn-clause encoding. Liquid Haskell and F\* are the two main production systems; Refined TypeScript brings the idea to the JS ecosystem.

## The refinement syntax

A refinement type is `{ x : B | φ(x) }` where `B` is a base type and `φ` is a predicate in a **decidable fragment** of first-order logic — typically quantifier-free linear integer arithmetic (LIA) extended with uninterpreted functions and algebraic datatypes. For example:

```liquidhaskell
{-@ type Pos   = {v:Int | v > 0}        @-}
{-@ type Nat   = {v:Int | 0 <= v}       @-}
{-@ type Lt N  = {v:Int | v < N}       @-}

{-@ divide :: Int -> Pos -> Int         @-}
divide :: Int -> Int -> Int
divide _ 0 = error "impossible by type"
divide x y = x `div` y
```

The Liquid Haskell comment `{-@ ... @-}` is a refinement annotation; the actual Haskell type remains `Int -> Int -> Int`. The annotation says: the second argument must satisfy `v > 0`. The case `_ 0` becomes **unreachable by type** — and Liquid Haskell will warn if a function has dead code the refinement proves is unreachable.

A few syntactic conventions:
- The bound variable `v` is the value being refined.
- The predicate is in SMT-LIB syntax, with integer arithmetic, Booleans, uninterpreted functions, and (in some systems) algebraic datatypes.
- Refinements are **decidable** — you trade expressiveness for automation. There is no `∃` over arbitrary domains, no quantifier alternation.

## How it works: Horn clauses + SMT

The engineering insight that makes refinements tractable is the **Horn-clause encoding**. Given a program with refinement types, the verifier generates a set of Horn clauses over **refinement variables** (one per type position) and asks Z3 to solve for the unknown predicates.

Concretely, consider:

```liquidhaskell
{-@ range :: lo:Int -> hi:{v:Int|lo<v}
          -> [{v:Int | lo <= v && v < hi}] @-}
range lo hi = if lo < hi then lo : range (lo+1) hi else []
```

The verifier wants to find a refinement `κ` for the return type such that:
- `lo < hi` ⇒ `κ(lo, hi)` (the empty list in the else branch satisfies whatever `κ` requires)
- `lo < hi` ⇒ the head `lo` satisfies the element refinement `lo <= lo ∧ lo < hi`
- the recursive call `range (lo+1) hi` returns a list satisfying `κ(lo+1, hi)`, which is appended

This becomes a set of Horn clauses over the unknown `κ`:

```
  ∀ lo, hi.
    (lo < hi ∧ κ(lo+1, hi))  ⇒  κ(lo, hi)
  ∀ lo, hi.
    (lo < hi ∧ lo <= lo ∧ lo < hi)  ⇒  κ(lo, hi)
  ∀ lo, hi.
    ¬(lo < hi)  ⇒  κ(lo, hi)        -- the empty list is trivially refined
```

Z3 solves for `κ`, producing a solution like `κ(lo, hi) = (∀ e ∈ list. lo <= e ∧ e < hi)`. The user never writes the inferred refinements; the system discovers them.

This is the "liquid" in Liquid Types: refinements flow through the program like liquid, filling the shape of the program graph.

```
   Program source                Horn clauses               Z3 solves
   ┌───────────────────┐          ┌──────────────────┐      ┌───────────────┐
   │ f :: ... -> X     │   ───>   │ p(x1,...) -> q(...)│ ──> │ q := infer    │
   │   refinement      │   gen    │ q(x1,...) -> r(...)│      │ refinement    │
   │   templates       │   clauses│ ...               │      │ values        │
   └───────────────────┘          └──────────────────┘      └───────────────┘
        (one var per                          (Z3 finds a
         type position)                       model iff safe)
```

## Abstract refinements: measure functions

Plain refinements over `Int` are limited; real programs need to express "this list is sorted" or "this binary tree is balanced." Liquid Types handle this via **measure functions**: inductively defined predicates that the SMT solver treats as uninterpreted functions with rewrite axioms.

```liquidhaskell
{-@ measure len @-}
len :: [a] -> Int
len []     = 0
len (_:xs) = 1 + len xs

-- The list's refinement can now mention len(tl)
{-@ data [a] = [] | (::) { hd :: a, tl :: [{v:a | true}] } @-}
```

Once you have measures, you can write:

```liquidhaskell
{-@ take :: n:Nat -> xs:[a] -> {v:[a] | len v == if len xs < n then len xs else n} @-}
{-@ map  :: (a -> b) -> xs:[a] -> {v:[b] | len v == len xs} @-}
{-@ sort :: Ord a => xs:[a] -> {v:[a] | len v == len xs} @-}
```

The SMT solver does not compute `len` at runtime — it reasons *axiomatically* about it, using the measure's defining equations as rewrite rules. A list of length 3 cannot be sorted into one of length 2 — Z3 proves it from the rewrite rules.

## Higher-order refinements and reflection

A limitation of the original Liquid Types is that they only refine **base types**, not function types. Liquid Haskell extends with **abstract refinements** — refinements parameterized by predicates:

```liquidhaskell
{-@ foldr :: forall <p :: a -> Bool>.
              (a -> b -> b) -> b -> [a<p>] -> b @-}
```

The `<p>` is a refinement variable the caller gets to instantiate. This gives you higher-order polymorphism over refinements: a list filter takes a list refined by `p` and returns one refined by `p`, without committing to a specific `p`.

For full program equivalence (proving `f x == g x` for arbitrary `f` and `g`), Liquid Haskell introduces **reflection**: you mark a function as `reflect`-able, and the system adds its defining equations as SMT axioms. This is powerful but expensive — each reflected function blows up the SMT context. The rule of thumb: reflect only the small, total functions you actually need to reason about; rely on measures for everything else.

## Production systems

| System | Host language | Decidable logic | Distinctive feature |
|--------|----------------|------------------|----------------------|
| **Liquid Haskell** | Haskell | Z3 (SMT-LIB) | Measure functions, reflection, abstract refinements |
| **F\*** | F\* (own language) | Z3 + custom solver | Refinement + effects + proofs; used by Project Everest |
| **Refined TypeScript** | TypeScript | Z3 | Tainted-data tracking, regex-validated strings |
| **Dafny** | Dafny (own language) | Z3 | Auto-active verification; full Hoare logic |
| **RefinedC** | C | Isabelle + SMT | Pointer-precise C verification |

Project Everest (Microsoft Research) uses F\* to verify the entire mbedTLS TLS stack — the result is **HaCl\*** and **EverCrypt**, cryptographic primitives proven correct against their specs. Refined TypeScript has been used to enforce taint-tracking in real JS codebases; Liquid Haskell is used at Target Corporation for verifying distributed protocol implementations.

## Comparison: refinements vs contracts

Refinement types are often confused with **contracts** (Design-by-Contract, Racket contracts, JS assertions). They are different in important ways:

| Aspect | Refinement types | Runtime contracts |
|--------|-------------------|-------------------|
| When checked | Compile time | Run time |
| Coverage | All paths, all inputs | Only executed paths |
| Decidability | Decidable logic (SMT) | Turing-complete (any predicate) |
| Failure mode | Compile error | Runtime exception |
| Performance | Zero runtime cost | Assertion overhead |
| Expressiveness | Decidable fragment | Any predicate |
| Blame | Caller (statically) | Explicit blame assignment |

A contract can say `divide x y where y != 0` and check at runtime; a refinement type says the same thing statically. The contract is more expressive (any predicate, even undecidable ones) but less safe (you only learn about a violation when the path executes).

Languages often **combine** the two. Racket's contract system can be made first-class; Typed Racket adds types on top. F\* has both refinements (static) and assertions (runtime) — the SMT-undecidable parts get compiled to runtime checks with explicit blame.

The killer use case for refinements is **eliminating the runtime check**. If `divide :: Int -> Pos -> Int` is statically checked, the `_ 0` case is dead code that the compiler can remove entirely. No branch, no panic, no exception. That is the value: refactor the contract from "checked when executed" to "checked once, forever."

## What refinements cannot do

The price of decidability is expressiveness. Things refinement types cannot express:

- **Heap-shape invariants**: "this pointer is the head of an acyclic linked list" — needs separation logic, which is not in SMT-LIB's decidable fragment. (See VST for Coq or the Verifast tool.)
- **Termination measures** that involve nonlinear recursion — you mark functions as `terminating` and provide a metric, but the SMT solver's automation drops.
- **Equivalence with loops**: proving `f x = loop x` requires the loop's invariant, which Liquid Haskell can encode but won't infer.

For these you graduate to F\* (with its proof tactic language) or to Coq/Lean (with full dependent types and tactics). Refinements are the sweet spot of "expressive enough for safety properties, decidable enough for automation."

## Conclusion

Refinement types occupy the middle ground: more expressive than ordinary types, more automated than dependent types. They are the cheapest way to add **arithmetic safety** (no divide-by-zero, no out-of-bounds, no null-after-check) to a codebase, with zero runtime cost. The 2008 Liquid Types paper made them inference-driven and practical; the rest of the engineering has been about scaling SMT to real codebases.

For industry adoption: Liquid Haskell is used in production but mostly for library verification (`liquid-base`, `liquid-vector`, etc.); F\* is the heavyweight for security-critical code (EverCrypt, Project Everest); Refined TypeScript is the bridge to the JS world. The trend is clear: more languages are getting SMT-backed refinements, and SMT solving itself is getting fast enough that the compile-time cost is acceptable for libraries (if not for every application build).

## References

- P. Rondon, M. Kawaguchi, R. Jhala, *Liquid Types* (PLDI 2008) — https://dl.acm.org/doi/10.1145/1375581.1375602
- T. Freeman, F. Pfenning, *Refinement Types for ML* (PLDI 1991) — https://dl.acm.org/doi/10.1145/113315.113328
- Liquid Haskell documentation (UCSD Progsys) — https://ucsd-progsys.github.io/liquidhaskell/
- F\* tutorial and language — https://www.fstar-lang.org/tutorial/
- Project Everest (verified TLS via F\*) — https://project-everest.github.io/
- The Z3 SMT solver guide — https://microsoft.github.io/z3guide/
- N. Vazou et al., *LiquidHaskell: Haskell as a Theorem Prover* — https://arxiv.org/abs/1503.00024
- A. Bakst et al., *Refining Refinement Types with SMT* (Liquid Haskell papers index) — https://ucsd-progsys.github.io/liquidhaskell/papers.html
- K. Knowles et al., *Refinement Types for TypeScript* (ESOP 2018 extended) — https://dl.acm.org/doi/10.1145/3158103
