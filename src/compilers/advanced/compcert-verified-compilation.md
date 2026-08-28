# CompCert: Inside the Machine-Checked Compiler

[Verified Compilation & CompCert](./verified-compilation.md) makes the general argument: compilers miscompile in practice, testing cannot bound absence of bugs, and CompCert answers with a machine-checked preservation theorem. This page stays inside the machine and answers a different set of questions: *which* passes are actually proved, *which* language is the proof anchored at, what a single proof obligation looks like, where the compiler silently switches from proving to checking, and what parts of the toolchain the word "verified" never touches. The semantics-side background (operational semantics, "going wrong", observable behavior) lives in [Formal Semantics](./formal-semantics.md).

Everything below reflects the pass inventory published with the compiler itself [1]; release facts are from the official distribution's release history [5].

## The three bands: proved, validated, trusted

CompCert is not one theorem about one blob of code. It is a chain of about a dozen transformations, each with its own proof, and the chain has holes on both ends. Reading the pipeline as three bands makes the actual trust arrangement visible:

```text
   C source file
        |
        |  preprocessor, lexer, parser, typechecker, elaboration
        |  ..................................... UNVERIFIED (plain OCaml)
        v
   CompCert C abstract syntax tree
        |
        |  SimplExpr, SimplLocals, Cshmgen, Cminorgen, Selection, RTLgen,
        |  RTL optimizations, Tunneling, Linearize, CleanupLabels, Debugvar,
        |  Stacking, Asmgen, + the composed top-level theorem
        |  ..................................... COQ-PROVED, pass by pass
        |        (one exception inside this band:)
        |        RTL -> LTL register allocation = UNVERIFIED oracle
        |                                        + COQ-PROVED validator
        v
   Asm abstract syntax
        |
        |  Asm printer, external assembler, linker, runtime libraries,
        |  operating system, hardware
        |  ..................................... UNVERIFIED / TRUSTED
        v
   executable binary
```

Three observations about this arrangement that interviewers like to probe:

- **The proof does not start at C.** It starts at the *CompCert C abstract syntax tree*. The front end that produces that AST -- preprocessing, lexing, parsing, typechecking/elaboration into the AST -- is unverified OCaml. The preservation theorem is relative to the AST: if the front end mis-elaborates your source, the compiler will faithfully preserve the semantics of the wrong program. The accepted risk is that a parser/typechecker bug changes *which* program gets the guarantee, not that the guarantee is false for the program it sees.
- **The proof does not end at a binary.** It ends at `Asm` abstract syntax. The pretty-printer that turns `Asm` into assembly text, and the external assembler and linker that turn text into an executable, are outside every proof. (Bugs here are rarer and easier to test than optimizer bugs, which is the qualitative defense -- but they are trust, not proof.)
- **One band is neither proved nor fully trusted.** Register allocation is *validated*: an unverified algorithm proposes, a verified checker disposes. That hybrid gets its own section below, because it is the single most interesting engineering decision in the pipeline.

## The IR ladder, pass by pass

The intermediate languages the mission-standard retelling lists are *almost* right -- the ladder actually has a `Linear` stage between `LTL` and `Mach` that summaries routinely drop, and the first proved pass starts from `CompCert C`, not `Clight` directly. The verified pass inventory [1]:

| Pass | From -> To | What it does | Status |
|------|------------|--------------|--------|
| (front end) | C -> CompCert C AST | preprocess, lex, parse, typecheck | unverified |
| SimplExpr | CompCert C AST -> Clight | pull side effects out of expressions; fix an evaluation order | proved |
| SimplLocals | Clight -> Clight | pull non-addressable scalar locals out of memory | proved |
| Cshmgen | Clight -> Csharpminor | simplify control structures; make type-dependent computations explicit | proved |
| Cminorgen | Csharpminor -> Cminor | stack-allocate address-taken locals; simplify switches | proved |
| Selection | Cminor -> CminorSel | recognize machine operators/addressing modes; if-conversion | proved |
| RTLgen | CminorSel -> RTL | build the CFG; emit 3-address code over unlimited pseudo-registers | proved |
| Tailcall / Inlining / Renumber / Constprop / CSE / Deadcode / Unusedglob | RTL -> RTL | the optimizer: tail calls, inlining, CFG renumbering, constant propagation, CSE, dead-code elimination, unused-globals removal | proved |
| Allocation | RTL -> LTL | register allocation: unverified oracle + verified validator | validated |
| Tunneling | LTL -> LTL | branch tunneling | proved |
| Linearize | LTL -> Linear | replace the CFG with a linear instruction list + explicit branches | proved |
| CleanupLabels / Debugvar | Linear -> Linear | drop unreferenced labels; synthesize debug info | proved |
| Stacking / Stacklayout | Linear -> Mach | lay out activation records (concrete stack frame view) | proved |
| Asmgen | Mach -> Asm | emit target assembly abstract syntax | proved |
| Compiler | all of the above | compose every lemma into the whole-compiler preservation theorem | proved |

Language ladder in one line: `Clight -> Csharpminor -> Cminor -> CminorSel -> RTL -> LTL -> Linear -> Mach -> Asm`. RTL carries infinitely many pseudo-registers and a control-flow graph; LTL shrinks registers down to the finite physical set and moves overflow into infinitely many stack slots; Linear makes instruction order explicit; Mach makes the stack frame concrete; Asm is the target assembly syntax. The RTL optimizations are supported by static analyses (liveness, value/alias analysis, neededness analysis) that are formalized inside the same development -- they are not external tools bolted on.

## Forward simulation: what one proof obligation looks like

Every proved arrow in the table discharges the same shaped obligation. Draw the executions of source and target side by side, with `R` a relation between source states and target states (typically "the memory model, register file, and program counter correspond"):

```text
   source  S0 --tau--> S1 --out 5--> S2 --tau--> S3 --> ... (terminates)
             |            |              |
             | R          | R            | R        R = state relation
             v            v              v
   target  T0 --tau--> T1 --out 5--> T2 --tau--> T3 --> ... (terminates)
```

The per-pass lemma is a **forward simulation**: whenever the source program can take a step from `S_i` to `S_j` -- emitting an observable event or the silent token `tau` -- the compiled program, started in a state `T_i` with `R(S_i, T_i)`, can take steps to some `T_j` with `R(S_j, T_j)`, emitting the *same* observable events along the way. Because target steps may include extra `tau`s, this is a *weak* simulation: the target may do more work per source step, but the outside world cannot see it.

Composition is what makes the architecture scale: each pass proves its own simulation lemma against the state relation between its two languages, and Coq composes the lemmas transitively into the top-level theorem. In plain shape, the whole-compiler result is:

```text
   If the source program p does not go wrong under the CompCert-C
   semantics, and compilation of p succeeds producing tp, then tp does
   not go wrong, and every observable behavior of tp is an observable
   behavior of p: the same trace of input/output events, and the same
   termination condition (terminates, or runs forever).
```

This is what "no miscompilation" means formally, and it is *stronger and weaker* than naive expectations in specific ways. Stronger: it is not "usually correct" or "tested correct" -- it is a quantified statement over all executions and all inputs, machine-checked down to axioms of logic. Weaker-looking by design: it is *refinement*, not full equivalence. The compiled code may exhibit only a subset of the source's allowed behaviors; if the source was nondeterministic (unspecified evaluation order, for instance), the compiler was always allowed to pick one. Observational equivalence falls out where it matters: any runtime context that distinguishes the two programs would have to distinguish them by a trace of I/O events or by a termination difference -- and the theorem says there is none. A subject that has never seen the proof can still check the theorem's shape against its consequences, which is exactly the exercise the [Verified Compilation](./verified-compilation.md) page walks through statement-by-statement.

## The validated pass: register allocation as embedded translation validation

