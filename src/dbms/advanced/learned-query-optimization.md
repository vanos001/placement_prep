# Learned Query Optimization

For thirty years the query optimizer has been a compiler with a statistics
problem: it plans with estimates it cannot verify, and the estimates get worse
exactly where plans get expensive. Learned query optimization repairs that
pipeline with models trained on the database's own observed behavior. Three
generations have run since 2015 - learned cardinality, fully learned planning,
learned steering - and the production verdict, as of 2026, is that the mildest
of the three wins.

## The optimizer's blind spot

Every classical optimizer (System R lineage, Cascades lineage) is open-loop:
it estimates cardinalities before execution, commits to a plan, and never
learns from the gap between estimate and reality. Three structural facts make
that fatal at scale:

1. **The independence assumption.** Selectivities are multiplied as if
   correlated columns were independent. Real data is correlated; that is
   usually why you are querying it.
2. **Errors multiply through join trees.** A k-way join multiplies k
   per-predicate q-errors, so estimate error grows exponentially with plan
   depth - precisely where plan alternatives matter most. Even mild 1.2x
   per-predicate errors compound past 1.3x on a four-way join.
3. **Plan cliffs are discontinuous.** Sometimes a 2x estimate error costs 2x
   runtime; sometimes it flips a hash join into a spilling nested loop and
   costs 50x. The tail, not the median, is where the damage lives.

