# seL4 Kernel Verification

In 2009, a team at NICTA (now Trustworthy Systems, UNSW) published the first machine-checked functional correctness proof of a complete, general-purpose OS kernel. The verified artifact, seL4, is a third-generation L4 microkernel of 8,700 lines of C plus 600 lines of assembler. The proof that pinned the C code to its abstract specification weighed about 200,000 lines of Isabelle/HOL script and cost roughly 20 person-years. Three developments since then turned a landmark paper into an engineering practice: the security properties integrity and confidentiality were proved on top of the correctness result, the binary code itself was brought into the proof via translation validation, and the whole proof base is now maintained continuously against the evolving kernel - the seL4 fact sheet currently reports 1.3 million lines of proofs and zero violations of verified properties since 2009.

This page dissects what exactly was proved, how the proof stack is assembled, what it deliberately does not cover, and why the capability-based kernel design is what made verification tractable at this scale. For a survey of other verified systems (CompCert, HACL*, CakeML), see [Verified Systems](./verified-systems.md); for the kernel-architecture comparisons (L4 vs monolithic vs exokernel), see [Kernel Architectures](../os/advanced/kernel-architectures.md).

## What is actually proved

The seL4 proofs are not one theorem but a stack of statements about different artifacts. The seL4 project's proof pages enumerate them as follows:

| Property | Precise statement | First established |
|----------|-------------------|-------------------|
| Functional correctness | The C implementation is a refinement of the abstract specification: every behavior of the C code is one allowed by the spec | Klein et al., SOSP 2009 |
| Security enforcement | In a correctly configured system the kernel enforces integrity (no unauthorized modification), confidentiality (no unauthorized information flow), and availability (no unauthorized denial of resource access) | Murray et al., IEEE S&P 2013 |
| Binary correctness | The machine code the compiler emits implements the same behavior as the C code, closing the compiler-trust gap | Sewell et al., PLDI 2013 |
| System initialisation | The user-level boot protocol produces exactly the capability distribution the static system description demands | capDL-based work, 2012+ |

Two remarks keep this honest. First, "functional correctness" here means *refinement*, not equality: the C code may exhibit fewer behaviors than the spec allows (the kernel has no obligation to be slow in exactly the way the spec is vague about), but it can never step outside the spec's envelope. Second, every statement is conditional on a short, explicit list of assumptions discussed below - the proofs are unconditional only about the C text itself.

One free by-product is worth stating explicitly. Because refinement subsumes "the kernel never does anything the spec does not allow," it immediately excludes entire bug classes in verified configurations: buffer overflows, null-pointer dereferences, use-after-free, arithmetic exceptions, and undefined behavior generally. Nobody wrote separate proofs for these; they fall out of the main theorem.

### Reading it like an engineer

Concretely, suppose a system has two protection domains: a critical controller and an untrusted legacy stack. Given a correctly configured system (no write capabilities between them), the theorem stack delivers:

- **Integrity**: the legacy stack cannot modify the controller's memory or capabilities, no matter how it is compromised - the kernel code provably refuses the access, so there is no exploit path through the kernel.
- **Confidentiality**: the legacy stack cannot learn the controller's data by observing kernel behavior (storage channels proved out; timing channels are the open part - see below).
- **Availability**: the legacy stack cannot revoke the controller's capabilities or interfere with its authorized resource access - an unusual property to see proved at kernel level, and the one that separates seL4's statement from "just memory safety."

The FAQ's answer to "so does seL4 have zero bugs?" is deliberately two-sided: yes under the formal-verification meaning (code implements spec, modulo assumptions), potentially no under a general user's meaning (hardware bugs or unmet assumptions can still bite). Both halves are accurate, and the second half is why the assumptions section below matters.

## The proof stack: from Haskell prototype to checked C

The original verification chain was unusual because it fused the development process with the proof process. The kernel was designed as a Haskell prototype that doubled as the *executable specification*: running it on real hardware forced the design to be concrete before any proof work started. A purpose-built translator (about 3 person-months of work, per the SOSP 2009 paper) converted the Haskell prototype into an executable specification in Isabelle/HOL. The C implementation was then proved correct in two refinement steps, summarized in the paper's own statistics:

```text
   artifact                          code base            Isabelle formalization
   --------------------------------  ------------------   ----------------------
   Abstract spec                     - (hand-written)     4,900 LOC HOL
   Executable spec                   5,700 LOC Haskell    13,000 LOC (translated)
   C implementation                  8,700 LOC C          15,000 LOC (C parser)
   
   Invariants carried                ~75 (spec level)     ~80 (exec spec level)
   Refinement proofs                 -                    110,000 + 55,000 LOP
   Total proof base                  -                    200,000 lines of script
                                                          (incl. frameworks)
```

The second half of the chain looks like a category error until you see the trick: C has no official mathematical semantics, so the seL4 team wrote a C parser *inside Isabelle/HOL* that reads the actual kernel C code and gives it meaning in higher-order logic. The refinement proof then relates the executable spec to this formalized C - there is no manual transcription step in which a proof-friendly model could drift from the shipped code. The price is a restricted C dialect: the kernel avoids the subtler corners of ISO C, and the parser defines the semantics the proof assumes the C compiler implements. The 2013 binary-correctness work (below) is what discharges that last assumption.

Today's chain, as drawn in the seL4 white paper, adds the compiler and the silicon:

```text
   +------------------+  refinement   +----------------+  refinement  +-----------+
   | Abstract model   | ------------> | Formalized C   | -----------> | C source  |
   | (Isabelle/HOL)   |               | ("C spec")     |              | (8.7k LOC)|
   +------------------+               +----------------+              +-----------+
        |        |                             |                            |
        |        | security proofs             |                            | gcc
        |        v                             v                            v
        |   +------------------+   +------------------------------+   +-----------+
        |   | Integrity /      |   | Translation validation       |   | ARM /     |
        |   | Confidentiality /|   | (SMT equivalence check       |   | RISC-V /  |
        |   | Availability     |   |  of C vs binary, PLDI 2013)  |   | x86 bin   |
        |   +------------------+   +------------------------------+   +-----------+
        |                                     |                            |
        |                                     v                            |
        |                    +----------------------------------+          |
        +------------------->| Binary machine code (L3 ISA      |<---------+
             spec-level      | models, HOL4 disassembler,       |
             properties      | graph rewriting + SMT)           |
                             +----------------------------------+
```

