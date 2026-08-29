# Variational Quantum Algorithms: VQE and QAOA

VQE (Variational Quantum Eigensolver) and QAOA (Quantum Approximate Optimization Algorithm) are the two canonical hybrid quantum-classical algorithms: a shallow parameterized quantum circuit prepares a trial state, hardware measurements estimate a cost, and a classical optimizer updates the parameters. They matter for one reason above all others -- they are the only known quantum algorithms structured to run end-to-end on near-term hardware, because every quantum subroutine is short enough to finish inside a coherence window. This page works the machinery in detail: the eigensolver loop and its measurement cost, the ansatz families, the barren-plateau trainability cliff, the parameter-shift rule, QAOA on MaxCut, and a sober comparison against fault-tolerant algorithms. Prerequisites: qubits, gates, and measurement in [Quantum Fundamentals](quantum-fundamentals.md); the NISQ framing in [Quantum Computing](../cs-theory/quantum-computing.md); the survey-level tour and hybrid-workflow patterns in [Quantum Advanced Topics](quantum-advanced.md).

## Why the variational pattern exists

Fault-tolerant algorithms (Shor, phase estimation) need millions of high-fidelity logical gates; NISQ hardware offers hundreds to thousands of physical qubits with roughly 0.1-1% gate error and no error correction (the correction path is covered in [Quantum Error Correction](quantum-error-correction.md)). The variational workaround splits the problem:

- The quantum processor does only what it is irreplaceable for: preparing and measuring entangled states that are hard to handle classically.
- Everything that tolerates noise -- parameter search, bookkeeping, data reduction -- stays classical.

For ground-state problems the mathematical anchor is the Rayleigh-Ritz variational principle: for any normalized trial state |psi(theta)>,

```text
E(theta) = <psi(theta)| H |psi(theta)>  >=  E0     (the true ground-state energy)
```

so minimizing E(theta) over parameters theta is a well-posed classical optimization whose objective happens to be measured on a quantum device. Minimization is the entire algorithm; there is no separate convergence proof to satisfy. VQE (Peruzzo et al., 2014) targets molecular Hamiltonians; QAOA (Farhi et al., 2014) targets combinatorial costs such as MaxCut. Both were introduced in 2014 and both were demonstrated on real (photonic and superconducting) hardware within three years.

## VQE: the eigensolver loop

```text
            theta_k                     new theta
   +--------------------+   E(theta_k)   +------------------------+
   | classical optimizer|<---------------| estimator: <H> from    |
   | (update rule)      |                | S shots per Pauli term |
   +--------------------+                +------------------------+
            |                                        ^
            v                                        | weighted sum of
   +-------------------------------------------------+----------+
   | quantum processor: prepare |psi(theta)>, measure each    |
   | Pauli term in its own basis (commuting terms share runs)  |
   +-----------------------------------------------------------+
```

Per iteration the optimizer proposes theta, the hardware runs the ansatz circuit once per measurement setting, and the estimator combines shot counts into E(theta) = sum_k c_k <P_k>. The loop is dominated by repeated state preparation and measurement, so the engineering questions are: which terms must be measured (next section), how many shots each needs, and whether the ansatz can even represent the answer.

### What actually gets measured

Chemistry Hamiltonians arrive as weighted Pauli strings. The two-qubit reduced H2 Hamiltonian used by O'Malley et al. (coefficients from their Table I at R = 0.75 Angstrom, the same numbers the demo below runs on) is:

```text
H = g0*I + g1*Z0 + g2*Z1 + g3*Z0Z1 + g4*X0X1 + g5*Y0Y1
    g0=0.2252, g1=0.3435, g2=-0.4347, g3=0.5716, g4=g5=0.0910
```

Six terms, but not six circuits: mutually commuting terms share one measurement setting because a single basis rotation makes them all diagonal.

| Setting | Basis rotation | Terms measured |
|---------|----------------|----------------|
| Z basis | none | Z0, Z1, Z0Z1 |
| X basis | Hadamard on each qubit | X0X1 |
| Y basis | S-dagger then Hadamard on each qubit | Y0Y1 |

