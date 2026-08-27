# Verified Compilation and CompCert

Every argument about your program's correctness - a static-analysis result, a proof effort, a code review - silently assumes the compiler did not change what the program does. CompCert attacks that assumption directly: it is a realistic C compiler whose verified core is written and proved in the Coq proof assistant, so that a machine-checked theorem states the generated code preserves the observable behavior of the source. Xavier Leroy's CACM 2009 paper describing the first release remains the canonical account [1]; the compiler has been industrialized since (ANSYS/AbsInt distribution, ISO C 2011 coverage, ARM/PowerPC/RISC-V/x86 targets) and, as of 2026, is qualified to carry DO-178C certification credit in avionics [2].

This page covers the empirical case for worrying about miscompilation, the exact formal statement "correct compilation" gets replaced with, the architecture of the verified core, the trusted computing base that the theorem deliberately does *not* cover, and the landscape of what came after - CakeML, Vellvm, Iris, and translation validation as the lighter-weight alternative covered in depth in [Translation Validation & Compiler Bootstrapping](../translation-validation-bootstrapping.md).

## The empirical case: compilers do miscompile

CompCert's own motivation page [2] collects three studies that make miscompilation concrete rather than hypothetical:

| Study | Method | Result |
|-------|--------|--------|
| Nullstone C conformance suite, 1995 | Conformance testing of commercial compilers | Defects in integer division found in 12 of 20 compilers evaluated |
| Eide & Regehr, EMSOFT 2008 | Testing `volatile` access code generation | All 13 production C compilers tested miscompiled some volatile accesses |
| Yang et al., PLDI 2011 (Csmith) | 2.5 years of random-program differential testing | 325+ previously unknown wrong-code bugs; every tested compiler both crashed and silently generated wrong code on valid inputs |

The 2008 result is the sharpest for critical embedded software: `volatile` accesses are exactly the construct that OS kernels and device drivers depend on, and "we tested thirteen production-quality C compilers and, for each, found situations in which the compiler generated incorrect code" [2]. The Csmith headline matters for a different reason: wrong-code bugs found by testing were fixes to bugs *someone happened to trigger*. Testing bounds bug density; it cannot bound absence.

## What "correct compilation" means formally

"Doesn't change the program's behavior" is not a theorem; it has to be sharpened into one. Leroy's paper works through the sharpening [1], and the progression is the best short lecture on semantic preservation:

1. **Observable behavior.** A program's observable behavior is its termination, divergence, or "going wrong" (invoking an operation that can crash), together with the trace of input/output operations (system calls) it performs. This is what the outside world can actually see.
2. **Naive statement.** Source and compiled program have exactly the same observable behaviors: `forall B, S ==> B <-> C ==> B`. Too strong: nondeterministic sources legitimately let the compiler pick one behavior, and optimizations may delete a "going wrong" behavior whose result is unused.
3. **The usable statement.** If the source is *safe* (no going-wrong behavior), then every observable behavior of the compiled code is an allowed behavior of the source:

```text
   (2)  S safe  =>  ( forall B, C ==> B  =>  S ==> B )

   (3)  deterministic case:
        forall B not in Wrong,  S ==> B  =>  C ==> B

   consequence for verified sources:
        S |= Spec  =>  C |= Spec
```

Note the direction and the side condition. The theorem is *not* "compiled code is correct"; it is "compilation preserves whatever the source guarantees, provided the source stays in defined behavior." Undefined behavior remains the user's problem - a fact that shapes everything else about verified compilation, including CompCert's refusal to compile programs whose behavior the source semantics cannot pin down.

The formulation earns its abstraction in composition. The whole value of source-level formal methods - abstract interpreters, deductive verifiers, model checkers - is a statement of the form `S |= Spec`. But those tools reason about the C source, and the machine executes the binary; a buggy compiler breaks the chain between them, quietly voiding every source-level guarantee. CompCert's property plugs exactly that gap: prove the program at the source level with whatever tool you like, and the compiler theorem transports `S |= Spec` to the executable. This argument - verified source, verified compilation, one end-to-end guarantee - is the sentence that carried CompCert from a research prototype into certification-critical toolchains.

