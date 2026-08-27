# Profile-Guided Optimization

A static compiler has to guess. Is this branch taken? Is this callee worth inlining? Does this loop trip often enough to vectorize? Decades of heuristics encode the answers, and they are right often enough to ship. Profile-guided optimization (PGO) replaces the guessing with measurement: run the program (or sample it in production), record where time actually goes, and rebuild the binary so the optimizer acts on observed frequencies instead of priors. The [optimization overview](./compiler-optimizations.md) carries a short survey of the PGO workflow; this page goes deeper on where profiles come from, exactly which optimizations consume them, how JVMs do the same thing live, and what breaks in production.

## Two roads to a profile

**Instrumentation** builds a throwaway binary with counters in every basic block, trains it on a representative workload, and feeds the merged counters back into a rebuild. **Sampling** attaches to a normal - unmodified - binary and harvests hardware-counter samples (on Intel, Last Branch Record traces of taken branches), then reconstructs approximate flow counts offline.

| Dimension | Instrumented build | Sampled profile (AutoFDO-style) |
| --- | --- | --- |
| Collection | Counters compiled into every edge/block | PMU samples of taken branches, attributed offline |
| Training cost | Heavy: counter updates pollute caches, distort layout | Near zero: production traffic is the workload |
| Fidelity | Exact edge counts | Normalized hotness, reconstructed counts |
| Build coupling | Strict: profile checksums must match the rebuild | Loose: symbolization maps samples onto the binary |
| Freshness risk | Stale profile after source edits | Cold code is never sampled; skews toward hot paths |
| Toolchain flags | GCC `-fprofile-generate` / `-fprofile-use`; Clang `-fprofile-instr-generate` / `-fprofile-instr-use` | Clang `-fprofile-sample-use`; Google AutoFDO pipeline |

GCC's flow is `-fprofile-generate` (compile + link with instrumentation), train, then `-fprofile-use`; the same page documents `-fprofile-values`, which `-fprofile-use` enables to feed value histograms, and `-fprofile-update` for thread-safe counter updates. Clang supports both roads: `-fprofile-instr-generate`/`-fprofile-instr-use` for instrumented IR PGO and `-fprofile-sample-use` for AutoFDO-created profiles.

The lineage of the sampling road is the AutoFDO system at Google. Chen, Li, and Moseley described it in "AutoFDO: Automatic Feedback-Directed Optimization for Warehouse-Scale Applications" (CGO 2016): sample taken branches with LBRs on *production* servers, symbolize, reconstruct block and edge counts, and feed LLVM a profile that reflects real fleet traffic - including the day's actual query mix, not a lab benchmark. That coupling to production data is why sampling won at hyperscale: the profile stays fresh by construction, and no instrumented build farm is needed.

## What the profile actually feeds

Instrumentation gives four data products: block/edge execution counts, function entry counts, branch probabilities derived from the counts, and value profiles (hot *values* at chosen sites). Different consumers eat different products.

### 1. Basic-block layout: make the hot path fall through

A fallthrough is free; a taken branch costs fetch redirection and potentially a mispredict. Pettis and Hansen (PLDI 1990) formulated layout as a chain-merging problem: start with every basic block as its own chain, then repeatedly merge along the hottest edge that connects a chain tail to another chain's head (reversing or concatenating when the edge runs the other way). The result maximizes realized fallthrough weight. Their second technique, function splitting, pulls cold regions out of hot functions so the hot region occupies fewer instruction-cache lines - they measured substantial I-cache miss reductions on HP-PA RISC workloads. LLVM's `MachineBlockPlacement` and `HotColdSplitting` passes implement both ideas; the [codegen deep dive](../ipa-attributor-codegen-deep.md) walks those passes and their flags pass-by-pass, so here we keep the concept.

```text
BEFORE (source order)                    AFTER (profile order)
addr   block      why it hurts           addr   block      why it is fast
----   --------   ----------------       ----   --------   ----------------
0x00   entry                             0x00   entry
0x20   b1 (hot)                          0x20   b1         fallthrough 1000x
0x40   err (10x)  <== splits hot path    0x40   b2         fallthrough  990x
0x60   b2         <== taken branch in    0x60   exit       fallthrough  990x
0x80   exit                                  ----   err
                  hot path = 2 taken        cold handler exiled to the
                  branches + 4+ I-cache     end; hot chain is one linear
                  lines for the hot loop    fallthrough run
```

The simulator below replays the Pettis-Hansen greedy merge on a tiny instrumented CFG - a hot straight-line path plus a cold error handler that the source happens to place in the middle:

```python
"""Mini Pettis-Hansen layout: greedy chain merging over an instrumented CFG."""
from collections import namedtuple

Edge = namedtuple("Edge", "src dst weight")

# Edge counts as an instrumented build would record them: the hot loop body
# executes ~1000x per call, each error check fires ~10x (rare, but nonzero).
edges = [
    Edge("entry", "b1",  1000),
    Edge("b1",    "b2",   990),
    Edge("b2",    "exit", 990),
    Edge("entry", "err",   10),
    Edge("b1",    "err",   10),
    Edge("b2",    "err",   10),
]
textual = ["entry", "b1", "err", "b2", "exit"]   # order the source happens to give

def greedy_layout(all_blocks, edges):
    """Pettis-Hansen style: merge chains along hottest edges first."""
    chain = {b: [b] for b in all_blocks}
    for e in sorted(edges, key=lambda x: -x.weight):
        a, b = chain[e.src], chain[e.dst]
        if a is b:
            continue                              # already one chain
        if a[-1] == e.src and b[0] == e.dst:      # tail -> head: append
            a.extend(b)
            for x in b:
                chain[x] = a
        elif a[0] == e.src and b[-1] == e.dst:    # head <- tail: prepend
            b_reversed = b[::-1]
            b_reversed.extend(a)
            for x in b_reversed:
                chain[x] = b_reversed
        else:
            continue                              # edge into mid-chain: deferred
    # deterministic output: keep chains, leftover singleton last
    seen, out = set(), []
    for b in textual:
        c = chain[b]
        if id(c) not in seen:
            seen.add(id(c))
            out.append(c)
    return [b for c in out for b in c]

def coverage(order, edges):
    pos = {b: i for i, b in enumerate(order)}
    hit = sum(e.weight for e in edges if pos[e.dst] == pos[e.src] + 1)
    total = sum(e.weight for e in edges)
    return hit, total

print("instrumented CFG (edge weights):")
for e in edges:
    print(f"  {e.src:>5} -> {e.dst:<4} {e.weight}")
print(f"textual layout : {' '.join(textual)}")
h, t = coverage(textual, edges)
print(f"  fallthrough coverage: {h}/{t} = {h/t:.1%}")
ph = greedy_layout(textual, edges)
print(f"greedy layout  : {' '.join(ph)}")
h, t = coverage(ph, edges)
print(f"  fallthrough coverage: {h}/{t} = {h/t:.1%}")
```

```text
instrumented CFG (edge weights):
  entry -> b1   1000
     b1 -> b2   990
     b2 -> exit 990
  entry -> err  10
     b1 -> err  10
     b2 -> err  10
textual layout : entry b1 err b2 exit
  fallthrough coverage: 2000/3010 = 66.4%
greedy layout  : err entry b1 b2 exit
  fallthrough coverage: 2980/3010 = 99.0%
```

Note the cold `err` block landed *before* `entry`, not after: the hot edge `entry -> err` connects the head of the hot chain to the tail of the cold singleton, so the paper's head-tail rule prepends it. Coverage is identical either way (2980/3010); production tools break such ties by entry-point and exception-ordering conventions.

### 2. Inlining decisions

Static inlining heuristics use code size; profiles add *frequency*. A callee with a high entry count relative to its caller gets an inflated inline budget (and once inlined, its internal branches get real probabilities, compounding the layout win). The reverse matters just as much: a call site that fires once per program execution is a prime candidate for `cold` treatment - outlined, moved to `.text.unlikely`, and never worth inlining into. LLVM records per-function entry counts in the IR and Clang attaches `hot`/`cold` semantics from them.

### 3. Indirect-call promotion (ICP)

