# Python Interview Questions

## Fundamentals

### Q1: What are Python's key features?

- Interpreted, dynamically typed
- First-class functions and closures
- List comprehensions, generators
- Duck typing ("if it walks like a duck...")
- Automatic memory management (reference counting + GC)
- Extensive standard library ("batteries included")

### Q2: Mutable vs immutable types?

| Mutable | Immutable |
|---------|-----------|
| list, dict, set, bytearray | int, float, str, tuple, frozenset, bytes |
| Can change in place | Creates new object on change |

```python
s = "hello"
s += " world"  # New string object created

lst = [1, 2]
lst.append(3)  # Same list object modified
```

### Q3: What is the GIL?

The Global Interpreter Lock. It allows only one thread to execute Python bytecode at a time. This simplifies memory management but limits CPU-bound parallelism.

**Workarounds:**
- `multiprocessing` (separate processes)
- `asyncio` (I/O-bound concurrency)
- C extensions that release the GIL (NumPy, etc.)
- Python 3.13+ free-threaded build (experimental)

### Q4: Shallow vs deep copy?

```python
import copy

original = [[1, 2], [3, 4]]
shallow = copy.copy(original)      # New outer list, same inner lists
deep = copy.deepcopy(original)     # Completely independent

original[0][0] = 99
print(shallow[0][0])  # 99 (affected)
print(deep[0][0])     # 1 (unaffected)
```

### Q5: What are *args and **kwargs?

```python
def func(*args, **kwargs):
    print(args)    # tuple of positional args
    print(kwargs)  # dict of keyword args

func(1, 2, x=3, y=4)
# (1, 2)
# {'x': 3, 'y': 4}
```

## Data Model

### Q6: What are dunder methods?

Special methods with double underscores that define object behavior.

```python
class Vector:
    def __init__(self, x, y):
        self.x, self.y = x, y
    
    def __add__(self, other):           # v1 + v2
        return Vector(self.x + other.x, self.y + other.y)
    
    def __len__(self):                  # len(v)
        return 2
    
    def __repr__(self):                 # repr(v)
        return f"Vector({self.x}, {self.y})"
    
    def __getitem__(self, index):       # v[0], v[1]
        return (self.x, self.y)[index]
    
    def __eq__(self, other):            # v1 == v2
        return self.x == other.x and self.y == other.y
```

### Q7: What are descriptors?

Objects that define `__get__`, `__set__`, or `__delete__`. They control attribute access.

```python
class Property:
    def __init__(self, fget, fset=None):
        self.fget = fget
        self.fset = fset
    
    def __get__(self, obj, objtype=None):
        return self.fget(obj)
    
    def __set__(self, obj, value):
        if self.fset:
            self.fset(obj, value)

class Circle:
    def __init__(self, radius):
        self._radius = radius
    
    @Property
    def radius(self):
        return self._radius
    
    @radius.setter
    def radius(self, value):
        if value < 0: raise ValueError("Negative radius")
        self._radius = value
```

### Q8: Context managers?

```python
class FileManager:
    def __init__(self, filename, mode):
        self.filename, self.mode = filename, mode
    
    def __enter__(self):
        self.file = open(self.filename, self.mode)
        return self.file
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()
        return False  # Don't suppress exceptions

# Or use contextlib
from contextlib import contextmanager

@contextmanager
def managed_resource():
    resource = acquire()
    try:
        yield resource
    finally:
        release(resource)
```

## Generators and Iterators

### Q9: Generators vs iterators?

```python
# Iterator: implements __iter__ and __next__
class CountDown:
    def __init__(self, n):
        self.n = n
    def __iter__(self):
        return self
    def __next__(self):
        if self.n <= 0: raise StopIteration
        self.n -= 1
        return self.n + 1

# Generator: simpler syntax
def countdown(n):
    while n > 0:
        yield n
        n -= 1

# Generator expression
squares = (x**2 for x in range(10))  # Lazy, memory efficient
```

### Q10: send() and throw() on generators?

```python
def accumulator():
    total = 0
    while True:
        value = yield total
        if value is None:
            break
        total += value

gen = accumulator()
next(gen)           # Prime the generator (advance to first yield)
gen.send(10)        # 10
gen.send(20)        # 30
gen.throw(ValueError)  # Raises ValueError inside generator
```

## Async

### Q11: asyncio vs threading vs multiprocessing?

| asyncio | threading | multiprocessing |
|---------|-----------|-----------------|
| Single thread, cooperative | Multiple threads, preemptive | Multiple processes |
| I/O-bound | I/O-bound (with GIL limitation) | CPU-bound |
| No race conditions | Race conditions possible | Separate memory |
| Lowest overhead | Moderate overhead | Highest overhead |

```python
import asyncio

async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.text()

async def main():
    results = await asyncio.gather(
        fetch("http://a.com"),
        fetch("http://b.com"),
    )

asyncio.run(main())
```

### Q12: TaskGroup (Python 3.11+)?

```python
async def main():
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(fetch("http://a.com"))
        task2 = tg.create_task(fetch("http://b.com"))
    # All tasks complete when exiting the context
    # Exceptions are grouped (ExceptionGroup)
```

## Typing

### Q13: Type hints — typing.Protocol?

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Drawable(Protocol):
    def draw(self) -> None: ...

class Circle:
    def draw(self) -> None:
        print("drawing circle")

def render(item: Drawable) -> None:
    item.draw()

render(Circle())  # OK: Circle satisfies Drawable (structural subtyping)
```

### Q14: Generic types?

```python
from typing import TypeVar, Generic

T = TypeVar('T')

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []
    def push(self, item: T) -> None:
        self._items.append(item)
    def pop(self) -> T:
        return self._items.pop()

