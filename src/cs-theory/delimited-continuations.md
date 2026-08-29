# Delimited Continuations: Prompts, shift/reset, One-Shot Control

A continuation is the rest of a computation. **First-class continuations** (`call/cc`, Scheme 1975) reify that rest as a callable value - the ultimate escape hatch, and an awkward one: it captures the *whole* rest of the program, invoking it abandons the caller's frame forever, and it does not compose (library code using `call/cc` and framework code using `call/cc` fight over the same undivided control state). **Delimited continuations** (Felleisen's prompts, POPL 1988; Danvy & Filinski's `shift`/`reset`, LFP 1990) fix this by placing a **delimiter** (prompt) on the stack and capturing only the slice between the capture point and the nearest delimiter. The slice becomes an ordinary function value; everything outside the delimiter stays untouched. That one change makes continuations composable, typeable, and cheap enough to build production concurrency on.

This page covers the three capture disciplines, exact `shift`/`reset` semantics, the typing story, the one-shot vs multi-shot split, and how real runtimes store the captured slice. Two siblings sit adjacent: [CPS transformation](../compilers/advanced/cps-transformation.md) (continuations as explicit functions - the compilation route) and [effect systems and algebraic effects](../compilers/advanced/effect-systems.md) (handlers as the disciplined interface over the same resumption machinery). `call/cc`'s logical alter ego (Peirce's law) lives in [lambda calculus](./lambda-calculus.md) and [programming language theory](./programming-language-theory.md); the runtime survey is [runtime systems](./runtime-systems.md).

## Three capture disciplines

| Primitive          | Delimiter? | Captured context                   | Invoking it                                     |
|--------------------|------------|------------------------------------|-------------------------------------------------|
| `call/cc`          | no         | the entire rest of the program     | jumps back to the capture point, then returns    |
| prompt + `abort`   | yes        | slice up to the nearest prompt     | aborts: context discarded, prompt returns value  |
| `shift` / `reset`  | yes        | slice up to the delimiter, as `k`  | composable: `k` is a function, runs anywhere     |
| effect handler     | yes        | slice as resumption `k` (one-shot) | handler decides: resume now, later, or never     |

The last row is the modern endpoint: Felleisen's prompt/abort and Danvy-Filinski's shift/reset were generalized by Plotkin & Pretnar into **algebraic effects and handlers** (ESOP 2009), where the delimiter is a handler and the captured slice is the resumption. Exceptions are an abort that ignores `k`; generators and async are resumptions that park `k` in a scheduler - the interface view is the handler encodings table in [effect systems](../compilers/advanced/effect-systems.md).

## shift/reset semantics

