# "90% code coverage means the code is well tested"

## Overview

Coverage is the easiest quality number to produce and the easiest to
misread. The claim that a 90% figure certifies a well-tested codebase
commits a category error that is simple to state and endlessly productive
in practice: coverage measures which code *executed*, not whether anything
*checked* the results. A test suite that calls every function and asserts
nothing reaches 100% coverage while verifying nothing; a suite can be
densely covering and thinly asserting; and the 10% left uncovered is
routinely exactly the error-handling paths that fail in production. This
page audits the claim, quantifies the execution-versus-verification gap
with mutation testing, works the path-explosion arithmetic that bounds
what coverage could even mean, and delineates it from the sibling audit of
the green-build inference. The verdict is false — with one honest regime,
coverage as a floor, where the metric genuinely pays.

## The Claim, Stated Fairly

The strongest common form is: "Our coverage report says 90% of lines are
executed by tests; the codebase is therefore well tested, and the
remaining 10% is edge dust." This deserves fairness on three counts. The
number is honestly computed by the tooling; teams with 90% coverage
usually *do* have substantial test suites, built through real effort; and
in the domain the metric was designed for — noticing large untested
tracts of a growing codebase — it reliably finds them.

The claim fails because "well tested" is a claim about verification:
behavior was observed and checked against expectations that are
themselves correct. Coverage certifies execution only. The gap between
"ran" and "checked" is not a rounding error; it is the entire content of
testing, and it can be near-zero at 100% coverage. The rest of this page
measures that gap and shows where the 90% reading leads teams astray.

## Verdict

**False.** A valid counterexample needs two lines: a test that calls the
function under test and asserts nothing executes the line, satisfies the
coverage tool, and verifies nothing — suites with many such tests reach
any coverage target while their mutation score, the share of injected
faults they detect, approaches zero. The metric measures the wrong
variable for the conclusion drawn: execution is an input to verification,
not a substitute for it. Coverage's honest meanings — a map of unexecuted
code and a ratchet against entropy — are real but categorically
different from "well tested".

## Why People Believe It

The kernel of truth is that coverage is correlated with test quality in
organically grown suites. Suites reach high coverage by accumulating
tests, tests accumulate assertions, and a codebase where 90% of lines run
under test is empirically safer to refactor than one at 30%. The number
also has real findings to its credit: dead modules discovered at 0%, a
branch that no test ever triggered, a migration path that had silently
rotted. Every engineer has seen coverage surface something real, which
makes the metric feel like a direct measurement of safety.

The compression error is a causal one. Coverage went up *because* tests
were added; the safety came from the assertions those tests carried.
Treating the number as the cause invites Goodhart's law: once coverage
becomes a target, teams optimize the metric, and the cheapest way to move
it is to write tests that execute lines without constraining behavior —
assertion-free tests, tests asserting on mocks re-recording the
implementation, tests copying the function's output back as the expected
value. Each of these raises coverage while adding nothing to the
verification the claim is really about.

The third reason is that the failure is invisible in the metric's own
units. Two suites, both at 90% coverage, can differ by an order of
magnitude in defect detection; nothing in the coverage report
distinguishes them. A number that cannot distinguish a strong suite from
an empty one cannot carry the conclusion "well tested" by itself.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "90% covered" | 90% of lines *executed* by some test at some point |
| "So it is well tested" | Tested = executed *and checked*; assertion strength is a separate, unmeasured axis |
| "The suite is strong" | Measure with mutation testing: kill-rate over injected faults, not line execution |
| "The uncovered 10% is edge dust" | The uncovered residue concentrates exactly where failures are expensive: error paths, retries, rollbacks, rare configs |
| "Line coverage is fine-grained" | Paths explode combinatorially: n branches are 2^n paths; loops multiply further — covering lines is far weaker than covering behavior |
| "So coverage is worthless" | False — as a floor and dead-code finder it is cheap and effective; as a target it corrupts |

The corrected sentence: "Our coverage is 90% *and* our mutation score on
critical modules is above 70%, with error paths covered by tests whose
expectations were derived independently of the implementation."
Coverage is one conjunct of the claim, not the claim.

