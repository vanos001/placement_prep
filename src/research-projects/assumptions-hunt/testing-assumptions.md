# Testing Assumptions: What "Tests Pass" Silently Promises

## Overview

"Tests pass, so it works" and "more coverage means fewer bugs" are the two most quoted sentences in software quality, and both are conditional statements whose conditions almost never get stated. A green suite certifies that the tests you wrote passed — which silently assumes the tests model real usage, the mocks mirror the real collaborators, the order of execution is irrelevant, the flakiness is environmental noise rather than signal, and the coverage number measures assertion rather than mere execution. Each of those assumptions fails in a well-characterized way, and the failures have a shared signature: the suite stays green while the system misbehaves, which is the most expensive failure mode in software because it destroys the team's only source of confidence.

This chapter audits the family with the collection's five-step pattern. Citations lean on the primary literature of testing: Dijkstra's formulation of what testing can prove, Fowler's coverage essays, the property-based-testing lineage from QuickCheck to Hypothesis, and the mutation-testing argument. Where a failure has a documented incident in this repo's casebook — Therac-25, Knight Capital, Ariane 5 — the chapter links rather than retells.

## Assumption 1: "Tests Pass, So It Works"

### The taught rule

A comprehensive test suite that runs green is evidence the system works; CI enforces it on every change, so regressions cannot reach production.

### The hidden assumptions

- Tests sample the input space; a green run certifies the sampled inputs only. Dijkstra's line from "Notes on Structured Programming" (1970) remains the sharpest statement: testing can show the presence of bugs, never their absence — the suite is evidence, not proof.
- The tests model the usage their author imagined. Systems fail most often at boundaries the author did not imagine: zero, maximum, concurrent access, reordered events, adversarial input — the same boundary catalog this collection audits chapter by chapter.
- "Works" is scoped to the tested envelope. Code reused in a new context runs outside the conditions it was tested under, and passes none of the tests again by virtue of having passed them once.
- The suite itself is code with bugs; a broken assertion, a stale snapshot, or a mock that encodes a misunderstanding tests the misunderstanding forever.

### Counterexample

The casebook chapters in this repo are the counterexample catalog. Ariane 5 (linked below): the inertial-reference code was exhaustively tested — against Ariane 4 trajectories; flying it on Ariane 5 placed it outside its tested envelope, and the untested alignment condition threw within 37 seconds of launch, twice. Knight Capital (linked below): the deployment left a dead power-flag on a server, activating a code path whose testing had been retired with the flag — the "works" evidence predated the path that executed. Therac-25 (linked below): race-dependent hardware-timing assumptions passed every test run conducted on faster machines. In each case the suite — to the extent one existed — was green; the gap was between the tested envelope and the executed envelope.

### What changes when the assumption is removed

Corrected statement: *a green suite certifies that the tested behaviors, under the tested conditions, in the tested order, behaved as asserted — nothing more; the engineering question is whether the tested envelope matches the production envelope.* Practical responses: enumerate the envelope explicitly (inputs, timing, concurrency, failure injection, scale) and check each axis against production reality; treat "this code passed its tests" as a statement with a date and an environment attached; and keep the suite honest by testing behavior (observable outputs) rather than implementation detail, so refactorings do not silently invalidate the evidence.

### Consequences

The interview question "tests are green but production failed — walk me through how" expects exactly this envelope analysis. The corollary for code review: the highest-value thing to read in a pull request is often what the tests *cannot* see.

## Assumption 2: "Mocks Mirror the Real Thing"

### The taught rule

Unit tests substitute fast, deterministic mocks for slow, nondeterministic collaborators — the database, the HTTP client, the clock — and the suite stays hermetic.

### The hidden assumptions

