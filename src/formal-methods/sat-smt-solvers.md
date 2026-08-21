# SAT and SMT Solvers

## Overview

Modern formal methods rest on a hidden workhorse: the **SAT solver**, which decides satisfiability of propositional logic formulas. SAT is the canonical NP-complete problem (Cook 1971), so in the worst case every known algorithm is exponential. But over the last 25 years, *practical* SAT solvers — built around the **CDCL** (Conflict-Driven Clause Learning) algorithm — have grown fast enough to handle industrial instances with millions of variables and tens of millions of clauses. The most consequential impact: a SAT solver can solve problems nobody knows how to solve any other way, because they are "exponential in theory, polynomial in practice" for the instances that actually show up.

**SMT** (Satisfiability Modulo Theories) lifts this capacity above pure propositional logic: it decides satisfiability of formulas in first-order logic over a chosen background theory — linear integer arithmetic, bit vectors, arrays, uninterpreted functions with equality. **DPLL(T)** is the architecture that lets SMT solvers reuse the CDCL machinery for the Boolean structure and delegate theory-specific reasoning to a separate, swappable solver. Z3 (Microsoft Research), CVC5 (NYU/Iowa/Stanford), and Boolector (Johannes Kepler Universität Linz) are the production-grade open-source SMT solvers, and they are the engine behind program verifiers (Dafny, Frama-C/WP, KLEE), bounded model checkers (CBMC, ESBMC), symbolic execution engines (SAGE, KLEE), and protocol analyzers.

This page covers DPLL (the baseline), CDCL (what made SAT fast), the SMT theories and DPLL(T) architecture, the major solvers, and production use cases.

## The DPLL Baseline

The **Davis-Putnam-Logemann-Loveland** algorithm (DPLL, 1962) is the foundation of all modern CDCL solvers. The input is a formula in **conjunctive normal form** (CNF) — a conjunction of clauses, where each clause is a disjunction of literals, and a literal is a Boolean variable or its negation:

```
φ = (x1 ∨ ¬x2 ∨ x3) ∧ (¬x1 ∨ x4) ∧ (¬x3 ∨ ¬x4) ∧ ...
```

DPLL performs a backtracking depth-first search:

```
function DPLL(φ):
    while there is a unit clause (l) in φ:
        φ := simplify(φ, l)            # propagate: set l=true, remove clauses containing l,
                                       #                  drop ¬l from clauses containing it
    if φ is empty (no clauses):        return SAT
    if φ contains an empty clause:     return UNSAT
    pick a literal l from φ
    if DPLL(φ ∧ (l)):                  return SAT      # try l = true
    else:                return DPLL(φ ∧ (¬l))          # backtrack, try l = false
```

The two workhorses are (1) **unit propagation** (the while loop), which propagates forced assignments cheaply; (2) **pure-literal elimination** (deprecated in modern solvers, but historically important) — a variable that appears only with one polarity can be set to that polarity.

The weakness of DPLL: when it hits a conflict, it backtracks one level and tries the opposite literal. It *forgets* what it learned. A formula with 100 variables and many symmetries can cause DPLL to explore the same failed sub-tree millions of times under different prefixes. **CDCL fixes this**.

## CDCL: Conflict-Driven Clause Learning

CDCL (Marques-Silva and Sakallah 1996; Zhang et al., zChaff, 2001) augments DPLL with three mechanisms that make modern SAT solvers practical:

1. **Implication graph and 1-UIP learning** — when a conflict occurs, CDCL analyzes the implication graph (the DAG of variable assignments and their causes) and learns a **conflict clause** that captures the reason for the failure. This clause is added to the formula permanently, ensuring the solver never re-explores the same failed subspace. The conflict clause is derived by resolution starting from the conflicting clause, cutting at the **first unique implication point** (1-UIP) — the unique dominator reachable from the conflict through the implication graph restricted to the current decision level.

2. **Non-chronological backtracking** — after learning a conflict clause, CDCL doesn't just undo one decision; it jumps back to the second-highest decision level mentioned in the learned clause. This skips large portions of the search space.

3. **VSIDS / LRB / activity-based heuristics** — variable selection is data-driven. The classic **VSIDS** (Variable State-Independent Decaying Sum) keeps a per-variable score that is bumped when the variable appears in a conflict, decays over time so recent conflicts dominate. Modern solvers like Kissat use **LRB** (Learning Rate Based branching) which uses multi-armed bandit ideas to pick variables that have historically led to fast learning.

