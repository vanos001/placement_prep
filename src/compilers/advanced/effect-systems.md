# Effect Systems & Algebraic Effects

Every function answers two questions: what value does it produce, and what else happened along the way - I/O, mutation, exceptions, suspension? Classical type systems answer only the first question; an **effect system** folds the second into the type. **Algebraic effects and handlers** (Plotkin & Pretnar, ESOP 2009) go one step further and turn effects into first-class requests: a program can *perform* an operation (`get`, `read`, `await`) and the nearest enclosing **handler** decides what that request means - compute it, substitute a canned answer, retry, or abort. Because the handler also captures the rest of the computation as a **one-shot delimited continuation**, it can resume, discard, or reroute that remainder however it likes.

This page builds the model end to end: effect annotations, the operation/handler algebra, the continuation machinery underneath, and a runnable effects interpreter in pure Python. It deepens the survey treatment in [Type Systems](./type-systems.md) (its "Effect Systems and Algebraic Effects" section) and the denotational framing in [Formal Semantics](./formal-semantics.md); [Session Types](./session-types.md) and [Linear Types](./linear-types.md) are sibling schemes for tracking *communication* and *resource usage* rather than computational behavior.

## What an effect annotation actually tracks

The core idea is a second type-level dimension. In Koka, a function type is a value type plus an **effect row**:

```text
fun square( i : int ) : int               -- pure: empty effect row
fun println( s : string ) : io ()         -- returns (), performs io
fun spin_forever() : div int              -- may diverge (div), no io

fun map( f : int -> e int, xs : list<int> ) : e list<int>
--            ^^ effect row variable: map inherits whatever
--               effects f performs (io? div? nothing?)
```

Rows are what make this scale. A row is an open set of effect names plus a row variable; effect-polymorphic functions quantify over it, so `map` and `foreach` do not hardcode "may do io" - they inherit whatever their arguments do. This is the same row-polymorphism trick that powers record polymorphism, reused for behavior.

Languages differ mainly in how much of that dimension they expose:

| Language   | How effects are tracked            | Granularity                    | Notes                             |
|------------|------------------------------------|--------------------------------|-----------------------------------|
| Haskell    | IO monad in the return type        | one coarse effect (all I/O)    | pure ST/State exist beside it     |
| Koka       | per-function effect rows           | fine: io, div, ndet, st, ...   | rows inferred; async via handlers |
| OCaml 5    | nothing (handlers are untyped)     | divergence implicit only       | fine-grained typing still open    |
| Unison     | "abilities" in the type            | fine-grained, inferred         | compiled to its own runtime       |
| Rust       | no effects; async/RWLock by design | coarse (unsafe = catch-all)    | "effect generics" debated         |

The Haskell column is the useful contrast: `IO` is exactly an effect system with a single effect name, which is why mixing pure and effectful code is disciplined but *which* effects run is invisible to the type. Koka is what you get by splitting that name into a row. OCaml 5 made the opposite bet: ship runtime machinery first, type it later - deliberate, and still the main gap in its story.

## Operations and handlers: the algebraic core

Plotkin and Pretnar's insight was to define effects **algebraically**: an effect signature declares operation symbols, a program is a (free) term built from those operations, and a handler is an interpretation that maps every operation to code. Concretely, an operation carries parameters *and* a spot for its answer: `op : P -> R -> A` - given parameters `P` and a resumption result `R` (what the continuation will be handed), the handler must produce the overall answer `A`. A handler has two kinds of clauses:

```text
handle { ...computation... } with
| return x  -> ...           -- what to do if it finishes normally
| op(p, k)  -> ...           -- what to do when `op` is performed;
                                k is the captured continuation, a
                                ONE-SHOT delimited function: k(v)
                                resumes the rest of the program
```

If you know free monads, this is the same object with better syntax: a computation *is* the free monad over the operation signature (an AST of suspended requests), a handler *is* the fold/interpreter over that AST, and `handle` is `runFreeT`. The difference is ergonomic and practical - you write direct-style code with no `>>=` plumbing, handlers compose without transformer towers (see the monad comparison in [Type Systems](./type-systems.md)) - and mechanical, because real implementations skip the explicit AST entirely and use native continuations.

Dispatch is dynamic: a performed operation travels to the *nearest enclosing* handler for that operation name, exactly like an exception travels to the nearest `catch` - except the operation can come back:

```text
 user code (direct style)              handler scope
 --------------------------------      -------------------------------------
 | let n = get() in               |      | handle                             |
 | put(n + 1);                    |      | | get()     -> k(42)   resume 42   |
 | n * 2                          |      | | put(v)    -> k(())   resume ()   |
 --------------------------------      | | return r   -> r       finalize   |
        |  perform("get")              -------------------------------------
        v                                        ^        |
   [ nearest handler for get ]                   |        |
        |  suspend: capture rest as k -----------+        |
        +  handler computes 42, resumes k(42) ------------+
```

