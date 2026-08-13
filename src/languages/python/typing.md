# Type Hints and Static Typing in Python

## Overview

Python is **dynamically typed** — variables have no declared types and type errors are caught at runtime. **Type hints** (PEP 484, Python 3.5+) add optional static annotations that tools like **mypy**, **pyright**, and **pytype** can check without affecting runtime behavior.

```python
# Without type hints — what types are expected?
def process(data, limit):
    return [item for item in data if item > limit]

# With type hints — self-documenting
def process(data: list[int], limit: int) -> list[int]:
    return [item for item in data if item > limit]
```

> **Key insight:** Type hints are **ignored at runtime** by CPython. They're purely for tooling and documentation.

---

## Basic Type Hints

```python
# Variable annotations
name: str = "Alice"
age: int = 25
height: float = 5.9
is_active: bool = True

# Function annotations
def greet(name: str) -> str:
    return f"Hello, {name}"

# Return type None
def log(message: str) -> None:
    print(message)

# Multiple return types (use Union)
from typing import Union

def parse(input_str: str) -> Union[int, float]:
    try:
        return int(input_str)
    except ValueError:
        return float(input_str)

# Python 3.10+ — use | instead of Union
def parse_modern(input_str: str) -> int | float:
    try:
        return int(input_str)
    except ValueError:
        return float(input_str)
```

---

## Collection Types

```python
from typing import List, Dict, Tuple, Set, Optional

# Python 3.9+ — use built-in types directly
def process(
    items: list[int],
    mapping: dict[str, int],
    coordinates: tuple[int, int],
    unique: set[str],
) -> list[str]:
    return [str(item) for item in items]

# Python 3.5-3.8 — use typing module
def process_old(
    items: List[int],
    mapping: Dict[str, int],
    coordinates: Tuple[int, int],
    unique: Set[str],
) -> List[str]:
    return [str(item) for item in items]

# Nested types
matrix: list[list[int]] = [[1, 2], [3, 4]]
nested_dict: dict[str, list[int]] = {"a": [1, 2], "b": [3, 4]}

# Optional — value can be None
def find_user(user_id: int) -> Optional[str]:  # str | None
    if user_id == 1:
        return "Alice"
    return None

# Python 3.10+ syntax
def find_user_modern(user_id: int) -> str | None:
    if user_id == 1:
        return "Alice"
    return None
```

---

## TypeVar — Generics

`TypeVar` lets you write functions that work with any type while preserving type relationships:

```python
from typing import TypeVar

T = TypeVar('T')

def first(items: list[T]) -> T:
    """Returns first element — preserves type."""
    return items[0]

# Usage — type checker knows the return type
x: int = first([1, 2, 3])       # T = int
y: str = first(["a", "b", "c"])  # T = str

# Bounded TypeVar — restrict to subtypes
Numeric = TypeVar('Numeric', int, float)

def add(a: Numeric, b: Numeric) -> Numeric:
    return a + b

add(1, 2)       # OK — int
add(1.5, 2.5)   # OK — float
# add("a", "b")  # Error — str not in bound

# Constrained TypeVar
AnyStr = TypeVar('AnyStr', str, bytes)

def concat(a: AnyStr, b: AnyStr) -> AnyStr:
    return a + b

concat("a", "b")     # OK
concat(b"a", b"b")   # OK
# concat("a", b"b")  # Error — mixing str and bytes
```

---

## Protocol — Structural Subtyping

`Protocol` (PEP 544) defines interfaces by **structure** (what methods/attributes an object has) rather than inheritance:

```python
from typing import Protocol, runtime_checkable

class Drawable(Protocol):
    def draw(self) -> str: ...

class Circle:
    def draw(self) -> str:
        return "Drawing circle"

class Square:
    def draw(self) -> str:
        return "Drawing square"

class Triangle:
    def paint(self) -> str:  # Different method name — NOT compatible
        return "Drawing triangle"

def render(shape: Drawable) -> str:
    return shape.draw()

render(Circle())    # OK — Circle has draw()
render(Square())    # OK — Square has draw()
# render(Triangle())  # Error — Triangle has no draw()

# runtime_checkable — allows isinstance checks
@runtime_checkable
class Closeable(Protocol):
    def close(self) -> None: ...

import io
f = io.StringIO()
print(isinstance(f, Closeable))  # True — StringIO has close()
```

### Protocol with Attributes

```python
from typing import Protocol

class HasName(Protocol):
    name: str
    age: int

class Person:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

class Dog:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age
        self.breed = "Unknown"

def greet(entity: HasName) -> str:
    return f"Hello, {entity.name}! You are {entity.age}."

greet(Person("Alice", 30))  # OK
greet(Dog("Rex", 5))        # OK — has name and age attributes
```

---

## Literal Types

`Literal` restricts values to specific constants:

```python
from typing import Literal

def set_direction(direction: Literal["north", "south", "east", "west"]) -> None:
    print(f"Going {direction}")

set_direction("north")   # OK
set_direction("up")      # Error — not a valid literal

# Literal with integers
def set_level(level: Literal[0, 1, 2, 3]) -> None:
    print(f"Level: {level}")

# Practical use — API endpoints
def request(method: Literal["GET", "POST", "PUT", "DELETE"], url: str) -> None:
    pass

request("GET", "/api/users")     # OK
request("PATCH", "/api/users")   # Error
```

---

## TypedDict — Typed Dictionaries

`TypedDict` defines dictionaries with specific key-value types:

