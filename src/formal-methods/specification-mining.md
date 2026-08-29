# Specification Mining: Inferring What Code Was Supposed to Do

Most code has no contract: documentation is stale, and the preconditions,
postconditions, and object invariants the code enforces were never written
down. Specification mining recovers contracts from *evidence* instead of author
intent: run the program and keep the properties that survive, or read a corpus
and keep the patterns that repeat. A mined specification is a hypothesis that
has resisted falsification so far, not a theorem -- mining never proves, it
ranks hypotheses by failed refutations.

## The evidence pipeline

Every miner, dynamic or static, fits the same four-stage shape:

```text
  evidence source               candidate generation              filtering
+-------------------+         +------------------------+     +--------------------------+
| instrumented runs | ----->  | templates and patterns | --> | discard anything         |
| source corpus     |         | x > 0, x == orig(x),   |     | violated by >= 1 sample; |
| call traces       |         | sorted(a), call pairs  |     | suppress implications    |
+-------------------+         +------------------------+     +-------------+------------+
                                                                            |
                                                                            v
                     consumers: assertions, contracts, test oracles, bug reports, provers
```

Dynamic miners generate candidates from property templates and filter them
against observed values; static miners generate candidates from syntactic
patterns and filter them by frequency or consistency across a corpus. What
reaches consumers -- and the confidence allowed there -- is where the risk lives.

## Dynamic invariant detection: Daikon

Daikon (MIT PLSE, now hosted by UW PLSE) is the canonical dynamic miner; its own
page summarizes: "Dynamic invariant detection runs a program, observes the
values that the program computes, and then reports properties that were true
over the observed executions."

1. **Instrument and run.** The program executes under a test suite; front ends
   exist for C and Java among others. At each *program point* (function entries
   and exits, loop heads), each execution emits a sample: the variable values
   at that point.
2. **Generate candidates from a template hierarchy.** Unary properties
   (`x != null`, `x > 0`, `x in {1, 2, 3}`), binary relationships
   (`x <= y`, `a == b + c`, `x % 5 == 0`), sequence properties (`a` is sorted),
   postconditions via `orig` values (`x == orig(x)`), and implication forms
   (`x != null ==> y > 0`) inferred by conditioning.
3. **Filter by falsification, then emit.** A candidate violated by even one
   sample is discarded; survivors get redundancy suppression (if `x > 0` and
   `x >= 1` both survive, only the stronger is shown) and become assertions,
   `.dtrace`/`.decls` files, or JML- and ESC-style contracts.

Two costs decide usability: instrumentation and sample volume (every variable
of interest, at every program point, on every execution), and test-suite
distribution: weak tests yield trivially true invariants, narrow tests yield
confidently wrong ones.

## Static mining: the corpus as evidence

Static miners treat the source itself as the sample space: if nearly all call
sites follow a pattern, the pattern is probably a real constraint and the
deviating call site is probably a bug.

- **Consistency rules.** Engler et al.'s "bugs as deviant behavior" mined rules
  from source lines that *imply each other* (a lock taken in most near-identical
  contexts but not all): the majority defines the rule, the minority is the
  defect list.
- **Itemset and sequence mining.** PR-Miner encoded each function as an itemset
  of co-occurring API calls and mined interleaved usage patterns; PERIMETER
  (Wasylkowski, Zeller, Lindig) related parameter sets to call sequences and
  flagged object-usage outliers, later extended to temporal specifications.
- **Model learning.** Where an interface can be *queried*, active automata
  learning (L*-style queries) infers a finite-state machine of legal operation
  sequences -- used to reverse-engineer SSH protocol state machines.

| Family | Evidence | Typical output | Confidence basis | Classic failure |
|---|---|---|---|---|
| Dynamic detection (Daikon) | Instrumented runs | Pre/postconditions, object invariants | Survived every observed execution | Mirrors only what tests exercised |
| Consistency mining (Engler) | Source lines | Implicit programming rules | The majority agrees with itself | The bug is the majority |
| Itemset/sequence mining (PR-Miner, PERIMETER) | Code and call traces | API usage patterns, call orders | Frequency across a large corpus | Outliers are legitimate special cases |
| Model learning (L*) | Queries to a black box | FSMs of legal operation sequences | Conformance checks between rounds | Unqueried behavior stays invisible |

Two rows have a "confidence basis" that can invert into the failure mode -- that is the deployment risk.

## Probabilistic and learned inference

Between the classical families sits a statistical layer: candidates carry
*confidence scores* rather than boolean survival, support thresholds tune
precision against recall, and covariates predict which candidates deserve
review. Le Goues and Weimer showed that simple code-quality measures predict
which inferred invariants are likelier to be spurious.

