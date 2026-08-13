# Test Strategy

A test strategy defines *what* to test, *how* to test it, and *when* to run each type of test. It's the blueprint that guides your team's testing efforts and ensures you get maximum confidence with minimum effort.

## The Test Pyramid Revisited

### Classic Pyramid (Mike Cohn)

```
        /  \
       / E2E \         ~5-10% of tests
      /-------\
     / Integr. \       ~15-25% of tests
    /-----------\
   / Unit Tests  \     ~70-80% of tests
  /_______________\
```

**Characteristics:**
- Many fast unit tests at the base
- Fewer slower integration tests in the middle
- Few slow E2E tests at the top
- Each layer catches different types of bugs

### The Testing Trophy (Kent C. Dodds)

```
        ___
       / E2E \
      /-------\
     /         \
    / Integration\     ← Focus here for best ROI
   /_____________\
   |    Static    |    ← Type checking, linting
   |   Analysis   |
   |______________|
   |     Unit     |    ← Pure business logic
   |______________|
```

**Argument:** Integration tests provide the best confidence-to-effort ratio. Static analysis catches many bugs for free. Unit tests are still valuable for complex logic.

### The Testing Honeycomb

```
         ___
        / E2E \
       /-------\
      / Contract \
     /    Tests   \
    /---------------\
   /   Integration   \
  /      Tests        \
 /---------------------\
|    Component Tests    |
|    (unit + shallow    |
|     integration)      |
 \---------------------/
```

**Argument:** Focus on component tests (testing a component with minimal mocking) as the sweet spot.

## Choosing Your Strategy

There's no one-size-fits-all. Choose based on your context:

| Context                    | Recommended Strategy         |
|----------------------------|------------------------------|
| Startup / fast-moving      | Trophy (integration-heavy)   |
| Enterprise / regulated     | Pyramid (unit-heavy)         |
| Microservices              | Pyramid + contract tests     |
| Monolith                   | Trophy works well            |
| Library / SDK              | Pyramid (lots of unit tests) |
| API-only backend           | Pyramid + integration tests  |
| Mobile app                 | Pyramid + device tests       |

## Risk-Based Testing

Not all code is equally important. Focus testing effort on high-risk areas.

### Risk Assessment Matrix

|              | Low Impact         | High Impact        |
|--------------|--------------------|--------------------|
| **High Likelihood** | Medium risk  | **Critical risk**  |
| **Low Likelihood**  | Low risk     | Medium risk        |

### Identifying High-Risk Areas

1. **Payment processing** — bugs cost real money
2. **Authentication/authorization** — security vulnerabilities
3. **Data migration** — can corrupt or lose data
4. **Public APIs** — breaking changes affect consumers
5. **Complex business rules** — many edge cases
6. **Recently changed code** — new bugs are introduced here
7. **Previously buggy code** — history of defects

### Applying Risk-Based Testing

```markdown
## Module Risk Assessment

| Module              | Risk Level | Test Coverage Target | Test Types              |
|---------------------|------------|----------------------|-------------------------|
| Payment Processing  | Critical   | 95%+                 | Unit + Integration + E2E|
| User Authentication | Critical   | 95%+                 | Unit + Integration + E2E|
| Order Management    | High       | 85%+                 | Unit + Integration      |
| Product Catalog     | Medium     | 75%+                 | Unit + Integration      |
| Logging             | Low        | 50%+                 | Unit                    |
| Admin Dashboard     | Medium     | 70%+                 | Integration + E2E       |
```

## Testing in CI/CD

### Pipeline Stages

```
Code Push → Lint → Unit Tests → Build → Integration Tests → Deploy to Staging → E2E Tests → Deploy to Production
```

### Typical CI Pipeline

