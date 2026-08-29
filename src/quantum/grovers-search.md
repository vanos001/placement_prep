# Grover's Search and Amplitude Amplification

Grover's algorithm (STOC 1996) finds a marked item in an unstructured space of N items using about (pi/4)*sqrt(N) oracle queries, versus N/2 expected queries classically. The speedup is quadratic, not exponential -- and it is provably optimal: no quantum algorithm can do better for unstructured search. This page works the algorithm end to end: the oracle and diffuser operators, the two-angle geometric derivation, a runnable state-vector simulator, the amplitude-amplification generalization, the optimality lower bounds, and a careful account of what the quadratic speedup does and does not mean for cryptanalysis. Prerequisites: qubits, gates, and the oracle-model warmups (Deutsch-Jozsa, Bernstein-Vazirani, Simon) live in [Quantum Fundamentals](quantum-fundamentals.md); the complexity-class framing in [Quantum Computing](../cs-theory/quantum-computing.md).

## The problem and the query model

Given a boolean function f: {0,1}^n -> {0,1} promised to have M inputs with f(x) = 1 (the "marked" items, N = 2^n), find one. The only access to f is a phase oracle:

```text
O_f |x> = (-1)^f(x) |x>          (marks x by flipping its phase)
```

The cost measure is the number of oracle queries; all other gates are free. This abstraction is what makes lower bounds provable -- and it is also why "1 query = 1 cheap operation" is a trap (see the cryptanalysis section: for key search, one oracle call *is* the full cipher). Classically, any algorithm needs an expected N/2 queries (worst case N - M + 1); nothing about the instance is exploitable because the problem is *unstructured*. Grover's insight was that quantum interference can amplify the marked amplitudes with sqrt(N) instead of N queries.

## The Grover iterate: phase oracle + diffuser

One Grover iteration applies two reflections to the uniform start state |s> = (1/sqrt(N)) sum_x |x>:

```text
        +------------------ repeat k times ------------------+
|s> --->|  +----------------+     +-----------------------+  |--> measure
        |  | oracle O_f     |     | diffuser D            |
        |  | |x> -> -|x>    |     | 2|s><s| - I           |
        |  | phase flip on  |     | inversion about the   |
        |  | marked items   |     | mean amplitude        |
        |  +----------------+     +-----------------------+
        +-----------------------------------------------------+
```

If the current state is |psi> = sum_x a_x |x>, the iterate does, component-wise:

```text
1. oracle:   b_x = (-1)^f(x) * a_x          (flip sign of marked amplitudes)
2. diffuser: mu  = (1/N) * sum_x b_x        (the mean)
             a_x = 2*mu - b_x               (invert every amplitude about mu)
```

The diffuser is the matrix D = 2|s><s| - I, and it factors into familiar gates: D = H^n [2|0><0| - I] H^n -- Hadamards around a multi-controlled Z (up to a global sign; I - 2|s><s| is physically identical). Hardware constructions prepare an ancilla in |-> = (|0> - |1>)/sqrt(2) and use phase kickback, which is exactly the construction in the AES resource estimates cited below.

## The geometry: rotation by 2*theta per iteration

Write the state in the 2-D plane spanned by the uniform superposition over marked items |w> and over unmarked items |r>. The start state sits at angle theta from the |r> axis:

```text
|s> = sin(theta) |w> + cos(theta) |r>,        sin(theta) = sqrt(M/N)
```

The oracle reflects about the |r> axis; the diffuser reflects about the |s> axis. Two reflections compose into a rotation by twice the angle between their axes, so each Grover iterate rotates the state by 2*theta toward |w>:

```text
  |w>
   ^              s4 (angle pi/2: peak, p ~ 1)
   |               |
   |     s2        |          each iterate: rotate by 2*theta
   |      \        |          inside span(|w>, |r>)
   |       \       |
   |  s0 \  \ s3   |
   |     \\  \\    |
   |      \\  \\   |
   +-------\--\----\-------------------> |r>
       s0 at angle theta, s1 at 3*theta, s2 at 5*theta, ...
```

