# CPS Transformation & Defunctionalization

A continuation is the rest of a computation, reified as a value. Most languages hide it in the return address at the bottom of the stack; **continuation-passing style (CPS)** drags it into the open by passing it as an explicit parameter: instead of `f(x)` returning a result to whoever called it, `f(x, k)` *sends* its result to `k`. That one mechanical rewrite - repeated over a whole program - turns arbitrary control flow into pure function calls, and it has paid the rent for decades of language implementation: SML/NJ compiles to CPS, Scheme interpreters define it, and every `async fn` you have shipped is a distant cousin of it.

This page walks the transform and its intuition, its relationship to ANF and SSA, Reynolds' defunctionalization (the flip side: turning continuation closures back into data), and why async/await in JavaScript, C#, Kotlin, and Rust is best read as "defunctionalized CPS". A runnable Python program demonstrates all three layers: direct style, CPS with a trampoline, and a defunctionalized state machine.

## The transform: hand every function its future

The rule: a function `f : A -> B` becomes `f : A x (B -> Answer) -> Answer`, taking a continuation `k` that consumes the result. Non-tail calls no longer "return to the caller" - they receive a continuation describing what the caller wanted next:

```text
 direct style                       CPS
 ---------------------------        --------------------------------------
 fun fact(n) =                      fun factC(n, k) =
   if n <= 1 then 1                   if n <= 1 then k(1)
   else n * fact(n - 1)               else factC(n - 1,
                                                  fn v => k(n * v))
                                                ^^ caller's future is
                                                   packaged as a closure

 stack discipline:                  stack discipline:
   fact suspends inside `*`           every call is a TAIL call;
   frames accumulate                  the chain of "what next" lives
                                      in k, not on the machine stack
```

The classic way to make this feel inevitable is the **double-negation view**. Read `A -> Answer` as "not-A" (a proof by contradiction, if you like logic; a callback, if you like code). Then CPS says: an expression of type `B` becomes a function taking `B -> Answer` and producing `Answer` - i.e. `(B -> Answer) -> Answer`, the double negation of `B`. Nothing about the *information* changes; only who holds the baton. Fix `Answer` once (say, `Value`), and control flow becomes first-class data flowing through function arguments.

Two properties follow immediately, and they are why compilers care:

1. **Every call is a tail call.** In `factC`, no call site waits for a result - the result travels forward through `k`. A compiler for CPS code needs no call-stack discipline at all; calls are jumps. (The Python demo below has to fake this with a trampoline, since Python lacks TCO.)
2. **Control flow is explicit data.** The "return address" is a closure you can inspect, optimize, discard, or store. That makes control-flow-sensitive interprocedural optimizations directly expressible - the continuation of a call that never uses its result is dead code, and dead-continuation elimination falls out of ordinary dead-function elimination after inlining.

## Why a compiler pipeline wants CPS

Appel's *Compiling with Continuations* is the canonical account: CPS first, then optimize in a world where every evaluation order choice, call, and return is a plain beta-reduction away, then closure-convert (continuations are just functions - now they need environments), then flatten into machine code. Working on CPS makes some transformations trivial: sequencing is explicit, so reordering or eliminating effects has a syntactic handle; "evaluate all arguments before the call" and "inline this continuation" are local rewrites.

The price: CPS allocates a closure per non-tail call, code becomes dense with binders, and register allocation gets harder (every continuation is a potential live range). That cost is why mainstream compilers moved to ANF for the same benefits at lower overhead - and to SSA below ANF:

| IR    | What is explicit                  | Stack discipline   | Typical producers            |
|-------|-----------------------------------|--------------------|------------------------------|
| CPS   | every continuation + call         | impossible (fine)  | SML/NJ, Scheme compilers     |
| ANF   | let-bound atomic arguments        | yes                | ML/OCaml, GHC's core stages  |
| SSA   | phi nodes merge control joins     | yes                | LLVM IR, GCC GIMPLE, V8 TurbFan |

ANF (A-normal form, Flanagan et al. 1993) keeps the CPS benefit - every intermediate value is named, argument order is fixed - without turning returns into closures. Kelsey's 1995 correspondence closes the triangle: an SSA basic block *is* a continuation, a phi node *is* a continuation parameter, dominance *is* lexical scope of those parameters. Appel compressed the same observation into the slogan "SSA is functional programming" (SIGPLAN Notices 1998). So when you read [LLVM IR](./llvm-ir.md) phi nodes or the SSA treatment in [Intermediate Representation](../intermediate-representation.md), you are reading defunctionalized-and-rehydrated CPS with 30 years of tooling.

## Defunctionalization: continuations become data

CPS uses first-class functions to represent control. **Defunctionalization** (Reynolds, 1972, *Definitional Interpreters for Higher-Order Programming Languages*) removes them: collect every closure that is actually created (here, only continuations), replace the function type with a **sum type of frames** (one constructor per creation site, carrying the captured variables), and replace every application with an **apply loop** that dispatches on the constructor tag. The inverse transform is refunctionalization.

