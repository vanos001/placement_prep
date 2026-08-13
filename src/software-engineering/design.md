# Software Design Principles

## Table of Contents

- [SOLID Principles](#solid-principles)
- [DRY — Don't Repeat Yourself](#dry--dont-repeat-yourself)
- [KISS — Keep It Simple, Stupid](#kiss--keep-it-simple-stupid)
- [YAGNI — You Aren't Gonna Need It](#yagni--you-arent-gonna-need-it)
- [Separation of Concerns](#separation-of-concerns)
- [Coupling vs Cohesion](#coupling-vs-cohesion)
- [Design by Contract](#design-by-contract)
- [Composition vs Inheritance](#composition-vs-inheritance)
- [Law of Demeter](#law-of-demeter)
- [Principle of Least Astonishment](#principle-of-least-astonishment)
- [Interview Questions](#interview-questions)

---

## SOLID Principles

SOLID is a set of five design principles introduced by Robert C. Martin (Uncle Bob) that make object-oriented designs more understandable, flexible, and maintainable.

### S — Single Responsibility Principle (SRP)

> "A class should have one, and only one, reason to change."

Each class should have **one job**. If a class handles multiple responsibilities, changes to one responsibility may break the other.

**Violation:**
```python
class UserManager:
    def create_user(self, name, email):
        # Business logic
        user = {"name": name, "email": email}
        # Database logic
        db.execute("INSERT INTO users ...", user)
        # Email logic
        send_email(email, "Welcome!", "Your account is created.")
        # Logging logic
        logger.info(f"User {name} created")
        return user
```

**Four reasons to change:** business rules, database schema, email service, logging format.

**Fixed:**
```python
class UserCreator:
    def create_user(self, name, email):
        return {"name": name, "email": email}

class UserRepository:
    def save(self, user):
        db.execute("INSERT INTO users ...", user)

class EmailService:
    def send_welcome(self, email):
        send_email(email, "Welcome!", "Your account is created.")

class Logger:
    def log_user_creation(self, name):
        logger.info(f"User {name} created")
```

Now each class has one reason to change.

---

### O — Open/Closed Principle (OCP)

> "Software entities should be open for extension, but closed for modification."

You should be able to add new behavior **without modifying existing code**.

**Violation:**
```python
class AreaCalculator:
    def calculate(self, shape):
        if isinstance(shape, Circle):
            return 3.14 * shape.radius ** 2
        elif isinstance(shape, Rectangle):
            return shape.width * shape.height
        elif isinstance(shape, Triangle):
            return 0.5 * shape.base * shape.height
        # Every new shape requires modifying this class!
```

**Fixed:**
```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        pass

class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius

    def area(self) -> float:
        return 3.14 * self.radius ** 2

class Rectangle(Shape):
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def area(self) -> float:
        return self.width * self.height

class Triangle(Shape):
    def __init__(self, base, height):
        self.base = base
        self.height = height

    def area(self) -> float:
        return 0.5 * self.base * self.height

class AreaCalculator:
    def total_area(self, shapes: list[Shape]) -> float:
        return sum(shape.area() for shape in shapes)
```

New shapes are added by creating a new class — AreaCalculator never changes.

---

### L — Liskov Substitution Principle (LSP)

> "Subtypes must be substitutable for their base types without altering the correctness of the program."

If class B is a subclass of A, you should be able to use B anywhere you use A without things breaking.

**Classic Violation — Square/Rectangle:**
```python
class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def set_width(self, width):
        self.width = width

    def set_height(self, height):
        self.height = height

    def area(self):
        return self.width * self.height

class Square(Rectangle):
    def set_width(self, width):
        self.width = width
        self.height = width  # Forces height to match

    def set_height(self, height):
        self.width = height  # Forces width to match
        self.height = height

# Problem:
def print_area(rect: Rectangle):
    rect.set_width(5)
    rect.set_height(4)
    print(rect.area())  # Expected: 20. For Square: 16!

r = Rectangle(3, 4)
print_area(r)  # 20 ✓

s = Square(3, 3)
print_area(s)  # 16 ✗ — violates LSP!
```

**Fix:** Don't force Square to inherit from Rectangle. Use a common Shape interface instead.

---

### I — Interface Segregation Principle (ISP)

> "Clients should not be forced to depend on interfaces they do not use."

Don't create fat interfaces. Split them into smaller, specific ones.

**Violation:**
```java
interface Worker {
    void work();
    void eat();
    void sleep();
    void attendMeeting();
}

class Robot implements Worker {
    public void work() { /* works */ }
    public void eat() { throw new Exception("Robots don't eat!"); }
    public void sleep() { throw new Exception("Robots don't sleep!"); }
    public void attendMeeting() { /* sits there */ }
}
```

**Fixed:**
```java
interface Workable {
    void work();
}

interface Eatable {
    void eat();
}

interface Sleepable {
    void sleep();
}

interface MeetingAttendee {
    void attendMeeting();
}

class Human implements Workable, Eatable, Sleepable, MeetingAttendee {
    public void work() { /* works */ }
    public void eat() { /* eats */ }
    public void sleep() { /* sleeps */ }
    public void attendMeeting() { /* attends */ }
}

class Robot implements Workable, MeetingAttendee {
    public void work() { /* works */ }
    public void attendMeeting() { /* attends */ }
}
```

---

### D — Dependency Inversion Principle (DIP)

> "High-level modules should not depend on low-level modules. Both should depend on abstractions."
> "Abstractions should not depend on details. Details should depend on abstractions."

**Violation:**
```python
class MySQLDatabase:
    def query(self, sql):
        return self.connection.execute(sql)

class UserRepository:
    def __init__(self):
        self.db = MySQLDatabase()  # Direct dependency on concrete class

    def get_user(self, user_id):
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
```

If you want to switch to PostgreSQL, you must modify UserRepository.

**Fixed:**
```python
from abc import ABC, abstractmethod

class Database(ABC):
    @abstractmethod
    def query(self, sql):
        pass

class MySQLDatabase(Database):
    def query(self, sql):
        return self.mysql_connection.execute(sql)

class PostgreSQLDatabase(Database):
    def query(self, sql):
        return self.pg_connection.execute(sql)

class UserRepository:
    def __init__(self, db: Database):  # Depends on abstraction
        self.db = db

    def get_user(self, user_id):
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")

# Usage — inject the dependency
repo = UserRepository(MySQLDatabase())
# or
repo = UserRepository(PostgreSQLDatabase())
```

---

### SOLID Summary Table

| Principle | Key Idea | Benefit |
|---|---|---|
| **S**RP | One class, one job | Easier to understand, test, and modify |
| **O**CP | Open for extension, closed for modification | Add features without breaking existing code |
| **L**SP | Subtypes are substitutable | Polymorphism works correctly |
| **I**SP | Small, specific interfaces | Classes only depend on what they use |
| **D**IP | Depend on abstractions | Loose coupling, easy to swap implementations |

---

## DRY — Don't Repeat Yourself

> "Every piece of knowledge must have a single, unambiguous, authoritative representation within a system." — Andy Hunt & Dave Thomas

**DRY** is about eliminating **knowledge duplication**, not just code duplication.

### What Counts as Duplication

```
Code duplication:
├── Copy-pasted functions
├── Similar if-else chains in multiple places
└── Repeated validation logic

Knowledge duplication:
├── Business rules expressed in code AND documentation AND database constraints
├── Hardcoded values that should be constants or config
└── Same validation logic in frontend AND backend
```

### DRY Example

**Violation:**
```python
def calculate_tax_us(price):
    return price * 0.08  # Tax rate hardcoded

def calculate_tax_uk(price):
    return price * 0.20  # Same pattern, different rate

def display_tax_us(price):
    tax = price * 0.08  # Same calculation repeated!
    return f"Tax: ${tax}"
```

**Fixed:**
```python
TAX_RATES = {"US": 0.08, "UK": 0.20}

def calculate_tax(price, country):
    return price * TAX_RATES[country]

def display_tax(price, country):
    tax = calculate_tax(price, country)
    return f"Tax: ${tax}"
```

### When NOT to Apply DRY

```
⚠️ Don't DRY prematurely:
├── Two pieces of code look similar but serve different purposes
├── Abstracting too early creates wrong abstractions
├── Some duplication is acceptable if it keeps code independent
└── "Duplication is far cheaper than the wrong abstraction" — Sandi Metz
```

---

## KISS — Keep It Simple, Stupid

> "Simplicity is the ultimate sophistication." — Leonardo da Vinci

**KISS** means choosing the simplest solution that works.

### KISS in Practice

```python
# Over-engineered
class FibonacciCalculator:
    def __init__(self, cache_size=100):
        self.cache = {}
        self.cache_size = cache_size

    def calculate(self, n):
        if n in self.cache:
            return self.cache[n]
        if n <= 1:
            return n
        result = self.calculate(n-1) + self.calculate(n-2)
        if len(self.cache) < self.cache_size:
            self.cache[n] = result
        return result

# KISS
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

```
Guidelines:
├── Start with the simplest solution
├── Add complexity only when needed (and proven necessary)
├── If you can't explain it simply, you don't understand it well enough
├── Prefer standard library over custom code
├── Avoid clever one-liners that sacrifice readability
└── A working simple solution beats an elegant complex one
```

---

## YAGNI — You Aren't Gonna Need It

> "Always implement things when you actually need them, never when you just foresee that you need them." — Ron Jeffires

**YAGNI** says don't build features until they're actually needed.

### Examples

```
❌ YAGNI Violations:
├── "We might need to support multiple databases someday" → Use what you need now
├── "Let's add a caching layer just in case" → Add it when performance is a problem
├── "What if we need to scale to 10 million users?" → Handle current scale first
├── "Let's make this configurable" → Hardcode until you have multiple configs
└── "We'll need an event bus eventually" → Use direct calls until you need decoupling

✅ YAGNI Applied:
├── Build for current requirements
├── Write clean, refactorable code (so future changes are easy)
├── Trust that you can add complexity later when the need is proven
└── Focus on delivering value NOW
```

### YAGNI vs Being Prepared

YAGNI doesn't mean writing bad code. It means:
- Write **clean, well-structured** code that's easy to change
- Don't add **features** you don't need yet
- Don't add **abstractions** for hypothetical future requirements
- Design for **today's** requirements with **good architecture** for tomorrow

---

## Separation of Concerns

> "Each section of a program should address a separate concern." — Edsger Dijkstra

**Separation of Concerns (SoC)** means dividing a program into distinct sections, each addressing a separate aspect of the system.

### Classic Example: MVC Pattern

```
┌─────────────────────────────────────────┐
│              Application                │
├─────────────┬─────────────┬─────────────┤
│    Model    │    View     │  Controller │
│             │             │             │
│  Business   │  User       │  Input      │
│  logic      │  interface  │  handling   │
│  Data       │  Display    │  Routing    │
│  Validation │  Templates  │  Requests   │
└─────────────┴─────────────┴─────────────┘

Model:     "What is the data and what are the rules?"
View:      "How does it look?"
Controller: "How does the user interact with it?"
```

### SoC in Practice

```
Layers of a typical web application:
├── Presentation Layer (UI/Views)
│   └── Handles rendering, user input
├── Application Layer (Services/Use Cases)
│   └── Orchestrates business workflows
├── Domain Layer (Business Logic)
│   └── Core business rules, entities
├── Infrastructure Layer (Database, External APIs)
│   └── Technical implementation details
└── Cross-Cutting Concerns
    ├── Logging
    ├── Security
    ├── Caching
    └── Error handling
```

---

## Coupling vs Cohesion

These two concepts are fundamental to evaluating software design quality.

### Cohesion

**Cohesion** measures how closely related the responsibilities of a single module/class are.

```
High Cohesion (GOOD):                  Low Cohesion (BAD):
┌─────────────────────┐               ┌─────────────────────┐
│   OrderProcessor    │               │   UtilityManager    │
│                     │               │                     │
│  - create_order()   │               │  - send_email()     │
│  - validate_order() │               │  - calculate_tax()  │
│  - apply_discount() │               │  - format_date()    │
│  - calculate_total()│               │  - parse_xml()      │
│  - confirm_order()  │               │  - log_message()    │
│                     │               │  - validate_input() │
│  All about orders!  │               │  Random stuff!      │
└─────────────────────┘               └─────────────────────┘
```

### Coupling

**Coupling** measures how dependent modules/classes are on each other.

```
Low Coupling (GOOD):                   High Coupling (BAD):
┌─────────┐  ┌─────────┐             ┌─────────┐  ┌─────────┐
│ Order   │  │ Payment │             │ Order   │──│ Payment │
│ Service │  │ Service │             │ Service │──│ Service │
└────┬────┘  └────┬────┘             └────┬────┘──└────┬────┘
     │             │                       │            │
     ▼             ▼                       ▼            ▼
┌─────────┐  ┌─────────┐             ┌──────────────────────┐
│ Order   │  │ Payment │             │   Shared State       │
│ Database│  │ Gateway │             │   (tightly coupled)  │
└─────────┘  └─────────┘             └──────────────────────┘

Each service uses        Services share state and
its own dependencies     directly call each other
```

### Coupling vs Cohesion Table

| Aspect | Coupling | Cohesion |
|---|---|---|
| **Measures** | Dependency between modules | Relatedness within a module |
| **Good** | Low coupling | High cohesion |
| **Bad** | High coupling | Low cohesion |
| **Goal** | Modules are independent | Module does one thing well |
| **How to improve** | Use interfaces, dependency injection | Apply SRP, group related functions |

### Types of Coupling (Weakest to Strongest)

```
1. Data Coupling    — Pass only necessary data (best)
2. Stamp Coupling   — Pass data structures
3. Control Coupling — Pass control flags
4. External Coupling — Shared external format/protocol
5. Common Coupling  — Shared global data
6. Content Coupling — Directly accessing internals (worst)
```

---

## Design by Contract

**Design by Contract (DbC)**, introduced by Bertrand Meyer, uses formal contracts between software components.

### The Three Contract Elements

```
┌─────────────────────────────────────────────────────────┐
│                    Function Contract                     │
├──────────────┬──────────────────────────────────────────┤
│ Preconditions│ What must be true BEFORE the function    │
│              │ is called. Caller's responsibility.      │
├──────────────┼──────────────────────────────────────────┤
│ Postconditions│ What will be true AFTER the function    │
│              │ completes. Function's responsibility.    │
├──────────────┼──────────────────────────────────────────┤
│ Invariants   │ What is ALWAYS true during the object's  │
│              │ lifetime. Maintained by the object.      │
└──────────────┴──────────────────────────────────────────┘
```

### Example

```python
def transfer(from_account, to_account, amount):
    """
    Contract:
    Precondition:  amount > 0
    Precondition:  from_account.balance >= amount
    Precondition:  from_account != to_account
    Postcondition: from_account.balance decreased by amount
    Postcondition: to_account.balance increased by amount
    Postcondition: total money in system unchanged
    Invariant:     account.balance >= 0 for all accounts
    """
    assert amount > 0, "Amount must be positive"
    assert from_account.balance >= amount, "Insufficient funds"
    assert from_account != to_account, "Cannot transfer to self"

    from_account.balance -= amount
    to_account.balance += amount

    assert from_account.balance >= 0, "Invariant violated"
    assert to_account.balance >= 0, "Invariant violated"
```

---

## Composition vs Inheritance

### The Classic Dilemma

```
"Prefer composition over inheritance" — Gang of Four
```

### Inheritance

```python
class Animal:
    def eat(self):
        print("Eating")

    def sleep(self):
        print("Sleeping")

class Dog(Animal):
    def bark(self):
        print("Woof!")

class Robot:
    def work(self):
        print("Working")

# Problem: What about a RobotDog?
class RobotDog(Dog, Robot):  # Multiple inheritance — messy!
    pass
```

### Composition

```python
class Eater:
    def eat(self):
        print("Eating")

class Sleeper:
    def sleep(self):
        print("Sleeping")

class Barker:
    def bark(self):
        print("Woof!")

class Worker:
    def work(self):
        print("Working")

class Dog:
    def __init__(self):
        self._eater = Eater()
        self._sleeper = Sleeper()
        self._barker = Barker()

    def eat(self): self._eater.eat()
    def sleep(self): self._sleeper.sleep()
    def bark(self): self._barker.bark()

class RobotDog:
    def __init__(self):
        self._eater = Eater()
        self._sleeper = Sleeper()
        self._barker = Barker()
        self._worker = Worker()

    def eat(self): self._eater.eat()
    def sleep(self): self._sleeper.sleep()
    def bark(self): self._barker.bark()
    def work(self): self._worker.work()
```

### When to Use Each

| Use Inheritance When | Use Composition When |
|---|---|
| True "is-a" relationship | "has-a" relationship |
| Base class is designed for extension | Behavior needs to be swapped at runtime |
| Subclass is a specialization | You need multiple behaviors |
| Framework requires it (e.g., Android Activity) | Avoiding the fragile base class problem |
| Shallow hierarchy (1-2 levels) | Complex behavior combinations |

---

## Law of Demeter

> "Only talk to your immediate friends."

A method should only call methods on:
1. Its own parameters
2. Objects it creates
3. Its own fields (direct component objects)

**Violation:**
```python
# Deep chain of calls
user.get_address().get_city().get_zip_code()
```

**Fixed:**
```python
user.get_zip_code()  # User knows how to get its own zip code
```

**Benefits:** Reduces coupling, makes code easier to refactor and test.

---

## Principle of Least Astonishment

> "A component of a system should behave in a way that most users will expect it to behave."

```python
# Astonishing (bad)
def add(a, b):
    return a - b  # Surprise!

# Expected (good)
def add(a, b):
    return a + b
```

```
Guidelines:
├── Functions do what their names say
├── Return types are consistent
├── Side effects are documented
├── Error handling is predictable
└── API behavior matches common conventions
```

---

## Interview Questions

### Beginner

**Q1: Explain SOLID principles in one sentence each.**

- **SRP:** A class should have only one reason to change.
- **OCP:** Open for extension, closed for modification.
- **LSP:** Subclasses must be usable in place of their parent class.
- **ISP:** Don't force clients to depend on methods they don't use.
- **DIP:** Depend on abstractions, not concrete implementations.

**Q2: What is the difference between coupling and cohesion?**

Coupling measures how dependent modules are on each other — low coupling is good. Cohesion measures how related the responsibilities within a module are — high cohesion is good. A well-designed system has modules with high internal cohesion and low external coupling.

**Q3: What does "composition over inheritance" mean?**

It means building complex objects by combining simpler objects (composition) rather than creating deep class hierarchies (inheritance). Composition is more flexible because behaviors can be swapped at runtime, and it avoids problems like the fragile base class and tight coupling.

### Intermediate

**Q4: Give an example where applying DRY too aggressively causes problems.**

Two modules have similar-looking validation code for email addresses. You extract a shared `validate_email()` function. Later, Module A needs to accept emails with "+" aliases while Module B doesn't. Now you modify the shared function with a flag parameter, making it more complex. The "right" approach was to recognize these were different concerns that happened to look similar initially — separate implementations with shared unit tests would have been better.

**Q5: How does the Dependency Inversion Principle relate to Dependency Injection?**

DIP is the principle: depend on abstractions. Dependency Injection (DI) is a technique to implement DIP: instead of a class creating its dependencies, they are "injected" from outside (constructor injection, setter injection, or interface injection). DI containers (like Spring, Guice) automate this process. DIP is the "what," DI is the "how."

**Q6: Explain Design by Contract with a real-world analogy.**

A restaurant order is a contract: Precondition — the restaurant must be open and the menu item available. Postcondition — you receive the food you ordered, cooked to specification. Invariant — the restaurant maintains health code standards throughout. If the precondition fails (item unavailable), the contract is void. If the postcondition fails (wrong food), the restaurant must correct it. This is exactly how software contracts work between functions/modules.

### Advanced

**Q7: You're designing a payment processing system. How would you apply SOLID?**

- **SRP:** Separate `PaymentValidator`, `PaymentProcessor`, `PaymentLogger`, `ReceiptGenerator`. Each has one job.
- **OCP:** Define a `PaymentMethod` interface. Add `CreditCard`, `PayPal`, `Crypto` implementations without modifying the processor.
- **LSP:** All payment methods must be usable interchangeably — `PayPal.process()` must conform to the same contract as `CreditCard.process()`.
- **ISP:** Separate `Refundable`, `Recurring`, `Tokenizable` interfaces — not all payment methods support all features.
- **DIP:** The processor depends on `PaymentGateway` abstraction, not `StripeGateway` directly — enables testing with mock gateways and switching providers.

**Q8: When is inheritance actually the right choice?**

When you have a genuine "is-a" relationship with shared behavior, the hierarchy is shallow (1-2 levels), and the base class was designed for extension. Examples: `Exception` hierarchies (IOException extends Exception), UI framework base classes (Activity in Android), and template method patterns where the algorithm is fixed but steps vary. The key test: does the Liskov Substitution Principle hold? If substituting the subclass for the parent breaks expectations, inheritance is wrong.

**Q9: How would you refactor a "God class" that violates SRP and has 5,000 lines?**

Step by step: (1) Identify responsibilities — read the class and list every distinct thing it does. (2) Group related methods and fields into potential new classes. (3) Extract one class at a time, starting with the most independent responsibility. (4) Use delegation — the God class delegates to the new class. (5) Run tests after each extraction. (6) Use the Extract Class refactoring pattern. (7) Apply Dependency Injection to wire new classes together. (8) Repeat until each class has a single responsibility. (9) If the God class is still used as a facade, keep it thin — just delegation. Don't try to refactor everything in one PR.