Since roughly 2023 the candidate *generator* is often an LLM: propose plausible
preconditions, refinements, or API rules from code text, then hand the proposals
to the classical pipeline -- dynamic checking, differential testing, a prover --
as the filter. The pipeline survives unchanged; only the candidate source
changed. An LLM-suggested invariant is a hypothesis with fluent English and
nothing more, until it survives falsification.

## Where mined specifications go

| Consumer | What it does with mined specs | Guardrail |
|---|---|---|
| Verifiers (Houdini + ESC/Java) | Candidates become annotations the prover confirms or refutes | A refuted candidate discredits the guess, not the program |
| Test oracles (property-based testing) | Surviving predicates become checks over generated inputs | Property only covers the observed input distribution |
| Bug finding (anomaly detection) | Deviations from mined patterns get flagged for review | Every report costs reviewer attention |
| Runtime monitoring | Invariants checked continuously in staging or production | False alarms teach operators to ignore the monitor |

The Houdini row is the cleanest division of labor: mining supplies *plausible*
annotations at scale, the prover supplies the *certainty* mining lacks, and
refutations prune the miner's false positives for free.

The deployment question is not "can we mine specifications" but "what is the
cost per true positive": if 20 of 500 candidates are real defects, the 480
false positives are the salary of every engineer who triages them. So raise the
survival bar (diverse runs, strict suppression), rank by risk-adjusted
confidence, auto-discharge what a prover can resolve, and ship mined specs as
oracles, not verdicts.

## The confidence problem

- **Absence of counterexample is not truth.** "Held over all observed
  executions" and "is an invariant" are different statements; the gap between
  them is the gap between testing and proof.
- **The sample distribution is the specification.** The mini miner below
  "discovers" that the list has no duplicate items -- because the state
  generator happens to draw distinct values. It survives every check and is
  still wrong about the real contract; every dynamic miner inherits this
  failure, at any scale.
- **Confidence must match consumer risk.** A mined spec used to seed a prover
  costs nothing if wrong (the prover refutes it); the same spec wired into a
  monitor that pages on-call engineers is expensive if wrong.
- **Mitigations are all evidence upgrades.** Diverse runs, cross-validation
  across program versions, agreement between independent miners, human review
  atop a ranked list -- none converts a hypothesis into a theorem; each only
  makes a missed refutation less likely.

Verification closes the world (proof over all executions); mining samples an
open one (no counterexample yet). Mined specifications are for *finding where
to look*; proofs are for *stopping looking*. Interview shorthand: legacy-code
specs -> the pipeline plus the distribution caveat; "can a miner be wrong?" ->
yes, give the no-duplicates example; Houdini -> mining proposes, the prover
disposes.

## A worked miniature: a 60-line mini Daikon

The demo runs Daikon's core loop at one program point over 20 observed states
of a sorted-list-with-capacity structure, then injects two buggy states and
reports which surviving invariants catch them.

```python
"""Mini invariant learner, Daikon-style: filter candidates over samples."""
import random
random.seed(7)

def gen_valid(rng):
    "A valid state of a sorted-list-with-capacity structure."
    cap = rng.randint(0, 10)
    size = rng.randint(0, cap)
    return {"items": sorted(rng.sample(range(0, 12), size)),  # distinct values!
            "size": size, "cap": cap}

CANDIDATES = [
    ("size == len(items)", lambda s: s["size"] == len(s["items"])),
    ("size <= cap", lambda s: s["size"] <= s["cap"]),
    ("items non-decreasing", lambda s: all(a <= b for a, b in zip(s["items"], s["items"][1:]))),
    ("no duplicate items", lambda s: len(set(s["items"])) == len(s["items"])),
    ("size >= 1", lambda s: s["size"] >= 1),
    ("max(items) <= cap", lambda s: not s["items"] or max(s["items"]) <= s["cap"]),
]

train = [gen_valid(random) for _ in range(20)]
survivors, discarded = [], []
for name, pred in CANDIDATES:
    bad = next((s for s in train if not pred(s)), None)
    (discarded if bad is not None else survivors).append((name, bad))

print("training states: 20 (generator: sorted distinct items, size <= cap)\n")
print("SURVIVED over all 20 states:")
for name, _ in survivors: print("  [x] %s" % name)
print("\nDISCARDED (violated by training data):")
for name, bad in discarded: print("  [ ] %-20s violated by: %r" % (name, bad))

bugs = [("A: off-by-one size", {"items": [3, 5], "size": 3, "cap": 8}),
        ("B: insert out of order", {"items": [9, 2, 6], "size": 3, "cap": 10})]
print("\nBUG INJECTION:")
for label, s in bugs:
    caught = [n for n, _ in survivors if not dict(CANDIDATES)[n](s)]
    print("  %s %r" % (label, s))
    print("    caught by: %s" % (", ".join(caught) if caught else "NOTHING"))
```

