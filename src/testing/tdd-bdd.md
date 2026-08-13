# TDD & BDD

Test-Driven Development (TDD) and Behavior-Driven Development (BDD) are development methodologies that use tests to drive design and ensure software meets requirements. Both write tests *before* code, but they differ in scope and audience.

## Test-Driven Development (TDD)

TDD is a development practice where you write a failing test before writing the production code that makes it pass.

### The Red-Green-Refactor Cycle

```
    ┌─────────────────────────────────┐
    │                                 │
    ▼                                 │
  RED ──────▶ GREEN ──────▶ REFACTOR ┘
  Write a     Write the     Clean up
  failing     minimum code  the code
  test        to pass       while tests
                            stay green
```

#### 1. Red — Write a Failing Test

Write the smallest test that expresses the desired behavior:

```python
# test_fizzbuzz.py
def test_fizzbuzz_returns_1_for_1():
    assert fizzbuzz(1) == "1"
```

This test fails because `fizzbuzz` doesn't exist yet.

#### 2. Green — Write Minimum Code to Pass

Write just enough code to make the test pass:

```python
# fizzbuzz.py
def fizzbuzz(n):
    return "1"
```

The test passes. It's ugly, but it's correct for the case tested.

#### 3. Refactor — Clean Up

Improve the code structure while keeping tests green:

```python
# Add more tests
def test_fizzbuzz_returns_fizz_for_3():
    assert fizzbuzz(3) == "Fizz"

def test_fizzbuzz_returns_buzz_for_5():
    assert fizzbuzz(5) == "Buzz"

def test_fizzbuzz_returns_fizzbuzz_for_15():
    assert fizzbuzz(15) == "FizzBuzz"

def test_fizzbuzz_returns_number_for_non_divisible():
    assert fizzbuzz(2) == "2"
    assert fizzbuzz(7) == "7"

# Now refactor to handle all cases
def fizzbuzz(n):
    if n % 15 == 0:
        return "FizzBuzz"
    if n % 3 == 0:
        return "Fizz"
    if n % 5 == 0:
        return "Buzz"
    return str(n)
```

### TDD Example: Shopping Cart

```python
# Step 1: Empty cart
def test_empty_cart_has_zero_total():
    cart = ShoppingCart()
    assert cart.total() == 0

# Implementation
class ShoppingCart:
    def total(self):
        return 0

# Step 2: Add single item
def test_cart_with_one_item_returns_its_price():
    cart = ShoppingCart()
    cart.add(Item("Widget", price=10.00))
    assert cart.total() == 10.00

# Implementation
class ShoppingCart:
    def __init__(self):
        self._items = []

    def add(self, item):
        self._items.append(item)

    def total(self):
        return sum(item.price for item in self._items)

# Step 3: Multiple items
def test_cart_with_multiple_items_returns_sum():
    cart = ShoppingCart()
    cart.add(Item("Widget", price=10.00))
    cart.add(Item("Gadget", price=25.00))
    assert cart.total() == 35.00

# Step 4: Quantity
def test_cart_handles_quantity():
    cart = ShoppingCart()
    cart.add(Item("Widget", price=10.00), quantity=3)
    assert cart.total() == 30.00

# Refactor — add quantity support
class ShoppingCart:
    def __init__(self):
        self._items = []

    def add(self, item, quantity=1):
        self._items.append((item, quantity))

    def total(self):
        return sum(item.price * qty for item, qty in self._items)

# Step 5: Discount
def test_cart_applies_percentage_discount():
    cart = ShoppingCart()
    cart.add(Item("Widget", price=100.00))
    cart.apply_discount(PercentageDiscount(10))
    assert cart.total() == 90.00

# Step 6: Remove item
def test_removing_item_reduces_total():
    cart = ShoppingCart()
    widget = Item("Widget", price=10.00)
    cart.add(widget)
    cart.add(Item("Gadget", price=20.00))
    cart.remove(widget)
    assert cart.total() == 20.00
```

### TDD Benefits

| Benefit                | Explanation                                          |
|------------------------|------------------------------------------------------|
| **Design feedback**    | If it's hard to test, the design needs improvement   |
| **Regression safety**  | Every feature has a test from day one                |
| **Living documentation** | Tests describe what the code should do            |
| **Confidence to refactor** | Change code freely — tests catch mistakes       |
| **Reduced debugging**  | Failures are small and localized                     |

### TDD Rules (Uncle Bob)

1. You are not allowed to write any production code unless it is to make a failing unit test pass
2. You are not allowed to write any more of a unit test than is sufficient to fail, and compilation failures are failures
3. You are not allowed to write any more production code than is sufficient to pass the one failing unit test

### When TDD Works Best

- Well-understood requirements
- Business logic and algorithms
- Library and API design
- Code that needs to be reliable

### When TDD Is Challenging

- Exploratory/spike work (you don't know what you're building yet)
- UI layout (visual design is hard to TDD)
- Concurrency and timing-dependent code
- Integration with hardware or external systems

## Behavior-Driven Development (BDD)

