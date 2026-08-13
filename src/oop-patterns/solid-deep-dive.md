# SOLID Principles Deep Dive

The SOLID principles are five foundational design principles for object-oriented programming, introduced by Robert C. Martin (Uncle Bob). They guide developers toward code that is easier to maintain, extend, and test. Each principle addresses a specific aspect of software design, and together they form a framework for building robust systems.

## 1. Single Responsibility Principle (SRP)

### Definition
A class should have only one reason to change. Every class should have a single, well-defined responsibility.

### Why It Matters
When a class has multiple responsibilities, changes to one responsibility can break the other. This creates fragile code that is hard to test and modify. SRP promotes high cohesion—keeping related behavior together—and low coupling—keeping unrelated behavior apart.

### Violation Example (Java)
```java
// BAD: This class has multiple responsibilities
public class Employee {
    private String name;
    private double salary;
    
    public Employee(String name, double salary) {
        this.name = name;
        this.salary = salary;
    }
    
    // Responsibility 1: Employee data
    public String getName() { return name; }
    public double getSalary() { return salary; }
    
    // Responsibility 2: Salary calculation
    public double calculateTax() {
        return salary * 0.3;
    }
    
    // Responsibility 3: Persistence
    public void saveToDatabase() {
        // SQL INSERT logic
    }
    
    // Responsibility 4: Reporting
    public String generateReport() {
        return String.format("Employee: %s, Salary: %.2f", name, salary);
    }
}
```

This class changes when:
- Employee data model changes
- Tax calculation rules change
- Database schema changes
- Report format changes

### Refactored (Java)
```java
// Employee data model
public class Employee {
    private String name;
    private double salary;
    
    public Employee(String name, double salary) {
        this.name = name;
        this.salary = salary;
    }
    
    public String getName() { return name; }
    public double getSalary() { return salary; }
}

// Tax calculation responsibility
public class TaxCalculator {
    public double calculateTax(Employee employee) {
        return employee.getSalary() * 0.3;
    }
}

// Persistence responsibility
public class EmployeeRepository {
    public void save(Employee employee) {
        // SQL INSERT logic
    }
    
    public Employee findById(int id) {
        // SQL SELECT logic
    }
}

// Reporting responsibility
public class ReportGenerator {
    public String generateEmployeeReport(Employee employee) {
        return String.format("Employee: %s, Salary: %.2f",
            employee.getName(), employee.getSalary());
    }
}
```

### Violation Example (Python)
```python
# BAD: Multiple responsibilities in one class
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
    
    def validate_email(self):
        return '@' in self.email
    
    def save_to_db(self):
        db.execute("INSERT INTO users VALUES (?, ?)", self.name, self.email)
    
    def send_welcome_email(self):
        smtp.send(self.email, "Welcome!", f"Hello {self.name}")
    
    def to_json(self):
        return json.dumps({"name": self.name, "email": self.email})
```

### Refactored (Python)
```python
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email

class EmailValidator:
    @staticmethod
    def is_valid(email):
        return '@' in email and '.' in email.split('@')[1]

class UserRepository:
    def save(self, user):
        db.execute("INSERT INTO users VALUES (?, ?)", user.name, user.email)
    
    def find_by_id(self, user_id):
        return db.execute("SELECT * FROM users WHERE id = ?", user_id)

class EmailService:
    def send_welcome(self, user):
        smtp.send(user.email, "Welcome!", f"Hello {user.name}")

class UserSerializer:
    def to_json(self, user):
        return json.dumps({"name": user.name, "email": user.email})
```

### Key Takeaway
Ask: "Does this class have more than one reason to change?" If yes, split it.

---

## 2. Open-Closed Principle (OCP)

### Definition
Software entities should be open for extension but closed for modification. You should be able to add new behavior without changing existing code.

### Why It Matters
Modifying existing code risks introducing bugs in working functionality. OCP encourages designing systems where new features are added by writing new code (extending) rather than changing existing code (modifying).

