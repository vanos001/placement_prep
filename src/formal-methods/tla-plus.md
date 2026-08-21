# TLA+: Specifying Distributed Systems

## Overview

TLA+ is a formal specification language created by Leslie Lamport in the late 1990s, built on top of the **Temporal Logic of Actions** (TLA), which Lamport introduced in 1994. Unlike most formal-methods tools that target either functional programs (Coq, Lean) or hardware models (NuSMV), TLA+ was designed specifically for **concurrent and distributed systems** — the domain where Lamport himself spent decades (Paxos, Byzantine generals, causality in distributed computation). The result is a specification language whose core abstractions are *states*, *actions*, and *temporal formulas*, not *types* or *functions*. A TLA+ spec is, in effect, a single mathematical formula that describes every legal execution of the system. The model checker TLC then explores finite instances of that formula and reports any execution that violates the properties you care about.

The reason TLA+ is the canonical tool for distributed-systems specification in industry (used by Amazon for DynamoDB/S3/EBS, Microsoft for Cosmos DB, Google for Spanner internals, and MongoDB/Confluent/CockroachDB engineers) is that it works *above the level of code*. You don't model the implementation; you model the protocol. Bugs in the protocol — deadlocks, lost updates, liveness violations under reordering or partition — are exactly the class of bugs that survive every test suite and only surface at 3 a.m. in production.

This page covers TLA+ syntax, PlusCal, the TLC model checker, invariants versus liveness, the Paxos spec as the canonical example, and the contrast with Coq/Lean.

## The TLA (Temporal Logic of Actions) Foundation

TLA is built on three layers, stacked on top of Zermelo-Fraenkel set theory with choice (ZFC). The three layers are:

1. **State predicates** — Boolean-valued functions of a single state. `x = 0`, `queue = <<>>`, `phase[a] = "idle"` are state predicates. They describe *what is true at one instant*.
2. **Actions** — Boolean-valued functions of two states (a "current" and a "next"). An action `A` is true of a pair `(s, t)` iff taking the step `s → t` is allowed by the action. The fundamental action of a TLA spec is the **next-state action**, conventionally named `Next`.
3. **Temporal formulas** — Boolean-valued functions of *behaviors* (infinite sequences of states). The two operators that matter are `□` (always) and `◇` (eventually).

A complete system spec is a single temporal formula:

```
Spec == Init ∧ □[Next]_vars ∧ L
```

Read this as: the system starts in a state satisfying `Init`, every step is either a `Next` step or a stuttering step (a no-op where no variable changes — `[Next]_vars` is "the action `Next` *or* the variables `vars` are unchanged"), and the behavior satisfies the liveness property `L` (often `□◇<some action>` for fairness). Stuttering steps are not a curiosity; they are *essential* to the refinement story, because they let a finer-grained implementation refine an abstract spec without locking step-for-step.

### TLA+ syntax basics

TLA+ is untyped. Values are ZF sets; integers, strings, and booleans are predefined, and `BOOLEAN = {TRUE, FALSE}`. Records, tuples, and functions (in the mathematical sense) are first-class. The most-used combinators:

| TLA+ construct | Meaning |
|----------------|---------|
| `x' = e` | Next-state of variable `x` equals expression `e` |
| `UNCHANGED vars` | All variables in `vars` are unchanged in this step |
| `A ∧ B` | Conjunction; used to combine multiple sub-actions of `Next` |
| `∨` (or `\or`) | Disjunction; used for non-deterministic choice in `Next` |
| `∃ x ∈ S : P` | Existential quantifier over set `S` |
| `[x ∈ S ↦ e]` | Function (map) constructor — equivalent to lambda |
| `<<a, b, c>>` | Tuple |
| `[f1: v1, f2: v2]` | Record |
| `Seq(S)` | Set of all finite sequences over `S` (defined in `Sequences` module) |

A minimal spec — a one-place buffer that drops messages on overflow — looks like:

```tla
---- MODULE Buffer ----
EXTENDS Naturals, Sequences
VARIABLES queue, dropped

CONSTANTS MaxSize

Init ==
    /\ queue = <<>>
    /\ dropped = 0

Enq ==
    /\ Len(queue) < MaxSize
    /\ queue' = Append(queue, "msg")
    /\ dropped' = dropped

Drop ==
    /\ Len(queue) = MaxSize
    /\ queue' = <<>>
    /\ dropped' = dropped + 1

Next == Enq \/ Drop

vars == <<queue, dropped>>
Spec == Init /\ [][Next]_vars

MsgLossInvariant == dropped <= 100  (* bounded retransmit budget *)
====
```

Read it: at any state, `Next` offers a choice between `Enq` (enqueue if there's room) and `Drop` (clear the buffer if it's full). The invariant `MsgLossInvariant` says we never drop more than 100 messages — TLC will check every reachable state of every finite instance to confirm.

## PlusCal: Algorithm Language on Top of TLA+

Writing raw TLA+ for a multi-process algorithm is doable but tedious. **PlusCal** is a small algorithm-description language embedded inside TLA+ comments that compiles to TLA+. It provides the constructs programmers actually want — labeled atomic blocks, `while`/`if`, local variables, and `await` (a guard) — while keeping the output as plain TLA+ that you can read and prove things about.

The two PlusCal syntaxes are `pcal` (Pascal-like `begin/end`) and `pcpp` (C-like braces). The Pascal dialect is more common in Lamport's own specs. A two-process mutual-exclusion algorithm in PlusCal:

```tla
---- MODULE Mutex ----
EXTENDS Naturals
(* --algorithm Mutex
variables lock = 0;  \* 0 = free, 1 = held by A, 2 = held by B
process A = "A"
begin
    AwaitLock:
        await lock = 0;
        lock := 1;
    Critical:
        skip;  \* critical section body
        lock := 0;
end process;
process B = "B"
begin
    AwaitLock:
        await lock = 0;
        lock := 2;
    Critical:
        skip;
        lock := 0;
end process;
end algorithm; *)
====
```

Each label (`AwaitLock`, `Critical`) is an **atomic step boundary**: the statements between two consecutive labels execute atomically. Choosing where to put labels is the central PlusCal design decision — coarse labels give you strong atomicity (easy to reason about, hard to scale), fine labels give you realistic interleavings (harder to prove, more faithful). The compiler produces TLA+ where each labeled block becomes a disjunct of the `Next` action. The above actually has a race: both processes can pass the `await lock = 0` guard in the same step because each block is atomic but the scheduler is fair — TLC will find this and produce a counterexample where both set `lock` simultaneously. (The fix is to fold `await lock = 0; lock := self` into a single labeled block so the test-and-set is atomic.)

## The TLC Model Checker

TLC is an **explicit-state** model checker for TLA+. It does not interpret TLA+ in full generality — TLA+ is untyped and unbounded, but TLC needs a finite model — so it imposes two restrictions:

- **Constants must be assigned concrete values** in a *configuration file* (`MaxSize <- 3`, `Nodes <- {n1, n2, n3}`). The model is over the constant instantiations you give it; you typically run TLC with several different configurations to vary the instance size.
- **Infinite types must be bounded** — `Seq(S)` becomes "sequences of length ≤ N", `Nat` becomes `0..N`, etc. Bounding is explicit (the user writes `Nat == 0..10` as an override).

TLC performs a BFS/DFS over reachable states, storing them in a disk-backed hash table. It also supports **symmetry sets** (if your spec is invariant under a permutation of node IDs, TLC only explores one representative per orbit), **view functions** for fingerprints, and **distributed mode** for running across a cluster. Throughput on a single machine is typically 10^5–10^6 states/sec; production specs routinely explore 10^8–10^12 states overnight.

A typical TLC config file:

```
\* tlc.cfg
SPECIFICATION Spec
INVARIANT TypeOK
INVARIANT MutualExclusion
PROPERTY Liveness
CONSTANTS
    MaxSize = 3
    Nodes = {n1, n2, n3}
SYMMETRY SymNodes
```

