# Unit Testing

Unit testing is the foundation of a healthy test suite. A unit test verifies that a small, isolated piece of code (a function, method, or class) behaves correctly.

## FIRST Principles

Every unit test should adhere to the FIRST principles:

### Fast
Tests must execute in milliseconds. If your unit tests take seconds, something is wrong — likely hitting a real database, network, or filesystem.

```python
# ❌ Slow — hits real database
def test_get_user():
    user = UserRepository(db=real_database).get(1)
    assert user.name == "Alice"

# ✅ Fast — uses in-memory stub
def test_get_user():
    repo = InMemoryUserRepository({1: User("Alice")})
    user = repo.get(1)
    assert user.name == "Alice"
```

### Independent
Tests must not depend on execution order. Each test should set up its own state and clean up after itself.

```python
# ❌ Depends on order — test_create_user must run first
user = None
def test_create_user():
    global user
    user = create_user("Alice")
def test_update_user():
    user.update("Bob")  # Fails if test_create_user didn't run

# ✅ Independent — each test is self-contained
def test_update_user():
    user = create_user("Alice")
    user.update("Bob")
    assert user.name == "Bob"
```

### Repeatable
Running the same test 1000 times should produce the same result. No dependence on time, random seeds, network state, or file system state.

```python
# ❌ Not repeatable — depends on current time
def test_is_weekday():
    assert is_weekday(datetime.now())  # Fails on weekends!

# ✅ Repeatable — fixed input
def test_is_weekday_on_monday():
    monday = datetime(2026, 1, 5)  # A Monday
    assert is_weekday(monday) == True

def test_is_weekday_on_sunday():
    sunday = datetime(2026, 1, 4)  # A Sunday
    assert is_weekday(sunday) == False
```

### Self-Validating
Tests must have a clear pass/fail result. No manual log inspection, no "does this look right?"

```python
# ❌ Not self-validating
def test_sort():
    result = sort([3, 1, 2])
    print(result)  # Human must check output

# ✅ Self-validating
def test_sort():
    result = sort([3, 1, 2])
    assert result == [1, 2, 3]
```

### Timely
Tests should be written at the same time as production code — ideally just before (TDD) or immediately after.

## The AAA Pattern

Arrange-Act-Assert is the most common test structure:

```python
def test_transfer_reduces_source_balance():
    # Arrange — set up preconditions
    source = Account(balance=1000)
    destination = Account(balance=500)

    # Act — perform the action under test
    source.transfer(destination, amount=200)

    # Assert — verify the expected outcome
    assert source.balance == 800
    assert destination.balance == 700
```

Some teams use a variant: **Given-When-Then** (from BDD):

```python
def test_transfer_reduces_source_balance():
    # Given an account with $1000
    source = Account(balance=1000)
    destination = Account(balance=500)

    # When I transfer $200
    source.transfer(destination, amount=200)

    # Then the source balance is $800
    assert source.balance == 800
```

## Testing with JUnit (Java)

```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

class CalculatorTest {

    private Calculator calc;

    @BeforeEach
    void setUp() {
        calc = new Calculator();
    }

    @Test
    void add_twoPositiveNumbers_returnsSum() {
        // Arrange & Act
        int result = calc.add(2, 3);

        // Assert
        assertEquals(5, result);
    }

    @Test
    void divide_byZero_throwsException() {
        assertThrows(ArithmeticException.class, () -> {
            calc.divide(10, 0);
        });
    }

    @Test
    @DisplayName("Square root of negative number should throw")
    void sqrt_negativeNumber_throwsIllegalArgumentException() {
        assertThrows(IllegalArgumentException.class, () -> {
            calc.sqrt(-1);
        });
    }

    @ParameterizedTest
    @CsvSource({
        "0, 0",
        "1, 1",
        "4, 2",
        "9, 3",
        "16, 4"
    })
    void sqrt_perfectSquares_returnsCorrectRoot(int input, int expected) {
        assertEquals(expected, calc.sqrt(input));
    }

    @AfterEach
    void tearDown() {
        // Cleanup if needed
    }
}
```

### JUnit 5 Features

