# Monads and Effect Systems: return, bind, and the Programmable Semicolon

A **pure function** maps inputs to outputs and nothing else: same call, same value, no state changes, no I/O, no exceptions. That property - **referential transparency** - is what lets you replace `f(x)` with its value and reason equationally (the typing machinery behind it is [Hindley-Milner](./hindley-milner.md)). Real programs, though, read files, throw, roll back, choose. **Effects** break transparency: `getChar()` returns something different each call, `throw` never returns, `rand()` is not a function in any honest sense. The insight due to Moggi (1991) and turned into practice by Wadler (1994) is not to forbid effects but to make them *values*: an effectful computation producing an `a` becomes a plain value of type `M a`, where `M` is a type constructor, and two operations - `return` and `>>=` (bind) - sequence those values under three laws. The monad is that interface plus its laws; the laws are what make effectful code composable and the pure reasoning sound.

This page builds the idea from the problem statement, walks the standard instances (Maybe, Either, List, State, Reader, Writer, Cont), desugars `do`-notation, places the theory (Moggi's computational lambda-calculus, Kleisli composition, monad transformers), and contrasts monads with **algebraic effects and handlers** - the model behind Koka, Unison, and OCaml 5, covered hands-on in [Effect Systems](../compilers/advanced/effect-systems.md). A runnable Python demo implements Maybe and State and machine-checks the laws.

## The problem: effects in a pure language

For a pure `f : a -> b`, the rewrite `f(x) + f(x) = 2 * f(x)` is safe. The moment effects sneak in it is not: if `f` throws, the second call may never happen; if `f` reads a file, the two calls may disagree; if `f` is nondeterministic, running it twice changes the result set. Imperative languages resolve the tension by abandoning the pure model (every statement may effect). Haskell keeps the model and instead forces effects to appear *in the type* and be sequenced *in the term*:

```text
   value level                computation level (effectful)
   -----------                ------------------------------
   x, y  : a                  getChar : M Char          one run of input
   f, g  : a -> b             h       : a -> M b        "effects, then a b"
   f x + f x                  getChar >>= \c1 -> getChar >>= \c2 -> return [c1,c2]
                              -- two reads, visible and ordered:
                              -- an optimizer may not drop the second one
```

The type `M a` reads "a computation that, when run, performs `M`'s effects and yields an `a`". Because effects are now ordinary data that only bind may combine, substitution happens exactly where the program's binds say it does - the equational reasoning of the pure core (see [Lambda Calculus](./lambda-calculus.md)) survives, and the effectful shell is disciplined by composition.

## A monad, demystified

Concretely, a monad over a type constructor `M` is three things:

- a **type constructor** `M : * -> *` - `Maybe`, `[]`, `IO a`, `State s a`;
- `return : a -> M a` (also `unit` or `pure`) - lift a plain value into a trivial computation;
- `bind : M a -> (a -> M b) -> M b` (Haskell `>>=`) - run a computation, feed its result to the next step.

And three laws, which are exactly what stops `M` from being an arbitrary API:

```text
   return x >>= f    =  f x                        left identity:
                       wrap-then-run is just run

   m >>= return      =  m                          right identity:
                       a trailing wrap changes nothing

   (m >>= f) >>= g   =  m >>= (\x -> f x >>= g)    associativity:
                       how the sequencing groups is irrelevant
```

Reading `>>=` as a semicolon makes Wadler's phrase land. The semicolon between two statements is normally hardcoded: fixed order, fixed data flow, fixed error behavior. A monad is a **programmable semicolon** - each instance decides what flows between the statements (a failure flag, an error, a list of alternatives, a state thread) and what "run the next statement" even means. Note also what the laws are: theorems, not API conventions. They make bind behave exactly like ordinary function composition, so regrouping chains of binds is a soundness-preserving step - the same discipline of typed terms the [Curry-Howard](./curry-howard.md) correspondence formalizes from the pure side.

**Applicative vs monad.** McBride & Paterson (2008) isolate an intermediate strength: an *applicative* functor sequences effects whose structure is fixed in advance - you cannot pick the next effect based on the value flowing through. A monad's bind can: `do x <- get; if x > 0 then save x else abort` is data-dependent and needs bind. If a pipeline never branches on intermediate values, applicative suffices and buys a real prize: applicative effects always compose, monads in general do not (the root of the transformer pain below). Every monad is an applicative; not every applicative is a monad - a fixed-format record parser is applicative, parsing a context-sensitive grammar is monadic.

## The standard instances

The pattern earns its keep by how many distinct "effects" collapse to the same two operations:

| Monad                  | Effect modeled                | Canonical operation      | Failure / spread behavior        |
|------------------------|-------------------------------|--------------------------|----------------------------------|
| `Maybe`                | failure, absence              | `Nothing` short-circuits | first `Nothing` wins             |
| `Either e` / `Result`  | error carrying a payload      | `Left e` propagates      | first `Left` wins                |
| `[]` (List)            | nondeterminism, all results   | `concatMap`              | empty list kills the branch      |
| `State s`              | threaded mutable state        | `get` / `put`            | never fails, just threads        |
| `Reader r`             | read-only environment         | `ask`                    | no failure; shared config        |
| `Writer w`             | accumulation (log, audit)     | `tell`                   | appends monoidally               |
| `Cont r`               | continuation-passing style    | `callCC`                 | rest of program as argument      |

Two families hide in that table. Maybe, Either, and List *short-circuit or multiply*: their bind decides whether the next step runs at all, and how often. State, Reader, and Writer *thread* an ambient quantity: their bind plumbs a hidden parameter through every step. Same three operations, wildly different meanings - that inversion of meaning is the whole trick.

## do-notation is desugaring

`do`-notation is syntax for nested binds; nothing more:

```text
   do x <- parse tok1              parse tok1 >>= \x ->
      y <- parse tok2         =    parse tok2 >>= \y ->
      return (x + y)               return (x + y)

   fully desugared, right-nested:
   parse tok1 >>= (\x -> parse tok2 >>= (\y -> return (x + y)))
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                each continuation encloses everything after it -
                that nesting is where "the rest" hides
```

Two small sugars ride along: `let x = e` splices a pure value by substitution (no bind involved), and `_ <- m` sequences without naming the result. Note what the notation is *not*: it is not exception handling, not a thread, not lazy evaluation - those are just different monads underneath the same desugaring.

## The theory, briefly

- **Moggi (1991)** introduced the computational lambda-calculus: a two-level extension of the simply typed [lambda calculus](./lambda-calculus.md) that separates values from computations, with a modality mapping value types to computation types. Its reading is the paper's title: monads are *notions of computation*. Partiality, nondeterminism, exceptions, state, and I/O each get a monad, and the calculus stays sound because substitution is assumed only where it actually holds.
- **Wadler (1994)** (Marktoberdorf lecture notes) carried that semantics into programming practice: each monad is an *interpreter* written in the host language. `Maybe` interprets failure by stopping, `State` interprets by threading, and user programs stay written in do-notation while the interpreter underneath changes - the "programmable semicolon" made executable.
- **Kleisli composition** `>=> : (a -> M b) -> (b -> M c) -> (a -> M c)`, defined `f >=> g = \x -> f x >>= g`, makes the laws read as a monoid: `return` is the identity element and `>=>` is associative. This is the cleanest statement of what the laws buy - effectful functions compose like plain ones.
- **Monad transformers** (Liang, Hudak & Jones, POPL 1995) stack monads - State over Maybe is "state that can fail". Each layer needs a `lift`, the stack order changes the meaning (Maybe over State vs State over Maybe are different computations), and boilerplate grows with depth: the practical symptom that monads do not compose in general.

## Beyond monads: algebraic effects and handlers

Monads put the sequencing discipline in the type but fix each effect's meaning at its definition site, and stacking is clumsy. **Algebraic effects and handlers** (Plotkin & Pretnar) invert the design: code *performs* named operations (`ask`, `get`, `throw`), and a **handler** in scope interprets each operation, receiving the rest of the computation as a one-shot resumption it may resume, discard, or rerun. Koka and Unison type the effects directly; OCaml 5 ships handlers in the runtime. Where each model lands:

| Model                   | Errors surface as             | Sequencing                 | Composition story               |
|-------------------------|-------------------------------|----------------------------|---------------------------------|
| Haskell `IO` + monads   | values in `Either` / `Maybe`  | binds / do-notation        | transformers per stack layer    |
| Rust `Result` / `Option`| enums you must match or `?`   | `?` = early-return bind    | no stack; one error channel     |
| Java checked exceptions | `throws` clauses, try/catch   | implicit control flow      | invisible in the value's type   |
| Koka / Unison / OCaml 5 | operations + handlers         | perform, handle, resume    | handlers stack over one runtime |

Rust's `?` operator is a Maybe/Either bind in disguise - it desugars to early return on the error arm (see [Rust error handling](../languages/rust/error-handling-deep.md)). The handler/resumption machinery is delimited continuation wearing a typed interface; the runnable interpreter, one-shot design, and the OCaml 5 / Koka / Unison comparison live in [Effect Systems](../compilers/advanced/effect-systems.md). A third middle path, the **free monad**, reifies binds into a tree of instructions that an interpreter walks - the same "program as data" move, with heavier ergonomics.

## Demo: Maybe and State in pure Python

Python's `>>` operator plays Haskell's `>>=` (fluent bind). A tiny `add x y` token pipeline is written twice - imperative with hand-coded failure checks, monadic with bind doing the plumbing - then the three monad laws are machine-checked on samples of both monads:

```python
"""Monads in pure Python: Maybe (short-circuit) and State (threaded state).
Python's >> plays Haskell's >>= (fluent bind). A tiny 'add x y' parser shows
imperative vs monadic failure plumbing, then the three monad laws are
machine-checked on samples of both monads."""

# ---- Maybe: Just a | Nothing; bind short-circuits on Nothing ----
class Just:
    __slots__ = ("value",)
    def __init__(self, value): self.value = value
    def __rshift__(self, f): return f(self.value)    # Just a >>= f  =  f a
    def __eq__(self, o): return type(o) is Just and o.value == self.value
    def __repr__(self): return "Just(%r)" % (self.value,)

class Nothing:
    __slots__ = ()
    def __rshift__(self, f): return self             # Nothing >>= f = Nothing
    def __eq__(self, o): return type(o) is Nothing
    def __repr__(self): return "Nothing"

def mreturn(a): return Just(a)                       # unit: a -> M a

# ---- State: a computation s -> (a, s); bind threads the state ----
class State:
    __slots__ = ("run",)
    def __init__(self, run): self.run = run
    def __rshift__(self, f):                         # m >>= f
        def run(s):
            a, s1 = self.run(s)
            return f(a).run(s1)
        return State(run)

def st_return(a): return State(lambda s: (a, s))
def st_get():     return State(lambda s: (s, s))
def st_put(s):    return State(lambda _: ((), s))

# ---- 'add x y' parsed two ways: sum of the two ints, or failure ----
def imperative(toks):                 # every failure hand-coded
    if len(toks) != 3:        return None
    if toks[0] != "add":      return None
    if not toks[1].isdigit(): return None
    if not toks[2].isdigit(): return None
    return int(toks[1]) + int(toks[2])

def at(toks, i):                      # Maybe-flavored token access
    return Just(toks[i]) if i < len(toks) else Nothing()

def num(tok):                         # Maybe-flavored int parse
    return Just(int(tok)) if tok.isdigit() else Nothing()

def monadic(toks):                    # bind does all the plumbing
    return (at(toks, 0)
            >> (lambda op: Just(op) if op == "add" else Nothing())
            >> (lambda _: at(toks, 1) >> num)
            >> (lambda x: at(toks, 2) >> num
                          >> (lambda y: mreturn(x + y))))

# ---- a State program: grow a log without ever naming it ----
def add_log(entry):
    return st_get() >> (lambda log:
           st_put(log + [entry]) >> (lambda _: st_return(entry)))

program = add_log("add") >> (lambda _: add_log(40)) >> (lambda _: add_log(2))

if __name__ == "__main__":
    for toks in (["add", "40", "2"], ["add", "40", "x"],
                 ["sub", "40", "2"], ["add", "40"]):
        print("parse %-22r imperative=%-4s monadic=%s"
              % (toks, imperative(toks), monadic(toks)))
    print("state program from []  ->", program.run([]))
    print("state program from [9] ->", program.run([9]))

    f, g, m = (lambda x: Just(x + 1)), (lambda x: Just(x * 2)), Just(3)
    print("Maybe left identity :", (mreturn(3) >> f) == f(3))
    print("Maybe right identity:", (m >> mreturn) == m)
    print("Maybe associativity :", ((m >> f) >> g) == (m >> (lambda x: f(x) >> g)))

    sf = lambda x: State(lambda s: (x * 2, s + 1))   # double, tick a counter
    sg = lambda y: State(lambda s: (y + 1, s + 1))   # bump,   tick a counter
    sm = st_return(3)
    print("State  left identity :", (st_return(3) >> sf).run(0) == sf(3).run(0))
    print("State  right identity:", (sm >> st_return).run(0) == sm.run(0))
    print("State  associativity :",
          ((sm >> sf) >> sg).run(0) == (sm >> (lambda x: sf(x) >> sg)).run(0))
```

```text
parse ['add', '40', '2']     imperative=42   monadic=Just(42)
parse ['add', '40', 'x']     imperative=None monadic=Nothing
parse ['sub', '40', '2']     imperative=None monadic=Nothing
parse ['add', '40']          imperative=None monadic=Nothing
state program from []  -> (2, ['add', 40, 2])
state program from [9] -> (2, [9, 'add', 40, 2])
Maybe left identity : True
Maybe right identity: True
Maybe associativity : True
State  left identity : True
State  right identity: True
State  associativity : True
```

Read the traces against the prose. In the monadic pipeline no function checks for failure: `Nothing >> f` skips `f` entirely, which is the entire Maybe semantics in one method body. The State program grows a log without ever naming it - that is "bind threads the state" mechanically. The law checks are not decoration: they certify that fluent chaining composes the way ordinary function composition does, so refactoring `m >> f >> g` into grouped or Kleisli form is safe.

## Interview-facing takeaways

- **"What problem does a monad solve?"** Sequencing effectful steps in a pure language without losing referential transparency: effects become values of type `M a`, order and data flow become explicit binds, and each effect's meaning lives in one instance instead of scattered across call sites.
- **"State the three laws and why they matter."** `return x >>= f = f x`, `m >>= return = m`, and bind associativity. They make bind behave like composition (via Kleisli `>=>`: `return` is the unit, `>=>` associative), so code refactoring across groupings is sound and library-level reasoning is possible at all.
- **"Maybe vs Either vs exceptions?"** All three are failure. Maybe discards *why* (cheapest, short-circuits); Either carries an error value through the same shape; exceptions abort through a hidden channel invisible in types. Monadic Either makes the failure path a value you can map over, sequence, and test purely.
- **"Why do effect-handler languages bother, given monads?"** Handlers interpret operations at the call site instead of at the monad definition, effects stack over one runtime instead of transformer towers, and data-dependent control (retry, resume twice, log) falls out of the resumption - the tradeoffs monad transformers pay in `lift` boilerplate.
- **"Is Rust's `?` a monad?"** In spirit yes: `?` on `Result` is exactly `Either`'s bind plus early return, and `Option`/`Result` follow the monad laws. What Rust lacks is a general user-writable monad interface with do-notation; `?` is a fixed, built-in instance for two types.

## References

- Eugenio Moggi - *Notions of Computation and Monads*, Information and Computation 93(1):55-92, 1991 (computational lambda-calculus; monads as notions of computation): [doi.org/10.1016/0890-5401(91)90052-4](https://doi.org/10.1016/0890-5401(91)90052-4)
- Philip Wadler - *Monads for Functional Programming*, Marktoberdorf summer school notes (Bastad), in Advanced Functional Programming, LNCS 925, 1995: [homepages.inf.ed.ac.uk/wadler/papers/marktoberdorf/baastad.pdf](https://homepages.inf.ed.ac.uk/wadler/papers/marktoberdorf/baastad.pdf)
- Conor McBride, Ross Paterson - *Applicative Programming with Effects*, Journal of Functional Programming 18(1):1-13, 2008 (the applicative/monad divide): [doi.org/10.1017/S0956796807006326](https://doi.org/10.1017/S0956796807006326)
- Gordon Plotkin, Matija Pretnar - *Handling Algebraic Effects*, Logical Methods in Computer Science 9(4:23), 2013 (journal version; the ESOP 2009 "Handlers of Algebraic Effects" introduced the framework): [doi.org/10.2168/lmcs-9(4:23)2013](https://doi.org/10.2168/lmcs-9(4:23)2013)
- Sheng Liang, Paul Hudak, Mark Jones - *Monad Transformers and Modular Interpreters*, POPL 1995 (layered monads, `lift`)
- OCaml 5 manual - *Effect Handlers* chapter (one-shot resumptions, `Effect.Deep`/`Shallow`): [ocaml.org/manual/latest/effects.html](https://ocaml.org/manual/latest/effects.html)
- Haskell `base` library - *Control.Monad* documentation (`>>=`, `return`, Kleisli `>=>`, `mapM`, the standard instance zoo): [hackage.haskell.org/package/base/docs/Control-Monad.html](https://hackage.haskell.org/package/base/docs/Control-Monad.html)