```text
 CPS (higher-order)                 defunctionalized (first-order)
 -------------------------------    ----------------------------------
 k1 = fn v => k(n * v)              frame  = Mul(n, rest)
        applied dynamically         k      : frame list / chain
                                    applyk(k, v):
                                      case k of
                                        Mul(n, rest) -> applyk(rest, n*v)
                                        Done         -> v
 closure allocation + indirect      constructor + static dispatch;
 call through unknown code          frames are plain data: copyable,
                                    serializable, storable in a struct
```

The payoff is an **abstract machine**: take an interpreter, CPS it, defunctionalize it, and you get CEK-style machines - that derivation is the standard Danvy-school route from interpreter to virtual machine, and it explains why language runtimes keep "frames as tagged structs with a next pointer": that is a defunctionalized continuation wearing a C struct. Reynolds' paper also pinned down the tail-call discipline that makes the whole thing go: an evaluator whose every step is a tail call cannot blow the stack, and the apply loop inherits that guarantee.

## async/await is defunctionalized CPS

Look again at the defunctionalized frame column and you will recognize the production machinery:

- **Kotlin** `suspend` functions are literally compiled CPS: the compiler adds a hidden `Continuation` parameter, and each suspension point becomes a resumption with a state index stored in the continuation object (see [Kotlin coroutines](../../languages/kotlin/coroutines.md)).
- **JavaScript / C# / Python** generators lower `await`/`yield` into state-machine objects: the function's locals are fields, the "program counter between yields" is an integer, `next()`/`MoveNext()` is the apply step. Python's asyncio drives exactly this trampoline (see [the asyncio internals page](../../languages/python/gil-asyncio-deep.md)).
- **Rust** `async fn` compiles to an `enum`-shaped `Future` - one variant per suspension point carrying the live locals - and the executor's `poll` loop is the apply loop (see [Rust async runtimes](../../languages/rust/async-runtimes.md); the official async book describes the state-machine lowering directly).

```text
 async fn f() {                     defunctionalized continuation:
   let a = g().await;               enum StateF {
   let b = h(a).await;                Start,
   a + b                              WaitG { next: WaitH },   locals of
 }                                    WaitH { a: A },          each stage
                                      Done
 executor loop: poll(state)         }
   = apply(frame, input_value)      poll = applyk; wakeups = the trampoline
```

The difference from the 1970s formulation is only who runs the apply loop (a per-call-site loop vs a central executor) and that frames are heap-allocated futures rather than stack frames. The "what color is your function" tax - two syntaxes, two library ecosystems - is the price of exposing defunctionalization to users instead of hiding it in the compiler; effect handlers (see [Effect Systems](./effect-systems.md)) are the research answer that hides it again.

## Runnable: direct style, CPS + trampoline, defunctionalized

Python has no tail calls, so the CPS version bounces through a trampoline of thunks; the defunctionalized version consumes a chain of data frames in an apply loop. All three compute identical results, but only the CPS/machine forms survive inputs that would overflow the native stack:

```python
"""CPS + trampoline vs defunctionalized continuation, in Python.
Python has no tail calls, so even CPS code must bounce through a
trampoline of thunks. The defunctionalized version replaces continuation
closures with data frames consumed by an apply loop (a state machine)."""

from collections import deque
import sys
sys.set_int_max_str_digits(300000)            # allow str() of huge results

# ---------- 1. direct style (reference answers) ----------
def fact(n):
    return 1 if n <= 1 else n * fact(n - 1)

def fib(n):
    return n if n <= 1 else fib(n - 1) + fib(n - 2)

# ---------- 2. CPS: every call is a tail call -> thunk + trampoline ----------
def tramp(thunk):
    while callable(thunk):
        thunk = thunk()
    return thunk

def fact_cps(n, k):
    if n <= 1:
        return lambda: k(1)
    return lambda: fact_cps(n - 1, lambda v: lambda: k(n * v))

def fib_cps(n, k):
    if n <= 1:
        return lambda: k(n)
    return lambda: fib_cps(n - 1,
                  lambda a: lambda: fib_cps(n - 2,
                           lambda b: lambda: k(a + b)))

# ---------- 3. defunctionalized: continuations are DATA, apply loop runs ----------
# factorial continuation frames: ("mul", n, rest); terminal: None
def fact_machine(n):
    k = None
    for i in range(n, 1, -1):                 # build ("mul",i,rest) chain
        k = ("mul", i, k)
    v = 1
    while k is not None:                      # the apply loop
        tag, mul, rest = k
        v = mul * v
        k = rest
    return v

# fibonacci needs a machine with two states, not just a linear chain:
#  ("compute", n)     evaluate fib(n)            (like calling fib_cps)
#  frame ("add2", n)  got fib(n-1); next want fib(n-2), remember n
#  frame ("finish", a) got fib(n-2) = v; deliver a + v upstream
def fib_machine(n):
    todo = ("compute", n)
    stack = deque()                           # defunctionalized continuation
    while True:
        if todo[0] == "compute":
            m = todo[1]
            if m <= 1:
                todo = ("deliver", m)
            else:
                stack.append(("add2", m))     # save what remains to do
                todo = ("compute", m - 1)
        else:                                 # ("deliver", v): apply top frame
            v = todo[1]
            if not stack:
                return v
            frame = stack.pop()
            if frame[0] == "add2":
                stack.append(("finish", v))   # store fib(m-1) result
                todo = ("compute", frame[1] - 2)
            else:                             # ("finish", a)
                todo = ("deliver", frame[1] + v)

if __name__ == "__main__":
    print("direct  : fact(10)=%d fib(20)=%d" % (fact(10), fib(20)))
    print("cps     : fact(10)=%d fib(20)=%d" %
          (tramp(fact_cps(10, lambda v: v)), tramp(fib_cps(20, lambda v: v))))
    print("defunc  : fact(10)=%d fib(20)=%d" % (fact_machine(10), fib_machine(20)))
    try:
        fact(50000)
    except RecursionError:
        print("direct fact(50000)      -> RecursionError (no TCO in Python)")
    print("cps fact(50000)         -> %d digits, constant Python stack" %
          len(str(tramp(fact_cps(50000, lambda v: v)))))
    print("defunc fib(25)          -> %d (matches direct: %d)" %
          (fib_machine(25), fib(25)))
```

