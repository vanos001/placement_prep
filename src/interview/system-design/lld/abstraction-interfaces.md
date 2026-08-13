# Abstraction and Interfaces

## Abstract Classes

An abstract class is a class that cannot be instantiated and may contain abstract methods that subclasses must implement.

### Abstract Class Characteristics

| Feature | Abstract Class | Concrete Class |
|---------|---------------|----------------|
| Instantiation | ❌ Cannot | ✅ Can |
| Abstract methods | ✅ Can have | ❌ Cannot |
| Concrete methods | ✅ Can have | ✅ Can have |
| State (fields) | ✅ Can have | ✅ Can have |
| Constructor | ✅ Can have | ✅ Can have |

### Example: Payment Processing

```python
from abc import ABC, abstractmethod
from datetime import datetime

class PaymentProcessor(ABC):
    def __init__(self, merchant_id: str):
        self.merchant_id = merchant_id
        self._transaction_log = []
    
    # Concrete method - shared implementation
    def process_payment(self, amount: float, currency: str) -> dict:
        self._validate_amount(amount)
        result = self._execute_payment(amount, currency)
        self._log_transaction(amount, currency, result)
        return result
    
    # Abstract methods - subclass must implement
    @abstractmethod
    def _execute_payment(self, amount: float, currency: str) -> dict:
        pass
    
    @abstractmethod
    def refund(self, transaction_id: str, amount: float) -> dict:
        pass
    
    # Concrete helper method
    def _validate_amount(self, amount: float):
        if amount <= 0:
            raise ValueError("Amount must be positive")
    
    def _log_transaction(self, amount: float, currency: str, result: dict):
        self._transaction_log.append({
            "timestamp": datetime.now().isoformat(),
            "amount": amount,
            "currency": currency,
            "result": result
        })
    
    def get_transaction_history(self) -> list:
        return self._transaction_log.copy()

class StripeProcessor(PaymentProcessor):
    def __init__(self, merchant_id: str, api_key: str):
        super().__init__(merchant_id)
        self.api_key = api_key
    
    def _execute_payment(self, amount: float, currency: str) -> dict:
        # Stripe-specific payment logic
        return {
            "status": "success",
            "processor": "stripe",
            "transaction_id": "stripe_txn_123"
        }
    
    def refund(self, transaction_id: str, amount: float) -> dict:
        return {
            "status": "refunded",
            "processor": "stripe",
            "transaction_id": transaction_id
        }

class PayPalProcessor(PaymentProcessor):
    def __init__(self, merchant_id: str, client_secret: str):
        super().__init__(merchant_id)
        self.client_secret = client_secret
    
    def _execute_payment(self, amount: float, currency: str) -> dict:
        # PayPal-specific payment logic
        return {
            "status": "success",
            "processor": "paypal",
            "transaction_id": "paypal_txn_456"
        }
    
    def refund(self, transaction_id: str, amount: float) -> dict:
        return {
            "status": "refunded",
            "processor": "paypal",
            "transaction_id": transaction_id
        }
```

## Interfaces

An interface defines a contract that implementing classes must fulfill. It specifies **what** an object can do, not **how**.

### Python Interfaces (Protocol)

```python
from typing import Protocol, runtime_checkable
from dataclasses import dataclass

@runtime_checkable
class Serializable(Protocol):
    def serialize(self) -> str: ...
    def deserialize(self, data: str) -> None: ...

@runtime_checkable
class Cacheable(Protocol):
    def get_cache_key(self) -> str: ...
    def get_ttl(self) -> int: ...

@dataclass
class UserProfile:
    user_id: int
    name: str
    email: str
    
    def serialize(self) -> str:
        import json
        return json.dumps({"user_id": self.user_id, "name": self.name, "email": self.email})
    
    def deserialize(self, data: str) -> None:
        import json
        parsed = json.loads(data)
        self.user_id = parsed["user_id"]
        self.name = parsed["name"]
        self.email = parsed["email"]
    
    def get_cache_key(self) -> str:
        return f"user:{self.user_id}"
    
    def get_ttl(self) -> int:
        return 3600  # 1 hour

# Check if object satisfies protocol
profile = UserProfile(1, "Alice", "alice@example.com")
print(isinstance(profile, Serializable))  # True
print(isinstance(profile, Cacheable))     # True
```

