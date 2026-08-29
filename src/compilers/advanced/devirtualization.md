# Devirtualization: When the JIT Deletes Your Virtual Calls

A virtual call is cheap in cycles and expensive in information. The indirect
jump itself is usually well predicted on a hot site; what really hurts is that
the callee is unknown at compile time, so the compiler cannot inline it - and
without inlining, every downstream optimization that needs to see through the
call dies too: null-check elimination, argument constant propagation, escape
analysis, scalar replacement. **Devirtualization** is the family of techniques
that recovers a concrete target for a virtual call site, either by *proving*
one statically or by *betting* on one dynamically and paying for the bet with
a guard. The proof path fails when the program grows; the bet path fails when
the profile goes stale. Both failures end in the same place: the
[deoptimizer](./deoptimization-osr.md).

## What a virtual call actually costs

```text
     virtual dispatch                       devirtualized + inlined
     ----------------                       -----------------------
     load vptr from receiver                compare receiver class to Circle
     load slot[k] from vtable               jne  slow_path
     jmp  slot[k]        (indirect)         <inlined Circle::area body>
     |                                      |
     +- callee opaque: no inline            +- target proven: full opt window
```

Three costs stack up:

1. **Dispatch mechanics** - two dependent loads plus an indirect branch, plus
   an extra memory stall whenever the vtable line is cold.
2. **The lost inline** - the single biggest cost on modern hardware. A small
   accessor that would compile to two instructions becomes a full call.
3. **The optimization wall** - the optimizer cannot reason past an opaque
   call, so the virtual call site poisons the whole enclosing method.

In C++ the programmer can hand the compiler the proof:

```cpp
class Circle final : public Shape {  // final class: no subclasses exist
  public:
    double area() final;             // final override: slot cannot change
};
s->area();                           // s is Shape*: dynamic type unknown ->
                                     // vtable dispatch, not inlinable
c->area();                           // c is Circle*, and Circle::area is
                                     // final -> static dispatch permitted
```

The standard explicitly permits treating a call to a `final`-designated
function as non-virtual ([class.virtual] in the working draft). Without
`final`, the compiler must prove no subclass overrides the slot - which is
exactly what class hierarchy analysis does for languages where you cannot
annotate it away.

## Static devirtualization: the call-graph construction family

**Class Hierarchy Analysis (CHA)** answers one question per (static type,
selector) pair: which method bodies could ever run? It scans the class
hierarchy - every subclass of the declared receiver type that overrides the
selector - and if exactly one candidate survives, the call site is
monomorphic *by proof* and may be compiled as a direct, inlinable call. The
original formulation (Dean, Grove, and Chambers) precomputes per-class
subclass bitsets so each query is cheap, and reported substantial speedups
from CHA-driven inlining on their benchmark suite. The same trick powers
single-implementation
reasoning in HotSpot's C2: a virtual call whose method has no overriding
implementation anywhere in the loaded hierarchy gets devirtualized without
any profile data at all.

CHA is fast because it ignores control flow - and imprecise for the same
reason. The **reachable-type** family tightens the over-approximation:

| Analysis | Over-approximates with | Cost | Precision | Where you meet it |
|---|---|---|---|---|
| CHA | any subclass of the static type, regardless of instantiation | lowest | worst | HotSpot C2, Jikes RVM, Soot (Spark) |
| RTA | all types reachable from the set of instantiated classes | low | better | Soot (Spark), analysis literature |
| VTA | types that flow into each variable, per assignment edge | higher | best of the three | Soot (Spark), call-graph research |

The precision/cost ordering is the classic exam question: CHA asks "does the
class graph forbid a second target?" (cheap, over-approximates), RTA asks
"is the receiver's class even instantiated?" (a fixed point over a type
set), VTA (variable type analysis) additionally tracks which variables each
type flows through, pruning impossible receivers at dense call sites like
factory returns. Sundaresan et al. built VTA specifically because RTA still
left too many virtual calls unresolved in real Java programs.