Run it (Python 3.12):

```text
direct  : fact(10)=3628800 fib(20)=6765
cps     : fact(10)=3628800 fib(20)=6765
defunc  : fact(10)=3628800 fib(20)=6765
direct fact(50000)      -> RecursionError (no TCO in Python)
cps fact(50000)         -> 213237 digits, constant Python stack
defunc fib(25)          -> 75025 (matches direct: 75025)
```

Three things to notice. First, all three agree on the answers - the transforms are semantics-preserving by construction. Second, `fact(50000)` crashes the direct version (Python raises `RecursionError` around depth 1000) while the CPS version computes all 213,237 digits at constant Python stack depth: the "stack" now lives in heap-allocated thunks, exactly what a TCO-enabled CPS compiler promises. Third, `fib_machine` needed *two* frame constructors plus a driver state - defunctionalization is mechanical, but the shape of the resulting data (linear chain vs general state machine) reveals the real control-flow complexity that the source syntax hides. That is precisely the enum-per-`async fn` that the Rust compiler emits.

## Interview-facing takeaways

- **"What does CPS buy a compiler?"** All calls become tail calls (no stack discipline), control flow becomes explicit data (dead-continuation elimination, explicit sequencing), and the transform sets up closure conversion. Cost: closure allocation pressure - hence ANF/SSA in mainstream pipelines.
- **"How is SSA related to functional programming?"** Via Kelsey's correspondence: basic blocks are continuations, phi nodes are parameters, dominance is scope; Appel's slogan. Use the table above to place CPS/ANF/SSA.
- **"What is defunctionalization?"** Reynolds' 1972 recipe: function-valued continuations become a sum type of frames plus an apply loop; interpreter + CPS + defunctionalization yields an abstract machine. Refunctionalization goes the other way.
- **"How is my `async fn` compiled?"** Into a defunctionalized continuation: one state per suspension point, locals hoisted into the frame, an executor apply loop. Name it in those terms in a systems interview and you are describing JavaScript, C#, Kotlin, and Rust with one sentence.

## References

- J. C. Reynolds - *Definitional Interpreters for Higher-Order Programming Languages* (1972; reprint with commentary, Higher-Order and Symbolic Computation 11, 1998): [doi.org/10.1023/A:1010027404223](https://doi.org/10.1023/A:1010027404223)
- R. Kelsey - *A Correspondence between Continuation Passing Style and Static Single Assignment Form*, ACM SIGPLAN Workshop on Intermediate Representations, 1995: [bernsteinbear.com/assets/img/kelsey-ssa-cps.pdf](https://bernsteinbear.com/assets/img/kelsey-ssa-cps.pdf)
- A. W. Appel - *SSA is Functional Programming*, ACM SIGPLAN Notices 33(8), 1998: [doi.org/10.1145/278283.278285](https://doi.org/10.1145/278283.278285)
- A. W. Appel - *Compiling with Continuations*, Cambridge University Press (book page): [cambridge.org/core/books/compiling-with-continuations/7CA9C36DCE78AD82218E745F43A4E740](https://www.cambridge.org/core/books/compiling-with-continuations/7CA9C36DCE78AD82218E745F43A4E740)
- The Rust Async Book (async fn lowers to state-machine futures): [rust-lang.github.io/async-book](https://rust-lang.github.io/async-book/)
