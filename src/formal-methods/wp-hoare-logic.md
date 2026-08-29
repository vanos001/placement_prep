# Hoare Logic and Weakest Preconditions

Every deductive program verifier ships a proof engine built from the same few parts: a small axiomatic semantics for imperative commands, a predicate transformer that turns postconditions into preconditions, and a translation of "check my annotations" into first-order formulas handed to an SMT solver. This page works through those parts precisely -- Hoare triples, the wp/wlp calculus as Dijkstra defined it, loop invariants and variants, guarded commands, and what verifiers like Dafny, Frama-C/WP, and Why3 actually emit. It is the deep companion to the survey in [Program Verification](./program-verification.md); the heap-specific continuation lives in [Separation Logic](./separation-logic.md), and the algorithm-flavored use of triples in interview settings is in [Correctness Proofs of Algorithms](../dsa/chapters/ch69-correctness-proofs.md).

## Partial vs Total Correctness

A Hoare triple `{P} C {Q}` reads: if assertion P holds in the state before command C runs, and C halts, then Q holds in the state after. The "if it halts" is the whole subtlety.

| Property | Notation | Guarantee | What it does NOT give | Transformer |
|---|---|---|---|---|
| Partial correctness | `{P} C {Q}` | If C halts having started with P, then Q holds | No claim that C halts | `wlp(C, Q)` |
| Total correctness | `[P] C [Q]` | Starting with P, C halts and Q holds | Nothing -- halting is included | `wp(C, Q)` |

The distinction is not pedantry: `{true} while true do x := x {false}` is a *valid* partial-correctness triple, because the loop never halts and so never violates the postcondition. Total correctness rejects it. Every proof of an iterative algorithm therefore has two independent battles: preservation of a property, and termination. Hoare introduced the logic in his 1969 CACM paper "An axiomatic basis for computer programming", giving a small imperative language an axiomatic interpretation as an alternative to flowchart reasoning.

## The Proof System

The judgment is the triple; the rules are syntax-directed and compositional. The assignment axiom, in the modern backward form, substitutes the assigned expression into the postcondition:

```text
(skip)        {P} skip {P}

(assignment)  {Q[E/x]} x := E {Q}          Q[E/x] = Q with E substituted for x
              (Hoare's 1969 paper stated it forward: |- P0 x:=E P, where
               P0 is P with E substituted in before execution)

(sequence)    {P} C1 {R}    {R} C2 {Q}
              --------------------------
                    {P} C1; C2 {Q}

(conditional) {P /\ B} C1 {Q}    {P /\ ~B} C2 {Q}
              ----------------------------------
                    {P} if B then C1 else C2 {Q}

(while)       {I /\ B} S {I}
              ----------------------------   (partial correctness)
                {I} while B do S {I /\ ~B}

(consequence) P' => P     {P} C {Q}     Q => Q'
              -----------------------------------
                       {P'} C {Q'}
```

Everything except assignment is an inference rule; assignment is the only axiom, and the consequence rule is what makes the system usable: you may strengthen preconditions and weaken postconditions at any step. Proofs are normally built backwards from Q, computing what must have been true before each command.

## wp and wlp: Predicate Transformers

Dijkstra inverted the view. Instead of deriving rules, define a function from commands and postconditions to preconditions:

- `wp(C, Q)` -- the *weakest* precondition such that C, started in any state satisfying it, **terminates** in a state satisfying Q. Total correctness.
- `wlp(C, Q)` -- the weakest precondition such that *if* C terminates at all, the final state satisfies Q. Partial correctness.

| Command C | `wp(C, Q)` (total) | `wlp(C, Q)` (partial) |
|---|---|---|
| `skip` | Q | Q |
| `x := E` | `Q[E/x]` | `Q[E/x]` |
| `C1; C2` | `wp(C1, wp(C2, Q))` | `wlp(C1, wlp(C2, Q))` |
| `if B then C1 else C2` | `(B /\ wp(C1,Q)) \/ (~B /\ wp(C2,Q))` | same shape |
| `abort` (diverges) | `false` | `true` (vacuous: never halts) |
| `while B do S` | `(E k >= 0: H_k)`, see below | greatest fixpoint of `X = (~B /\ Q) \/ (B /\ wlp(S,X))` |

