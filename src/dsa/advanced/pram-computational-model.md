# The PRAM Model: Parallel Computation as Theory

Every interview answer about parallelism leans, knowingly or not, on a machine that nobody ever built: the Parallel Random Access Machine. A PRAM is the RAM of classical algorithm analysis with many processors bolted on - P processors, one shared memory, and a clock that ticks in lockstep, each step letting every processor read or write one shared word and do one unit of local computation. Communication is free, synchronization is free, caches do not exist. That set of deliberately absurd assumptions is what makes the model useful: it isolates the question "does this algorithm expose *algorithmic* parallelism at all?" from the engineering question "how fast is memory access on real silicon?" - the same separation of concerns that work-span analysis brings to [parallel sorting](./parallel-sorting.md).

The model earned its keep twice. In the 1980s it was the arena where the theory of parallel algorithms was built: list ranking, connectivity, maxima, sorting, and the complexity class NC were all defined and mined there. When the PRAM failed as a hardware blueprint - real machines charge dearly for communication - its *accounting* survived: work (total operations) and depth (longest dependency chain) remain the first-order metrics reported by every parallel-algorithms paper and every serious parallel library, and Brent's theorem remains the bridge from those two numbers to a predicted runtime on P processors. This page walks the machine, its variants, the two results that carry all the weight (Brent's theorem and pointer jumping), the class NC, and what survived the model's fall into real GPUs and multicore schedulers.

## The machine and its one design decision

A PRAM program is a sequence of synchronized rounds. In a round, each of P processors may compute with its private registers, read one shared cell, or write one shared cell. The only genuinely consequential design decision is what happens when several processors touch the *same* cell in the same round. Everything else about the model - unit time, lockstep, unbounded memory - is cosmetic by comparison, because it only rescales constants; the conflict policy changes which algorithms exist at all.

```text
        P0        P1        P2       ...     P(P-1)
         |         |         |                 |      private registers
         v         v         v                 v
    +-------------------------------------------------+
    |        shared global memory, unit-time          |
    |        read/write of any word, lockstep         |
    +-------------------------------------------------+
    one round = each processor computes / reads / writes one word

    EREW : no two processors may touch the same cell in a round
    CREW : any number may read the same cell; writes stay exclusive
    CRCW : reads and writes may conflict; a rule picks the write winner
```

The acronyms read Exclusive-or-Concurrent separately for reads and writes: EREW, CREW, ERCW (rarely used), and CRCW. For CRCW the model must also state a **write arbitration rule** - the classical three are **common** (concurrent writers must all write the same value, which then lands), **arbitrary** (some unspecified contender wins), and **priority** (the lowest-numbered processor among the writers wins). Vishkin's monograph, which this page follows for all technical statements, additionally proves that the resulting machine hierarchy is strict - priority-CRCW is the most powerful, then arbitrary, then common, then CREW, and EREW is the weakest - while formal simulations show the whole family differs by at most a logarithmic factor in processor count, so algorithms can be designed in whichever rule is convenient and ported across the spectrum at a bounded cost.

The porting cost is worth demystifying because its mechanism is the same two-stage trick everywhere. To simulate a round of concurrent accesses on an EREW machine with P processors, stage the reads first: each distinct cell is read once and broadcast through a copy tree, so n reads to one cell cost O(log n) depth instead of one step. Then stage the writes: concurrent writes to a cell are collected into one location and resolved by sorting or a small reduction, which implements the common, arbitrary, or priority rule with the same logarithmic overhead. This is exactly why the simulation loses a factor of O(log P) and no more - and why the "which rule?" argument, while asymptotically real, is a second-order concern next to getting W and D right.

```text
   same round:  P1 writes 7 to M      P5 writes 9 to M

   EREW          not expressible; scheduler splits into two rounds
                 M becomes 7 then 9
   CREW          still illegal (reads may collide, writes may not)
                 M becomes 7 then 9
   CRCW common   legal only if both write the same value (7 == 9)
   CRCW arbitrary legal; exactly one of 7 / 9 survives, which one is unspecified
   CRCW priority legal; P1 < P5 so 7 wins and M becomes 7
```

## Maximum finding: the same problem priced under every rule

Maximum finding is the canonical exercise because the identical problem gets visibly different prices as the conflict rule loosens. On an EREW PRAM, the pairwise tree reduction gives O(log n) time with O(n) work: each round halves the candidates, all reads hit distinct cells, and a CREW machine does no better since the reduction never conflicts anyway. On a CRCW machine with the common rule, the famous constant-time trick compares *every pair at once*: initialize a flag array B to zero, and for every ordered pair (i, j) have a processor compare A[i] against A[j], writing 1 into B[i] whenever A[i] loses; all concurrent writers write the same value, so the common rule applies, and the unique index left with B[i] = 0 is the maximum. Vishkin states the bill explicitly: the maximum of n elements is found in O(1) time and O(n^2) work with the common-CRCW convention.

