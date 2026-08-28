# JIT Compilation in HotSpot

## Why a JIT, and Why Tiers

The JVM ships with an interpreter that walks `code[]` arrays from `.class` files one instruction at a time, decoding the opcode, dispatching through a switch, and updating the `pc`. Interpreted bytecode is portable but slow — a tight `iadd` in bytecode may take 5–15 native cycles through the dispatch loop, versus a single `add` for the JIT'd form. The trick the HotSpot VM has used since ~1999 is *adaptive optimization*: profile code while it runs, find the 1–5% of methods that matter, and compile those to native code with aggressive optimization while everything else stays interpreted.

The two compilers — **C1** (`-client`, historically) and **C2** (`-server`) — sit at different points on the compile-time vs. run-time tradeoff:

```
                compile time per method
   high   ──────────────────────────────────
                       /                C2  (server)
                     /       Sea-of-Nodes IR
                   /         escape analysis
                 /          aggressive inline
               /
             /                              C1  (client)
   low  ───────                              LinearScan RA
            interpreter only                 fast codegen
                runtime throughput
```

Opt-in since JDK 7 and the default for the HotSpot server VM since JDK 8, **tiered compilation** chains them: interpreter → C1-with-profiling → C2. The interpreter is warm-up, C1 captures profile data quickly at low cost, then C2 recompiles the genuinely hot methods with the profile in hand. C2's biggest win comes from being able to inline across virtual calls when the profile says "this call site is monomorphic — it always dispatches to class `Foo`".

## Compilation Tiers and Levels

HotSpot distinguishes 5 execution levels, encoded in the `CompileLevel` argument seen in `-XX:+PrintCompilation` output:

```
Level 0   Interpreter              (template interpreter, hand-written asm)
Level 1   C1, no profiling         (fastest compiled, used for trivial methods)
Level 2   C1, limited profiling
Level 3   C1, full profiling       (the workhorse during warm-up)
Level 4   C2                        (peak throughput)
```

A typical hot method's lifecycle looks like:

```
  t0 ──── t1 ──── t2 ──── t3 ──── t4 ───►  time
   L0      L0+L3   L3      L4      L4
   interp  interp   C1 w/    C2     stable
           + C1     profile
```

- At `t1` the **method invocation counter** (`-XX:CompileThreshold=10000`) is hit and C1 at L3 is enqueued.
- At `t2` the L3-compiled version is running and C1 is collecting profiling records (types seen at call sites, branch outcomes, null/non-null).
- At `t3` the **back-edge counter** for hot loops crosses a separate threshold; this triggers C2 at L4. C2 consumes the L3 profile.
- If a deoptimization happens, control drops to L0 and is rebuilt from L3 again.

You can observe this live:

```
$ java -XX:+UnlockDiagnosticVMOptions \
       -XX:+PrintCompilation -XX:+PrintInlining \
       -cp myapp.jar com.example.Main
  127  449       3       com.example.Vector::dot (29 bytes)
  128  450 %     3       com.example.Vector::dot @ 5 (29 bytes)
  ...
  245  449       4       com.example.Vector::dot (29 bytes)
```

The `%` denotes an **on-stack replacement (OSR)** compile — the loop body was replaced while the method was on the call stack. The `@ 5` is the bytecode index of the back-branch that triggered OSR.

## Counters and the CompileBroker

Each `Method*` carries two counters in its `MethodCounters` struct:

- **`InvocationCounter`** for method-entry: incremented by 2 each call, decayed periodically.
- **`BackedgeCounter`** for loop back-edges: incremented on every backward branch.

The two counters are summed into a *compilation threshold* check. Both decay over time, which means a server that's been running for hours needs sustained heat to re-enqueue, not just a burst. The flag `-XX:CompileThreshold` sets the entry threshold (default 10000 in non-tiered server mode); in tiered mode the thresholds are managed by `TieredStopAtLevel` and the tier-specific thresholds `-XX:Tier3InvocationThreshold`, `-XX:Tier4InvocationThreshold`, etc.