After k full iterates the state is at angle (2k+1)*theta from the |r> axis, so the success probability is p_k = sin^2((2k+1)*theta) with theta = arcsin(sqrt(M/N)). Stop when (2k+1)*theta = pi/2, i.e. at the integer

```text
k* = round(pi/(4*theta) - 1/2)   ~   (pi/4) * sqrt(N/M)      (asymptotically)
```

For M = 1 this is (pi/4)*sqrt(N) -- Grover's famous iteration count. The simulator below confirms every piece of this picture on N = 32.

## State-vector simulator: per-iteration probabilities and the peak

```python
# Grover state-vector simulator: N=32, one marked item.
# Amplitudes stay real during Grover, but we carry complex to stay faithful.
import math

N = 32                      # 2^5 search space
marked = 13                 # the item the oracle flips
theta = math.asin(1.0 / math.sqrt(N))

state = [complex(1.0 / math.sqrt(N)) for _ in range(N)]

def oracle(a):
    a[marked] = -a[marked]                    # phase flip on |marked>

def diffuser(a):
    mu = sum(a) / len(a)
    return [2.0 * mu - x for x in a]          # inversion about the mean

print("N=%d, M=1, theta = arcsin(1/sqrt(N)) = %.5f rad" % (N, theta))
print("exact peak k* = round(pi/(4*theta) - 0.5) = %d" %
      round(math.pi / (4 * theta) - 0.5))
print("asymptotic (pi/4)*sqrt(N) = %.4f" % (math.pi / 4 * math.sqrt(N)))
print()
print(" k   p(sim)    sin^2((2k+1)theta)   |diff|")
for k in range(9):
    p_sim = abs(state[marked]) ** 2
    p_form = math.sin((2 * k + 1) * theta) ** 2
    print(" %d   %.4f    %.4f             %.1e" %
          (k, p_sim, p_form, abs(p_sim - p_form)))
    oracle(state)
    state = diffuser(state)
```

Output (real run; the simulator matches the closed form to float precision):

```text
N=32, M=1, theta = arcsin(1/sqrt(N)) = 0.17771 rad
exact peak k* = round(pi/(4*theta) - 0.5) = 4
asymptotic (pi/4)*sqrt(N) = 4.4429

 k   p(sim)    sin^2((2k+1)theta)   |diff|
 0   0.0312    0.0312             0.0e+00
 1   0.2583    0.2583             1.1e-16
 2   0.6024    0.6024             3.3e-16
 3   0.8969    0.8969             4.4e-16
 4   0.9992    0.9992             2.2e-16
 5   0.8596    0.8596             2.2e-16
 6   0.5459    0.5459             3.3e-16
 7   0.2099    0.2099             5.6e-17
 8   0.0145    0.0145             6.9e-18
```

Two things to notice: p_0 = 1/N exactly (the algorithm starts no better than blind guessing), and success is **not monotone** -- past the peak at k* = 4 it collapses back toward zero; there is no "keep iterating until you are sure".

## Multiple solutions, partial search, and quantum counting

With M solutions, sin(theta) = sqrt(M/N) and the count shrinks to (pi/4)*sqrt(N/M): more solutions, fewer queries. The second demo sweeps M, then deliberately over-rotates:

```python
# M solutions in N=32: peak within the FIRST oscillation period vs
# (pi/4)*sqrt(N/M), then an over-rotation sweep (success is not monotone).
import math

def grover_curve(N, marked_list, kmax):
    st = [complex(1.0 / math.sqrt(N)) for _ in range(N)]
    curve = []
    for k in range(kmax + 1):
        curve.append(sum(abs(st[i]) ** 2 for i in marked_list))
        for i in marked_list:
            st[i] = -st[i]
        mu = sum(st) / N
        st = [2.0 * mu - x for x in st]
    return curve

N = 32
print("M  k_peak  p_peak   (pi/4)*sqrt(N/M)   k* = floor(pi/(4*theta))")
for M in (1, 2, 3, 4):
    th = math.asin(math.sqrt(M / N))
    period = int(math.floor(math.pi / (2 * th)))   # first oscillation period
    marked = list(range(N - M, N))                 # any fixed set of M indices
    curve = grover_curve(N, marked, period)
    k_peak = max(range(len(curve)), key=lambda k: curve[k])
    print("%d  %d       %.4f   %.4f            %d" %
          (M, k_peak, curve[k_peak], math.pi / 4 * math.sqrt(N / M),
           math.floor(math.pi / (4 * th))))

print()
curve = grover_curve(32, [13], 16)
print("Over-rotation, N=32, M=1: success prob vs iteration count")
for k in (2, 4, 6, 8, 9, 10, 12, 13):
    print("  k=%2d   p=%.4f" % (k, curve[k]))
```