- A mock encodes an *assumed* contract. The real collaborator evolves (new error codes, new pagination semantics, new rate limits) and the mock keeps encoding the old world — contract drift, invisible to a suite that only ever talks to the mock.
- Mocks return success by default. The real client throws on timeout, returns 429s, paginates at 100 items, and reorders; the mock that "never throws while the real client does" trains the code to skip error paths that production executes on day one.
- Some of the system's most important behavior *is* the collaborator's behavior: constraint violations, retry amplification, isolation anomalies (the database-isolation chapter's subject) cannot be reproduced by a stand-in that has no isolation to violate.

### Counterexample

An order service's client for the inventory API is unit-tested against a hand-rolled mock that always returns 200 with a JSON body. Production has three behaviors the mock lacks: 429 responses under load, 207-style partial failures, and — after an API evolution — a new error enum value (the additive-change trap in the API contracts chapter). The first production incident looks like this: inventory returns the new error code; the client's untested error branch treats it as a network failure and retries; the retry amplification (the timeout chapter's arithmetic) turns a single degraded call into a storm. The suite stayed green through the entire causal chain because every link ran through the mock, and the mock had none of the failure modes. The corrected pairing: contract tests against the real API contract (Pact's consumer-driven model, linked in the API contracts chapter) verify the assumptions the mock encodes, and integration tests at the real seams (testcontainers-style real databases and queues) verify the behavior mocks cannot encode.

### What changes when the assumption is removed

Corrected statement: *a mock is a hypothesis about the collaborator's contract; the suite is only as honest as the last time that hypothesis was checked against the real thing.* Use mocks for speed on the inner loop, but check the hypotheses: consumer-driven contract tests for service boundaries, real-dependency integration tests for the seams where behavior concentrates (transactions, retries, consistency), and stubs that *do* implement the error paths rather than only the happy path.

### Consequences

The interview probe "your unit tests are green and the integration failed — why did the mock lie?" is this section. The frontend testing page shows the same mock-drift issue at the UI boundary; the software-engineering testing page situates the test pyramid that balances mock speed against integration honesty.

## Assumption 3: "More Coverage = Fewer Bugs"

### The taught rule

Coverage percentage measures test quality; raising it to 80% (or 100%) reduces bugs proportionally, so teams set it as a gate.

### The hidden assumptions

- Coverage measures *execution*, not *verification*: a test that calls the function and asserts nothing executes every line. 100% line coverage with zero assertions is constructible in an afternoon and proves nothing beyond "the code runs".
- Line coverage hides branch and condition coverage; the untested half of every `if` is invisible at 90% line coverage if the taken half is well covered.
- The correlation between coverage and defect rate is real but weak and saturating — Fowler's TestCoverage essay (linked) makes the standard argument, and Google's Testing Blog made the same point publicly ("Code Coverage Best Practices", 2010: coverage is a useful diagnostic, not a target). Coverage's information content is highest as a *floor* (this module has zero tests) and decays as a *target* (this module has 94%).
- Goodhart's law applies: once coverage becomes the metric, tests optimize for the metric — assertion-free lines, trivial getters, excluded files.

### Counterexample

Two forms, both real and reproducible. *The vacuous suite:* `function testProcess() { processOrder(sampleInput); }` — green, 100% line coverage of `processOrder`, zero assertions; it would pass identically if `processOrder` corrupted every order. Nothing in the coverage number distinguishes this test from a real one, which is precisely why the number cannot measure quality. *The surviving mutant:* mutation testing (DeMillo, Lipton, and Sayward's 1978 idea, now standard tooling) flips a `<=` to `<` in the discount logic and reruns the suite — green. The suite executes the mutated line (coverage says so) but no assertion distinguishes the two behaviors, so the mutant survives, and every surviving mutant is a bug the suite is structurally unable to catch. A suite can score 95% and still survive a large fraction of mutants; a suite that kills the mutants is doing the thing coverage was assumed to measure.

### What changes when the assumption is removed

Corrected statement: *coverage is a floor and a diagnostic — it answers "what is definitely untested?" and cannot answer "what is well tested?" — so treat low coverage as a gap, high coverage as a hygiene floor, and measure assertion strength with mutation testing where the stakes justify it.* The strongest single upgrade to a suite is not more coverage but stronger oracles: property-based testing (QuickCheck, Claessen and Hughes, ICFP 2000; its most popular current implementation is Hypothesis, linked) generates inputs and checks *invariants* — round-trips, idempotence, conservation laws — which is how suites find the boundary bugs hand-picked examples never sample.

### Consequences

"Your coverage is 85% — why is that number nearly meaningless?" is a complete senior interview answer in one sentence plus the mutation-testing example. The engineering discipline it maps to: gate on *new* code being covered (the floor), review tests for their assertions (the substance), and let property tests cover the input space (the breadth).

## Assumption 4: "Flaky Tests Are Noise" (and Tests Are Order-Independent)

### The taught rule

A test that fails intermittently is an environmental problem — timing, CI resources — and should be retried or skipped; deterministic suites are the norm, so order does not matter.

### The hidden assumptions

- Flakiness is signal until proven otherwise. The two most common real causes are time and concurrency, and concurrency-dependent flakiness is often the *only* observable manifestation of a data race — the memory-model chapter's subject — which the suite is reporting through the only channel it has.
- Time-dependent tests (sleep-based waits, "now" used directly, timezone-local assertions) flake on slow CI; the fix teams reach for — longer sleeps and retries — converts a deterministic bug into a probabilistic one and trains the suite to tolerate the race it detected.
- Suites that share state (a singleton, a database row, a temp directory) pass in alphabetical order and fail shuffled; the order dependence means every "green" run is one of several possible experiments, and the result is not a property of the code at all.
- Retrying flaky tests until green converts the suite from a verifier into a lottery: the team's confidence number now includes an unknown failure rate hidden by the retry policy.

### Counterexample

A payment-processor test suite includes `testConcurrentRefund`, which fires two refunds concurrently and asserts the balance decreases exactly once. It fails roughly one run in forty in CI, always on the busy shared runner; the team adds a retry decorator. Eight months later, double refunds are reported in production. The flaky test was the race detector: the refund path checked-then-acted on a balance without synchronization (the concurrency-and-scheduling chapter's check-then-act audit applies verbatim), and the assertion failed exactly when the interleaving hit the window. The retry policy — not the race — made the suite green, and the production incident reproduced the CI failure at transaction scale. The corrected handling: treat a flaky test as a defect in either the test's determinism or the code's synchronization; fix or quarantine *with an owner and a deadline*, run order-shuffled suites to expose state leaks, inject clocks, and run the race detector (TSan, Go's `-race`) in CI where the platform offers one.

### What changes when the assumption is removed

Corrected statement: *a deterministic suite is the deliverable, and every flaky failure is one of three named things — a nondeterministic test, a state leak, or a real race — each of which has an owner, a diagnosis, and a fix; retries exist for genuinely environmental noise only, and they must not be the default policy.* Chaos engineering (the repo has a dedicated page) extends the same principle in the other direction: deliberately nondeterministic experiments in production, with the suite of *invariants* — rather than individual assertions — as what must stay green.

### Consequences

The interview escalation "how do you make a flaky test suite trustworthy again?" touches every chapter of this collection: determinism (time, seeds, order), isolation (state), synchronization (races), and honesty of metrics (no retry-laundered greens). Teams that rebuild the trust once rarely lose it again — the quarantine-and-fix loop is a habit, not a project.

## Interview Questions

1. **What does a green test suite actually certify?** That the tested behaviors, under tested conditions, in the tested order, behaved as asserted. It is evidence against the tested envelope, not proof about the production envelope — Dijkstra's presence/absence formulation is the anchor.
2. **How do mocks lie, and what catches the lies?** They encode an assumed contract that drifts from the real collaborator and they default to success, hiding error paths. Consumer-driven contract tests verify the encoded assumptions; integration tests at real seams verify behavior mocks cannot encode (constraints, isolation, retries).
3. **Why is 100% coverage compatible with zero bug detection?** Coverage measures execution, not verification: assertion-free tests execute lines without checking anything, and mutation testing exposes the gap — a surviving mutant (e.g., `<=` flipped to `<`, suite still green) is proof the suite cannot detect the difference.
4. **What are the three things a flaky test can be, and what is the policy for each?** A nondeterministic test (fix the test: inject the clock, control seeds), a state leak (fix isolation: shuffle order, reset shared state), or a real race (fix the code: synchronization, race detector). Retries are for environmental noise only — never a default that launders real failures.
5. **Where does property-based testing fit relative to example-based tests?** Examples encode known cases; property tests generate inputs against invariants (round-trip, idempotence, conservation), sampling boundaries no author thinks to hand-write. The lineage is QuickCheck (Claessen & Hughes, 2000) through Hypothesis; it complements, not replaces, behavioral example suites.

## Key Takeaways

- A green suite is evidence with a scope: the tested envelope, not the production one — Ariane 5, Knight Capital, and Therac-25 are the casebook forms of the gap.
- Mocks are hypotheses about contracts; contract tests and real-seam integration tests are what keep the hypotheses honest.
- Coverage is a floor and a diagnostic, never a target: assertion-free lines count, mutants survive, and Goodhart's law applies the moment the number becomes the goal.
- Property-based testing upgrades the oracle, not the coverage: generated inputs against stated invariants find boundary bugs example suites structurally miss.
- Flaky tests are signal until proven otherwise — the three-way diagnosis (nondeterministic test, state leak, real race) turns the suite from a lottery back into a verifier.
- The correct statement of the taught rule: "tests pass" certifies the tests, and only the discipline of keeping tests honest lets you infer anything about the system.

## Cross-References

- [Testing (software engineering)](../../software-engineering/testing.md) — the pyramid, test doubles, and CI discipline.
- [Testing (frontend)](../../frontend/testing.md) — mock drift and flakiness at the UI boundary.
- [Chaos engineering](../../sre/chaos-engineering.md) — invariant-based confidence under deliberate nondeterminism.
- [Concurrency and scheduling](concurrency-and-scheduling.md) — the check-then-act and interleaving assumptions flaky tests expose.
- [Memory model](memory-model.md) — data races and visibility, the deepest cause of "passes sometimes".
- [Ariane 5 1996](../failure-casebook/ariane-5-1996.md) — tested-envelope versus executed-envelope, with primary sources.
- [Knight Capital 2012](../failure-casebook/knight-capital-2012.md) — the untested path that activated in production.
- [Therac-25](../failure-casebook/therac-25.md) — race-dependent failures passing every conducted test.
- [API contracts](api-contracts.md) — contract drift and the consumer-driven testing model.
- [Hypothesis](https://hypothesis.readthedocs.io/en/latest/) — property-based testing in practice, from the source.
- [TestCoverage (Fowler)](https://martinfowler.com/bliki/TestCoverage.html) — the coverage-as-diagnostic argument.