The CompileBroker runs a fixed-size pool of compiler threads (`-XX:CICompilerCount`, default ~`max(2, ncpu-1)`). When the queue fills up it will *unprofile* (drop counters) rather than burst-compile the whole world.

## C1 — the Client Compiler

C1 is a one-pass, linear compiler designed for fast startup. Its pipeline is:

```
  Bytecode ──► HIR (SSA, high-level IR)
                │
                ▼
              Optimizations: value numbering, null-check elision
                │
                ▼
              LIR (lowered, register-aware)
                │
                ▼
              LinearScan register allocation
                │
                ▼
              Native code emission
```

C1 was designed for things like Swing demos — code where you want responsiveness more than peak throughput. It does *not* do escape analysis, loop unrolling, or lock elision. C1's inliner is conservative (size limit ~35 bytes default).

## C2 — the Server Compiler

C2 is the heavyweight. Its IR is Cliff Click's *sea of nodes* representation, where data and control dependencies are nodes in a graph and edges are the dependencies:

```
   ┌────────────┐         ┌────────────┐
   │  Start     │ ──────► │  Region 0   │
   └────────────┘         └────────────┘
                                  │
                                  ▼
                       ┌──────────────────┐
                       │  AddI(i, j)      │  ← data node
                       └──────────────────┘
                                  │
                                  ▼
                          ┌─────────────────┐
                          │  If (cmp lt)    │  ← control node
                          └─────────────────┘
```

C2's optimization catalog is large; the ones interviewers love to ask about:

1. **Escape analysis** (and scalar replacement): if C2 proves that an object allocated inside a method does not escape — it's not stored in a heap field, not returned, not passed to a call that escapes — the object is decomposed into its scalar fields and the `new` vanishes. This turns `HashMap`-style allocation churn in tight inner loops into registers.

2. **Lock elision / coarsening**: a `synchronized` block whose monitor object is provably thread-local (escapes analysis again) is removed entirely. A sequence of `synchronized` blocks on the same monitor is coarsened into one.

3. **Loop optimizations**: unrolling, parallelization of reductions (`Arrays.setAll`-style loops → vector instructions when CPUID says AVX2/AVX-512 is available), range-check elimination (the array-bounds check is hoisted out of the loop because `0 ≤ i < len` is provable from the loop bounds).

4. **Inlining**: the inlining tree is the single biggest source of speed in JIT'd Java. C2 inlines:
   - Static and special (`invokespecial`) calls directly.
   - Virtual calls when the call site is *monomorphic* (profile shows exactly one receiver type) or *bimorphic* (two — the second one becomes a fast-path / slow-path).
   - With CHA (class hierarchy analysis), even some non-final methods on classes with no subclasses can be devirtualized and inlined.

   The inlining budget is `-XX:MaxInlineSize=35` bytes for trivial methods and `-XX:FreqInlineSize=325` for hot ones; multi-level inlining (a hot method that inlines calls that inlines calls) is what lets the JIT build a single optimized block out of many source-level methods.

You can ask the JIT to dump the inlining tree:

```
$ java -XX:+UnlockDiagnosticVMOptions \
       -XX:+PrintInlining \
       -XX:CompileCommand=print,com.example.Vector.dot \
       -cp myapp.jar com.example.Main
```

`-XX:CompileCommand=print,<class>.<method>` is the most useful of the `CompileCommand` directives — it dumps the generated assembly (with the help of `hsdis`) so you can see exactly what C2 produced:

```
$ java -XX:+UnlockDiagnosticVMOptions \
       -XX:+PrintAssembly -XX:+PrintInlining \
       -cp myapp.jar com.example.Main
```

For the curious, `-XX:CompileCommand=dontinline,<method>` forces a call site out of the inline budget — useful when you're tuning and want to see whether the JIT is responsible for a regression.

## On-Stack Replacement (OSR)

