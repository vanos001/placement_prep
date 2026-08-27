# Quantum Error Correction: Making One Good Qubit Out of Many Bad Ones

A classical bit survives anywhere a voltage survives. A qubit is a coherent
superposition that decoheres whenever the environment learns anything about it:
superconducting qubits hold their state for roughly 100 microseconds and the best
two-qubit gates fail about once per thousand operations. Circuits beyond a few
thousand gates therefore almost surely accumulate an error before finishing,
which is why quantum error correction (QEC) - encoding one logical qubit across
many entangled physical qubits - gates everything else. This page goes one level
below the [Quantum Advanced Topics](./quantum-advanced.md) survey: the mechanics
of syndrome extraction, the code families, the threshold math, and the December
2024 result that pushed the field across its most important line. Qubit and
Bloch-sphere basics live in [Quantum Fundamentals](./quantum-fundamentals.md).

## Why You Cannot Just Copy Three Times

Classical redundancy says: store three copies, take a majority vote. Quantum
mechanics kills this twice over.

**No-cloning.** No unitary U satisfies U(|psi>|0>) = |psi>|psi> for arbitrary
unknown |psi>. Cloning would have to preserve inner products, so from
U(|+>|0>) = |+>|+> and U(|->|0>) = |->|-> we would need <+|-> = <+|->^2 - but
0 = 0 only accidentally; for any non-orthogonal pair the required map shrinks
the inner product and is not unitary (Wootters & Zurek, 1982). An unknown state
cannot be copied - and cannot even be inspected for damage, since measuring it
collapses it.

**The escape.** Encode so that (a) individual physical errors do not touch the
logical information and (b) there exist measurements whose outcome depends on
*which error occurred* but not on *which amplitudes* the logical qubit carries.
Those measurements are the stabilizers, and measuring them collapses only
sacrificial ancilla qubits.

## The 3-Qubit Bit-Flip Code

Encode alpha|0> + beta|1> as alpha|000> + beta|111>, protected by two parity
checks (stabilizers): Z1Z2 (do qubits 1 and 2 agree?) and Z2Z3. The stabilizers
act as +1 on the entire code space, so measuring them on undamaged data always
returns +1 - the measurement is guaranteed to reveal nothing about alpha and
beta. An error that anticommutes with a stabilizer flips that outcome to -1, and
the pattern of flips (the *syndrome*) names the culprit:

| Syndrome (Z1Z2, Z2Z3) | Inferred error | Recovery   |
|-----------------------|----------------|------------|
| (+1, +1)              | none           | do nothing |
| (-1, +1)              | X on qubit 1   | flip qubit 1 |
| (-1, -1)              | X on qubit 2   | flip qubit 2 |
| (+1, -1)              | X on qubit 3   | flip qubit 3 |

The (+1, +1) case cannot distinguish "no error" from "two errors", so the code
fails on 2 or more simultaneous flips. With independent flip probability p per
qubit, logical failure is 3p^2 - 2p^3, which beats the raw qubit's p exactly
when p < 1/3 - and for small p the win is quadratic: 1% raw becomes ~0.03%
logical (the runnable simulation below reproduces both facts). The gap this
code leaves: a phase flip (Z error) rotates the sign of beta and is invisible
to Z-parity checks. Fixing that took one more idea.

## CSS Codes and the Stabilizer Formalism

Calderbank, Shor, and Steane (1996) showed that two classical codes C1 and C2
with C2-perp contained in C1 combine into a quantum code whose bit-flip (X) and
phase-flip (Z) errors are detected by *separate classical decoders*. The CSS
[[n, k, d]] family corrects any error on up to floor((d-1)/2) qubits; canonical
examples are the Steane code [[7,1,3]] (from the classical [7,4] Hamming code)
and Shor's [[9,1,3]] nine-qubit code. Gottesman's stabilizer formalism (1997)
generalizes: a code is an Abelian subgroup of the n-qubit Pauli group with n-k
independent commuting generators; the code space is their joint +1 eigenspace
(dimension 2^k); every error either commutes with all generators (harmless or a
logical operator) or anticommutes with exactly the subset that forms its
syndrome.

The measurement mechanics deserve a picture, because "measure without collapsing
the data" is the heart of the field:

```text
syndrome extraction for Z1Z2 (bit-flip parity of qubits 1 and 2)

  data q1:  |psi> ----*-------------------  control
                      |
  data q2:  |psi> ----|---*---------------  control
                      |   |
  ancilla:  |0> ------X---X----[measure]--  ancilla = q1 XOR q2

  outcome 0  ->  Z1Z2 = +1   even parity: no flip, or both flipped
  outcome 1  ->  Z1Z2 = -1   odd parity : exactly one of q1, q2 flipped
```

