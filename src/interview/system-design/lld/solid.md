# SOLID Principles

## What is SOLID?

SOLID is a set of five design principles that make object-oriented designs more understandable, flexible, and maintainable. Coined by Robert C. Martin (Uncle Bob).

```
S - Single Responsibility Principle (SRP)
O - Open/Closed Principle (OCP)
L - Liskov Substitution Principle (LSP)
I - Interface Segregation Principle (ISP)
D - Dependency Inversion Principle (DIP)
```

## S — Single Responsibility Principle

> "A class should have only one reason to change."

Each class should have exactly one job or responsibility.

### Violation
```python
class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email
    
    # Responsibility 1: User data
    def get_name(self) -> str:
        return self.name
    
    # Responsibility 2: Persistence (should be separate!)
    def save_to_database(self):
        db.execute("INSERT INTO users ...", self.name, self.email)
    
    # Responsibility 3: Email (should be separate!)
    def send_email(self, message: str):
        smtp.send(self.email, message)
```

**Problems**: Changing email logic requires changing User class. Database change affects User.

### Correct
```python
class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

class UserRepository:
    def save(self, user: User):
        db.execute("INSERT INTO users ...", user.name, user.email)

class EmailService:
    def send(self, user: User, message: str):
        smtp.send(user.email, message)
```

Each class has one responsibility and one reason to change.

## O — Open/Closed Principle

> "Software entities should be open for extension but closed for modification."

You should be able to add new behavior without modifying existing code.

### Violation
```python
class AreaCalculator:
    def calculate_area(self, shape):
        if isinstance(shape, Circle):
            return 3.14 * shape.radius ** 2
        elif isinstance(shape, Rectangle):
            return shape.width * shape.height
        elif isinstance(shape, Triangle):  # Must modify for each new shape!
            return 0.5 * shape.base * shape.height
```

Every new shape requires modifying `AreaCalculator`.

### Correct
```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        pass

class Circle(Shape):
    def __init__(self, radius: float):
        self.radius = radius
    
    def area(self) -> float:
        return 3.14 * self.radius ** 2

class Rectangle(Shape):
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height
    
    def area(self) -> float:
        return self.width * self.height

class Triangle(Shape):
    def __init__(self, base: float, height: float):
        self.base = base
        self.height = height
    
    def area(self) -> float:
        return 0.5 * self.base * self.height

class AreaCalculator:
    def calculate_area(self, shape: Shape) -> float:
        return shape.area()  # No modification needed for new shapes
```

Adding a new shape? Just create a new class extending Shape.

## L — Liskov Substitution Principle

> "Subtypes must be substitutable for their base types."

If class B is a subclass of class A, you should be able to use B anywhere A is expected without breaking the program.

### Violation
```python
class Bird:
    def fly(self):
        return "Flying"

class Sparrow(Bird):
    def fly(self):
        return "Sparrow flying"

class Penguin(Bird):
    def fly(self):
        raise Exception("Penguins can't fly!")  # Violates LSP!

def make_bird_fly(bird: Bird):
    print(bird.fly())  # Crashes for Penguin!
```

### Correct
```python
from abc import ABC, abstractmethod

class Bird(ABC):
    @abstractmethod
    def move(self) -> str:
        pass

class FlyingBird(Bird):
    @abstractmethod
    def fly(self) -> str:
        pass
    
    def move(self) -> str:
        return self.fly()

class Sparrow(FlyingBird):
    def fly(self) -> str:
        return "Sparrow flying"

class Penguin(Bird):
    def move(self) -> str:
        return "Penguin swimming"

def make_bird_move(bird: Bird):
    print(bird.move())  # Works for all birds!
```

## I — Interface Segregation Principle

> "Clients should not be forced to depend on interfaces they don't use."

Keep interfaces small and focused. Don't create "fat" interfaces.

### Violation
```python
class Machine(ABC):
    @abstractmethod
    def print_document(self):
        pass
    
    @abstractmethod
    def scan_document(self):
        pass
    
    @abstractmethod
    def fax_document(self):
        pass

class SimplePrinter(Machine):
    def print_document(self):
        print("Printing...")
    
    def scan_document(self):
        raise Exception("Can't scan!")  # Forced to implement!
    
    def fax_document(self):
        raise Exception("Can't fax!")  # Forced to implement!
```