```python
from typing import TypedDict

class UserDict(TypedDict):
    name: str
    age: int
    email: str

# Creating instances
user: UserDict = {
    "name": "Alice",
    "age": 30,
    "email": "alice@example.com",
}

# Type checker catches errors
bad_user: UserDict = {
    "name": "Bob",
    "age": "thirty",  # Error — should be int
    "email": "bob@example.com",
}

# Optional keys (Python 3.11+)
from typing import TypedDict, NotRequired

class PartialUser(TypedDict):
    name: str
    age: int
    email: NotRequired[str]  # Optional key

# Python 3.9-3.10 — use total=False
class PartialUserOld(TypedDict, total=False):
    name: str
    age: int
    email: str

# Or mix required and optional
class UserWithOptional(TypedDict, total=False):
    name: str  # Required (overridden below)
    age: int
    email: str

class RequiredUser(UserWithOptional, total=True):
    name: str  # This one is required
```

---

## Callable Types

```python
from typing import Callable

# Function that takes a callback
def apply(func: Callable[[int, int], int], a: int, b: int) -> int:
    return func(a, b)

apply(lambda x, y: x + y, 1, 2)  # 3

# Callback with no return
def on_complete(callback: Callable[[str], None], message: str) -> None:
    callback(message)

# Complex callable
from typing import Callable, Awaitable

AsyncHandler = Callable[[str, int], Awaitable[bool]]

async def process(handler: AsyncHandler) -> None:
    result = await handler("data", 42)
    print(f"Result: {result}")
```

---

## Type Aliases and NewType

```python
from typing import TypeAlias, NewType

# Type Alias — just a shorthand
Vector: TypeAlias = list[float]
Matrix: TypeAlias = list[Vector]

def dot_product(a: Vector, b: Vector) -> float:
    return sum(x * y for x, y in zip(a, b))

# NewType — creates a distinct type (for type checker only)
UserId = NewType("UserId", int)
OrderId = NewType("OrderId", int)

def get_user(user_id: UserId) -> str:
    return f"User {user_id}"

get_user(UserId(42))      # OK
# get_user(42)            # Error — int is not UserId
# get_user(OrderId(42))   # Error — OrderId is not UserId

# At runtime, NewType is just the identity function
print(UserId(42))  # 42 (just an int)
```

---

## Type Guards

```python
from typing import TypeGuard

def is_string_list(val: list[object]) -> TypeGuard[list[str]]:
    """Type guard — narrows type if returns True."""
    return all(isinstance(x, str) for x in val)

def process(items: list[object]) -> None:
    if is_string_list(items):
        # Type checker knows items is list[str] here
        print(", ".join(items))
    else:
        # items is still list[object]
        print(items)
```

---

## mypy — Static Type Checker

```bash
# Install
pip install mypy

# Run type checking
mypy script.py

# Strict mode
mypy --strict script.py

# Check entire project
mypy src/

# Configuration in pyproject.toml
# [tool.mypy]
# strict = true
# warn_return_any = true
# warn_unused_configs = true
```

### mypy Configuration

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

# Per-module overrides
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

### Runtime vs Static Typing

| Aspect | Runtime | Static (mypy/pyright) |
|---|---|---|
| When checked | Execution time | Before running code |
| Performance | Overhead if using `beartype` | No runtime cost |
| Coverage | Only executed paths | All code paths |
| Tools | `beartype`, `typeguard` | `mypy`, `pyright`, `pytype` |
| Recommendation | Use for validation | Use for development |

```python
# Runtime type checking (optional, adds overhead)
from beartype import beartype

@beartype
def greet(name: str) -> str:
    return f"Hello, {name}"

greet("Alice")   # OK
greet(42)        # Runtime error: int is not str
```

---

## Common Mistakes

1. **Using `list` instead of `List` in older Python** — `list[int]` works in 3.9+, use `List[int]` for 3.7-3.8.
2. **Forgetting `Optional` for nullable types** — `def f(x: int)` means x can't be None. Use `Optional[int]` or `int | None`.
3. **Type hints don't enforce types** — `def f(x: int)` doesn't prevent `f("hello")` at runtime.
4. **Using `Any` too much** — `Any` disables type checking. Use `object` if you want maximum flexibility but still have checks.
5. **Not using `TypeVar` for generics** — `def first(items: list) -> ???` loses type info. Use `def first(items: list[T]) -> T`.
6. **Mixing `isinstance` with Protocol** — Use `@runtime_checkable` for `isinstance` checks with Protocol.

```python
# WRONG — loses type information
def first(items: list) -> object:
    return items[0]

# RIGHT — preserves type with TypeVar
from typing import TypeVar
T = TypeVar('T')

def first(items: list[T]) -> T:
    return items[0]

# WRONG — Optional not specified
def find(name: str) -> str:
    if name == "alice":
        return "Alice"
    return None  # mypy error!

# RIGHT
from typing import Optional
def find(name: str) -> Optional[str]:
    if name == "alice":
        return "Alice"
    return None
```

---

## Summary Table

| Feature | Syntax | Purpose |
|---|---|---|
| Basic hints | `x: int = 5` | Annotate variables and functions |
| Union | `int \| str` or `Union[int, str]` | Multiple possible types |
| Optional | `str \| None` or `Optional[str]` | Nullable values |
| TypeVar | `T = TypeVar('T')` | Generic type parameters |
| Protocol | `class Drawable(Protocol)` | Structural subtyping |
| Literal | `Literal["a", "b"]` | Restrict to specific values |
| TypedDict | `class User(TypedDict)` | Typed dictionaries |
| Callable | `Callable[[int], str]` | Function type signatures |
| NewType | `UserId = NewType("UserId", int)` | Distinct types |
| TypeGuard | `TypeGuard[list[str]]` | Type narrowing |
| TypeAlias | `Vector: TypeAlias = list[float]` | Type shorthand |