For straight-line and branching code the two transformers coincide; they separate exactly on divergence. The while row shows why annotations exist: the exact wp of a loop is an infinite disjunction `H_0 \/ H_1 \/ H_2 \/ ...`, where `H_0 = ~B /\ Q` and `H_{k+1} = ~B /\ Q \/ (B /\ wp(S, H_k))` -- "terminates within k iterations". No finite formula captures it in general, so humans (or inference procedures) supply an invariant and the tool generates obligations instead.

Dijkstra's "healthiness" laws constrain any sensible transformer: monotonicity (`P => Q` implies `wp(C,P) => wp(C,Q)`); positive conjunctivity (`wp(C, Q1 /\ Q2) = wp(C,Q1) /\ wp(C,Q2)`); and the law of the excluded miracle, `wp(C, false) = false` -- no implementable command guarantees termination into an impossible state. Disjunctivity (`wp(C, Q1 \/ Q2) = wp(C,Q1) \/ wp(C,Q2)`) holds for deterministic commands and fails for nondeterministic ones, which is exactly the fault line Dijkstra was probing with guarded commands.

## Loop Invariants and Variant Functions

Given a loop `while B do S`, an invariant I is inductive when three obligations hold, plus a **variant function** v (Dijkstra's bound function) for termination -- an expression bounded below and strictly decreased by the body, since a strictly descending chain in the naturals cannot be infinite:

```text
(1) initiation:    P => I
(2) preservation:  I /\ B  =>  wp(S, I)
(3) completion:    I /\ ~B =>  Q
(4) variant:       I /\ B  =>  0 <= v' < v      (v' = v after one body step)
```

These are precisely what the wp calculus emits when the uncomputable loop transformer is replaced by the supplied I. A working example, Euclid's gcd on positive inputs:

```text
requires: a >= 1 /\ b >= 1           (a0, b0: ghost snapshot of the inputs)
a0 := a; b0 := b;
while b != 0
  invariant: gcd(a, b) == gcd(a0, b0) /\ a >= 1 /\ b >= 0
  variant:   b
  { t := a % b; a := b; b := t }
ensures:  a == gcd(a0, b0)
```

The invariant is the only creative step; everything else is mechanical -- the demo below generates and discharges the obligations.

## Dijkstra's Guarded Commands

In "Guarded commands, nondeterminacy and formal derivation of programs" (CACM 1975; manuscript EWD472) Dijkstra proposed composing programs from guarded commands:

```text
if B1 -> S1 [] B2 -> S2 fi     execute one Si whose guard Bi is true;
                               abort if no guard holds; choose freely if both do

do B1 -> S1 [] B2 -> S2 od     repeat while any guard holds
```

Nondeterminism is a reasoning device, not an implementation trick: when both guards hold, the program must be correct for *either* branch, which lets you state algorithms without inventing an artificial order between symmetric cases. The transformer for the conditional form is `wp(if fi, Q) = (B1 \/ B2) /\ (B1 => wp(S1,Q)) /\ (B2 => wp(S2,Q))` -- note the leading `(B1 \/ B2)`: aborting is only permitted when no guard holds. The looping form's wp is again the infinite-disjunction characterization from the previous section. This language plus the wp calculus is the core of Dijkstra's 1976 book *A Discipline of Programming*, which develops program construction as predicate-transformer derivation rather than verify-after-the-fact debugging.

## From Annotations to Verification Conditions

Production verifiers apply exactly the machinery above, mechanically, to annotated source, and emit **verification conditions** (proof obligations) that automated provers then discharge:

```text
        annotated program                          proof obligations
+---------------------------------------+        +--------------------------+
| Dafny:  requires / ensures /          |        |  VC-1: P => I            |
|         decreases / invariant         |   wp   |  VC-2: I /\ B => wp(S,I) |
| C+ACSL: requires / ensures /          | -----> |  VC-3: I /\ ~B => Q      |
|         loop invariant / loop variant | calc.  |  VC-4: variant decreases |
| WhyML:  requires / ensures / variant  |        |  ...one per annotation   |
+---------------------------------------+        +------------+-------------+
                                                              |
                     counterexample model <-------------------+---> SMT solver
                     (a failing VC points at the                (Z3 / Alt-Ergo /
                      annotation to strengthen)                  CVC / Coq)
```

| Tool | Input + annotation surface | VC engine | Back-end provers |
|---|---|---|---|
| Dafny | Dafny language; requires/ensures/decreases/invariant | translates to Boogie, which generates the VCs | SMT: Z3 default; others via SMT-LIB2 output |
| Frama-C/WP | C + ACSL contracts (loop invariant/variant, assigns) | wp calculus over a memory model; Qed simplifier first | Alt-Ergo, Z3, CVC4, Coq, and Why3-supported provers |
| Why3 | WhyML; contracts + variants | generates goals/VCs itself | dispatches to many automated and interactive provers |
| Boogie | intermediate verification language | the VC generator itself | pluggable SMT solvers |

Dafny's `decreases` clause is the variant function; ACSL's `loop variant` is the same idea for C. When a prover fails, the verifier reports the obligation it could not discharge, ideally with a counterexample state -- the developer's job is then to strengthen an invariant or fix a spec, not to re-derive proofs by hand.

## Demo: a Weakest-Precondition Calculator for a While Language

The model below implements wp for assignment, sequence, assume/assert, if, and while-with-supplied-invariant over a tiny AST. Assertions are Python expression strings; the substitution `Q[E/x]` is done on the parsed AST (as a real VC generator would); each obligation is discharged by brute-force checking over a small grid of states. A negative control shows the checker catching an unsound invariant, and the same AST is executed concretely as a cross-check.

```python
import ast, itertools, math

ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Name,
           ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Mod, ast.USub, ast.Not,
           ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
           ast.Load, ast.Call)
ENV = {"gcd": math.gcd}                    # uninterpreted here: a model function

def ev(text, state):                       # guarded evaluator over the state dict
    tree = ast.parse(text, mode="eval")
    for n in ast.walk(tree):
        if not isinstance(n, ALLOWED):
            raise ValueError("node not allowed: %r" % n)
    return eval(compile(tree, "<vc>", "eval"), {"__builtins__": {}},
                dict(state, **ENV))

def sub(text, var, expr):                  # textual Q[x := E] on the parsed AST
    class T(ast.NodeTransformer):
        def visit_Name(self, n):
            return ast.parse("(%s)" % expr, mode="eval").body if n.id == var else n
    return ast.unparse(T().visit(ast.parse(text, mode="eval")))

class A:                                   # assertion = display text + predicate
    def __init__(self, text, fn):
        self.text, self.fn = text, fn

def mk(text):  return A(text, lambda s, t=text: ev(t, s))
def AND(p, q): return p if q.text == "true" else (q if p.text == "true" else A(
    "(%s) and (%s)" % (p.text, q.text), lambda s: p.fn(s) and q.fn(s)))
def IMP(p, q): return A("(not (%s)) or (%s)" % (p.text, q.text),
                        lambda s: (not p.fn(s)) or q.fn(s))

VCS = []                                   # collected proof obligations

def step(stmts, state):                    # one concrete pass through a block
    s = dict(state)
    for st in stmts:
        s[st[1]] = ev(st[2], s)            # statements are (assign, x, expr) tuples
    return s

def wp(st, Q):
    kind = st[0]
    if kind == "assign":
        x, e = st[1], st[2]
        return A(sub(Q.text, x, e), lambda s, x=x, e=e, Q=Q:
                 Q.fn(dict(s, **{x: ev(e, s)})))
    if kind == "assume": return IMP(mk(st[1]), Q)
    if kind == "assert": return AND(mk(st[1]), Q)
    if kind == "block":
        for s2 in reversed(st[1]): Q = wp(s2, Q)
        return Q
    if kind == "while":                    # st = (while, B, invariant, variant, body)
        b, inv, var, body = st[1], st[2], st[3], st[4]
        I, W = mk(inv), wp(("block", body), mk(inv))
        VCS.append(("preservation", "(%s) and (%s) -> %s" % (inv, b, W.text),
                    lambda s: not (I.fn(s) and ev(b, s)) or W.fn(s)))
        VCS.append(("completion", "(%s) and (not (%s)) -> %s" % (inv, b, Q.text),
                    lambda s: not (I.fn(s) and not ev(b, s)) or Q.fn(s)))
        VCS.append(("variant", "(%s) and (%s) -> (%s decreases and %s >= 0)"
                    % (inv, b, var, var),
                    lambda s: not (I.fn(s) and ev(b, s))
                    or (ev(var, step(body, s)) < ev(var, s) and ev(var, s) >= 0)))
        return I                           # supplied invariant replaces exact wp
    raise ValueError(kind)

INV = "gcd(a, b) == gcd(a0, b0) and a >= 1 and b >= 0"
prog = [("assign", "a0", "a"), ("assign", "b0", "b"),
        ("assume", "a >= 1 and b >= 1"),                 # requires-clause
        ("while", "b != 0", INV, "b",
         [("assign", "t", "a % b"), ("assign", "a", "b"), ("assign", "b", "t")]),
        ("assert", "a == gcd(a0, b0)")]                  # ensures-clause

def check(program, note):
    VCS.clear()
    C = wp(("block", program), A("true", lambda s: True))
    VCS.append(("entry", "true -> %s" % C.text, C.fn))
    GRID = [-1, 0, 1, 2, 3, 5, 9]
    print("===", note, "===  invariant:", program[3][2])
    ok = 0
    for i, (name, text, fn) in enumerate(VCS, 1):
        bad = [t for t in itertools.product(GRID, repeat=4)
               if not fn({"a": t[0], "b": t[1], "a0": t[2], "b0": t[3]})]
        ok += (not bad)
        if bad: print("VC-%d %-12s REJECTED, e.g. a=%d b=%d a0=%d b0=%d"
                      % (i, name, *bad[0]))
        else:   print("VC-%d %-12s %s  [VALID on grid]" % (i, name, text))
    print("discharge: %d/%d obligations valid on grid %s^4 (%d states each)\n"
          % (ok, len(VCS), GRID, len(GRID) ** 4))

check(prog, "annotated Euclid gcd")
check([p if p[0] != "while" else ("while", p[1],
       "gcd(a, b) == gcd(a0, b0) and a >= 1", p[3], p[4]) for p in prog],
      "negative control (weakened invariant)")

s = {"a": 48, "b": 18}
for st in prog:                            # concrete execution, same AST
    if st[0] == "assign": s[st[1]] = ev(st[2], s)
    elif st[0] == "assume": assert ev(st[1], s)
    elif st[0] == "while":
        while ev(st[1], s):
            assert ev(st[2], s), st[2]
            s = step(st[4], s)
print("concrete run gcd(48, 18) -> a = %d ; math.gcd(48, 18) = %d ; match = %s"
      % (s["a"], math.gcd(48, 18), s["a"] == math.gcd(48, 18)))
```

Output (the negative control drops the invariant's `b >= 0` conjunct):

```text
=== annotated Euclid gcd ===  invariant: gcd(a, b) == gcd(a0, b0) and a >= 1 and b >= 0
VC-1 preservation (gcd(a, b) == gcd(a0, b0) and a >= 1 and b >= 0) and (b != 0) -> gcd(b, a % b) == gcd(a0, b0) and b >= 1 and (a % b >= 0)  [VALID on grid]
VC-2 completion   (gcd(a, b) == gcd(a0, b0) and a >= 1 and b >= 0) and (not (b != 0)) -> a == gcd(a0, b0)  [VALID on grid]
VC-3 variant      (gcd(a, b) == gcd(a0, b0) and a >= 1 and b >= 0) and (b != 0) -> (b decreases and b >= 0)  [VALID on grid]
VC-4 entry        true -> not (a >= 1 and b >= 1) or (gcd(a, b) == gcd(a, b) and a >= 1 and (b >= 0))  [VALID on grid]
discharge: 4/4 obligations valid on grid [-1, 0, 1, 2, 3, 5, 9]^4 (2401 states each)

=== negative control (weakened invariant) ===  invariant: gcd(a, b) == gcd(a0, b0) and a >= 1
VC-1 preservation REJECTED, e.g. a=1 b=-1 a0=-1 b0=-1
VC-2 completion   (gcd(a, b) == gcd(a0, b0) and a >= 1) and (not (b != 0)) -> a == gcd(a0, b0)  [VALID on grid]
VC-3 variant      REJECTED, e.g. a=1 b=-1 a0=-1 b0=-1
VC-4 entry        true -> not (a >= 1 and b >= 1) or (gcd(a, b) == gcd(a, b) and a >= 1)  [VALID on grid]
discharge: 2/4 obligations valid on grid [-1, 0, 1, 2, 3, 5, 9]^4 (2401 states each)

concrete run gcd(48, 18) -> a = 6 ; math.gcd(48, 18) = 6 ; match = True
```

The rejected obligations encode exactly the expected failure: without `b >= 0` the hypothesis `I /\ B` admits `b = -1`, where the body can produce `a' = b = -1` (breaking `a >= 1`) and the variant is no longer bounded below. Real verifiers report the same shape of failure, just against an SMT model instead of a grid.

## Soundness and Relative Completeness

Hoare's calculus is sound -- induction on the derivation shows every derivable triple is a true statement about the operational semantics, so a proof never certifies a broken program. Completeness cannot be absolute, because by Godel's incompleteness theorems no effective proof system captures all true statements of arithmetic; the precise result is Stephen Cook's relative-completeness theorem (SIAM Journal on Computing, 1978): for the while-language over the natural numbers with addition and multiplication, Hoare's proof system derives exactly the true partial-correctness triples, provided the assertion language is expressive, meaning that for every program C and postcondition Q the strongest postcondition of C (equivalently, the wlp) is definable in it -- a property Peano arithmetic enjoys. "Relative" means relative to the arithmetical theory, and the hypothesis bites in practice: restrict the assertion language or the data domain too far and true triples can become underivable, which is why practical VC generators rely on users supplying the invariants the theory says exist but no bounded tool can invent. For total correctness the same architecture extends with well-founded variant functions for deterministic while-programs (see Apt, de Boer, and Olderog's textbook treatment), with soundness again unproblematic and completeness the delicate direction.

## Why Pointers Broke It -- and Where the Story Goes

Classical Hoare logic quietly assumes the state is a flat store of variables: an assignment rule that substitutes into postconditions has no way to say "and *only* cell p changed". With pointers, `p.next := v` can affect anything reachable through any alias, so the precondition of every command must enumerate the entire heap it might touch, the frame property (reasoning locally about untouched state) is lost, and modular verification of linked structures becomes impractical. Separation logic (O'Hearn, Reynolds, and colleagues) repaired exactly this by adding the spatial separating conjunction `P * Q` (P and Q hold on disjoint heap fragments) and a frame rule that makes locality a first-class inference; the resulting calculus underpins modern heap verifiers and Infer's bi-abduction at scale. The full development -- separating conjunction, the frame rule, symbolic execution of heaps, Iris -- is covered in [Separation Logic](./separation-logic.md).

## Where This Fits in the Book

- [Program Verification](./program-verification.md) -- the survey chapter this page deepens
- [Separation Logic](./separation-logic.md) -- the pointer-aware successor logic
- [SAT/SMT Solvers](./sat-smt-solvers.md) -- the engines that discharge the obligations above
- [Symbolic Execution](./symbolic-execution.md) -- the forward, test-flavored dual of backward wp
- [Model Checking](./model-checking.md) -- state exploration over finite abstractions instead of deduction
- [Formal Semantics](../compilers/advanced/formal-semantics.md) -- operational and denotational background for the rules
- [Correctness Proofs of Algorithms](../dsa/chapters/ch69-correctness-proofs.md) -- triples applied to interview algorithms
- [Formal Methods (survey)](../cs-theory/formal-methods.md) -- where Dafny sits among theorem provers

## References

- [C. A. R. Hoare, "An Axiomatic Basis for Computer Programming", CACM 12(10), 1969 -- the original triples and assignment axiom](https://doi.org/10.1145/363235.363259)
- [E. W. Dijkstra, "Guarded Commands, Nondeterminacy and Formal Derivation of Programs", CACM 18(8), 1975](https://doi.org/10.1145/360933.360975)
- [E. W. Dijkstra, EWD472 -- the author's manuscript of the guarded-commands paper (UT Austin archive)](https://www.cs.utexas.edu/~EWD/transcriptions/EWD04xx/EWD472.html)
- E. W. Dijkstra, *A Discipline of Programming*, Prentice-Hall, 1976 -- wp, wlp, and program derivation as predicate transformers
- [S. A. Cook, "Soundness and Completeness of an Axiom System for Program Verification", SIAM J. Comput. 7(1), 1978](https://doi.org/10.1137/0207005)
- [K. R. M. Leino, "Dafny: An Automatic Program Verifier for Functional Correctness", LPAR 2010](https://doi.org/10.1007/978-3-642-17511-4_20)
- [Dafny Reference Manual -- requires/ensures/decreases/invariant, translation to Boogie and SMT](https://dafny.org/dafny/DafnyRef/DafnyRef)
- [Frama-C WP plug-in -- deductive proofs of ACSL contracts, Qed simplifier, external provers](https://www.frama-c.com/fc-plugins/wp.html)
- [Frama-C WP plug-in manual (PDF) -- memory models and obligation generation](https://frama-c.com/download/frama-c-wp-manual.pdf)
- [Why3 -- platform for deductive program verification; WhyML and VC discharge](https://why3.org/)
- [Boogie -- intermediate verification language and VC generator used by Dafny](https://github.com/boogie-org/boogie)
