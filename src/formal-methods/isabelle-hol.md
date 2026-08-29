# Isabelle/HOL: The LCF-Style Kernel Architecture

Isabelle is a **generic proof assistant**: a small logical framework (Isabelle/Pure) on which object logics such as higher-order logic (Isabelle/HOL), ZF set theory, and constructive type theory are layered. Developed at the University of Cambridge and TU Munich since 1986, it is the system behind the seL4 microkernel proof, the CakeML compiler, and the Archive of Formal Proofs. Its most interview-relevant idea is architectural, not logical: like its ancestor Edinburgh LCF, Isabelle makes **theorems an abstract type** whose values can only be constructed by a small trusted kernel. Everything else -- tactics, automation, external ATP bridges -- is untrusted elaboration feeding that kernel.

This page dissects that architecture: the Pure/HOL split, the LCF kernel trick, structured Isar proofs, Sledgehammer's reconstruct-not-trust automation, HOL modeling style, the flagship verified projects, and how Isabelle's curation model differs from Coq's and Lean's. For the CIC-based provers, see [Coq and Lean](./coq-lean.md); for the proof-terms-as-types view, see [Curry-Howard](../cs-theory/curry-howard.md).

## Pure and HOL: a framework, not just a logic

Most proof assistants bake one logic into their kernel. Isabelle instead implements **Isabelle/Pure**: a minimal intuitionistic natural-deduction framework with a tiny set of primitive rules (equivalence, implication, conjunction, universal quantification at the meta-level). Object logics are then *encoded* in it:

| Layer | What it is | What it provides |
|------|-----------|-----------------|
| Isabelle/Pure | Logical framework kernel | Primitive meta-level inference rules; `thm` abstract type |
| Isabelle/HOL | Object logic (simple type theory + classical choice) | `ALL`, `EX`, datatypes, inductive definitions, `simp` set |
| Isabelle/Isar | Proof language layer | Structured human-readable proofs over either logic |
| Isabelle/ML | Programming layer | User tactics and automation, all kernel-gated |

The payoff of the framework design: automation is written once against Pure and works for every object logic, and the soundness argument never changes -- a theorem is trusted iff the kernel produced it. HOL is by far the dominant instance, so "Isabelle" and "Isabelle/HOL" are used almost interchangeably. Paulson's foundational paper ("The foundation of a generic theorem prover", 1989) formalizes exactly this design.

## The LCF trick: theorems are an abstract type

Edinburgh LCF (Gordon, Milner, Wadsworth, late 1970s) introduced a trick now used across the field: implement the prover in ML and declare the type of theorems `thm` **abstract** in the module signature, hiding its constructor. The only way to obtain a `thm` is to call the kernel's primitive inference rules. Consequences:

- A buggy tactic can waste your time but cannot break soundness: whatever it does, its output went through kernel rules.
- The trusted computing base (TCB) shrinks to the kernel plus the ML runtime -- a few thousand lines, reviewable, versus hundreds of thousands of lines of tactic code.
- Odd tactics can still exist (even "prove anything by axiom"), but their results must carry the hypotheses and structure the kernel gives them; a rule application that does not fit is rejected.

Milner argued for this machine-checkable discipline in his 1984 lecture "The use of machines to assist in rigorous proof". Isabelle kept the design: its `thm` type in ML is abstract, and Isar proofs, tactics, and elaborators all reduce to primitive inferences that the kernel checks **at the moment they happen**. Unlike Coq/Lean, Isabelle historically does not re-check a stored explicit proof term -- the guarantee is that no object of type `thm` was ever produced except by kernel primitives. The trade-off is a smaller re-verification artifact but faster incremental checking of enormous developments like seL4.

```text
        .thy theory files          user interaction (proof explorer)
              |                              |
              v                              v
   +---------------------+        +---------------------+
   | Isar interpreter    |        | tactics / simp /    |
   | (structured proofs) |        | auto, Sledgehammer  |
   +---------------------+        +---------------------+
              |                              |   external ATPs (E, Vampire)
              |                              |   and SMT (Z3, CVC) are
              |                              |   ADVISORY: their output is
              |                              |   re-proven as metis/smt
              |                              |   proofs before reaching
              |                              |   the kernel
              v                              v
        +--------------------------------------------------+
        |          Isabelle/Pure kernel  (trusted)         |
        |   thm : abstract type -- no public constructor   |
        |   primitive inferences: assume / imply / conj /  |
        |   forall intros + elims (meta-level)             |
        +--------------------------------------------------+
                               |
                               v
        +--------------------------------------------------+
        |  Isabelle/HOL object logic: HOL axioms + rules,  |
        |  datatypes, inductives, simpset, type classes    |
        +--------------------------------------------------+
```