Here is the interview trap hiding in that theorem. The O(1) claim is frequently quoted as "max in constant time" with the processor count quietly dropped - but n processors running for constant time execute only O(n) operations in total, and the flag scheme needs Theta(n^2) comparisons, one per pair, before every loser is marked. The honest statements form a tradeoff table, and any answer that mixes the time column of one row with the processor column of another is wrong:

| Variant | Time | Work (processors needed) | Mechanism |
|---|---|---|---|
| EREW / CREW | O(log n) | O(n) | pairwise reduction, no conflicts to arbitrate |
| CRCW common | O(1) | O(n^2) | all-pairs comparison, losers flagged concurrently |
| CRCW common | O(log log n) | O(n log log n) | doubly-logarithmic split into sqrt(n) blocks |
| CRCW randomized | O(1) w.h.p. | O(n) | random-sampling tournament |

The table's last two rows show why the model stayed interesting after the trick stopped being a parlor game: the doubly-logarithmic paradigm (reduce to sqrt(n) candidates recursively, then one constant-time all-pairs round over sqrt(n) items) and randomized tournaments are real algorithm-design techniques that were discovered *because* the model charges work and time separately.

## Work, depth, and Brent's theorem

The work-depth view replaces the machine with a DAG: nodes are unit operations, edges are data dependencies, **work** W is the number of nodes, and **depth** D is the length of the longest chain. Brent's theorem says a P-processor PRAM executes any such DAG in O(W/P + D) time: the W/P term is the throughput limit no schedule can beat, the D term is the latency limit, and a greedy level-by-level schedule achieves both simultaneously up to constants. Vishkin's notes prove exactly this as the central work-depth theorem - an algorithm taking x operations and d time runs in O(x/p + d) on p processors, under any of the five conflict conventions - and Brent's original 1974 paper (JACM 21(2):201-206) already contained the bound in the concrete: arithmetic expressions with n variables and constants evaluate in time 4 log2 n + 10(n-1)/p on p processors, within a constant factor of the best possible schedule.

```text
   E = ((a+b+c+d) * (e+f+g+h)) + ((i+j) * (k+l))

   a  b   c  d     e  f   g  h      i  j     k  l
    \/     \/       \/     \/       \/      \/
    p1     p2       p3     p4       p5      p6        depth 1, 6 ops
     \    /          \    /          \      /
     q1=p1+p2       q2=p3+p4       q3=p5*p6          depth 2, 3 ops
         \             /             |
          \           /              |
           s1=q1*q2                  |               depth 3, 1 op
                \                   /
                 E = s1 + q3                        depth 4, 1 op

   W = 11 operations,  D = 4 levels
   greedy schedule on P = 3 processors:
     t1: p1 p2 p3 | t2: p4 p5 p6 | t3: q1 q2 q3 | t4: s1 | t5: E
   hence T(3) = 5, and Brent's bound W/P + D = 11/3 + 4 = 7.7 holds
   also T(1) = W = 11,  T(11) = D = 4,  T(6) = 4 (depth-limited)
```

The ratio W/D is the algorithm's **parallelism** - the most processors that can be kept busy - and it drives the practical rule Valiant later named *parallel slackness*: if the machine has fewer processors than W/D, a greedy scheduler loses nothing, and oversubscribing hardware by a large constant factor is harmless because Brent's bound degrades only by that factor. Every parallel runtime you have used - Cilk-style work stealing, Rust's rayon, ForkJoinPool - is an implementation of this greedy-scheduling bound under a realistic scheduler; Blumofe and Leiserson proved for randomized work stealing that a fully strict computation runs in expected time T1/P + O(T-infinity), which is Brent's theorem realized in production software.

## List ranking: the canonical PRAM exercise