### Java Interfaces

```java
// Interface definition
public interface Drawable {
    void draw();
    void resize(double factor);
    default void rotate(int degrees) {
        System.out.println("Rotating by " + degrees + " degrees");
    }
}

public interface Resizable {
    void setScale(double scale);
    double getScale();
}

// Multiple interface implementation
public class Circle implements Drawable, Resizable {
    private double radius;
    private double scale = 1.0;
    
    public Circle(double radius) {
        this.radius = radius;
    }
    
    @Override
    public void draw() {
        System.out.println("Drawing circle with radius " + (radius * scale));
    }
    
    @Override
    public void resize(double factor) {
        this.radius *= factor;
    }
    
    @Override
    public void setScale(double scale) {
        this.scale = scale;
    }
    
    @Override
    public double getScale() {
        return scale;
    }
}
```

## Abstract Class vs Interface

| Aspect | Abstract Class | Interface |
|--------|---------------|-----------|
| State | Can have instance variables | No state (constants only) |
| Methods | Abstract + concrete | Abstract (+ default in Java 8+) |
| Constructor | Can have | Cannot |
| Inheritance | Single | Multiple |
| Speed | Slightly faster | Slightly slower (indirection) |
| Use case | "is-a" with shared code | "can-do" capability |

### When to Use Which

```
Use Abstract Class when:
- Classes share common state (fields)
- You want to provide default implementation
- You need constructors
- "is-a" relationship with shared behavior

Use Interface when:
- You want to define a capability
- Multiple inheritance is needed
- Loose coupling is desired
- "can-do" relationship
```

### Example: Shape Hierarchy

```python
from abc import ABC, abstractmethod

# Interface-like: defines capability
class Drawable(ABC):
    @abstractmethod
    def draw(self) -> str: ...

class Scalable(ABC):
    @abstractmethod
    def scale(self, factor: float) -> None: ...

# Abstract class: shared state + behavior
class Shape(ABC, Drawable, Scalable):
    def __init__(self, color: str):
        self.color = color  # Shared state
    
    @abstractmethod
    def area(self) -> float: ...
    
    @abstractmethod
    def perimeter(self) -> float: ...
    
    def describe(self) -> str:  # Shared behavior
        return f"{self.color} shape with area {self.area():.2f}"

class Circle(Shape):
    def __init__(self, color: str, radius: float):
        super().__init__(color)
        self.radius = radius
    
    def area(self) -> float:
        return 3.14159 * self.radius ** 2
    
    def perimeter(self) -> float:
        return 2 * 3.14159 * self.radius
    
    def draw(self) -> str:
        return f"Drawing {self.color} circle"
    
    def scale(self, factor: float) -> None:
        self.radius *= factor
```

## Dependency Injection (DI)

**Definition**: A technique where an object receives its dependencies from external sources rather than creating them internally.

### Without DI (Tight Coupling)

```python
class MySQLDatabase:
    def query(self, sql: str):
        return f"MySQL: {sql}"

class UserService:
    def __init__(self):
        self.db = MySQLDatabase()  # Hard-coded dependency!
    
    def get_user(self, user_id: int):
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
```

**Problems**:
- Can't switch to PostgreSQL without changing UserService
- Can't mock database for testing
- Tight coupling between UserService and MySQLDatabase

### With DI (Loose Coupling)

```python
from abc import ABC, abstractmethod

class Database(ABC):
    @abstractmethod
    def query(self, sql: str) -> str: ...

class MySQLDatabase(Database):
    def query(self, sql: str) -> str:
        return f"MySQL: {sql}"

class PostgreSQLDatabase(Database):
    def query(self, sql: str) -> str:
        return f"PostgreSQL: {sql}"

class MockDatabase(Database):
    def query(self, sql: str) -> str:
        return f"Mock result for: {sql}"

class UserService:
    def __init__(self, db: Database):  # Injected dependency
        self.db = db
    
    def get_user(self, user_id: int):
        return self.db.query(f"SELECT * FROM users WHERE id = {user_id}")

# Usage - easy to swap implementations
service = UserService(MySQLDatabase())
service = UserService(PostgreSQLDatabase())
service = UserService(MockDatabase())  # For testing
```