`reset e` runs `e` under a fresh delimiter. `shift f`, performed inside `e`, suspends the current computation, *cuts out* the slice between itself and the delimiter, packages it as the function `k`, and calls `f(k)`. Two properties distinguish this from `call/cc`: **the slice is removed, not just jumped** (after `shift`, the captured region no longer exists on the current stack; `f` runs in the context of `reset`'s caller, whereas `call/cc` re-enters the capture point), and **`k` is composable** (calling `k(v)` splices the slice into *whatever context you are in now*; `k` is a plain function you can pass around, partially apply, or never call at all).

The whole model is two rewriting rules (angle brackets denote `reset`, `E` is a context up to the delimiter):

```text
< E[shift f] >   =   f (fn a => < E[a] >)     capture: slice E handed over as k,
                                              re-installed under a fresh delimiter
< v >            =   v                        a value flows through the delimiter
```

Worked example with both possible behaviors visible:

```text
   expression:   reset ( 10 + shift (fn k => k(1) * 100) )

   1. shift captures the slice  k = fn a => 10 + a     ("10 + _" is removed)
   2. f = fn k => k(1) * 100 runs OUTSIDE the delimiter
   3. k(1) splices back:  10 + 1  =  11                (composable resume)
   4. f returns 11 * 100 = 1100
   5. value of the whole reset: 1100

   variant:  shift (fn k => 42)  ->  k never called
             slice "10 + _" is never re-entered: value is 42   (abort)
```

`shift (fn k => k x)` behaves as if `shift` were not there; `shift (fn k => c)` aborts to the delimiter; anything else in between is a user-defined control operator. Sitaram & Felleisen (1990) mapped the hierarchy of such delimiter disciplines and their expressive separation.

## Typing shift/reset

In the monomorphic system of Danvy & Filinski, one fixed **answer type** `r` flows through the whole program:

```text
shift : ((a -> r) -> r) -> a     the handler must deliver something of type r,
                                 and the shift expression itself has type a
reset : r -> r                   the delimiter anchors the answer type
```

The full power comes from **answer-type modification**: a handler's result may *change* the delimiter's answer type, so one `reset` can anchor code whose captured continuations are used at unrelated types (this is what makes typeable `printf`/`yield` encodings possible). Asai & Kameyama (APLAS 2007) give the polymorphic type system - built on the monomorphic scheme, with explicit answer types - and prove soundness, principal types, and inference. Kameyama & Hasegawa (ICFP 2003) proved a sound and complete axiomatization of the equational theory, making `shift`/`reset` one of the few control operators with a fully verified algebra. Untyped `call/cc`, by contrast, has Peirce's law as its type - it changes the logic of the language, not just its control flow (see [lambda calculus](./lambda-calculus.md)).

## One-shot vs multi-shot

Can `k` be called twice? Two answers divide the field:

- **Multi-shot** (Scheme's `call/cc`, Chez by default, Haskell's `Cont` monad): a continuation is a value like any function; resuming it twice re-executes the slice. This buys backtracking and nondeterminism for free, at the cost of copying or reifying the stack slice and of soundness headaches with linear resources (resuming a continuation that owns a socket twice is unsound without linearity discipline).
- **One-shot** (OCaml 5, Koka, Chez's `call/1cc`, Python generators): each captured continuation may be resumed at most once; a second resume raises an error. The OCaml manual states the rationale verbatim: *"One-shot continuations are sufficient for almost all concurrent programming needs. They are also much cheaper to implement compared to multi-shot continuations since they do not require stack frames to be copied."* The manual also shows the failure mode - `continue k 21 + continue k 21` inside a handler fails with `Exception: Stdlib.Effect.Continuation_already_resumed`.

Chez Scheme ships both, which makes the trade concrete: `call/cc` gives multi-shot continuations backed by stack copying, `call/1cc` gives one-shot continuations that avoid the copy - the implementation is described in "Representing Control in the Presence of One-Shot Continuations" (Bruggeman, Waddell & Dybvig, PLDI 1996). Kiselyov (TCS 2012) goes further: delimited control *with* multi-shot resumptions can be added as a library to a host language without native multi-shot capture, by re-running captured slices instead of copying them - the same trick the second demo below uses in miniature.

## Where the slice lives: implementation survey

| Runtime / system        | Mechanism                                              | Continuation flavor                   |
|-------------------------|--------------------------------------------------------|---------------------------------------|
| SML/NJ, Scheme-to-CPS   | whole-program CPS transformation                       | multi-shot (continuations are closures) |
| OCaml 5                 | heap-allocated fiber stacks; stack slicing at `perform` | one-shot                              |
| Chez Scheme             | copyable native stack segments                         | `call/cc` multi-shot, `call/1cc` one-shot |
| Python generators       | `yield` suspends the slice, `send` resumes it          | one-shot                              |
| Haskell effect libraries| continuations are ordinary closures (CPS as a library) | multi-shot                            |

Two notes worth internalizing. The CPS route needs no runtime change at all: continuations are just functions, which is how the SML/NJ compiler and every user-level effect library in Haskell work (see [CPS transformation](../compilers/advanced/cps-transformation.md)). The fiber route (OCaml 5, Koka) allocates each call stack segment on the heap, so capturing a delimited slice means detaching a linked list of segments - the mechanism of "Retrofitting Effect Handlers onto OCaml" (PLDI 2021), over which the OCaml 5 concurrency stack (Eio; see [OCaml ecosystem](../languages/ocaml/ecosystem.md)) is library code. Unison's **abilities** and Koka's effect rows (see the [Koka book](https://koka-lang.github.io/koka/doc/book.html)) sit one abstraction higher still: effect-typed interfaces over the same one-shot resumptions.

## Demo 1: one-shot shift/reset, in a Python generator driver

Python generators natively implement one-shot delimited control: `yield` suspends the slice, `gen.send(v)` resumes it exactly once. The driver below turns that protocol into real `shift`/`reset` - `shift(f)` captures the slice as a callable `k`, hands it to `f`, and `f`'s return value becomes the value of the whole delimited expression. Three programs exercise composable use, abortive use, and the one-shot violation:

```python
"""One-shot delimited continuations via Python generators: reset(body)
installs a delimiter; shift(f) captures the slice as a one-shot callable k
and f's return value becomes the value of the whole delimited expression."""

LOG = []

class OneShotError(Exception):
    pass

def shift(f):
    return (yield ("shift", f))

def reset(body):
    gen = body()
    LOG.clear()
    try:
        req = gen.send(None)                  # start the body
    except StopIteration as done:
        return done.value
    if req[0] != "shift":
        raise RuntimeError("unknown request %r" % (req[0],))
    f, used = req[1], [False]

    def k(v):                                 # the captured slice, one-shot
        if used[0]:
            raise OneShotError("continuation resumed twice")
        used[0] = True
        LOG.append("resume k(%d)" % v)
        try:
            gen.send(v)
        except StopIteration as done:
            LOG.append("slice -> %d" % done.value)
            return done.value
        return None                           # slice suspended again (unmodeled)

    LOG.append("capture")
    result = f(k)
    LOG.append("f -> %d" % result)
    return result

def p1():
    a = yield from shift(lambda k: k(1) * 100)
    return 10 + a                             # captured slice: "10 + _"

def p2():
    a = yield from shift(lambda k: 42)        # f ignores k: abort
    return 10 + a

def p3():
    a = yield from shift(lambda k: k(5) + k(6))   # 2nd resume violates one-shot
    return 10 + a

if __name__ == "__main__":
    print("p1 (composable):", reset(p1), " log:", " | ".join(LOG))
    print("p2 (abortive):  ", reset(p2), " log:", " | ".join(LOG))
    try:
        print("p3 (one-shot):  ", reset(p3), " log:", " | ".join(LOG))
    except OneShotError as e:
        print("p3 (one-shot):   OneShotError:", e, " log:", " | ".join(LOG))
```

```text
p1 (composable): 1100  log: capture | resume k(1) | slice -> 11 | f -> 1100
p2 (abortive):   42  log: capture | f -> 42
p3 (one-shot):   OneShotError: continuation resumed twice  log: capture | resume k(5) | slice -> 15
```

Read the traces against the semantics section. In `p1` the handler runs *outside* the delimiter, calls `k(1)`, the slice `10 + _` computes `11`, and that value flows back into `f` - composable capture. In `p2` the handler ignores `k`, so `10 + a` never runs - abortive capture, exactly Felleisen's `abort`. In `p3` the handler succeeds with `k(5)` but then attempts `k(6)`: the driver raises before resuming - the one-shot discipline the OCaml manual documents, enforced here in user code.

## Demo 2: multi-shot behavior by replay

The same protocol can *simulate* multi-shot resumption without stack copying: each fork re-runs the whole pure computation from the start, replaying recorded decisions and taking one fresh decision per branch. This is the library-side strategy (Kiselyov 2012) in miniature, and the cost model - re-execution, exponential in decision points - is the honest price of multi-shot on a one-shot substrate:

```python
"""Multi-shot resumption by deterministic replay: a generator resumption is
one-shot, so each fork re-runs the pure computation from the start, replaying
recorded decisions and taking one fresh decision per branch. Same observable
behavior as a multi-shot continuation; the price is re-execution."""

RUNS = 0

class Fail(Exception):
    pass

class Branch:
    __slots__ = ("thunk", "replay")

    def __init__(self, thunk, replay):
        self.thunk, self.replay = thunk, replay

def shift(f):
    return (yield ("shift", f))

def drive(branch):
    global RUNS
    RUNS += 1
    try:
        gen, answers = branch.thunk(), []

        def step(v):
            try:
                return ("yield", gen.send(v))
            except StopIteration as done:
                return ("return", done.value)

        kind, value = step(None)              # start; first request arrives
        while kind == "yield":
            if value[0] != "shift":
                raise RuntimeError("unknown request %r" % (value[0],))
            i = len(answers)
            if i < len(branch.replay):        # recorded decision: replay it
                answers.append(branch.replay[i])
                kind, value = step(branch.replay[i])
            else:                             # fresh decision: multi-shot k
                f = value[1]
                return f(lambda w: drive(Branch(branch.thunk, answers + [w])))
        return value
    except Fail:
        return None                           # dead branch

def amb(*options):
    def choose(k):
        return [k(o) for o in options]        # the SAME k, resumed per option
    return (yield ("shift", choose))

def require(cond):
    if not cond:
        raise Fail

def puzzle():
    x = yield from amb(1, 2, 3)
    y = yield from amb(1, 2, 3)
    require(x * y == 6)
    return (x, y)

if __name__ == "__main__":
    res = drive(Branch(puzzle, []))
    print("pairs with x*y == 6 ->", [r for row in res for r in row if r is not None])
    print("raw branch tree     ->", res)
    print("computation runs    ->", RUNS, "(1 root + 3 + 9 forks)")
```

```text
pairs with x*y == 6 -> [(2, 3), (3, 2)]
raw branch tree     -> [[None, None, None], [None, None, (2, 3)], [None, (3, 2), None]]
computation runs    -> 13 (1 root + 3 + 9 forks)
```

`amb` performs one shift per choice point, and its handler `choose` calls the same `k` once per option - impossible natively (that is the `Continuation_already_resumed` case), but the replay driver re-runs the pure `puzzle` 13 times to deliver the semantics. Note what replay does *not* need: no stack copying, no special runtime - only a pure, re-runnable computation. That purity requirement is exactly the linearity concern that pushes production runtimes toward one-shot.

## Interview-facing takeaways

- **"`call/cc` vs `shift/reset`?"** `call/cc` captures the entire rest of the program and invoking it jumps back to the capture point; `shift` captures only up to the delimiter, removes the slice, and hands it over as an ordinary function whose invocation splices the slice into the *current* context. Delimiting is what makes continuations composable and typeable.
- **"Abortive vs composable?"** Abortive (`prompt`/`abort`, exceptions): the context is discarded; the delimiter's value is the handler's result. Composable (`shift`): the context is reified as `k`; whether the slice ever re-runs is the handler's decision.
- **"Why do production runtimes ship one-shot?"** Cheaper (no stack-frame copying - the OCaml manual's stated rationale), sound with linear resources (sockets, file descriptors), and sufficient for concurrency: a scheduler parks and resumes each fiber exactly once. Multi-shot buys backtracking, which a pure replay layer can emulate when the application allows it.
- **"How does `async/await` relate?"** It is a compiled-down, single-purpose delimited control: each suspension point captures the rest of the function as a state-machine frame (defunctionalized CPS) and the executor resumes it - compare [Kotlin coroutines](../languages/kotlin/coroutines.md) and [Rust async runtimes](../languages/rust/async-runtimes.md). Effects and handlers generalize the same machinery to arbitrary operations (see [effect systems](../compilers/advanced/effect-systems.md)).
- **"What did delimited control fix about `call/cc`?"** Composability (slices are values, not jumps), typing (answer-type discipline instead of Peirce's law), and reasoning: Kameyama-Hasegawa's sound-and-complete equational theory applies to `shift`/`reset`, not to undelimited capture.

## References

- M. Felleisen - *The Theory and Practice of First-Class Prompts*, POPL 1988 (prompts and `abort`; the delimiter idea): [doi.org/10.1145/73560.73576](https://doi.org/10.1145/73560.73576)
- O. Danvy, A. Filinski - *Abstracting Control*, LFP 1990 (`shift`/`reset`): [doi.org/10.1145/91556.91622](https://doi.org/10.1145/91556.91622)
- D. Sitaram, M. Felleisen - *Control Delimiters and Their Hierarchies*, LISP and Symbolic Computation 3(1), 1990: [doi.org/10.1007/BF01806126](https://doi.org/10.1007/BF01806126)
- Y. Kameyama, M. Hasegawa - *A Sound and Complete Axiomatization of Delimited Continuations*, ICFP 2003: [doi.org/10.1145/944705.944722](https://doi.org/10.1145/944705.944722)
- K. Asai, Y. Kameyama - *Polymorphic Delimited Continuations*, APLAS 2007 (answer types, principal types, inference): [doi.org/10.1007/978-3-540-76637-7_16](https://doi.org/10.1007/978-3-540-76637-7_16)
- C. Bruggeman, O. Waddell, R. K. Dybvig - *Representing Control in the Presence of One-Shot Continuations*, PLDI 1996: [doi.org/10.1145/231379.231395](https://doi.org/10.1145/231379.231395)
- O. Kiselyov - *Delimited Control in OCaml, Abstractly and Concretely*, Theoretical Computer Science 435, 2012 (multi-shot delimited control as a library): [doi.org/10.1016/j.tcs.2012.02.025](https://doi.org/10.1016/j.tcs.2012.02.025)
- G. Plotkin, M. Pretnar - *Handlers of Algebraic Effects*, ESOP 2009 (handlers as the delimited-control discipline): [doi.org/10.1007/978-3-642-00590-9_7](https://doi.org/10.1007/978-3-642-00590-9_7)
- KC Sivaramakrishnan et al. - *Retrofitting Effect Handlers onto OCaml*, PLDI 2021 (fiber stacks, stack slicing, one-shot design): [doi.org/10.1145/3453483.3454039](https://doi.org/10.1145/3453483.3454039)
- OCaml 5 manual - *Effect handlers* chapter (one-shot rationale, `Continuation_already_resumed`, `Effect.Deep`/`Effect.Shallow`): [ocaml.org/manual/latest/effects.html](https://ocaml.org/manual/latest/effects.html)
- Chez Scheme User's Guide, Section 6.3 *Continuations* (`call/cc` multi-shot vs `call/1cc` one-shot): [cisco.github.io/ChezScheme/csug/control.html](https://cisco.github.io/ChezScheme/csug/control.html)
- Koka language book (effect rows, handlers over one-shot continuations): [koka-lang.github.io/koka/doc/book.html](https://koka-lang.github.io/koka/doc/book.html)
- Unison docs - *Abilities: A Mental Model* (abilities as handler-typed effects): [unison-lang.org/docs/fundamentals/abilities](https://www.unison-lang.org/docs/fundamentals/abilities/)