## One pass, one theorem

CompCert is structured the way compilers are normally structured - a chain of passes over intermediate languages - and the correctness statement is lifted through the chain. Each pass carries its own semantic-preservation theorem; the composition theorem chains them into an end-to-end result. Schematically, in the style the development states it:

```coq
(* Schematic of the per-pass correctness statement, in the shape used by
   CompCert-style developments: source behaviors are preserved by the
   compiled code, modulo the safety side condition.  In CompCert itself
   this is not a hypothesis but a proved theorem for every pass. *)

Section PassCorrect.

  Variable behavior : Type.                     (* observable behaviors  *)
  Variable Wrong    : behavior.                 (* "going wrong"         *)

  Variable Source Target : Type.                (* adjacent languages    *)
  Variable SemS : Source -> behavior -> Prop.   (* source semantics      *)
  Variable SemT : Target -> behavior -> Prop.   (* target semantics      *)
  Variable compile : Source -> option Target.   (* the pass itself       *)

  Definition safe (p : Source) : Prop :=
    forall B, SemS p B -> B <> Wrong.

  Hypothesis pass_correct :
    forall (p : Source) (tp : Target),
      compile p = Some tp ->
      safe p ->
      forall B, SemT tp B -> SemS p B.

End PassCorrect.
```

The pass itself (`compile`) is also written in Coq's functional language, then extracted to OCaml for the shipped executable. The compiler is the theorem's subject and its implementation at once, which removes the usual "does the model match the code?" gap for the verified core. The proof-assistant machinery behind this style of development is covered in [Coq & Lean](../../formal-methods/coq-lean.md).

## Architecture: passes, intermediate languages, proofs

The CACM 2009 compiler ran 14 passes through 8 intermediate languages; the current release is 16 passes over 10 intermediate languages [1][3]. The spine:

```text
  C source
     |  (UNVERIFIED: preprocessor + parser/elaboration)
     v
  Clight ----> C#minor ----> Cminor ----> Cminor/Sel ----> RTL
  typed,       loops->blocks  typeless,    function         register
  32/64-bit    + multi-exits  no &operator  placement       transfer lang
     ^             ^              ^             ^               |
     |             |              |             |               |  dataflow opts:
     |             |              |             |               |  const prop,
     |             |              |             |               v  value numbering,
   semantics     operator       address-of   stack alloc   instr selection  DCE
   1100 LOC Coq  splitting      elimination
                                                                |
  PPC/ARM/x86/RISC-V <---- Mach <---- LTL <---- Linear <------- LTL
  assembly            physical regs  pseudo-regs  spilling      (graph coloring,
     |                                                              Appel-George)
     |  (UNVERIFIED: printer, assembler, linker)
     v
  executable binary
```

The front-end deletes C-specificities (type-dependent operator overloading, loops, address-of); the back-end is a classic register-allocation pipeline, but every arrow above carries a preservation proof. The 2009 accounting: 42,000 lines of Coq (excluding comments/blanks) at roughly 3 person-years, of which 14% is compilation algorithm, 10% language semantics, and 76% the correctness proofs; a typical pass costs 1,500-3,000 lines of Coq, each intermediate language 300-600 [1]. That ratio - proofs are five times the code - is the recurring price tag of verified compilation, and the reason research since has concentrated on cheaper assurance modes (validation, verified verifiers) for fast-moving optimizers.

## The trusted computing base

The theorem covers the passes between Clight and assembly-level abstract syntax. Leroy's own list of what you must still trust [1] is the honest boundary of the guarantee:

```text
   +-------------------------------------------------------------+
   |  OUTSIDE the correctness theorem (the TCB)                  |
   |                                                             |
   |   C source --> [cpp + parser/elaboration] --> Clight        |
   |   assembly abstract syntax --> printer --> assembler        |
   |                                --> linker --> binary        |
   |                                                             |
   |   + Coq extraction mechanism                                |
   |   + the OCaml compiler and runtime that run the extracted   |
   |     compiler                                                |
   |   + the Coq kernel that checks the proofs                   |
   |   + the formal semantics of Clight and the target ISA       |
   |     (do they match ISO C and the silicon?)                  |
   +-------------------------------------------------------------+
```