Most compiles happen lazily: when control returns from a hot method, the next call enters the compiled version. But a single long-running method (a `while(true)` in a server `main`, for example) would never be compiled if it never returns. OSR solves this by compiling a *method-version-at-loop-entry*: a compiled body whose entry point is the back-edge of a loop, with a "skeleton" that materializes the current operand-stack and locals from the interpreter frame.

```
   Interpreter frame for method M, currently at bci=12 (loop back-edge):

   ┌────────────────────────────────┐
   │  locals: [i, sum, arr]          │
   │  operand stack: []              │
   │  ── bci 12: goto 5 ──           │ ← back-edge counter overflows
   └────────────────────────────────┘
                  │  OSR entry
                  ▼
   ┌────────────────────────────────┐
   │  Compiled frame for M at bci=12 │
   │  (prologue reconstructs locals)│
   │  then continues compiled loop  │
   └────────────────────────────────┘
```

OSR-compiled code is often slightly slower than non-OSR-compiled code because it can't assume things about argument types or the inlining that a normal compile would have done at method entry. After OSR fires, C2 may also produce a non-OSR version that gets swapped in on the next method call.

## Escape Analysis in Practice

```java
public long sum() {
    long acc = 0;
    for (int i = 0; i < 1000; i++) {
        Point p = new Point(i, i + 1);  // p does not escape
        acc += p.x + p.y;
    }
    return acc;
}
```

If C2 can prove `p` does not escape (the call to `Point`'s `<init>` doesn't stash `this` anywhere), then:

- The `new` allocation is removed.
- `p.x` and `p.y` become two scalars (registers).
- The whole loop body compiles as if you'd written `acc += (long)(2 * i + 1)`.

Verify with `-XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining -XX:+PrintIdealGraph` (or `-XX:CompileCommand=Option,Point::*,PrintIdealGraph`). The definitive flag is `-XX:-DoEscapeAnalysis` to disable it for benchmarking.

## Deoptimization — Uncommon Traps

C2's optimizations are *speculative*: they're valid only under assumptions like "this call site is monomorphic" or "no subclass of `Shape` has been loaded". When an assumption fails — say a subclass is loaded that violates CHA, or a call site suddenly sees a second receiver type — the JIT must throw away the compiled code and resume in the interpreter. This is **deoptimization**, and C2 implements it via *uncommon traps*: hot-path code that always exits to the deopt handler.

```
   Compiled code:
     call site -> receiver's vtable[rslot]
        ^----^  deoptimization record maps
                bci 17  -> locals/stack/monitors

   If CHA invalidation fires:
     1. Patch the receiver check to jump to "uncommon trap"
     2. Trap handler reads the deopt record
     3. Reconstructs interpreter frame
     4. Resumes at bci 17
     5. Recompiles at L3/L4 with new profile
```

The JVM keeps a *deoptimization record* for every safe-point in compiled code that maps machine state (registers, spill slots) back to bytecode state (locals, operand stack, monitor holdings) at a corresponding bytecode index. Reconstructing the interpreter frame at the right bci — and unwinding the inlining — is what makes the JVM spec-compliant recompilation contract possible: the observable behavior must be identical to running in the interpreter from the start.

You can see deopts in the compilation log:

```
 452  471       4       com.example.Shape::area (18 bytes)
 453  471       4   !   com.example.Shape::area (18 bytes)   ← made not entrant
 454  475       3       com.example.Shape::area (18 bytes)   ← recompiled at L3
```

The `!` in the right-hand column means "made not entrant" — the previous compile is discarded. A `%` would mean "made zombie" (no live frames reference it, can be freed).

## The Graal Compiler

Graal is a C2 replacement written in Java itself, exposed via the **JVMCI** (JVM Compiler Interface, JEP 243) — a stable API that allows a JIT written in Java to be plugged into HotSpot. With `-XX:+UnlockExperimentalVMOptions -XX:+UseJVMCICompiler -XX:+EnableJVMCI -Djvmci.compiler=graal` you can swap C2 out for Graal in a stock OpenJDK build.