```text
M  k_peak  p_peak   (pi/4)*sqrt(N/M)   k* = floor(pi/(4*theta))
1  4       0.9992   4.4429            4
2  3       0.9613   3.1416            3
3  2       0.9998   2.5651            2
4  2       0.9453   2.2214            2

Over-rotation, N=32, M=1: success prob vs iteration count
  k= 2   p=0.6024
  k= 4   p=0.9992
  k= 6   p=0.5459
  k= 8   p=0.0145
  k= 9   p=0.0542
  k=10   p=0.3098
  k=12   p=0.9290
  k=13   p=0.9927
```

Read the over-rotation table against the lower bound of the next section: running roughly twice as long as optimal (k = 9 vs k* = 4) lands you at p = 0.054 -- worse than the 1/32 you started with. Sweeping past the first period can find slightly higher later peaks (for M = 2 the curve returns to p = 0.9996 at k = 15), which is why Boyer-Brassard-Hoyer-Tapp derive exact stopping rules and adaptive schedules achieving O(sqrt(N/M)) expected queries even when M is unknown. Estimating M itself is **quantum counting**: the Grover operator has eigenvalues e^(+-2i*theta), so quantum phase estimation on it recovers theta, hence M = N * sin^2(theta) -- the same primitive that powers Shor's algorithm (see [Quantum Fundamentals](quantum-fundamentals.md)).

## Amplitude amplification (Brassard-Hoyer-Mosca-Tapp)

Grover is the special case of a much more general booster. Given any state-preparation unitary A with A|0> = |psi>, partition the state space into "good" and "bad" via an indicator chi, and let a = |good component|^2 = sin^2(theta). Define the Grover-like operator

```text
Q = -A S_0 A^(-1) S_chi      where  S_0   = flip phase of |0...0>
                                    S_chi = flip phase of every good state
```

Q is exactly Grover's iterate with A playing the role of "Hadamard over the search space": after k applications, p_k = sin^2((2k+1)*theta) with theta = arcsin(sqrt(a)). So boosting an a-probability event to constant success takes O(1/sqrt(a)) uses of A, versus O(1/a) classical repetitions -- the same quadratic gain, now for arbitrary state preparation. This is the workhorse pattern behind quantum Monte Carlo speedups and amplitude estimation (Montanaro's survey covers the landscape), and it slots into variational pipelines wherever a measurement success probability needs amplifying (see [Quantum Advanced Topics](quantum-advanced.md)). The over-rotation problem persists in the general case; Yoder-Low-Chuang fixed-point variants replace the schedule with rotations that approach the target monotonically at the same asymptotic query cost.

## Optimality: BBBV and Zalka

The quadratic speedup is a ceiling, not a warm-up act:

- **Bennett-Bernstein-Brassard-Vazirani (1997)** proved that any quantum algorithm for unstructured search needs Omega(sqrt(N)) oracle queries. The hybrid argument: each query can shift amplitudes toward the marked set by at most O(1/sqrt(N)), so after t queries the success probability is O(t^2/N) -- constant success needs t = Omega(sqrt(N)). This is one of the few tight quantum lower bounds known.
- **Zalka (1999)** strengthened it to constants: for *any* target success probability, Grover's total query count (pi/4)*sqrt(N/M) is optimal, and -- quoting the abstract -- "quantum searching cannot be parallelized better than by assigning different parts of the search space to independent quantum computers". Splitting N across p machines gives wall-clock (pi/4)*sqrt(N/p) but total queries (pi/4)*sqrt(N*p): parallelism buys a sqrt(p) depth reduction at a sqrt(p) total-work *penalty*. Consequence for NP-complete problems: brute force goes from 2^n to 2^(n/2) steps -- real but merely quadratic, and no route to NP inside BQP (see [Complexity Classes](../cs-theory/complexity-classes.md)).

