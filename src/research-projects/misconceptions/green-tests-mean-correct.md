# "All tests pass, so the code is correct"

## Overview

A green build is the most persuasive object in software engineering: the
checkmark appears, the merge button lights up, and the inference "tests pass,
therefore the code is correct" completes itself silently in everyone's head.
This page audits that inference and finds it false — not because tests are
worthless, but because "correct" is a universal quantifier that no finite
suite can discharge. Tests sample the behavior space; assertions choose what
is observed; the oracle (the thing that decides right from wrong) is the same
fallible human understanding that wrote the code. The honest version of the
claim is narrower and still useful: a green suite proves that, on the inputs
the suite exercises, the program behaved as the assertions expected. This
page works the arithmetic of sampling and mutation, shows where the inference
breaks, and marks the one regime — the regression ratchet — where green
genuinely pays.

## The Claim, Stated Fairly

The strongest common form is: "Our CI runs 4,000 tests and they all pass on
every commit; the suite would catch mistakes, so code that is green is code
that works." This is not naivety. It is the daily operational meaning of a
test suite, and in most teams green code does, in fact, mostly work. The
claim deserves its fairness because it encodes a real, repeatedly rewarded
experience: the one time a developer removed a test, the behavior it guarded
broke within a month, and the suite caught dozens of regressions nobody would
have found by hand.

The question is whether the experience honestly generalizes to "correct".
Correct means: for all valid inputs, configurations, timings, and
interleavings, the program produces the specified outputs. A suite is a
finite list of runs. The claim silently upgrades a sample to a proof, and
the rest of this page is about what that upgrade costs.

## Verdict

**False.** A passing test suite demonstrates the absence of the specific
failures it can detect, on the specific inputs it exercises, checked by the
specific assertions it contains. A counterexample where every test passes
and the code is nonetheless wrong requires no exotic machinery: a test that
executes the wrong behavior without asserting on the wrong value, or a
specification bug copied identically into code and test, defeats the
inference completely. Dijkstra's observation — that testing can show the
presence of bugs but never their absence — is not a slogan here but the
exact shape of the logic.

## Why People Believe It

The kernel of truth has three parts, and each is real. First, tests do catch
re-breakage: once a behavior is encoded in an assertion, later changes that
alter that behavior turn the suite red. Teams watch this happen weekly, and
the causal link between green and "still working" is genuine for covered
behavior. Second, suites accumulate: a 4,000-test repository has, by
construction, a large sample of historically important inputs, and the
probability that a random change breaks something unobserved falls as the
suite grows. Third, testing is the best widely deployed evidence-producing
practice we have; the alternatives (formal verification at scale, proofs
over real code) are expensive and rare, so "green" is the strongest signal
most engineers ever hold.

What disappears in compression is the difference between evidence and
proof. A suite is a sample of the behavior space, and samples license
inference about what was sampled. Consider the arithmetic: a function that
takes two 64-bit integers has 2^128 ≈ 3.4 × 10^38 possible input pairs. A
dedicated suite with 50 test cases for that function samples 50 of them —
about 1.5 × 10^-37 of the space. Even a million cases on a thousand such
functions leaves each function's coverage of its own input space below
10^-30. Nothing about those numbers is pessimism; it is just counting, and
counting says the suite's verdict about unsampled inputs is extrapolation,
not observation.

The second compressed element is the oracle. A test compares observed
behavior against an expectation, and the expectation was written by a
person, from the same understanding (or the same ticket, or the same flawed
spec) that produced the implementation. When the misunderstanding is shared,
code and tests agree perfectly and the suite glows green over incorrect
software. The third element is assertion strength, which most suites never
measure at all — a gap that mutation testing, covered below, makes visible
and numeric.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "The code is correct" | No finite suite proves correctness; green shows bugs absent *from the sampled region, at the sampled strength* |
| "The behavior is verified" | Only the executed inputs are verified, and only as strongly as the assertions check them |
| "The suite is strong" | Assertion strength is measurable (mutation score), and suites vary from near-zero to near-one |
| "The spec is right" | Tests encode the spec as understood; shared misunderstandings produce consistent, green, wrong systems |
| "Untested code is broken" | Untested does not mean incorrect — coverage and correctness are different axes |
| "Testing is worthless then" | False — as a regression guard, the suite is the highest-value safety net in the building |