Graal's IR is a graph too, but it's more uniform than C2's and benefits from the standard Java toolchain — the compiler is debuggable with the same IDE you debug app code with. Graal is also the basis for the **SubstrateVM** ahead-of-time compiler in GraalVM Native Image, which uses closed-world analysis to produce a single statically linked executable.

A natural question is "does Graal replace C2 in OpenJDK?" The short answer is *not in OpenJDK itself* — Graal lives in the `graal` repository and ships with GraalVM, but the upstream OpenJDK builds still use C2. Project Metropolis ("JEP 376 — JEP 376: macOS/AArch64 Port" is unrelated — there's a long-running push to make Graal the in-tree JIT, see the "Leyden" and "Babylon" explorations) is the umbrella for collapsing the AOT/JIT split.

## Comparison to V8 and PyPy

| Aspect | HotSpot C2 | V8 (TurboFan) | PyPy (RPython) |
|---|---|---|---|
| Base representation | Sea of Nodes (C2) | TurboFan sea-of-nodes + bytecode | RPython flow graphs |
| Profiler | Method/back-edge counters, type feedback embedded in code | Inline caches, feedback vectors | Counters + green/red bridges in the tracer |
| First-tier | Template interpreter + C1 | Ignition bytecode interpreter | Plain interpreter |
| Second-tier | C2 | TurboFan (now Maglev+TurboFan) | RPython JIT tracer |
| OSR | Yes, at back-edges | Yes, baseline tier switch | Yes, "green bridges" |
| Deopt | Uncommon traps, per-frame deopt records | Eager deopt + lazy patching | "Blackholes" via guard failure |
| Speculation granularity | Per-call-site | Per-call-site (IC slots) | Per-loop (traces) |

V8 famously took the *sea-of-nodes* IR idea from C2 (and Cliff Click's papers). PyPy traces loops rather than whole methods — a fundamentally different unit of compilation — which works well in Python where everything is dynamic dispatch but loop bodies are short.

The two big ideas interviewers like to probe:
1. *Why tier?* Compile cost is amortized across runtime. A 10ms compile on a method called 100M times is a great trade; the same 10ms on a method called twice is a loss.
2. *Why speculate?* If you only compile when you have profile data, the optimizations you can make are much more aggressive than a static compiler's — because you know what the code *actually* does, not what it *might* do.

## References

- The Java HotSpot Performance Engine Architecture — original Sun whitepaper: <https://www.oracle.com/java/technologies/javase/javase-tech-programming.html>
- The HotSpot Group wiki (architecture, compilers, tiered): <https://openjdk.org/groups/hotspot/>
- "Optimizing Java" by Benjamin J. Evans, ch. 4–6 (covers the C1/C2 pipeline in depth)
- Aleksey Shipilev — JVM Anatomy Quark series, e.g. #14 "OSR" and #6 "Lifespan of a JIT Compiled Method": <https://shipilev.net/jvm/anatomy-quarks>
- Cliff Click, "A Simple Technique for Building and Optimizing Bytecodes" — the early HotSpot IR work: <https://www.usenix.org/legacy/publications/library/proceedings/jvm01/full_papers/click/click.pdf>
- JEP 243, Java-Level JVM Compiler Interface (JVMCI): <https://openjdk.org/jeps/243>
- JEP 291, deprecate client VM and enable tiered by default context: <https://openjdk.org/jeps/291>
- HotSpot-style `-XX:+PrintCompilation` output reference: <https://wiki.openjdk.org/display/HotSpot/PrintCompilation>
- GraalVM documentation, "JIT compilation with Graal": <https://www.graalvm.org/latest/graalvm/jit-compiler/>
- The V8 Maglev paper and TurboFan docs: <https://v8.dev/blog/maglev>
- PyPy tracing JIT explainer: <https://pypy.org/stm1.html> and the canonical tracing-JIT paper <https://www.cs.purdue.edu/homes/zheng16/papers/tracing-jit.pdf>
