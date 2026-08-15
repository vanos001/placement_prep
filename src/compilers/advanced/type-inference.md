# Type Inference

Type inference is the process of **automatically deducing types** without explicit annotations. A good type inference system gives you the safety of static types with the ergonomics of dynamic typing. This chapter covers the algorithms, tradeoffs, and real-world implementations.

## Structural vs. Nominal Typing

### Structural Typing

In structural typing, two types are equivalent if they have **the same structure** (same fields, same methods), regardless of their declared name.

```typescript
// TypeScript: structural — these are the same type
type Point1 = { x: number; y: number };
type Point2 = { x: number; y: number };
const p: Point1 = { x: 1, y: 2 } as Point2;  // OK
```

### Nominal Typing

In nominal typing, types are equivalent only if they have the **same name/declaration**.

```java
// Java: nominal — even with identical fields, these are different types
class Point1 { int x, y; }
class Point2 { int x, y; }
Point1 p = new Point2();  // COMPILE ERROR
```

| Aspect | Structural | Nominal |
|--------|-----------|----------|
| **Equivalence** | By shape | By name |
| **Languages** | TypeScript, Go (interfaces), OCaml, ML | Java, C#, Rust, C++ |
| **Pros** | Flexible, less boilerplate | Clear intent, better encapsulation |
| **Cons** | Accidental equivalence | Verbose alias types |

> **Interview Angle**: "Why does Go use structural typing for interfaces?" Go interfaces are satisfied implicitly — any type with the required methods implements the interface. This enables retroactive implementation without modifying the original type, supporting the 'accept interfaces, return structs' idiom.

## Subtyping and Variance

### Subtyping

Subtyping (denoted `S <: T`) means "every value of type `S` can be used where `T` is expected." Classical example: `Dog <: Animal`.

```java
Animal a = new Dog();  // OK: Dog <: Animal
List<Animal> list = new ArrayList<Dog>();  // ERROR in Java!
```

### Variance

Variance describes how subtyping composes with type constructors:

| Variance | Notation | Meaning | Example |
|----------|----------|---------|--------|
| **Covariant** | `S <: T` ⇒ `F<S> <: F<T>` | Producer/container | `IEnumerable<out Dog> <: IEnumerable<out Animal>` |
| **Contravariant** | `S <: T` ⇒ `F<T> <: F<S>` | Consumer | `IComparer<in Animal> <: IComparer<in Dog>` |
| **Invariant** | No subtyping between `F<S>` and `F<T>` | Mutable container | `MutableList<Dog>` ≠ `MutableList<Animal>` |
| **Bivariant** | Both covariant and contravariant | Weakens soundness | Avoid — soundness holes |

```scala
// Scala: variance annotations
class Box[+A]   // covariant (producer)
class Writer[-A] // contravariant (consumer)
class Cell[A]   // invariant (mutable)

// Function type: contravariant in input, covariant in output
// Function1[-A, +B]
```

Function types are **contravariant in argument position** and **covariant in return position**. This follows from the Liskov Substitution Principle: if `f : Dog → String` and `g : Animal → Dog`, then `f ∘ g : Animal → String`. To accept a broader input, you need a more general function.

### Declaration-Site vs. Use-Site Variance