Pointer chasing is the worst case for parallelism - each element's value depends on its neighbor's, so the dependency chain has length n - and list ranking is the problem that taught the field how to break such chains. Given a linked list, compute for every element its distance to the end. **Pointer jumping** (Wyllie's 1979 thesis introduced it) doubles every pointer each round: in lockstep, every node sets succ[i] = succ[succ[i]] and accumulates the distance covered, so after round r each pointer reaches 2^r hops ahead, and after ceil(log2 n) rounds every distance to the tail is known - O(log n) time and O(n log n) work, as Vishkin's Theorem 9.1 states. The work is a log factor above optimal, and the notes' later sections close the gap with randomized and deterministic symmetry-breaking schemes achieving O(n) work at O(log n) time; the jump-based version remains the one to reach for in interviews because it is five lines and always right.

List ranking matters beyond lists because it is the subroutine inside half of PRAM algorithmics. The Euler-tour technique ranks a rooted tree by converting it into a list, then ranks the list - rooting trees, computing subtree sizes, and pre/postorder numbers all fall out; Shiloach-Vishkin-style graph connectivity iterates hooking steps followed by parallel pointer jumping; and the same doubling discipline reappears wherever "follow a dependency chain" appears, from binary-lifting tables in LCA and level-ancestor structures to pointer-doubled skip lists. The demo below runs Wyllie's algorithm on an 8-node chain, printing the distance array after each doubling round; watch round 3 snap every entry to the exact serial ranks in one shot.

```python
# Pointer jumping (Wyllie 1979): list ranking on a chain of 8 nodes.
# State: succ[i] = node i's current successor, dist[i] = hops from i to that
# successor. One PRAM round = every node updates in lockstep:
#     dist[i] += dist[succ[i]] ;  succ[i] = succ[succ[i]]
# so after round r, succ[i] sits 2^r hops down the list. Node 8 is the TAIL.

n = 8
succ = list(range(1, n + 1))          # chain 0 -> 1 -> ... -> 7 -> TAIL(=n)
dist = [1] * n                        # one hop to the current successor

def s_of(j):
    return succ[j] if j < n else n    # TAIL points to itself, distance 0

def d_of(j):
    return dist[j] if j < n else 0

r = 0
while any(s < n for s in succ):
    r += 1
    old = succ[:]                     # snapshot = one synchronous PRAM round
    succ = [s_of(old[i]) for i in range(n)]
    dist = [dist[i] + d_of(old[i]) for i in range(n)]
    print(f"after round {r} (pointers {2**r} ahead): dist = {dist}")

# Serial cross-check: rank of node i = number of hops to the tail.
rank = [0] * n
for i in range(n - 1, -1, -1):
    rank[i] = 1 if i == n - 1 else rank[i + 1] + 1
print("ranks match serial walk:", rank == dist)
```

Real output:

```text
after round 1 (pointers 2 ahead): dist = [2, 2, 2, 2, 2, 2, 2, 1]
after round 2 (pointers 4 ahead): dist = [4, 4, 4, 4, 4, 3, 2, 1]
after round 3 (pointers 8 ahead): dist = [8, 7, 6, 5, 4, 3, 2, 1]
ranks match serial walk: True
```

## NC: what parallelism can and cannot buy

The PRAM's complexity-theoretic payload is the class **NC**: decision problems solvable in polylogarithmic time on polynomially many processors. Formally the Complexity Zoo defines NC^i via uniform Boolean circuits of polynomial size and depth O(log^i n) with fan-in 2, and the standard equivalence - NC equals the class of problems with PRAM algorithms running in log^O(1) time using n^O(1) processors - means the PRAM and circuit views are interchangeable for this purpose. Everything on this page lands inside NC: prefix sums and maxima in O(log n) or better, sorting in O(log^2 n) time by parallel mergesort with O(n log n) work (Vishkin's Theorem 4.2), list ranking in O(log n) rounds by pointer jumping, and graph connectivity in O(log n) iterations of hooking plus jumping (his Theorem 11.2 bounds the iterations). NL sits inside NC^2, so nondeterministic logspace computation is itself quite parallel.

The flip side is the belief that NC is a proper subclass of P. Problems that are **P-complete** under NC-reductions - the circuit value problem and lexicographically-first depth-first search are the standard exemplars catalogued by Greenlaw, Hoover, and Ruzzo - are believed to admit no polylogarithmic-time polynomial-processor algorithm unless NC collapses to P, i.e., unless every polynomial-time computation is inherently parallelizable. This is the theory behind the honest interview answer to "can we just parallelize this?": for P-complete-shaped problems (sequential pointer chasing with data-dependent control, iterative solvers whose next step consumes the last), no cleverness in the conflict rule or the scheduler changes the asymptotic depth, and the best you can do is Amdahl's constant, not Brent's logarithm.

## The fall and the afterlife