Each expectation value comes from S shots with statistical error falling as 1/sqrt(S). Resolving an energy to absolute error eps needs roughly S = O(1/eps^2) shots per term, which -- multiplied by the number of settings, the optimizer iterations, and the parameter shifts for gradients -- is the dominant runtime cost of VQE on real hardware.

### The ansatz decides everything

| Family | Structure | Strength | Weakness |
|--------|-----------|----------|----------|
| UCCSD | Trotterized excitation operators from coupled cluster | chemistry-guided, systematically improvable | deep circuits; Trotter error and noise stack up |
| Hardware-efficient (Kandala et al., 2017) | layers of single-qubit rotations plus fixed entanglers, matched to native gates | shallow, minimal compilation overhead | no physics insight; prone to barren plateaus |
| ADAPT-VQE (Grimsley et al., 2019) | grows the ansatz operator by operator, adding whichever pool operator has the largest energy gradient | near-minimal depth for a target accuracy | many extra measurements each time an operator is screened |

The tension is expressibility versus trainability: an ansatz too shallow cannot reach the ground state (the variational minimum sits above E0 no matter how good the optimizer is), while an ansatz expressive enough to approximate any state is typically untrainable for the reason below.

## Barren plateaus: the trainability cliff

McClean et al. (2018) proved that for sufficiently random parameterized circuits the variance of the cost-function gradient vanishes exponentially in the number of qubits: the optimization landscape flattens into a plateau, and the exponentially many local minima sit at essentially the same energy. Concretely, the probability that a randomly initialized optimizer measures a gradient above any fixed threshold is exponentially small -- gradient descent cannot even detect a downhill direction.

- Intuition: random deep circuits scramble information so thoroughly that the cost becomes a random variable with concentration of measure; the gradient distribution narrows to a spike at zero as n grows.
- Noise makes it worse: Wang et al. (2021) showed that under realistic local noise the gradient also vanishes exponentially whenever the ansatz depth grows linearly with qubit count, independent of initialization.
- What survives: shallow, structured, problem-inspired ansaetze; local (few-qubit) cost functions instead of global ones; layerwise training; identity-block initializations. This is the strongest argument for chemistry-motivated ansaetze over generic hardware-efficient ones.

The operational warning for practitioners: check the variance of measured gradients across parameter resets early in training. A shrinking gradient spread at fixed energy is the plateau signature, and more shots cannot fix an information-theoretic flatness.

## Gradients without finite differences: the parameter-shift rule

Every parameterized gate used in these loops has the form U(theta) = exp(-i*theta*G). When G has exactly two eigenvalues (a Pauli generator scaled by 1/2, e.g. RY = exp(-i*theta*Y/2)), the derivative of any measured expectation is exact and hardware-friendly (Mitarai et al., 2018; generalized by Schuld et al., 2019):

```text
dE/dtheta = [ E(theta + pi/2) - E(theta - pi/2) ] / 2
```

Two extra circuit runs per parameter replace finite differences, with no truncation error and no differencing noise floor. Costs: a K-parameter ansatz needs 2K evaluations per gradient step, each paying the full shot budget -- one reason derivative-free optimizers (COBYLA, Nelder-Mead) and noise-tolerant approximations like SPSA remain popular on hardware. Two caveats worth stating in an interview: the two-point rule is exact only for two-eigenvalue generators (multi-eigenvalue generators such as QAOA cost unitaries need generalized multi-point shifts), and the rule is about exact expectations -- shot noise still rides on every evaluation.

## QAOA: MaxCut as the canonical problem

MaxCut asks for the partition of a graph's vertices maximizing the number of edges crossing the partition. Encoding bit x_i as the side of vertex i, the cost Hamiltonian (Farhi et al., 2014) is

```text
H_C = sum_{(i,j) in E} (1 - Z_i Z_j) / 2      (counts crossing edges; ground state = MaxCut)
H_M = sum_i X_i                                (mixer: flips individual bits)
```

