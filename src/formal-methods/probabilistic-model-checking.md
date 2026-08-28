# Probabilistic Model Checking: DTMCs, MDPs, and PCTL

When a system's behavior includes genuine dice - randomized backoff,
lossy channels, fault-tolerant quorum choices - the verification question
changes shape: not "can the bad state happen?" but "what is the probability
of the bad state, and can you guarantee a bound?". Probabilistic model
checking answers quantitatively: given a probabilistic automaton and a
PCTL/CSL property, compute the exact probability that the property holds
and compare it to the specification. This page covers the three model
classes, the property logic, the numerical engines (with a working value
iteration), and where statistical checking replaces exact computation.

Companion pages: [model checking](./model-checking.md) for the
non-probabilistic machinery this generalizes,
[bisimulation](./bisimulation.md) for the minimization step that also
applies here (probabilistic bisimulation), and
[queueing theory](../queueing-theory/mm1-queue.md) for the analytical
modeling of the same stochastic systems when closed forms exist.

## Three model classes

| model      | branching        | time            | typical use                     |
|------------|------------------|-----------------|----------------------------------|
| DTMC       | probabilistic only | discrete steps | fully randomized systems, Markov chains |
| MDP        | nondeterministic + probabilistic | discrete steps | distributed protocols (who moves next is unscheduled), controller synthesis |
| CTMC       | probabilistic, exponentially timed | continuous | reliability/availability, queues, chemistry |

The nondeterminism of MDPs is not decorative: in a distributed protocol,
which message arrives next is genuinely unscheduled. PCTL over MDPs then
quantifies over *schedulers* (resolutions of nondeterminism): "under all
schedulers, P(error) <= 0.001" is the meaningful worst-case guarantee, and
solving for it is a maximization/minimization over policies - which is
exactly the MDP optimal-policy problem from planning.

## PCTL: the property language

PCTL replaces CTL's path quantifiers with probability bounds:

```text
  P>=0.99 [ F ack ]      with probability >= 0.99, ack eventually happens
  P<=0.001 [ X failed ]  next-step failure probability bounded
  P>0.5 [ ack U<=100 done ] bounded until: ack before done within 100 steps
```

Add rewards and you get expected-cost queries: `R{"energy"}<=4.5 [C]`
(the expected cumulative energy over the run, bounded). The property
language is why this field connects directly to SLO engineering - the
queries are literally percentile guarantees.

## The numerical engines

For a DTMC and a reachability property, computing P(reach bad) is a linear
system solve over the state space. For MDPs, it is a sequence of linear
systems (one per policy) guided by policy iteration, or a fixed-point
iteration that fuses the max into each step. The workhorse everywhere is
**value iteration**:

```text
  x_0(bad) = 1;  x_0(other) = 0
  repeat until eps-converged:
      x_{k+1}(s) = max over actions a of  sum over t of  P(s, a, t) * x_k(t)
```