Everything in the pipeline is proved except one algorithm: the register allocator that turns RTL (unbounded pseudo-registers) into LTL (physical registers and stack slots). Proving a state-of-the-art allocator (spilling heuristics, coalescing, live-range splitting) correct outright has historically defeated the cost/benefit analysis. CompCert's answer, developed in Rideau & Leroy's work on validating register allocation and spilling [4], is to *not prove the allocator* and instead prove a **validator**: an unverified oracle (an OCaml implementation, external to the proved core) proposes an allocation, and a Coq-proved checker examines the input RTL function and the proposed LTL function and decides whether the allocation is semantics-preserving -- right values in right locations at each program point, live ranges respected, stack slots disjoint where required.

If the validator rejects, the compiler aborts with an error rather than emit code no one has checked. The correctness of the resulting compiler therefore never depends on the cleverness of the allocator, only on the honesty of the checker -- and the checker is small enough to prove. This is translation validation [3] *embedded inside* a proven compiler: the same checking-after-the-fact discipline that [Translation Validation & Compiler Bootstrapping](../translation-validation-bootstrapping.md) covers end-to-end (Alive2 for LLVM, and the validation-vs-verification tradeoff generally), applied at exactly the one pass where full proof was too expensive. For the allocator's own data structures and why the pass is hard, see [Register Allocation](./register-allocation.md).

## What the guarantee does not cover

The theorem's boundary is precise, and quoting it honestly is the difference between understanding CompCert and marketing it:

| Component | Verified? | If it is wrong |
|-----------|-----------|----------------|
| Preprocessor, lexer, parser, typechecker/elaboration | no | wrong program gets compiled *correctly*; guarantee is relative to the AST produced |
| Register-allocation oracle | no | allocation rejected by the proved validator -> compilation aborts, not wrong code |
| All passes Clight -> Asm + their composition | yes (Coq) | a proof hole here would be a flaw in the theorem itself; none is known [1] |
| Asm printer, assembler, linker | no | binary can differ from proved `Asm` semantics; small, heavily exercised surface |
| Runtime libraries, OS, CPU | no | hardware errata and libc bugs are the program's problem, not the theorem's |
| Coq kernel, extraction to OCaml, the OCaml toolchain | trusted | the proof is only as good as the kernel checking it; a known, stated trust root |
| A handful of classical axioms (functional extensionality, proof irrelevance, excluded middle) | stated | listed explicitly in the distribution so the trust root is auditable |

The sharpest boundary, though, is the **input side: undefined behavior**. CompCert compiles CompCert-C, a defined-behavior subset of ISO C99/C11 -- a large one, but with a semantics that assigns meanings rather than voiding them. The preservation theorem is stated *per execution*: an execution of the source that never enters an undefined situation is preserved exactly; once an execution enters undefined behavior, the theorem says nothing about that execution, and the compiler was entitled to have exploited it (deleted the branch, assumed the impossible, picked any outcome). In a few documented corners the CompCert-C semantics even *gives* a defined meaning where ISO C leaves behavior undefined -- a deliberately conservative direction -- but no such charity runs the other way. For programs whose safety depends on staying inside defined behavior (which is what MISRA-style coding rules exist to enforce), the guarantee holds; for anything else, all bets were off before the compiler was ever invoked.

## Performance: the price of the proof

The classic objection to verified compilation was that a provably correct compiler would be a toy. Leroy's published measurements in the CACM 2009 and JAR 2009 papers [2, 3] addressed this qualitatively: on his benchmark suites, CompCert-generated code ran modestly slower than GCC at moderate optimization -- on the order of 15-20% behind `gcc -O1`, clearly ahead of unoptimized output, and generated at a fraction of GCC's compile-time sophistication. The gap is structural, not accidental: CompCert deliberately ships a *smaller* optimization arsenal (no aggressive vectorization, no superblock scheduling, a validated-but-not-tuned allocator) because every additional pass must carry its own proof to remain inside the theorem. The engineering lesson generalizes: the verified pipeline optimizes for *provable* transformations, and the residual performance cost is the listed price of the unbounded quantifier "for all executions".

