# Python Data Model and Metaclasses Deep Dive

This is the *mechanism* view of the Python data model: how `__new__`
interacts with `__init__`, the difference between `__getattr__` and
`__getattribute__`, the C3 linearization that produces the MRO, the
descriptor protocol that powers `property`/`classmethod`/`staticmethod`,
the `__init_subclass__` hook that displaced many metaclasses, `ABCMeta`
and `@dataclass`. The sibling page [data-model](./data-model.md) is the
API tour; this page is the C-level *how*. There is a brief comparison
with Ruby's object model at the end.

## 1. Object Construction — `__new__` vs `__init__`

When Python evaluates `MyClass(*args, **kwargs)`, the call is dispatched
through `type.__call__`, which runs (CPython source `Objects/typeobject.c`):

```c
static PyObject *
type_call(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    obj = type->tp_new(type, args, kwds);   // 1. __new__ — allocate
    if (obj != NULL && type == Py_TYPE(obj)) {
        type->tp_init(obj, args, kwds);      // 2. __init__ — initialize
    }
    return obj;
}
```

Two consequences of this code:

1. **`__init__` only runs if `__new__` returns an instance of `cls`.**
   Subclass `B` overrides `__new__` to return an instance of `A` (a
   different type), and `B.__init__` is *never called*. The check
   `type == Py_TYPE(obj)` enforces this — `__init__` belongs to the type
   that *owns the returned object*, not to the type you nominally called.

2. **Immutable types force `__new__` overrides.** `int`, `str`, `tuple`,
   `frozenset` are created *during* `__new__` (the value is locked in
   before `__init__` runs). To subclass `int` with a fixed value, you
   override `__new__`:

```python
class Octal(int):
    def __new__(cls, value: str):
        return super().__new__(cls, int(value, 8))   # value baked in here
    # no __init__ — int has none to override

assert Octal("10") == 8
```

The most-quoted real-world use of `__new__` is the singleton, but its
*legitimate* uses are (a) immutable subclasses and (b) `__init_subclass__`
registration via the metaclass — not singletons.

## 2. Attribute Access — `__getattribute__` vs `__getattr__`

The two hooks are easy to conflate. They are not symmetric:

- **`__getattribute__(self, name)`** — called on *every* attribute access,
  including reads from `__dict__`. It implements the full lookup chain
  (data descriptors → instance `__dict__` → non-data descriptors →
  `__getattr__` if defined).
- **`__getattr__(self, name)`** — called only as a *fallback* when the
  normal chain fails to find `name`.

The full lookup order, with descriptor precedence, is:

```
   obj.x
      │
      ▼
   type(obj).__getattribute__(obj, "x")
      │
      ├─ 1. Look up "x" on type(obj) and bases — is there a DATA descriptor?
      │       (has __set__ or __delete__)
      │       YES → call __get__(obj, type(obj)) ; return result
      │       NO  → continue
      │
      ├─ 2. Look in obj.__dict__['x']
      │       if present → return it
      │
      ├─ 3. Look up "x" on type(obj) and bases — is there a NON-DATA descriptor?
      │       (only __get__)
      │       YES → call __get__(obj, type(obj))
      │       NO  → return the class attribute, or fall through to __getattr__
      │
      └─ 4. type(obj).__getattr__(obj, "x")  (if defined)
              — otherwise raise AttributeError
```

The key practical implication: **only data descriptors shadow instance
`__dict__`**. A `property` is a data descriptor (it has `__set__`), so
assigning `obj.x = 5` invokes the setter — you cannot "stash" a value
into `__dict__['x']` that overrides the property. A `classmethod` is a
non-data descriptor — you *can* shadow it by setting `obj.method = ...`,
which is rarely what you want.

The classic foot-gun is overriding `__getattribute__` and recursing
forever:

```python
class Bad:
    def __getattribute__(self, name):
        return self.__dict__[name]   # infinite recursion — `self.__dict__`
                                     # itself goes through __getattribute__
```

The correct form delegates to `object.__getattribute__`:

```python
class Cached:
    def __getattribute__(self, name):
        d = object.__getattribute__(self, "__dict__")
        if name in d:
            return d[name]
        ...
```

`__getattr__` should be preferred whenever you only need a fallback — it
is dramatically cheaper (not invoked on every access) and impossible to
recurse into.

## 3. `__slots__`

`__slots__` is a class-level tuple/iterable that *disables* the per-instance
`__dict__`. The interpreter allocates fixed offsets in the instance for
each slot name; attribute access compiles to a direct pointer offset
(`_PyObject_GetSlot`) instead of a dict lookup.

```python
class Point:
    __slots__ = ("x", "y", "__dict__")   # __dict__ re-enabled here
    def __init__(self, x, y):
        self.x, self.y = x, y
```

Behavioral consequences:

- **Memory.** A `dict` costs ~104 bytes overhead + 8 bytes per entry.
  A 1-MiB instance array of objects with `__slots__` ("x","y","z") saves
  ~110 bytes per object versus a plain class — roughly 100 MiB.
- **Attribute safety.** Without `__dict__`, `obj.new_attr = 1` raises
  `AttributeError`. This catches typos at write time, not at read time.
- **Inheritance traps.** If a subclass does not declare `__slots__`, it
  gets a `__dict__` again — the savings are lost for the subclass only,
  not the parent. Empty `__slots__ = ()` on an abstract base is a common
  micro-optimization.
- **Defaults.** Slot members *cannot* have class-level defaults like
  `x = 5` — the slot name shadows any descriptor you would attach.
  Defaults must live in `__init__`.

`__slots__` interacts subtly with descriptors: a `property` stored in a
slot name behaves correctly because `property` is a data descriptor and
the slot itself is implemented as a data descriptor at the C level — the
metaclass resolves the collision at class creation time.

## 4. The MRO — C3 Linearization

Since Python 2.3 the MRO is computed by the **C3 linearization**
algorithm (the original [C3 paper][c3-paper] by Dylan developers; Python
adopted it after the "monotonic MRO" issue with the older
depth-first-left-to-right order). The algorithm:

Given a class `C(B1, B2, ..., Bn)`:

```
L[C] = C + merge(L[B1], L[B2], ..., L[Bn], [B1, B2, ..., Bn])
```

`merge` takes the head of the first list; if that head does not appear in
the tail (any non-first position) of any other list, it is appended to
the output and removed from all lists. Otherwise the next list is tried.
If no list has a head that satisfies the invariant, the algorithm raises
`TypeError: Cannot create a consistent method resolution order`.

Worked example:

```python
class A:            pass
class B(A):         pass
class C(A):         pass
class D(B, C):      pass
```

```
L[A] = [A, object]
L[B] = [B, A, object]
L[C] = [C, A, object]
L[D] = D + merge([B, A, object], [C, A, object], [B, C])
     = [D, B, C, A, object]
```

The diamond (`A` appears in both `B` and `C`) is resolved in the order
`B, C, A` — `A` is deferred until both its subclasses are visited. This
matches Python's "left-to-right, depth-first" mental model for the common
case and gives a *monotonic* order: the MRO of a subclass never
re-orders bases relative to their standalone MROs.

The pathological case:

```python
class X(B, C): pass     # X's MRO is [X, B, C, A, object]
class Y(C, B): pass     # Y's MRO is [Y, C, B, A, object]
class Z(X, Y): pass     # TypeError!
```

`merge` finds `B` in `[C, B, A, object]`'s tail (position 1), so it
cannot pick `B` from `[B, A, object]`'s head; `C` is similarly blocked.
No consistent MRO exists — and CPython raises `TypeError` *at class
creation time*, not at method call time.

## 5. The Descriptor Protocol

A descriptor is any object that defines one or more of:

```python
__get__(self, instance, owner)       # owner is the class; instance may be None
__set__(self, instance, value)
__delete__(self, instance)
__set_name__(self, owner, name)      # called once, at class creation (PEP 487)
```

Two flavors:

| Type | Defines | Precedence vs `instance.__dict__` |
|------|---------|------------------------------------|
| **Data descriptor** | `__get__` + (`__set__` or `__delete__`) | Data descriptor wins |
| **Non-data descriptor** | `__get__` only | Instance `__dict__` wins |

### 5.1 `property` — the data descriptor built into C

`property` is a C-level descriptor. Its Python-equivalent definition:

```python
class Property:
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget, self.fset, self.fdel, self.__doc__ = fget, fset, fdel, doc
        self.__set_name__(None, None)   # filled in by PEP 487

    def __get__(self, obj, owner=None):
        if obj is None: return self
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        return self.fget(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        self.fdel(obj)

    def setter(self, fset):    self.fset = fset;  return self
    def getter(self, fget):    self.fget = fget;  return self
    def deleter(self, fdel):   self.fdel = fdel; return self
```

Because `property` defines `__set__`, it is a *data* descriptor — `obj.x = 5`
always goes through `__set__`, even if you stash `5` into
`instance.__dict__['x']` via `super().__setattr__` you cannot escape the
property's setter (the property sits on the class, and class-level data
descriptors always win over instance `__dict__`).

### 5.2 `classmethod` and `staticmethod` — non-data descriptors

```python
class ClassMethod:
    def __init__(self, f):
        self.f = f
    def __get__(self, obj, owner=None):
        if owner is None:
            owner = type(obj)
        def bound(*args, **kw): return self.f(owner, *args, **kw)
        return bound

class StaticMethod:
    def __init__(self, f):
        self.f = f
    def __get__(self, obj, owner=None):
        return self.f        # unchanged — no binding
```

Both define only `__get__`. This is why you can *override* a class method
on an instance (`obj.method = lambda: ...`) — instance `__dict__` wins
because the descriptor is non-data. The C implementation lives in
`Objects/funcobject.c` (`PyClassMethodDescrObject` /
`PyStaticMethod_Object`).

### 5.3 Plain functions are non-data descriptors too

`def` inside a class produces a function whose `__get__` returns a bound
method (`MethodType`). This is why `self` "just works" — there is no
compiler magic, just a descriptor:

```python
class C:
    def f(self): pass

c = C()
c.f   # <bound method C.f of <__main__.C object at 0x...>>
C.f   # <function C.f at 0x...>    (instance is None → unbound)
```

The function descriptor returns a bound method object holding `(function,
instance)`; calling it prepends `instance` to the args.

## 6. `__init_subclass__` — Metaclass-free Hooks (PEP 487)

Before PEP 487, the only way to be notified at subclass-creation time was
to write a metaclass. PEP 487 introduced two hooks on the *parent* class:

```python
class Plugin:
    registry = []
    def __init_subclass__(cls, name=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if name:
            Plugin.registry.append((name, cls))

class Foo(Plugin, name="foo"): pass
class Bar(Plugin, name="bar"): pass

assert Plugin.registry == [("foo", Foo), ("bar", Bar)]
```

The hook is `@staticmethod`-like — `cls` is the *new* subclass, not the
parent. Keyword arguments in the `class Foo(Plugin, name="foo")` syntax
are passed through. `__set_name__` on descriptors (also PEP 487) lets a
descriptor learn the attribute name it was assigned to at class creation
time, which `dataclasses` uses to populate `__dataclass_fields__`.

## 7. `ABCMeta` and `dataclass`

### 7.1 `ABCMeta`

`ABCMeta` is a metaclass that tracks *abstract methods* (those decorated
with `@abstractmethod`). On instantiation, `ABCMeta.__call__` walks the
MRO and checks for any unimplemented abstract methods on the concrete
class; if any remain, it raises `TypeError`:

```python
from abc import ABCMeta, abstractmethod

class Stream(metaclass=ABCMeta):
    @abstractmethod
    def read(self, n: int) -> bytes: ...

class ClosedStream(Stream): pass       # does not override read
ClosedStream()                        # TypeError: Can't instantiate abstract
                                      # class ClosedStream without an
                                      # implementation for abstract method 'read'
```

