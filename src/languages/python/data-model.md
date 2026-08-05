# Python Data Model — Dunder Methods and Object Protocol

## Overview

Python's **data model** is the framework that makes the language consistent and extensible. Every built-in operation (calling `len()`, using `[]`, iteration, `with` statements) is backed by a **dunder (double underscore) method**. Understanding the data model lets you make your custom classes behave like built-in types.

---

## The Dunder Methods Philosophy

```python
# len() doesn't just "count" — it calls __len__
class MyCollection:
    def __init__(self, items):
        self._items = items
    
    def __len__(self):
        return len(self._items)

c = MyCollection([1, 2, 3])
print(len(c))  # Calls c.__len__() → 3

# [] doesn't just "index" — it calls __getitem__
class MyList:
    def __init__(self, data):
        self._data = data
    
    def __getitem__(self, index):
        return self._data[index]

lst = MyList([10, 20, 30])
print(lst[1])  # Calls lst.__getitem__(1) → 20
```

---

## String Representation: `__str__` and `__repr__`

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def __repr__(self):
        """Unambiguous representation — for developers/debugging.
        Should ideally be valid Python to recreate the object."""
        return f"Point({self.x}, {self.y})"
    
    def __str__(self):
        """Human-readable string — for end users.
        Called by print() and str()."""
        return f"({self.x}, {self.y})"

p = Point(3, 4)
print(repr(p))  # "Point(3, 4)" — developer-facing
print(str(p))   # "(3, 4)" — user-facing
print(p)        # Uses __str__ → "(3, 4)"

# If only __repr__ is defined, it's used as fallback for __str__
```

---

## Container Protocols

### `__len__` and `__bool__`

```python
class ShoppingCart:
    def __init__(self):
        self.items = []
    
    def add(self, item, price):
        self.items.append({"item": item, "price": price})
    
    def __len__(self):
        """Called by len()."""
        return len(self.items)
    
    def __bool__(self):
        """Called by bool() and truthiness checks.
        If not defined, Python falls back to __len__ (0 = False)."""
        return len(self.items) > 0

cart = ShoppingCart()
print(bool(cart))  # False — empty cart
cart.add("Apple", 1.50)
print(bool(cart))  # True — has items
print(len(cart))   # 1

# Truthiness: if cart:  →  calls __bool__ first, then __len__
```

### `__getitem__`, `__setitem__`, `__delitem__`

```python
class DictLike:
    """A class that behaves like a dictionary."""
    def __init__(self):
        self._data = {}
    
    def __getitem__(self, key):
        """Called by obj[key]."""
        return self._data[key]
    
    def __setitem__(self, key, value):
        """Called by obj[key] = value."""
        self._data[key] = value
    
    def __delitem__(self, key):
        """Called by del obj[key]."""
        del self._data[key]
    
    def __contains__(self, key):
        """Called by 'key in obj'."""
        return key in self._data

d = DictLike()
d["name"] = "Alice"      # __setitem__
print(d["name"])          # __getitem__
print("name" in d)        # __contains__
del d["name"]             # __delitem__
```

### `__iter__` and `__next__` — Iterators

```python
class Fibonacci:
    """Iterable Fibonacci sequence."""
    def __init__(self, max_count):
        self.max_count = max_count
    
    def __iter__(self):
        """Returns an iterator object (often self)."""
        self.a, self.b = 0, 1
        self.count = 0
        return self
    
    def __next__(self):
        """Returns next value. Raises StopIteration when done."""
        if self.count >= self.max_count:
            raise StopIteration
        value = self.a
        self.a, self.b = self.b, self.a + self.b
        self.count += 1
        return value

# Usage
for num in Fibonacci(10):
    print(num, end=" ")  # 0 1 1 2 3 5 8 13 21 34
print()