This is not a footnote; it is where the one famous production incident landed. A widely discussed case from industrial use: a CompCert user on a safety-critical program hit a wrong-code bug - located in the hand-written C front-end, the *unverified* part of the chain, and fixed in a subsequent release. The case is remembered precisely because it validated the TCB analysis: the verified core has accumulated roughly two decades of industrial use with no wrong-code bug reported in the proved passes, while the bug that did occur fell exactly inside the predicted trust boundary. Bugs in the unverified front-end continue to be documented in the release notes of the industrial distribution [2]. (For contrast, the parser bug class itself has since been eliminated in successor projects - see CakeML below, which proved its parser sound *and complete*.)

Why not verify the parser and assembler too? Semantic preservation for a parser is awkward to even state (the "semantics" of concrete syntax *is* the AST), the ISO C standard deliberately leaves preprocessing and translation limits to the implementation, and assembler/linker verification is "feasible, if unexciting" in Leroy's phrase [1]. Successor projects made different trade-offs - CakeML wrote its whole toolchain inside the logic; seL4 sidestepped its C compiler assumption via translation validation ([seL4 Kernel Verification](../../formal-methods/sel4-verification.md)).

## When the theorem is load-bearing

A subtle property of the CompCert setup is *where* a failure would show up, and it is worth spelling out because it is the difference between assurance theater and real evidence.

- **A bug in the proved core is essentially impossible to ship silently.** The extraction pipeline regenerates the compiler from the Coq sources, and the Coq kernel re-checks every proof term against the logic each build. If someone edits a pass and breaks its preservation theorem, the build fails - loudly, at compile time of the compiler, in front of the engineers. The development is on GitHub [2] precisely so this re-checking is reproducible.
- **A bug in the TCB ships silently.** The parser, the assembler, the linker, the extraction mechanism, the OCaml runtime: defects there are ordinary software defects, found by ordinary means (or by users, as the parser incident above showed). The TCB is small and inspectable, but it is where the residual risk lives.
- **The assumptions are load-bearing too.** "The formal semantics of Clight matches ISO C" is a mathematical-modeling claim, not a theorem. It is defended by review, testing the executable semantics, and cross-checks against independently developed semantics - informal anchors around a formal core [1].

This failure-mode analysis is what made the certification argument of DO-333 plausible: a qualification authority can inspect a short, explicit list (proved theorem, TCB inventory, assumption list) instead of the compiler's entire source. The seL4 project's assumption pages make the same move for kernels - small, stated, auditable trust bases on both sides of the verified-systems world.

## Performance and certification

Two objections meet every verified compiler: is the code any good, and can it be used in regulated industries?

**Code quality.** The CACM 2009 benchmarking against GCC 4.0.1 reported CompCert-generated code more than twice as fast as unoptimized GCC output, on average 7% slower than `gcc -O1` and 12% slower than `gcc -O2` [1]. CompCert implements the dataflow workhorses (constant propagation, value-numbering CSE, dead-code elimination, graph-coloring register allocation) but not the most aggressive loop transformations of production optimizers. The gap versus modern GCC/Clang at `-O2` remains the price of proof; for the safety-critical segment CompCert targets, that price is routinely accepted because the alternative assurance route - analyzing generated assembly by hand - costs far more.

**Certification.** This is where CompCert diverged from academia into industry. It underpins ANSYS SCADE Suite KCG (qualified code generator) toolchains used by Airbus and others, and in March 2026 it was qualified for the MFC_NG flight computer of the ATR 42/72, claiming certification credits for DO-178C/DO-333/DO-330 compliance on critical avionics software - reported as the first time such credits were claimed from compiler usage [2]. The argument DO-333 formally allows is exactly CompCert's: a verified tool can replace verification activities that would otherwise be performed on its output. Release 3.17 (February 2026) added compatibility with the Rocq prover (the renamed Coq) 9.1; release 3.16 (September 2025) added position-independent code support [2].