The path arithmetic sharpens the point. A function with ten independent
`if` statements has 2^10 = 1,024 distinct paths; covering every *line*
can be done with a handful of inputs that wander through the code,
leaving 99% of behavioral combinations unexecuted. Add a loop and the
space multiplies again — iteration counts interact with the branches
inside. Coverage tools that report branch or condition coverage narrow
the gap, and MC/DC (modified condition/decision coverage, required for
safety-critical avionics software) narrows it further, but no execution
metric escapes the fundamental problem: the behavior space is
exponential in the program's decisions, and any execution report is a
summary of a sample of it. That is the same sampling gap the sibling
audit of "green means correct" works through; here it appears as the
metric's resolution, there as the suite's reach.

## Where It Breaks

**The assertion-free suite.** The canonical two-liner:

```text
function test_transfer_executes():
    transfer(account_a, account_b, 50)
```

No assertion, no verification, full credit on the coverage report. Scale
the pattern — a team under a coverage mandate converting integration
tests to "smoke" style, or generating tests from method signatures — and
the repository reaches its target while mutation testing reports a kill
rate in single digits. The 90% number and the "well tested" conclusion
are now maximally far apart, and nothing in the coverage dashboard
registers the difference.

**The missing 10% is the expensive 10%.** Look at what coverage
residue is made of: the catch blocks, the retry loops, the timeout
handlers, the compensation and rollback paths, the "should never happen"
branches. These are precisely the paths that (a) are hardest to arrange
in a test, and (b) fail in production at the worst moments. A team that
reads 90% as "well tested, remaining 10% is dust" has read the report
backwards: the residue is the map to the next outage. The fix is not
chasing 100% globally but naming the uncovered paths on critical flows
and deciding, path by path, whether each is tested elsewhere (fault
injection, chaos drills) or consciously accepted.

**How to manufacture 90%.** Coverage figures respond to configuration as
much as to testing. Exclude the generated code, the `main` entrypoints,
and the DTO layer; write mock-heavy tests where the mock's canned return
is both the stimulus and the expectation; assert on the collaborator
instead of the result. The report reads 90%; the suite verifies the
mocking framework. None of this requires dishonesty — each step is
defensible locally, which is why coverage targets reliably produce this
pattern: the metric is optimized, the verification is not.

**Mutation arithmetic.** Mutation testing makes the gap numeric: the
tool injects small faults (flip a comparison, change a constant, remove
a call) and counts how many the suite *kills*. A critical payments
module at 92% line coverage produces 47 mutants: 31 killed, 16 survive —
a 66% mutation score. The 16 survivors are itemized, reviewable gaps:
`<` instead of `<=` passes unnoticed, the rounding call can vanish,
a fee constant can drift. Coverage could not see any of this; the
mutation score summarizes it in one number, and the survivors convert
"improve testing" into a work list.

**The residue conversation that never happens.** Teams that read 90% as
a grade stop reading the report at the headline number, so the
conversation the metric was built to start — "what, specifically, is
uncovered, and does it matter?" — never occurs. The productive version
of the meeting is short and path-level: the payment retry loop is
uncovered (test it via fault injection), the currency-rounding branch
is uncovered (assertion quality is the real gap, not execution), the
CORS preflight handler is uncovered (accept it, in writing). Absent
that conversation, "90%" functions as a mood rather than a measure,
and the risk map the tool just handed over goes straight into the bin.

**When it accidentally works: the floor.** Coverage's honest regime is
anti-entropy. A ratchet — "changed files must not drop below N% branch
coverage" — prevents untested code from accreting in a legacy repository
without mandating the number game that a global target invites; diff
coverage in CI is the practical form. As a map, coverage reliably finds
dead code and never-executed branches worth a look. In that regime the
90% figure genuinely means something: the floor is holding. It still
means "executed", never "verified" — the floor keeps the sample from
shrinking; only assertion strength keeps it meaningful.

## Practical Implications

- Pair every coverage number with a mutation score on the modules that
  matter; report both or report neither.
- Prefer branch or condition coverage over line coverage where the tool
  supports it, and read the *residue*: the uncovered paths on critical
  flows are the work list.
- Resist global percentage targets; use ratchets (diff coverage, no-drop
  rules) that add tests where changes happen instead of farming easy
  lines.
- Audit for the assertion-free pattern directly: tests without
  assertions, expectations copied from the implementation's output, and
  assertions on mocks rather than results.