## Industrial deployment (kept qualitative)

The commercial and certification story is real but mostly lives in qualification documents rather than papers, so it is best stated cautiously: CompCert has been distributed commercially (AbsInt) alongside the INRIA non-commercial research license; it has been qualified by ANSSI (France) for use in the development of certifiable safety-critical systems; and it was publicly demonstrated in 2012 in a fly-by-wire flight-control computer context by Dassault Aviation -- routinely cited as the first industrial use of a formally verified compiler in that domain. Avionics certification regimes (the DO-178C family) are where a compiler with a machine-checked preservation theorem changes the cost equation, because qualification credit for a verified tool substitutes for enormous amounts of testing evidence. As of this writing (Aug 2026) the project remains actively maintained, with release v3.17 published in February 2026 [5].

## A forward-simulation checker, small enough to run

The proof obligations above reduce to a mechanical check on traces, which is exactly why they can be mechanized. Below is a two-instruction-set toy: a stack-machine source VM, a register-machine target VM, a one-pass "compiler", and a checker that runs both machines in lockstep, maintains the state relation `R` (stack slot `i` lives in register `i`), and reports PRESERVED or DIVERGED. A deliberately broken compiler shows the checker catching a miscompilation.

```python
# compcert_sim_demo.py -- miniature forward-simulation checker.
# Source VM: stack machine.  Target VM: registers.  R: stack[i] == reg[i].

def step_src(prog, st):
    pc, stk = st
    if pc >= len(prog):
        return (None, None)                         # halted, no event
    op = prog[pc]
    if op[0] == "PUSH":
        return ((pc + 1, stk + [op[1]]), None)
    if op[0] == "ADD":
        if len(stk) < 2: return ("wrong", None)
        return ((pc + 1, stk[:-2] + [stk[-2] + stk[-1]]), None)
    if op[0] == "OUT":
        if not stk: return ("wrong", None)
        return ((pc + 1, stk), ("out", stk[-1]))    # observable event
    return ("wrong", None)

def step_tgt(prog, st):
    pc, regs = st
    if pc >= len(prog):
        return (None, None)
    op = prog[pc]
    if op[0] == "LOADI":
        return ((pc + 1, {**regs, op[1]: op[2]}), None)
    if op[0] == "ADDR":
        return ((pc + 1, {**regs, op[1]: regs[op[1]] + regs[op[2]]}), None)
    if op[0] == "OUTR":
        return ((pc + 1, regs), ("out", regs[op[1]]))

def relate(s, t):
    """R: both halted, or equal pcs with reg[i] == stack[i].
    Dead registers may keep stale values -- the relation constrains
    only the live part, exactly like a real allocation validator."""
    if s is None or t is None:
        return (s is t, "one side halted early")
    (spc, stk), (tpc, regs) = s, t
    if spc != tpc:
        return (False, "pc %d vs %d" % (spc, tpc))
    if any(regs.get(i) != stk[i] for i in range(len(stk))):
        return (False, "stack %s vs regs %s" % (stk, regs))
    return (True, "")

def compile_stack_to_regs(prog):
    out, depth = [], 0                              # slot i -> register i
    for op in prog:
        if op[0] == "PUSH": out.append(("LOADI", depth, op[1])); depth += 1
        elif op[0] == "ADD": out.append(("ADDR", depth - 2, depth - 1)); depth -= 1
        elif op[0] == "OUT": out.append(("OUTR", depth - 1))
    return out

def check_simulation(src, tgt, max_steps=64):
    s, t, evs = (0, []), (0, {}), []
    for k in range(max_steps):
        s2, ev_s = step_src(src, s)
        t2, ev_t = step_tgt(tgt, t)
        if ev_s != ev_t:
            return "step %d: DIVERGED -- events %s vs %s" % (k, ev_s, ev_t)
        if ev_s is not None: evs.append(ev_s)
        if s2 == "wrong": return "step %d: source went wrong -- no guarantee, check withdrawn" % k
        if t2 == "wrong": return "step %d: DIVERGED -- target went wrong alone" % k
        ok, why = relate(s2, t2)
        if not ok:
            return "step %d: DIVERGED -- relation broken (%s); src=%s tgt=%s" % (k, why, s2, t2)
        s, t = s2, t2
        if s is None:
            return ("PRESERVED -- %d observable events matched, both terminated, "
                    "R held at every step: %s" % (len(evs), evs))
    return "step bound exceeded"

src = [("PUSH", 2), ("PUSH", 3), ("ADD",), ("OUT",), ("PUSH", 10), ("OUT",)]
good = compile_stack_to_regs(src)
buggy = [("LOADI", 0, 2), ("LOADI", 1, 3), ("ADDR", 0, 0), ("OUTR", 0),
         ("LOADI", 1, 10), ("OUTR", 0)]            # ADD compiles to r0 += r0
print("program :", src)
print("compiled:", good)
print("A:", check_simulation(src, good))
print("B:", check_simulation(src, buggy))
```