As a hardware blueprint the PRAM died of one symptom: it pretends a memory access costs the same whether the cell is next door or across the machine. Valiant's bulk-synchronous parallel model (CACM 1990) was proposed explicitly as a *bridging* model between PRAM-style algorithmics and real machines, replacing free shared memory with periodic communication supersteps priced by a bandwidth and latency parameter; LogP (PPoPP 1993) went further and charged each short message for its latency, overhead, and the gap between sends. On real multiprocessors the conflict rules of the CRCW spectrum get resolved in hardware - cache-coherence protocols, atomic read-modify-write units, NUMA interconnects - at costs the PRAM never booked, and that gap is why the 1990s produced a zoo of "realistic" shared-memory models (QSM and friends) all trying to keep PRAM convenience while booking communication.

What survived is the accounting, and it survives everywhere. On GPUs, the scan (parallel prefix sum) is a load-bearing primitive, and the standard CUDA implementation is precisely a work-depth construction - Blelloch's 1990 vector-model scan, in all its up-sweep/down-sweep glory - adapted to SIMT warps; the [GPU Gems 3 chapter](https://developer.nvidia.com/gpugems/gpugems3/part-vi-gpu-computing/chapter-39-parallel-prefix-sum-scan-cuda) that taught a generation of CUDA programmers to build it opens by crediting Blelloch's observation that prefix sums look sequential but parallelize in logarithmic depth. SIMT execution itself is a bounded-CRCW machine in disguise: a warp is 32 processors in lockstep, scatter writes collide through hardware arbitration (priority-flavored atomics), and divergence is exactly the EREW penalty for not planning your memory access pattern. On multicore, the Brent bound T(P) = O(W/P + D) is what work-stealing runtimes actually deliver, while NUMA effects decide which of two algorithms with identical W and D wins - the second-order term that the model ignores on purpose. The discipline the PRAM teaches - first make the work near-serial-optimal and the depth polylogarithmic, only then pay for locality - is exactly how [matrix algorithms](./matrix-algorithms.md) get parallelized (Strassen's recursion is depth-efficient, BLAS-3 is the locality-aware rendering of it), and the same modeling philosophy, an idealized machine standing in for a messy one, powers [streaming and sublinear algorithms](./streaming-sublinear.md) and the PRAM-flavored [parallel graph algorithms](./parallel-graph-algorithms.md) that reuse pointer jumping for connectivity and Euler tours.

| Model | Unit-cost assumption | What it charges | Legacy |
|---|---|---|---|
| PRAM | memory access, sync | nothing | work-depth design, NC, Brent scheduling |
| BSP (1990) | local compute | superstep communication (g, L) | bridging model, slackness principle |
| LogP (1993) | local compute | latency, overhead, gap per message | network-accurate HPC modeling |
| GPU SIMT | warp instruction | divergence, global traffic, atomics | production kernels, scan-centric design |

## Interview lens: six questions this model settles

**"You have a DAG with work W and depth D. How fast on P processors, and what does the scheduler have to do?"** Bound T(P) <= W/P + D (Brent), achieved up to constants by any greedy schedule that never idles a processor while work remains. Check parallelism W/D against P first: if W/D < P, extra processors are dead weight and the honest answer is the depth bound alone. Then note the slackness corollary: oversubscribing P by any constant factor costs only that factor, so runtime schedulers can schedule aggressively.

**"How would you parallelize a linked list / pointer-chasing loop?"** Pointer jumping: lockstep doubling of successors gives O(log n) rounds and O(n log n) work, and the pattern extends to trees via Euler tours and to connectivity via hooking-plus-jumping. Mention the practical caveat - real linked lists in cache-hostile hardware are better converted to arrays or implicit structures first, which is why GPU code rarely ranks lists and instead redesigns the data layout - and you have covered theory and practice in one answer.

**"Does the EREW/CREW/CRCW distinction actually matter?"** It changes complexity by at most a logarithmic factor (the EREW simulation of CRCW costs O(log P) slowdown), so it matters at the margin - and at exactly one famous place it matters asymptotically: constant-time maximum finding on CRCW-common with Theta(n^2) work has no EREW analogue because EREW forbids the concurrent flag writes. The mature answer: design in the loosest rule you like, port to the strictest at a bounded cost, and know the all-pairs trick is a CRCW-only species.

**"Is it true that maximum of n numbers can be found in O(1) in parallel?"** Only with Theta(n^2) processors under the common CRCW rule, by all-pairs comparison with concurrent loser-flagging. With n processors, constant time is impossible for that scheme (n processors do O(n) operations total, and the flag scheme needs one comparison per pair), so the truthful pairing is either O(1) time with O(n^2) work, O(log log n) time with O(n log log n) work, or O(log n) time with O(n) work on EREW. Quoting the time without the processor count is the error the question is fishing for.

**"Is every polynomial-time problem parallelizable if we throw enough cores at it?"** Theory's answer is no, modulo an unresolved collapse: P-complete problems (circuit value, lexicographically-first DFS) get polylog-time PRAM algorithms only if NC = P, which is about as believed-against as P != NP. The practical translation: for problems whose dependency structure is inherently sequential, cores buy Amdahl constants, not depth reductions, and recognizing the shape (data-dependent control flow, iterative refinement) is the actual skill being tested.

**"When do PRAM numbers mislead?"** Whenever the dominant cost is neither work nor depth but data movement: a pointer-chasing traversal has W = n, D = n and predicts nothing useful, because the serial chain means the depth *is* the work and the real cost is n dependent cache misses. Bandwidth-bound kernels (the scatter phase of a sort, prefix scans over arrays larger than cache) have beautiful W/P + D curves on paper and are memory-limited in fact, which is why the measured [parallel sorting](./parallel-sorting.md) numbers in this book land far from their span predictions. The correct use of the model is as a first-order filter - if W is not near-optimal or D is not polylogarithmic, parallelizing is hopeless - after which locality, coherence traffic, and bandwidth take over as the second-order terms that decide which of the work-optimal candidates wins.

## References

1. R. M. Karp and V. Ramachandran, "Parallel Algorithms for Shared-Memory Machines," in *Handbook of Theoretical Computer Science, Volume A: Algorithms and Complexity*, J. van Leeuwen (ed.), MIT Press/Elsevier, 1990, pp. 869-942 (the canonical survey; no stable public copy is hosted online).
2. R. P. Brent, "The Parallel Evaluation of General Arithmetic Expressions," *Journal of the ACM* 21(2):201-206, 1974, DOI [10.1145/321812.321815](https://doi.org/10.1145/321812.321815) (Crossref-verified; the DOI 10.1145/321850.321854 that sometimes circulates for this paper actually resolves to a different JACM 1974 article - Rubin's Hamilton-paths search).
3. J. C. Wyllie, *The Complexity of Parallel Computations*, Ph.D. dissertation, Computer Science Department, Cornell University, 1979 (introduced pointer-jumping list ranking; institutional copies sit behind a bot wall, so cited without URL).
4. U. Vishkin, "Thinking in Parallel: Some Basic Data-Parallel Algorithms and Techniques" (104-page monograph/lecture notes): <https://www.umiacs.umd.edu/users/vishkin/PUBLICATIONS/classnotes.pdf> - source for the work-depth theorem (O(x/p + d)), the max-finding table, pointer-jumping Theorem 9.1, and the PRAM hierarchy.
5. J. JaJa, *An Introduction to Parallel Algorithms*, Addison-Wesley, 1992 (book; shared-memory algorithm design in the PRAM tradition).
6. G. E. Blelloch, *Vector Models for Data-Parallel Computing*, MIT Press, 1990 (scan/vector model underlying GPU prefix sums; PDF): <https://www.cse.chalmers.se/edu/course.2016/course/DAT280_Parallel_Functional_Programming/Papers/Ble90.pdf>
7. L. G. Valiant, "A Bridging Model for Parallel Computation," *Communications of the ACM* 33(8):103-111, 1990, DOI [10.1145/79173.79181](https://doi.org/10.1145/79173.79181) (Crossref-verified).
8. D. Culler, R. Karp, D. Patterson, et al., "LogP: Towards a Realistic Model of Parallel Computation," PPoPP 1993, DOI [10.1145/155332.155333](https://doi.org/10.1145/155332.155333) (Crossref-verified).
9. R. Blumofe and C. Leiserson, "Scheduling Multithreaded Computations by Work Stealing," *Journal of the ACM* 46(4):720-748, 1999, DOI [10.1145/324133.324234](https://doi.org/10.1145/324133.324234) (Crossref-verified; expected time T1/P + O(T-infinity)).
10. R. Greenlaw, H. J. Hoover, W. L. Ruzzo, *Limits to Parallel Computation: P-Completeness Theory*, Oxford University Press, 1995 (book; the P-completeness compendium).
11. Complexity Zoo, entry "NC" (Nick's Class): <https://complexityzoo.net/Complexity_Zoo:N>
12. G. Lentaris, *Models of Parallel Computation and Parallel Complexity* (survey thesis, Univ. of Athens): <http://users.uoa.gr/~glentaris/papers/MPLA_thesis_lentaris.pdf> - corroborates NC = PRAM[n^O(1) processors, log^O(1) time] and the logarithmic EREW-CRCW simulation gap.