Leis et al. measured this across engines and found cardinality estimation -
not cost modeling - dominates bad plan choices ([How Good Are Query
Optimizers, Really?](http://www.vldb.org/pvldb/vol9/p204-leis.pdf), PVLDB 9(3),
2015; a 2025 follow-up re-ran the methodology and the core result held). That
paper is the empirical license for everything below.

```text
Classical pipeline (open loop):

  SQL -> parse -> rewrite -> estimate card/cost -> plan search -> plan -> execute
                  |                  |                                    |
                  |                  +---- estimates never verified ------+---> results
                  +-- statistics refreshed by nightly ANALYZE at best

Where learned components plug in:

  SQL -> parse -> rewrite -> [learned cardinality] -> plan search -> execute
                                  (MSCN, 2019)            ^
                                    [steered hints / learned planner] (Bao 2021, Neo 2019)
```

## Generation 1: learned cardinality estimation

The MSCN model (Kipf et al., CIDR 2019) featurizes a query directly: filter
predicates become a bit mask over the schema's columns, the join graph becomes
a set of hyperedges, and a multi-set convolutional network pools over filter
and join groups to output one cardinality estimate, trained end-to-end on
(query, true count) pairs. On join-heavy workloads with correlated columns it
beats per-column histograms by a wide margin, because it can represent what
independence assumes away. The costs showed up just as clearly:

| Limitation | Mechanism | Consequence |
|---|---|---|
| Distribution shift | workload drifts away from training queries | estimates decay until retrained |
| Extrapolation | query far from training distribution | confident garbage, no error bars |
| Opacity | one number, no confidence interval | optimizer cannot hedge |
| Retraining cost | full pass over workload history | awkward inside an OLTP engine |

Learned estimators fix the *arithmetic* problem but inherit a *time* problem.
Follow-up work (Flow-Loss, PVLDB 14, 2021) attacked a subtler flaw: models
minimize q-error on row counts, but the optimizer does not pay for row-count
error - it pays for the *plan* the error induces. Training against plan cost
instead of estimate accuracy improves the plans actually chosen, and exposed
that most estimation errors are harmless while a few are catastrophic. Both
ideas matter later: harmlessness justifies steering; the catastrophic tail
defines the risk.

## Generation 2: fully learned planning

Neo (PVLDB 12(11), 2019) went further: replace the cost model and join-order
search with a learned value network over partial plans, trained by
reinforcement learning on actual execution feedback. On repetitive analytical
workloads Neo beats a well-tuned open-source optimizer - the model simply has
more information (yesterday's runtimes) than a cost model built from tuple
counts and magic constants.

But Neo's training regime is the tell: it re-executes workloads thousands of
times to gather feedback. An OLTP engine cannot re-run production queries in
simulation, and a warehouse will not sit still while the model converges. The
end-to-end design also concentrates risk: the learned planner owns *every*
decision, so one distribution shift can produce a tail plan of arbitrary
badness with no optimizer fallback in the loop. Bao's authors summarized the
end-to-end record as substantive training overhead, inability to adapt to
change, and poor tail performance - the three failure modes steering avoids.

## Generation 3: steering - hint sets instead of plan spaces

Bao (Marcus et al., SIGMOD 2021) keeps the classical optimizer as the plan
generator and learns only a *choice among optimizers*. Each hint set in a
small set K ("disable nested loop", "prefer hash join", "force index X")
turns the native optimizer into a different deterministic optimizer with its
own blind spots. A tree convolutional network over the query's plan sketch
predicts which hint set yields the fastest plan; Thompson sampling handles the
explore/exploit trade-off. The plan space the model must understand is K
choices, not the exponentially many join orders the native search enumerates.

Three properties make this production-shaped:

- **Bounded downside.** The default configuration is always in K, so the
  steerer can never lose to the unmodified optimizer by more than one query.
- **Cheap feedback.** Every execution labels which hint set won, so the model
  learns continuously from production traffic - no simulator needed.
- **A portable lever.** Postgres-style hints, Oracle hints, and Spark plan
  annotations all expose the same mechanism.

The idea carried to big data and to production: Negi et al. steered Spark
TPC-DS plans with cost-guided cardinality feedback (SIGMOD 2021), and
Microsoft deployed a steered optimizer on Azure SQL production workloads
(SIGMOD 2022) - worth reading as the engineering counterweight to the paper
record: refresh cadence, guard rails, and the explicit decision to steer
rather than replace.

## Learning without demonstrations

Balsa (Yang et al., SIGMOD 2022) reopens the end-to-end question with one
rule: learn from *self-generated* experience, no expert demonstrations, no
pretrained cost models. Balsa uses shadow execution (candidate plans run on
real data outside the serving path) to collect safe feedback and matches
heuristic optimizers on join-order benchmarks within hours. It is the
strongest evidence that fully learned planning is not doomed - and a catalog
of why it stays research-grade: shadow execution is real cost, and the design
presupposes a safe execution substrate most engines do not have.

## Parametric query optimization: Kepler

Kepler (Marcus et al., SIGMOD 2023) attacks a narrower, production-relevant
slice: parametric query optimization (PQO). Application queries arrive as
templates with different literals (`WHERE region = ?`), and the best plan for
a template can change with the parameter. Classical PQO partitions a template
into static plan regions; Kepler trains a per-template model that maps
parameter values to the fastest plan, validated by execution, on top of
MariaDB. The scope restriction is the point: one template is a tiny, stable
learning problem with tight feedback loops, versus one global model facing an
entire workload. As of 2026 this "learn the small thing nearest the
execution" pattern keeps winning across the learned-DBMS space.

## The 2001 ancestor

None of this started with deep learning. LEO, IBM DB2's LEarning Optimizer
(VLDB 2001), patched the classical optimizer with feedback: when observed
cardinalities diverged from estimates, LEO stored correction factors and
reapplied them to later queries with matching subplans. Same loop, same
insight (execution is the best statistics), none of the model risk - and it
shipped. The parts of LEO that made it deployable (conservative, per-subplan,
always on top of the base optimizer) are exactly what the steering generation
reinvented.

| System | Venue | Learns | Replaces optimizer? | Safe fallback |
|---|---|---|---|---|
| LEO | VLDB 2001 | estimate corrections | no, patches estimates | always |
| MSCN | CIDR 2019 | cardinality estimates | no, swaps estimator | statistics |
| Neo | PVLDB 2019 | plan values via RL | yes, cost + search | none |
| Bao | SIGMOD 2021 | hint-set choice | no, steers search | default hints |
| Balsa | SIGMOD 2022 | planning from scratch | yes | shadow execution |
| MS steering | SIGMOD 2022 | hint choice at scale | no, steers | default plan |
| Kepler | SIGMOD 2023 | plan per parameter range | no, per-template | native plan |

## Demo: steering versus tail-plan risk

The toy below makes the trade-off concrete. Three query templates, three hint
sets, lognormal latencies with different medians and tails. The offline
profile shows why "pick the best median" is wrong: for range-join, hash-all
wins the median (7.11 vs 8.87 ms) and loses the p95 badly (51.88 vs 22.50 ms)
- a plan cliff in miniature. An epsilon-greedy bandit tracking means still
lands on the robust choice for range-join and saves 26% over always-default
by doing nothing but choosing among safe plans.

```python
"""Bao-style steered optimizer, toy simulation.

Three query classes (templates), three hint sets, seeded latency samples.
A context-bandit learns per-class hint choices from observed latencies.
"""
import math
import random

random.seed(7)

CLASSES = [                                   # template -> tree-conv features
    ("point-lookup", [1, 0, 0, 1]),           # 1 join, no sort, equality filter
    ("range-join",   [2, 0, 1, 0]),           # 2 joins, sort, range filter
    ("big-hash",     [4, 1, 0, 0]),           # 4 joins, hash-heavy, no sort
]

COST = {                                      # (class, hint): (median_ms, tail_mult)
    ("point-lookup", 0): (0.8, 3.0), ("point-lookup", 1): (1.4, 3.0),
    ("point-lookup", 2): (0.5, 2.5),
    ("range-join",   0): (12.0, 8.0), ("range-join", 1): (7.0, 20.0),
    ("range-join",   2): (9.0, 4.0),
    ("big-hash",     0): (40.0, 6.0), ("big-hash", 1): (22.0, 9.0),
    ("big-hash",     2): (31.0, 7.0),
}
HINT_NAMES = {0: "default", 1: "hash-all", 2: "index-steered"}

def draw(cls, hint):
    med, tail = COST[(cls, hint)]
    return random.lognormvariate(math.log(med), math.log(tail) / 2.5)

# offline ground truth: p50 / p95 per (class, hint) over 20k draws
print("offline latency profile (ms), 20k samples per cell")
print(f"{'class':<14}{'hint':<15}{'p50':>8}{'p95':>9}{'tail ratio':>12}")
for cls, _ in CLASSES:
    for hint in (0, 1, 2):
        xs = sorted(draw(cls, hint) for _ in range(20000))
        print(f"{cls:<14}{HINT_NAMES[hint]:<15}"
              f"{xs[10000]:>8.2f}{xs[19000]:>9.2f}{xs[19000] / xs[10000]:>11.1f}x")

# online: epsilon-greedy context bandit, 30 rounds per class
est = {(c, h): [0.0, 0] for c in range(3) for h in (0, 1, 2)}
steered = default = 0.0
for rnd in range(30):
    for c, (name, _) in enumerate(CLASSES):
        h = next((h for h in (0, 1, 2) if est[(c, h)][1] == 0), None)  # unseen first
        if h is None:
            h = min((0, 1, 2), key=lambda h: est[(c, h)][0])
            if random.random() < 0.10:
                h = random.choice((0, 1, 2))
        lat = draw(name, h)
        m, n = est[(c, h)]
        est[(c, h)] = [(m * n + lat) / (n + 1), n + 1]
        steered += lat
        default += draw(name, 0)
print("\n30 rounds per class, epsilon-greedy bandit vs always-default")
for c, (name, _) in enumerate(CLASSES):
    best = min((0, 1, 2), key=lambda h: est[(c, h)][0])
    print(f"  {name:<13} learned hint = {HINT_NAMES[best]:<14} est = {est[(c, best)][0]:6.2f} ms")
print(f"  cumulative: steered {steered:7.1f} ms   always-default {default:7.1f} ms"
      f"   saved {100 * (1 - steered / default):.1f}%")
```

```text
offline latency profile (ms), 20k samples per cell
class         hint                p50      p95  tail ratio
point-lookup  default            0.80     1.66        2.1x
point-lookup  hash-all           1.40     2.88        2.1x
point-lookup  index-steered      0.50     0.92        1.8x
range-join    default           11.86    47.63        4.0x
range-join    hash-all           7.11    51.88        7.3x
range-join    index-steered      8.87    22.50        2.5x
big-hash      default           39.85   129.01        3.2x
big-hash      hash-all          21.88    93.11        4.3x
big-hash      index-steered     30.99   111.15        3.6x

30 rounds per class, epsilon-greedy bandit vs always-default
  point-lookup  learned hint = index-steered  est =   0.52 ms
  range-join    learned hint = index-steered  est =  10.85 ms
  big-hash      learned hint = hash-all       est =  39.15 ms
  cumulative: steered  1645.4 ms   always-default  2236.4 ms   saved 26.4%
```

## Production reality: why steering beats end-to-end

Strip the branding and the steering generation survives for four reasons:

1. **It adds information instead of replacing machinery.** The native optimizer
   keeps its hardened rewrites, transformation rules, and physical operators;
   the model only arbitrates between plans the optimizer considers legal.
2. **The action space is tiny and stable.** K hint sets is a bandit problem
   solvable from production feedback; exponentially many join orders is a
   search problem that needs a simulator.
3. **Failure is bounded and attributable.** A wrong steer costs one query's
   gap to the default plan and shows up in the next feedback cycle. A wrong
   end-to-end model can be globally wrong with nothing to fall back to.
4. **Deployment is change management, not correctness proofs.** The Microsoft
   paper's real contribution is operational - shadow evaluation, refresh
   cadence, kill switches - all easier when model authority is capped at
   hint selection.

The remaining end-to-end frontier is real but narrow: engines that already
replay exploratory workloads safely (Balsa's substrate), or closed worlds of
stable templates (Kepler's slice). For a general-purpose engine in 2026 the
state of the art is: tuned statistics, a conventional optimizer, and -
increasingly shipped - a steerer watching execution feedback and flipping
hints where the estimates keep lying.

## Interview probes

- **"Why does cardinality estimation fail on correlated columns, and what does
  a learned estimator buy?"** Independence multiplies selectivities; a model
  over filter/join features learns the correlation - but converts a statistics
  bug into an operations problem (drift, retraining).
- **"Your learned planner is 20% faster at median and 10x slower at p99 on one
  template. What ships?"** The steerer: cap model authority, keep the default
  plan as fallback, watch the tail. Median wins do not pay for p99 incidents.
- **"Bao vs Neo - the actual architectural difference?"** Where the model
  sits: Bao chooses among optimizer configurations; Neo *is* the cost model
  and the search. Production feedback in one case, simulator in the other.
- **"What did LEO get right in 2001?"** Conservative scope - corrections
  attached to matching subplans, layered on the base optimizer. Every
  deployable learned optimizer since follows that sketch.

## Cross-References

- [Cardinality Estimation](./cardinality-estimation.md) - the classical statistics these models replace or repair
- [Query Optimizers](./query-optimizers.md) - the System R and Cascades machines being steered
- [Cascades Optimizer](./cascades-optimizer.md) - the search framework whose plan space makes estimate errors expensive
- [Learned Indexes](./learned-indexes.md) - the sibling field: ML replacing index structures rather than planning
- [Volcano Optimizer](./volcano-optimizer.md) - the original optimization pipeline this page upgrades

## References

- Kipf et al. "Learned Cardinalities: Estimating Correlated Joins with Deep Learning" (MSCN). CIDR 2019. https://arxiv.org/abs/1809.00677
- Marcus et al. "Neo: A Learned Query Optimizer." PVLDB 12(11), 2019. https://www.vldb.org/pvldb/vol12/p1705-marcus.pdf
- Marcus et al. "Bao: Making Learned Query Optimization Practical." SIGMOD 2021. https://doi.org/10.1145/3448016.3452838 (extended: https://arxiv.org/abs/2004.03814)
- Yang et al. "Balsa: Learning a Query Optimizer Without Expert Demonstrations." SIGMOD 2022. https://doi.org/10.1145/3514221.3517885
- Marcus et al. "Kepler: Robust Learning for Parametric Query Optimization." Proc. ACM Manag. Data 1(1), 2023. https://doi.org/10.1145/3588963
- Zhang et al. "Deploying a Steered Query Optimizer in Production at Microsoft." SIGMOD 2022. https://doi.org/10.1145/3514221.3526052
- Leis et al. "How Good Are Query Optimizers, Really?" PVLDB 9(3), 2015. http://www.vldb.org/pvldb/vol9/p204-leis.pdf