The ancilla starts in |0>, accumulates the parity via CNOTs, and is measured.
Only the ancilla collapses - the data amplitudes are never queried. Repeat for
every stabilizer and you get a classical bit string that a classical decoder
turns into a recovery operation.

## The Surface Code and the Threshold

The [advanced survey](./quantum-advanced.md) shows the lattice layout; the
engineering-critical part is the accounting. The surface code is a CSS code on a
2D grid needing only nearest-neighbor interactions - the one layout that matches
chip fabrication. A distance-d rotated surface code uses d^2 data qubits and
d^2 - 1 syndrome qubits, which is where the "roughly 2d^2 physical qubits per
logical qubit" rule of thumb comes from:

| Distance d | Data (d^2) | Syndrome (d^2-1) | Total (~2d^2) | Correctable errors (d-1)/2 |
|------------|------------|------------------|---------------|----------------------------|
| 3          | 9          | 8                | 17            | 1                          |
| 5          | 25         | 24               | 49            | 2                          |
| 7          | 49         | 48               | 97            | 3                          |
| 11         | 121        | 120              | 241           | 5                          |
| 21         | 441        | 440              | 881           | 10                         |
| 27         | 729        | 728              | 1457          | 13                         |

(Google's distance-7 Willow memory used 101 physical qubits - right at the 2d^2
estimate.) Each added distance layer costs ~4x the qubits but suppresses the
logical error rate exponentially, *provided* the physical error rate p is below
the threshold p_th. Fowler et al. (PRA 2012) worked the full circuit-level noise
model and put the surface-code threshold just under 1% - quoted as "about 1%",
the highest of any practical code, which is why superconducting hardware settled
on it. Below threshold, a widely used empirical fit from that paper is
p_L = 0.1 * (100*p)^((d+1)/2). The cliff is brutal near threshold: the
simulation at the end of this page evaluates the fit and finds that one logical
qubit at a 1e-12 error rate costs ~3,700 physical qubits at p = 0.3% but
~103,000 at p = 0.8%. Halving hardware error is worth tens of thousands of
qubits; that single fact organizes the industry roadmap.

## Below Threshold, on Real Hardware

December 2024 is when the threshold concept stopped being theoretical. Google's
Willow chip (105 qubits) ran distance-5 and distance-7 surface-code memories
with a real-time decoder and reported in Nature: logical error suppression by a
factor Lambda = 2.14 +/- 0.02 per distance-2 step (the exponential suppression
that defines "below threshold", measured on hardware); 0.143% +/- 0.003% error
per 1.1-microsecond cycle for the 101-qubit distance-7 memory; and - beyond
break-even - a logical qubit outliving its best physical qubit by 2.4x +/- 0.3.
The real-time decoder held 63-microsecond average latency across a million
cycles; repetition-code runs up to distance 29 exposed rare correlated error
events (~once per hour) as the next bottleneck.

Neutral atoms are the second front: Bluvstein et al. (Nature, 2024) ran a
logical processor on up to 280 reconfigurable atom-array qubits, improved a
logical gate by scaling surface-code distance from 3 to 7, and operated 40
colour-code logical qubits at break-even fidelity. Microsoft's program takes a
different route - topological qubits plus high-distance codes on trapped-ion
hardware - and reports logical error rates orders of magnitude below physical
ones. The platforms disagree on the qubit; all route through the stabilizer
formalism above.

## Lattice Surgery

Fowler's 2012 framework moved logical qubits by braiding defects; modern scaling
plans mostly use lattice surgery. Two logical patches are *merged* by measuring
the joint stabilizer of the seam qubits - directly measuring the parity
Z_L x Z_L or X_L x X_L of the two logical qubits - then *split* again. A logical
CNOT is two parity measurements plus a Hadamard. Surgery needs no braided
corridors and stays in one flat 2D layer (Google's resource projections assume
it); the cost is extra cycles, which surface as slower logical clock speeds.

## What Interviews Actually Ask

> "Why can't we just back up a qubit like a classical bit?"

No unitary can copy an unknown state (no-cloning), and any direct measurement
collapses the superposition you are protecting. QEC sidesteps both by measuring
parity operators that act as +1 on the whole code space: you learn which error
happened, never which state you are in.

> "What is the threshold theorem, in one breath?"

Below a code-specific threshold (~1% for the surface code), increasing code
distance suppresses logical error exponentially, so arbitrarily reliable
computation is possible at finite polynomial overhead; above it, adding qubits
makes things worse - which is why "did you beat threshold?" is THE 2024+
milestone question.