| Feature               | Annotation / Method              |
|-----------------------|----------------------------------|
| Before each test      | `@BeforeEach`                    |
| After each test       | `@AfterEach`                     |
| Before all tests      | `@BeforeAll` (static)            |
| After all tests       | `@AfterAll` (static)             |
| Disabled test         | `@Disabled`                      |
| Display name          | `@DisplayName("...")`            |
| Parameterized tests   | `@ParameterizedTest`             |
| Tagged tests          | `@Tag("unit")`                   |
| Timeout               | `@Timeout(value = 500, MILLIS)`  |
| Nested test classes   | `@Nested`                        |

## Testing with pytest (Python)

```python
import pytest
from calculator import Calculator

class TestCalculator:
    """Tests for the Calculator class."""

    @pytest.fixture
    def calc(self):
        """Create a fresh Calculator for each test."""
        return Calculator()

    def test_add_positive_numbers(self, calc):
        assert calc.add(2, 3) == 5

    def test_add_negative_numbers(self, calc):
        assert calc.add(-2, -3) == -5

    def test_divide_by_zero_raises(self, calc):
        with pytest.raises(ZeroDivisionError):
            calc.divide(10, 0)

    @pytest.mark.parametrize("a, b, expected", [
        (0, 0, 0),
        (1, 2, 3),
        (-1, 1, 0),
        (100, 200, 300),
    ])
    def test_add_parametrized(self, calc, a, b, expected):
        assert calc.add(a, b) == expected

    def test_subtract(self, calc):
        assert calc.subtract(5, 3) == 2


class TestCalculatorEdgeCases:
    """Edge case tests."""

    @pytest.fixture
    def calc(self):
        return Calculator()

    def test_add_with_zero(self, calc):
        assert calc.add(0, 0) == 0

    def test_multiply_large_numbers(self, calc):
        assert calc.multiply(10**6, 10**6) == 10**12
```

### pytest Fixtures

Fixtures provide test dependencies and setup/teardown:

```python
@pytest.fixture
def database():
    """Create a test database, yield it, then clean up."""
    db = create_test_database()
    seed_test_data(db)
    yield db
    db.cleanup()

@pytest.fixture(scope="module")
def expensive_resource():
    """Shared across all tests in the module."""
    resource = load_expensive_resource()
    yield resource
    resource.close()

@pytest.fixture(autouse=True)
def reset_state():
    """Runs before every test automatically."""
    global_state.reset()
    yield
    global_state.cleanup()
```

## Testing with Jest (JavaScript/TypeScript)

```javascript
// calculator.test.js
const { Calculator } = require('./calculator');

describe('Calculator', () => {
  let calc;

  beforeEach(() => {
    calc = new Calculator();
  });

  describe('add', () => {
    test('adds two positive numbers', () => {
      expect(calc.add(2, 3)).toBe(5);
    });

    test('adds negative numbers', () => {
      expect(calc.add(-2, -3)).toBe(-5);
    });

    test('adds zero', () => {
      expect(calc.add(0, 0)).toBe(0);
    });
  });

  describe('divide', () => {
    test('divides two numbers', () => {
      expect(calc.divide(10, 2)).toBe(5);
    });

    test('throws on division by zero', () => {
      expect(() => calc.divide(10, 0)).toThrow('Division by zero');
    });
  });

  describe('sqrt', () => {
    test.each([
      [0, 0],
      [1, 1],
      [4, 2],
      [9, 3],
      [16, 4],
    ])('sqrt(%i) = %i', (input, expected) => {
      expect(calc.sqrt(input)).toBe(expected);
    });
  });
});
```

### Jest Matchers

| Matcher                     | Purpose                              |
|-----------------------------|--------------------------------------|
| `toBe(value)`               | Strict equality (`===`)             |
| `toEqual(value)`            | Deep equality (objects/arrays)      |
| `toBeTruthy()`              | Value is truthy                     |
| `toBeFalsy()`               | Value is falsy                      |
| `toBeNull()`                | Value is null                       |
| `toBeUndefined()`           | Value is undefined                  |
| `toContain(item)`           | Array/string contains item          |
| `toBeGreaterThan(n)`        | Value > n                           |
| `toBeCloseTo(n, precision)` | Floating point comparison           |
| `toThrow(error)`            | Function throws an error            |
| `toHaveBeenCalled()`        | Mock function was called            |
| `toHaveBeenCalledWith(args)` | Mock called with specific args     |

## Code Coverage

### What Is Coverage?

Coverage measures how much of your code is exercised by tests:

```
Statements: 85.7% ( 180/210 )
Branches:   72.3% ( 47/65  )
Functions:  91.2% ( 31/34  )
Lines:      84.9% ( 169/199 )
```

