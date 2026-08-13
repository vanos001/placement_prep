# Testing in Software Engineering

## Table of Contents

- [Why Testing Matters](#why-testing-matters)
- [Testing Levels](#testing-levels)
- [Testing Types](#testing-types)
- [Test-Driven Development (TDD)](#test-driven-development-tdd)
- [Behavior-Driven Development (BDD)](#behavior-driven-development-bdd)
- [Test Strategy](#test-strategy)
- [Test Doubles](#test-doubles)
- [Common Mistakes](#common-mistakes)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## Why Testing Matters

Testing is the engineering practice of verifying that software behaves as intended and
meets its requirements. It is not a phase tacked on at the end of a project — it is a
continuous activity that runs alongside development.

Testing matters because it:

- **Catches regressions** — a change in one module must not silently break another.
- **Documents behavior** — tests act as an executable specification of the system.
- **Enables refactoring** — you can restructure code confidently when tests guard its behavior.
- **Reduces cost** — a bug found in development is orders of magnitude cheaper to fix than one found in production.
- **Builds confidence** — teams ship faster when they trust their test suite.

> "Testing shows the presence, not the absence of bugs." — Edsger Dijkstra

## Testing Levels

| Level | Scope | Speed | Typical volume | Example |
|---|---|---|---|---|
| **Unit** | Single function/class in isolation | ms | 70–80% | `calculateDiscount(100, 10) == 90` |
| **Integration** | Multiple components together | seconds | 15–25% | Order service writes to and reads from a DB |
| **System** | The whole system against requirements | minutes | 5–10% | Full workflow across all subsystems |
| **End-to-End (E2E)** | Full user journey through the UI/API | minutes | 5–10% | Signup → browse → checkout |

### The Testing Pyramid

```
        /  \
       / E2E \         ← few, slow, expensive
      /-------\
     / Integr. \       ← moderate
    /-----------\
   /   Unit      \     ← many, fast, cheap
  /_______________\
```

The pyramid (Mike Cohn) says: write **many fast unit tests** and **few slow E2E tests**.
The **Testing Trophy** (Kent C. Dodds) shifts the emphasis to integration tests as the
best confidence-to-effort trade-off, with static analysis as the base.

## Testing Types

| Type | Purpose |
|---|---|
| **Functional testing** | Verify the system does what requirements say |
| **Non-functional testing** | Verify performance, security, usability, reliability |
| **Smoke testing** | Quick check that critical paths work before deeper testing |
| **Sanity testing** | Verify a specific fix or change works as expected |
| **Regression testing** | Ensure previously working features still work |
| **Load testing** | Behavior under expected load |
| **Stress testing** | Behavior beyond expected load until failure |
| **Soak testing** | Behavior under sustained load over time |
| **Property-based testing** | Verify invariants hold for many generated inputs (Hypothesis, QuickCheck) |
| **Fuzz testing** | Feed random/malformed input to find crashes and leaks |
| **Mutation testing** | Introduce deliberate bugs to check whether tests catch them |
| **Contract testing** | Verify the agreed API contract between services (Pact) |
| **Snapshot testing** | Compare rendered output against a stored snapshot |

## Test-Driven Development (TDD)

TDD is a discipline where tests are written **before** production code, in a short cycle:

```
RED → GREEN → REFACTOR
```

1. **Red** — write a failing test that expresses the desired behavior.
2. **Green** — write the minimum code to make the test pass.
3. **Refactor** — clean up the code while tests stay green.

```python
# RED: the test defines the API we want
def test_stack_pop_returns_last_pushed():
    s = Stack()
    s.push(1)
    s.push(2)
    assert s.pop() == 2          # fails: Stack doesn't exist yet

# GREEN: minimal implementation
class Stack:
    def __init__(self): self.items = []
    def push(self, x): self.items.append(x)
    def pop(self): return self.items.pop()

# REFACTOR: improve without changing behavior
```

### Benefits and Costs

**Benefits:** forces a clear API, drives design, guarantees every behavior is tested,
gives a fast feedback loop, and results in a regression suite you trust.

**Costs:** slower in the very short term, requires discipline, can tempt over-testing
trivial code, and is hard to apply to exploratory/UI-heavy work.

## Behavior-Driven Development (BDD)

BDD extends TDD by expressing scenarios in **business-readable language** so that
developers, testers, and non-technical stakeholders share a common vocabulary.

The classic format is **Given–When–Then** (Gherkin):

```gherkin
Feature: Withdraw money
  Scenario: Withdraw within balance
    Given an account with balance 100
    When I withdraw 30
    Then the balance should be 70
```

Tools: **Cucumber** (Ruby/Java), **SpecFlow** (.NET), **Behave** (Python), **Gauge**.

The value of BDD is not the tool — it is the shared understanding of *what success
looks like* before implementation starts.

## Test Strategy

A test strategy describes **what** will be tested, **how**, and **to what depth**,
given the project's risk profile and constraints.

Key elements:

- **Scope** — which components and behaviors are in/out of scope.
- **Levels** — the mix of unit, integration, and E2E tests.
- **Environment** — local, CI, staging, production canaries.
- **Data** — test data strategy, fixtures, anonymization.
- **Entry/exit criteria** — when testing starts and when it is "done".
- **Risk-based prioritization** — test the riskiest paths most heavily.

### Test Isolation

Tests must be **independent**: each test sets up its own state and cleans up after
itself. Shared state between tests is the leading cause of flaky, order-dependent suites.

## Test Doubles

| Double | What it does |
|---|---|
| **Dummy** | Passed around but never used (satisfies parameters) |
| **Stub** | Returns canned answers to calls made during the test |
| **Fake** | Working implementation with a shortcut (in-memory DB) |
| **Spy** | Records calls so you can assert on them |
| **Mock** | Pre-programmed expectations; fails if calls differ |

Use doubles to isolate the unit under test from slow or non-deterministic
dependencies (databases, networks, clocks). Over-mocking leads to brittle tests that
verify implementation instead of behavior.

## Common Mistakes

| Mistake | Consequence |
|---|---|
| Testing implementation, not behavior | Tests break on every refactor |
| One giant test for 20 behaviors | Hard to locate failures |
| Shared state between tests | Flaky, order-dependent results |
| No assertions (smoke-only "tests") | False confidence |
| Ignoring flaky tests | Team stops trusting the suite |
| Chasing 100% coverage | Low-value tests on trivial code |

## Interview Questions

### Beginner
- What is the difference between unit, integration, and end-to-end testing?
- What is a regression test, and why is it important?
- What does the testing pyramid suggest about test distribution?

### Intermediate
- Explain the TDD cycle and one benefit and one drawback.
- What is the difference between a mock, a stub, and a fake?
- What is BDD, and how does Given–When–Then help a team?

### Advanced
- What is property-based testing, and when is it more valuable than example-based tests?
- What is mutation testing, and what problem does it solve?
- How would you design a test strategy for a payment-processing service?

### Common Traps
- "It has 100% coverage, so it's well tested" — coverage measures execution, not assertion quality.
- Confusing smoke and sanity testing.
- Over-mocking to the point that tests only verify the mocks themselves.

## References

- [Martin Fowler — TestPyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Kent C. Dodds — The Testing Trophy](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications)
- [ISTQB Glossary](https://glossary.istqb.org/)
- [Google Testing Blog — Test Sizes](https://testing.googleblog.com/2010/12/test-sizes.html)
- [Uncle Bob — The Three Laws of TDD](https://blog.cleancoder.com/uncle-bob/2014/12/17/TheCyclesOfTDD.html)

---

For a deeper, dedicated treatment (including mocking, contract testing, and CI
integration), see the [Testing section](../testing/README.md) of this book.