```yaml
# GitHub Actions example
name: Test Pipeline
on: [push, pull_request]

jobs:
  # Stage 1: Fast checks (< 1 min)
  lint-and-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck

  # Stage 2: Unit tests (< 3 min)
  unit-tests:
    needs: lint-and-typecheck
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run test:unit -- --coverage
      - uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/

  # Stage 3: Integration tests (< 10 min)
  integration-tests:
    needs: unit-tests
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: testdb
          POSTGRES_PASSWORD: test
        ports: ['5432:5432']
      redis:
        image: redis:7
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run test:integration

  # Stage 4: E2E tests (< 15 min)
  e2e-tests:
    needs: integration-tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run test:e2e
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

### When to Run Each Test Type

| Test Type       | On Every Commit | On PR | Before Merge | Nightly | Before Release |
|-----------------|:---:|:---:|:---:|:---:|:---:|
| **Lint/Static** | ✅  | ✅  | ✅  | ✅  | ✅  |
| **Unit**        | ✅  | ✅  | ✅  | ✅  | ✅  |
| **Integration** | ❌  | ✅  | ✅  | ✅  | ✅  |
| **E2E**         | ❌  | ❌  | ✅  | ✅  | ✅  |
| **Performance** | ❌  | ❌  | ❌  | ✅  | ✅  |
| **Security**    | ❌  | ❌  | ❌  | ✅  | ✅  |

## Test Environments

### Environment Strategy

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│   Dev   │────▶│  CI/CD  │────▶│ Staging │────▶│  Prod   │
│         │     │         │     │         │     │         │
│ Unit    │     │ Unit    │     │ E2E     │     │ Smoke   │
│ tests   │     │ Integr. │     │ Manual  │     │ Canary  │
│         │     │ E2E     │     │ Perf    │     │ Monitor │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
```

### Environment Configuration

| Environment | Purpose                    | Data              | Tests                    |
|-------------|----------------------------|-------------------|--------------------------|
| **Local**   | Developer machine          | Fake/seed data    | Unit, some integration   |
| **CI**      | Automated pipeline         | Test fixtures     | All automated tests      |
| **Staging** | Pre-production validation  | Production-like   | E2E, performance, manual |
| **Production** | Live users              | Real data         | Smoke, canary, monitoring|

## Test Data Management

### Strategies

**1. Fixtures / Seed Data**
```python
# tests/fixtures/users.json
[
  {"id": 1, "name": "Alice", "email": "alice@test.com", "role": "admin"},
  {"id": 2, "name": "Bob", "email": "bob@test.com", "role": "user"}
]
```

**2. Factories**
```python
class UserFactory:
    _counter = 0

    @classmethod
    def create(cls, **overrides):
        cls._counter += 1
        defaults = {
            "name": f"User {cls._counter}",
            "email": f"user{cls._counter}@test.com",
            "role": "user"
        }
        defaults.update(overrides)
        return User(**defaults)

# Usage
admin = UserFactory.create(role="admin")
user = UserFactory.create()
```

**3. Testcontainers (for integration tests)**
```python
@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:16") as pg:
        yield pg
```

**4. Snapshots (for complex data)**
```python
def test_api_response_format(snapshot):
    response = client.get("/api/users")
    snapshot.assert_match(response.json(), "users_response.json")
```

## Contract Testing Strategy

For microservices, contract tests prevent integration failures:

```
Consumer                    Pact Broker                   Provider
   │                            │                            │
   │  1. Write consumer test    │                            │
   │  2. Generate contract ─────┼──▶ Store contract          │
   │                            │                            │
   │                            │    3. Verify provider ─────▶│
   │                            │    against contract         │
   │                            │                            │
   │  4. CI checks contract ◀───┼─── Provider publishes result│
```

### Contract Test Guidelines

1. **Consumer-driven** — consumers define expectations
2. **Bi-directional** — verify both sides
3. **Version-controlled** — contracts in source control
4. **Automated** — verified in CI for both consumer and provider
5. **Backward compatible** — breaking changes require version bumps

## Performance Testing Strategy

### Types of Performance Tests

| Type              | Purpose                              | Tool              |
|-------------------|--------------------------------------|-------------------|
| **Load test**     | Expected traffic levels              | k6, JMeter, Gatling |
| **Stress test**   | Beyond normal capacity               | k6, Locust        |
| **Spike test**    | Sudden traffic bursts                | k6                |
| **Soak test**     | Extended duration (memory leaks)     | k6, JMeter        |
| **Scalability**   | How system scales with load          | Custom scripts    |

```javascript
// k6 load test
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },  // Ramp up
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],    // < 1% error rate
  },
};

export default function () {
  const res = http.get('http://localhost:3000/api/products');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  sleep(1);
}
```

## Security Testing

### Types of Security Tests