BDD extends TDD by writing tests in natural language that all stakeholders can understand. It focuses on the *behavior* of the system from the user's perspective.

### The BDD Cycle

```
    ┌───────────────────────────────────┐
    │                                   │
    ▼                                   │
  GIVEN ──▶ WHEN ──▶ THEN ──▶ IMPLEMENT┘
  Set up    Perform   Verify    Write code
  context   action    outcome   to make it
                                pass
```

### Given-When-Then

The core BDD syntax describes scenarios:

```gherkin
Feature: Shopping Cart
  As a customer
  I want to add items to my cart
  So that I can purchase them

  Scenario: Add item to empty cart
    Given an empty shopping cart
    When I add a "Widget" priced at $10.00
    Then the cart total should be $10.00
    And the cart should contain 1 item

  Scenario: Apply discount to cart
    Given a cart with "Widget" priced at $100.00
    When I apply a 10% discount
    Then the cart total should be $90.00

  Scenario: Remove item from cart
    Given a cart with:
      | item   | price  | quantity |
      | Widget | $10.00 | 2        |
      | Gadget | $20.00 | 1        |
    When I remove "Widget"
    Then the cart total should be $20.00
    And the cart should contain 1 item
```

### Gherkin Syntax

| Keyword     | Purpose                              | Example                           |
|-------------|--------------------------------------|-----------------------------------|
| `Feature`   | High-level description               | `Feature: User Authentication`    |
| `Scenario`  | Individual test case                 | `Scenario: Valid login`           |
| `Given`     | Preconditions / context              | `Given I am on the login page`    |
| `When`      | Action / trigger                     | `When I submit valid credentials` |
| `Then`      | Expected outcome                     | `Then I see the dashboard`        |
| `And`       | Additional step (any keyword)        | `And my name is displayed`        |
| `But`       | Negative step                        | `But I cannot see admin options`  |
| `Background`| Steps run before every scenario      | `Background: Given I am logged in`|
| `Scenario Outline` | Parameterized scenarios       | `Scenario Outline: Login attempts`|
| `Examples`  | Data for parameterized scenarios     | `Examples: \| user \| pass \|`   |

### Scenario Outline (Parameterized)

```gherkin
Scenario Outline: Login with various credentials
  Given I am on the login page
  When I enter "<email>" and "<password>"
  Then I should "<result>"

  Examples:
    | email            | password       | result            |
    | alice@test.com   | correct        | see the dashboard |
    | wrong@test.com   | wrong          | see an error      |
    | alice@test.com   | wrong          | see an error      |
    | ''               | ''             | see validation    |
```

## Cucumber

Cucumber is the most popular BDD framework, supporting multiple languages.

### Cucumber with Java (Cucumber-JVM)

```java
// Step definitions
public class ShoppingCartSteps {

    private ShoppingCart cart;

    @Given("an empty shopping cart")
    public void emptyShoppingCart() {
        cart = new ShoppingCart();
    }

    @Given("a cart with {string} priced at ${double}")
    public void cartWithItem(String item, double price) {
        cart = new ShoppingCart();
        cart.add(new Item(item, price));
    }

    @When("I add a {string} priced at ${double}")
    public void addItem(String item, double price) {
        cart.add(new Item(item, price));
    }

    @When("I apply a {int}% discount")
    public void applyDiscount(int percentage) {
        cart.applyDiscount(new PercentageDiscount(percentage));
    }

    @Then("the cart total should be ${double}")
    public void cartTotalShouldBe(double expected) {
        assertEquals(expected, cart.total(), 0.01);
    }

    @Then("the cart should contain {int} item(s)")
    public void cartShouldContain(int count) {
        assertEquals(count, cart.itemCount());
    }
}
```

```java
// Data table steps
@Given("a cart with:")
public void cartWithItems(DataTable table) {
    cart = new ShoppingCart();
    List<Map<String, String>> rows = table.asMaps();
    for (Map<String, String> row : rows) {
        String item = row.get("item");
        double price = parsePrice(row.get("price"));
        int quantity = Integer.parseInt(row.get("quantity"));
        cart.add(new Item(item, price), quantity);
    }
}
```

### Cucumber with JavaScript (Cucumber.js)

```javascript
// features/step_definitions/cart.steps.js
const { Given, When, Then } = require('@cucumber/cucumber');
const { expect } = require('chai');

Given('an empty shopping cart', function () {
  this.cart = new ShoppingCart();
});

Given('a cart with {string} priced at ${float}', function (item, price) {
  this.cart = new ShoppingCart();
  this.cart.add(new Item(item, price));
});

When('I add a {string} priced at ${float}', function (item, price) {
  this.cart.add(new Item(item, price));
});

When('I apply a {int}% discount', function (percentage) {
  this.cart.applyDiscount(new PercentageDiscount(percentage));
});

Then('the cart total should be ${float}', function (expected) {
  expect(this.cart.total()).to.be.closeTo(expected, 0.01);
});

Then('the cart should contain {int} item(s)', function (count) {
  expect(this.cart.itemCount()).to.equal(count);
});
```

