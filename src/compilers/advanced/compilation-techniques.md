# Compilation Techniques

This chapter covers core program transformations that bridge the gap between high-level source languages (especially functional languages with first-class functions) and low-level target machines. These techniques are the bread and butter of compilers for ML-family languages, Scheme, Haskell, and increasingly JavaScript and Rust.

## CPS (Continuation-Passing Style)

### What Is CPS?

In continuation-passing style, **no function ever returns** — instead, every function takes an extra argument called the **continuation**, which represents "what to do next." The continuation is itself a function.

```scheme
;; Direct style
(define (fact n)
  (if (= n 0)
      1
      (* n (fact (- n 1)))))

;; CPS-transformed
(define (fact-cps n k)
  (if (= n 0)
      (k 1)                          ;; pass 1 to continuation
      (fact-cps (- n 1)              ;; tail call!
                (lambda (v)
                  (k (* n v))))))    ;; multiply after recursive call
```

The CPS transform makes **all function calls tail calls**, eliminating the need for a return stack. This is the key insight used by compilers like **Chez Scheme**, **Standard ML of New Jersey (SML/NJ)**, and historically **LLVM's initial backend design**.

### The CPS Transform

The transform `[[e]] k` takes an expression `e` and a continuation `k`:

```
[[ n ]]                k = k(n)
[[ x ]]                k = k(x)
[[ λx. e ]]           k = k(λx. [[e]])
[[ e1 e2 ]]           k = [[e1]] (λf. [[e2]] (λv. f v k))
[[ if e then e1 e2 ]] k = [[e]]  (λb. if b then [[e1]] k else [[e2]] k)
[[ let x = e1 in e2 ]] k = [[e1]] (λv. let x = v in [[e2]] k)
```

The key property: after CPS transformation, **every call is a tail call**. This makes control flow explicit as data flow (continuations are just functions).

> **Interview Angle**: "Why did early compilers like SML/NJ use CPS as their IR?" Because CPS makes control flow first-class: exceptions, coroutines, and call/cc are just different ways of manipulating the continuation. CPS-based IRs simplify optimization because control flow becomes data flow.

### CPS in Practice

- **Chez Scheme**: The entire compiler is structured around CPS. The IR is CPS, and the code generator does "unCPS" as the final step.
- **LLVM**: Originally designed with a CPS-like IR. Later abandoned in favor of SSA (CPS is SSA for functional programs — see Kelsey 1995).
- **JavaScript engines**: Node.js callbacks are essentially manual CPS. Promises/async-await are a syntactic sugar that restores direct style.

## Closure Conversion

First-class functions (lambdas) can **capture free variables** from their enclosing scope. The compiler must transform these into closed functions that only reference their formal parameters.

```ml
(* Before closure conversion *)
let make_adder n = fun x -> x + n

(* After closure conversion *)
(* Closure = (code pointer, environment record) *)
type 'a closure = Closure of ('a -> int) * env
and env = { n : int }

let make_adder n = Closure ((fun env x -> x + env.n), { n })
```

Every lambda becomes a **closure record** containing:
1. A pointer to the generated function code.
2. An environment record with the values of free variables.

OCaml's runtime represents closures as a pair of `(code_ptr, env_block)` where the env block is a heap-allocated array. The GC must track closure environments as roots.

## Lambda Lifting

Lambda lifting is the dual of closure conversion. Instead of heap-allocating an environment, **free variables are passed as additional parameters** to the lifted function.

```ml
(* Before *)
let rec f x = 
  let g y = x + y in
  g 3

(* After lambda lifting *)
let g_lifted x y = x + y   (* x is now a parameter *)
let rec f x = g_lifted x 3
```

Lambda lifting eliminates heap-allocated closures at the cost of **parameter bloat** — every call site must pass all free variables. In practice, compilers use a hybrid: lambda-lift small environments, closure-convert large ones. GCC uses tree-nested-function lowering (a form of lambda lifting for C nested functions).

## Defunctionalization

Defunctionalization eliminates higher-order functions by **converting every function value into a tagged union (sum type)** of all possible functions that could appear at that program point.

```ml
(* Before: higher-order *)
let rec fold f acc lst = match lst with
  | [] -> acc
  | x :: xs -> fold f (f acc x) xs

let sum = fold (+) 0 [1;2;3]

(* After defunctionalization *)
type fold_fun = ADD

let apply_fold_fun (fn : fold_fun) acc x = match fn with
  | ADD -> acc + x

let rec fold_dispatch fn acc lst = match lst with
  | [] -> acc
  | x :: xs -> fold_dispatch fn (apply_fold_fun fn acc x) xs

let sum = fold_dispatch ADD 0 [1;2;3]
```

Defunctionalization is a **first-class to first-order transformation**. It's used in Kotlin's coroutine compiler (suspend lambdas become state machines) and is the theoretical basis for **Reynolds' defunctionalization theorem**.

> **Interview Angle**: "How do Kotlin coroutines work at the bytecode level?" The Kotlin compiler defunctionalizes suspend lambdas into a state machine class. Each suspension point becomes a `when` label, and the continuation is a `label + saved locals` tuple.

## Partial Evaluation

Partial evaluation is a program specialization technique: given a program `P(x, y)` where `x` is known at compile time, produce a **residual program** `P_x(y)` that is specialized for that `x`.

```c
// Original
int power(int base, int exp) {
    if (exp == 0) return 1;
    return base * power(base, exp - 1);
}

// After partial evaluation with base = 2
int power_of_2(int exp) {
    if (exp == 0) return 1;
    return 2 * power_of_2(exp - 1);  // specialized!
}
```