### Violation Example (Java)
```java
// BAD: Must modify this class every time we add a new shape
public class AreaCalculator {
    public double calculate(Object shape) {
        if (shape instanceof Circle) {
            Circle c = (Circle) shape;
            return Math.PI * c.getRadius() * c.getRadius();
        } else if (shape instanceof Rectangle) {
            Rectangle r = (Rectangle) shape;
            return r.getWidth() * r.getHeight();
        } else if (shape instanceof Triangle) {
            Triangle t = (Triangle) shape;
            return 0.5 * t.getBase() * t.getHeight();
        }
        // Every new shape requires adding another else-if
        throw new IllegalArgumentException("Unknown shape");
    }
}
```

### Refactored (Java)
```java
// Open for extension: add new shapes by implementing the interface
// Closed for modification: AreaCalculator never changes
public interface Shape {
    double area();
}

public class Circle implements Shape {
    private double radius;
    
    public Circle(double radius) { this.radius = radius; }
    
    @Override
    public double area() {
        return Math.PI * radius * radius;
    }
}

public class Rectangle implements Shape {
    private double width, height;
    
    public Rectangle(double width, double height) {
        this.width = width;
        this.height = height;
    }
    
    @Override
    public double area() {
        return width * height;
    }
}

public class Triangle implements Shape {
    private double base, height;
    
    public Triangle(double base, double height) {
        this.base = base;
        this.height = height;
    }
    
    @Override
    public double area() {
        return 0.5 * base * height;
    }
}

// This class is CLOSED for modification
public class AreaCalculator {
    public double calculate(Shape shape) {
        return shape.area();
    }
    
    public double calculateTotal(List<Shape> shapes) {
        return shapes.stream().mapToDouble(Shape::area).sum();
    }
}
```

### Violation Example (Python)
```python
# BAD: Type checking with if/elif chains
def calculate_discount(customer_type, amount):
    if customer_type == "regular":
        return amount * 0.05
    elif customer_type == "premium":
        return amount * 0.10
    elif customer_type == "vip":
        return amount * 0.20
    # Adding a new type requires modifying this function
```

### Refactored (Python)
```python
from abc import ABC, abstractmethod

class DiscountStrategy(ABC):
    @abstractmethod
    def calculate(self, amount):
        pass

class RegularDiscount(DiscountStrategy):
    def calculate(self, amount):
        return amount * 0.05

class PremiumDiscount(DiscountStrategy):
    def calculate(self, amount):
        return amount * 0.10

class VIPDiscount(DiscountStrategy):
    def calculate(self, amount):
        return amount * 0.20

# New discount types are added by creating new classes, not modifying this
class DiscountCalculator:
    def __init__(self, strategy: DiscountStrategy):
        self.strategy = strategy
    
    def calculate(self, amount):
        return self.strategy.calculate(amount)

# Adding a new discount type:
class EmployeeDiscount(DiscountStrategy):
    def calculate(self, amount):
        return amount * 0.30
```

### Key Takeaway
Use abstractions (interfaces, abstract classes) to allow extension without modification. The Strategy pattern is the most common way to achieve OCP.

---

## 3. Liskov Substitution Principle (LSP)

### Definition
Objects of a superclass should be replaceable with objects of a subclass without breaking the correctness of the program. If S is a subtype of T, then objects of type T may be replaced with objects of type S without altering any desirable properties of the program.

### Why It Matters
LSP ensures that inheritance is used correctly. Violating LSP means that code that works with a base class will break when given a subclass, which defeats the purpose of polymorphism and leads to fragile `instanceof` checks.

### Classic Violation: Rectangle and Square
```java
// Mathematical relationship: Square IS-A Rectangle
// But in code, this inheritance violates LSP

public class Rectangle {
    protected double width;
    protected double height;
    
    public void setWidth(double width) { this.width = width; }
    public void setHeight(double height) { this.height = height; }
    
    public double area() { return width * height; }
}

public class Square extends Rectangle {
    @Override
    public void setWidth(double width) {
        this.width = width;
        this.height = width;  // Square constraint
    }
    
    @Override
    public void setHeight(double height) {
        this.width = height;  // Square constraint
        this.height = height;
    }
}

// This code works with Rectangle but BREAKS with Square
void testArea(Rectangle r) {
    r.setWidth(5);
    r.setHeight(4);
    assert r.area() == 20;  // FAILS for Square! area = 16
}
```