When TLC finds a violation it dumps a counterexample trace: an initial state plus a sequence of transitions, each annotated with which sub-action of `Next` fired. The trace is the *most valuable* output of formal verification — it gives you a precise reproduction recipe before you ever write a line of implementation code.

## Invariants vs. Liveness

TLA+ inherits the standard formal-methods distinction:

- **Safety properties** say "bad things never happen." They are invariants of the form `□ P`. `MutualExclusion == □(¬(pc[A] = "CS" ∧ pc[B] = "CS"))` is a safety property. Safety violations have *finite* counterexamples: a state where the bad thing happened.
- **Liveness properties** say "good things eventually happen." They have the form `□◇P` (always eventually P) or `P ↝ Q` (P leads to Q). `EventuallyFreed == □(pc[A] = "Waiting" => ◇(pc[A] = "CS"))` is a liveness property. Liveness violations require *infinite* counterexamples: a behavior where the good thing never happens.

TLC checks safety by walking the reachable state graph and confirming `P` in every state. Liveness is harder — TLC builds a **Büchi automaton** from the negation of the property and searches the product automaton for an accepting cycle (a "lasso" trace: finite prefix + a loop that visits a state where P is pending forever). This is the standard *fairness* machinery: to prove `□◇P` you also need a fairness assumption on the scheduler (e.g., "process A's `await` action cannot be disabled forever"), written `WF_vars(Next)` (weak fairness) or `SF_vars(Next)` (strong fairness) in TLA+.

The engineering lesson: **invariants are cheap; liveness is expensive.** A spec with rich safety invariants and one or two liveness properties typically runs in minutes; adding more `□◇` clauses or stronger fairness assumptions can blow up the search by orders of magnitude. Lamport's advice in *Specifying Systems* is to write safety properties aggressively (they catch most real bugs) and to add liveness sparingly, only for properties whose absence would actually be a correctness failure.

## The Paxos Spec as Canonical Example

The Paxos specification distributed with the TLA+ tools is the canonical "this is what TLA+ is for" example. It is roughly 200 lines of TLA+ (compilable from a 60-line PlusCal), and it captures the essence of Lamport's 1998 paper *The Part-Time Parliament* in a form that TLC can check. The state of each acceptor is a record `(bal, mbal, mval)` — current ballot, max ballot seen, value chosen for that ballot — and the spec models a single proposer driving ballots upward.

```
+---------------------------------+
|  Acceptor state                 |
|  bal   = highest ballot seen    |
|  mbal  = highest ballot voted   |
|  mval  = value for mbal         |
+---------------------------------+
              |
              v
+---------------------------------+
|  Proposer action Phase1a        |
|  choose b > maxSeenBallot       |
|  send (1a, b) to all acceptors  |
+---------------------------------+
              |
              v
+---------------------------------+
|  Acceptor Phase1b               |
|  if b > bal: bal := b           |
|  reply (mbal, mval)             |
+---------------------------------+
              |
              v
+---------------------------------+
|  Proposer Phase2a               |
|  collect quorum of 1b replies   |
|  pick value from highest mbal   |
|  send (2a, b, v)                |
+---------------------------------+
              |
              v
+---------------------------------+
|  Acceptor Phase2b               |
|  if b >= bal: vote (b, v)       |
|  bal := b; mval := v            |
+---------------------------------+
```

The two safety invariants TLC verifies are **consistency** (no two values are ever chosen) and **validity** (any value that is chosen was originally proposed). Liveness (`□◇ chosen` under fair scheduling and a stable majority) is checked separately. The full Paxos spec is included in the TLA+ distribution under `examples/Paxos`; Lamport's *Paxos Made Simple* paper is essentially a prose walkthrough of this TLA+ module.

Production variants exist: Multi-Paxos, Fast Paxos, Vertical Paxos, EPaxos — each is a separate TLA+ spec with its own TLC config. CockroachDB's replication layer was prototyped in TLA+ before being implemented in Go; the spec caught a deadlock in the range-split protocol that survived months of randomized testing.