### Types of Dependency Injection

#### Constructor Injection (Recommended)
```python
class OrderService:
    def __init__(self, payment_gateway: PaymentGateway, 
                 inventory_service: InventoryService):
        self.payment_gateway = payment_gateway
        self.inventory_service = inventory_service
```

#### Setter Injection
```python
class OrderService:
    def set_payment_gateway(self, gateway: PaymentGateway):
        self.payment_gateway = gateway
    
    def set_inventory_service(self, service: InventoryService):
        self.inventory_service = service
```

#### Method Injection
```python
class OrderService:
    def process_order(self, order: Order, 
                      payment_gateway: PaymentGateway):
        payment_gateway.charge(order.total)
```

## Inversion of Control (IoC)

**Definition**: A principle where the control of object creation and lifecycle is transferred from the application code to a framework or container.

### Traditional Control Flow
```python
# Application controls everything
class Application:
    def run(self):
        db = MySQLDatabase()        # App creates dependencies
        user_repo = UserRepository(db)  # App wires them together
        service = UserService(user_repo)
        service.get_user(1)
```

### IoC Control Flow
```python
# Framework/Container controls object creation
class IoCContainer:
    def __init__(self):
        self._registrations = {}
    
    def register(self, interface, implementation):
        self._registrations[interface] = implementation
    
    def resolve(self, interface):
        return self._registrations[interface]()

# Setup (typically at application startup)
container = IoCContainer()
container.register(Database, MySQLDatabase)
container.register(UserRepository, lambda: UserRepository(container.resolve(Database)))
container.register(UserService, lambda: UserService(container.resolve(UserRepository)))

# Usage - framework manages dependencies
service = container.resolve(UserService)
```

### IoC Benefits

| Benefit | Description |
|---------|-------------|
| **Loose coupling** | Components depend on abstractions |
| **Testability** | Easy to mock dependencies |
| **Flexibility** | Swap implementations easily |
| **Maintainability** | Changes are localized |

## Interface Segregation in Practice

```python
from abc import ABC, abstractmethod

# ❌ Fat interface - forces implementors to implement unused methods
class Worker(ABC):
    @abstractmethod
    def work(self): ...
    
    @abstractmethod
    def eat(self): ...
    
    @abstractmethod
    def sleep(self): ...

# ✅ Segregated interfaces
class Workable(ABC):
    @abstractmethod
    def work(self): ...

class Eatable(ABC):
    @abstractmethod
    def eat(self): ...

class Sleepable(ABC):
    @abstractmethod
    def sleep(self): ...

# Classes implement only what they need
class HumanWorker(Workable, Eatable, Sleepable):
    def work(self): return "Working..."
    def eat(self): return "Eating..."
    def sleep(self): return "Sleeping..."

class RobotWorker(Workable):  # Robots don't eat or sleep
    def work(self): return "Working efficiently..."
```

## Interview Tips

1. **Start with interfaces** — Define the contract first
2. **Use abstract classes for shared code** — When multiple classes share behavior
3. **Apply DI everywhere** — "I'll inject the database dependency"
4. **Explain your choices** — "Interface because we might have multiple implementations"
5. **Show testability** — "This design makes it easy to mock dependencies"
6. **Consider future changes** — "If we add a new payment method..."

## Common Mistakes

- ❌ Creating interfaces with too many methods
- ❌ Using abstract class when interface is sufficient
- ❌ Not using DI (hard-coding dependencies)
- ❌ Confusing "is-a" with "can-do"
- ❌ Over-abstracting (too many layers)

## Cross-References

- [SOLID Principles](./solid.md) — ISP and DIP directly relate
- [Design Patterns](./design-patterns.md) — Patterns use abstraction
- [OOP Concepts](./oop-concepts.md) — Foundation concepts
- [UML Class Diagrams](./uml-class-diagrams.md) — Visualizing abstractions