| Type                    | What It Catches                    | Tool                |
|-------------------------|------------------------------------|---------------------|
| **SAST** (Static)       | Code vulnerabilities               | SonarQube, Semgrep  |
| **DAST** (Dynamic)      | Runtime vulnerabilities            | OWASP ZAP, Burp     |
| **Dependency scanning**  | Known CVEs in dependencies        | Snyk, Dependabot    |
| **Penetration testing**  | Real-world attack scenarios        | Manual / specialized|

### Security in CI

```yaml
security-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: npm audit --audit-level=high
    - uses: github/codeql-action/analyze@v3
```

## Test Metrics

### Key Metrics to Track

| Metric                  | What It Measures              | Target        |
|-------------------------|-------------------------------|---------------|
| **Code coverage**       | % of code exercised by tests  | 80%+          |
| **Test pass rate**      | % of tests passing            | 99%+          |
| **Test duration**       | How long tests take           | < 10 min CI   |
| **Defect escape rate**  | Bugs found in production      | < 5%          |
| **Flaky test rate**     | % of tests that flake         | < 2%          |
| **Test-to-code ratio**  | Lines of test vs production   | Varies        |
| **Mean time to detect** | Time from commit to bug found | < 1 day       |

### Coverage Dashboard

```python
# pytest.ini — enforce coverage
[tool:pytest]
addopts = --cov=src --cov-report=html --cov-report=term --cov-fail-under=80
```

```javascript
// jest.config.js
module.exports = {
  coverageThreshold: {
    global: { branches: 80, functions: 80, lines: 80, statements: 80 },
    './src/critical/': { branches: 95, functions: 95, lines: 95, statements: 95 },
  },
};
```

## Common Testing Mistakes

| Mistake                          | Consequence                       | Solution                         |
|----------------------------------|-----------------------------------|----------------------------------|
| Testing everything at E2E level  | Slow, brittle test suite          | Follow the pyramid               |
| Ignoring flaky tests             | Team loses trust in tests         | Fix or delete them               |
| No test data strategy            | Tests depend on production data   | Use factories, fixtures          |
| Testing implementation details   | Brittle tests that break on refactor | Test behavior               |
| Skipping integration tests       | "Works on my machine" syndrome    | Use Testcontainers               |
| No CI integration                | Tests rot and aren't run          | Run tests in CI on every PR      |
| 100% coverage obsession          | Tests trivial code, wastes time   | Focus on meaningful coverage     |
| Not testing error paths          | Production errors unhandled       | Always test failure scenarios    |

## Building a Test Strategy Document

A good test strategy document includes:

```markdown
# Test Strategy — Project Name

## Overview
- Testing philosophy and goals
- Team testing standards

## Test Types
- What types of tests we write
- Where each type lives in the codebase
- Who writes each type

## Test Pyramid
- Distribution of test types
- Coverage targets per layer

## Environments
- Local development testing
- CI/CD pipeline stages
- Staging validation
- Production monitoring

## Test Data
- How we create test data
- How we manage test fixtures
- How we handle sensitive data

## CI/CD Integration
- What runs when
- Quality gates
- Failure handling

## Metrics
- What we measure
- Targets and thresholds
- Reporting and dashboards

## Risk Areas
- Critical modules and their test requirements
- Known gaps and plans to address them
```

## Best Practices

1. **Start with the strategy** — don't just write tests randomly
2. **Match test type to risk** — more risk = more testing
3. **Automate everything in CI** — no manual test gates
4. **Fix flaky tests immediately** — they erode trust
5. **Track metrics** — you can't improve what you don't measure
6. **Review test code** — it deserves the same rigor as production code
7. **Keep tests fast** — slow tests don't get run
8. **Document the strategy** — so everyone on the team knows the plan

## Summary

| Concept            | Key Takeaway                                    |
|--------------------|------------------------------------------------|
| **Test Pyramid**   | Unit-heavy, integration-middle, E2E-light       |
| **Trophy**         | Integration tests are the sweet spot            |
| **Risk-based**     | Focus testing on high-risk areas                |
| **CI/CD**          | Run appropriate tests at each pipeline stage    |
| **Metrics**        | Track coverage, pass rate, flaky rate, duration |
| **Environments**   | Local → CI → Staging → Production               |