The corrected sentence: "All tests pass" means that, on the specific inputs,
configurations, and timings the suite exercises, the program's observable
behavior matched the assertions, and the assertions matched someone's
understanding of the requirements. Any claim about inputs the suite does not
exercise, or about behavior the assertions do not observe, is extrapolation
and should be labeled as such.

Two techniques convert the vague gap into a measurable one. Property-based
testing changes what is sampled: instead of hand-picked examples, the
framework generates hundreds or thousands of inputs per property
automatically, shrinking counterexamples to minimal form when one fails —
Hypothesis, for example, generates cases from declared strategies and then
minimizes failures before reporting them. Mutation testing changes what is
measured: the tool injects small faults (flip a comparison, delete a call,
change a constant) into the code and counts how many the suite kills. A
mutant that survives is a fault the suite would not catch — a direct,
itemized measurement of the distance between "executed" and "checked".

## Where It Breaks

**The oracle gap, concretely.** A payments module gets a test written on a
busy day:

```text
function test_transfer_moves_money():
    transfer(account_a, account_b, 50)
```

The function executes; no exception is raised; the test passes; line
coverage reports the transfer path covered. Nothing in the suite asserts
that account A decreased by 50, that account B increased by 50, that the
operation is atomic, or that it is recorded. The suite is green and the
inference "the code is correct" is false on the very line the test was
written to protect. This is not a contrived bug — assertion-light tests are
the standard byproduct of coverage targets, as the sibling audit of the
90%-coverage claim details.

