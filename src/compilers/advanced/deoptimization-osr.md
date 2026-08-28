# Deoptimization and On-Stack Replacement

A speculative JIT trades a guarantee for a bet: it compiles the code as if the hot path's types, maps, and branch outcomes will hold, and installs machine-code traps for the moment they do not. Deoptimization is how the bet is settled - the compiled frame is abandoned and an interpreter frame is rebuilt from metadata, mid-execution, without losing program state. On-stack replacement (OSR) is the same trick run in the other direction: an interpreter frame that is already inside a hot loop is converted *into* a compiled frame. This page covers the mechanics both directions share - frame-state metadata, materialization of speculative values, entry/exit protocols, and what happens when deopts repeat. The tiering overview and the speculative-optimization loop live in [JIT Compilation](../jit-compilation.md) and [JIT Optimization](./jit-optimization.md); inline-cache-driven deopts are in [Inline Caches](./inline-caches.md). Here we go under the hood of the transition itself.

## The two transitions

```text
        interpreter frame               optimized frame
        +----------------+              +----------------+
 OSR    |  bytecode @bci |   deopt      |  machine code  |
  ==>   |  (inside hot   |  <==  ==>    |  pc @return    |
        |   loop)        |              |  address       |
        +----------------+              +----------------+
             slow tier    <------------>   fast tier
        OSR entry: swap THIS frame      deopt: rebuild THIS frame
        for a compiled one, same loop   from the translation array,
        iteration, stack keeps running  then continue in the interpreter
```

Both directions need the same prerequisite: the optimizing compiler must emit, for every point where control can cross tiers, a *complete description of the interpreter state* in terms of the optimized code's values. In HotSpot this description lives in the nmethod's debug information (scope + `ScopeValue`s); in V8 it is a serialized **translation array** stored in the code object's `DeoptimizationData`. Without it, deoptimization is impossible - this is why the original dynamic deoptimization paper (Holzle, Chambers, Ungar, PLDI 1992) introduced it together with the debugging use case: the frame metadata needed to show source-level variables in a debugger is exactly the metadata needed to resume in the interpreter.

## Eager vs lazy deopt

The distinction is *which* bytecode the reconstructed frame points at:

| Property | Eager deopt | Lazy deopt |
|----------|-------------|------------|
| Trigger | A guard/check fails inline | A runtime event during a call the compiled code made |
| Frame state describes | Inputs of the faulting instruction (it re-executes) | Result of the call (execution continues at the next bytecode) |
| Resume offset | The failing instruction's bci | bci after the call |
| Typical causes | Type check, bounds check, null check, overflow | Map/prototype invalidation, debugger attach |
| V8 reason enum | `DEOPTIMIZE_REASON_LIST` (e.g. `NotASmi`, `MinusZero`, `OutOfBounds`) | `LAZY_DEOPTIMIZE_REASON_LIST` (e.g. `PrototypeChange`, `MapDeprecated`) |

V8's `deoptimize-reason.h` literally ships two lists for the two cases - eager reasons name the failed speculation (`NotASmi`, `LostPrecisionOrNaN`, `InsufficientTypeFeedbackForBinaryOperation`), lazy reasons name the dependency that broke while a call was on the stack (`PrototypeChange`, `PropertyCellChange`, `Debugger`). HotSpot's uncommon trap is the eager case; the lazy case fires when a dependency registered on a class/field invalidates while *any* frame is executing the nmethod, including callees that have not returned yet.

## Frame-state materialization

The optimized code keeps values wherever it likes - machine registers, stack slots, folded into constants, or *not materialized at all* (scalar-replaced objects, values that only exist as SSA names). The translation array maps every live interpreter slot back:

```text
optimized frame at the deopt point        interpreter frames rebuilt
+---------------------------------+       +------------------------------+
| rax = a         (int32)         |       | f:  bci=2  a=Smi(5) b=<str>  |
| [sp+8] = b      (tagged slot)   |  -->  |      (add_smi re-executes)   |
| obj#1 = {sum: [sp+8],           |       |                              |
|           echo: rax}  captured  |       | g:  (caller frames follow)   |
+---------------------------------+       +------------------------------+
     CAPTURED_OBJECT / DUPLICATED_OBJECT opcodes tell the deoptimizer
     to allocate real heap objects during the walk
```

