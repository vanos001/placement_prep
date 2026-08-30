# Deutsch-Jozsa and Bernstein-Vazirani: The First Quantum Algorithms

The first quantum algorithms ever written down -- Deutsch's 1985 one-qubit trick, its 1992 generalization by Deutsch and Jozsa, and the 1993 Bernstein-Vazirani (BV) hidden-string algorithm -- solve toy problems that no one runs in production. They earned their place in the story for two other reasons. First, they gave the **first proven separations** between quantum and classical computation, and the black-box (oracle) setting they use is still the only setting where such separations can be proved cleanly. Second, they isolated the interference primitive called **phase kickback**, the engine later reused in quantum phase estimation, Shor's algorithm, and Grover's diffuser. The lineage is direct: Deutsch -> Deutsch-Jozsa -> Bernstein-Vazirani -> Simon -> Shor (see [Shor's Algorithm](shors-algorithm.md)). [Quantum Fundamentals](quantum-fundamentals.md) carries a short survey paragraph on each of these algorithms; this page is the slow version -- the query model, the circuits derived step by step, a runnable simulator, and an honest account of what the speedups do and do not mean. Complexity-class context lives in [Quantum Computing](../cs-theory/quantum-computing.md); the largest successor application is [Grover's Search](grovers-search.md).

## The oracle model: why black boxes

To prove that a quantum algorithm beats *every* classical algorithm, the input must be pinned down, or "every classical algorithm" collapses into "every program ever written". The standard move is the **oracle** (black box): the input is a function f: {0,1}^n -> {0,1}, and both kinds of algorithm access it only through queries. A classical query hands over x and receives f(x). A quantum query is the reversible unitary

```text
U_f:  |x>|y>  ->  |x>|y ^ f(x)>      (x: n-qubit register, y: 1-qubit ancilla)
```

**Query complexity** is the number of oracle calls an algorithm makes, worst case over all inputs satisfying the problem's promise; all other gates are free. The abstraction is what makes lower bounds provable -- you simply count looks at f, as in the classical 2^(n-1)+1 bound below -- and it puts both paradigms on one scoreboard: how many views of the input does each need? It is also the model's main weakness, taken up in the limitations section.

## Deutsch's problem: one query where two are forced

Take n = 1. Given f: {0,1} -> {0,1} with the **promise** that f is constant (f(0) = f(1)) or balanced (f(0) != f(1)), decide which.

Classically this needs **two** queries: seeing only f(0) leaves both promise branches open, and no strategy learns the relationship between f(0) and f(1) without evaluating f twice. This is the simplest example of a query lower bound.

Deutsch's circuit puts the x-qubit in |+>, holds the ancilla in |->, applies U_f once, then Hadamards and measures the x-qubit. Tracing the amplitudes, the final amplitude of |0> on the x-qubit is

```text
(1/2) * [ (-1)^f(0) + (-1)^f(1) ]
```

If f is constant the two terms agree: the amplitude is +1 or -1, and the measurement returns 0 with certainty. If f is balanced they cancel: the amplitude is 0 and the measurement returns 1 with certainty. One query suffices because the two evaluations that a classical machine reads from two separate queries are computed **in superposition** and then brought together on one qubit to **interfere**. The property that decides the problem is relational (how f(0) compares to f(1)), and interference reads out relational information in a way no single classical answer can.

## Deutsch-Jozsa: the n-qubit version, and phase kickback

**The promised problem**: f: {0,1}^n -> {0,1} is promised to be constant (same value on all 2^n inputs) or balanced (value 1 on exactly 2^(n-1) inputs). Decide which.

- Classical, deterministic, worst case: **2^(n-1) + 1** queries. If your first 2^(n-1) queries all return 0, you cannot yet stop: a balanced f has exactly 2^(n-1) zeros, so one further query either finds a 1 (balanced) or pushes the zero count past the balanced budget (constant). The demo below watches this happen on n = 4: 9 queries.
- Quantum: **1** query, deterministically, with this circuit:

```text
             +---+      +---------------+     +---+
x_0     |0> -| H |-----|               |-----| H |----->  measure -> c_0
             +---+      |               |     +---+
x_1     |0> -| H |-----|      U_f      |-----| H |----->  measure -> c_1
             +---+      |   (applied    |     +---+
  ...                  |     once)     |      ...
             +---+      |               |     +---+
x_{n-1} |0> -| H |-----|               |-----| H |----->  measure -> c_{n-1}
             +---+      |               |     +---+
a       |1> -| H |-----|               |---------------------->  ancilla stays |->
             +---+      +---------------+

             step 1         step 2              step 3       step 4
             Hadamard       U_f, the ONE        Hadamard     sample the
             on all n+1     query: |x>|y> ->    on the       x-register;
             wires          |x>|y ^ f(x)>       x-register   answer 0^n?
```

**Phase kickback, step by step.** The whole algorithm is the observation that U_f acts diagonally when the ancilla sits in the |-> eigenstate:

1. Hadamard on the ancilla: |1> -> (|0> - |1>)/sqrt(2) = |->.
2. Apply U_f to |x>|-> for one fixed x. If f(x) = 0, the ancilla is untouched: the state is +|x>|->. If f(x) = 1, U_f swaps the ancilla's |0> and |1> amplitudes, which flips the sign of |->: the state is -|x>|->.
3. Compact statement: U_f |x>|-> = (-1)^f(x) |x>|->. The ancilla is an eigenstate of the query's action with eigenvalue (-1)^f(x), and that eigenvalue **kicks back** onto the register that triggered the query. The ancilla can now be ignored.
4. After the query, the x-register holds the phase pattern sum_x (-1)^f(x) |x> / sqrt(2^n): every input's answer encoded as a sign, from one physical query.
5. The final Hadamard layer computes, for each outcome y, the amplitude (1/2^n) sum_x (-1)^(f(x) + x.y): the correlation of f with the parity character x.y.
6. Readout. Constant f: every term of the y = 0 amplitude carries the same sign, so they add to +1 or -1 -- outcome 0^n with probability 1. Balanced f: sum_x (-1)^f(x) = (#zeros) - (#ones) = 0, so the 0^n amplitude is exactly zero -- outcome 0^n never occurs.

The decision rule "answer constant iff the measurement returns 0^n" needs nothing about f beyond the promise. One honesty point: the quantum machine does not learn *which* balanced function it faced. The demo below shows the non-0000 outcomes are not even uniform -- the promise is what lets the algorithm ignore everything except the single amplitude at 0^n.

## Bernstein-Vazirani: one query reads out a secret string

Now the oracle is f(x) = a.x + c (mod 2), where a in {0,1}^n is a **secret string**, "." is the dot product mod 2 (the parity of a AND x), and c is a fixed constant. Task: recover a. Classically, n queries are necessary and sufficient: query the basis vectors x = e_i, and a_i = f(e_i); fewer than n binary answers cannot separate 2^n candidate secrets (so even randomness and bounded error do not help).

The same DJ circuit recovers a in **one** query. Two equivalent views:

**GF(2) / syndrome view.** The final Hadamard layer evaluates, for each candidate y, the character-correlation sum that the measurement samples:

```text
(1/2^n) * sum_x (-1)^(a.x + x.y)  =  1  if y = a,  and  0  otherwise
```

Why: (-1)^(a.x + x.y) = (-1)^((a XOR y).x) (dot products are mod 2), and summing a nontrivial character over the whole group (Z_2)^n gives 0, while the trivial character sums to 2^n. So the outcome distribution is a point mass at y = a. Think of the 2^n equations f(x) = a.x as an overdetermined linear system over GF(2): classically you solve it by substituting n well-chosen points; the quantum circuit absorbs the entire system in one query because its input is a superposition over *all* points, and the Hadamards read out the solution like a syndrome check. The constant c only multiplies the x-register state by a global phase (-1)^c and is invisible to the measurement.

**Gate / Hadamard-test view.** The BV phase oracle factors into single-qubit gates: O|x> = (-1)^(a.x)|x> = the product of Z_i over the bits i where a_i = 1. The circuit is therefore: prepare |+>^n (the +1 eigenstate of every X_i), apply the secret Z-string, measure in the X basis. Each measured bit is the X-eigenvalue after a Z^(a_i) twist -- |+> flips to |-> exactly when a_i = 1. This is the **Hadamard test** pattern (prepare an eigenstate, apply the operator, read out the eigenvalue in the conjugate basis) applied to n qubits at once: BV is the n-bit parity version of it. Swap the secret Z-string for an arbitrary phase gradient and the same readout becomes quantum phase estimation -- the core of [Shor's Algorithm](shors-algorithm.md).

## The circuits, simulated exactly

The simulator below is pure stdlib: a state vector over n + 1 qubits (ancilla = bit 0), Hadamards implemented as 2x2 mixing passes, and the oracle implemented literally as U_f -- the (x,0)/(x,1) amplitude swap, which is exactly what kickback turns into phases. It runs DJ on random constant and random balanced oracles, runs BV with two secrets (one with c = 1), and drives the classical worst case for DJ at n = 4.

```python
# Deutsch-Jozsa and Bernstein-Vazirani, exact state-vector simulation.
# Pure stdlib. Qubit layout: ancilla = bit 0 of the basis index, the
# n-qubit x-register = bits 1..n, so a basis index is 2*x + ancilla.

import random
from collections import Counter

H = 2 ** -0.5

def hadamard(psi, k):
    # Hadamard on the qubit stored in bit k of the basis index.
    step = 1 << k
    for base in range(0, len(psi), 2 * step):
        for i in range(base, base + step):
            a, b = psi[i], psi[i + step]
            psi[i], psi[i + step] = (a + b) * H, (a - b) * H

def oracle(psi, f):
    # U_f: |x>|y> -> |x>|y ^ f(x)>.  With the ancilla held in |-> this
    # acts on the x-register as the phase (-1)^f(x)  (phase kickback).
    for x in range(len(psi) // 2):
        if f(x):
            psi[2 * x], psi[2 * x + 1] = psi[2 * x + 1], psi[2 * x]

def one_query_circuit(f, n, shots, rng):
    # |0...0>|1> -> H on all n+1 qubits -> U_f -> H on x-register -> sample.
    N = 1 << (n + 1)
    psi = [0j] * N
    psi[1] = 1.0                                   # x = 0...0, ancilla = 1
    for q in range(n + 1):
        hadamard(psi, q)
    oracle(psi, f)
    for q in range(1, n + 1):
        hadamard(psi, q)
    probs = [abs(psi[2 * x]) ** 2 + abs(psi[2 * x + 1]) ** 2
             for x in range(N >> 1)]               # marginal over ancilla
    return Counter(rng.choices(range(N >> 1), weights=probs, k=shots))

def random_dj_oracle(n, kind):
    # Constant or balanced f: {0,1}^n -> {0,1}, random truth table.
    if kind == "constant":
        b = random.randint(0, 1)
        return (lambda x: b), "constant"
    xs = list(range(1 << n))
    random.shuffle(xs)
    ones = frozenset(xs[:1 << (n - 1)])            # exactly 2^(n-1) ones
    return (lambda x: x in ones), "balanced"

def bv_oracle(a, c):
    # f(x) = a.x + c  (mod 2);  a is the secret string, c a constant offset.
    return lambda x: (bin(a & x).count("1") + c) & 1

def classical_dj(f, n, order):
    # Query in order until the promise forces an answer; return query count.
    half = 1 << (n - 1)
    zeros = ones = 0
    for i, x in enumerate(order, 1):
        if f(x):
            ones += 1
        else:
            zeros += 1
        if ones and zeros:
            return i, "balanced (saw both values)"
        if zeros > half or ones > half:
            return i, "constant (one value seen more than half the time)"
    return len(order), "constant"

random.seed(7)
rng = random.Random(11)
n, SHOTS = 4, 512
N = 1 << n
print("n = {} x-qubits + 1 ancilla, {} shots per run, random.seed(7)".format(n, SHOTS))
print()
print("Deutsch-Jozsa: one query, verdict = 'constant' iff every shot lands on 0000")
for t, kind in enumerate(["constant", "balanced", "balanced"], 1):
    f, kind = random_dj_oracle(n, kind)
    counts = one_query_circuit(f, n, SHOTS, rng)
    verdict = "CONSTANT" if set(counts) == {0} else "BALANCED"
    ok = "match" if verdict.lower().startswith(kind) else "MISMATCH"
    if set(counts) == {0}:
        detail = "all {} shots on 0000".format(SHOTS)
    else:
        detail = "0000: {}, distinct outcomes: {} (spread over non-zeros)".format(
            counts.get(0, 0), len(counts))
        if t == 2:
            full = dict(sorted((format(x, "04b"), c) for x, c in counts.items()))
            detail += " -> " + str(full)
    print("  oracle {}: {}     circuit says {}  ({})".format(t, kind.ljust(8), verdict, ok))
    print("    x-register counts: " + detail)
print()
print("Bernstein-Vazirani: one query, recover the secret string a in f(x) = a.x + c")
for t, (a, c) in enumerate([(0b1011, 0), (0b0110, 1)], 1):
    counts = one_query_circuit(bv_oracle(a, c), n, SHOTS, rng)
    got = format(counts.most_common(1)[0][0], "04b")
    pretty = dict((format(x, "04b"), v) for x, v in counts.items())
    print("  trial {}: a = {}, c = {} -> counts {}".format(t, format(a, "04b"), c, pretty))
    print("    recovered a = {}  {}".format(got, "MATCH" if got == format(a, "04b") else "WRONG"))
print()
print("Classical query counts (exact algorithms, n = 4, worst case 2^(n-1)+1 = 9):")
adv = [1 if x == 8 else 0 for x in range(N)]       # zeros on the first 8 queries
q, why = classical_dj(lambda x: adv[x], n, list(range(N)))
print("  DJ  adversarial balanced oracle : {} queries ({})".format(q, why))
for kind in ["constant", "balanced"]:
    f, _ = random_dj_oracle(n, kind)
    q, why = classical_dj(f, n, list(range(N)))
    print("  DJ  random {} oracle      : {} queries ({})".format(kind.ljust(8), q, why))
a0 = 0b1001
f = bv_oracle(a0, 0)
bits = "".join(str(f(1 << i)) for i in reversed(range(n)))
print("  BV  basis-vector strategy       : {} queries -> a = {} (n queries in general)".format(n, bits))
```

Output (verbatim from one run; the script is seeded and deterministic):

```text
n = 4 x-qubits + 1 ancilla, 512 shots per run, random.seed(7)

Deutsch-Jozsa: one query, verdict = 'constant' iff every shot lands on 0000
  oracle 1: constant     circuit says CONSTANT  (match)
    x-register counts: all 512 shots on 0000
  oracle 2: balanced     circuit says BALANCED  (match)
    x-register counts: 0000: 0, distinct outcomes: 10 (spread over non-zeros) -> {'0001': 25, '0010': 39, '0100': 27, '0111': 30, '1000': 35, '1010': 128, '1011': 39, '1100': 123, '1101': 31, '1110': 35}
  oracle 3: balanced     circuit says BALANCED  (match)
    x-register counts: 0000: 0, distinct outcomes: 10 (spread over non-zeros)

Bernstein-Vazirani: one query, recover the secret string a in f(x) = a.x + c
  trial 1: a = 1011, c = 0 -> counts {'1011': 512}
    recovered a = 1011  MATCH
  trial 2: a = 0110, c = 1 -> counts {'0110': 512}
    recovered a = 0110  MATCH

Classical query counts (exact algorithms, n = 4, worst case 2^(n-1)+1 = 9):
  DJ  adversarial balanced oracle : 9 queries (balanced (saw both values))
  DJ  random constant oracle      : 9 queries (constant (one value seen more than half the time))
  DJ  random balanced oracle      : 2 queries (balanced (saw both values))
  BV  basis-vector strategy       : 4 queries -> a = 1001 (n queries in general)
```

Reading the run: the constant oracle puts all 512 shots on 0000; the balanced oracles put **exactly zero** shots on 0000, with the rest scattered over f-dependent non-uniform weights (amplitude of y is (1/16) * sum_x (-1)^(f(x) + x.y), which varies with f) -- the promise makes that scatter irrelevant. BV concentrates all 512 shots on the secret string, including with the c = 1 offset, which confirms the global-phase argument. On the classical side, the adversarial balanced oracle (zeros on the algorithm's first eight probes, a one on the ninth) forces 9 = 2^(n-1)+1 queries, as does any constant oracle before "constant" can be certified; the BV basis strategy needs n = 4.

## Why these matter despite being impractical

- **First proven separations.** Deutsch (1985) established the first task on which a quantum machine provably beats every classical one; Deutsch-Jozsa stretched the gap to exponential (1 vs 2^(n-1)+1 queries); and the Bernstein-Vazirani paper went further, defining the class BQP and proving BQP is contained in PSPACE -- the first structural theorem about efficient quantum computation.
- **Phase kickback is reusable technique.** Eigenstate-in, phase-out is the template of quantum phase estimation (Shor's order finding is QPE of modular multiplication), of the ancilla-in-|-> conversion from bit oracles to phase oracles that [Grover's Search](grovers-search.md) builds its diffuser on, and of controlled-gate decompositions throughout fault-tolerant circuit design. The one-query BV readout is the n-bit parity instance of the Hadamard test.
- **The lineage matters more than the problems.** Simon's algorithm (1994), BV's direct descendant, gave the first exponential oracle separation with enough structure to survive de-oracleing, and Shor converted that structure into factoring. DJ and BV are the first two links of the chain that leads to the algorithms with real cryptanalytic force.
- **They are cheap to verify.** The state spaces are small enough to simulate by hand (the demo above does it in ~50 lines), which is why these circuits are the standard first contact with interference-based algorithms.

## Limitations, honestly

- **Promise problems.** Both algorithms lean on a promise -- constant/balanced, or exactly-linear-plus-constant -- that natural computational tasks rarely carry, and checking the promise can cost as many queries as the algorithm saves. Drop the promise and the circuit's output is just the correlation profile of f, with no decision guarantee behind it.
- **Bounded error collapses the DJ separation.** The gap 1 vs 2^(n-1)+1 is exact-vs-exact. A classical randomized algorithm drawing k distinct random queries errs only if all k land on one value of a balanced f, which has probability 2 * C(2^(n-1), k) / C(2^n, k) ~ 2^(1-k); three queries already give error below 1/3 at every n. So for DJ, once both sides are allowed to err, the "exponential" separation is 1 vs constant. BV is the contrast case: its classical cost stays n even with bounded error, since n binary answers are needed to separate 2^n secrets.
- **Oracle separations are relative.** "No classical algorithm with this oracle matches you" is not "here is a natural, efficiently computable function family where the speedup survives implementation". DJ and BV demonstrate that interference decides relational properties cheaply; they do not themselves yield useful computations. Bridging that gap was Simon's contribution, and Shor's.
- **The significance is pedagogical and technique-level.** These algorithms are where query complexity, phase oracles, kickback, and the superpose-query-interfere template first appear in a setting small enough to verify by hand. That is their job, and they do it well -- but they are not evidence that useful exponential speedups are common.

## Where this fits in this book

[Quantum Fundamentals](quantum-fundamentals.md) holds the qubit and gate prerequisites and a one-paragraph-per-algorithm survey of Deutsch, Deutsch-Jozsa, BV, and Simon (the recap this page unpacks). [Grover's Search](grovers-search.md) scales the same oracle framing to the first practically relevant quantum speedup, with the optimality lower bound. [Shor's Algorithm](shors-algorithm.md) is where the kickback/QPE technique factors integers, completing the DJ -> BV -> Simon -> Shor arc. [Quantum Computing](../cs-theory/quantum-computing.md) situates BQP -- the class defined in the BV paper -- among the classical complexity classes.

## References

1. D. Deutsch. "Quantum theory, the Church-Turing principle and the universal quantum computer." *Proc. R. Soc. Lond. A* 400:97-117, 1985. <https://doi.org/10.1098/rspa.1985.0070>
2. D. Deutsch, R. Jozsa. "Rapid solution of problems by quantum computation." *Proc. R. Soc. Lond. A* 439:553-558, 1992. <https://doi.org/10.1098/rspa.1992.0167>
3. E. Bernstein, U. Vazirani. "Quantum Complexity Theory." *STOC 1993*, pp. 11-20; journal version *SIAM J. Comput.* 26(5):1411-1473, 1997. <https://doi.org/10.1137/S0097539796300921>
4. C. H. Bennett, E. Bernstein, G. Brassard, U. Vazirani. "Strengths and Weaknesses of Quantum Computing." *SIAM J. Comput.* 26(5):1510-1523, 1997. <https://arxiv.org/abs/quant-ph/9701001>
5. M. A. Nielsen, I. L. Chuang. *Quantum Computation and Quantum Information*, 10th anniversary ed. Cambridge University Press, 2010 -- Chapter 1 introduces Deutsch's and Deutsch-Jozsa's algorithms as the first case studies in the circuit model.
6. A. M. Childs. *Lecture Notes on Quantum Algorithms* (course notes, University of Maryland). <https://www.cs.umd.edu/~amchilds/qa/>