```
A simplified CDCL loop:

state: trail (assignment stack), levels (decision level per variable),
       reason (clause that caused each non-decision assignment)
loop:
    propagate()                  # unit propagation; if conflict, return clause
    if no conflict and all vars assigned: return SAT
    if conflict and decision level = 0: return UNSAT
    if conflict:
        learnt := analyze_conflict()    # 1-UIP cut + resolution
        add learnt to clause database
        backtrack_level := second_highest_level(learnt)
        unwind trail to backtrack_level
    else:
        pick decision variable x with highest VSIDS score
        assign x := true (or false by polarity heuristic)
        decision_level++
```

A few CDCL engineering details that matter for production performance:

- **Clause minimization** reduces learnt clauses by self-subsumption before adding them (a 1-2× speedup).
- **Restart strategies** (Luby, geometric) periodically reset the trail to escape deep unproductive branches; the *learnt clauses* survive restarts, so progress is retained.
- **Phase saving** remembers each variable's last value across backtracks to bias future decisions (gives ~30% speedup on industrial instances).
- **Watched literals** let unit propagation be O(1) per clause-event rather than O(clause-length) — without this, propagation dominates runtime.
- **Glucose / Maple_LCM / Kissat** scoring measures "clause usefulness" and periodically deletes learnt clauses with low scores to bound memory.

A modern solver like Kissat (Biere, 2020+) decides a 5-million-variable, 20-million-clause industrial SAT instance in seconds to minutes. This is what makes bounded model checking of C programs, equivalence checking of hardware, and AI-planning-as-SAT practical.

## From SAT to SMT: Theories and DPLL(T)

Pure SAT solvers work on Boolean abstractions — `p`, `q`, `r` — but real verification problems involve arithmetic, arrays, and uninterpreted functions. **SMT** (Satisfiability Modulo Theories) generalizes: it decides formulas in first-order logic with equality over a background theory `T`. An SMT solver answers SAT (with a model), UNSAT (with a proof), or UNKNOWN (when its decision procedure is incomplete for the fragment).

The major theories standardized by the **SMT-LIB** initiative:

| Theory | Fragment | Decidable? | Notes |
|--------|----------|------------|-------|
| **QF_UF** (uninterpreted functions with equality) | ground first-order | yes (congruence closure) | the workhorse of program verification |
| **QF_LIA** (linear integer arithmetic) | Presburger arithmetic over ℤ | yes (Cooper's / Omega) | excellent for loop invariants |
| **QF_LRA** (linear real arithmetic) | linear arithmetic over ℝ | yes (Simplex) | used in continuous-control proofs |
| **QF_NIA** (nonlinear integer arithmetic) | polynomials over ℤ | no (Hilbert 10) | incomplete; uses SMT + CAD |
| **QF_BV** (bit vectors) | fixed-width machine integers | yes (bit-blast to SAT) | underpins hardware verification |
| **QF_ABV** (arrays + bit vectors) | Selinger-style array theory | yes | reasoning about memory |
| **QF_FP** (floating point) | IEEE 754 | decidable but expensive | bit-blasted with structural constraints |

The "QF" prefix means "quantifier-free." Quantifiers are handled by separate instantiation heuristics (E-matching, MBQI) and are in general undecidable.

### The DPLL(T) Architecture

The breakthrough that made SMT practical was the **DPLL(T)** architecture (Nieuwenhuis, Oliveras, Tinelli 2006): combine a CDCL-based SAT solver with a *theory solver* `T-solver` for the chosen theory, communicating through a clean interface.

```
+-----------------------------------+
|  SAT solver (CDCL)                |   <-- Boolean reasoning
|  - decides boolean abstraction   |
|  - calls T-solver at every node   |
+---------------+-------------------+
                |  T-propose (assignment to atoms)
                v
+-----------------------------------+
|  T-solver for theory T            |   <-- theory reasoning
|  - checks T-consistency of model  |
|  - returns conflict clause (T-lemma)
|  - propagates implied literals    |
+-----------------------------------+
```

The SAT solver maintains a Boolean abstraction of the formula: each theory atom `a = b`, `x < y`, `select(arr, i) = v` is replaced by a fresh propositional variable. CDCL explores assignments; at each node it queries the T-solver with the current assignment (translated back to theory literals). The T-solver returns one of:

- **Consistent** — and possibly some implied literals (theory propagation, e.g., `a = b ∧ b = c ⇒ a = c`);
- **Inconsistent** — with a T-unsat core (a minimal subset of the literals the T-solver can prove contradictory). CDCL learns the corresponding Boolean clause and backtracks.

The key engineering insight: the **theory solver is incremental and backtrackable**. It maintains state across SAT-solver decisions and rolls back via a trail stack, never re-deriving facts it already knew. This is what lets DPLL(T) handle formulas with 10^5+ theory atoms.

For **QF_BV**, the dominant approach is **bit-blasting**: each bit-vector operation (add, mul, shift) is compiled to a Boolean circuit, and the whole formula is sent to a SAT solver. This is what Boolector excels at. For **QF_LIA**, the dominant approach uses Simplex-style branch-and-bound plus cutting planes (CVC5) or the Omega test (older MathSAT). For **QF_UF**, the **congruence closure** algorithm over an E-graph (Nelson-Oppen union-find with term labels) is the core.

### Combining theories: Nelson-Oppen

Many practical formulas mix theories — e.g., `(a + b) = c ∧ select(arr, a) = v` involves linear arithmetic and arrays. The **Nelson-Oppen** combination method (1979) lets you combine two **stably-infinite, signature-disjoint, decidable** theories `T1` and `T2` into a decision procedure for `T1 ∪ T2`. (Stably infinite means: any satisfiable formula has a model of infinite cardinality. Most useful theories — arithmetic, uninterpreted functions, arrays — are.) Modern SMT solvers generalize this with **polymorphic** decision procedures and **model-based theory combination** (de Moura and Bjørner 2009).

## The Major SMT Solvers

### Z3

Z3 was developed at Microsoft Research (Leonardo de Moura, Nikolaj Bjørner, Christoph Wintersteiger, et al.) and open-sourced in 2015. It is the most-used SMT solver in industry, the engine behind:

- **Dafny** (Rustan Leino's program verifier — verification conditions go to Z3)
- **Frama-C/WP** (C program verification)
- **KLEE** and **SAGE** (symbolic execution engines at Imperial and Microsoft)
- **SymPy / SymPy Logic**, **Boogie** (intermediate verification language)
- **Cryptography proofs** (CryptoVerif, ProVerif use Z3 for sub-goals)

Z3's API is the de-facto standard. Python bindings are first-class:

```python
from z3 import *

# Verify: in a sorted array, every element is between the bounds
def verify_bounded_sort(arr, lo, hi, N):
    s = Solver()
    s.add([And(lo <= arr[i], arr[i] <= hi) for i in range(N)])
    s.add([arr[i] <= arr[i+1] for i in range(N-1)])
    # Suppose a property P implies the array is bounded; check:
    s.add(Not(And([lo <= arr[i] for i in range(N)])))
    return s.check()  # unsat -> P implies the bound

# Direct theorem proving
s = Solver()
x, y = Reals('x y')
s.add(x + y > 0, x*y < 0)               # can x+y > 0 and x*y < 0 co-exist?
print(s.check(), s.model() if s.check() == sat else "")
# Expected: unsat -- the two conditions are mutually exclusive over ℝ
```

Z3 supports the full SMT-LIB theory stack, decision procedures for bit vectors with their own fast bit-blaster, polynomial arithmetic (with CAD-based decision for nonlinear real arithmetic over bounded dimensions), sequences, strings, regular-expression matching, and floating-point reasoning.

### CVC5

CVC5 (the successor to CVC4 and CVC3) is developed jointly at NYU, Stanford, and the University of Iowa. It's used by the **Coq Hammer** and **Lean 4** projects for automation — when you call `sorry`-free `hammer` in Lean, or ` aesop` with SMT backends, CVC5 is one of the backends invoked. CVC5 also supports **proof production**: it can emit a checkable proof object (in the **LFSC** or **Alethe** formats) that lets a skeptical checker independently verify the unsat result. This is the basis of **proof-carrying** SMT and is the current research frontier (the SMT-LIB proof track).

CVC5 is particularly strong at:

- **Quantifier reasoning** via E-matching and conflict-based instantiation
- **Theory combination** (a re-architected, cleaner implementation than Z3's)
- **Model-based quantifier instantiation** (MBQI) for unsat-model synthesis

### Boolector

Boolector (FMV, JKU Linz — Armin Biere's group; now maintained as **Bitwuzla** by Mathias Preiner) is the leading SMT solver for **bit-vector and array theories**. It does aggressive bit-blasting plus lazy layered BV-solving and is consistently the top performer in the QF_BV and QF_ABV divisions of the SMT-COMP competition. It's the engine behind equivalence checking tools for hardware (e.g., ABC, the Berkeley synthesis-and-verification toolkit).

## Production Use Cases

### Bounded Model Checking of C/C++ Programs

**CBMC** (Cambridge — Daniel Kröning) takes a C program, unrolls its loops for k iterations, and encodes the resulting straight-line program as a SAT instance with a negated assertion. If the SAT solver returns SAT, the model is a counterexample of length ≤ k.

```
Source: void f(int *p) { int x = *p; if (x > 0) assert(x + 1 > 0); }
              |
              v   (SSA + bounded unrolling)
        x_0 == *p ∧ x_0 > 0 ∧ ¬(x_0 + 1 > 0)
              |
              v   (bit-blast to CNF)
        SAT instance (QF_BV)
              |
              v   Z3/Boolector
        UNSAT => property holds for k iterations
        SAT   => counterexample (e.g., x_0 = 0x7FFFFFFF, INT_MAX + 1 = INT_MIN)
```

CBMC has been used to verify the Microsoft Windows kernel Hyper-V stack, the Linux kernel's RWLock implementation, and core parts of OpenSSL.

### Symbolic Execution and Test Generation

**KLEE** (Stanford/Cadence) and **SAGE** (Microsoft) drive programs with *symbolic* inputs, fork at each branch, and call an SMT solver (Z3 by default) to determine path feasibility. SAGE, used internally by Microsoft, found thousands of bugs in Office file parsers; KLEE is the foundation of the **symcc** and **angr** ecosystems.

### Constraint Solving for Synthesis

Synthesis tools — from **Sketch** (Solar-Lezama) to modern **program-synthesis** systems — encode "does there exist a program of size ≤ n that satisfies spec P" as a constraint problem and ship it to Z3. The synthesizer for the **P Vanguard** LLVM compiler and the **Rosette** synthesis-on-Racket framework both rest on this.

### Bug Finding in Smart Contracts

Tools like **Certora Prover**, **Halmos**, and **K** (runtime verification) encode Solidity smart contract execution symbolically and ship verification conditions to Z3 or CVC5. The high stakes (DeFi exploits regularly drain 9-figure sums) make formal verification cost-effective.

## When to Use SMT

- Your verification problem is decidable in a standard SMT theory (arithmetic, bit-vectors, arrays, uninterpreted functions).
- You need automation: the solver returns an answer without human proof guidance.
- You can tolerate incompleteness in the rare fragments where SMT is undecidable (e.g., quantified nonlinear integer arithmetic) — the solver returns UNKNOWN and you fall back to interactive proving.
- You want a *model* on SAT, not just a yes/no — useful for test generation and counterexample production.

You probably should not reach for SMT when: the property is naturally a temporal/liveness property over a finite state machine (use a model checker like SPIN or TLC), or the system is too large to bit-blast and your invariants are first-order but richly quantified (use a proof assistant with automation).

## References

- Armin Biere, Marijn Heule, Hans van Maaren, Toby Walsh (eds.). *Handbook of Satisfiability*, 2nd edition, IOS Press 2021. The canonical reference; covers DPLL, CDCL, proof complexity, and applications. https://easychair.org/publications/openaccess/qhC
- Joao Marques-Silva and Karem Sakallah. **GRASP: A Search Algorithm for Propositional Satisfiability**. IEEE TC 1999. The original CDCL paper. https://doi.org/10.1109/12.799831
- Robert Nieuwenhuis, Albert Oliveras, Cesare Tinelli. **Solving SAT and SAT Modulo Theories: From an Abstract Davis-Putnam-Logemann-Loveland Procedure to DPLL(T)**. JACM 2006. The foundational DPLL(T) reference. https://dl.acm.org/doi/10.1145/1160538.1160539
- Daniel Kröning and Ofer Strichman. *Decision Procedures: An Algorithmic Point of View*, 2nd edition, Springer 2016. The standard textbook; covers all the major SMT theories. https://link.springer.com/book/10.1007/978-3-662-53590-1
- The Microsoft Z3 documentation and tutorials. https://microsoft.github.io/z3guide/ and https://github.com/Z3prover/z3
- The CVC5 documentation and papers. https://cvc5.github.io/ and https://github.com/cvc5/cvc5
- Bitwuzla (Boolector's successor) documentation. https://bitwuzla.github.io/
- The SMT-LIB standard and benchmarks. http://smtlib.cs.uiowa.edu/ and the SMT-COMP results http://smt-comp.github.io/
- Clark Barrett, Leonardo de Moura et al. *SMT-COMP: the Satisfiability Modulo Theories Competition*. Annual since 2005; results steer both solver development and the SMT-LIB standard. https://smt-comp.github.io/
