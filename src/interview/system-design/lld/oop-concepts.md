# OOP Concepts for Interviews

## The Four Pillars of OOP

Object-Oriented Programming is built on four fundamental concepts. Mastering these is essential for LLD interviews.

## 1. Encapsulation

**Definition**: Bundling data (attributes) and methods that operate on that data into a single unit (class), and restricting direct access to internal state.

### Why Encapsulation?
- **Data integrity**: Control how state is modified
- **Reduced coupling**: Internal changes don't affect external code
- **Easier testing**: Can mock/replace implementations
- **Security**: Hide sensitive data

### Example
```python
class BankAccount:
    def __init__(self, owner: str, balance: float = 0):
        self._owner = owner          # Protected
        self.__balance = balance     # Private (name mangling)
        self.__transactions = []     # Private
    
    @property
    def balance(self) -> float:
        """Read-only access to balance"""
        return self.__balance
    
    @property
    def owner(self) -> str:
        return self._owner
    
    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.__balance += amount
        self.__transactions.append(f"Deposit: +{amount}")
    
    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if amount > self.__balance:
            raise ValueError("Insufficient funds")
        self.__balance -= amount
        self.__transactions.append(f"Withdrawal: -{amount}")
    
    def get_statement(self) -> list:
        return self.__transactions.copy()  # Return copy, not reference

# Usage
account = BankAccount("Alice", 1000)
account.deposit(500)
account.withdraw(200)
print(account.balance)  # 1300 (read-only)
# account.balance = 9999  # Error! Can't set directly
# account.__balance       # Error! Can't access private
```

### Java Example
```java
public class BankAccount {
    private String owner;
    private double balance;
    private List<String> transactions;
    
    public BankAccount(String owner, double balance) {
        this.owner = owner;
        this.balance = balance;
        this.transactions = new ArrayList<>();
    }
    
    public double getBalance() {
        return balance;
    }
    
    public String getOwner() {
        return owner;
    }
    
    public void deposit(double amount) {
        if (amount <= 0) throw new IllegalArgumentException("Amount must be positive");
        this.balance += amount;
        transactions.add("Deposit: +" + amount);
    }
    
    public void withdraw(double amount) {
        if (amount <= 0) throw new IllegalArgumentException("Amount must be positive");
        if (amount > balance) throw new IllegalStateException("Insufficient funds");
        this.balance -= amount;
        transactions.add("Withdrawal: -" + amount);
    }
}
```

## 2. Inheritance

**Definition**: A mechanism where a new class (child/subclass) inherits attributes and methods from an existing class (parent/superclass).

### Why Inheritance?
- **Code reuse**: Common logic in parent class
- **Polymorphism**: Treat child objects as parent type
- **Hierarchy**: Model "is-a" relationships

### Example
```python
from abc import ABC, abstractmethod

class Animal(ABC):
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age
    
    @abstractmethod
    def make_sound(self) -> str:
        pass
    
    @abstractmethod
    def get_type(self) -> str:
        pass
    
    def describe(self) -> str:
        return f"{self.name} is {self.age} years old"

class Dog(Animal):
    def __init__(self, name: str, age: int, breed: str):
        super().__init__(name, age)
        self.breed = breed
    
    def make_sound(self) -> str:
        return "Woof!"
    
    def get_type(self) -> str:
        return "Dog"
    
    def fetch(self, item: str) -> str:
        return f"{self.name} fetches the {item}"

class Cat(Animal):
    def __init__(self, name: str, age: int, indoor: bool):
        super().__init__(name, age)
        self.indoor = indoor
    
    def make_sound(self) -> str:
        return "Meow!"
    
    def get_type(self) -> str:
        return "Cat"
    
    def purr(self) -> str:
        return f"{self.name} purrs..."

# Usage
dog = Dog("Rex", 5, "German Shepherd")
cat = Cat("Whiskers", 3, True)

print(dog.describe())      # "Rex is 5 years old"
print(dog.make_sound())    # "Woof!"
print(dog.fetch("ball"))   # "Rex fetches the ball"
print(cat.make_sound())    # "Meow!"
```

