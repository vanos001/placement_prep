# Quantum Fundamentals

## Overview

Quantum computing leverages the principles of quantum mechanics—superposition, entanglement, and interference—to perform computations that are intractable for classical computers for certain problems. This chapter builds the conceptual and mathematical foundations needed to understand quantum algorithms.

## Qubits

A **qubit** is the quantum analog of a classical bit. While a classical bit is definitively 0 or 1, a qubit exists in a superposition:

```
|ψ⟩ = α|0⟩ + β|1⟩

where |α|² + |β|² = 1
|α|² = probability of measuring |0⟩
|β|² = probability of measuring |1⟩
```

The state |ψ⟩ is a vector in a two-dimensional complex vector space (Hilbert space). The computational basis states are:

```
|0⟩ = [1]    |1⟩ = [0]
       [0]          [1]
```

A qubit can be physically realized using superconducting circuits (transmons), trapped ions, photonic qubits, or topological qubits. Each technology trades off coherence time, gate fidelity, and scalability.

## Bloch Sphere

Any single-qubit pure state can be visualized on the **Bloch sphere**:

```
|ψ⟩ = cos(θ/2)|0⟩ + e^(iφ)sin(θ/2)|1⟩

          |0⟩
           |
           | (θ, φ)
        •/ \
       /     \
      /   •   \
     |    |ψ⟩  |
      \       /
       \_____/
           |
          |1⟩
```

- **θ (polar angle)**: controls the |0⟩/|1⟩ mixture (0 = pure |0⟩, π = pure |1⟩)
- **φ (azimuthal angle)**: controls the relative phase
- Points on the equator: equal superposition with different phases
- The Bloch sphere is a powerful intuition tool but does not generalize directly to multi-qubit states

## Quantum Gates

Quantum gates are **unitary matrices** acting on qubit states. Unitarity preserves the normalization condition |α|² + |β|² = 1.

### Single-Qubit Gates

| Gate | Matrix | Effect |
|------|--------|--------|
| X (NOT) | [[0,1],[1,0]] | Flips |0⟩↔|1⟩ |
| H (Hadamard) | 1/√2 [[1,1],[1,-1]] | Creates equal superposition |
| Z (Phase) | [[1,0],[0,-1]] | Applies π phase to |1⟩ |
| S | [[1,0],[0,i]] | π/2 phase gate |
| T | [[1,0],[0,e^(iπ/4)]] | π/4 phase gate (universal with H+CNOT) |
| Rz(θ) | [[1,0],[0,e^(iθ)]] | Arbitrary phase rotation |
| Rx(θ), Ry(θ) | Rotation matrices | Bloch sphere rotations around x/y axes |

The **Hadamard gate** is particularly important: H|0⟩ = (|0⟩+|1⟩)/√2 creates a uniform superposition, and H is its own inverse (H² = I).

### Multi-Qubit Gates

| Gate | Action | Importance |
|------|--------|------------|
| CNOT (CX) | Flips target qubit if control is |1⟩ | Entanglement, universal with single-qubit gates |
| Toffoli (CCX) | Flips target if both controls are |1⟩ | Reversible AND; universal for classical reversible computing |
| SWAP | Exchanges two qubit states | Useful in circuit optimization |
| CZ | Applies Z to target if control is |1⟩ | Alternative entangling gate |

**Universality**: any quantum computation can be decomposed into a sequence of single-qubit rotations + CNOT gates (or any other entangling two-qubit gate). This is analogous to NAND-universality in classical computing.

## Quantum Circuits

A quantum circuit is a sequence of gates applied to qubits, read left to right:

```
q0: ──H────■─────
              │
q1: ────H────X─────

1. Apply H to q0  → superposition
2. Apply H to q1  → superposition
3. Apply CNOT(q0, q1) → creates Bell state (|00⟩+|11⟩)/√2
```

Circuit depth = number of sequential gate layers. Width = number of qubits. Minimizing depth is critical for NISQ devices where coherence time limits circuit length.

## Measurement

Measurement in the computational basis **collapses** the quantum state:

```
Measure |ψ⟩ = α|0⟩ + β|1⟩:
  → Result 0 with probability |α|², state collapses to |0⟩
  → Result 1 with probability |β|², state collapses to |1⟩
```

**No-cloning theorem**: it is impossible to create an identical copy of an arbitrary unknown quantum state. This has profound implications for quantum information processing and security.

## Entanglement & Bell States

**Entanglement** is a correlation between qubits that has no classical analog. Two qubits are entangled if their joint state cannot be factored into individual qubit states.

The four **Bell states** (maximally entangled two-qubit states):

```
|Φ+⟩ = (|00⟩ + |11⟩)/√2
|Φ-⟩ = (|00⟩ - |11⟩)/√2
|Ψ+⟩ = (|01⟩ + |10⟩)/√2
|Ψ-⟩ = (|01⟩ - |10⟩)/√2
```

Created by: H on first qubit → CNOT. Measuring one qubit of a Bell state instantaneously determines the other, regardless of distance. This is not "faster-than-light communication" because individual measurement outcomes are random—only the correlation is revealed when classical information is exchanged.

## Quantum Teleportation

Quantum teleportation transmits an unknown qubit state using only classical communication and pre-shared entanglement:

```
Alice has: |ψ⟩ (unknown state)
Alice and Bob share: Bell pair (|00⟩+|11⟩)/√2

1. Alice applies CNOT(|ψ⟩, Alice's half of Bell pair)
2. Alice applies H to |ψ⟩
3. Alice measures both qubits → 2 classical bits (00, 01, 10, 11)
4. Alice sends 2 bits to Bob
5. Bob applies corrections based on received bits:
   00 → I, 01 → X, 10 → Z, 11 → XZ

Bob now has |ψ⟩. Original |ψ⟩ is destroyed (no-cloning).
```