Actual output (run as shown above):

```text
program : [('PUSH', 2), ('PUSH', 3), ('ADD',), ('OUT',), ('PUSH', 10), ('OUT',)]
compiled: [('LOADI', 0, 2), ('LOADI', 1, 3), ('ADDR', 0, 1), ('OUTR', 0), ('LOADI', 1, 10), ('OUTR', 1)]
A: PRESERVED -- 2 observable events matched, both terminated, R held at every step: [('out', 5), ('out', 10)]
B: step 2: DIVERGED -- relation broken (stack [5] vs regs {0: 4, 1: 3}); src=(3, [5]) tgt=(3, {0: 4, 1: 3})
```

Run A is the theorem in miniature: every step of the target stayed inside the set of behaviors the source allows, the observable traces match, and the state relation held at every step -- the trace-level content of forward simulation. Run B is a miscompilation (the `ADD` compiled to `r0 += r0`) caught by exactly the mechanism CompCert's validator uses: the state relation broke at the first step where the target's registers no longer mirrored the source's stack. One subtlety visible in run A: after the `ADD`, register 1 still holds the stale value 3 -- dead registers are unconstrained, so the relation checks only the live part, which is why real validators reason over liveness rather than full memory images.

## Where this sits

- [Verified Compilation & CompCert](./verified-compilation.md) -- the argument for needing this, the theorem-statement progression, and what came after (CakeML, Vellvm); this page is the CompCert-specific mechanics it points at.
- [Translation Validation & Compiler Bootstrapping](../translation-validation-bootstrapping.md) -- the checking discipline CompCert embeds in its one unproved pass, and the bootstrapping trust problem CompCert's theorem does not solve.
- [Formal Semantics](./formal-semantics.md) -- the operational-semantics machinery ("goes wrong", traces, determinism) the simulation statements are written against.
- [Register Allocation](./register-allocation.md) -- what the oracle in the validated pass actually computes.

## References

1. CompCert project, official site and documentation (language and pass inventory; `compcert.inria.fr` redirects here). https://compcert.org/ and https://compcert.org/doc/
2. X. Leroy. Formal verification of a realistic compiler. *Communications of the ACM* 52(7), 2009 (expanded from the POPL 2009 paper of the same title). DOI: 10.1145/1538788.1538814
3. X. Leroy. A Formally Verified Compiler Back-end. *Journal of Automated Reasoning* 43(4):363-446, 2009. DOI: 10.1007/s10817-009-9155-4
4. S. Rideau, X. Leroy. Validating Register Allocation and Spilling. *Compiler Construction (CC 2010)*, LNCS 6011. DOI: 10.1007/978-3-642-11970-5_13
5. AbsInt/CompCert release history (v3.17, February 2026). https://github.com/AbsInt/CompCert/releases