**Shared-blindness failures.** A tax rule is misread as "apply 8% to the
pre-discount price". The developer implements it; the tester writes the
expected value from the same reading; every test passes; customers are
overcharged for a quarter. The suite was not weak in any mechanical sense —
its assertions were strong and its inputs were reasonable. It failed because
the oracle and the implementation shared one source of truth that was wrong.
No amount of additional test cases of the same kind would have helped; only
an independent oracle (a second derivation, a property such as "tax is
invariant to line-item order", or a complaint from accounting) breaks the
symmetry.

**Sampling and interleavings.** A data structure passes 200 sequential unit
tests and every integration test, then corrupts itself in production on
week two. The untested axis was concurrency: a resize racing with a reader.
A deterministic suite exercises one interleaving per test — the scheduler
happens to serialize operations the same way on every run, so the suite is
reproducibly green while the bug sits one preemption away. This is the
sampling argument applied to time: the behavior space of a concurrent
program includes its schedules, and a suite that never varies schedules is
sampling one point of that axis.

**Mutation arithmetic.** A 30-line pricing function produces 40 mutants
under a mutation tool. The suite kills 26 and 14 survive — a mutation score
of 65%, against a line-coverage figure of 96%. Each survivor is a concrete
finding: change `<` to `<=` and nothing fails; delete the rounding call and
nothing fails. The green suite was not lying about what it checked; it was
never asked what it would notice. (Caveat worth naming in interviews:
"equivalent mutants" — mutations with no observable behavioral difference —
can survive any suite, so mutation scores measure assertion strength, not
perfectly.)

**When it accidentally works: the regression ratchet.** The claim holds in
one specific, valuable regime. If a behavior was correct when its test was
written, the suite's lock on that behavior is real: any change that alters
the observed values turns red, and the team finds out before production.
This ratchet — green today proves "no covered behavior has re-broken", not
"no bug exists" — is the honest core of the belief, and it is why deleting
tests is a fireable offense in most mature codebases. The failure mode of
this page is not "stop trusting suites"; it is "stop upgrading the ratchet
into a proof".

## Practical Implications

- Treat green as evidence about sampled behavior, and say so in reviews:
  "this is covered and asserted" is a stronger sentence than "this is green".
- Spend effort where the sampling is weakest: boundary values, error paths,
  concurrency schedules, and configuration combinations are exactly what
  example-based suites under-sample.
- Measure assertion strength, not just execution: run a mutation tool on
  critical modules and treat survivors as named, fixable gaps.
- Use property-based testing on algorithmic code where an oracle exists
  (round-trips, invariants, references models) — it replaces guessing
  inputs with generating them.
- Write tests against requirements independently of the implementation
  where possible: derive expected values from the spec, a second person, or
  a property, not from running the code and copying its output.
- Keep the ratchet: never weaken or delete an assertion to make a red build
  green; that converts the one honest guarantee the suite offers into noise.

## Interview Questions

### Your CI is fully green. What exactly have you proven, and what have you not?

You have proven that on the inputs, configurations, and schedules the suite
exercises, observable behavior matched the assertions. You have not proven
correctness over unsampled inputs, behavior the assertions do not inspect,
or requirements the spec got wrong. A strong answer names the three gaps —
sampling, oracle, assertion strength — and notes the regression-ratchet
guarantee that green does provide.

### How would you detect that a test suite passes but checks nothing?

Mutation testing: inject small faults and count survivors. If most mutants
survive, the suite executes code without constraining it — the
assertion-free pattern. Cheaper proxies: grep the suite for tests with no
assertions or only trivial ones, and review whether expected values were
derived from the spec or copied from the implementation's output.

### Why can a suite be 100% passing and 100% covering while the feature is wrong?

Because coverage and passing measure execution, not verification, and
neither validates the spec. An assertion-free test covers lines without
checking them, and a correctly asserted test validates a wrong requirement
if code and test share the misunderstanding. The two sibling audits — this
page and the coverage page — fail at different links of the same chain.

### Where does the "green means correct" inference actually hold?

For re-breakage of behavior that was correct when captured: if the
assertions encode right behavior, green means that behavior has not
regressed. It also holds weakly as evidence — a large suite with strong
assertions raises the probability that untested behavior is fine, without
ever licensing certainty. Interviews reward candidates who give the ratchet
formulation instead of either extreme.

### What is the role of property-based testing relative to example tests?

It changes the sampling strategy. Example tests encode point beliefs about
specific inputs; property tests declare invariants and let the framework
generate hundreds of inputs, including boundary shapes humans skip, then
shrink any failure to a minimal counterexample. The two compose: examples
pin known regressions, properties sweep the space around them.

## Key Takeaways

- "All tests pass" is a statement about a sample; "the code is correct" is
  a statement about a universe. The inference between them is never valid.
- The three gaps are sampling (which inputs ran), oracle (who says the
  expectation is right), and assertion strength (whether the run was
  observed). Mutation testing measures the third directly.
- Shared misunderstandings produce green suites over wrong software; no
  volume of same-kind tests fixes an oracle problem.
- The honest guarantee is the regression ratchet: covered, correctly
  asserted behavior does not re-break silently. That guarantee is real and
  valuable.
- Upgrades that shrink the gap: property-based generation, independent
  oracles, mutation scores, and deliberately varied concurrency schedules.

## Cross-References

- [Misconceptions: coverage-means-tested](./coverage-means-tested.md) — the
  sibling audit: coverage measures execution, not assertion strength, and
  targets corrupt both
- [Assumptions Hunt: Testing Assumptions](../assumptions-hunt/testing-assumptions.md)
  — the hidden assumptions behind "the tests cover it"
- [Misconceptions: average-case-complexity](./average-case-complexity.md) —
  the same sampling failure in performance: averages over a distribution
  license nothing about adversarial inputs
- [Testing: Mutation Testing](../../testing/mutation-testing.md) — how
  survivors are generated, scored, and triaged
- [Testing: Property-Based Testing](../../testing/property-based-testing.md)
  — generation and shrinking mechanics behind the sweep
- [Testing: Unit Testing](../../testing/unit-testing.md) — where example
  tests fit and what they promise
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- E. W. Dijkstra. *Notes on Structured Programming*, 1970 — origin of the
  "testing shows the presence, not the absence, of bugs" observation, cited
  by title.
- DeMillo, Lipton, and Sayward. *Hints on Test Data Selection: Help for the
  Practicing Programmer*, IEEE Computer, 1978 — the mutation-testing
  hypothesis, cited by title.
- Hypothesis documentation: strategies, generation, and shrinking.
  <https://hypothesis.readthedocs.io/en/latest/>