V8's translation opcodes (from `src/deoptimizer/translation-opcode.h`) include `INTERPRETED_FRAME_WITH_RETURN`, `INT32_REGISTER`, `DOUBLE_STACK_SLOT`, `HOLEY_DOUBLE_REGISTER`, and the materialization pair `CAPTURED_OBJECT`/`DUPLICATED_OBJECT` - the last two rebuild an object the optimizer had scalar-replaced, or point at a previously materialized twin when two SSA names alias the same escape analysis artifact. Materialization is the expensive part: each rebuilt object is a real allocation, which is why escape analysis with deopt support ([Kotzmann and Mossenbock, VEE 2005](https://doi.org/10.1145/1064979.1064996)) only pays off when the deopt is rare.

Two details matter for correctness:

1. **The walk is physical, once.** The deoptimizer runs at a safepoint, walks every inlined frame (deopt data covers the whole inlining tree), patches return addresses, and hands control to a stub that enters the interpreter. It cannot deopt "halfway" - either every frame is rebuilt or none is.
2. **The re-executed instruction must not double its side effects.** That is why eager deopt state snapshots the instruction's *inputs*: the add has not happened yet. Lazy deopt snapshots *outputs*: the call already happened and must not run twice.

## What a deopt costs

Anatomy of one transition, roughly in cost order:

| Step | Cost driver |
|------|-------------|
| Trap + safepoint entry | Fixed, small (hundreds of ns) |
| Frame walk + rebuild | Linear in frame count x live values; inlining depth multiplies it |
| Object materialization | Real allocations; GC pressure |
| Interpreter warm-up | ICs, inline caches and feedback re-learn from cold |
| Lost optimization | The nmethod is invalidated; its inlining decisions, LICM results, and unrolling are gone until recompilation |

The single-deopt price is bounded and fine when guards are rare. The pathology is repetition.

## Deopt storms and how runtimes fight them

A **deopt storm** is a deopt-recompile-deopt cycle: the profiler sees type A, the optimizer bakes in A, reality alternates B/A/B/A, each observation invalidates the code, and the runtime burns all its time compiling. Both flagship VMs carry explicit machinery:

- **HotSpot per-bci trap history.** `deoptimization.hpp` records uncommon-trap reasons per bytecode index in the MethodData; once a bci's trap count exceeds the history limit, escalation stops. The `DeoptAction` ladder is `none -> maybe_recompile -> reinterpret -> make_not_entrant -> make_not_compilable` - the last one bans recompilation of that method outright. Reasons can also be *tenured* (`Reason_tenured`): an nmethod that has aged out is not given fresh chances.
- **V8 budget-based re-optimization.** Tier-up from interpreter to Sparkplug/Maglev/TurboFan is gated on interrupt budgets (see `tiering-manager.cc`); a deopt drops the function back and the re-optimization budget grows, so a function that deopts on every Nth call spends proportionally more time in lower tiers. Soft deopts - `InsufficientTypeFeedback*` reasons, which fire when a function was optimized before its feedback stabilized - additionally leave the feedback in a state that makes the next compile more conservative.
- **Speculation downgrade.** When a specific speculation keeps failing, the recompile drops it: HotSpot recompiles without the failing intrinsic/check; V8 marks the failing builtin speculation mode (the `OutOfBounds` reason carries `SpeculationMode::kDisallowBoundsCheckSpeculation`), and the deopt reason `LoopSpeculationFailed` stops loop-specific speculation.

The user-facing symptom is a function that "never gets optimized" or a `--trace-deopt` (V8) / `PrintDeoptimizationDetails` (HotSpot) log full of one reason at one bci. The fix is upstream: stabilize the input distribution, or rewrite the hot path so the polymorphic case is explicit rather than speculated.

## On-stack replacement

OSR exists because tiering thresholds are call-count based but heat can live inside a single call: one function whose body is a 10^8-iteration loop would never return, never re-enter, and never see its back-edge counter translated into a compiled frame. The interpreter counts **back-edge overflows**; when one trips, the VM requests an OSR compilation of the method *at the current bytecode offset*.

```text
OSR entry (interpreter -> compiled):
  interpreter loop, bci B, back-edge overflow #k
      -> enqueue OSR compile(bci B), keep interpreting (profiling still on)
      -> next back edge at B: poll the OSR result
           present? -> build a compiled frame whose state == interpreter state
                       at B, jump to the OSR entry point (a special prologue
                       that skips the cold prologue of the nmethod)
           absent?  -> keep looping

OSR exit (compiled -> interpreted):
  the OSR loop deopts, or the loop finishes
      -> normal deopt machinery rebuilds the interpreter frame
      -> V8 additionally records OSREarlyExit ("exit from OSR'd inner loop")
         so the exit itself feeds back into future tiering decisions
```