### Refactored (Java)
```java
// Use composition or separate interfaces
public interface Shape {
    double area();
}

public class Rectangle implements Shape {
    private final double width;
    private final double height;
    
    public Rectangle(double width, double height) {
        this.width = width;
        this.height = height;
    }
    
    @Override
    public double area() { return width * height; }
}

public class Square implements Shape {
    private final double side;
    
    public Square(double side) {
        this.side = side;
    }
    
    @Override
    public double area() { return side * side; }
}
```

### Python Violation
```python
class Bird:
    def fly(self):
        return "Flying"

class Ostrich(Bird):
    def fly(self):
        raise NotImplementedError("Ostriches can't fly")
        # LSP violation: code expecting Bird.fly() breaks with Ostrich

# Refactored: Use composition
class Bird:
    def __init__(self, movement):
        self.movement = movement
    def move(self):
        return self.movement.move()

class FlyingBehavior:
    def move(self):
        return "Flying"

class RunningBehavior:
    def move(self):
        return "Running"

# Usage
eagle = Bird(FlyingBehavior())
ostrich = Bird(RunningBehavior())
print(eagle.move())   # "Flying"
print(ostrich.move()) # "Running"
```

### Key Takeaway
Subclasses should honor the contracts of their parent classes: preconditions cannot be strengthened, postconditions cannot be weakened, and invariants must be preserved.

---

## 4. Interface Segregation Principle (ISP)

### Definition
Clients should not be forced to depend on interfaces they do not use. Prefer many small, focused interfaces over one large, general-purpose interface.

### Why It Matters
Fat interfaces force implementing classes to provide methods they don't need (often with empty or throwing implementations). This creates coupling and makes the system harder to change.

### Violation Example (Java)
```java
// BAD: One fat interface forces all workers to implement irrelevant methods
public interface Worker {
    void work();
    void eat();
    void sleep();
}

// A robot worker doesn't eat or sleep
public class RobotWorker implements Worker {
    @Override
    public void work() { /* works fine */ }
    
    @Override
    public void eat() { throw new UnsupportedOperationException(); }
    
    @Override
    public void sleep() { throw new UnsupportedOperationException(); }
}
```

### Refactored (Java)
```java
// Segregated interfaces
public interface Workable {
    void work();
}

public interface Feedable {
    void eat();
}

public interface Sleepable {
    void sleep();
}

// Human worker implements all interfaces
public class HumanWorker implements Workable, Feedable, Sleepable {
    @Override
    public void work() { /* ... */ }
    
    @Override
    public void eat() { /* ... */ }
    
    @Override
    public void sleep() { /* ... */ }
}

// Robot worker only implements what it needs
public class RobotWorker implements Workable {
    @Override
    public void work() { /* ... */ }
}
```

### Python Violation and Fix
```python
# BAD
class Machine(ABC):
    @abstractmethod
    def print_document(self, doc): pass
    
    @abstractmethod
    def scan_document(self, doc): pass
    
    @abstractmethod
    def fax_document(self, doc): pass

class SimplePrinter(Machine):
    def print_document(self, doc):
        print(f"Printing {doc}")
    
    def scan_document(self, doc):
        raise NotImplementedError("SimplePrinter can't scan")
    
    def fax_document(self, doc):
        raise NotImplementedError("SimplePrinter can't fax")

# GOOD: Segregated interfaces
class Printer(ABC):
    @abstractmethod
    def print_document(self, doc): pass

class Scanner(ABC):
    @abstractmethod
    def scan_document(self, doc): pass

class Fax(ABC):
    @abstractmethod
    def fax_document(self, doc): pass

class SimplePrinter(Printer):
    def print_document(self, doc):
        print(f"Printing {doc}")

class MultiFunctionMachine(Printer, Scanner, Fax):
    def print_document(self, doc): print(f"Printing {doc}")
    def scan_document(self, doc): print(f"Scanning {doc}")
    def fax_document(self, doc): print(f"Faxing {doc}")
```