The mechanism is a `__abstractmethods__` frozenset computed at class
creation time by walking the MRO. The check is *not* a runtime method
call — it is a single attribute lookup at `__call__` time, so the cost is
zero for the normal case.

### 7.2 `@dataclass` (PEP 557)

`@dataclass` is a class decorator (not a metaclass — by design). It runs
*after* class creation, reads `cls.__annotations__`, and synthesizes:

- `__init__` with positional args matching field order (or `kw_only` etc.)
- `__repr__` with `field=repr(field)` for each field
- `__eq__` comparing `(field1, field2, ...)` tuples (so subclasses compare
  unequal to parents even with same fields, by checking `other.__class__`)
- `__hash__`, `__lt__`, `__le__`, `__gt__`, `__ge__` (with `order=True`)
- `__post_init__` hook called from the generated `__init__` last

The fields live in `cls.__dataclass_fields__`, a dict of `Field` objects.
The `@dataclass(frozen=True)` mode uses `object.__setattr__` and
`object.__delattr__` in the generated methods to bypass the
`__setattr__` interceptor the decorator installs (a frozen dataclass is
*not* a `__slots__` class — instances still have a `__dict__`, just
read-only).

## 8. Comparison with Ruby

| Concern | Python | Ruby |
|---------|--------|------|
| Class-of-class | `type` (or a metaclass); `type(type) is type` | `Class < Module`; `Class`'s class is itself, but `Module` exists separately |
| Metaclass per object | Not directly; the class of an instance is one | *Every* object has a singleton class (`obj.singleton_class`) — methods can be added per-instance without a class |
| Method lookup fallback | `__getattr__(name)` after the chain fails | `method_missing(symbol, *args)` — same idea, different dispatch |
| Attribute access hook | `__getattribute__` on every access | `Module#attr_*` macros + `instance_variable_get`; no per-access hook |
| Class creation hook | `__init_subclass__` (PEP 487) | `Class#inherited(subclass)` callback |
| Multiple inheritance | C3 linearization across arbitrary graphs | Only one "regular" superclass + modules (mixins); no diamonds |
| Property-like API | `property` (data descriptor) | `attr_accessor :x` (generates plain methods, no descriptor) |
| Metaprogramming culture | Decorators, descriptors, metaclass if needed | Open classes, `method_missing`, `const_missing`, refinements |

The two philosophies diverge on **per-object customization**. Ruby's
*singleton class* is a real class inserted between the object and its
class — you can attach methods to a single object with `def obj.foo` and
the lookup chain walks `obj → obj.singleton_class → obj.class → ...`.
Python has no equivalent: every instance shares its class's methods; the
only per-instance state is `instance.__dict__`, which holds data but
cannot hold *behavior* (you cannot attach a method to one `Point`
instance — only to the class, affecting all instances). The work-around
is `types.MethodType(func, obj)` assigned to `instance.__dict__`, which
works because the function is a descriptor; but this is rare in real code.

## References

- [Python Data Model — reference documentation](https://docs.python.org/3/reference/datamodel.html)
- [Descriptor HowTo Guide (by Raymond Hettinger)](https://docs.python.org/3/howto/descriptor.html)
- [PEP 3115 — Metaclasses in Python 3000](https://peps.python.org/pep-3115/)
- [PEP 487 — `__set_name__` and `__init_subclass__`](https://peps.python.org/pep-0487/)
- [PEP 557 — Data Classes](https://peps.python.org/pep-0557/)
- [C3 linearization — original Dylan paper (Barbuto)][c3-paper]
- *Fluent Python* (2nd ed.), Luciano Ramalho — chapters 11, 13, 14
- *Python Descriptors*, Mark Sheridan — [online PDF](https://kpug.org/reference/python-descriptors.pdf)
- [CPython `Objects/typeobject.c` — `type_call` and MRO computation](https://github.com/python/cpython/blob/main/Objects/typeobject.c)

[c3-paper]: https://docs.python.org/3/howto/mro.html
