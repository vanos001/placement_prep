# Python Decorators and Metaclasses

## Overview

Python's object model is unusually exposed. The same machinery that builds a class — calling `type(name, bases, namespace)` — is available to user code, and every callable that takes a callable and returns a callable behaves as a decorator. This gives the language two powerful code-generation mechanisms:

- **Decorators** transform a function or class at definition time.
- **Metaclasses** customize the class creation process itself.

Mastering both is a hard requirement for understanding how `dataclass`, `abc.ABC`, `attrs`, ORM declarative models, and `pydantic` work under the hood.

## Function decorators

A decorator is just a callable that takes a function and returns a function (or any callable). The `@decorator` syntax is sugar for an assignment after the function definition:

```python
def log_calls(func):
    def wrapper(*args, **kwargs):
        print(f"calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log_calls
def greet(name):
    return f"hello {name}"

# equivalent to: greet = log_calls(greet)
```

`greet` is now `wrapper`, a closure that captures `func`. The original `greet` function object survives only inside that closure.

## `functools.wraps` — preserving metadata

Without care, `greet.__name__` becomes `"wrapper"`, `help(greet)` shows the wrapper's docstring, and `inspect.signature` reports the wrong signature. `functools.wraps` copies over the dunder attributes from the wrapped function:

```python
import functools

def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper
```

`functools.wraps` is itself a decorator that updates `__name__`, `__qualname__`, `__module__`, `__doc__`, `__dict__`, and `__wrapped__`. The latter is what `inspect.signature` walks to find the real signature.

## Decorators with arguments

A decorator factory is a function that *returns* a decorator. The decorator takes one fewer argument than you'd expect — the function being decorated — while the outer factory takes the user-supplied arguments.

```python
import functools

def repeat(times):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            for _ in range(times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(times=3)
def say_hi():
    print("hi")
```

The call graph is `repeat(3)` → `decorator(say_hi)` → `wrapper`. The three-level nesting is unavoidable when the user can supply arguments; the decorator factory is the only layer that has access to `times`, and the innermost wrapper is the only layer that has access to the function's arguments at call time.

## Class decorators

A class decorator receives the class and returns a class (or anything else — but typically the same class, mutated):

```python
def add_repr(cls):
    def __repr__(self):
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{cls.__name__}({attrs})"
    cls.__repr__ = __repr__
    return cls

@add_repr
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

Point(1, 2)        # Point(x=1, y=2)
```

Class decorators run *after* `type()` has constructed the class. They see the fully formed namespace.

## Stacking decorators

Decorators apply bottom-up:

```python
@dec_a
@dec_b
@dec_c
def f(): ...

# equivalent to: f = dec_a(dec_b(dec_c(f)))
```

So `dec_c` runs first, then `dec_b`, then `dec_a` — but each call wraps the result of the previous. The *outermost* decorator's wrapper runs first at call time.

## The class creation process

To understand metaclasses, you must understand how `class Foo(Base): ...` is executed. In CPython:

```
+-----------------------------+
|  source: class Foo(Base):  |   1. determine metaclass
|      x = 1                  |   2. evaluate base expressions
|      def f(self): ...       |   3. __prepare__ -> ns
+-----------------------------+   4. execute body in ns
              |                          |
              |                          v
              |              +--------------------------+
              |              |  namespace ns (a dict)  |
              |              +--------------------------+
              |                          |
              v                          v
       +------------------------------------------+
       |  metaclass(name, bases, ns)              |
       |   -> type.__call__(metaclass, ...)       |
       |       -> __new__(mcs, name, bases, ns)   |
       |       -> __init__(cls, name, bases, ns)  |
       +------------------------------------------+
                          |
                          v
                +--------------------+
                |  new class object  |
                +--------------------+
```

Concretely:

1. Python determines the metaclass: explicit `metaclass=` kwarg, else the most-derived type of all bases (a.k.a. the *metaclass conflict* rule), else `type`.
2. Python evaluates the body in a fresh namespace (a `dict`-like; see PEP 3115 for `__prepare__`).
3. The body's assignments populate that namespace.
4. Python calls `metaclass(name, bases, ns, **kwargs)`. By the descriptor protocol this dispatches to `type.__call__(metaclass, ...)`, which calls `metaclass.__new__(metaclass, name, bases, ns)` and then `metaclass.__init__(cls, name, bases, ns)`.