### Coverage Tools

| Language   | Tool                     | Command                          |
|------------|--------------------------|----------------------------------|
| Java       | JaCoCo                   | `mvn test jacoco:report`        |
| Python     | coverage.py + pytest     | `pytest --cov=src --cov-report` |
| JavaScript | Jest (built-in)          | `jest --coverage`               |
| Go         | go test                  | `go test -cover ./...`          |
| TypeScript | c8 / istanbul            | `npx c8 npm test`               |

### Coverage Thresholds

Enforce minimum coverage in CI:

```javascript
// jest.config.js
module.exports = {
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
};
```

```python
# pytest.ini
[tool:pytest]
addopts = --cov-fail-under=80
```

### Coverage Anti-Patterns

```python
# ❌ Testing for coverage without meaningful assertions
def test_get_user():
    user = get_user(1)
    # Runs the code but verifies nothing!

# ✅ Meaningful test
def test_get_user_returns_correct_data():
    user = get_user(1)
    assert user.name == "Alice"
    assert user.email == "alice@example.com"
    assert user.is_active == True
```

## Testing Pure Functions

Pure functions are the easiest to test — no side effects, deterministic output:

```python
# Pure function: easy to test
def calculate_tax(amount, rate):
    return round(amount * rate, 2)

def test_calculate_tax_standard_rate():
    assert calculate_tax(100, 0.1) == 10.00

def test_calculate_tax_zero_amount():
    assert calculate_tax(0, 0.1) == 0.00

def test_calculate_tax_rounding():
    assert calculate_tax(99.99, 0.075) == 7.50
```

## Testing Stateful Code

Stateful objects require testing transitions:

```python
class TestStack:
    def test_new_stack_is_empty(self):
        stack = Stack()
        assert stack.is_empty()
        assert stack.size() == 0

    def test_push_makes_stack_non_empty(self):
        stack = Stack()
        stack.push(42)
        assert not stack.is_empty()
        assert stack.size() == 1

    def test_pop_returns_last_pushed_item(self):
        stack = Stack()
        stack.push(1)
        stack.push(2)
        assert stack.pop() == 2
        assert stack.pop() == 1

    def test_pop_empty_stack_raises(self):
        stack = Stack()
        with pytest.raises(EmptyStackError):
            stack.pop()

    def test_peek_without_removing(self):
        stack = Stack()
        stack.push(42)
        assert stack.peek() == 42
        assert stack.size() == 1  # Not removed
```

## Testing Exceptions

Always test error paths:

```python
class TestUserService:
    def test_create_user_with_duplicate_email_raises(self):
        service = UserService()
        service.create(email="alice@test.com", name="Alice")

        with pytest.raises(DuplicateEmailError):
            service.create(email="alice@test.com", name="Bob")

    def test_create_user_with_invalid_email_raises(self):
        service = UserService()
        with pytest.raises(ValidationError, match="Invalid email"):
            service.create(email="not-an-email", name="Alice")
```

```java
@Test
void createUser_duplicateEmail_throwsException() {
    service.createUser("alice@test.com", "Alice");

    DuplicateEmailException ex = assertThrows(
        DuplicateEmailException.class,
        () -> service.createUser("alice@test.com", "Bob")
    );

    assertEquals("alice@test.com", ex.getEmail());
}
```

## Best Practices

1. **One assertion per concept** — test one logical thing, not one literal `assert` statement
2. **Name tests descriptively** — `test_withdraw_more_than_balance_throws_overdraft_error`
3. **Use fixtures/factories** — don't copy-paste setup code
4. **Test edge cases** — empty inputs, nulls, boundaries, maximum values
5. **Don't test private methods** — test through the public interface
6. **Keep tests DRY** but not at the expense of readability
7. **Run tests before every commit** — make it a habit
8. **Delete dead tests** — tests for removed features add noise

## Summary

| Concept           | Key Takeaway                                    |
|-------------------|------------------------------------------------|
| FIRST             | Fast, Independent, Repeatable, Self-validating, Timely |
| AAA Pattern       | Arrange → Act → Assert                          |
| Coverage          | 80%+ is good; 100% isn't the goal              |
| Pure functions    | Trivially testable, always test edge cases      |
| Stateful code     | Test state transitions and invalid state access |
| Error paths       | Always test that errors are raised correctly    |