All of them share one assumption: **the hierarchy they analyzed is the
hierarchy that exists**. Load a new class at run time and every fact
downstream of it evaporates. The HotSpot glossary is explicit that the
compilers benefit from observing "a more complete class hierarchy" after
warm-up - and HotSpot pays for that assumption by registering CHA
dependencies on compiled code: when a subclass loads, dependent nmethods are
deoptimized. A static proof is sound only inside a closed world, and Java's
world is closed only until the next `Class.forName`.

## Closing the world: final, sealed, and link-time devirtualization

The cheapest way to make CHA sound is to shrink the world:

- **C++ `final`** on a class or member function hands the proof to the
  compiler; `override` + `final` on a leaf implementation is the idiom that
  makes devirtualization legal, not just likely.
- **Java `final`/`sealed`** - `sealed` interfaces (standard since Java 17)
  publish a closed permit list, so single-implementation reasoning survives
  even in open frameworks.
- **Whole-program views** - static compilers get the closed world for free
  when they can see every translation unit. GCC's `-fdevirtualize` (on at
  `-O2` and above) converts virtual calls to direct calls
  intraprocedurally and via IPA constant propagation, and
  `-fdevirtualize-speculatively` goes further, using "the analysis of the
  type inheritance graph" to find "the set of likely targets" and emitting
  "a conditional deciding between direct and indirect calls" - static
  speculation, same guard shape a JIT uses. `-fdevirtualize-at-ltrans`
  streams extra type information to the link-time optimizer's local
  transformation stage for aggressive LTO devirtualization. LLVM's
  `WholeProgramDevirt` pass does the analogous job over ThinLTO summaries,
  including vtable constant propagation when a slot holds a unique target.

## The JIT playbook: profile, guard, deopt

A JIT with an open world cannot prove - so it samples. The interpreter and
the fast tier record, per call site, which receiver classes actually show up
(HotSpot's method data, V8's feedback vector). The optimizing tier then
compiles the bet:

```text
        profile: {Circle: 1000, Square: 2} at site s.area()

  fast path (speculated)                  guard-miss path
  -----------------------------------     -----------------------------------
  cmp  klass(recv), Circle                slow_path:
  jne  fast_b                               report reason "receiver profile"
  <Circle::area, inlined>                   deoptimize: discard machine code,
  fast_b:                                   rebuild interpreter frame from
  cmp  klass(recv), Square                  frame-state metadata, resume
  jne  slow_path                            recompile s.area() with the
  <Square::area, inlined>                   fresh profile, reinstall
  jmp  join
  fallback (cold): load vtable, indirect call
```

The ladder in production engines: monomorphic profile -> one guard + inline;
bimorphic -> a two-link guard chain, both targets inlined; beyond that,
engines diverge - HotSpot's C2 traditionally falls back to a true virtual
call once the profile is wider than two, while V8's compilers keep chaining
up to the inline cache's polymorphic limit and only then emit generic
dispatch. Receiver profiles are just one input to the same
[profile-guided machinery](./profile-guided-optimization.md) that lays out
blocks and sizes inlining budgets - and the guard is a literal branch: every
speculative devirtualization spends compare-and-branch cost on every
execution, forever, in exchange for deleting the dispatch.

Two failure paths feed the deoptimizer, and they are distinct:

- **Guard miss** (a new receiver shows up at run time): an eager
  deoptimization of the executing frame, then recompilation with the
  widened profile.
- **Dependency invalidation** (a class loads that breaks a CHA-style fact):
  the VM walks its dependency lists and deoptimizes affected compiled code
  even where it is currently on the stack - the lazy deopt case.

The mechanics of frame-state reconstruction and trap escalation are the
subject of [Deoptimization and On-Stack Replacement](./deoptimization-osr.md).

## The megamorphic cliff