QAOA alternates evolutions of the two, starting from the uniform superposition |+>^n:

```text
|0>^n --H^n--> |+>^n --[e^{-i*g1*H_C}]--[e^{-i*b1*H_M}]-- ... --[e^{-i*gp*H_C}]--[e^{-i*bp*H_M}]--> measure
                |        cost phase per edge        per-qubit bit flips        |
                |        (diagonal, easy)           Rx(2*b) gates              +--> sample bitstrings,
                +-------------------- p alternating layers, depth O(p*|E|) -------    keep the best cut
```

The cost evolution is diagonal (phase per bitstring proportional to its cut value); the mixer re-mixes amplitudes between bitstrings. Depth is 2p blocks, and the optimizer searches the 2p angles (beta_k, gamma_k). What the algorithm returns is a distribution over cuts, not a cut: you optimize the expected value <H_C> and then sample, keeping the best string seen.

Honest performance facts to memorize:

- Farhi et al. proved that at p = 1 on 3-regular graphs QAOA always finds a cut of at least 0.6924 times the optimal size. The classical Goemans-Williamson semidefinite program guarantees 0.878 on every graph -- better, with a proof, at any p = 1.
- Brandao et al. showed that for fixed p the QAOA objective concentrates across typical random instances: per-instance angle tuning buys almost nothing at low depth, and no instance-level quantum advantage appears at p = 1.
- Increasing p strictly improves the achievable expectation and connects to the adiabatic limit, but the angle landscape develops the trainability problems of the previous section, and each extra layer costs coherent two-qubit gates on noisy hardware.

## Where NISQ reality bites

- Shot budgets compound. The two-qubit demo Hamiltonian below has 3 settings and 1 parameter: one gradient step costs 2 shifted evaluations x 3 settings; at 1000 shots each that is 6000 shots per step, and a 200-step optimization is ~1.2M shots -- for two qubits. Molecules with 6-20 qubits run to hundreds of Pauli terms, and the multiplier becomes tens of millions of shots per energy curve.
- Noise biases the variational minimum. Depolarizing noise pulls measured expectations toward the maximally mixed value, so even a perfect optimizer converges to a noise-limited floor above E0. The variational guarantee E(theta) >= E0 is an ideal-circuit statement; on hardware the measured value can sit below E0 only through error, which is why raw VQE outputs need mitigation.
- Error mitigation is not error correction. Zero-noise extrapolation, measurement-matrix unrolling, and symmetry post-selection (e.g. rejecting bitstrings with the wrong particle number) claw back accuracy at extra shot cost but scale poorly; the durable fix is error correction (see [Quantum Error Correction](quantum-error-correction.md)).
- Optimizers meet noise. Gradient estimates are the objective plus 1/sqrt(S) noise; coordinate descent can wander along flat directions; SPSA deliberately uses only two stochastic evaluations per step and is often the most shot-efficient choice on hardware. Cheap classical tricks (commuting-term grouping, parameter tying) usually move the runtime needle more than optimizer cleverness.

## VQE and QAOA versus fault-tolerant algorithms

| Aspect | VQE (NISQ) | QAOA (NISQ) | QPE-based chemistry (fault-tolerant) |
|--------|------------|-------------|--------------------------------------|
| Output | energy upper bound E(theta*) >= E0 | distribution over cuts | eigenvalue to target precision |
| Circuit depth | ansatz-limited, shallow | 2p blocks, depth O(p * E) with E the edge count | deep: evolution time grows as 1/eps |
| Precision cost | O(1/eps^2) shots, no hard eps floor | sampling only, no eps guarantee | O(1/eps) coherent evolution |
| Guarantee | none beyond the variational bound | 0.6924 ratio at p=1 on 3-regular graphs | exact within simulated basis |
| Hardware | today's, no error correction | today's, no error correction | error-corrected logical qubits |