## `__new__`, `__init__`, `__call__` on a metaclass

A metaclass is a subclass of `type`:

```python
class Meta(type):
    def __new__(mcs, name, bases, ns, **kwargs):
        print(f"creating {name}")
        return super().__new__(mcs, name, bases, ns, **kwargs)

    def __init__(cls, name, bases, ns, **kwargs):
        print(f"initializing {name}")
        super().__init__(name, bases, ns, **kwargs)

    def __call__(cls, *args, **kwargs):
        print(f"calling {cls.__name__}(...)")
        return super().__call__(*args, **kwargs)

class Thing(metaclass=Meta):
    def __init__(self, v):
        self.v = v

t = Thing(42)
# prints: creating Thing
#         initializing Thing
#         calling Thing(...)
```

The order matters: `__new__` must return the class object, then `__init__` runs. `__call__` is invoked when instances of the class are constructed (because `Thing(x)` calls `Meta.__call__(Thing, x)`, since `Thing` is an instance of `Meta`).

This is the same split as for ordinary classes — but at the *class-of-class* level. Hence a metaclass can intercept the construction of *every instance* of its classes, which is the technique `__init_subclass__` builds on.

## `__prepare__` — customizing the class namespace

`__prepare__` returns the mapping that the body executes in. `enum.Enum` uses it to make the namespace *ordered and non-rebinding*, so you cannot accidentally redefine a member:

```python
class OrderedNamespace(type):
    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        return {}  # could be collections.OrderedDict or a custom type
```

The default `dict` in CPython is insertion-ordered, so `__prepare__` is rarely needed now — but `enum` still uses a custom `_EnumDict` to enforce invariants, and ORMs sometimes use it to track field declaration order.

## `ABCMeta` — abstract base classes

`abc.ABCMeta` is a metaclass that overrides `__new__` to scan the namespace for `@abstractmethod`-decorated callables and record them on the class. `ABCMeta` also implements `register()` for virtual subclasses (so `list` is registered as `Sequence` even without inheritance):

```python
from abc import ABCMeta, abstractmethod

class Animal(metaclass=ABCMeta):
    @abstractmethod
    def sound(self): ...

class Dog(Animal):
    def sound(self):
        return "woof"

# Animal()  -> TypeError: abstract class
Dog().sound()  # "woof"
```

`@abstractmethod` sets `__isabstractmethod__ = True`; `ABCMeta.__new__` collects any such attribute into `__abstractmethods__` (a `frozenset`). Instantiation fails until the set is empty.

## `dataclasses` (PEP 557)

`@dataclass` is a class decorator that introspects `cls.__annotations__` and synthesizes `__init__`, `__repr__`, `__eq__` (and optionally `__hash__`, `__lt__`, etc.). It does *not* use a metaclass — class decorators are sufficient because they can mutate the namespace after construction.

```python
from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int = 0
    tags: list[str] = field(default_factory=list)
```

`frozen=True` overrides `__setattr__` and `__hash__`; `slots=True` (3.10+) generates a `__slots__` and rebuilds the class. The decorator's only input is the class object — annotations are read from `__annotations__`, defaults from class attributes.

## `__init_subclass__` — the lightweight metaclass

For most "do something on subclass creation" use cases, a full metaclass is overkill. PEP 487 introduced `__init_subclass__`, a hook called on every subclass creation, which is enough for plugin registration, validation, etc., without the complexity of a metaclass:

```python
class Plugin:
    registry = []

    def __init_subclass__(cls, name=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if name is None:
            raise TypeError("subclasses must pass name=")
        cls.name = name
        Plugin.registry.append(cls)

class Foo(Plugin, name="foo"):
    pass

# Foo.name == "foo", Plugin.registry == [Foo]
```

Keyword arguments to the `class` statement (`class Foo(Plugin, name="foo")`) become kwargs to `__init_subclass__`. This is far more composable than metaclasses: two unrelated libraries can both use `__init_subclass__` without conflicts, whereas two metaclasses that don't cooperate cause a *metaclass conflict* (TypeError at class creation).

