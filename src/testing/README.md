# Testing

> "Testing shows the presence, not the absence of bugs." — Edsger Dijkstra

## Why Testing Matters

Software testing is the process of evaluating a system to find defects and verify it meets requirements. It's not an afterthought — it's a core engineering practice that:

- **Prevents regressions** — changes don't silently break existing features
- **Documents behavior** — tests serve as executable specifications
- **Enables refactoring** — change code confidently knowing tests will catch mistakes
- **Reduces cost** — bugs caught early are orders of magnitude cheaper to fix
- **Builds confidence** — teams ship faster when they trust their test suite

## The Testing Pyramid

The testing pyramid, coined by Mike Cohn, describes the ideal distribution of tests:

```
        /  \
       / E2E \          ← Few, slow, expensive
      /-------\
     / Integr. \        ← Moderate count, moderate speed
    /-----------\
   /   Unit Tests \     ← Many, fast, cheap
  /_______________\
```

### Unit Tests (Base)
- **What:** Test individual functions, methods, or classes in isolation
- **Speed:** Milliseconds
- **Scope:** Single unit, mocked dependencies
- **Volume:** 70-80% of your test suite
- **Example:** Testing that `calculateDiscount(price, percentage)` returns the correct value

### Integration Tests (Middle)
- **What:** Test how multiple components work together
- **Speed:** Seconds
- **Scope:** Multiple units, real or test databases, APIs
- **Volume:** 15-25% of your test suite
- **Example:** Testing that an order service correctly reads from and writes to the database

### End-to-End Tests (Top)
- **What:** Test the entire system from the user's perspective
- **Speed:** Minutes
- **Scope:** Full application stack, UI, network
- **Volume:** 5-10% of your test suite
- **Example:** Testing a complete user journey from signup to checkout

## The Testing Trophy

Kent C. Dodds proposed an alternative — the **Testing Trophy** — emphasizing integration tests:

```
        ___
       / E2E \
      /-------\
     /         \
    / Integration\    ← Sweet spot: most value per test
   /_____________\
   |   Static     |   ← TypeScript, ESLint, type checking
   |   Analysis   |
   |______________|
   |    Unit      |   ← Testing pure business logic
   |______________|
```

The argument: integration tests give the best confidence-to-effort ratio. Unit tests are still valuable for pure logic, but over-mocking integration boundaries yields brittle, low-value tests.

## Testing Philosophy

### Test Behavior, Not Implementation

```python
# ❌ Bad: tests implementation details
def test_calls_database():
    service.get_user(1)
    assert database.query.called_once_with("SELECT * FROM users WHERE id=1")

# ✅ Good: tests behavior
def test_returns_user_when_exists():
    user = service.get_user(1)
    assert user.name == "Alice"
    assert user.email == "alice@example.com"
```

### The FIRST Principles

| Principle   | Description                                      |
|-------------|--------------------------------------------------|
| **Fast**    | Tests should run quickly — slow tests get skipped |
| **Independent** | Tests shouldn't depend on each other           |
| **Repeatable**  | Same result every time, any environment        |
| **Self-validating** | Pass or fail — no manual interpretation    |
| **Timely**  | Written at the same time as production code      |

### Arrange-Act-Assert (AAA)

Every test should follow this structure:

```python
def test_withdraw_decreases_balance():
    # Arrange — set up the scenario
    account = BankAccount(balance=100)

    # Act — perform the action
    account.withdraw(30)

    # Assert — verify the outcome
    assert account.balance == 70
```

### Test Naming Conventions

Good test names describe the behavior being tested:

```python
# Pattern: test_<unit>_<condition>_<expected_result>
test_calculate_discount_with_zero_percentage_returns_original_price
test_login_with_invalid_password_returns_401
test_sort_empty_list_returns_empty_list
```

## What to Test

### Always Test
- Business logic and domain rules
- Edge cases and boundary conditions
- Error handling and validation
- Public APIs and contracts

### Sometimes Test
- Complex algorithms
- Integration points
- Configuration loading
- Serialization/deserialization

### Usually Don't Test
- Getters and setters (trivial code)
- Framework code
- Third-party libraries
- Private implementation details that frequently change

## Test Coverage

Code coverage measures what percentage of code is executed by tests:

| Metric           | What It Measures                          |
|------------------|-------------------------------------------|
| **Line coverage**    | % of lines executed                    |
| **Branch coverage**  | % of if/else branches taken            |
| **Function coverage**| % of functions called                  |
| **Statement coverage**| % of statements executed              |

### Coverage Guidelines
- **80%+ line coverage** is a reasonable target for most projects
- **100% coverage is not the goal** — some code is not worth testing
- **High coverage ≠ good tests** — you can have 100% coverage with zero assertions
- Coverage helps find what you've *missed*, not prove what you've *tested*

## Testing in Different Paradigms

### Object-Oriented Testing
- Test public interfaces, not private methods
- Use dependency injection for testability
- Mock external dependencies

### Functional Testing
- Pure functions are trivially testable
- Test input → output transformations
- Property-based testing shines here (e.g., Hypothesis, QuickCheck)

### API Testing
- Test request/response contracts
- Verify status codes, headers, body structure
- Test error responses and edge cases

## Common Anti-Patterns

| Anti-Pattern               | Problem                                      | Solution                        |
|----------------------------|----------------------------------------------|---------------------------------|
| **Testing implementation** | Brittle tests that break on refactoring      | Test behavior, not internals    |
| **Mega tests**             | One test verifying 20 things                 | One assertion per concept       |
| **Shared test state**      | Tests interfere with each other              | Independent setup/teardown      |
| **No assertions**          | Code runs but nothing is verified            | Always assert expected outcomes |
| **Testing the framework**  | Wasting time on framework internals          | Trust the framework             |
| **Ignoring flaky tests**   | Random failures erode trust                  | Fix or delete — no in-between   |

## CI/CD Integration

Modern testing integrates with continuous integration:

```yaml
# Example GitHub Actions
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run test:unit
      - run: npm run test:integration
      - run: npm run test:e2e
```

### Best Practices for CI Testing
- Run unit tests on every push
- Run integration tests on pull requests
- Run E2E tests before merging to main
- Fail fast — run fastest tests first
- Cache dependencies to speed up builds

## Key Terminology

| Term               | Definition                                              |
|--------------------|---------------------------------------------------------|
| **SUT**            | System Under Test — the thing being tested              |
| **Fixture**        | Fixed state/setup used as a baseline for tests          |
| **Test double**    | Generic term for mocks, stubs, fakes, spies             |
| **Regression**     | A bug that was previously fixed but reappeared          |
| **Smoke test**     | Quick sanity check that critical paths work             |
| **Canary test**    | Test deployed to production to verify real-world behavior|
| **Fuzz testing**   | Providing random/malformed input to find crashes        |

## Section Contents

- [Unit Testing](unit-testing.md) — FIRST principles, AAA pattern, coverage, examples
- [Integration Testing](integration-testing.md) — test containers, contract testing, in-memory DB
- [End-to-End Testing](e2e-testing.md) — Playwright/Cypress, page object model, flaky tests
- [TDD & BDD](tdd-bdd.md) — Red-Green-Refactor, Given-When-Then, Cucumber
- [Mocking](mocking.md) — mocks vs stubs vs fakes vs spies, DI for testing
- [Test Strategy](test-strategy.md) — test pyramid/trophy, risk-based testing, CI testing
- [Interview Questions](interview-questions.md) — testing interview Qs at all levels