Inline caches give dispatch its own ladder: monomorphic (one cached target),
polymorphic (2-4 targets, linear probe), megamorphic (>4, shared stub cache
with hash + probe and no inline). The cliff matters here because a
speculative compiler consumes the same profile the IC does: once a site goes
megamorphic, there is no "hottest target" worth guarding in the common case,
and the site is dispatched generically. The failure mode is site-wide, not
per-receiver - one brand-new receiver kind can flip an entire hot call site
onto the stub-cache path. [Inline Caches & Hidden
Classes](./inline-caches.md) covers the cache mechanics; [V8
Engine](../../languages/javascript/v8.md) shows the hidden-class side of why
sites degrade. The compiler's counter-move is call-site splitting: clone the
site so each clone stays monomorphic.

## Pricing the guard: a worked model

The whole trade is quantitative, so price it. The model below fixes the
constants, walks one call site through three phases as subclasses load, and
accounts for deopt charges. It is a model - invented constants, one site,
one deopt per phase boundary - but it has the right shape.

```python
"""Devirtualization economics: a cycle-count model, not a benchmark.

One hot call site, CALLS iterations per phase; receiver population shifts
monomorphic -> polymorphic -> megamorphic as unseen subclasses load. Costs
are illustrative constants for a well-behaved x86-class core; only the
ratios carry meaning.
"""
DIRECT_INLINE = 1.0   # inlined method body, no dispatch
GUARD_CMP     = 0.5   # one class-identity compare, well-predicted branch
VTABLE_CALL   = 6.0   # inline-cache hit: checked dispatch + indirect call
MEGA_CALL     = 10.0  # megamorphic stub cache: hash + probe + indirect call
DEOPT_EVENT   = 2000.0  # one-time: discard code, resume in interpreter, recompile

CALLS = 1000          # iterations of the hot loop per phase

PHASES = [  # (name, receiver counts; "other" = subclasses not yet loaded
            #  when the site was compiled)
    ("monomorphic",  {"A": 1000, "B": 0,   "C": 0,   "other": 0}),
    ("polymorphic",  {"A": 600,  "B": 400, "C": 0,   "other": 0}),
    ("megamorphic",  {"A": 400,  "B": 300, "C": 200, "other": 100}),
]

def dispatch_cost(dist):
    """Generic dispatch for one phase. Up to 4 receiver kinds fit the inline
    cache; a 5th kind ('other') flips the WHOLE site to the shared megamorphic
    stub, so every call pays MEGA_CALL, not just the newcomers."""
    return CALLS * (MEGA_CALL if dist["other"] else VTABLE_CALL)

def run_baseline():
    return [(name, dispatch_cost(dist), 0) for name, dist in PHASES]

def run_cha():
    """Compiled before P1 as a plain direct call: 'A has no subclasses'.
    Eagerly invalidated when B loads; permanent virtual fallback after."""
    rows, events = [], []
    for name, dist in PHASES:
        if name == "monomorphic":
            rows.append((name, CALLS * DIRECT_INLINE, 0))
        elif name == "polymorphic":
            events.append("P2: class B loads -> 'A has no subclasses' is now"
                          " unsound; eager invalidation, 1 deopt"
                          " (%d cycles), site reverts to virtual dispatch"
                          % DEOPT_EVENT)
            rows.append((name, DEOPT_EVENT + dispatch_cost(dist), 1))
        else:
            rows.append((name, dispatch_cost(dist), 0))   # already fallen back
    return rows, events

def run_spec():
    """Recompiles grow the guard chain: [A] -> [A,B] -> [A,B,C]. Receivers
    outside the chain miss a guard, deopt, and the new compile trims its
    chain to the 3 hottest targets, leaving the rest to the stub cache."""
    chains = {1: ["A"], 2: ["A", "B"], 3: ["A", "B", "C"]}
    rows = []
    for i, (name, dist) in enumerate(PHASES, 1):
        chain = chains[i]
        inlineable = sum(dist[c] for c in chain)
        cost = (DEOPT_EVENT if i > 1 else 0.0)              # first call deopts
        cost += inlineable * (len(chain) * GUARD_CMP + DIRECT_INLINE)
        cost += (CALLS - inlineable) * MEGA_CALL            # miss -> stub cache
        rows.append((name, cost, 1 if i > 1 else 0))
    events = [
        "P2: receiver B misses the [A] guard chain -> 1 deopt (%d cycles),"
        " recompiled bimorphic [A,B]" % DEOPT_EVENT,
        "P3: receivers C/other miss the [A,B] chain -> 1 deopt (%d cycles),"
        " recompiled trimorphic [A,B,C], 'other' left to the stub cache"
        % DEOPT_EVENT,
    ]
    return rows, events

strategies = [
    ("virtual (baseline)", run_baseline()),
    ("CHA static devirt",  run_cha()[0]),
    ("guarded speculation", run_spec()[0]),
]
events = run_cha()[1] + run_spec()[1]

print("Receiver mix per phase (A/B/C/other out of %d calls):" % CALLS)
for name, dist in PHASES:
    print("  %-12s A=%-4d B=%-4d C=%-4d other=%d"
          % (name, dist["A"], dist["B"], dist["C"], dist["other"]))
print()
print("\n".join(events))
print()
hdr = ("%-12s %-14s %9s %9s %9s %9s %9s"
       % ("phase", "mix A/B/C/o", "virtual", "cha", "guarded", "d_cha", "d_spec"))
print(hdr)
print("-" * len(hdr))
totals = []
for idx, (name, dist) in enumerate(PHASES):
    vals = [s[1][idx][1] for s in strategies]
    mix = "%d/%d/%d/%d" % (dist["A"], dist["B"], dist["C"], dist["other"])
    totals = [t + v for t, v in zip(totals or [0] * 3, vals)]
    print("%-12s %-14s %9.1f %9.1f %9.1f %9.1f %9.1f"
          % (name, mix, vals[0], vals[1], vals[2],
             vals[0] - vals[1], vals[0] - vals[2]))
print("-" * len(hdr))
print("%-12s %-14s %9.1f %9.1f %9.1f %9.1f %9.1f"
      % ("TOTAL", "3000 calls", *totals,
         totals[0] - totals[1], totals[0] - totals[2]))
print()
print("deopt events: CHA static devirt = %d, guarded speculation = %d"
      % (sum(r[2] for r in strategies[1][1]),
         sum(r[2] for r in strategies[2][1])))
print("MODEL ONLY: constants are illustrative; no hardware was measured.")
```