## Metaclass conflict

If two base classes have incompatible metaclasses, class creation fails:

```python
class A(metaclass=MetaA): ...
class B(metaclass=MetaB): ...

class C(A, B): ...  # TypeError: metaclass conflict
```

The resolution rule is: the metaclass of `C` must be a subclass of the metaclasses of *all* bases. The fix is to write a third metaclass that subclasses both `MetaA` and `MetaB` and pass it explicitly via `metaclass=`.

## When to use what

- **Function decorator** — to wrap, log, cache, validate, register.
- **Class decorator** — to add methods, invariants, or wrap a class. Use over a metaclass when you only need post-construction tweaks.
- **`__init_subclass__`** — to react to subclassing. Use over a metaclass whenever you don't actually need to control instantiation or namespace preparation.
- **Metaclass** — when you must intercept `__call__` (instance creation), `__new__` (class creation), or `__prepare__` (namespace type). Examples: ORMs (`declarative_base`), `ABCMeta`, plugin frameworks that enforce interface contracts.

The dominant rule: prefer the simplest mechanism that solves the problem. Metaclasses are *contagious* — once one base uses a metaclass, subclasses must agree — and that cost is often invisible at first.

## Common pitfalls

1. **Forgetting `functools.wraps`** — breaks `help()`, pickling, and debugging.
2. **Returning `None` from a decorator** — silently removes the function. Always return something callable.
3. **Decorator with arguments called without them** — `@repeat` (no parens) passes the function as `times`, which then fails at call time. To accept both forms, detect `callable(times)` and switch behavior.
4. **Overwriting `__abstractmethods__` incorrectly** — manual fiddling breaks `ABCMeta`'s checks; let the decorator do it.
5. **Metaclass conflicts in mixins** — abstract the metaclass out, or use `__init_subclass__` instead.
6. **Mutating `__annotations__` instead of defaults** — `dataclass` reads defaults from the *class attribute*, not the annotation.

## Interview questions

1. **What is a decorator?**
   Any callable that takes a callable and returns a callable. `@dec def f` desugars to `f = dec(f)`.

2. **Why use `functools.wraps`?**
   It copies `__name__`, `__doc__`, `__wrapped__`, etc. from the wrapped function so that `help()`, `inspect`, and pickling continue to work.

3. **How does class creation work?**
   Python computes the metaclass, calls `__prepare__` to get a namespace, executes the body in it, then calls `metaclass(name, bases, ns)` which dispatches through `type.__call__` to `__new__` and `__init__`.

4. **What's the difference between `__new__` and `__init__` on a metaclass?**
   `__new__` builds and returns the class object; `__init__` then configures it. Both run during class creation, in that order.

5. **Why prefer `__init_subclass__` over a metaclass?**
   It's lighter, doesn't cause metaclass conflicts, and works without needing every base to agree on a metaclass.

## References

- [PEP 318 — Decorators for Functions and Methods](https://peps.python.org/pep-0318/)
- [PEP 3129 — Class Decorators](https://peps.python.org/pep-3129/)
- [PEP 3115 — Metaclasses in Python 3000 (`__prepare__`)](https://peps.python.org/pep-3115/)
- [PEP 487 — `__init_subclass__` and `__set_name__`](https://peps.python.org/pep-0487/)
- [PEP 557 — Dataclasses](https://peps.python.org/pep-0557/)
- [Python Data Model — Special method names](https://docs.python.org/3/reference/datamodel.html)
- [Python Reference — Customizing class creation](https://docs.python.org/3/reference/datamodel.html#customizing-class-creation)
- [Python `functools.wraps` documentation](https://docs.python.org/3/library/functools.html#functools.wraps)
- [Python `abc` module documentation](https://docs.python.org/3/library/abc.html)
- [Luciano Ramalho — *Fluent Python*, 2nd edition](https://www.oreilly.com/library/view/fluent-python-2nd/9781492056348/)

## See also

- [Data Model](./data-model.md) — `__init_subclass__` is part of the data model
- [Typing](./typing.md) — `@overload` and `@final` are decorators
- [Cpython Internals](./cpython-internals.md) — how `type.__call__` is dispatched