## Run It Yourself

Classical simulation: Monte Carlo of the 3-qubit bit-flip code over independent
X errors, plus an evaluation of the Fowler distance formula.

```python
# Classical simulation of the 3-qubit bit-flip repetition code.
# Qubit Z-basis values are modeled as bits; an X error is a bit flip.
import random

def syndrome(bits):
    # Z1Z2 and Z2Z3 parities: differing bits -> that stabilizer returned -1
    return (bits[0] ^ bits[1], bits[1] ^ bits[2])

def recover(bits):
    table = {(1, 0): 0, (1, 1): 1, (0, 1): 2}   # syndrome -> qubit to flip
    s = syndrome(bits)
    if s == (0, 0):
        return bits
    i = table[s]
    return bits[:i] + (bits[i] ^ 1,) + bits[i + 1:]

def trial(p, protect):
    b = random.randint(0, 1)
    if protect:
        bits = recover(tuple(x ^ 1 if random.random() < p else x for x in (b, b, b)))
        return (sum(bits) >= 2) != b            # majority vote, compare
    return (b ^ 1 if random.random() < p else b) != b   # raw qubit

N = 200_000
random.seed(7)
print(f"{'p':>5} {'raw qubit':>10} {'3-qubit code':>13} {'3p^2-2p^3':>10}")
for p in (0.01, 0.05, 0.10, 0.15, 0.20):
    raw = sum(trial(p, False) for _ in range(N)) / N
    enc = sum(trial(p, True) for _ in range(N)) / N
    print(f"{p:5.2f} {raw:10.4f} {enc:13.4f} {3*p*p - 2*p**3:10.4f}")

print("\nFowler et al. 2012 fit  p_L = 0.1 * (100*p)^((d+1)/2),  p_th = 1%")
print("distance d needed for logical error <= 1e-12 per round:")
for p in (0.008, 0.005, 0.003):
    d = 3
    while 0.1 * (100 * p) ** ((d + 1) / 2) > 1e-12:
        d += 2
    print(f"  p = {p*100:4.1f}%  ->  d = {d:3d}  (~{2*d**2:6d} physical qubits at 2d^2)")
```

Output (Python 3.11, seed fixed):

```text
    p  raw qubit  3-qubit code  3p^2-2p^3
 0.01     0.0101        0.0003     0.0003
 0.05     0.0500        0.0072     0.0073
 0.10     0.0992        0.0282     0.0280
 0.15     0.1493        0.0600     0.0607
 0.20     0.2000        0.1039     0.1040

Fowler et al. 2012 fit  p_L = 0.1 * (100*p)^((d+1)/2),  p_th = 1%
distance d needed for logical error <= 1e-12 per round:
  p =  0.8%  ->  d = 227  (~103058 physical qubits at 2d^2)
  p =  0.5%  ->  d =  73  (~ 10658 physical qubits at 2d^2)
  p =  0.3%  ->  d =  43  (~  3698 physical qubits at 2d^2)
```

The first table is the quadratic-suppression lesson (raw 1% -> encoded 0.03%,
a 30x win); the last block is the threshold lesson. Everything here is
classical, which is why [the Qiskit textbook](https://github.com/Qiskit/qiskit-textbook/blob/main/content/ch-quantum-hardware/error-correction-repetition-code.ipynb)
teaches QEC with exactly this code. For scale: Gidney & Ekera estimate factoring
RSA-2048 at ~20 million noisy physical qubits over 8 hours
([arXiv:1905.09749](https://arxiv.org/abs/1905.09749)).

## References

- Fowler et al., "Surface codes: Towards practical large-scale quantum
  computation", Phys. Rev. A 86, 032324 (2012) - https://arxiv.org/abs/1208.0928
- Google Quantum AI, "Quantum error correction below the surface code threshold",
  Nature 638, 920-926 - https://www.nature.com/articles/s41586-024-08449-y
- Google, "Meet Willow, our state-of-the-art quantum chip" -
  https://blog.google/innovation-and-ai/technology/research/google-willow-quantum-chip/
- Bluvstein et al., "Logical quantum processor based on reconfigurable atom
  arrays", Nature 626, 58-65 (2024) -
  https://www.nature.com/articles/s41586-023-06927-3
- Qiskit Textbook, "Error Correction with the Repetition Code" -
  https://github.com/Qiskit/qiskit-textbook/blob/main/content/ch-quantum-hardware/error-correction-repetition-code.ipynb

Book: Nielsen & Chuang, "Quantum Computation and Quantum Information" (10th
anniversary ed., Cambridge UP) - chapters 10-11 for QEC and stabilizers in full.