### Correct
```python
class Printer(ABC):
    @abstractmethod
    def print_document(self):
        pass

class Scanner(ABC):
    @abstractmethod
    def scan_document(self):
        pass

class Fax(ABC):
    @abstractmethod
    def fax_document(self):
        pass

class SimplePrinter(Printer):
    def print_document(self):
        print("Printing...")

class MultiFunctionMachine(Printer, Scanner, Fax):
    def print_document(self):
        print("Printing...")
    
    def scan_document(self):
        print("Scanning...")
    
    def fax_document(self):
        print("Faxing...")
```

Each class only implements the interfaces it needs.

## D — Dependency Inversion Principle

> "High-level modules should not depend on low-level modules. Both should depend on abstractions."

Depend on interfaces, not concrete implementations.

### Violation
```python
class MySQLDatabase:
    def connect(self):
        print("Connecting to MySQL")
    
    def query(self, sql: str):
        print(f"MySQL: {sql}")

class UserService:
    def __init__(self):
        self.db = MySQLDatabase()  # Direct dependency on concrete class!
    
    def get_user(self, user_id: int):
        self.db.connect()
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
```

**Problems**: Can't switch to PostgreSQL without changing UserService. Hard to test.

### Correct
```python
from abc import ABC, abstractmethod

class Database(ABC):
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def query(self, sql: str):
        pass

class MySQLDatabase(Database):
    def connect(self):
        print("Connecting to MySQL")
    
    def query(self, sql: str):
        print(f"MySQL: {sql}")

class PostgreSQLDatabase(Database):
    def connect(self):
        print("Connecting to PostgreSQL")
    
    def query(self, sql: str):
        print(f"PostgreSQL: {sql}")

class UserService:
    def __init__(self, db: Database):  # Depends on abstraction
        self.db = db
    
    def get_user(self, user_id: int):
        self.db.connect()
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")

# Usage
service = UserService(MySQLDatabase())      # Easy to swap
service = UserService(PostgreSQLDatabase())  # Just change this line
```

## SOLID Summary

| Principle | Key Idea | Benefit |
|-----------|----------|---------|
| **SRP** | One class, one job | Easier to maintain and test |
| **OCP** | Extend, don't modify | Add features without breaking existing code |
| **LSP** | Subtypes are substitutable | Polymorphism works correctly |
| **ISP** | Small, focused interfaces | Classes don't depend on unused methods |
| **DIP** | Depend on abstractions | Loose coupling, easy to swap implementations |

## Applying SOLID in Real Systems

### Example: Notification System

```python
# SRP: Separate responsibilities
class Notification:
    def __init__(self, recipient: str, message: str):
        self.recipient = recipient
        self.message = message

class NotificationSender(ABC):
    @abstractmethod
    def send(self, notification: Notification):
        pass

class EmailSender(NotificationSender):
    def send(self, notification: Notification):
        print(f"Email to {notification.recipient}: {notification.message}")

class SMSSender(NotificationSender):
    def send(self, notification: Notification):
        print(f"SMS to {notification.recipient}: {notification.message}")

# OCP: Add new channels without modifying existing code
class PushNotificationSender(NotificationSender):
    def send(self, notification: Notification):
        print(f"Push to {notification.recipient}: {notification.message}")

# DIP: High-level depends on abstraction
class NotificationService:
    def __init__(self, senders: list[NotificationSender]):
        self.senders = senders
    
    def notify(self, notification: Notification):
        for sender in self.senders:
            sender.send(notification)

# ISP: Small, focused interfaces
class Retryable(ABC):
    @abstractmethod
    def retry(self, notification: Notification, max_attempts: int):
        pass

class Loggable(ABC):
    @abstractmethod
    def log(self, notification: Notification):
        pass
```

## Interview Tips

1. **Mention SOLID by name** — "I'm applying the Open/Closed Principle here"
2. **Explain the "why"** — Not just "I used SRP" but "SRP makes this easier to test"
3. **Show trade-offs** — Sometimes strict SOLID adds complexity
4. **Apply naturally** — Don't force SOLID where it doesn't fit
5. **Give examples** — Reference real-world code you've written

## Common Mistakes

- ❌ Creating too many tiny classes (over-applying SRP)
- ❌ Using inheritance when composition is better
- ❌ Forcing interfaces where concrete classes would suffice
- ❌ Not explaining why you chose a principle

## Cross-References

- [Design Patterns](./design-patterns.md) — Patterns embody SOLID principles
- [OOP Concepts](./oop-concepts.md) — Foundation for SOLID
- [Abstraction & Interfaces](./abstraction-interfaces.md) — DIP and ISP implementation
- [UML Class Diagrams](./uml-class-diagrams.md) — Visualizing SOLID designs