### Inheritance Anti-Patterns

```python
# ❌ Bad: Inheritance for code reuse only
class FileManager:
    def read_file(self, path):
        ...

class NetworkManager(FileManager):  # NetworkManager "is-a" FileManager? No!
    def send_data(self, data):
        # Reusing read_file doesn't make sense here
        ...

# ✅ Good: Composition over inheritance
class FileReader:
    def read_file(self, path):
        ...

class NetworkManager:
    def __init__(self, file_reader: FileReader):
        self.file_reader = file_reader  # Has-a relationship
```

## 3. Polymorphism

**Definition**: The ability of different classes to be treated as instances of the same class through a common interface. "One interface, many forms."

### Types of Polymorphism

#### Compile-time (Method Overloading)
```python
# Python doesn't support true overloading, but we can simulate it
class Calculator:
    def add(self, a, b, c=None):
        if c is not None:
            return a + b + c
        return a + b
```

```java
// Java: True method overloading
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
    
    public int add(int a, int b, int c) {
        return a + b + c;
    }
    
    public double add(double a, double b) {
        return a + b;
    }
}
```

#### Runtime (Method Overriding)
```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        pass
    
    @abstractmethod
    def perimeter(self) -> float:
        pass

class Circle(Shape):
    def __init__(self, radius: float):
        self.radius = radius
    
    def area(self) -> float:
        return 3.14159 * self.radius ** 2
    
    def perimeter(self) -> float:
        return 2 * 3.14159 * self.radius

class Rectangle(Shape):
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height
    
    def area(self) -> float:
        return self.width * self.height
    
    def perimeter(self) -> float:
        return 2 * (self.width + self.height)

class Triangle(Shape):
    def __init__(self, a: float, b: float, c: float):
        self.a = a
        self.b = b
        self.c = c
    
    def area(self) -> float:
        s = (self.a + self.b + self.c) / 2
        return (s * (s - self.a) * (s - self.b) * (s - self.c)) ** 0.5
    
    def perimeter(self) -> float:
        return self.a + self.b + self.c

# Polymorphism in action
def print_shape_info(shape: Shape):
    print(f"Area: {shape.area():.2f}")        # Same method call
    print(f"Perimeter: {shape.perimeter():.2f}")  # Different behavior

shapes = [Circle(5), Rectangle(4, 6), Triangle(3, 4, 5)]
for shape in shapes:
    print_shape_info(shape)  # Works with any Shape subclass
```

### Duck Typing (Python)
```python
# Python: If it quacks like a duck, it's a duck
class Duck:
    def quack(self):
        return "Quack!"
    
    def swim(self):
        return "Swimming"

class Person:
    def quack(self):
        return "I'm quacking like a duck!"
    
    def swim(self):
        return "Swimming like a human"

def make_it_quack(thing):
    print(thing.quack())  # Works if object has quack()

make_it_quack(Duck())    # "Quack!"
make_it_quack(Person())  # "I'm quacking like a duck!"
```

## 4. Abstraction

**Definition**: Hiding complex implementation details and exposing only the essential features.

### Abstract Classes vs Interfaces

```python
from abc import ABC, abstractmethod

# Abstract class: Can have state and partial implementation
class Database(ABC):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._connected = False
    
    def connect(self):
        """Template method - concrete implementation"""
        print(f"Connecting to {self.connection_string}")
        self._connect()  # Delegate to subclass
        self._connected = True
    
    @abstractmethod
    def _connect(self):
        """Subclass must implement this"""
        pass
    
    @abstractmethod
    def query(self, sql: str):
        pass
    
    @abstractmethod
    def close(self):
        pass

class MySQLDatabase(Database):
    def _connect(self):
        print("MySQL specific connection logic")
    
    def query(self, sql: str):
        if not self._connected:
            raise Exception("Not connected")
        print(f"MySQL executing: {sql}")
        return [{"result": "data"}]
    
    def close(self):
        print("Closing MySQL connection")
        self._connected = False

class PostgreSQLDatabase(Database):
    def _connect(self):
        print("PostgreSQL specific connection logic")
    
    def query(self, sql: str):
        if not self._connected:
            raise Exception("Not connected")
        print(f"PostgreSQL executing: {sql}")
        return [{"result": "data"}]
    
    def close(self):
        print("Closing PostgreSQL connection")
        self._connected = False
```