An indirect call defeats inlining, branch prediction, and sometimes the return-stack buffer. Value profiling records which concrete targets an indirect site actually reaches (LLVM's value-profile kind `IPVK_IndirectCallTarget`); the optimizer then emits a guarded direct sequence:

```text
          before                            after (top target promoted)
          --------                          ---------------------------
  call [rax]                        cmp   rax, &foo_hot      ; profile says 92%
                                    je    .direct_foo        ; -> direct call,
                                    call  __icp_slowpath     ;    inlinable
                                    ...
                              .direct_foo:
                                    call  foo_hot
```

Current LLVM trees extend the same mechanism to C++ virtual calls with a vtable-target value profile kind (`IPVK_VTableTarget`), promoting speculative devirtualization to profile-driven decision rather than a static guess.

### 4. Value profiling: specialize the values, not just the paths

Edge counts say *where*; value profiles say *what*. The other first-class kind in LLVM's instrumentation is `IPVK_MemOPSize` ("memory intrinsic functions size"): if 99% of `memcpy` calls at a site copy 32 bytes, the compiler can emit an inline 32-byte move with a size check against a real call for the rare case. GCC's `-fprofile-values` (auto-enabled under `-fprofile-use`) similarly records value histograms - historically including hot operands for division, so a hot denominator can be tested and the divide strength-reduced. This is the same logic that V8-style engines call type feedback, applied to constants instead of types.

### 5. Register pressure: the tax layouts dodge

Hot/cold splitting and good layout do more than help the I-cache: code hoisted out of the hot path stops extending live ranges across it, and the hot region allocates registers against only its own uses. The profile also weights spill *cost* - a spill in a block running 1000x is priced 1000x - so the allocator evicts cold values first. The mechanics (splitting, rematerialization, cost/degree spilling) are covered in [Register Allocation](./register-allocation.md) and the [codegen deep dive](../ipa-attributor-codegen-deep.md); the PGO-specific point is that without frequencies, every spill cost is a blind guess.

## The same idea, live: FDO in HotSpot

A JIT never stops doing PGO. HotSpot runs tiers: the interpreter and C1 (the fast tier-1..3 compilers) accumulate per-method profiles - invocation and backedge counters, plus a method data structure recording branch outcomes, receiver types at virtual calls, and call-site frequencies. When C2 compiles a hot method, it consumes that record: receiver-type profiles drive monomorphic/bimorphic devirtualization and guarded inlining, branch back-edges drive layout. Tiered compilation is therefore best understood as *continuous* feedback-directed optimization, trading a few percent of steady-state peak for profiles no offline build could produce. The mechanics of each tier are in [JIT Optimization](./jit-optimization.md); the AOT-vs-JIT framing (including where offline PGO closes the gap) is in [JIT Compilation](../jit-compilation.md).

## LLVM IRPGO, briefly

Clang's instrumented PGO is IR-level: counters are inserted over the optimized IR (not the AST), each function gets an entry count, and results flow back as branch-weight metadata consumed by block-frequency analysis - the same `!prof`/BFI machinery the code-layout passes read (documented in [BranchWeightMetadata](https://llvm.org/docs/BranchWeightMetadata.html)). The artifacts are: run the instrumented binary to emit `.profraw` files, merge them with `llvm-profdata merge` into a `.profdata` index, and pass it via `-fprofile-instr-use` at the optimized rebuild. Each function's record carries a hash of its CFG; on the `-fprofile-use` compile, a hash mismatch means the profile cannot be trusted for that function and the compiler warns and falls back to heuristics for it.

## BOLT: layout with a whole-binary view

The compiler lays out code one function at a time; the linker, at best, groups sections. BOLT (Binary Optimization and Layout Tool; Panchenko et al., CGO 2019) goes post-link: disassemble the final binary, reconstruct the CFG, replay a sampled profile (typically `perf`/LBR), then re-layout *functions themselves* - clustering hot functions, splitting cold halves, and reordering blocks with an extended traveling-salesperson cost model that prices both fallthrough and branch direction. Reported gains on already-`-O2`/`-O3` datacenter binaries are low single digits - small per binary, but free performance across an entire fleet, which is why Meta and Google run it in production. BOLT is the proof that Pettis-Hansen layout is *not* solved at compile time: the profile the compiler trained on is not the profile production produces. BOLT now lives in the LLVM tree (see its [README](https://raw.githubusercontent.com/llvm/llvm-project/main/bolt/README.md)); the [codegen deep dive](../ipa-attributor-codegen-deep.md) shows its command-line workflow.

## Production guidance

- **Profile freshness is a build artifact.** Treat `.profdata` like a dependency: version it per release, regenerate on any CFG-touching change, and read the `-Wprofile-instr-out-of-date`-style warnings instead of ignoring them. A silently ignored profile silently returns you to -O2 heuristics.
- **Training-workload drift is the classic failure.** Optimizing the build farm's smoke test shifts code you never run and pessimizes the code you always run. Sample from production (AutoFDO-style) or rotate several training workloads, and canary the rebuild before fleet-wide rollout.
- **Sampling profiles bias hot.** Blocks too cold to ever be sampled get zero counts - usually fine, but it under-weights startup and error paths, exactly the code whose *latency* you sometimes care about.
- **Expect the win where hot/cold contrast is extreme.** Payout concentrates in dispatch loops, parsers, and interpreters with cold error arms. Flat profiles yield flat results.

| Symptom | Root cause | Fix |
| --- | --- | --- |
| No speedup after `-fprofile-use` | Profile hash mismatch, functions fell back to heuristics | Check build log for out-of-date/stale-profile warnings; retrain |
| Regression after rebuild | Training workload does not match production mix | Resample production traffic; canary before rollout |
| Huge binaries, cold code everywhere | No hot/cold splitting; everything inlined for size | Verify PGO actually attached; check `--print-debug-info`/layout |
| PGO helps dev, not prod | Profile from synthetic benchmark | Continuous sampling infra (AutoFDO/BOLT pipeline) |

## References

- Pettis, K. & Hansen, R. C., "Profile Guided Code Positioning," PLDI 1990: <https://doi.org/10.1145/93542.93550>
- Chen, D., Li, D. X., & Moseley, T., "AutoFDO: Automatic Feedback-Directed Optimization for Warehouse-Scale Applications," CGO 2016: <https://doi.org/10.1145/2854038.2854044>
- Panchenko, M. et al., "BOLT: A Practical Binary Optimizer for Data Centers and Beyond," CGO 2019: <https://doi.org/10.1109/CGO.2019.8661201>
- Clang User's Manual, "Profile Guided Optimization": <https://clang.llvm.org/docs/UsersManual.html#profile-guided-optimization>
- GCC Documentation, "Instrumentation Options" (`-fprofile-generate`, `-fprofile-use`, `-fprofile-values`): <https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html>