```text
Receiver mix per phase (A/B/C/other out of 1000 calls):
  monomorphic  A=1000 B=0    C=0    other=0
  polymorphic  A=600  B=400  C=0    other=0
  megamorphic  A=400  B=300  C=200  other=100

P2: class B loads -> 'A has no subclasses' is now unsound; eager invalidation, 1 deopt (2000 cycles), site reverts to virtual dispatch
P2: receiver B misses the [A] guard chain -> 1 deopt (2000 cycles), recompiled bimorphic [A,B]
P3: receivers C/other miss the [A,B] chain -> 1 deopt (2000 cycles), recompiled trimorphic [A,B,C], 'other' left to the stub cache

phase        mix A/B/C/o      virtual       cha   guarded     d_cha    d_spec
-----------------------------------------------------------------------------
monomorphic  1000/0/0/0        6000.0    1000.0    1500.0    5000.0    4500.0
polymorphic  600/400/0/0       6000.0    8000.0    4000.0   -2000.0    2000.0
megamorphic  400/300/200/100   10000.0   10000.0    5250.0       0.0    4750.0
-----------------------------------------------------------------------------
TOTAL        3000 calls       22000.0   19000.0   10750.0    3000.0   11250.0

deopt events: CHA static devirt = 1, guarded speculation = 2
MODEL ONLY: constants are illustrative; no hardware was measured.
```

Reading the table:

- **The proof wins its phase and loses the argument.** CHA's direct call
  needs zero guards, so it beats speculation while the world stays closed
  (5000 vs 4500 saved). One subclass load and it is permanently worse: the
  eager invalidation costs 2000 cycles and the site never regains inlining.