## The landscape after CompCert

- **CakeML** - the maximalist answer. An ML implementation whose *entire* toolchain lives inside the HOL4 logic: the compiler backend to six target architectures, but also the parser (proved sound and complete against the grammar), the type inferencer, and the self-bootstrap - the compiler compiled itself inside the logic, yielding a verified binary implementing the compiler [3]. Version 1 shipped a verified read-eval-print loop, so even the interactive session is inside the proof. Descendant verified compilers (Pancake, PureCake, Candle - a verified HOL Light) build on its infrastructure.
- **Vellvm** - CompCert's move applied to the ecosystem people actually use: a Coq development formalizing LLVM's IR and proving transformations over it [4]. Where CompCert proves its own passes, Vellvm lets verification target LLVM's.
- **Iris** - the proof-infrastructure descendant: a higher-order concurrent separation logic framework (implemented in Coq/Rocq) that has become the standard tool for verifying programs *and* verifying type systems and language semantics - the kind of source-level verification whose results CompCert then preserves into machine code [5].
- **Translation validation and verified verifiers** - the lightweight alternative. CompCert itself experimented with the "verified verifier" design: run an aggressive untrusted optimization (instruction scheduling, lazy code motion) in OCaml, then check its output with a *proved* symbolic-evaluation validator - only the checker needs a proof. This is the same economics as Alive2 validating LLVM's passes per-run with SMT, treated in depth in [Translation Validation & Compiler Bootstrapping](../translation-validation-bootstrapping.md). The trade is per-run checking cost and bounded coverage against a fraction of the proof effort.

The unresolved debate is about how much assurance the market will pay for. Mainstream compilers ship a known, small rate of wrong-code bugs (Csmith's numbers above), and most software lives with that - compilers are, in the dismissive phrase used by skeptics of verification efforts, "not buggy enough" to justify rewriting them in a proof assistant. The counter-evidence is sector-specific: aviation toolchains qualified on CompCert, and seL4 deployments, exist because in those domains the question is not average bug rate but whether any *known* pathway to silent corruption remains. Verified compilation did not replace GCC; it carved out a high-assurance niche and, just as importantly, exported its techniques - simulation proofs, compositional pass theorems, verified validators - into the toolchains of unverified compilers.

The design space those projects now occupy, compressed:

| System | What is proved | Logic | Front-end inside the proof? | Relation to CompCert |
|--------|----------------|-------|-----------------------------|----------------------|
| CompCert | C compiler core, pass by pass, to 4 ISAs | Coq/Rocq | No (parser/elaboration unverified) | The original realistic result |
| CakeML | Compiler backend, parser, type inference, bootstrap, REPL | HOL4 | Yes (proved sound and complete) | Maximalist successor, different source language |
| Vellvm | Selected LLVM IR transformations | Coq | N/A (targets LLVM's own IR) | Ports the method to the dominant IR |
| Alive2 / TV | Each optimization's input/output pair, per run | SMT encodings | N/A | No proof, per-run checking of unverified compilers |

## References

- X. Leroy, "Formal verification of a realistic compiler", CACM 52(7), 2009 (author's copy; all quotes, pass counts, LOC and benchmark numbers above) - <https://xavierleroy.org/publi/compcert-CACM.pdf>
- CompCert project site: news (3.16/3.17 releases, Rocq 9.1, ATR 42/72 MFC_NG DO-178C qualification), motivations and research pages; sources live at github.com/AbsInt/CompCert - <https://compcert.inria.fr/>
- CakeML project: verified backend, verified parser and type inferencer, verified bootstrap and REPL - <https://cakeml.org/>
- Vellvm (Verified LLVM) Coq development - <https://github.com/Vellvm/vellvm>
- Iris project: higher-order concurrent separation logic in Coq/Rocq - <https://iris-project.org/>