V8's side is visible in `runtime-compiler.cc`: `Runtime_CompileOptimizedOSR` compiles at the OSR bytecode offset, and the feedback vector caches the resulting OSR code so later iterations reuse it (`PrepareForOnStackReplacement` and `OSREarlyExit` both appear in the eager-deopt reason list). HotSpot's side is the OSR nmethod: a second compilation of the same method, entered at `osr_entry`, whose successor blocks start at the loop header bci.

OSR-compiled code is systematically a little worse than a natural-entry compile of the same loop, for structural reasons worth knowing:

| OSR handicap | Why |
|--------------|-----|
| No prologue profiling | The compiler must trust the interpreter's profile at one bci; guards it would have hoisted are installed per-iteration instead |
| Entry-state constraints | Values live at the entry bci (loop-carried variables, phi inputs) must be accepted as-is, blocking some expression re-association |
| Peak-shape distortion | The OSR compile optimizes *this* loop; call sites outside it compile as deopt-prone cold paths |
| One-shot usage | Once the loop exits, the OSR nmethod is usually dead weight; tiering compiles a natural-entry version later anyway |

The inverse flow - a deopt inside an OSR-compiled loop - lands the frame back in the interpreter *inside the same loop*, where back-edge counting resumes and, if the loop is still hot, OSR compilation can fire again. Runtimes damp this with the same storm controls as above.

## A worked micro-model

The simulation below models the state machine at small scale: translation arrays for one eager and one lazy deopt point, materialization of a scalar-replaced object, and a re-optimization budget that doubles after each deopt (a crude stand-in for V8's budget reset and HotSpot's trap history). Type instability is injected on calls 9 and 13.

```python
"""Mini model of JIT deoptimization: translation arrays, frame materialization,
eager vs lazy deopt points, and re-optimization budgets after repeated deopts."""

# --- bytecode of the hot function f(a, b):  return {sum: a + b, echo: g(a)} ---
BYTECODE = ["load a", "load b", "add_smi", "call g", "return"]

class FrameState:
    """A deopt point: bytecode offset + where each live value lives."""
    def __init__(self, bci, values):
        self.bci = bci
        self.values = values  # list of (kind, location, source) tuples

# eager point = state BEFORE the faulting instruction (interpreter re-executes it)
# lazy point  = state AFTER the call (interpreter continues at the next bci)
EAGER_AT_ADD = FrameState(2, [("int32_reg", "rax", "a"), ("int32_stack", "sp+8", "b")])
LAZY_AT_CALL = FrameState(4, [("int32_reg", "rax", "ret_g"),
                              ("captured", "obj#1",
                               {"sum": ("int32_stack", "sp+8"),
                                "echo": ("int32_reg", "ret_g")})])

def materialize(state, regs, stack, heap):
    """Walk the translation array, rebuilding interpreter-frame values."""
    frame = []
    for kind, loc, src in state.values:
        if kind == "int32_reg":
            frame.append(("tagged", regs[src]))
        elif kind == "int32_stack":
            frame.append(("tagged", stack[loc]))
        else:  # captured object: scalar-replaced value must get a heap home
            obj = {}
            for field_name, (fsrc, floc) in src.items():
                obj[field_name] = regs[floc] if fsrc == "int32_reg" else stack[floc]
            heap.append(obj)
            frame.append(("heap_object", "obj#%d" % len(heap)))
    return frame

def run_sim(calls=16):
    budget, tier, heap, log = 3, "interp", [], []
    last_deopt = 0
    for call in range(1, calls + 1):
        b = "seven" if call in (9, 13) else 7        # inject type instability
        if tier == "optimized":
            if isinstance(b, str):
                frame = materialize(EAGER_AT_ADD, {"a": 5}, {"sp+8": b}, heap)
                log.append((call, "EAGER deopt (NotASmi)",
                            "resume bci=%d, b=%r" % (EAGER_AT_ADD.bci, b)))
                tier, budget, last_deopt = "interp", min(budget * 2, 12), call
            elif call == 11:
                frame = materialize(LAZY_AT_CALL, {"ret_g": 42}, {"sp+8": b}, heap)
                log.append((call, "LAZY deopt (PrototypeChange)",
                            "continue bci=%d" % LAZY_AT_CALL.bci))
                tier, budget, last_deopt = "interp", min(budget * 2, 12), call
            else:
                log.append((call, "optimized ok", ""))
        else:
            if call - last_deopt >= budget and isinstance(b, int):
                tier = "optimized"
                log.append((call, "re-optimize (TurboFan)", "budget=%d" % budget))
            else:
                log.append((call, "interp", "waiting out budget"))
    return log, heap

log, heap = run_sim()
print("call  state                        detail")
for call, state, detail in log:
    print("%4d  %-28s %s" % (call, state, detail))

print("\ninterpreter frame rebuilt by the eager deopt at call 9:")
regs, stack, heap = {"a": 5}, {"sp+8": "seven"}, []
for kind, val in materialize(EAGER_AT_ADD, regs, stack, heap):
    print("  %-13s %r" % (kind, val))

heap2 = []
vals = materialize(LAZY_AT_CALL, {"ret_g": 42}, {"sp+8": 7}, heap2)
print("lazy deopt after call g (call 11): continue at bci %d, accumulator=%d,"
      " frame also carries" % (LAZY_AT_CALL.bci, vals[0][1]))
print("  %-13s %r  (scalar-replaced object got a real heap home: %r)"
      % (vals[1][0], vals[1][1], heap2[0]))
```