Real output of the script above (verified byte-identical across two runs):

```text
training states: 20 (generator: sorted distinct items, size <= cap)

SURVIVED over all 20 states:
  [x] size == len(items)
  [x] size <= cap
  [x] items non-decreasing
  [x] no duplicate items

DISCARDED (violated by training data):
  [ ] size >= 1            violated by: {'items': [], 'size': 0, 'cap': 10}
  [ ] max(items) <= cap    violated by: {'items': [6], 'size': 1, 'cap': 5}

BUG INJECTION:
  A: off-by-one size {'items': [3, 5], 'size': 3, 'cap': 8}
    caught by: size == len(items)
  B: insert out of order {'items': [9, 2, 6], 'size': 3, 'cap': 10}
    caught by: items non-decreasing
```

How to read it, including the two traps:

- **Four candidates survived; three are plausibly real.** Sortedness, the
  `size <= cap` bound, and `size == len(items)` are contracts a human would
  write, and each injected bug was caught by exactly the right invariant.
- **`no duplicate items` survived and should not have.** `random.sample` draws
  distinct values, so no training state could ever refute it: one line of
  generator code manufactured a lifetime invariant -- the sample-distribution
  trap in miniature.
- **`max(items) <= cap` died for the opposite reason:** item values range to 11
  while caps stop at 10, so one legitimate state refuted it -- discarded does
  not mean unintended, it means the data said no.
- **Every discarded candidate is a free refutation** -- each elimination is
  information about the structure.

## How this shows up in interviews

1. Daikon official page, UW PLSE (verified live; legacy MIT CSAIL page groups.csail.mit.edu/pag/daikon/ rejects plain HTTP clients with 403): <https://plse.cs.washington.edu/daikon/>
2. Daikon source repository: <https://github.com/codespecs/daikon>
3. M. D. Ernst, J. Cockrell, W. G. Griswold, D. Notkin, "Dynamically Discovering Likely Program Invariants to Support Program Evolution," IEEE TSE 27(2), 2001. <https://doi.org/10.1109/32.908957>
4. M. D. Ernst et al., "The Daikon system for dynamic detection of likely invariants," Science of Computer Programming 69(1-3), 2007. <https://doi.org/10.1016/j.scico.2007.01.015>
5. D. Engler, B. Chen, S. Chou, D. Hallem, "Bugs as Deviant Behavior: A General Approach to Inferring Errors in Systems Code," SOSP 2001. <https://doi.org/10.1145/502034.502041>
6. A. Wasylkowski, A. Zeller, C. Lindig, "Detecting Object Usage Anomalies," ESEC/FSE 2007. <https://doi.org/10.1145/1287624.1287632>
7. A. Wasylkowski, A. Zeller, "Mining Temporal Specifications from Object Usage," ASE 2009. <https://doi.org/10.1109/ASE.2009.30>
8. Z. Li, Y. Zhou, "PR-Miner: Automatically Extracting Implicit Programming Rules and Detecting Violations in Large Software Code," OSDI 2004. <https://www.usenix.org/legacy/events/osdi04/tech/full_papers/li_z/li_z.pdf>
9. F. Vaandrager, "Model Learning," Communications of the ACM 60(2), 2017. <https://doi.org/10.1145/2967606>
10. E. T. Barr, M. Harman, P. McMinn, M. Shahbaz, S. Yoo, "The Oracle Problem in Software Testing: A Survey," IEEE TSE 41(5), 2015. <https://doi.org/10.1109/TSE.2014.2372785>
11. C. Flanagan, K. R. M. Leino, "Houdini, an Annotation Assistant for ESC/Java," FME 2001. <https://doi.org/10.1007/3-540-45251-6_29>
12. C. Le Goues, W. Weimer, "Measuring Code Quality to Improve Specification Mining," IEEE TSE 38(1), 2012. <https://doi.org/10.1109/TSE.2011.5>
13. X. Hou et al., "Large Language Models for Software Engineering: A Systematic Literature Review," arXiv:2310.03533. <https://arxiv.org/abs/2310.03533>

## Related pages

- [Testing + Formal Methods](./testing-formal.md) -- testing versus proving; mined invariants as test oracles
- [Program Verification](./program-verification.md) -- what happens when mined annotations meet a prover
- [Symbolic Execution and Concolic Testing](./symbolic-execution.md) -- the other way to extract behavior from code
- [Property-Based Testing](../testing/property-based-testing.md) -- where mined properties become executable oracles