## What Grover does and does not mean for cryptanalysis

Grover counts *oracle queries*. For key search the oracle is the cipher itself: U_f evaluates AES(K, P) for candidate K, compares against known plaintext-ciphertext pairs, and uncomputes. So the honest unit is gates, not queries, and the definitive study is Grassl-Langenberg-Roetteler-Steinwandt (PQCrypto 2016), whose Clifford+T resource estimates for the full Grover pipeline are:

| Key size | Grover iterations     | T-gate count | Overall depth | Logical qubits |
|----------|-----------------------|--------------|---------------|----------------|
| AES-128  | floor((pi/4) x 2^64)  | 1.19 x 2^86  | 1.16 x 2^81   | 2,953          |
| AES-192  | floor((pi/4) x 2^96)  | 1.81 x 2^118 | 1.33 x 2^113  | 4,449          |
| AES-256  | floor((pi/4) x 2^128) | 1.41 x 2^151 | 1.57 x 2^145  | 6,681          |

Three caveats, in decreasing order of solidity:

1. **Serial depth is the killer.** The authors note that "the overall depth is a direct result of the serial nature of Grover's algorithm", and Zalka's parallelization result above bounds how much that can be attacked with more machines (a sqrt(p) time gain for a sqrt(p) total-work penalty).
2. **Logical qubits are not physical qubits.** The counts above are fault-tolerant *logical* resources; surface-code error correction multiplies them by orders of magnitude and adds magic-state distillation for the T gates (see [Quantum Error Correction](quantum-error-correction.md)). A 2^64-deep logical circuit at microsecond-scale logical clock rates is a project no hardware roadmap approaches -- the barrier is engineering, not the query model.
3. **The standard mitigation is cheap.** NIST's post-quantum report (IR 8105) states the heuristic plainly -- "doubling the key size will be sufficient to preserve security" -- while cautioning the rule "may be overly conservative". That is exactly why AES-256 and SHA-256 preimage resistance (2^128 quantum work under Grover) are regarded as safe, and why NIST judged that a quadratic speedup "does not render cryptographic technologies obsolete". The same report notes specialized quantum algorithms exist for hash *collision* finding with better-than-birthday scaling (Brassard-Hoyer-Tapp: 2^(n/3) for an n-bit hash) -- a reminder that details, not headlines, decide the margins.

The careful summary for an interview: Grover's speedup against symmetric crypto is real, provably optimal, and already priced into key-size guidance; what it is not is an exponential collapse. RSA/ECC fall to Shor; AES falls -- if ever -- to a quadratically-faster, fabulously expensive brute force, and AES-256 restores a 2^128 quantum security margin. Public-key migration is urgent ([Post-Quantum Cryptography](../cryptography/post-quantum.md)); symmetric migration is a key-length policy question.

## Interview-style derivations

> **"Derive the optimal number of Grover iterations from scratch."**

Start from |s> = sin(theta)|w> + cos(theta)|r> with sin(theta) = sqrt(M/N). One iterate is a reflection about |r> (oracle) followed by a reflection about |s> (diffuser); two reflections compose to a rotation of 2*theta. After k iterates the marked amplitude is sin((2k+1)*theta), maximized at (2k+1)*theta = pi/2, so k* = round(pi/(4*theta) - 1/2) ~ (pi/4)*sqrt(N/M). For N = 32, M = 1: theta = 0.17771 and k* = 4, matching the simulator above.

> **"Show the diffuser is 'inversion about the mean', and why."**

D = 2|s><s| - I acting on |psi> gives (2|s><s||psi>)_x - psi_x = 2*(1/N)*sum_y psi_y - psi_x, i.e. every amplitude is replaced by 2*mu - a_x where mu is the mean. Geometrically that is a reflection through the state |s>: components below the mean are lifted, components above are lowered. This is also why the diffuser needs no knowledge of f -- it is defined purely by the current state.