## Comparison to Coq and Lean

TLA+ and Coq/Lean occupy different points in the formal-methods design space, and Lamport has been emphatic about the distinction in talks (notably his 2014 keynote "Why We Should Build Better TLA+ Tools and Stop Wasting Time on Proof Assistants"):

| Dimension | TLA+ | Coq / Lean |
|-----------|------|------------|
| **Domain** | Concurrent/distributed protocols, system state machines | Pure math, data structures, sequential algorithms, compiler correctness |
| **Logic** | Untyped ZF set theory + temporal logic | Dependent type theory (CIC for Coq, dependent type theory for Lean) |
| **Style** | Specify the *behavior* you want; check finite instances | *Construct* the program/proof as a term that inhabits the spec type |
| **Automation** | TLC: push-button, counterexample or PASS | Tactic-driven; automation (`auto`, `hammer`) for subgoals, but proof effort is real |
| **Scale** | 10^6 – 10^12 states explored in hours | A proof of a non-trivial theorem is days-to-months of expert work |
| **Output** | Counterexample trace (on failure) or PASS (within bound) | Machine-checked proof term + extracted code |
| **Refinement** | Implementation ⟹ TLA+ abstract spec via `THEOREM Impl => Spec` (refinement map) | Refinement via type-level embedding; composable but heavier |

The philosophical point: TLA+ says "tell me what states are legal and what bad things must never happen; I'll search for counterexamples." Coq/Lean says "give me a construction of the program together with a proof it inhabits the spec type." The first approach catches design-level bugs in distributed protocols before you write code; the second catches deep correctness bugs in sequential algorithms and compilers *after* you've written code. The choice depends on where you are in the lifecycle.

Notable industry splits: AWS, CockroachDB, Confluent use TLA+; CompCert, Iris, VST, RustBelt use Coq; mathlib uses Lean. TheCompCert verified compiler was built in Coq because the proof obligations are inherently about an *unbounded* syntax tree of programs — exactly what TLC's finite-instance model cannot express. Conversely, the Paxos protocol's correctness is fundamentally about *all possible interleavings of message delivery* — exactly the case where explicit-state exploration shines and where a Coq proof would require manually reasoning about every scheduler nondeterminism.

## When to Reach for TLA+

- You are designing a consensus, replication, lock-service, or queueing protocol and want to find bugs *before* implementation.
- Your team has been bitten by an outage caused by an interleaving nobody predicted.
- You can articulate the protocol as a state machine with at most a few hundred lines of math.
- Your liveness requirements are simple (a finite set of "eventually" clauses) and your fairness model is standard.

You probably should *not* reach for TLA+ when: the spec is dominated by rich data structures (use Coq/Lean), the system is single-threaded functional code (use QuickCheck/property tests), or the protocol's correctness is fundamentally about arithmetic over unbounded integers (use an SMT solver like Z3).

## References

- Leslie Lamport. *Specifying Systems: The TLA+ Language and Tools for Hardware and Software Engineers*. Addison-Wesley, 2002. The canonical reference. https://lamport.org/tla/book.html
- TLA+ Hyperbook and the official TLA+ page maintained by Lamport. https://lamport.org/tla/tla.html
- Leslie Lamport. *The TLA+ Video Course* (2017–). A free 14-hour video series walking through PlusCal, TLC, and the Paxos spec. https://lamport.org/tla/tla-video.html
- Hillel Wayne. *Learn TLA+*. The most popular community tutorial; includes worked examples on Die Hard, the barbershop, and a small bank. https://www.learntla.com/
- Leslie Lamport. *The Part-Time Parliament*. ACM TOCS 1998. The original Paxos paper, with the TLA+ spec as a companion. https://lamport.org/tla/paxos.pdf
- Markus Kuppe. *Distributed TLC and the TLC Model Checker Performance* (TLaConf talks). Useful for understanding the production-scale workflow. https://github.com/tlaplus/tlaplus
- TLA+ Examples repository, including Paxos, Raft, and other canonical specs. https://github.com/tlaplus/Examples