### Cucumber with Python (behave)

```python
# features/steps/cart_steps.py
from behave import given, when, then
from shopping_cart import ShoppingCart, Item

@given('an empty shopping cart')
def step_empty_cart(context):
    context.cart = ShoppingCart()

@given('a cart with "{item}" priced at ${price:f}')
def step_cart_with_item(context, item, price):
    context.cart = ShoppingCart()
    context.cart.add(Item(item, price))

@when('I add a "{item}" priced at ${price:f}')
def step_add_item(context, item, price):
    context.cart.add(Item(item, price))

@when('I apply a {percentage:d}% discount')
def step_apply_discount(context, percentage):
    context.cart.apply_discount(PercentageDiscount(percentage))

@then('the cart total should be ${expected:f}')
def step_check_total(context, expected):
    assert abs(context.cart.total() - expected) < 0.01

@then('the cart should contain {count:d} item(s)')
def step_check_count(context, count):
    assert context.cart.item_count() == count
```

## TDD vs BDD

| Aspect            | TDD                              | BDD                                |
|-------------------|----------------------------------|------------------------------------|
| **Focus**         | Code correctness                 | System behavior                    |
| **Language**       | Programming language             | Natural language (Gherkin)         |
| **Audience**       | Developers                       | Everyone (devs, QA, product)       |
| **Granularity**    | Functions and methods            | Features and scenarios             |
| **Test type**      | Unit tests                       | Acceptance / integration tests     |
| **Design level**   | Low-level (class design)         | High-level (feature design)        |
| **Speed**         | Very fast                        | Slower (more setup)                |
| **Documentation**  | Technical                        | Business-readable                  |

### When to Use TDD
- Implementing algorithms
- Designing class interfaces
- Writing library code
- Business logic that needs precise testing

### When to Use BDD
- Defining user-facing features
- Communicating with non-technical stakeholders
- Acceptance criteria for stories
- Integration and E2E scenarios

## Example: TDD + BDD Together

A typical workflow uses both:

1. **BDD** defines the feature at a high level (product owner writes Gherkin)
2. **TDD** implements the internals (developer writes unit tests)

```gherkin
# BDD: Feature-level specification
Feature: Password Reset
  Scenario: User resets password via email
    Given a registered user "alice@test.com"
    When I request a password reset for "alice@test.com"
    Then a reset email should be sent to "alice@test.com"
    And the reset link should expire in 24 hours
```

```python
# TDD: Unit-level implementation
from datetime import datetime, timedelta

class TestPasswordResetService:
    def test_generates_unique_token(self):
        service = PasswordResetService()
        token1 = service.generate_token("alice@test.com")
        token2 = service.generate_token("alice@test.com")
        assert token1 != token2

    def test_token_expires_after_24_hours(self):
        service = PasswordResetService()
        token = service.generate_token("alice@test.com")
        now = datetime.now()

        # 23 hours — still valid
        assert service.is_valid(token, now + timedelta(hours=23))

        # 25 hours — expired
        assert not service.is_valid(token, now + timedelta(hours=25))

    def test_sends_email_with_reset_link(self):
        email_service = MockEmailService()
        service = PasswordResetService(email=email_service)
        service.request_reset("alice@test.com")

        email_service.send.assert_called_once()
        sent_args, sent_kwargs = email_service.send.call_args
        # access the email object via sent_args[0] or sent_kwargs["email"], depending on signature
        sent_email = sent_args[0]
        assert "alice@test.com" in sent_email.to
        assert "/reset" in sent_email.body
```

## Anti-Patterns

### TDD Anti-Patterns

| Anti-Pattern              | Problem                             | Fix                              |
|---------------------------|-------------------------------------|----------------------------------|
| **Testing after coding**  | Not really TDD, misses design benefits | Write test first, always      |
| **Mega tests**            | One huge test for everything        | Small, focused tests             |
| **Premature generalization** | Over-engineering from test one    | Start specific, generalize later |
| **Ignoring refactoring**  | Skipping the refactor step          | Refactor every cycle             |

### BDD Anti-Patterns

| Anti-Pattern              | Problem                             | Fix                              |
|---------------------------|-------------------------------------|----------------------------------|
| **UI-level scenarios**    | Too slow, too brittle               | BDD for behavior, not UI clicks  |
| **Too many scenarios**    | Test suite takes forever            | Focus on critical paths          |
| **Vague steps**           | "Then it should work"               | Be specific and measurable       |
| **Step definition spaghetti** | Reusable steps become complex    | Keep steps simple, use helpers   |

## Summary

| Concept            | Key Takeaway                                    |
|--------------------|------------------------------------------------|
| **TDD**            | Write test first → make it pass → refactor     |
| **Red-Green-Refactor** | The heartbeat of TDD                       |
| **BDD**            | Describe behavior in natural language          |
| **Given-When-Then**| The standard BDD scenario format               |
| **Cucumber**       | Most popular BDD framework                     |
| **Together**       | BDD for features, TDD for implementation       |
