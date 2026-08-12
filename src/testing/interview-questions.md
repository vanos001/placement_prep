# Testing Interview Questions

## Fundamentals

**What is the test pyramid?**

A strategy with many fast unit tests, fewer integration tests, and a small
number of end-to-end tests. It is a heuristic: risk, architecture, and failure
cost determine the right mix.

**Unit test versus integration test?**

A unit test isolates a small unit and controls dependencies. An integration test
checks real boundaries such as a database, queue, filesystem, or HTTP contract.
The value is not the label but the boundary being verified.

**What makes a test reliable?**

Deterministic inputs, isolated state, controlled time/randomness, clear failure
messages, cleanup, and no dependence on test order or external availability.

## Intermediate

**What is contract testing?**

It verifies an agreement between a provider and consumer, often at an API or
event boundary. It catches incompatible changes without requiring every full
end-to-end environment.

**How do you test asynchronous code?**

Control the scheduler or use deterministic test clocks where possible, await
explicit completion signals, bound retries, inspect queues and cancellation,
and test timeouts and duplicate delivery. Avoid arbitrary sleeps.

**What is mutation testing?**

The test tool changes code in small ways and checks whether tests fail. Surviving
mutants reveal assertions or branches that lack meaningful coverage.

**How do you test flaky behavior?**

Capture seed, timing, environment, logs, traces, and artifacts; reproduce with
controlled scheduling; distinguish product races from test-environment races;
then fix the cause instead of only adding retries.

## Advanced

**What is property-based testing?**

Generate many inputs from a model and verify invariants rather than only fixed
examples. Shrinking reduces a failing input to a small counterexample.

**How do you test a distributed system?**

Inject delays, duplication, reordering, dropped messages, process restarts,
clock skew, partition, partial writes, and resource exhaustion. Assert safety
invariants and eventual recovery separately.

**What is the difference between coverage and confidence?**

Coverage shows which code or branches executed. Confidence depends on assertion
quality, input diversity, realistic boundaries, failure injection, and whether
critical invariants are tested.

## Interview exercise checklist

- State the test contract before listing cases.
- Include happy path, boundary, invalid input, duplicate, timeout, retry, and
  concurrent cases.
- Separate unit, integration, contract, and end-to-end responsibilities.
- Explain test data isolation and cleanup.
- Report what the test would detect and what it cannot detect.

## Cross-references

- [Testing overview](./README.md)
- [Unit Testing](./unit-testing.md)
- [Integration Testing](./integration-testing.md)
- [Test Strategy](./test-strategy.md)
- [TDD and BDD](./tdd-bdd.md)
- [Distributed failure modes](../failure-modes/common-failures.md)
- [Research audit](../meta/status.md)

## References

- [Google Testing Blog](https://testing.googleblog.com/)
- [Martin Fowler: Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Property-based testing with Hypothesis](https://hypothesis.readthedocs.io/)
- [Pact contract testing](https://docs.pact.io/)
- [Playwright documentation](https://playwright.dev/docs/intro)