**Futamura projections** are the theoretical limit:
- **First Futamura projection**: `PE(P, input) → specialized_P` — specialize a program.
- **Second Futamura projection**: `PE(PE_compiler, P) → compiler_for_P` — specialize the PE compiler with program P to get a compiler that compiles P.
- **Third Futamura projection**: `PE(PE_compiler, PE_compiler) → compiler_generator` — a self-applicable partial evaluator generates compilers.

Real implementations: **C-Mix** (C partial evaluator), **Similix** (Scheme), **Tempo** (C). The **LLVM -O2** pipeline performs a form of partial evaluation through constant propagation + dead code elimination.

## Supercompilation

Supercompilation, developed by V.F. Turchin, is a more aggressive form of program transformation than partial evaluation. It can:
- **Fold** recursive computations into iterative loops.
- **Unfold** definitions that partial evaluation cannot (whistleblowing).
- **Drive** evaluation through non-trivial conditional branches.

The **Supercompiler** (by Turchin) and **Supero** (by Mitchell) for Haskell are implementations. Supercompilation can prove program equivalences that require generalization of intermediate results — it's Turing-complete in its transformation power.

## Staging and Multi-Stage Programming

Staging makes the distinction between **compile-time** and **run-time** explicit in the language:

```scala
// Scala 3 metaprogramming (staging)
inline def power(b: Double, n: Int): Double =
  if n == 0 then 1.0
  else if n % 2 == 0 then power(b * b, n / 2)  // staged: b*b at compile time
  else b * power(b, n - 1)

// power(2.0, 16) compiles to: 65536.0 (all computation at compile time)
```

Multi-stage languages: **MetaOCaml** (`.< .>` brackets), **Scala 3** (inline/quotes/splices), **Rust** (const fn is limited staging). Staging avoids code bloat from C++ templates while achieving similar zero-cost abstractions.

## Macro Systems

### Hygienic Macros

Hygienic macros (Scheme, Rust, Julia) guarantee that macro-expanded code respects the **lexical scope** of the macro definition, preventing accidental capture.

```rust
// Rust: hygienic by default
macro_rules! log {
    ($($arg:expr),*) => {{
        println!($($arg),*);
    }};
}

// A variable 'x' inside the macro definition cannot capture
// a variable 'x' at the call site, and vice versa.
```

Implementation: Rust's macro system tracks **syntax contexts** (spans with hygiene marks) that prevent name capture. Scheme's `syntax-rules` uses *marks* — each macro expansion adds a mark to introduced identifiers.

### Procedural Macros (Rust)

Rust's **procedural macros** (`#[derive]`, attribute macros, function-like macros) operate on the **token stream** (or `syn` AST) at compile time. They run as a separate compiler crate:

```rust
// proc-macro crate
#[proc_macro_derive(Builder)]
pub fn derive_builder(input: TokenStream) -> TokenStream {
    let ast = parse_macro_input!(input as DeriveInput);
    // Generate Builder struct and impl
    let expanded = generate_builder(&ast);
    TokenStream::from(expanded)
}
```

### Comparison of Macro Approaches

| Approach | Language | Hygiene? | Turing-Complete? | Example |
|----------|----------|----------|-----------------|---------|
| C preprocessor | C/C++ | No | No (textual) | `#define MAX(a,b) ...` |
| `syntax-rules` | Scheme/Racket | Yes | No (pattern-matching) | `(syntax-rules () ...)` |
| `syntax-case` | Scheme | Yes | Yes | `(syntax-case stx () ...)` |
| Procedural | Rust | Yes | Yes | `#[proc_macro]` |
| Template Haskell | Haskell | Partial | Yes | `[| ... |]` |
| Metaprogramming | Zig | N/A (comptime) | Yes | `comptime { ... }` |

## Metaprogramming and Reflection

- **Reflection** (Java, C#, Python): Inspect and modify program structure **at runtime** via `Class.forName()`, `typeof`, `getattr`. Expensive due to runtime type lookup.
- **Compile-time metaprogramming** (Zig `comptime`, D `mixin`, C++ `constexpr`): Execute code **during compilation** to generate types, functions, and constants.
- **Zig's comptime**: The entire Zig language is available at compile time. Vectors, hash maps, and parsers can be computed at compile time with zero runtime cost.

```zig
// Zig: compile-time computation
const Grid = comptime blk: {
    var grid: [10][10]u8 = undefined;
    for (grid) |*row| for (row) |*cell| cell.* = 0;
    break :blk grid;
};
// Grid is a compile-time constant — no runtime initialization
```

## Transformation Pipeline for Functional Languages

```mermaid
flowchart LR
    A[Source with<br/>closures & HOFs] --> B[CPS Transform]
    B --> C[Closure Conversion]
    C --> D[Lambda Lifting /
/> Defunctionalization]
    D --> E[First-Order IR]
    E --> F[Standard SSA<br/>Optimizations]
    F --> G[Code Generation]
```

## References

- A. Appel, *Compiling with Continuations* (1992)
- O. Danvy, *CPS Transformations* (survey, BRICS, 1999)
- P. Turchin, *The Concept of a Supercompiler* (1986)
- C. Consel & O. Danvy, *Static and Dynamic Semantics Processing* (partial evaluation)
- R. Hirschfeld & A. Nierstratz, *Hygienic Macro Expansion* (2008)
- Zig documentation on comptime: <https://ziglang.org/documentation/master/#comptime>
