# Complexity Classes

## P (Polynomial Time)

Decision problems solvable by a deterministic Turing machine in O(n^k) time.

**Examples in P**:
- Sorting (O(n log n))
- Shortest path — Dijkstra (O((V+E) log V))
- Maximum flow (O(VE²))
- Primality testing (AKS: O(n^12))
- Linear programming

## NP (Nondeterministic Polynomial Time)

Decision problems where a "yes" answer can be **verified** in polynomial time given a certificate (witness).

**Key insight**: P ⊆ NP (if you can solve it, you can verify it).

**Examples in NP**:
- SAT (given an assignment, verify it satisfies the formula)
- Hamiltonian path (given a path, verify it visits all vertices)
- Graph coloring (given a coloring, verify no adjacent same color)
- Subset sum (given a subset, verify it sums to target)
- Traveling salesman (given a tour, verify it's ≤ k)

## NP-Complete

A problem L is NP-complete if:
1. L ∈ NP
2. Every problem in NP is polynomial-time reducible to L

**Implication**: If ANY NP-complete problem is in P, then P = NP.

### Classic NP-Complete Problems

| Problem | Input | Question |
|---|---|---|
| SAT | Boolean formula | Is it satisfiable? |
| 3-SAT | 3-CNF formula | Is it satisfiable? |
| Vertex Cover | Graph G, integer k | Cover of size ≤ k? |
| Clique | Graph G, integer k | Complete subgraph of size k? |
| Independent Set | Graph G, integer k | Independent set of size k? |
| Hamiltonian Path | Graph G | Path visiting all vertices? |
| TSP | Graph G, integer k | Tour of cost ≤ k? |
| Subset Sum | Set S, target t | Subset summing to t? |
| 3-Coloring | Graph G | Colorable with 3 colors? |

### Polynomial-Time Reductions

To prove problem B is NP-complete:
1. Show B ∈ NP
2. Pick a known NP-complete problem A
3. Show A ≤_p B (polynomial reduction from A to B)
4. Conclude B is NP-complete

## NP-Hard

Problems at least as hard as NP-complete, but not necessarily in NP.

**Examples**: Halting problem (undecidable), optimization versions of NP-complete problems.

## NP vs co-NP

- **NP**: "yes" answers have short proofs
- **co-NP**: "no" answers have short proofs
- Example: UNSAT (formula is unsatisfiable) is in co-NP
- Open question: NP = co-NP?

## Relationship Diagram

```
┌──────────────────────────────────────┐
│              NP-Hard                 │
│                                      │
│    ┌──────────────────────────┐      │
│    │          NP              │      │
│    │  ┌──────────────────┐    │      │
│    │  │   NP-Complete    │    │      │
│    │  │  (SAT, TSP-dec)  │    │      │
│    │  └──────────────────┘    │      │
│    │  ┌──────────────────┐    │      │
│    │  │        P         │    │      │
│    │  │ (Sort, Shortest  │    │      │
│    │  │  Path)           │    │      │
│    │  └──────────────────┘    │      │
│    └──────────────────────────┘      │
│                                      │
│  (NP-Hard problems outside NP, e.g.  │
│   Halting Problem, are in the        │
│   NP-Hard region but NOT in NP)      │
└──────────────────────────────────────┘

Note: NP-Hard is NOT a superset of NP. NP-Hard problems are "at least
as hard as the hardest NP problems." Some NP-Hard problems are in NP
(these are NP-Complete), and some are outside NP (e.g. undecidable
problems like the Halting Problem). The intersection of NP and NP-Hard
is exactly NP-Complete.
```

Unknown: P = NP?  (million-dollar question)

## PSPACE

Problems solvable with polynomial space (no time limit).

P ⊆ NP ⊆ PSPACE

PSPACE-complete: QBF (Quantified Boolean Formula)

## Approximation Algorithms

For NP-hard optimization problems:

| Problem | Approximation Ratio |
|---|---|
| Vertex Cover | 2-approx |
| TSP (metric) | 3/2-approx (Christofides) |
| Set Cover | O(ln n)-approx |
| Max Cut | 0.878-approx (SDP) |

## Interview Questions

**Q: What is the difference between P and NP?**
A: P = problems solvable in polynomial time. NP = problems where solutions can be verified in polynomial time. Every P problem is in NP, but whether NP problems are in P is the million-dollar P vs NP question.

**Q: What does NP-complete mean?**
A: A problem that is (1) in NP (solution verifiable in polynomial time) and (2) at least as hard as every other NP problem (all NP problems reduce to it). If any NP-complete problem is in P, then P = NP.

**Q: Is P = NP? Why does it matter?**
A: Unknown (one of the Millennium Prize Problems). If P = NP, many "hard" problems (cryptography, optimization, AI) would become efficiently solvable. Most computer scientists believe P ≠ NP.

**Q: How do you prove a problem is NP-complete?**
A: (1) Show it's in NP (verify solution in polynomial time), (2) pick a known NP-complete problem, (3) reduce it to your problem in polynomial time, (4) conclude NP-completeness.

## References

- [Introduction to Algorithms — CLRS](https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/)
- [Computational Complexity — Arora & Barak](http://theory.cs.princeton.edu/complexity/)
- [Clay Mathematics — P vs NP](https://www.claymath.org/millennium-problems/p-vs-np-problem)
