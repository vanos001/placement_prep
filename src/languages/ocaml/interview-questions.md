# OCaml Interview Questions

## Type System

### Q1: What is type inference?

OCaml automatically deduces types without explicit annotations using Hindley-Milner type inference.

```ocaml
let f x y = x + y    (* inferred: int -> int -> int *)
let g x y = x :: y   (* inferred: 'a -> 'a list -> 'a list *)
let h x = [x; x]     (* inferred: 'a -> 'a list *)
```

The algorithm uses unification: it generates type constraints and solves them.

### Q2: What are algebraic data types?

```ocaml
(* Sum types: OR *)
type color = Red | Green | Blue
type 'a tree = Leaf | Node of 'a tree * 'a * 'a tree

(* Product types: AND *)
type point = { x : float; y : float }
type person = { name : string; age : int }

(* Combining *)
type shape =
  | Circle of { radius : float }
  | Rect of { width : float; height : float }
```

### Q3: What is the value restriction?

```ocaml
(* This is fine *)
let id x = x          (* 'a -> 'a *)

(* Not an error, but r becomes monomorphic: '_a list ref *)
let r = ref []

(* Solution: use a function *)
let make_ref () = ref []  (* unit -> 'a list ref *)
```

The value restriction prevents unsoundness with mutable references. Only syntactic values (constants, functions, constructors) can be polymorphic.

### Q4: Phantom types?

```ocaml
type locked
type unlocked

type 'a door = { room : string }

let open_door : locked door -> unlocked door =
  fun d -> { room = d.room }

let close_door : unlocked door -> locked door =
  fun d -> { room = d.room }

(* Type-safe state machine at compile time *)
```

## Pattern Matching

### Q5: What is exhaustiveness checking?

```ocaml
type day = Mon | Tue | Wed | Thu | Fri | Sat | Sun

let is_weekend d = match d with
  | Sat | Sun -> true
  | Mon | Tue | Wed | Thu | Fri -> false
(* Compiler ensures all cases covered *)

(* Incomplete match → warning *)
let bad d = match d with
  | Mon -> "Monday"
  (* Warning: missing cases *)
```

### Q6: Or-patterns and when-clauses?

```ocaml
(* Or-patterns *)
let is_vowel c = match c with
  | 'a' | 'e' | 'i' | 'o' | 'u' -> true
  | _ -> false

(* When-clauses (guards) *)
let describe x = match x with
  | n when n > 0 -> "positive"
  | n when n < 0 -> "negative"
  | _ -> "zero"
```

## Modules

### Q7: What are functors?

```ocaml
(* Functor: module function *)
module MakeQueue (Element : sig type t end) = struct
  type t = Element.t list
  let empty = []
  let enqueue x q = q @ [x]
  let dequeue = function
    | [] -> None
    | x :: q -> Some (x, q)
end

(* Usage *)
module IntQueue = MakeQueue(struct type t = int end)
```

### Q8: First-class modules?

```ocaml
(* Pack a module into a value *)
let m = (module Set.Make(Int) : Set.S with type elt = int)

(* Pass modules as arguments *)
let sort (module Ord : Set.OrderedType) lst =
  List.sort Ord.compare lst

(* Existential types *)
type packed = P : (module S with type t = 'a) * 'a -> packed
```

## Functional Patterns

### Q9: What is a GADT?

```ocaml
type _ expr =
  | Lit : int -> int expr
  | Bool : bool -> bool expr
  | Add : int expr * int expr -> int expr
  | If : bool expr * 'a expr * 'a expr -> 'a expr

let rec eval : type a. a expr -> a = function
  | Lit n -> n
  | Bool b -> b
  | Add (a, b) -> eval a + eval b
  | If (c, t, e) -> if eval c then eval t else eval e
```

### Q10: Tail recursion?

```ocaml
(* Non-tail-recursive: uses stack *)
let rec sum = function
  | [] -> 0
  | x :: xs -> x + sum xs

(* Tail-recursive: constant stack *)
let sum lst =
  let rec aux acc = function
    | [] -> acc
    | x :: xs -> aux (acc + x) xs
  in
  aux 0 lst

(* Using List.fold_left (tail-recursive) *)
let sum lst = List.fold_left (+) 0 lst
```

### Q11: Map, filter, fold?

```ocaml
(* Map *)
let doubled = List.map (fun x -> x * 2) [1; 2; 3]
(* [2; 4; 6] *)

(* Filter *)
let evens = List.filter (fun x -> x mod 2 = 0) [1; 2; 3; 4]
(* [2; 4] *)

(* Fold (left) *)
let sum = List.fold_left (+) 0 [1; 2; 3; 4]
(* 10 *)

(* Fold (right) *)
let lst = List.fold_right (fun x acc -> x :: acc) [1; 2; 3] []
(* [1; 2; 3] *)
```

## Advanced

### Q12: What are OCaml objects?

```ocaml
(* Object types are structural *)
type printable = < print : unit >

let obj = object
  method print = print_endline "hello"
end

(* Polymorphic methods *)
type 'a printer = < print : 'a -> unit >

(* Objects vs modules: objects are first-class values *)
```

### Q13: Polymorphic variants?

```ocaml
(* Open variants *)
type colors = [ `Red | `Green | `Blue ]
type extended = [ colors | `Yellow ]

(* No need to declare upfront *)
let handle = function
  | `Red -> "stop"
  | `Green -> "go"
  | `Yellow -> "caution"

(* Subtyping *)
let f (x : [< `Red | `Green | `Blue]) = match x with
  | `Red -> 1
  | `Green -> 2
  | `Blue -> 3
```

### Q14: Labeled and optional arguments?

```ocaml
(* Labeled arguments *)
let make ~name ~age = { name; age }
make ~name:"Alice" ~age:25

(* Optional arguments *)
let ?(prefix="Hello") name =
  prefix ^ ", " ^ name

greet "Alice"           (* "Hello, Alice" *)
greet ~prefix:"Hi" "Alice"  (* "Hi, Alice" *)
```

### Q15: PPX (Preprocessor Extensions)?

```ocaml
(* Derive serializers *)
type point = { x: int; y: int } [@@deriving show, eq]

(* Let syntax *)
let%bind x = some_computation in
let%map y = another_computation in
x + y
```

## Comparison with Other Languages

### Q16: OCaml vs Haskell?

| OCaml | Haskell |
|-------|---------|
| Strict (eager) | Lazy by default |
| Type inference (local) | Type inference (global) |
| Side effects easy | Side effects controlled (IO monad) |
| No type classes | Type classes |
| Module functors | Type class instances |

### Q17: OCaml vs Rust?

| OCaml | Rust |
|-------|------|
| GC | Ownership system |
| Immutable by default | Immutable by default |
| Pattern matching | Pattern matching |
| Algebraic types | Enums |
| Higher-order functions | Closures |
| No null | Option type |
| Easier to write | Memory-safe without GC |

## Related Topics

- [Rust](../rust/) — Similar type system concepts
- [Functional Programming](../../concurrency/) — FP patterns
- [Type Systems](../../arch/) — Type theory