Three honest conclusions. First, variational algorithms trade guarantees for depth: what you get is an upper bound (VQE) or a sampler (QAOA), with no certificate of optimality and no promise the ansatz can reach the answer. Second, the fault-tolerant competition is not hypothetical -- phase estimation for chemistry is the asymptotically sound algorithm, and VQE's best-case role is a noisy preview of the same observable, not a replacement. Third, the same asymmetry appears for provable-speedup algorithms: Grover's quadratic search speedup ([Grover's Search and Amplitude Amplification](grovers-search.md)) is a theorem, yet still needs fault-tolerant depth to matter. Whether any variational heuristic beats the best classical competitor on a production-scale problem remains open; no such demonstration exists, and the leading candidates (small-molecule energies, MaxCut instances) all have strong classical rivals.

## Two runnable classical simulations

Both simulations are deterministic, stdlib-only, and run in well under a second -- small enough to check every step by hand.

### Demo 1: VQE on the two-qubit H2 Hamiltonian

The Hamiltonian is the six-term operator above. The ansatz is O'Malley et al.'s UCC excitation, which in this two-qubit encoding collapses to X(q1), RY(q0,t), CNOT(q0,q1), preparing |psi(t)> = cos(t/2)|01> + sin(t/2)|10> -- a one-parameter family that contains the exact ground state. The script exact-diagonalizes H with Jacobi rotations, then runs the VQE loop using parameter-shift gradients, and cross-checks the shift rule against a central difference.

```python
import math

G = [0.2252, 0.3435, -0.4347, 0.5716, 0.0910, 0.0910]  # O'Malley Table I, R = 0.75 A

def kron(a, b):
    return [[a[i // 2][j // 2] * b[i % 2][j % 2] for j in range(4)] for i in range(4)]

I4 = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
Z = [[1, 0], [0, -1]]; X = [[0, 1], [1, 0]]; I2 = [[1, 0], [0, 1]]
YY = [[0, 0, 0, -1], [0, 0, 1, 0], [0, 1, 0, 0], [-1, 0, 0, 0]]  # Y(x)Y is real

H = [[G[0] * I4[i][j] for j in range(4)] for i in range(4)]
for M, w in [(kron(Z, I2), G[1]), (kron(I2, Z), G[2]), (kron(Z, Z), G[3]),
             (kron(X, X), G[4]), (YY, G[5])]:
    for i in range(4):
        for j in range(4):
            H[i][j] += w * M[i][j]
print("Hamiltonian H (basis |00>, |01>, |10>, |11>):")
for row in H:
    print("   " + "  ".join(f"{v:+.4f}" for v in row))

def energy(t):
    psi = [0.0, math.cos(t / 2), math.sin(t / 2), 0.0]   # cos(t/2)|01> + sin(t/2)|10>
    Hp = [sum(H[i][j] * psi[j] for j in range(4)) for i in range(4)]
    return sum(psi[i] * Hp[i] for i in range(4))

# exact ground state: cyclic Jacobi rotations on the symmetric 4x4
A = [row[:] for row in H]
for _ in range(50):
    if sum(A[i][j] ** 2 for i in range(4) for j in range(4) if i != j) < 1e-24:
        break
    for p in range(3):
        for q in range(p + 1, 4):
            if abs(A[p][q]) < 1e-15:
                continue
            th = 0.5 * math.atan2(2 * A[p][q], A[q][q] - A[p][p])
            c, s = math.cos(th), math.sin(th)
            for k in range(4):
                A[k][p], A[k][q] = c * A[k][p] - s * A[k][q], s * A[k][p] + c * A[k][q]
            for k in range(4):
                A[p][k], A[q][k] = c * A[p][k] - s * A[q][k], s * A[p][k] + c * A[q][k]
E0 = min(A[i][i] for i in range(4))
print(f"exact ground state (Jacobi diagonalization): E0 = {E0:.6f} Ha")

print("VQE loop: parameter-shift gradient dE/dt = [E(t+pi/2) - E(t-pi/2)]/2")
t, lr = 0.0, 0.8
for step in range(61):
    if step % 12 == 0 or step == 60:
        print(f"   step {step:2d}   t = {t:+.4f}   E(t) = {energy(t):.6f}")
    t -= lr * (energy(t + math.pi / 2) - energy(t - math.pi / 2)) / 2
Ef = energy(t)
ps = (energy(math.pi / 2) - energy(-math.pi / 2)) / 2          # shift rule at t=0
fd = (energy(1e-6) - energy(-1e-6)) / 2e-6                      # finite difference
print(f"shift-rule vs central-difference gradient at t=0: {ps:+.6f} vs {fd:+.6f}")
print(f"VQE result: t* = {t:.4f} rad, E = {Ef:.6f} Ha, error |E - E0| = {abs(Ef - E0):.2e} Ha")
print(f"ground state: {math.cos(t/2):+.4f}|01> + {math.sin(t/2):+.4f}|10>")
```

Output:

```text
Hamiltonian H (basis |00>, |01>, |10>, |11>):
   +0.7056  +0.0000  +0.0000  +0.0000
   +0.0000  +0.4318  +0.1820  +0.0000
   +0.0000  +0.1820  -1.1246  +0.0000
   +0.0000  +0.0000  +0.0000  +0.8880
exact ground state (Jacobi diagonalization): E0 = -1.145599 Ha
VQE loop: parameter-shift gradient dE/dt = [E(t+pi/2) - E(t-pi/2)]/2
   step  0   t = +0.0000   E(t) = 0.431800
   step 12   t = -2.9108   E(t) = -1.145599
   step 24   t = -2.9118   E(t) = -1.145599
   step 36   t = -2.9118   E(t) = -1.145599
   step 48   t = -2.9118   E(t) = -1.145599
   step 60   t = -2.9118   E(t) = -1.145599
shift-rule vs central-difference gradient at t=0: +0.182000 vs +0.182000
VQE result: t* = -2.9118 rad, E = -1.145599 Ha, error |E - E0| = 0.00e+00 Ha
ground state: +0.1146|01> + -0.9934|10>
```

The optimizer recovers the correct two-determinant structure (one dominant determinant plus a small opposite-sign admixture) and matches exact diagonalization to machine precision. Note what the printed loop does not show: on hardware every E(t) above would carry a 1/sqrt(S) error bar, and the ansatz guarantees reachability only because this molecule is exactly solvable in this encoding -- the part VQE cannot promise in general.

### Demo 2: QAOA p=1 on a 4-node MaxCut instance

The graph is a 4-cycle plus one diagonal (5 edges). The script brute-forces MaxCut, scans the full (beta, gamma) landscape for p = 1 exactly (16-dimensional state vectors), then samples 200 shots at the best angles with a fixed seed.

```python
import math
import random

EDGES = [(0, 1), (1, 2), (2, 3), (3, 0), (1, 3)]
N = 1 << 4

def cost(x):
    bits = [(x >> q) & 1 for q in range(4)]
    return sum(1 for i, j in EDGES if bits[i] != bits[j])

best_cut = max(cost(x) for x in range(N))
opts = [x for x in range(N) if cost(x) == best_cut]
part = lambda x: "A={" + ",".join(str(q) for q in range(4) if not (x >> q) & 1) + \
                 "} B={" + ",".join(str(q) for q in range(4) if (x >> q) & 1) + "}"
print(f"brute force over all 16 cuts: MaxCut = {best_cut} of {len(EDGES)} edges")
print("optimal partitions (bit x encodes node side): " + "; ".join(part(x) for x in opts[:2]))

def qaoa_expect(beta, gamma):
    v = [complex(0.25, 0)] * N                      # |+>^4
    for x in range(N):                              # e^{-i*gamma*H_C}: diagonal phase
        v[x] = v[x] * complex(math.cos(gamma * cost(x)), -math.sin(gamma * cost(x)))
    for q in range(4):                              # e^{-i*beta*sum X} = Rx(2*beta) per qubit
        w = [0j] * N
        cb, sb = math.cos(beta), math.sin(beta)
        for x in range(N):
            w[x] = cb * v[x] - 1j * sb * v[x ^ (1 << q)]
        v = w
    return sum(cost(x) * abs(v[x]) ** 2 for x in range(N)), v

nb, ng = 48, 96
best = max(((qaoa_expect(2 * math.pi * a / nb, 2 * math.pi * b / ng)[0], a, b)
            for a in range(nb) for b in range(ng)))
C, _ = qaoa_expect(2 * math.pi * best[1] / nb, 2 * math.pi * best[2] / ng)
print(f"grid scan {nb}x{ng} = {nb*ng} angle pairs, <C> range over grid: "
      f"[{min(qaoa_expect(2*math.pi*a/nb, 2*math.pi*b/ng)[0] for a in range(nb) for b in range(ng)):.4f}, {C:.4f}]")
beta, gamma = 2 * math.pi * best[1] / nb, 2 * math.pi * best[2] / ng
print(f"best angles: beta = {beta:.4f} rad, gamma = {gamma:.4f} rad")
print(f"best <C> = {C:.4f}  (uniform random baseline 2.5000, MaxCut {best_cut}, ratio {C/best_cut:.4f})")
_, v = qaoa_expect(beta, gamma)
for x in sorted(opts):
    print(f"  P(optimal {part(x)}) = {abs(v[x])**2:.4f}")
avg_opt_prob = sum(abs(v[x])**2 for x in opts)
print(f"total probability on the 2 optimal bitstrings: {avg_opt_prob:.4f}")
print("landscape samples <C>(beta, gamma): " +
      ", ".join(f"({2*math.pi*a/nb:.2f},{2*math.pi*b/ng:.2f}):{qaoa_expect(2*math.pi*a/nb, 2*math.pi*b/ng)[0]:.3f}"
                for a, b in [(0, 6), (6, 12), (12, 24), (24, 48), (6, 30)]))
cum, acc = [], 0.0
for x in range(N):
    acc += abs(v[x]) ** 2
    cum.append(acc)
rnd = random.Random(7)                      # deterministic shot sampler
hist, best_found = {}, 0
for _ in range(200):
    r = rnd.random()
    x = next(i for i in range(N) if r <= cum[i])
    c = cost(x)
    best_found = max(best_found, c)
    hist[c] = hist.get(c, 0) + 1
print(f"200 shots at the best angles: best cut found = {best_found}, "
      f"histogram: " + ", ".join(f"cut {c}: {hist.get(c, 0)}" for c in sorted(hist)))
```

Output:

```text
brute force over all 16 cuts: MaxCut = 4 of 5 edges
optimal partitions (bit x encodes node side): A={1,3} B={0,2}; A={0,2} B={1,3}
grid scan 48x96 = 4608 angle pairs, <C> range over grid: [0.8899, 3.2173]
best angles: beta = 6.0214 rad, gamma = 5.6941 rad
best <C> = 3.2173  (uniform random baseline 2.5000, MaxCut 4, ratio 0.8043)
  P(optimal A={1,3} B={0,2}) = 0.1573
  P(optimal A={0,2} B={1,3}) = 0.1573
total probability on the 2 optimal bitstrings: 0.3145
landscape samples <C>(beta, gamma): (0.00,0.39):2.500, (0.79,0.79):1.543, (1.57,1.57):2.500, (3.14,3.14):2.500, (0.79,1.96):3.028
200 shots at the best angles: best cut found = 4, histogram: cut 0: 2, cut 2: 12, cut 3: 132, cut 4: 54
```

Read the last line carefully -- it contains the whole QAOA story. The optimized expectation (3.217) is far below MaxCut (4), yet 200 shots still surface the optimal cut 54 times because the distribution concentrates on good strings; the metric you optimize is not the quantity you ship. Also note the flat points in the landscape (beta = 0 or gamma = 0 reproduce the trivial 2.5 baseline): p = 1 landscapes are riddled with degenerate ridges, which is exactly where the concentration result of Brandao et al. bites.

## Interview angle

> **"Why can VQE run on today's hardware when phase estimation cannot?"**

VQE replaces coherent quantum depth with classical repetition: short ansatz circuits, many shots, and a classical optimizer. Phase estimation needs the Hamiltonian evolution applied coherently for time proportional to 1/eps plus an inverse QFT -- millions of high-fidelity logical gates that only error-corrected hardware provides. The price VQE pays is precision (1/eps^2 shots instead of 1/eps depth), no eigenvalue certificate, and dependence on ansatz expressibility.

> **"Your VQE run will not converge below some energy. Diagnose it."**

In order: (1) shot-noise floor -- estimate the 1/sqrt(S) error bar and check the gap against it; (2) ansatz expressibility -- is the variational minimum of your ansatz class known to sit above E0? (3) trainability -- measure gradient variance across parameter resets; a vanishing spread means a barren plateau, so shallow the circuit or switch to a problem-inspired ansatz; (4) noise bias -- compare zero-noise-extrapolated energies at different amplification factors; (5) optimizer budget -- plot energy per iteration and confirm the classical loop, not the hardware, is the bottleneck.

## References

1. A. Peruzzo et al. "A variational eigenvalue solver on a photonic quantum processor." Nature Communications 5:4213, 2014. <https://doi.org/10.1038/ncomms5213>
2. P. J. J. O'Malley et al. "Scalable Quantum Simulation of Molecular Energies." Phys. Rev. X 6:031007, 2016. <https://doi.org/10.1103/PhysRevX.6.031007> (preprint: <https://arxiv.org/abs/1512.06860>; Table I supplies the demo coefficients)
3. A. Kandala et al. "Hardware-efficient variational quantum eigensolver for small molecules and quantum magnets." Nature 549:242-246, 2017. <https://doi.org/10.1038/nature23879>
4. H. R. Grimsley et al. "An adaptive variational algorithm for exact molecular simulations on a quantum computer." Nature Communications 10:3007, 2019. <https://doi.org/10.1038/s41467-019-10988-2>
5. E. Farhi, J. Goldstone, S. Gutmann. "A Quantum Approximate Optimization Algorithm." 2014. <https://arxiv.org/abs/1411.4028>
6. F. G. S. L. Brandao, M. Broughton, E. Farhi, S. Gutmann, H. Neven. "For Fixed Control Parameters the Quantum Approximate Optimization Algorithm's Objective Function Value Concentrates for Typical Instances." <https://arxiv.org/abs/1812.04170>
7. J. R. McClean, S. Boixo, V. N. Smelyanskiy, R. Babbush, H. Neven. "Barren plateaus in quantum neural network training landscapes." Nature Communications 9:4812, 2018. <https://doi.org/10.1038/s41467-018-07090-4>
8. S. Wang et al. "Noise-induced barren plateaus in variational quantum algorithms." Nature Communications 12:6961, 2021. <https://doi.org/10.1038/s41467-021-27045-6> (preprint: <https://arxiv.org/abs/2007.14384>)
9. K. Mitarai, M. Negoro, M. Kitagawa, K. Fujii. "Quantum circuit learning." Phys. Rev. A 98:032309, 2018. <https://arxiv.org/abs/1803.00745>
10. M. Schuld, V. Bergholm, C. Gogolin, J. Izaac, N. Killoran. "Evaluating analytic gradients on quantum hardware." Phys. Rev. A 99:032331, 2019. <https://arxiv.org/abs/1811.11184>
11. M. Cerezo et al. "Variational quantum algorithms." Nature Reviews Physics 3:625-644, 2021. <https://doi.org/10.1038/s42254-021-00348-9>
12. J. Preskill. "Quantum Computing in the NISQ era and beyond." Quantum 2:79, 2018. <https://arxiv.org/abs/1801.00862>