# Also enables: list(Fibonacci(5)), tuple(Fibonacci(5)), etc.
```

### `__reversed__`

```python
class Countdown:
    def __init__(self, start):
        self.start = start
    
    def __iter__(self):
        return iter(range(self.start, 0, -1))
    
    def __reversed__(self):
        """Called by reversed()."""
        return iter(range(1, self.start + 1))

c = Countdown(5)
print(list(c))           # [5, 4, 3, 2, 1]
print(list(reversed(c)))  # [1, 2, 3, 4, 5]
```

---

## Numeric Protocols

```python
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def __add__(self, other):
        """Called by self + other."""
        return Vector(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        """Called by self - other."""
        return Vector(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar):
        """Called by self * scalar."""
        return Vector(self.x * scalar, self.y * scalar)
    
    def __rmul__(self, scalar):
        """Called by scalar * self (when left operand doesn't support it)."""
        return self.__mul__(scalar)
    
    def __neg__(self):
        """Called by -self."""
        return Vector(-self.x, -self.y)
    
    def __abs__(self):
        """Called by abs(self)."""
        return (self.x ** 2 + self.y ** 2) ** 0.5
    
    def __eq__(self, other):
        """Called by self == other."""
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        """Must be defined if __eq__ is defined (for use in sets/dicts)."""
        return hash((self.x, self.y))
    
    def __repr__(self):
        return f"Vector({self.x}, {self.y})"

v1 = Vector(1, 2)
v2 = Vector(3, 4)
print(v1 + v2)     # Vector(4, 6)
print(v1 - v2)     # Vector(-2, -2)
print(v1 * 3)      # Vector(3, 6)
print(3 * v1)      # Vector(3, 6) — uses __rmul__
print(abs(v1))     # 2.236...
print(-v1)         # Vector(-1, -2)
```

### In-Place Operators

```python
class Counter:
    def __init__(self, value=0):
        self.value = value
    
    def __iadd__(self, other):
        """Called by self += other. Must return self."""
        self.value += other
        return self
    
    def __isub__(self, other):
        """Called by self -= other."""
        self.value -= other
        return self
    
    def __repr__(self):
        return f"Counter({self.value})"

c = Counter(10)
c += 5
print(c)  # Counter(15)
```

---

## Callable: `__call__`

```python
class Multiplier:
    """A callable object — instances work like functions."""
    def __init__(self, factor):
        self.factor = factor
    
    def __call__(self, x):
        return x * self.factor

double = Multiplier(2)
triple = Multiplier(3)

print(double(5))   # 10
print(triple(5))   # 15

# Useful for: decorators, strategy pattern, stateful functions
# Check if object is callable
print(callable(double))  # True
```

---

## Context Managers: `__enter__` and `__exit__`

```python
class Timer:
    """Context manager that measures execution time."""
    def __init__(self, label="Block"):
        self.label = label
    
    def __enter__(self):
        """Called at the start of 'with' block. Returns value for 'as'."""
        import time
        self.start = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Called at the end of 'with' block.
        Args: exception type, value, traceback (None if no exception).
        Return True to suppress exception, False to propagate."""
        import time
        elapsed = time.perf_counter() - self.start
        print(f"{self.label}: {elapsed:.4f}s")
        return False  # Don't suppress exceptions

with Timer("Computation"):
    total = sum(range(1_000_000))

# Output: Computation: 0.0312s
```

### Context Manager with `contextlib`

```python
from contextlib import contextmanager

@contextmanager
def timer(label="Block"):
    """Generator-based context manager — simpler syntax."""
    import time
    start = time.perf_counter()
    try:
        yield  # Value for 'as' clause (if needed)
    finally:
        elapsed = time.perf_counter() - start
        print(f"{label}: {elapsed:.4f}s")

with timer("Fast operation"):
    sum(range(1_000_000))
```

---

## Descriptors — Attribute Access Control

Descriptors are objects that define `__get__`, `__set__`, or `__delete__` to customize attribute access:

```python
class Validated:
    """Descriptor that validates attribute values."""
    def __init__(self, min_value=None, max_value=None):
        self.min_value = min_value
        self.max_value = max_value
    
    def __set_name__(self, owner, name):
        """Called when descriptor is assigned to a class attribute."""
        self.name = name
        self.storage_name = f"_validated_{name}"
    
    def __get__(self, obj, objtype=None):
        """Called when attribute is read."""
        if obj is None:
            return self  # Class-level access returns descriptor itself
        return getattr(obj, self.storage_name, None)
    
    def __set__(self, obj, value):
        """Called when attribute is assigned."""
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"{self.name} must be >= {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"{self.name} must be <= {self.max_value}")
        setattr(obj, self.storage_name, value)

class Student:
    age = Validated(min_value=0, max_value=150)
    grade = Validated(min_value=0, max_value=100)
    
    def __init__(self, name, age, grade):
        self.name = name
        self.age = age      # Calls Validated.__set__
        self.grade = grade

s = Student("Alice", 20, 95)
print(s.age)  # 20 — calls Validated.__get__

try:
    s.age = -5  # Raises ValueError
except ValueError as e:
    print(e)  # "age must be >= 0"
```

### Property — Simpler Descriptor

```python
class Circle:
    def __init__(self, radius):
        self._radius = radius
    
    @property
    def radius(self):
        """Getter — called when accessing circle.radius."""
        return self._radius
    
    @radius.setter
    def radius(self, value):
        """Setter — called when assigning circle.radius = value."""
        if value < 0:
            raise ValueError("Radius cannot be negative")
        self._radius = value
    
    @property
    def area(self):
        """Read-only property — no setter defined."""
        import math
        return math.pi * self._radius ** 2

c = Circle(5)
print(c.area)      # 78.54...
c.radius = 10      # Calls setter
print(c.area)      # 314.16...
# c.area = 100     # AttributeError — read-only
```

---

## Metaclasses

A **metaclass** is the class of a class. Just as instances are created from classes, classes are created from metaclasses:

```python
# type is the default metaclass
class MyClass:
    pass

print(type(MyClass))  # <class 'type'>
print(type(MyClass()))  # <class 'MyClass'>

# Custom metaclass
class SingletonMeta(type):
    """Metaclass that ensures only one instance exists."""
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Database(metaclass=SingletonMeta):
    def __init__(self):
        print("Connecting to database...")

db1 = Database()  # "Connecting to database..."
db2 = Database()  # No output — reuses existing instance
print(db1 is db2)  # True
```

### Metaclass for Attribute Validation

```python
class ValidatedMeta(type):
    """Metaclass that validates class definitions."""
    def __new__(mcs, name, bases, namespace):
        # Check that all public methods have docstrings
        for key, value in namespace.items():
            if callable(value) and not key.startswith('_'):
                if not value.__doc__:
                    raise TypeError(f"Method {key} in {name} needs a docstring")
        return super().__new__(mcs, name, bases, namespace)

class MyService(metaclass=ValidatedMeta):
    def process(self):
        """Process the data."""
        pass
    
    # This would raise TypeError:
    # def bad_method(self):
    #     pass
```

---

## `__slots__` — Preventing Dynamic Attributes

```python
class SlottedClass:
    __slots__ = ('x', 'y')
    
    def __init__(self, x, y):
        self.x = x
        self.y = y

obj = SlottedClass(1, 2)
print(obj.x, obj.y)  # 1 2

# Cannot add new attributes
try:
    obj.z = 3
except AttributeError as e:
    print(e)  # 'SlottedClass' object has no attribute 'z'

# No __dict__ unless explicitly added
print(hasattr(obj, '__dict__'))  # False
```

---

## `__getattr__` and `__getattribute__`

```python
class DynamicObject:
    """Falls back to a default for missing attributes."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            object.__setattr__(self, k, v)
    
    def __getattr__(self, name):
        """Called ONLY when normal attribute lookup fails."""
        return f"'{name}' not found, returning default"

obj = DynamicObject(x=10, y=20)
print(obj.x)      # 10 — normal lookup
print(obj.z)       # "'z' not found, returning default" — __getattr__

class LoggingObject:
    """Logs ALL attribute access."""
    def __init__(self, value):
        self._value = value
    
    def __getattribute__(self, name):
        """Called for EVERY attribute access (even existing ones).
        WARNING: Be careful not to cause infinite recursion!"""
        print(f"Accessing: {name}")
        return object.__getattribute__(self, name)

obj = LoggingObject(42)
print(obj._value)  # Logs "Accessing: _value", then prints 42
```

---

## Data Classes — Modern Dunder Method Shortcut

```python
from dataclasses import dataclass, field

@dataclass
class Product:
    name: str
    price: float
    quantity: int = 0
    tags: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Called after __init__ — for validation."""
        if self.price < 0:
            raise ValueError("Price cannot be negative")

# Auto-generates: __init__, __repr__, __eq__, __hash__ (if frozen)
p1 = Product("Apple", 1.50, 100)
p2 = Product("Apple", 1.50, 100)
print(p1)           # Product(name='Apple', price=1.5, quantity=100, tags=[])
print(p1 == p2)     # True — auto-generated __eq__

# Frozen dataclass — immutable
@dataclass(frozen=True)
class ImmutablePoint:
    x: int
    y: int

pt = ImmutablePoint(1, 2)
# pt.x = 3  # FrozenInstanceError — can't modify

# Can be used in sets and as dict keys (hashable)
s = {ImmutablePoint(1, 2), ImmutablePoint(3, 4)}
```

---

## Common Mistakes

1. **Defining `__eq__` without `__hash__`** — Makes object unhashable (can't use in sets/dicts).
2. **Returning wrong type from `__iadd__`** — Must return `self`, not a new object.
3. **Infinite recursion in `__getattribute__`** — Use `object.__getattribute__()` to avoid.
4. **Forgetting `__enter__` return value** — `with obj as x` assigns whatever `__enter__` returns to `x`.
5. **Using `__del__` for cleanup** — Use context managers instead; `__del__` has no guaranteed timing.
6. **Not implementing `__repr__`** — Default repr is useless for debugging.

```python
# WRONG — __eq__ without __hash__
class Bad:
    def __init__(self, x):
        self.x = x
    def __eq__(self, other):
        return self.x == other.x

b = Bad(1)
# {b}  # TypeError: unhashable type: 'Bad'

# RIGHT — define both
class Good:
    def __init__(self, x):
        self.x = x
    def __eq__(self, other):
        return isinstance(other, Good) and self.x == other.x
    def __hash__(self):
        return hash(self.x)

g = Good(1)
print({g})  # Works!
```

---

## Summary Table

| Dunder Method | Called By | Purpose |
|---|---|---|
| `__repr__` | `repr()`, interactive shell | Developer-facing representation |
| `__str__` | `str()`, `print()` | User-facing string |
| `__len__` | `len()` | Container size |
| `__bool__` | `bool()`, truthiness | Truth value |
| `__getitem__` | `obj[key]` | Index/key access |
| `__setitem__` | `obj[key] = val` | Index/key assignment |
| `__contains__` | `x in obj` | Membership test |
| `__iter__` | `for x in obj` | Get iterator |
| `__next__` | `next()` | Get next item |
| `__add__` | `a + b` | Addition |
| `__call__` | `obj()` | Make instance callable |
| `__enter__`/`__exit__` | `with obj` | Context manager |
| `__get__`/`__set__` | Attribute access | Descriptor protocol |
| `__getattr__` | Missing attribute | Fallback attribute access |
| `__getattribute__` | Any attribute | Intercept all access |
| `__slots__` | Class definition | Prevent __dict__, save memory |