> **"An event has probability a = 1/1024. Boost it classically vs with amplitude amplification."**

Classical repetition reaches 90% in ln(0.1)/ln(1 - 1/1024) = 2,359 samples. Amplitude amplification: theta = arcsin(1/32) = 0.03126, so k* = round(pi/(4*theta) - 1/2) = 25 applications of Q, giving p = sin^2(51 * 0.03126) = 0.9995. Twenty-five queries instead of 2,359 samples -- the quadratic signature, on a number you can check by hand.

> **"Why can't a better algorithm amplify straight to 100%, or beat sqrt(N)?"**

The iterate is a fixed rotation, so p_k = sin^2((2k+1)*theta) oscillates and cannot be monotonically driven to 1. BBBV's hybrid argument bounds *any* algorithm: t queries move at most O(t/sqrt(N)) of amplitude onto the marked set, so constant success requires t = Omega(sqrt(N)); Zalka shows Grover's constant is optimal and that parallelizing beyond space partitioning does not help. The lower bound closes every escape route -- which is precisely why the quadratic speedup is credible enough to design cryptosystems around.

## Where this fits in this book

[Quantum Fundamentals](quantum-fundamentals.md) holds the qubit/gate math, the Deutsch-Jozsa/Bernstein-Vazirani/Simon warmups, and phase estimation (the quantum-counting subroutine); [Quantum Computing](../cs-theory/quantum-computing.md) places the BBBV bound in the BQP landscape; [Quantum Error Correction](quantum-error-correction.md) explains the logical-to-physical overhead dominating the cost column above; [Quantum Key Distribution & BB84](quantum-key-distribution.md) is a quantum protocol whose security rests on physics, not query bounds; and [Post-Quantum Cryptography](../cryptography/post-quantum.md) covers the lattice/code/hash migration that Shor (not Grover) forces.

## References

1. L. K. Grover. "A Fast Quantum Mechanical Algorithm for Database Search." STOC 1996, pp. 212-219. <https://doi.org/10.1145/237814.237866>
2. C. H. Bennett, E. Bernstein, G. Brassard, U. Vazirani. "Strengths and Weaknesses of Quantum Computing." SIAM J. Comput. 26(5):1510-1523, 1997. <https://arxiv.org/abs/quant-ph/9701001>
3. M. Boyer, G. Brassard, P. Hoyer, A. Tapp. "Tight Bounds on Quantum Searching." PhysComp 1996. <https://arxiv.org/abs/quant-ph/9605034>
4. G. Brassard, P. Hoyer, M. Mosca, A. Tapp. "Quantum Amplitude Amplification and Estimation." AMS Contemporary Mathematics 305:53-74, 2002. <https://arxiv.org/abs/quant-ph/0005055>
5. C. Zalka. "Grover's Quantum Searching Algorithm is Optimal." Phys. Rev. A 60:2746-2751, 1999. <https://arxiv.org/abs/quant-ph/9711070>
6. M. Grassl, B. Langenberg, M. Roetteler, R. Steinwandt. "Applying Grover's Algorithm to AES: Quantum Resource Estimates." PQCrypto 2016. <https://arxiv.org/abs/1512.04965>
7. NIST. "Post-Quantum Cryptography Preliminary Information" (IR 8105), 2016. <https://nvlpubs.nist.gov/nistpubs/ir/2016/NIST.IR.8105.pdf>
8. A. Montanaro. "Quantum Algorithms: an Overview." npj Quantum Information 2:15023, 2016. <https://arxiv.org/abs/1511.04206>
9. T. J. Yoder, G. H. Low, I. L. Chuang. "Fixed-Point Quantum Search with an Optimal Number of Queries." Phys. Rev. Lett. 113:210501, 2014. <https://doi.org/10.1103/PhysRevLett.113.210501>
10. G. Brassard, P. Hoyer, A. Tapp. "Quantum Algorithm for the Collision Problem." LATIN 1998, LNCS 1380. <https://arxiv.org/abs/quant-ph/9705002>
11. M. A. Nielsen, I. L. Chuang. "Quantum Computation and Quantum Information," 10th anniversary ed., Chapter 6. Cambridge University Press, 2010.