Convergence is asymptotic (value iteration is a contraction with factor
equal to the chain's eventual transition mass), which produces the
standard engineering caveat: the epsilon threshold bounds the *value*
error, not the number of steps - tools convert via relative-difference
tests, and exact answers come from Gaussian elimination or rational
arithmetic where the model is small enough.

The demo below runs value iteration on a 4-state MDP modeling a
randomized-retry client: action `retry` succeeds with p=0.9, `giveup`
goes to failure, and a scheduler maximizes success probability. The
fixed point is exact here (absorbing structure), and the script prints
every iteration so the convergence is visible.

```python
#!/usr/bin/env python3
"""Value iteration on a 4-state MDP: randomized-retry client.

States: s0 (start), s1 (transient), s2 (success, absorbing), s3 (fail, absorbing)
Actions from s0/s1:
  retry: with p -> success/next state, with 1-p -> stay/degrade
  giveup: go straight to the fail sink

Scheduler question: max over policies of P(eventually success)."""


P = {  # action -> {state: [(prob, target), ...]}
    "retry": {
        "s0": [(0.9, "s2"), (0.1, "s1")],
        "s1": [(0.5, "s2"), (0.5, "s1")],
    },
    "giveup": {
        "s0": [(1.0, "s3")],
        "s1": [(1.0, "s3")],
    },
}
ACTIONS = ["retry", "giveup"]
TARGET = "s2"

ALL_STATES = ["s0", "s1", "s2", "s3"]
x = {s: (1.0 if s == TARGET else 0.0) for s in ALL_STATES}
print("MDP: s0 -retry(0.9)-> s2, retry(0.1)-> s1; s1 -retry(0.5)-> s2,")
print("     stay(0.5); giveup -> s3 (fail). Max P(reach s2).")
print()

NON_ABSORBING = ["s0", "s1"]     # s2/s3 absorbing: value fixed forever
iters = 0
while True:
    iters += 1
    nxt = {}
    for s in NON_ABSORBING:
        best_v, best_a = -1.0, None
        for a in ACTIONS:
            v = sum(p * x[t] for (p, t) in P[a][s])
            if v > best_v:
                best_v, best_a = v, a
        nxt[s] = (best_v, best_a)
    print(f"iter {iters}: " +
          "  ".join(f"{s}:{nxt[s][0]:.4f}({nxt[s][1][0]})" for s in NON_ABSORBING))
    delta = max(abs(nxt[s][0] - x[s]) for s in NON_ABSORBING)
    x.update({s: nxt[s][0] for s in NON_ABSORBING})
    if delta < 1e-12:
        break

print()
print(f"converged in {iters} iterations (|delta| < 1e-12; absorbing MDP)")
print(f"  optimal policy: retry from both s0 and s1")
print(f"  P(success) from s0 = 1.0   (0.9 immediate + retries on the 0.1 tail)")
print(f"  P(success) from s1 = 1.0   (0.5 per attempt, unbounded retries)")
print()
print("now bound the retries: bounded-until variant P[F<=k success]")
for k in (0, 1, 2, 3):
    # x_k = P(success within k steps); absorbing bookkeeping by hand
    v_s1 = 1 - 0.5 ** k if k > 0 else 0.0
    v_s0 = 0.9 + 0.1 * v_s1 if k > 0 else 0.0
    print(f"  k={k}: P(success<= {k} steps) from s0 = {v_s0:.4f}, from s1 = {v_s1:.4f}")
print()
print("expected number of retries from s1 before success (geometric p=0.5):")
print(f"  E[retries] = (1-p)/p = {0.5 / 0.5:.1f}  -> reward queries are the")
print("  same fixed-point machinery with a per-step cost added")
```

```text
MDP: s0 -retry(0.9)-> s2, retry(0.1)-> s1; s1 -retry(0.5)-> s2,
     stay(0.5); giveup -> s3 (fail). Max P(reach s2).

iter 1: s0:0.9000(r)  s1:0.5000(r)
iter 2: s0:0.9500(r)  s1:0.7500(r)
iter 3: s0:0.9750(r)  s1:0.8750(r)
iter 4: s0:0.9875(r)  s1:0.9375(r)
iter 5: s0:0.9938(r)  s1:0.9688(r)
iter 6: s0:0.9969(r)  s1:0.9844(r)
iter 7: s0:0.9984(r)  s1:0.9922(r)
iter 8: s0:0.9992(r)  s1:0.9961(r)
iter 9: s0:0.9996(r)  s1:0.9980(r)
iter 10: s0:0.9998(r)  s1:0.9990(r)
iter 11: s0:0.9999(r)  s1:0.9995(r)
iter 12: s0:1.0000(r)  s1:0.9998(r)
iter 13: s0:1.0000(r)  s1:0.9999(r)
iter 14: s0:1.0000(r)  s1:0.9999(r)
iter 15: s0:1.0000(r)  s1:1.0000(r)
iter 16: s0:1.0000(r)  s1:1.0000(r)
iter 17: s0:1.0000(r)  s1:1.0000(r)
iter 18: s0:1.0000(r)  s1:1.0000(r)
iter 19: s0:1.0000(r)  s1:1.0000(r)
iter 20: s0:1.0000(r)  s1:1.0000(r)
iter 21: s0:1.0000(r)  s1:1.0000(r)
iter 22: s0:1.0000(r)  s1:1.0000(r)
iter 23: s0:1.0000(r)  s1:1.0000(r)
iter 24: s0:1.0000(r)  s1:1.0000(r)
iter 25: s0:1.0000(r)  s1:1.0000(r)
iter 26: s0:1.0000(r)  s1:1.0000(r)
iter 27: s0:1.0000(r)  s1:1.0000(r)
iter 28: s0:1.0000(r)  s1:1.0000(r)
iter 29: s0:1.0000(r)  s1:1.0000(r)
iter 30: s0:1.0000(r)  s1:1.0000(r)
iter 31: s0:1.0000(r)  s1:1.0000(r)
iter 32: s0:1.0000(r)  s1:1.0000(r)
iter 33: s0:1.0000(r)  s1:1.0000(r)
iter 34: s0:1.0000(r)  s1:1.0000(r)
iter 35: s0:1.0000(r)  s1:1.0000(r)
iter 36: s0:1.0000(r)  s1:1.0000(r)
iter 37: s0:1.0000(r)  s1:1.0000(r)
iter 38: s0:1.0000(r)  s1:1.0000(r)
iter 39: s0:1.0000(r)  s1:1.0000(r)
iter 40: s0:1.0000(r)  s1:1.0000(r)

converged in 40 iterations (|delta| < 1e-12; absorbing MDP)
  optimal policy: retry from both s0 and s1
  P(success) from s0 = 1.0   (0.9 immediate + retries on the 0.1 tail)
  P(success) from s1 = 1.0   (0.5 per attempt, unbounded retries)

now bound the retries: bounded-until variant P[F<=k success]
  k=0: P(success<= 0 steps) from s0 = 0.0000, from s1 = 0.0000
  k=1: P(success<= 1 steps) from s0 = 0.9500, from s1 = 0.5000
  k=2: P(success<= 2 steps) from s0 = 0.9750, from s1 = 0.7500
  k=3: P(success<= 3 steps) from s0 = 0.9875, from s1 = 0.8750

expected number of retries from s1 before success (geometric p=0.5):
  E[retries] = (1-p)/p = 1.0  -> reward queries are the
  same fixed-point machinery with a per-step cost added
```

Reading the numbers: value iteration converges to 1.0 but only
asymptotically - 40 iterations for a 1e-12 delta here, because the
contraction factor is 0.5 per step and the answer sits at the fixed
point's edge. With unbounded retries the success probability is 1.0
from both transient states - the interesting engineering quantities are
the *bounded* variants (k retries cap the tail risk) and the expected-cost
queries, which is why real PCTL usage leans on bounded-until operators
with reward structures rather than unbounded eventualities.

## Statistical model checking: simulation with error bars

When the state space is too large for numerical iteration (or the model is
a black-box simulator), statistical model checking replaces exact
computation with Monte Carlo: simulate N runs, count property
satisfactions, and decide against the bound with a hypothesis test. The
internals matter for honest numbers:

- **Fixed-size sampling** with a two-sided Hoeffding/Chernoff bound: N
  chosen so the estimate is within epsilon of the truth with probability
  1-delta. The N scales as O(log(2/delta) / (2 eps^2)) - halving the error
  bar quadruples the runs.
- **SPRT** (Wald's sequential test) when the property is a yes/no against
  a threshold: simulate until the likelihood ratio crosses one of two
  boundaries; dramatically fewer runs near-clear-cut cases, and the
  test's error levels (alpha, beta) are explicit inputs.
- The fine print: SMC gives no counterexample trace (a percentile bound
  violation has no single witness), and rare-event probabilities (the
  1e-9 SLO class) need importance sampling or splitting - naive Monte
  Carlo cannot resolve them in bounded time.

PRISM (with its simulator), the Modest Toolset, and SMC-oriented engines
(etalon: the modes/backends in Modest) ship both engines; the numerical
backends remain the reference answers where the model fits.

## Interview probes

- Why does nondeterminism force scheduler quantification in PCTL, and
  what changes in the value-iteration step (max vs plain sum)?
- Your P[F<=100 error] <= 1e-6 check needs validating on a 10^9-state
  model: contrast numerical (with abstraction) vs statistical approaches,
  including the rare-event caveat.
- Where does the contraction factor of value iteration come from, and
  why does an epsilon on values not directly bound the iteration count?
- Translate "99.9th percentile of latency <= 200ms" into a PCTL reward
  query, and name two modeling choices that would silently falsify it.

## References

1. Baier & Katoen, *Principles of Model Checking*, MIT Press, 2008 - the
   DTMC/MDP/CTMC semantics and PCTL/CSL chapters this page compresses
   (standard graduate text; no public URL).
2. Kwiatkowska, Norman, Parker, "Stochastic model checking", in
   *Formal Methods for Performance Evaluation*, LNCS 4486, 2007,
   [doi:10.1007/978-3-540-72522-0_6](https://doi.org/10.1007/978-3-540-72522-0_6)
   - the PRISM-line survey covering the numerical engines.
3. Kwiatkowska, Norman, Parker, "Probabilistic model checking: advances
   and applications", 2018,
   [doi:10.1007/978-3-319-57685-5_3](https://doi.org/10.1007/978-3-319-57685-5_3)
   - the modern survey with the case-study numbers.
4. [PRISM manual](https://www.prismmodelchecker.org/manual/) - property
   syntax (P/R operators), engine options, and the exact-vs-statistical
   backend split.
