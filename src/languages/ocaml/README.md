# OCaml

## Overview

OCaml (Objective Caml) is a statically typed, functional programming language with type inference. Developed at INRIA in France, it combines functional, imperative, and object-oriented programming. OCaml is known for its powerful type system, pattern matching, and performance.

## Why OCaml Matters for Interviews

- **Jane Street**: Major user — many finance interviews test OCaml
- **Type system**: Algebraic types, type inference, GADTs
- **Functional programming**: Pattern matching, immutability, higher-order functions
- **Compiler construction**: OCaml is widely used for building compilers and tools
- **Formal verification**: Used in Coq, Why3, and other proof assistants

## OCaml at a Glance

| Feature | OCaml |
|---------|-------|
| **Type system** | Static, inferred, structural |
| **Paradigm** | Functional, imperative, OOP |
| **Evaluation** | Strict (eager) |
| **Memory management** | GC (generational) |
| **Pattern matching** | First-class, exhaustive |
| **Module system** | Functors, first-class modules |

## Language Features

### Type System

```ocaml
(* Type inference *)
let x = 42          (* int *)
let f = 3.14        (* float *)
let s = "hello"     (* string *)
let b = true        (* bool *)

(* Type annotations *)
let add (x : int) (y : int) : int = x + y

(* Parametric polymorphism *)
let id x = x         (* 'a -> 'a *)
let fst (a, b) = a   (* 'a * 'b -> 'a *)
```

### Algebraic Data Types

```ocaml
(* Sum types (variants) *)
type shape =
  | Circle of float
  | Rectangle of float * float
  | Triangle of float * float * float

(* Product types (records) *)
type point = { x : float; y : float }

(* Pattern matching *)
let area = function
  | Circle r -> 3.14159 *. r *. r
  | Rectangle (w, h) -> w *. h
  | Triangle (a, b, c) ->
      let s = (a +. b +. c) /. 2.0 in
      sqrt (s *. (s -. a) *. (s -. b) *. (s -. c))

(* Option type *)
type 'a option = None | Some of 'a

let safe_div x y =
  if y = 0 then None
  else Some (x / y)
```

### Pattern Matching

```ocaml
(* Exhaustive matching *)
let describe lst = match lst with
  | [] -> "empty"
  | [x] -> "singleton: " ^ string_of_int x
  | [x; y] -> "pair"
  | _ -> "longer list"

(* Nested patterns *)
type expr =
  | Lit of int
  | Add of expr * expr
  | Mul of expr * expr

let rec eval = function
  | Lit n -> n
  | Add (a, b) -> eval a + eval b
  | Mul (a, b) -> eval a * eval b

(* Guards *)
let classify x = match x with
  | n when n > 0 -> "positive"
  | n when n < 0 -> "negative"
  | _ -> "zero"
```

### Functions and Higher-Order

```ocaml
(* Lambda *)
let double = fun x -> x * 2

(* Higher-order functions *)
let apply f x = f x
let compose f g x = f (g x)

(* Partial application *)
let add x y = x + y
let add5 = add 5     (* int -> int *)
add5 3               (* 8 *)

(* Pipeline operator *)
let result =
  [1; 2; 3; 4; 5]
  |> List.filter (fun x -> x mod 2 = 0)
  |> List.map (fun x -> x * x)
  |> List.fold_left (+) 0
(* 4 + 16 = 20 *)
```

### Module System

```ocaml
(* Module signature *)
module type STACK = sig
  type 'a t
  val empty : 'a t
  val push : 'a -> 'a t -> 'a t
  val pop : 'a t -> ('a * 'a t) option
end

(* Module implementation *)
module Stack : STACK = struct
  type 'a t = 'a list
  let empty = []
  let push x s = x :: s
  let pop = function
    | [] -> None
    | x :: s -> Some (x, s)
end

(* Functors *)
module MakeSet (Ord : Set.OrderedType) = struct
  include Set.Make(Ord)
end
```

### Imperative Features

```ocaml
(* Mutable references *)
let counter = ref 0
counter := !counter + 1
print_int !counter

(* Arrays (mutable) *)
let arr = [|1; 2; 3|]
arr.(0) <- 10

(* Loops *)
for i = 0 to 10 do
  print_int i
done;

while !counter > 0 do
  counter := !counter - 1
done;

(* Exception handling *)
exception NotFound of string

let find key assoc =
  try List.assoc key assoc
  with Not_found -> raise (NotFound key)
```

## Memory Management

```ocaml
(* OCaml uses a generational GC *)
(* Minor heap: young objects (fast, copying) *)
(* Major heap: old objects (mark-sweep) *)

(* Immutable data → no aliasing issues *)
(* Tail recursion → no stack overflow *)

(* Tail-recursive factorial *)
let fact n =
  let rec aux acc n =
    if n <= 1 then acc
    else aux (acc * n) (n - 1)
  in
  aux 1 n
```

## Interview Focus Areas

1. **Pattern matching** — Exhaustive matching, nested patterns, GADTs
2. **Type inference** — Hindley-Milner, unification, let-polymorphism
3. **Algebraic data types** — Sum types, product types, recursive types
4. **Module system** — Signatures, functors, first-class modules
5. **Functional patterns** — Fold, map, filter, composition
6. **Tail recursion** — Accumulator pattern, `@` operator performance
7. **OCaml runtime** — GC, representation of values, boxed vs unboxed

## Related Topics

- [Functional Programming](../../concurrency/functional/) — FP concepts
- [Type Systems](../../arch/) — Type theory
- [Compiler Construction](../../os/) — Parsing, AST
- [Rust](../rust/) — Similar type system concepts (algebraic types, pattern matching)