## A toy kernel you can run

The model below is the LCF discipline reduced to ~100 lines: a `Thm` class with a private constructor, and module-level kernel rules (`assume`, `mp`, `disch`, conjunction intro/elim) as the *only* callers of the hidden factory. Then natural-deduction derivations are built on top, and every forgery path is rejected.

```python
# Toy LCF-style kernel: a Theorem is an abstract value that can ONLY be
# created by the kernel's inference rules. Forgery is rejected at run time.
# (In OCaml/ML this is an abstract type in a module signature, so forgery
# is type-impossible; Python's privacy here is a runtime stand-in.)
class KernelError(Exception):
    pass
class Thm:
    """G |- A: a set of hypotheses and a conclusion formula."""
    __slots__ = ("_hyps", "_concl")
    def __init_subclass__(cls):
        raise KernelError("forgery: subclassing kernel type 'Thm' is forbidden")
    def __init__(self, *args, **kwargs):
        raise KernelError("forgery: Thm constructor is private; use kernel rules")
    @classmethod
    def _mk(cls, hyps, concl):
        th = object.__new__(cls)      # only the kernel may call this
        th._hyps = frozenset(hyps)
        th._concl = concl
        return th
    @property
    def hyps(self):
        return self._hyps             # immutable frozenset
    @property
    def concl(self):
        return self._concl
    def __str__(self):
        ctx = ", ".join(sorted(show(h) for h in self._hyps))
        return (ctx + " " if ctx else "") + "|- " + show(self._concl)
# Propositional formulas as tagged tuples: ('var','P'), ('->',A,B), ('/\\',A,B)
def var(n):
    return ("var", n)
def imp(a, b):
    return ("->", a, b)
def conj(a, b):
    return ("/\\", a, b)
def show(f):
    if f[0] == "var":
        return f[1]
    return "(" + show(f[1]) + " " + f[0] + " " + show(f[2]) + ")"
# --- the kernel: the only functions in the world that call Thm._mk ---------
def assume(a):
    return Thm._mk({a}, a)                      # A |- A
def mp(th_imp, th_ant):                         # |- P->Q and |- P give |- Q
    A, B = th_imp.concl[1], th_imp.concl[2]
    if th_imp.concl[0] != "->" or th_ant.concl != A:
        raise KernelError("mp: mismatch (%s vs %s)"
                          % (show(th_imp.concl), show(th_ant.concl)))
    return Thm._mk(th_imp.hyps | th_ant.hyps, B)
def disch(a, th):                               # G |- B  gives  G-{A} |- A->B
    return Thm._mk(th.hyps - {a}, imp(a, th.concl))
def conj_intro(th1, th2):
    return Thm._mk(th1.hyps | th2.hyps, conj(th1.concl, th2.concl))
def conj_elim_left(th):
    if th.concl[0] != "/\\":
        raise KernelError("conj_elim: not a conjunction")
    return Thm._mk(th.hyps, th.concl[1])
def conj_elim_right(th):
    if th.concl[0] != "/\\":
        raise KernelError("conj_elim: not a conjunction")
    return Thm._mk(th.hyps, th.concl[2])
# --- natural deduction on top of the kernel --------------------------------
P, Q, R = var("P"), var("Q"), var("R")
# intro/elim derivation of  |- P -> ((P -> Q) -> Q)
hP = assume(P)
hPQ = assume(imp(P, Q))
hQ = mp(hPQ, hP)                 # P, P->Q |- Q
step1 = disch(imp(P, Q), hQ)     # P |- (P->Q) -> Q
step2 = disch(P, step1)          # |- P -> ((P->Q) -> Q)
print("derived :", step2)
# weakening  |- P -> (Q -> P)
print("weaken  :", disch(P, disch(Q, assume(P))))
# conjunction symmetry  P, Q |- Q /\\ P
cs = conj_intro(conj_elim_right(assume(conj(P, Q))),
                conj_elim_left(assume(conj(P, Q))))
print("conj-sym:", cs)
# --- every forgery path is rejected ---------------------------------------
for name, attempt in [
    ("direct Thm(..)", lambda: Thm({P}, Q)),
    ("mp with wrong antecedent", lambda: mp(assume(imp(P, Q)), assume(R))),
    ("subclass Thm", lambda: type("EvilThm", (Thm,), {})),
]:
    try:
        attempt()
        print(name, "-> UNCAUGHT (kernel broken)")
    except KernelError as e:
        print("%-25s rejected: %s" % (name, e))
```

Output (deterministic):

