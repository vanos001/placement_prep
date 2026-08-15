# Type Systems

Type systems classify expressions by the kind of values they produce, enabling compilers to reject meaningless programs at compile time. Advanced type systems go far beyond simple type checking — they encode invariants like linearity, ownership, protocol conformance, and effect purity directly in the type language.

## Hindley-Milner Type System

Hindley-Milner (HM) is the canonical type system for functional languages (ML, Haskell, OCaml, Rust). It provides **parametric polymorphism** (generics) with **principal types** and **complete type inference**.

### Core Design

HM has two forms of types: **monotypes** (concrete, like `int → int`) and **polytypes** (schemes, like `∀α. α → α`). The key constraint: **let-polymorphism** — a polymorphic type is generalized only at `let`-bindings, not at function arguments.

```ml
(* Polymorphic at let-binding *)
let id x = x          (* id : ∀α. α → α *)
let a = id 3          (* α = int here *)
let b = id "hello"   (* α = string here — OK, different instantiation *)

(* NOT polymorphic at argument position in vanilla HM *)
let f g = (g 3, g "hello")  (* REJECTED — g must be monomorphic *)
```

### Algorithm W

Algorithm W is the classic type inference algorithm for HM. It operates by:

1. **Generating constraints** from the program structure (e.g., if `f x` is well-typed, the type of `f` must be `τ₁ → τ₂` and `x` must have type `τ₁`).
2. **Unifying** constraints using Robinson's unification algorithm (first-order, occurs-check).
3. **Generalizing** free type variables at `let`-bound definitions to produce polytypes.
4. **Instantiating** polytypes with fresh type variables when used.

```haskell
-- Algorithm W, simplified
infer :: Env -> Expr -> (Subst, Type)
infer env (Var x)   = instantiate (lookup env x)
infer env (App e1 e2) = 
  let (s1, t1) = infer env e1
      (s2, t2) = infer (apply s1 env) e2
      s3       = unify (apply s2 t1) (t2 --> tFresh)
  in (s3 . s2 . s1, apply s3 tFresh)
infer env (Lam x e) =
  let tv    = freshTyVar
      (s, t) = infer ((x, tv) : env) e
  in (s, apply s (tv --> t))
infer env (Let x e1 e2) =
  let (s1, t1) = infer env e1
      env'  = apply s1 env
      scheme = generalize (freeTyVars env') t1
      (s2, t2) = infer ((x, scheme) : env') e2
  in (s2 . s1, t2)
```

Complexity: Algorithm W is **DEXP-complete** (exponential in worst case) due to the occurs check and nested let-polymorphism, though PSPACE-complete with union-find optimization. In practice it's essentially linear.

> **Interview Angle**: "Why can't you have polymorphism at argument positions in vanilla HM?" Because full (rank-2+) polymorphism makes type inference undecidable. The value restriction in OCaml and the let-polymorphism restriction exist precisely to keep inference decidable.

## Dependent Types

Dependent types allow types to **depend on values**. The type `Vec n a` represents a vector of length `n` with elements of type `a`. This enables encoding invariants like "this list is sorted" or "this array index is in bounds" directly in the type.

```idris
data Vec : Nat -> Type -> Type where
  Nil  : Vec 0 a
  (::) : a -> Vec n a -> Vec (n + 1) a

-- head is safe: the type guarantees n >= 1
head : Vec (n + 1) a -> a
head (x :: _) = x

-- append preserves length
append : Vec m a -> Vec n a -> Vec (m + n) a
```

Languages with dependent types: **Coq**, **Agda**, **Idris 2**, **Lean 4**. The cost is that type checking becomes undecidable in general (type checking = proof checking), though practical systems are designed so that most programs type-check efficiently.

## Refinement Types

Refinement types attach **logical predicates** to base types. Instead of `int`, you write `{x : int | x > 0}` (positive integers). This is less powerful than full dependent types but **decidable** and often integrated into existing languages.

```liquidhaskell
-- LiquidHaskell refinement type
{-@ type Positive = {v:Int | v > 0} @-}

{-@ divide :: Int -> Positive -> Int @-}
divide :: Int -> Int -> Int
divide _ 0 = error "impossible by type"
divide x y = x `div` y
```

Refinement type checking reduces to **SMT solving** (Z3). Tools: **LiquidHaskell**, **Fstar**, **RefinedC** (for verifying C programs).

## Linear and Affine Types

**Linear types** require that every value of linear type is used **exactly once**. **Affine types** relax this to **at most once** (values may be dropped).

```
Linear:    x must be used exactly once
Affine:    x must be used at most once  
Unrestricted: x can be used any number of times
```

### Rust's Ownership as Affine Types

Rust's ownership system is essentially affine types with **borrowing** (a controlled form of aliasing):