**Deep vs shallow handlers.** A *deep* handler re-installs itself around every resumption: `k(v)` continues *inside the same handler*, which is what you want for state (every later `get` is seen again). A *shallow* handler captures the continuation but resumes it *outside* the handler: one operation is interpreted, then the wrapper is gone. Shallow is the finer primitive - deep handlers can be defined from shallow ones - and languages split on the default: Koka supports both with deep as the default, while OCaml 5's primitive `match ... with effect` clauses are shallow and the stdlib's `Effect.Deep` module (e.g. `Deep.match_with`) is the library-defined deep convenience. Exceptions are just a handler whose operation clause *ignores* `k`; state is just a deep handler that threads a store through every resumption.

## One-shot delimited continuations: the machinery

Everything above compiles down to one mechanism: **delimited continuations** - capture only the stack slice between the performer and the delimiter (Danvy & Filinski's `shift`/`reset`, Felleisen's prompt; see the runtime survey in [Runtime Systems](../../cs-theory/runtime-systems.md)). `reset` installs the delimiter (the handler boundary); `shift` captures the slice and hands it to you as a function. The handler model is a disciplined interface over exactly these two moves.

**One-shot vs multi-shot.** A captured continuation can in principle be resumed many times (that gives backtracking and nondeterminism for free: resume `k(1)` and `k(2)` and collect both answers). OCaml 5 and Koka restrict continuations to one-shot. Two reasons: cost (multi-shot requires copying or immutability guarantees for the stack slice, and breaks linear resources - see [Linear Types](./linear-types.md) for why resuming a continuation that owns a file handle twice is unsound) and semantics (observably re-running arbitrary user code is a big semantic commitment). Python generators are one-shot for the same practical reasons, which is what the demo below leans on.

**How OCaml 5 does it.** OCaml 5 gives every computation a **fiber**: a stack segment on the heap. Performing an effect captures the fiber - the implementation uses *stack slicing*: the live stack between handler and performer is detached and stored on the heap, and the handler's stack becomes current. Resuming installs the slice back onto a stack. Costs to internalize for interviews (from the PLDI 2021 paper): handlers that never see an operation are nearly free (just a delimited extent); capturing costs proportionally to the continuation's size; the whole OCaml 5 concurrency stack - `Lwt`'s direct-style successor Eio, structured concurrency, even parallel `Domain.join` - is user-level library code over these primitives. Koka's backend and the Eff language research prototype take the same route. The flagship production example is OCaml 5 itself (5.0 shipped December 2022): real-world servers run on handlers, not on a bespoke runtime scheduler.

## Every classic effect is a handler encoding

| Effect         | Operations            | Handler clause does                    | Resumption used? |
|----------------|-----------------------|----------------------------------------|------------------|
| Exceptions     | `raise(e)`            | return the error (ignore `k`)          | never            |
| State          | `get()`, `put(s)`     | thread a store through each resume     | always           |
| Async/sleep    | `suspend()` / `await` | record `k` in a scheduler queue        | later, elsewhere |
| Generators     | `yield(v)`            | return `v` + remember `k` for `next()` | on next pull     |
| Nondeterminism | `flip()`              | resume multiple times, collect answers | one-shot forbids |