```text
call  state                        detail
   1  interp                       waiting out budget
   2  interp                       waiting out budget
   3  re-optimize (TurboFan)       budget=3
   4  optimized ok                 
   5  optimized ok                 
   6  optimized ok                 
   7  optimized ok                 
   8  optimized ok                 
   9  EAGER deopt (NotASmi)        resume bci=2, b='seven'
  10  interp                       waiting out budget
  11  interp                       waiting out budget
  12  interp                       waiting out budget
  13  interp                       waiting out budget
  14  interp                       waiting out budget
  15  re-optimize (TurboFan)       budget=6
  16  optimized ok                 

interpreter frame rebuilt by the eager deopt at call 9:
  tagged        5
  tagged        'seven'
lazy deopt after call g (call 11): continue at bci 4, accumulator=42, frame also carries
  heap_object   'obj#1'  (scalar-replaced object got a real heap home: {'sum': 7, 'echo': 42})
```

Read the trace with the mechanics in mind: the eager deopt at call 9 resumes at bci 2, so `add_smi` re-executes in the interpreter with the now-string operand; the lazy deopt at call 11 continues at bci 4, because `g` already ran; and the budget doubling pushes re-optimization from gap 3 (calls 3) to gap 6 (call 15) - the same shape as a real deopt storm cooling down, just at toy scale.

## Diagnosing in practice

| Runtime | Tool | What you see |
|---------|------|--------------|
| V8 | `node --trace-deopt` | Per-deopt line: reason, bci, inlined frames, materialized objects; `soft` marker for feedback-driven deopts |
| V8 | `--trace-opt-verbose` | Why tier-up was granted or denied (budgets, deopt history) |
| HotSpot | `-XX:+PrintDeoptimizationDetails` | Uncommon trap site, reason/action, decoded frame walk |
| HotSpot | JFR compiler statistics | Deopt counts per method; nmethod state transitions |

The dominant production pattern: a deopt reason naming a type/map check, at a stable bci, repeating across recompiles - i.e., a polymorphic hot path the profiler cannot pin down. The structural fix is to hoist the variance (dispatch once, before the hot region) so the speculated region becomes stable again.

## References

- U. Holzle, C. Chambers, D. Ungar. [Debugging optimized code with dynamic deoptimization](https://doi.org/10.1145/143095.143114). PLDI 1992. doi:10.1145/143095.143114 - the original dynamic deoptimization design (Self), including frame-state reconstruction.
- V8 project. [DeoptimizeReason / LazyDeoptimizeReason enums](https://github.com/v8/v8/blob/main/src/deoptimizer/deoptimize-reason.h) - the split between eager and lazy reason lists, OSR-related reasons, and speculation-mode downgrades.
- V8 project. [src/deoptimizer/deoptimizer.cc](https://github.com/v8/v8/blob/main/src/deoptimizer/deoptimizer.cc) and [translation-opcode.h](https://github.com/v8/v8/blob/main/src/deoptimizer/translation-opcode.h) - the frame-walk driver and the translation-array opcode set, including `CAPTURED_OBJECT` materialization.
- OpenJDK project. [HotSpot deoptimization.cpp](https://github.com/openjdk/jdk/blob/master/src/hotspot/share/runtime/deoptimization.cpp) and [deoptimization.hpp](https://github.com/openjdk/jdk/blob/master/src/hotspot/share/runtime/deoptimization.hpp) - uncommon-trap handling, the `DeoptAction` escalation ladder, per-bci trap history.
- OpenJDK project. [HotSpot Glossary](https://openjdk.org/groups/hotspot/docs/HotSpotGlossary.html) - canonical definitions of deoptimization, uncommon trap, and on-stack replacement.
- V8 team. [Maglev: a fast optimizing compiler](https://v8.dev/blog/maglev) (2023) - the current four-tier pipeline (Ignition, Sparkplug, Maglev, TurboFan) and how each tier handles deopt metadata.