- Derive expected values independently — from the specification, a
  reference implementation, or a property — so the oracle does not
  inherit the code's mistakes.
- Treat uncovered error paths as explicit decisions: tested via fault
  injection, or accepted in writing; "uncovered" should never be
  discovered mid-incident.

## Interview Questions

### How can a suite reach 90% coverage and still miss serious bugs?

Because coverage records execution, not verification. Assertion-free
tests execute lines without checking them; asserted tests can encode the
same misunderstanding as the code; and the uncovered residue clusters on
error paths that fail in production. A strong answer adds the
quantitative check: mutation testing on critical modules, whose kill
rate reveals how much of the covered code the suite would actually
notice breaking.

### What is mutation testing, and why is it the natural companion to coverage?

It injects small faults into the code and counts how many the suite
detects — killed mutants over total mutants is the mutation score. It
measures the axis coverage ignores: whether executed behavior is
constrained by assertions. The two together answer complementary
questions — coverage says what ran; the mutation score says whether
running it would have mattered. Its caveat: equivalent mutants (behavior-
preserving faults) survive any suite, so scores measure assertion
strength, not perfection.

### Why does the uncovered 10% matter more than the covered 90%?

Because the residue is not random: it concentrates on error handling,
retries, timeouts, and rare configurations — the paths that are
hardest to test and most likely to fail under stress. The covered 90%
is the happy-path bulk; the uncovered 10% is the risk map. Reading the
residue and deciding its fate (test it, cover it with fault injection,
or accept it explicitly) is the highest-value use of a coverage report.

### Your team proposes a hard rule: no merge below 80% coverage. Argue both sides.

For: a ratchet prevents untested code accreting and keeps new logic
exercised in CI; cheap to enforce. Against: a hard global number
invites Goodhart — assertion-free tests, mocked assertions, and
excluded files that game the metric without adding verification. The
usual synthesis: ratchet on changed files (diff coverage), pair it with
review standards on assertion quality, and reserve mutation scoring for
critical modules where the number matters.

### How is this claim different from "all tests pass, so the code is correct"?

Different link of the same chain. The green-build audit rejects the
inference from suite *outcome* to correctness — even a strong suite
proves only its sample. This audit rejects the inference from a
*coverage metric* to suite quality — the number says nothing about
assertions at all. The first fails on sampling and oracles; the second
fails one level earlier, on what the measurement even measures.

## Key Takeaways

- Coverage measures execution; testing means verification. The gap
  between them is the whole subject, and it can be near-total at 100%.
- Mutation testing measures assertion strength and converts "improve
  tests" into itemized survivors; pair it with coverage or read neither.
- The uncovered residue maps the expensive paths — error handling and
  rare configurations — and deserves a decision, not a rounding.
- Targets corrupt the metric (Goodhart); ratchets preserve its honest
  use as a floor and dead-code finder.
- "90% covered" is a conjunction item, never a conclusion: executed,
  checked, and independently expected is the full sentence.

## Cross-References

- [Misconceptions: green-tests-mean-correct](./green-tests-mean-correct.md)
  — the sibling audit: this page rejects a coverage number as proof of
  suite quality; that page rejects the suite's green output as proof of
  correctness — mutation testing appears in both, as the direct measure
  here and as an oracle-gap detector there
- [Assumptions Hunt: Testing Assumptions](../assumptions-hunt/testing-assumptions.md)
  — the hidden assumptions behind "the tests cover it"
- [Testing: Unit Testing](../../testing/unit-testing.md) — where
  example-based suites and their assertions fit
- [Testing: Mutation Testing](../../testing/mutation-testing.md) — the
  tooling behind the kill-rate measurement used above
- [Testing: Property-Based Testing](../../testing/property-based-testing.md)
  — sweeping input space where an oracle exists, complementary to
  line-level coverage
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- PIT (pitest). *Mutation testing documentation* — mutation generation
  and scoring mechanics for JVM code. <https://pitest.org/>
- B. Marick. *How to Misuse Code Coverage*, 1999 — the classic treatment
  of coverage's failure modes, cited by title.
- C. Lemke. *Code Coverage Best Practices*, Google Testing Blog, 2017 —
  Google's guidance on coverage as a signal rather than a target, cited
  by title.