The async row dissolves the ["what color is your function"](https://journal.stuffwithstuff.com/2015/02/01/what-color-is-your-function/) problem: in a language with effects, user code is *always* direct style; `await` is just `perform suspend()`, and the color distinction (sync fn vs async fn signatures) disappears from library APIs and collapses into the *handler* - swap a concurrent handler for a sequential one and the same code runs scheduled or not. That is literally Eio's architecture on OCaml 5 (see [OCaml ecosystem](../../languages/ocaml/ecosystem.md)), Koka's async library, and the design Rust keeps circling in its "keyword generics / effect generics" explorations (see [Rust async runtimes](../../languages/rust/async-runtimes.md) for the state-machine alternative that Rust ships today, and [Kotlin coroutines](../../languages/kotlin/coroutines.md) for the CPS-transform flavor of the same idea).

## A working interpreter in ~75 lines of Python

Python generators give us exactly the needed primitive: `yield` performs an operation (the request travels up), and `gen.send(v)` resumes the one-shot continuation with `v`. First a **deep handler** for a state effect, then a **non-resuming handler** - exceptions:

```python
"""Algebraic effects emulated with Python generators:
yield = perform (send an operation request up), send() = resumption (k(v))."""

def perform(op, *args):
    """Raise an operation request to the nearest enclosing handler."""
    return (yield (op, args))

# ---------- a DEEP handler for a State effect (get / put) ----------
def run_state(thunk, state0=0):
    state = state0
    gen = thunk()
    try:
        req = next(gen)                       # start the computation
    except StopIteration as done:
        return done.value, state
    while True:
        op, args = req                        # deep handler: this same
        if op == "get":                       # loop keeps handling every
            resp = state                      # resumption, so the handler
        elif op == "put":                     # is implicitly re-installed
            state = args[0]; resp = None
        else:
            raise RuntimeError("unhandled operation: " + op)
        try:
            req = gen.send(resp)              # resume k(resp) -- one-shot
        except StopIteration as done:
            return done.value, state

# ---------- direct-style user code: no callbacks, no monads ----------
def increment():
    n = yield from perform("get")
    yield from perform("put", n + 1)
    return n + 1

def counter():
    a = yield from increment()                # nested calls pass through:
    b = yield from increment()                # the handler sees them all
    return a + b

# ---------- a NON-resuming handler = exceptions ----------
def run_result(thunk):
    gen = thunk()
    try:
        req = next(gen)
    except StopIteration as done:
        return ("ok", done.value)
    op, args = req
    if op == "throw":
        return ("error", args[0])             # continuation discarded:
    raise RuntimeError("unhandled operation: " + op)   # never resumed

def risky(i):
    if i % 2 == 0:
        _ = yield from perform("throw", "even input rejected: %d" % i)
        return None                           # unreachable (no resumption)
    return i * 10

def pipeline():
    a = yield from risky(2)                   # throws here
    b = yield from risky(3)
    return a + b

def pipeline_ok():
    a = yield from risky(1)
    b = yield from risky(3)
    return a + b

if __name__ == "__main__":
    v, s = run_state(counter)
    print("run_state(counter)      -> value=%d final_state=%d" % (v, s))
    print("run_result(pipeline)    ->", run_result(pipeline))
    print("run_result(pipeline_ok) ->", run_result(pipeline_ok))
```

Run it (Python 3.12):

```text
run_state(counter)      -> value=3 final_state=2
run_result(pipeline)    -> ('error', 'even input rejected: 2')
run_result(pipeline_ok) -> ('ok', 40)
```

Read the output against the model. `counter` never touches a store, callback, or monad - it is direct style; all state lives in the handler, which threads it through every resumption (deep). `pipeline` performs `throw` inside `risky(2)`; `run_result` returns the error *without ever calling `send`*, so the continuations of `risky(2)`, `pipeline`, and the code after the throw are all silently discarded - precisely exception semantics, and precisely the row of the table above. Note what is *missing*: you cannot resume the `throw` twice to emulate `try`-with-retry, because a Python generator is one-shot - the same restriction OCaml 5 and Koka impose.

## Interview-facing takeaways

- **"Monads vs algebraic effects?"** Monads bake interpretation into sequencing (`>>=`); effects separate the program from its interpretation, so handlers compose without transformers and one computation can run under different handlers (test-log vs prod-log). See the monad section of [Type Systems](./type-systems.md).
- **"How does OCaml 5 implement handlers?"** Heap-allocated fiber stacks + stack slicing at effect operations; one-shot continuations; shallow clauses as primitives, deep as a library (PLDI 2021 paper below).
- **"Why can't resume be called twice?"** Linear resource safety and copy costs; multi-shot needs deep copies of stack segments or linearity discipline - hook this to [Linear Types](./linear-types.md).
- **"What does this do to async APIs?"** Removes color from user code: scheduling policy moves from function signatures into the installed handler; compare with the explicit state machines in [Rust async runtimes](../../languages/rust/async-runtimes.md) and the CPS transform in [Kotlin coroutines](../../languages/kotlin/coroutines.md).
- **"Where is the typing story weak?"** OCaml 5 ships untyped handlers; fine-grained effect typing for ML with handlers remains an active research problem (row-polymorphic handler typing in Koka is the reference design).

## References

- G. Plotkin, M. Pretnar - *Handlers of Algebraic Effects*, ESOP 2009 (LNCS 5502): [doi.org/10.1007/978-3-642-00590-9_7](https://doi.org/10.1007/978-3-642-00590-9_7)
- G. Plotkin, M. Pretnar - *Handling Algebraic Effects* (extended journal version), Logical Methods in Computer Science 9(4), 2013: [lmcs.episciences.org/973](https://lmcs.episciences.org/973)
- KC Sivaramakrishnan et al. - *Retrofitting Effect Handlers onto OCaml*, PLDI 2021 (fibers, stack slicing, one-shot design): [doi.org/10.1145/3453483.3454039](https://doi.org/10.1145/3453483.3454039)
- OCaml 5 manual - *Effect handlers* chapter (shallow clauses, deep-handler library): [v2.ocaml.org/manual/effects.html](https://v2.ocaml.org/manual/effects.html)
- Koka language book (effect rows, deep/shallow handlers, async library): [koka-lang.github.io/koka/doc/book.html](https://koka-lang.github.io/koka/doc/book.html)