Two proof infrastructures deserve names because they are reused far beyond seL4: the **L3/IsaV ARM and RISC-V ISA models** (Fox & Myreen's Arm model, and an L3 RISC-V model) formalize what the binary means, and **[SMT-based translation validation](https://sel4.systems/Research/pdfs/translation-validation-verified-os-kernel.pdf)** (Sewell, Myreen & Klein, PLDI 2013) proves the compiled binary equivalent to the formalized C by disassembling it into a control-flow graph and discharging equivalence obligations to SMT solvers. This is the same intellectual move as the compiler-community's translation validators ([Translation Validation & Bootstrapping](../compilers/translation-validation-bootstrapping.md)) applied at kernel scale: instead of proving the compiler correct, prove *this binary* equivalent to *this C*.

## The effort arithmetic

The SOSP 2009 paper itemized its costs, and the numbers remain the best public dataset on what kernel verification actually costs:

| Item | Cost | Notes |
|------|------|-------|
| Kernel development (C, incl. Haskell) | 2.2 person-years | SLOCCount "embedded" profile estimate for the same code: 4 py |
| Abstract spec | 4 person-months | Hand-written in Isabelle/HOL |
| Executable spec translator | 3 person-months | One-off; the Haskell code itself cost ~2 py across phases |
| Proof total | ~20 person-years | Of which ~9 py in frameworks, tools, automation and libraries |
| seL4-specific proof | 11 person-years | The remainder was reusable infrastructure |
| First refinement (spec -> exec. spec) | 8 py | vs under 3 py for the second step - a ~3:1 ratio |

Two conclusions the authors drew from this table are still load-bearing. The refinement split shows *layering pays*: once the first, hardest abstraction gap was bridged, the second step - which localized memory-object reasoning - cost a third as much. And the framework share shows that most of the money goes into machinery (memory models, monads, automation) that survives the kernel: the team's estimate for re-verifying a similar kernel from scratch was 6 py. Set against industry rules-of-thumb of roughly $10k/LOC for Common Criteria EAL6-style evaluation - about $87M for seL4's size - the proof was cheap assurance.

## Why the capability design made this feasible

seL4 is not a conventional kernel that someone verified afterwards; its architecture was chosen so that the invariants a proof needs could actually be maintained by human engineers. The design decisions that matter for the proof:

| Design rule | Verification payoff |
|-------------|---------------------|
| Capability-based access control | All authority flows through unforgeable kernel-indexed capability slots; rights are checked in one small, provable code path, and there are no user-supplied pointers to dereference inside the kernel |
| No dynamic memory allocation after boot | Kernel memory is pre-partitioned and retyped explicitly via capabilities; absence of "out of memory mid-operation" states removes a whole family of error paths from the invariant set |
| Global invariants instead of history bounds | The kernel maintains invariants continuously (no "temporary violation" windows during syscall interleaving), so the ~75-80 invariants the proof carries are always true at kernel entry points |
| Small kernel, no threads inside the kernel | The refinement model stays single-threaded and small; concurrency is pushed to the scheduling boundary where it is cheap to formalize |

The capability system is also what makes the *security* theorems meaningful: integrity, confidentiality, and availability are statements about what configurations of capabilities permit, so a provably unforgeable capability mechanism turns them into checkable properties of the spec. For the microkernel-vs-monolithic trade-off framing and seL4's IPC performance numbers, see [Kernel Architectures](../os/advanced/kernel-architectures.md); for the proof-assistant landscape (Isabelle/HOL vs Coq vs Lean), see [Coq & Lean](./coq-lean.md).

## What seL4 does not guarantee

The seL4 documentation is unusually blunt about the proof's boundary, and that list is as instructive as the theorem itself ([assumptions page](https://sel4.systems/Verification/assumptions.html), [FAQ](https://sel4.systems/About/FAQ.html), [white paper](https://sel4.systems/About/seL4-whitepaper.pdf)):

```text
   COVERED by proofs                        OUTSIDE the proof (assumptions)
   -------------------------                -------------------------------
   C implementation behavior                ~600 lines of assembler
   (refinement of abstract spec)            (kernel entry/exit, HW access)

   Integrity, confidentiality,              ~1,200 lines of boot code
   availability of the spec                 (loaded-and-initialized is assumed)

   Binary <-> C equivalence                 Hardware correctness
   (on configurations that                  (no tampering, no Trojans,
    support it)                              operating conditions met)

   Absence of buffer overflows,             DMA devices misbehaving
   null derefs, UB, memory leaks            (must be absent or verified too)
```

- **Timing is not (yet) inside the confidentiality proof.** The FAQ states it directly: the confidentiality proof "makes no guarantees about the absence of covert timing channels". The proofs rule out *storage* channels; Spectre-style timing leakage is a separate problem. The ecosystem's answer is architectural: the Time Protection line of work (EuroSys 2019, best paper) adds clock, enforcement, and domains as OS mechanisms, and the MCS (mixed-criticality) scheduler with scheduling-context capabilities (EuroSys 2018) makes time a first-class kernel resource so that timeliness properties have something to attach to.
- **WCET was measured, not proved, on specified platforms.** Worst-case execution time analysis for seL4 has been done for ARM targets - including formally derived loop bounds and infeasible-path elimination - but WCET results attach to specific binaries, specific hardware timing models, and specific tool assumptions, not to the functional-correctness theorem. What the correctness proof *does* give a WCET tool for free is a binary with no hidden control-flow surprises: the code is free of UB, and loop bounds can be discharged as proved facts rather than reviewer guesses.
- **The performance story is orthogonal to the proof.** The fact sheet's claim that seL4 is 2 to 10 times faster than comparable systems comes from benchmarking, not from the theorem; the proof says nothing about speed. The two claims are independent guarantees that happen to share a codebase.
- **Specification intent.** A proof says the code matches the spec, not that the spec says what you meant. The security theorems shrink this gap (a noninterference-style statement is much easier to eyeball than 8,700 lines of C) but cannot eliminate it; seL4's own materials list this as one of the three standing assumptions, alongside hardware and the Isabelle LCF kernel (a few 10 kSLOC core that checks every proof).
- **Per-configuration status.** Not every property holds on every architecture; the project publishes exactly which configurations carry which proofs. As of August 2026 the headline status is: functional correctness and integrity long established, and the [confidentiality proof on AArch64 completed](https://sel4.systems/news/2026.html), closing the security-isolation story on 64-bit Arm.

## The ecosystem, briefly

The kernel, proofs, and tooling are developed in the open under the seL4 Foundation (a Linux Foundation project), with commits gated on proof maintenance - the fact sheet's "no code change without proof validation" discipline is the reason a 2009 result still describes the 2026 kernel. The proof base itself is inspectable: the [`l4v` Isabelle session on GitHub](https://github.com/seL4/l4v) contains the abstract spec, the refinement proofs, and the security proofs, and can be re-checked by anyone with a sufficiently patient machine.

Around the kernel:

- **seL4 Microkit** - a thin abstraction layer that [hides capabilities and system calls](https://github.com/seL4/microkit) behind static protection domains with three entry points (`init`, `notified`, `protected`); all components and their authorized communication channels are fixed at configuration time. Aimed at embedded teams who want verified isolation without becoming capability experts; the static architecture is also what keeps its systems inside the proof-friendly configuration space.
- **CAmkES** - the older component framework for composing seL4 systems out of interface-defined components, used where dynamic composition outweighs Microkit's rigidity.
- **Proofs and certification positioning** - the project's documentation argues the proof stack exceeds what Common Criteria EAL7, ISO 26262 ASIL-D, or DO-178C Level A require for *development* assurance; the proofs do not replace those schemes, but they shift the evaluation burden onto the explicit assumption list ([fact sheet](https://sel4.systems/About/fact-sheet.html), [certification page](https://sel4.systems/Verification/certification.html)).

The roadmap page tracks which proofs are complete or pending per architecture and feature; the August 2026 AArch64 confidentiality milestone closed the last gap in the headline security story for 64-bit Arm.

## Why verification at this scale became feasible

Pulling the threads together, seL4's feasibility argument has five components, none of which is "more proof engineers":

1. **A small target.** Eight to ten thousand lines of C is not a marketing number; it is the load-bearing constraint. Every architectural decision was tested against "can this stay in the verified set?"
2. **Refinement as an expense localizer.** Two-level refinement meant the brutal part (spec to executable spec) was paid once, and the machine-checked C linkage then anchored everything else.
3. **Design for invariants.** Capabilities, no post-boot allocation, and no user pointers mean the invariant burden is finite and stable - the difference between a proof that converges and one that thrashes.
4. **Proof engineering as a discipline.** Treat proof scripts as code: version them, re-run them per commit, and invest in reusable frameworks. That is why the proof base grew from 200k lines to 1.3M without decaying.
5. **Attacking the remaining gaps with the right tool.** Binary-level trust went to translation validation (SMT), not more refinement; timing went to new OS abstractions (MCS, time protection), not to heroic kernel proofs. Matching proof technology to the sub-problem is the transferable lesson.

## References

- G. Klein et al., "seL4: Formal Verification of an OS Kernel", SOSP 2009 (official copy; Table 1 and effort numbers quoted above) - <https://sel4.systems/Research/pdfs/sel4-formal-verification-os-kernel.pdf>
- seL4 Proofs - official statement of the proof stack, per-property status, and proof implications - <https://sel4.systems/Verification/proofs.html>
- seL4 Fact Sheet (1.3M lines of proofs; properties; certification positioning) - <https://sel4.systems/About/fact-sheet.html>
- seL4 White Paper (proof chain, translation validation, assumptions, MCS/Microkit) - <https://sel4.systems/About/seL4-whitepaper.pdf>
- seL4 FAQ - the zero-bugs and covert-timing-channel statements quoted above - <https://sel4.systems/About/FAQ.html>