```text
derived : |- (P -> ((P -> Q) -> Q))
weaken  : |- (P -> (Q -> P))
conj-sym: (P /\ Q) |- (Q /\ P)
direct Thm(..)            rejected: forgery: Thm constructor is private; use kernel rules
mp with wrong antecedent  rejected: mp: mismatch ((P -> Q) vs R)
subclass Thm              rejected: forgery: subclassing kernel type 'Thm' is forbidden
```

One honesty note: in Python, privacy is a runtime convention (a determined caller could reach `Thm._mk`). In OCaml, the original LCF setting, an abstract type in a module signature makes forgery *type-impossible* -- the compiler itself enforces the kernel boundary. That is the whole idea: the language's type system, not programmer discipline, carries soundness.

## Isar: proofs as structured documents

Early LCF-style provers presented proofs as tactic scripts. Isabelle's **Isar** ("Intelligible semi-automated reasoning", Wenzel, 1999) adds a structured layer: named cases, explicit goal statements, and a `proof ... qed` shape that reads like a human mathematical text and fails loudly when an assumption is silently dropped:

```isabelle
lemma "rev (rev xs) = xs"
  proof (induct xs)
    case Nil
    then show ?case by simp
  next
    case (Cons a xs)
    then show ?case by simp
  qed
```

Industrial developments mix both styles: apply-scripts and automation (`simp`, `auto`, Sledgehammer) do the heavy lifting, Isar is used where proof structure, maintenance, and review matter. The seL4 development leans heavily on automation with structured skeletons, because the proof is re-run continuously as the kernel evolves.

## Sledgehammer: automated discovery, LCF-gated delivery

**Sledgehammer** is Isabelle's bridge to external automated provers. Its pipeline, per the "Hammering towards QED" line of work (Blanchette, Bulwahn, Paulson):

1. **Relevance filter** picks lemmas plausibly needed for the goal (statistical/learning-based ranking -- the MaSh line of work).
2. The HOL goal is **translated** to first-order logic and dispatched in parallel to resolution provers (E, Vampire, historically SPASS) and SMT solvers (Z3, CVC), plus the internal first-order prover `metis`.
3. A prover's refutation is **minimized** to the used lemmas, then **reconstructed**: the system generates a one-line Isar proof (typically `by metis ...` or `by (smt ...)`) using only Isabelle's own tactics.
4. The kernel checks the reconstruction. The external solver is *advisory*: a wrong SAT/SMT certificate surfaces as a reconstruction failure, never as a false theorem.

This is the interview-ready version of the trust argument: automation can be as fast and as buggy as its authors like, because acceptance into the theorem base is kernel-gated. See [SAT and SMT Solvers](./sat-smt-solvers.md) for what those backend tools do internally.

## Modeling in higher-order logic

Isabelle/HOL is simple type theory extended with classical logic, Hilbert choice, datatypes, (co)inductive definitions, recursive function definitions, and Haskell-style type classes. Its total-function discipline (no divergence in logic) matches systems verification: properties are proved about specifications and implementations as total relations/functions, with models typically built as inductive sets or transition systems. A characteristic HOL session:

```isabelle
datatype tree = Leaf | Node tree tree

fun mirror :: "tree => tree" where
  "mirror Leaf = Leaf"
| "mirror (Node l r) = Node (mirror r) (mirror l)"

lemma mirror_mirror: "mirror (mirror t) = t"
  by (induction t) auto
```

The `datatype`/`fun` commands themselves elaborate to inductive definitions and induction principles -- again, generated theorems enter the kernel through the same primitive inferences. This command layer is what makes HOL developments compact compared with hand-written inference derivations.

## Verified artifacts built in Isabelle/HOL

**seL4.** The SOSP 2009 paper (Klein et al.) reported the first machine-checked functional correctness proof of a complete, general-purpose OS kernel: 8,700 lines of C plus 600 lines of assembly pinned to an abstract specification by about 200,000 lines of Isabelle/HOL proof script, at roughly 20 person-years of effort. Note what the line counts mean: the 200k measures *machine-checked proof script*, not the kernel, and it is script whose every inference was kernel-checked. "Functional correctness" means the implementation strictly follows the abstract specification -- never crash, never perform an unsafe operation -- under explicit assumptions that the compiler, assembly, and hardware behave as specified (the follow-up TOCS 2014 paper "Comprehensive formal verification of an OS microkernel" covers the full refinement stack, binary translation validation, and the security proofs). The proof base is maintained continuously against the evolving kernel and now stands at 1.3 million lines of proofs with zero violated verified properties since 2009, per the seL4 fact sheet. A full treatment lives on the dedicated [seL4 page](./sel4-verification.md).

