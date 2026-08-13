# Code Quality

## Table of Contents

- [Clean Code Principles](#clean-code-principles)
- [Naming Conventions](#naming-conventions)
- [Code Smells](#code-smells)
- [Technical Debt](#technical-debt)
- [Refactoring Techniques](#refactoring-techniques)
- [Static Analysis Tools](#static-analysis-tools)
- [Code Review Checklist](#code-review-checklist)
- [Interview Questions](#interview-questions)

---

## Clean Code Principles

Clean code is code that is **easy to read, understand, and modify**. Robert C. Martin's "Clean Code" is the definitive reference.

### The Characteristics of Clean Code

```
Clean Code is:
├── Readable     — Reads like well-written prose
├── Focused      — Each function does one thing
├── Minimal      — No unnecessary code
├── Testable     — Easy to write tests for
├── Expressive   — Names and structure reveal intent
├── Consistent   — Follows established patterns
└── Honest       — Error handling is explicit, not hidden
```

### Functions

```
Rules for Clean Functions:
├── Small — Ideally < 20 lines, ideally < 10
├── Do one thing — One level of abstraction per function
├── One level of abstraction — Don't mix high-level and low-level
├── Descriptive names — A function name should tell you what it does
├── Few arguments — 0-2 ideal, 3 max (use objects for more)
├── No side effects — Function does what its name says, nothing more
├── Error handling is one thing — A function that handles errors does only that
└── DRY — But not at the expense of clarity
```

**Bad:**
```python
def process(data):
    # Validate
    if not data.get("email"):
        raise ValueError("Email required")
    if not data.get("name"):
        raise ValueError("Name required")
    if len(data["name"]) < 2:
        raise ValueError("Name too short")

    # Transform
    data["email"] = data["email"].lower().strip()
    data["name"] = data["name"].strip().title()
    data["created_at"] = datetime.now()

    # Save
    db = Database()
    db.connect()
    db.execute("INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)",
               (data["name"], data["email"], data["created_at"]))
    db.disconnect()

    # Notify
    email = EmailService()
    email.send(data["email"], "Welcome!", "Your account is ready.")

    return data
```

**Good:**
```python
def register_user(data):
    validated = validate_registration(data)
    user = create_user(validated)
    send_welcome_email(user)
    return user

def validate_registration(data):
    require_field(data, "email")
    require_field(data, "name", min_length=2)
    return {**data, "email": data["email"].lower().strip(),
                    "name": data["name"].strip().title()}

def create_user(data):
    return user_repository.save(data)

def send_welcome_email(user):
    email_service.send(user.email, "Welcome!", "Your account is ready.")
```

### Comments

```
Good Comments:                     Bad Comments:
├── Why, not what                  ├── Restates the code
├── Legal/copyright notices        ├── Commented-out code
├── TODO with ticket number        ├── Obvious explanations
├── Warning of consequences        ├── Misleading comments
├── Public API documentation       ├── Noise ("// increment i")
└── Clarification of intent        └── Journal entries ("// updated 5/3/24")
```

```python
# Bad — comment restates code
i = i + 1  # increment i

# Bad — commented out code
# old_result = calculate_old(data)
result = calculate(data)

# Good — explains WHY
# Using retry with exponential backoff because the payment gateway
# has intermittent 503 errors during peak hours (see incident #1234)
result = retry_with_backoff(pay, max_retries=3)

# Good — explains intent
# We sort by created_at descending to show newest items first,
# per product requirement PRD-456
items.sort(key=lambda x: x.created_at, reverse=True)
```

---

## Naming Conventions

> "There are only two hard things in Computer Science: cache invalidation and naming things." — Phil Karlton

### General Rules

```
1. Reveal intent — Name should tell you why it exists and what it does
2. Avoid disinformation — Don't use misleading names
3. Make meaningful distinctions — Avoid "data", "info", "temp", "result"
4. Use pronounceable names — You'll discuss them in meetings
5. Use searchable names — Single-letter names are hard to find
6. Avoid encodings — No Hungarian notation (strName, intCount)
7. Class names — Nouns (User, Account, OrderProcessor)
8. Method names — Verbs (calculate_total, send_email, is_valid)
9. Boolean names — is_, has_, can_, should_ prefixes
10. Constants — UPPER_SNAKE_CASE
```

### Examples

```python
# ❌ Bad
def calc(d, t):
    return d / t

# ✅ Good
def calculate_speed(distance_km, time_hours):
    return distance_km / time_hours

# ❌ Bad
d = datetime.now()
flag = True
temp = get_data()

# ✅ Good
current_timestamp = datetime.now()
is_authenticated = True
user_profile = get_user_profile()
```

### Naming Patterns

```
Variables:
├── user_name          (not userName in Python, not user-name)
├── total_price        (describes what it holds)
├── is_active          (boolean)
├── has_permission     (boolean)
├── max_retry_count    (constant-like)
└── db_connection      (what it is)

Functions:
├── get_user()         (returns something)
├── calculate_tax()    (does computation)
├── is_valid_email()   (returns boolean)
├── has_permission()   (returns boolean)
├── send_notification() (performs action)
└── create_order()     (creates something)

Classes:
├── User               (entity)
├── OrderProcessor     (does something)
├── EmailService       (provides a service)
├── PaymentGateway     (external interface)
├── UserRepository     (data access)
└── InvalidInputError  (exception)
```

---

## Code Smells

Code smells are surface-level indicators that usually correspond to deeper problems in the system.

### The Most Common Code Smells

```
┌──────────────────┬──────────────────────────┬──────────────────────┐
│ Smell            │ What It Looks Like       │ Why It's Bad         │
├──────────────────┼──────────────────────────┼──────────────────────┤
│ Long Method      │ Function > 50 lines      │ Hard to understand   │
│                  │                          │ and test             │
├──────────────────┼──────────────────────────┼──────────────────────┤
│ God Class        │ One class does everything│ Violates SRP,        │
│                  │ (1000+ lines)            │ impossible to maintain│
├──────────────────┼──────────────────────────┼──────────────────────┤
│ Long Parameter   │ Function with 5+ params  │ Hard to use correctly│
│ List             │                          │ Group into objects   │
├──────────────────┼──────────────────────────┼──────────────────────┤
│ Duplicated Code  │ Same logic in 2+ places  │ Change one, forget   │
│                  │                          │ the other            │
├──────────────────┼──────────────────────────┼──────────────────────┤
│ Dead Code        │ Unreachable code, unused │ Confusing, increases │
│                  │ variables, unused imports│ cognitive load       │
├──────────────────┼──────────────────────────┼──────────────────────┤
│ Feature Envy     │ Method uses another      │ Method belongs in    │
│                  │ class's data more than   │ the other class      │
│                  │ its own                  │                      │
├──────────────────┼──────────────────────────┼──────────────────────┤
│ Data Clumps      │ Same group of variables  │ Extract into a class │
│                  │ always together          │                      │
├──────────────────┼──────────────────────────┼──────────────────────┤
│ Primitive        │ Using strings/ints for   │ Use value objects    │
│ Obsession        │ domain concepts          │ (Money, Email, etc.) │
├──────────────────┼──────────────────────────┼──────────────────────┤
│ Switch           │ Long if-else or switch   │ Use polymorphism     │
│ Statements       │ on type                  │                      │
├──────────────────┼──────────────────────────┼──────────────────────┤
│ Shotgun Surgery  │ One change requires      │ Violates SRP, high   │
│                  │ edits in many files      │ coupling             │
├──────────────────┼──────────────────────────┼──────────────────────┤
│ Speculative      │ Code written for         │ YAGNI — adds         │
│ Generality       │ hypothetical future needs│ unnecessary complexity│
└──────────────────┴──────────────────────────┴──────────────────────┘
```

### Smell → Refactoring Map

| Smell | Refactoring |
|---|---|
| Long Method | Extract Method |
| God Class | Extract Class |
| Long Parameter List | Introduce Parameter Object |
| Duplicated Code | Extract Method, Pull Up Method |
| Dead Code | Remove Dead Code |
| Feature Envy | Move Method |
| Data Clumps | Extract Class |
| Primitive Obsession | Introduce Value Object |
| Switch Statement | Replace with Polymorphism |
| Shotgun Surgery | Move Method, Inline Class |
| Speculative Generality | Remove Unused Code |

---

## Technical Debt

Technical debt is the implied cost of future rework caused by choosing an easy solution now instead of a better approach that would take longer.

### The Technical Debt Quadrant

```
                        Deliberate                    Inadvertent
                   ┌───────────────────────┬────────────────────────┐
                   │                       │                        │
    Reckless       │  "We don't have       │  "What's layered       │
                   │   time for design"    │   architecture?"       │
                   │                       │                        │
                   │  WORST: Knowingly     │  Dangerous: Don't know │
                   │  taking shortcuts     │  what they're doing    │
                   │                       │                        │
                   ├───────────────────────┼────────────────────────┤
                   │                       │                        │
    Prudent        │  "We must ship now    │  "Now we know how      │
                   │   and deal with the   │   we should have       │
                   │   consequences"       │   done it"             │
                   │                       │                        │
                   │  Strategic: Aware of  │  Learning: Discover    │
                   │  trade-offs           │  better approaches     │
                   │                       │                        │
                   └───────────────────────┴────────────────────────┘
```

### Types of Technical Debt

```
Code Debt:
├── Duplicated code
├── Complex/unclear code
├── Outdated dependencies
└── Lack of tests

Architecture Debt:
├── Monolithic systems that should be modular
├── Tight coupling between components
├── Wrong technology choices
└── Missing abstraction layers

Infrastructure Debt:
├── Manual deployment processes
├── Missing monitoring/alerting
├── Inconsistent environments
└── No infrastructure as code

Documentation Debt:
├── Missing or outdated docs
├── Undocumented tribal knowledge
├── No architecture decision records
└── Missing API documentation

Testing Debt:
├── Low test coverage
├── Flaky tests
├── Missing integration/e2e tests
└── Manual testing that should be automated
```

### Managing Technical Debt

```
Strategy 1: Boy Scout Rule
  "Leave the code better than you found it."
  → Fix small issues as you encounter them

Strategy 2: Dedicated Refactoring Sprints
  → Allocate 20% of each sprint to tech debt
  → Or dedicate 1 sprint every 5 sprints to debt

Strategy 3: Tech Debt Register
  → Track debt items as tickets in the backlog
  → Prioritize alongside features
  → Assign cost/impact estimates

Strategy 4: Quality Gates
  → CI pipeline blocks merges below quality thresholds
  → Code coverage > 80%, no critical linting errors
  → Prevents new debt from accumulating

Strategy 5: Architecture Reviews
  → Regular reviews of system design
  → Identify structural debt early
  → Plan refactoring roadmap
```

---

## Refactoring Techniques

Refactoring is changing the internal structure of code without changing its external behavior.

### Essential Refactoring Patterns

**1. Extract Method/Function**
```python
# Before
def print_invoice(invoice):
    # Calculate total
    total = 0
    for item in invoice.items:
        total += item.price * item.quantity
    # Apply discount
    if invoice.discount_code:
        total *= (1 - invoice.discount_rate)
    # Print
    print(f"Invoice #{invoice.id}")
    print(f"Total: ${total:.2f}")

# After
def print_invoice(invoice):
    total = calculate_total(invoice)
    print(f"Invoice #{invoice.id}")
    print(f"Total: ${total:.2f}")

def calculate_total(invoice):
    subtotal = sum(item.price * item.quantity for item in invoice.items)
    if invoice.discount_code:
        return subtotal * (1 - invoice.discount_rate)
    return subtotal
```

**2. Rename Variable/Method**
```python
# Before
def calc(d, t, r):
    return d * (1 + r) ** t

# After
def calculate_compound_interest(principal, years, annual_rate):
    return principal * (1 + annual_rate) ** years
```

**3. Replace Conditional with Polymorphism**
```python
# Before
def get_shipping_cost(order, method):
    if method == "standard":
        return 5.99
    elif method == "express":
        return 14.99
    elif method == "overnight":
        return 24.99

# After
class ShippingMethod(ABC):
    @abstractmethod
    def cost(self, order) -> float: pass

class StandardShipping(ShippingMethod):
    def cost(self, order) -> float:
        return 5.99

class ExpressShipping(ShippingMethod):
    def cost(self, order) -> float:
        return 14.99

class OvernightShipping(ShippingMethod):
    def cost(self, order) -> float:
        return 24.99
```

**4. Introduce Parameter Object**
```python
# Before
def create_user(name, email, phone, address, city, state, zip_code):
    pass  # 7 parameters!

# After
@dataclass
class UserAddress:
    address: str
    city: str
    state: str
    zip_code: str

def create_user(name: str, email: str, phone: str, address: UserAddress):
    pass  # 4 parameters, address is grouped
```

**5. Extract Class**
```python
# Before — one class doing too much
class Employee:
    def calculate_pay(self): ...
    def calculate_tax(self): ...
    def save_to_database(self): ...
    def generate_report(self): ...
    def send_email(self): ...

# After — responsibilities separated
class Employee:
    def __init__(self, name, salary): ...

class PayCalculator:
    def calculate_pay(self, employee): ...
    def calculate_tax(self, employee): ...

class EmployeeRepository:
    def save(self, employee): ...
    def find_by_id(self, id): ...

class EmployeeReporter:
    def generate_report(self, employee): ...
```

### Refactoring Checklist

```
Before Refactoring:
□ Understand the current behavior
□ Write characterization tests (if tests don't exist)
□ Make sure all tests pass
□ Small steps — refactor incrementally
□ Commit after each successful refactoring

During Refactoring:
□ One refactoring at a time
□ Run tests after each change
□ Don't change behavior AND structure simultaneously
□ Use IDE refactoring tools when available
□ Keep the code compiling and tests passing

After Refactoring:
□ All tests still pass
□ Code coverage hasn't decreased
□ No new warnings or linting errors
□ Review the changes for unintended side effects
□ Update documentation if needed
```

---

## Static Analysis Tools

| Language | Tools | What They Check |
|---|---|---|
| **Python** | pylint, flake8, mypy, black, ruff | Style, type checking, complexity |
| **JavaScript** | ESLint, Prettier, TypeScript | Style, type safety, best practices |
| **Java** | SpotBugs, PMD, Checkstyle, SonarQube | Bugs, code smells, style |
| **Go** | golangci-lint, go vet | Bugs, style, best practices |
| **C/C++** | Clang-Tidy, Cppcheck, SonarQube | Memory safety, style, bugs |
| **Ruby** | RuboCop | Style, complexity, best practices |

### Quality Gates in CI/CD

```yaml
# Example quality gate configuration
quality_gates:
  code_coverage:
    minimum: 80%
    new_code: 90%

  complexity:
    max_cyclomatic: 10
    max_cognitive: 15

  duplication:
    max_percentage: 3%

  issues:
    blocker: 0
    critical: 0
    major: 5

  security:
    vulnerabilities: 0
    hotspots: 0
```

---

## Code Review Checklist

```
Correctness:
□ Does the code do what it's supposed to?
□ Are edge cases handled?
□ Is error handling appropriate?
□ Are there any off-by-one errors?

Design:
□ Does it follow SOLID principles?
□ Is it DRY? (no unnecessary duplication)
□ Is it the simplest solution that works? (KISS)
□ Are abstractions at the right level?

Readability:
□ Are names descriptive and consistent?
□ Are functions small and focused?
□ Are comments explaining WHY, not WHAT?
□ Is the code self-documenting?

Testing:
□ Are there tests for the new code?
□ Do tests cover happy path AND edge cases?
□ Are test names descriptive?
□ Is test coverage adequate?

Security:
□ Is user input validated/sanitized?
□ Are secrets handled properly?
□ Are there SQL injection or XSS risks?
□ Is authentication/authorization correct?

Performance:
□ Are there any obvious performance issues?
□ Are database queries efficient?
□ Is caching used where appropriate?
□ Are there any N+1 query problems?

Maintainability:
□ Will future developers understand this?
□ Is the code easy to modify?
□ Are dependencies reasonable?
□ Is backward compatibility maintained?
```

---

## Interview Questions

### Beginner

**Q1: What is clean code?**

Clean code is code that is easy to read, understand, and modify. It has clear naming, small focused functions, minimal duplication, appropriate comments, and good test coverage. As Robert C. Martin says, "Clean code reads like well-written prose."

**Q2: What is a code smell?**

A code smell is a surface-level indication that usually points to a deeper problem in the code. Examples include long methods, duplicated code, large classes, and long parameter lists. Code smells aren't bugs — they don't break functionality — but they make code harder to maintain.

**Q3: What is technical debt?**

Technical debt is the implied cost of future rework caused by choosing a quick, easy solution now instead of a better approach. Like financial debt, it accumulates interest — the longer you wait to address it, the more expensive it becomes to fix.

### Intermediate

**Q4: How do you balance writing clean code with delivery deadlines?**

Apply the 80/20 rule: 80% of clean code benefits come from 20% of the effort — good naming, small functions, and basic testing. Apply the boy scout rule (leave code better than you found it) to address debt incrementally. For critical paths, invest in quality; for throwaway prototypes, accept some debt. Track tech debt explicitly so it can be prioritized alongside features. The key insight: clean code is faster in the long run because it reduces debugging time and makes changes easier.

**Q5: When is it acceptable to take on technical debt?**

When: (1) You need to ship an MVP quickly and will iterate based on user feedback. (2) There's a hard deadline (regulatory, contract) and the shortcut is deliberate and documented. (3) You're exploring a solution and don't know the right architecture yet. (4) The code is a throwaway prototype. The key is that it must be **deliberate** — you know you're taking the shortcut, you've estimated the cost, and you have a plan to address it.

**Q6: How would you introduce code quality practices to a team that has none?**

Start small: (1) Add a linter to the CI pipeline — it's automated and non-controversial. (2) Introduce code reviews — even lightweight ones. (3) Set a minimum test coverage threshold. (4) Adopt the boy scout rule. (5) Track tech debt in the backlog. (6) Run a "clean code" book club or lunch-and-learn. Don't try to implement everything at once — incremental adoption prevents resistance.

### Advanced

**Q7: You inherit a codebase with 500,000 lines of code, no tests, and frequent production incidents. How do you improve it?**

Phase 1 — Stop the bleeding: Add monitoring and alerting for critical paths. Fix the most impactful bugs. Implement feature flags for safe deployments. Phase 2 — Build the safety net: Write characterization tests for critical modules (tests that capture current behavior). Add integration tests for the most important user flows. Set up CI with basic quality gates. Phase 3 — Systematic improvement: Identify the most-changed files (hotspots) using git log analysis. Refactor hotspots first — highest ROI. Apply the strangler fig pattern for major architectural changes. Gradually increase test coverage requirements for new code. Phase 4 — Culture change: Establish code review practices. Document architecture decisions. Create a tech debt register with prioritized items.

**Q8: How do you measure code quality objectively?**

Combine multiple metrics: (1) **Cyclomatic complexity** — measures code complexity, flag functions > 10. (2) **Code coverage** — necessary but not sufficient, aim for 80%+. (3) **Duplication percentage** — should be < 3%. (4) **Code review turnaround** — measures team engagement. (5) **Defect density** — bugs per KLOC. (6) **Change failure rate** — percentage of deployments causing incidents. (7) **Technical debt ratio** — estimated remediation cost vs. development cost. No single metric tells the full story — use a dashboard combining several.

**Q9: Explain the difference between refactoring and rewriting. When would you choose each?**

Refactoring changes internal structure without changing behavior — it's incremental, safe, and preserves institutional knowledge. Rewriting starts from scratch — it's risky, takes longer, but can produce cleaner architecture. Choose refactoring when: the codebase is fundamentally sound but messy, tests exist (or can be written), and incremental improvement is feasible. Choose rewriting when: the architecture is fundamentally wrong, the technology stack is obsolete, the cost of understanding the existing code exceeds rewriting, or the system needs to scale in ways the current architecture can't support. Most of the time, refactoring is the better choice.