### Interface (Python Protocol)
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Drawable(Protocol):
    def draw(self) -> str: ...
    def resize(self, factor: float) -> None: ...

class Circle:
    def __init__(self, radius: float):
        self.radius = radius
    
    def draw(self) -> str:
        return f"Drawing circle with radius {self.radius}"
    
    def resize(self, factor: float) -> None:
        self.radius *= factor

class Square:
    def __init__(self, side: float):
        self.side = side
    
    def draw(self) -> str:
        return f"Drawing square with side {self.side}"
    
    def resize(self, factor: float) -> None:
        self.side *= factor

# Both satisfy Drawable protocol without explicit inheritance
def render(obj: Drawable):
    print(obj.draw())

render(Circle(5))   # Works!
render(Square(4))   # Works!
```

## Composition vs Inheritance

### The Problem with Inheritance

```python
# ❌ Deep inheritance hierarchy - fragile
class Vehicle:
    def start(self): ...

class MotorVehicle(Vehicle):
    def honk(self): ...

class Car(MotorVehicle):
    def open_trunk(self): ...

class SportsCar(Car):
    def enable_turbo(self): ...

# Problems:
# - Deep coupling
# - Hard to change
# - "Fragile base class" problem
# - Can't model multiple behaviors
```

### Composition is Better

```python
# ✅ Composition - flexible
class Engine:
    def start(self): return "Engine started"
    def stop(self): return "Engine stopped"

class GPS:
    def get_location(self): return (40.7128, -74.0060)
    def navigate(self, dest): return f"Navigating to {dest}"

class AudioSystem:
    def play_music(self, song): return f"Playing {song}"

class Car:
    def __init__(self):
        self.engine = Engine()        # Has-a
        self.gps = GPS()              # Has-a
        self.audio = AudioSystem()    # Has-a
    
    def start(self):
        return self.engine.start()
    
    def navigate(self, destination):
        return self.gps.navigate(destination)
    
    def play_music(self, song):
        return self.audio.play_music(song)

# Easy to swap components
class ElectricEngine:
    def start(self): return "Electric engine started silently"
    def stop(self): return "Electric engine stopped"

class ElectricCar(Car):
    def __init__(self):
        self.engine = ElectricEngine()  # Swap engine
        self.gps = GPS()
        self.audio = AudioSystem()
```

### When to Use Each

| Use Inheritance When | Use Composition When |
|---------------------|---------------------|
| True "is-a" relationship | "Has-a" relationship |
| Shared interface | Shared behavior |
| Shallow hierarchy (1-2 levels) | Deep hierarchy needed |
| Framework requires it | Need flexibility |
| Base class is stable | Components may change |

## Interview Tips

1. **Name the concept** — "I'm using polymorphism here to handle different payment types"
2. **Show practical examples** — Don't just define terms, show code
3. **Discuss trade-offs** — "Inheritance gives us code reuse but composition is more flexible"
4. **Apply SOLID** — OOP concepts are foundation for SOLID
5. **Use appropriate language features** — Abstract classes, interfaces, protocols

## Common Mistakes

- ❌ Deep inheritance hierarchies (more than 2-3 levels)
- ❌ Using inheritance for code reuse only
- ❌ Exposing internal state (violating encapsulation)
- ❌ Not using abstract classes/interfaces
- ❌ Confusing "is-a" with "has-a"

## Cross-References

- [SOLID Principles](./solid.md) — SOLID builds on OOP
- [Design Patterns](./design-patterns.md) — Patterns use OOP concepts
- [Abstraction & Interfaces](./abstraction-interfaces.md) — Deep dive on abstraction
- [UML Class Diagrams](./uml-class-diagrams.md) — Visualizing OOP