Teleportation is a fundamental primitive for quantum networking and distributed quantum computation.

## Superdense Coding

Superdense coding is the dual of teleportation: using one entangled qubit pair + one qubit of quantum communication to transmit **two classical bits**:

- Alice and Bob share a Bell pair
- Alice applies one of four gates (I, X, Z, XZ) to her qubit based on her 2-bit message (00, 01, 10, 11)
- Alice sends her qubit to Bob
- Bob performs a Bell measurement on both qubits to decode the 2-bit message

Where teleportation uses 2 classical bits to send 1 qubit, superdense coding uses 1 qubit to send 2 classical bits.

## Key Quantum Algorithms

### Deutsch & Deutsch-Jozsa

**Deutsch problem**: given a function f: {0,1} → {0,1}, determine if f is constant (same output for all inputs) or balanced (outputs differ) using **one** query. Classically requires two queries.

**Deutsch-Jozsa**: generalizes to f: {0,ⁿ} → {0,1}. Quantum: 1 query. Classical worst case: 2^(n-1) + 1 queries.

While the speedup is impressive, the problem itself is contrived—it served as a proof-of-concept that quantum algorithms could outperform classical ones exponentially for specific tasks.

### Bernstein-Vazirani

Given a function f(x) = a·x mod 2 (where a is a hidden n-bit string), find a with **one** quantum query. Classically requires n queries. This demonstrates the ability to extract a hidden structure with a single application of a quantum oracle.

### Simon's Algorithm

Given a function f: {0,1}ⁿ → {0,1}ⁿ with the promise that f(x) = f(x⊕s) for some hidden s ≠ 0ⁿ, find s.

- **Quantum**: O(n) queries
- **Classical**: Ω(2^(n/2)) queries

Simon's algorithm was the first to demonstrate an exponential quantum advantage for a problem with a clear black-box separation. It inspired Shor's algorithm.

### Grover's Search

**Unstructured search**: given an unstructured database of N items and a black-box function that identifies the target, find it.

- **Classical**: O(N) queries
- **Quantum**: O(√N) queries (quadratic speedup)

Grover's algorithm uses amplitude amplification: repeatedly apply the "oracle" (marking the target) and the "diffusion operator" (inverting about the mean) to amplify the target's amplitude.

```
Amplitude amplification:
1. Start in uniform superposition: all N states have amplitude 1/√N
2. Oracle: flip the sign of the target state
3. Diffusion: reflect about the mean amplitude
4. Repeat ~√(N/4) times
5. Measure: high probability of getting the target
```

Grover's algorithm is **optimal**—no quantum algorithm can do unstructured search in fewer than Ω(√N) queries (the BBBV lower bound; O(√N) is what Grover achieves, matching the bound up to constants). It has practical applications for NP problems where quantum computers can achieve quadratic speedup (e.g., SAT solving, graph coloring).

### Shor's Factoring Algorithm

**Integer factorization**: given N, find a non-trivial factor.

- **Classical best known**: sub-exponential (general number field sieve)
- **Quantum**: O((log N)³) polynomial time

Shor's algorithm combines:

1. **Quantum period finding**: find the period r of the function f(x) = a^x mod N (using QFT)
2. **Classical post-processing**: if r is even and a^(r/2) ≢ -1 mod N, then gcd(a^(r/2) ± 1, N) yields a factor

The **Quantum Fourier Transform (QFT)** is the core subroutine:

```
QFT|j⟩ = (1/√N) Σ_k e^(2πijk/N) |k⟩

Circuit: O(n²) Hadamard + controlled phase gates for n-qubit register
Can be simplified to O(n log n) with approximation
```

Shor's algorithm breaks RSA, ECC, and Diffie-Hellman—essentially all widely deployed public-key cryptography. This is the primary motivation for **post-quantum cryptography** (lattice-based, hash-based, code-based schemes).

### QFT & Phase Estimation

**Quantum Phase Estimation (QPE)** estimates the phase φ of an eigenvalue e^(2πiφ) of a unitary operator U:

- Uses two registers: one for the eigenstate, one for phase estimation
- Applies controlled-U^(2^j) operations with inverse QFT
- Accuracy: n-bit phase estimate with n ancilla qubits

QPE is the foundation for Shor's algorithm and many quantum chemistry and optimization algorithms (VQE, QAOA use variational approximations because QPE requires fault-tolerant quantum computers).

## Interview Angle

> **"Explain quantum entanglement to a software engineer."**

Entanglement means two qubits share a joint state that cannot be described independently. Measuring one immediately constrains the other's state—like two dice that are magically linked so that if you roll a 6 on one, the other is guaranteed to be a 6. However, you cannot control *which* value you get (random outcome), so you can't send information faster than light. The correlation only becomes useful when you compare results classically.

> **"Why can't Shor's algorithm run on today's quantum computers?"**

Shor's algorithm requires thousands of error-corrected qubits (logical qubits) and deep circuits with millions of gates. Current NISQ (Noisy Intermediate-Scale Quantum) devices have 50–1000 noisy physical qubits with coherence times too short for the required circuit depth. Fault-tolerant quantum computing—using quantum error correction to create reliable logical qubits from many noisy physical ones—is not yet achieved at scale.

## Key References

- Nielsen & Chuang, "Quantum Computation and Quantum Information" (2010)
- Shor, "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer" (1994)
- Grover, "A Fast Quantum Mechanical Algorithm for Database Search" (1996)
- IBM Qiskit Textbook (qiskit.org/textbook)
- Kaye, Laflamme, Mosca, "An Introduction to Quantum Computing" (2007)