### Key Takeaway
If an interface has methods that some implementations don't need, split it into smaller, more focused interfaces.

---

## 5. Dependency Inversion Principle (DIP)

### Definition
High-level modules should not depend on low-level modules. Both should depend on abstractions. Abstractions should not depend on details. Details should depend on abstractions.

### Why It Matters
Without DIP, high-level business logic is tightly coupled to low-level infrastructure (databases, file systems, APIs). This makes the code hard to test (you can't mock the database) and hard to change (switching databases requires rewriting business logic).

### Violation Example (Java)
```java
// BAD: High-level module depends directly on low-level module
public class OrderService {
    private MySQLDatabase database;  // Direct dependency on MySQL
    
    public OrderService() {
        this.database = new MySQLDatabase();  // Tightly coupled
    }
    
    public void placeOrder(Order order) {
        // Business logic
        database.insertOrder(order);  // Can't test without MySQL
    }
}

public class MySQLDatabase {
    public void insertOrder(Order order) {
        // MySQL-specific SQL
    }
}
```

### Refactored (Java)
```java
// Abstraction (interface)
public interface OrderRepository {
    void save(Order order);
    Order findById(String id);
}

// Low-level module implements abstraction
public class MySQLOrderRepository implements OrderRepository {
    @Override
    public void save(Order order) {
        // MySQL-specific implementation
    }
    
    @Override
    public Order findById(String id) {
        // MySQL-specific implementation
    }
}

// High-level module depends on abstraction
public class OrderService {
    private final OrderRepository repository;
    
    // Dependency injected through constructor
    public OrderService(OrderRepository repository) {
        this.repository = repository;
    }
    
    public void placeOrder(Order order) {
        // Business logic using the abstraction
        repository.save(order);
    }
}

// Easy to swap implementations
OrderService serviceWithMySQL = new OrderService(new MySQLOrderRepository());
OrderService serviceWithPostgres = new OrderService(new PostgresOrderRepository());
OrderService serviceForTesting = new OrderService(new InMemoryOrderRepository());
```

### Python
```python
# BAD
class OrderService:
    def __init__(self):
        self.db = MySQLDatabase()  # Direct dependency
    
    def place_order(self, order):
        self.db.insert(order)

# GOOD
class OrderRepository(ABC):
    @abstractmethod
    def save(self, order): pass

class MySQLOrderRepository(OrderRepository):
    def save(self, order):
        # MySQL implementation
        pass

class InMemoryOrderRepository(OrderRepository):
    def __init__(self):
        self.orders = []
    
    def save(self, order):
        self.orders.append(order)

class OrderService:
    def __init__(self, repository: OrderRepository):
        self.repository = repository
    
    def place_order(self, order):
        # Business logic
        self.repository.save(order)

# Testing is easy
service = OrderService(InMemoryOrderRepository())
```

### Key Takeaway
Depend on abstractions, not concretions. Use dependency injection to provide implementations at runtime. This makes code testable, flexible, and decoupled.

---

## SOLID in Practice

### How SOLID Principles Work Together
- **SRP** ensures each class has a focused purpose
- **OCP** ensures new features don't require modifying existing code
- **LSP** ensures inheritance hierarchies are correct
- **ISP** ensures interfaces are lean and focused
- **DIP** ensures modules are decoupled through abstractions

### When to Bend the Rules
SOLID principles are guidelines, not absolute laws. In some situations, strict adherence adds unnecessary complexity:
- **Small scripts**: SOLID is overkill for throwaway code
- **Performance-critical code**: Abstraction layers add overhead
- **Simple domains**: If a class genuinely has one reason to change and one responsibility, don't split it further
- **Prototypes**: Move fast first, refactor later

The key is understanding the principles well enough to know when to apply them and when to make pragmatic trade-offs.