- **Declaration-site** (Scala, Kotlin): Variance is declared once at the class definition.
- **Use-site** (Java wildcards, C#): Variance is specified at each usage: `List<? extends Animal>`.

Declaration-site is less verbose but less flexible. Java chose use-site because generics were retrofitted; Kotlin supports both (`out`/`in` at declaration, `*` projections at use).

## Unification

Unification is the core algorithm behind type inference. Given two type expressions, it finds a **substitution** (mapping of type variables to types) that makes them equal.

### Robinson's Unification Algorithm

```
unify(t1, t2):
  if t1 == t2: return {}
  if t1 is a variable: return {t1 ↦ t2}  (with occurs check)
  if t2 is a variable: return {t2 ↦ t1}  (with occurs check)
  if t1 = C(s1,...,sn) and t2 = C(r1,...,rn):
      S = {}
      for (si, ri) in zip(s1..sn, r1..rn):
          S' = unify(apply(S, si), apply(S, ri))
          S = compose(S', S)
      return S
  else: FAIL (type mismatch)
```

The **occurs check** prevents infinite types like `a = List<a>` (a type that contains itself). Most ML implementations skip the occurs check for performance and rely on the type system to prevent them structurally.

Union-find data structures make unification **near-linear** (inverse Ackermann): `O(α(n))` per operation.

## Bidirectional Type Checking

Bidirectional type checking splits inference into two modes:

- **Check mode** (`Γ ⊢ e ⇐ τ`): Given expected type `τ`, check that `e` has that type.
- **Synth mode** (`Γ ⊢ e ⇒ τ`): Synthesize (infer) the type of `e`.

```
Check(Γ, λx. e, τ₂ → τ₁) = Check(Γ, x:τ₂ ⊢ e, τ₁)
Check(Γ, e, τ)             = let τ' = Synth(Γ, e) in subsume(τ', τ)
Synth(Γ, x)               = Γ(x)
Synth(Γ, e1 e2)           = let τ = fresh()
                              Check(Γ, e1, τ → τ)  // infer from application
                              Check(Γ, e2, τ)
                              return τ
Synth(Γ, λx. e)           = cannot synthesize! Need annotation.
```

Bidirectional type checking is used by: **Haskell** (GHC), **Rust** (traits), **Scala 3**, **Lean 4**, **Agda**. It handles GADTs, dependent types, and type classes — all of which break plain Algorithm W.

> **Interview Angle**: "Why does Rust require type annotations on some closures but not others?" Rust uses bidirectional type checking. When a closure's type can be synthesized from context (e.g., passed to `map`), no annotation is needed. But `let f = |x| x;` is ambiguous because `Synth(λx. x)` fails — the return type is unknown. You must write `let f: fn(i32) -> i32 = |x| x;` or let context determine it.

## GADTs (Generalized Algebraic Data Types)

GADTs allow specifying the return type of each constructor explicitly, enabling **type-level computation**:

```haskell
data Expr a where
  Lit    :: Int  -> Expr Int
  Bool   :: Bool -> Expr Bool
  Add    :: Expr Int -> Expr Int -> Expr Int
  If     :: Expr Bool -> Expr a -> Expr a -> Expr a
  Cast   :: Expr Int -> Expr Bool   -- safe narrowing

eval :: Expr a -> a
eval (Lit n)    = n
eval (Bool b)   = b
eval (Add a b)  = eval a + eval b
eval (If c t e) = if eval c then eval t else eval e
eval (Cast n)   = eval n > 0  -- Int -> Bool, type-safe
```

The `eval` function is **type-safe by construction**: pattern matching on a `GADT` constructor refines the type variable `a` in each branch. Standard HM inference cannot handle this — you need **bidirectional type checking** or **equality constraints** in the inference algorithm.

## Existential Types

Existential types hide implementation details behind an abstract interface:

```haskell
data ShowBox = forall a. Show a => ShowBox a

showBox :: ShowBox -> String
showBox (ShowBox x) = show x  -- 'a' is existential, only Show methods available

boxes :: [ShowBox]
boxes = [ShowBox 42, ShowBox "hello", ShowBox True]
```

The type of each element is **unknown at compile time** (existential), but the `Show` constraint guarantees `show` is available. In Java, this is equivalent to a bounded wildcard: `List<?>` where `? extends Object`.

## Type Classes and Traits

### Type Classes (Haskell)

Type classes provide **ad-hoc polymorphism** — overloaded functions based on types, resolved at compile time:

```haskell
class Eq a where
  (==) :: a -> a -> Bool

instance Eq Int where
  (==) = primEqInt

instance (Eq a, Eq b) => Eq (a, b) where
  (x1, y1) == (x2, y2) = x1 == x2 && y1 == y2
```

Type class resolution is essentially **dictionary passing**: each constrained function receives an implicit record of the class methods. GHC compiles `show x` (where `Show a => ...`) into `show (dShow_a) x` where `dShow_a` is the dictionary.

### Traits (Rust)

Rust traits are similar but with two key differences:

1. **Coherence (orphan rules)**: You can only implement your trait for your type (or vice versa). This prevents overlapping instances that plague Haskell.
2. **Associated types**: Each implementation can define different associated types.

```rust
trait Iterator {
    type Item;  // associated type — different per impl
    fn next(&mut self) -> Option<Self::Item>;
}
```

## Ownership Types, Borrow Checking, and Region Inference

### Rust's Borrow Checker

Rust's type system encodes **ownership** (affine types), **borrowing** (shared `&T` and mutable `&mut T` references), and **lifetimes** (regions) into the type language.

```
Ownership rules:
1. Each value has exactly one owner.
2. When the owner goes out of scope, the value is dropped.
3. Moving a value transfers ownership (old binding is invalidated).

Borrowing rules:
1. &T: any number of shared borrows OR
2. &mut T: exactly one mutable borrow
   ... but never both simultaneously.
```

The borrow checker uses **non-lexical lifetimes (NLL)** — lifetimes are based on the last *use* of a reference, not the lexical scope. This is computed via a dataflow analysis on the MIR (Mid-level IR).

### Region Inference

Region inference (from Cyclone, adapted by Rust) **infers lifetime parameters** rather than requiring explicit annotations everywhere. The algorithm:

1. Assign each borrow a **region variable** `'_i`.
2. Generate constraints: `'_i ⊆ '_j` (region `i` outlives region `j`).
3. Solve constraints via **union-find** (each region's LCA = their union).
4. Report errors for unsatisfiable constraints (borrow lives too long).

## Gradual Typing

Gradual typing allows mixing **static** and **dynamic** typing in the same program. A `dynamic` type is compatible with any type, with runtime checks inserted at boundaries.

```typescript
// TypeScript: gradual typing in action
function add(a: number, b: number): number { return a + b; }
let x: any = add(1, "hello");  // No static error, runtime: "1hello"
```

Languages with gradual typing: **TypeScript**, **Pyret**, **Reticulated Python**, **Gradualtalk**. The theoretical guarantee: **gradual guarantees** — making a program more statically typed never changes its behavior on well-typed inputs.

## Polymorphic Recursion

Polymorphic recursion allows a function to call itself with a **different type instantiation** at each recursive call. Standard HM inference cannot infer this (it would require infinite types in the unifier).

```haskell
-- Polymorphic recursion: 'a' changes at each recursive call
data Nested a = Leaf a | Nest (Nested (a, a))

-- f :: Nested Int -> Int, but recursive call is on Nested (Int, Int)
f (Leaf x) = x
f (Nest n) = f n  -- f applied to a DIFFERENT type
```

ML/Haskell require explicit type annotations for polymorphic recursion. GHC can sometimes infer it with **extended type inference** (outside of HM).

## References

- L. Cardelli, *Structural Subtyping and the Notion of Type Safety* (1985)
- J. Dunfield & N. Krishnaswami, *Completeness and Soundness for Bidirectional Type Checking* (2021)
- The Rust Reference: Borrow Checking and Lifetimes
- S. Peyton Jones et al., *Type Classes: An Exploration of the Design Space* (1997)
- J. Siek & W. Taha, *Gradual Typing* (2006)