| Artifact | What is verified | Scale | Primary source |
|---------|-----------------|-------|----------------|
| seL4 | Functional correctness of C microkernel; integrity, confidentiality; binary-level TV | 8.7K LOC C vs ~200K proof lines (SOSP'09), 1.3M proof lines maintained | SOSP'09 + fact sheet |
| CakeML | ML compiler + runtime down to machine code, with verified bootstrapping and REPL | Compiler, runtime, and bootstrap all formalized in HOL | POPL'14, cakeml.org |
| Archive of Formal Proofs | Peer-reviewed theories: crypto, semantics, logics, algorithms | 1,000+ entries, journal-style reviewing | isa-afp.org |
| Sail (emits Isabelle) | Formal ISA specifications checked/emitted as Isabelle/HOL theories | ARM, RISC-V | see [Verified Systems](./verified-systems.md) |

**CakeML** deserves its place here because it exercises the full architecture: the compiler, its runtime, and even its bootstrap process are HOL theories, so the executable compiler's output is correct by construction relative to its semantics. This style -- verified compiler + verified runtime + verified bootstrap -- is Isabelle/HOL's signature contribution alongside seL4.

## Curation: AFP versus mathlib-style monorepos

Isabelle's ecosystem is **journal-curated**: the Archive of Formal Proofs accepts entries through an editorial board with per-entry review and cleanup, more like a journal than a community monorepo. Coq and Lean ecosystems instead concentrate mass in community libraries (mathlib for Lean), which grow faster but rely on CI and review norms rather than an editorial gate. Isabelle additionally ships a large standard HOL library and Sledgehammer out of the box, so *breadth* comes with the tool; *depth* (novel formalizations) lives in AFP entries. The practical consequences:

- For systems verification (kernels, compilers, protocols), Isabelle/HOL's automation and total-function style have an unmatched track record.
- For working mathematicians, Lean 4 + mathlib's shared library is currently the larger attractor -- the [Coq/Lean page](./coq-lean.md) covers that side.
- For interviews, the durable answer is: Isabelle bets on kernel trust + curated archive; the CIC provers bet on dependent types + community libraries. Both derive soundness from a small checked core.

## How this shows up in interviews

- **"Why can't a buggy tactic break soundness?"** Because `thm` is abstract; the tactic's every step is a kernel primitive application. Worst case is a wrong proof *attempt* rejected, or an unprovable claim that never produces a theorem.
- **"What does '200,000 lines of proof' actually mean?"** Machine-checked Isabelle/HOL script (tactics, Isar proofs, definitions) whose primitive inferences were all kernel-checked -- not 200k lines of C, and not prose.
- **"Where does the seL4 trust chain bottom out?"** Kernel, ML runtime, and the assumptions that compiler/assembly/hardware behave as modeled -- each an explicitly stated, actively researched side condition.
- **"Isabelle vs Coq vs Lean?"** Framework vs baked-in logic; simple types + classical logic vs dependent types; AFP curation vs mathlib-style monorepo; Sledgehammer's reconstruct-then-check vs proof-term re-checking.
- **"What is Isar for?"** Structured, reviewable, maintainable proofs -- the difference between proof-as-code and proof-as-document.

## References

1. Isabelle project site (TU Munich; current release line Isabelle2025) -- <https://isabelle.in.tum.de/>
2. Nipkow, Paulson, Wenzel, *Isabelle/HOL: A Proof Assistant for Higher-Order Logic*, LNCS 2283, Springer -- <https://link.springer.com/book/10.1007/3-540-45949-9>
3. Paulson, "The foundation of a generic theorem prover", *Journal of Automated Reasoning* 5, 1989 -- <https://doi.org/10.1007/BF00264240>
4. Milner, "The use of machines to assist in rigorous proof", *Phil. Trans. R. Soc. A* 312, 1984 -- <https://doi.org/10.1098/rsta.1984.0067>
5. Klein et al., "seL4: Formal Verification of an OS Kernel", SOSP 2009 -- <https://doi.org/10.1145/1629575.1629596>
6. Klein et al., "Comprehensive formal verification of an OS microkernel", *ACM TOCS* 32(1), 2014 -- <https://doi.org/10.1145/2560537>
7. seL4 fact sheet (proof size, verified properties, maintenance) -- <https://sel4.systems/About/fact-sheet.html>
8. Blanchette, Bulwahn, Paulson, "Hammering towards QED", *Journal of Automated Reasoning* 57, 2016 -- <https://link.springer.com/article/10.1007/s10817-015-9348-x>
9. Tan, Myreen, Kumar, Fox, Owens, Norrish, "CakeML: A Verified Implementation of ML", POPL 2014 -- <https://dl.acm.org/doi/10.1145/2535838.2535841>; project: <https://cakeml.org/>
10. Archive of Formal Proofs -- <https://www.isa-afp.org/>