int_stack: Stack[int] = Stack()
int_stack.push(42)
```

### Q15: TypedDict, Literal, Final?

```python
from typing import TypedDict, Literal, Final

class UserDict(TypedDict):
    name: str
    age: int

Direction = Literal["north", "south", "east", "west"]

MAX_RETRIES: Final = 3  # Cannot be reassigned
```

## Metaclasses

### Q16: What is a metaclass?

A class whose instances are classes. `type` is the default metaclass.

```python
# Class creation: type(name, bases, namespace)
MyClass = type('MyClass', (Base,), {'x': 42})

# Custom metaclass
class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Database(metaclass=SingletonMeta):
    pass

db1 = Database()
db2 = Database()
assert db1 is db2  # Same instance
```

## Performance

### Q17: __slots__?

```python
class Point:
    __slots__ = ('x', 'y')  # Restricts attributes, saves memory
    def __init__(self, x, y):
        self.x = x
        self.y = y

# Without __slots__: ~152 bytes per instance (dict)
# With __slots__: ~56 bytes per instance (no dict)
```

### Q18: How to profile Python?

```python
import cProfile
cProfile.run('my_function()')

# Line-by-line
# pip install line_profiler
@profile
def my_function(): ...

# Memory
# pip install memory_profiler
@profile
def my_function(): ...
```

### Q19: How to optimize Python?

1. Use built-in functions and libraries (C-implemented)
2. List comprehensions over loops
3. Generators for large sequences
4. `__slots__` for many small objects
5. `collections.defaultdict`, `collections.Counter`
6. C extensions for hot paths (ctypes, cffi, Cython)
7. Numba for numerical code
8. `functools.lru_cache` for memoization

## Common Gotchas

### Q20: Late binding closures?

```python
# Problem
funcs = [lambda: i for i in range(5)]
print([f() for f in f])  # [4, 4, 4, 4, 4] — not [0, 1, 2, 3, 4]!

# Fix: capture the value
funcs = [lambda i=i: i for i in range(5)]
print([f() for f in funcs])  # [0, 1, 2, 3, 4]
```

### Q21: Mutable default arguments?

```python
# Problem
def append_to(item, lst=[]):
    lst.append(item)
    return lst

append_to(1)  # [1]
append_to(2)  # [1, 2] — same list!

# Fix
def append_to(item, lst=None):
    if lst is None:
        lst = []
    lst.append(item)
    return lst
```

### Q22: Class variable vs instance variable?

```python
class Dog:
    tricks = []  # Class variable (shared by all instances)
    
    def __init__(self, name):
        self.name = name  # Instance variable (unique per instance)
    
    def learn(self, trick):
        self.tricks.append(trick)  # BUG: modifies class variable!

# Fix
def learn(self, trick):
    if not hasattr(self, 'tricks'):
        self.tricks = []
    self.tricks.append(trick)
```

### Q23: Exception handling?

```python
try:
    risky_operation()
except (ValueError, TypeError) as e:
    handle_error(e)
except Exception as e:
    logger.exception("Unexpected error")
    raise  # Re-raise after logging
else:
    log_success()  # Only if no exception
finally:
    cleanup()  # Always runs
```

### Q24: Decorators?

```python
def retry(max_attempts=3):
    def decorator(func):
        @functools.wraps(func)  # Preserves function metadata
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(2 ** attempt)
        return wrapper
    return decorator

@retry(max_attempts=3)
def fetch_data(): ...
```

### Q25: f-strings vs .format() vs %?

```python
name, age = "Alice", 30

# f-strings (fastest, most readable — use these)
f"{name} is {age} years old"

# .format() (flexible)
"{name} is {age} years old".format(name=name, age=age)

# % (old style, avoid)
"%s is %d years old" % (name, age)
```

### Q26: collections module?

```python
from collections import defaultdict, Counter, deque, namedtuple, OrderedDict

dd = defaultdict(list)    # Auto-creates missing keys
dd['key'].append(1)

counter = Counter("hello") # {'l': 2, 'h': 1, 'e': 1, 'o': 1}
counter.most_common(2)

dq = deque(maxlen=10)     # O(1) append/pop from both ends
dq.appendleft(1)

Point = namedtuple('Point', ['x', 'y'])  # Immutable, lightweight
```

### Q27: What is the MRO?

Method Resolution Order. Python uses C3 linearization to determine the order in which base classes are searched.

```python
class A: pass
class B(A): pass
class C(A): pass
class D(B, C): pass

print(D.__mro__)  # D -> B -> C -> A -> object
```

### Q28: `is` vs `==`?

```python
# is: identity (same object in memory)
# ==: equality (same value)

a = [1, 2, 3]
b = [1, 2, 3]
a == b  # True (same values)
a is b  # False (different objects)

# Small integers and strings are cached
a = 256
b = 256
a is b  # True (cached)
```

### Q29: Walrus operator (:=)?

```python
# Python 3.8+: assign and use in expression
if (n := len(data)) > 10:
    print(f"Too long: {n}")

while (chunk := f.read(8192)):
    process(chunk)
```

### Q30: Structural pattern matching (Python 3.10+)?

```python
match command:
    case {"action": "move", "direction": d, "steps": n}:
        move(d, n)
    case {"action": "attack", "target": t}:
        attack(t)
    case _:
        print("Unknown command")
```

## Related Topics

- [CPython Internals](./cpython-internals.md) — How Python works under the hood
- [GIL](./gil.md) — Global Interpreter Lock
- [AsyncIO](./asyncio.md) — Async programming
- [Performance](./performance.md) — Optimization techniques