```rust
fn consume(s: String) -> usize { s.len() }  // s is affine — moved

let s = String::from("hello");
let n = consume(s);
// println!("{}", s);  // ERROR: value borrowed after move
```

Clean and Rust use linear/affine types for memory management without garbage collection. The compiler inserts frees at the end of each linear variable's scope, knowing no aliases exist.

## Session Types

Session types specify the **communication protocol** between concurrent processes. They describe what messages are sent, in what order, over which channels.

```rust
// Conceptual session type for a server protocol:
// !Send(String).?Recv(Response).End
//  Send a string, then receive a response, then close
```

Languages implementing session types: **Sangster** (Haskell), **LoPi** (Rust), **Pony** (reference capabilities are a related concept). Session types catch protocol violations at compile time — a client that sends `Int` where `String` is expected fails type checking.

## Effect Systems and Algebraic Effects

### Effect Systems

An effect system tracks **computational effects** (I/O, state, exceptions, nondeterminism) in the type system, separate from the value type. A function `read : File → String ! IO` returns a `String` and may perform `IO` effects.

### Algebraic Effects

Algebraic effects generalize exceptions and other effects into **user-defined operations** that can be **handled** by effect handlers:

```ocaml
(* Define an effect *)
effect Ask : string -> string

(* Use it *)
let hello () =
  let name = perform Ask "What is your name?" in
  print_string ("Hello, " ^ name)

(* Handle it *)
let () =
  try hello ()
  with effect Ask _ -> fun k ->
    let name = read_line () in
    continue k name
```

Unlike monad transformers, algebraic effects compose freely — you don't need a stack of transformer layers. They also enable **delimited continuations** (the `k` above is a continuation). Languages: **Multicore OCaml** (Eff library), **Koka**, **Unison**, **Eff**.

> **Interview Angle**: "How do algebraic effects compare to monads for handling side effects?" Monads require a fixed ordering via the `>>=` chain and need transformer stacks for multiple effects. Algebraic effects are orthogonal — handlers can be composed and intercept effects at any call depth. However, algebraic effects require runtime support for delimited continuations, making them harder to compile efficiently.

## Monads and Comonads

### Monads

A monad is a type constructor `m` with `return : a → m a` and `bind : m a → (a → m b) → m b` satisfying three laws (left identity, right identity, associativity). In PL theory, monads **encapsulate effectful computation** as a purely functional program transformer.

| Effect | Monad | Key Operation |
|--------|-------|---------------|
| Failure | `Option` / `Maybe` | `None` short-circuits |
| State | `State s a = s → (a, s)` | Thread state through bind |
| I/O | `IO a` | Opaque, sequenced computation |
| Nondeterminism | `[] a` (list monad) | Cartesian product via bind |
| Exceptions | `Either e a` | `Left e` propagates errors |

### Comonads

A comonad is the categorical **dual** of a monad: `extract : w a → a` and `extend : (w a → b) → w a → w b`. Comonads model **context-dependent computation** — values that carry their environment.

```haskell
class Functor w => Comonad w where
  extract   :: w a -> a
  duplicate :: w a -> w (w a)
  extend    :: (w a -> b) -> w a -> w b
```

Practical use: **cellular automata**, **lenses** (Zipper comonad), **dataflow computation**. The `Store` comonad `s -> (a, s)` represents a read-only state where `extract` reads and `extend` propagates.

## Comparison Table

| Type System Feature | Decidable Inference? | Expressiveness | Real-World Use |
|---------------------|---------------------|----------------|----------------|
| HM / let-poly | Yes (PSPACE) | Medium | ML, OCaml, Haskell (98) |
| Rank-N types | Rank-2: yes; Rank-ω: no | High | GHC extensions |
| GADTs | With extensions | High | Haskell, Scala 3 |
| Dependent types | Undecidable in general | Very high | Coq, Agda, Lean, Idris |
| Refinement types | Yes (SMT) | Medium-high | LiquidHaskell, F* |
| Linear/affine | Yes | Medium | Rust, Clean, Zig (borrowing) |
| Session types | Yes | Medium (protocols) | Rust channels, Pony |
| Effect systems | Yes (with annotations) | Medium | Koka, Multicore OCaml |
| Algebraic effects | Yes | High | Koka, Unison, Eff |

## References

- B. C. Pierce, *Types and Programming Languages* (TAPL)
- L. Cardelli, *Type Systems* (ACM Computing Surveys, 1996)
- P. Wadler, *Monads for Functional Programming* (1995)
- D. Biernacki et al., *An Effect System for Algebraic Effects and Handlers* (2022)
- P.-M. Pédrot, *An Effectful Language with Algebraic Effects* (Koka)