- **Speculation pays rent on every call and survives every shift.** The
  guard chain costs 1.5-2.5 cycles per call, and the two deopts (4000
  cycles) consume about a quarter of the strategy's gross savings (15250
  without them, 11250 with).
- **The megamorphic flip is real and site-wide.** The baseline nearly
  doubles from phase 2 to phase 3 (6000 -> 10000) because the 100 "other"
  receivers push the whole site onto the stub cache.
- **What the model hides:** deopts priced once at the phase boundary, no
  code-size or I-cache cost for guard chains, and no recompile heuristics.
  Real engines also weigh all three.

## Where devirtualization loses

- **Deopt storms.** A site whose receiver population keeps changing can
  ping-pong between compiled forms; engines cool this down with per-site
  trap-history budgets and recompile bans.
- **Guard density.** Every guard is a live branch across the inlined body,
  extending live ranges and pressuring the predictor; trimorphic chains are
  not free even when they win.
- **Framework proxies.** CGLIB-style subclass proxies and dynamic proxies
  manufacture subclasses at run time, which is precisely the event that
  invalidates single-implementation facts. Heavy DI + AOP stacks deopt more
  for this reason, not because of type churn in application code.
- **Code-size blowup.** Aggressive speculative inlining multiplies method
  bodies; I-cache misses can hand back the savings, which is why the GCC
  flags exist to turn the whole business off per-unit.

The interview summary in one sentence: devirtualization trades a *soundness
obligation* (closed world or fresh profile) for the *inline window*, and
every real system prices that trade with guards, dependency lists, and a
deoptimizer - the interesting question is never "can we delete the virtual
call?" but "who pays when the assumption dies?"

## References

1. J. Dean, D. Grove, C. Chambers. [Optimization of Object-Oriented Programs
   Using Static Class Hierarchy Analysis](https://doi.org/10.1007/3-540-49538-x_5).
   ECOOP 1995, LNCS. doi:10.1007/3-540-49538-x_5 - the CHA paper; frequently
   miscited as OOPSLA 1995 (it is ECOOP, Springer LNCS, pp. 77-101).
2. D. F. Bacon, P. F. Sweeney. [Fast Static Analysis of C++ Virtual Function
   Calls](https://doi.org/10.1145/236337.236371). OOPSLA 1996.
   doi:10.1145/236337.236371 - introduces RTA.
3. V. Sundaresan, L. Hendren, C. Razafimahefa, et al. [Practical Virtual
   Method Call Resolution for Java](https://doi.org/10.1145/354222.353189).
   OOPSLA 2000. doi:10.1145/354222.353189 - VTA.
4. M. Paleczny, C. Vick, C. Click. [The Java HotSpot Client
   Compiler](https://www.usenix.org/legacy/events/jvm01/full_papers/paleczny/paleczny.pdf).
   USENIX JVM Research and Technology Symposium, 2001 - CHA and guarded
   inlining as shipped in HotSpot.
5. [HotSpot Virtual Machine Glossary](https://openjdk.org/groups/hotspot/docs/HotSpotGlossary.html)
   - warm-up, class-hierarchy observation, deoptimization definitions.
6. [TurboFan (V8 docs)](https://v8.dev/docs/turbofan) - V8's optimizing
   compiler design and speculation pipeline.
7. [WebAssembly Speculative Optimizations (V8 blog)](https://v8.dev/blog/wasm-speculative-optimizations)
   - how a production engine tiers speculation and rolls it back.
8. [C++ working draft, [class.virtual]](https://eel.is/c++draft/class.virtual)
   - final/override semantics that license static dispatch.
9. GCC manual, [Optimize Options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)
   - `-fdevirtualize`, `-fdevirtualize-speculatively`,
   `-fdevirtualize-at-ltrans` (page 403s to curl; wording verified against
   `gcc/doc/invoke.texi` on the gcc-mirror master branch).
