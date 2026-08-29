# Subtyping and Variance: The Algebra of Safe Substitutability

`S <: T` is a promise: any program expecting a `T` accepts an `S` and still behaves.
**Variance** asks when the promise survives a type constructor: given `S <: T`, what
relation holds between `F<S>` and `F<T>`? One principle generates every answer here:
a position that only *produces* `T` is covariant, one that only *consumes* `T` is
contravariant, one that does both is invariant. The anchor is behavioral subtyping
(Liskov & Wing, 1994): preconditions must not be strengthened, postconditions not
weakened - inputs versus outputs, the seed of the algebra. Cook, Hill, and Canning
(POPL 1990) add the standing warning that inheritance is not subtyping: variance is
a property of substitutability, not of who inherits whom. The survey table lives in
[Type Inference](./type-inference.md); this page proves the rules, watches three
languages patch or break them, and runs a checker that infers variance from usage.

## The Function-Space Rule: Consume Negative, Produce Positive

When is `S1 -> S2` a subtype of `T1 -> T2`? A caller of `T1 -> T2` hands it some `T1`
and relies on receiving something usable as `T2`, so the subtype must demand no more
(`T1 <: S1`) and produce no less (`S2 <: T2`) - arguments flip, returns preserve.
With `Cat <: Animal`: `(Animal -> Cat) <: (Animal -> Animal)` and
`(Dog -> Animal) <: (Cat -> Animal)`. The rule composes structurally: give each
position polarity `+1` (producing) or `-1` (consuming); a nested position's polarity
is the product of signs along its path. A method parameter is `-1`, but a `T` inside
a callback *in* that parameter, `m(cb: (T) -> Unit)`, is `(-1) * (-1) = +1` - which
is why `forEach(action: (T) -> Unit)` fits a covariant `List<out T>` in Kotlin.
## Mutable Cells Are Invariant: the Write-Path Proof

Give `Cell<T>` a read leg and a write leg, `get(): T` plus `set(x: T)`, and assume
covariance, `Cell<Dog> <: Cell<Animal>`:

```text
   c  : Cell<Dog>    = Cell<Dog>()
   ca : Cell<Animal> = c            -- accepted by the assumed covariance
   ca.set(new Cat())                -- Cat <: Animal, so this type-checks
   d  : Dog          = c.get()      -- statically a Dog, dynamically a Cat
```

The contradiction lives entirely on the **write path**: the setter consumes `T`, so
covariance lets a caller push a supertype through the wider type into storage owned
by the narrower one. Read the cell as two independent legs: `get` wants
`Dog <: Animal` (covariance delivers it), `set` wants `Animal <: Dog` (satisfiable
only when the two are equal) - both directions at once forces invariance. Delete the
write leg and covariance returns: that is the entire design of read-only views like
Kotlin's `List<out T>`. Delete the read leg and contravariance returns (sinks).
## Java Arrays: Covariance as Runtime Debt

JLS 4.10.3, "Subtyping among Array Types", makes arrays covariant: `S[] <: T[]`
whenever `S <: T`. Arrays are mutable, so the write-path proof applies - and Java
patches it dynamically instead of rejecting the program: every store carries a
component-type check and the failed one raises `java.lang.ArrayStoreException`,
documented as "thrown to indicate that an attempt has been made to store the wrong
type of object into an array of objects":

```java
Object[] a = new String[1];   // String[] <: Object[] per JLS 4.10.3
a[0] = 42;                    // compiles; ArrayStoreException at runtime
```

Historically, arrays predate generics (Java 5), and covariance bought
read-flexibility before wildcards existed. It still leaks into generics: `new T[n]`
is rejected because erasure leaves no component type for the runtime check, which is
why idiom forces the escape hatch `(T[]) new Object[n]` and its heap-pollution risk.
## Declaration-Site vs Use-Site Variance

Two syntactic regimes express the same algebra. Declaration-site (Kotlin `out`/`in`,
C# `out`/`in` on interfaces and delegates) computes variance once from the member
positions and rejects violating declarations; use-site (Java wildcards) keeps classes
invariant and lets callers pick a direction per instance:

| Aspect | Declaration-site (`out`/`in`) | Use-site (Java wildcards) |
|---|---|---|
| Annotated where | once, on the declaration | at every single usage |
| Legacy invariant classes | cannot be retrofitted | work immediately |
| Direction choice | fixed per class | both `? extends` and `? super` per use |
| Checker machinery | member-position computation | capture conversion (JLS 5.1.10) |

Capture conversion is the subtle part: `List<? extends Number>` names no type you
can write, so the compiler invents a fresh type variable for the wildcard's
unknown-but-fixed element type - which the classic swap idiom then binds to a generic
helper's `E`, giving the unknown a name for one call. Kotlin ships both regimes
(`out T` at declaration; `List<out Animal>` projections and `*` star-projections at
use). Go declined the whole feature: its generics are strictly invariant with explicit
constraints (see [Go Generics and Error Handling](../../languages/go/generics-error-handling.md)).

## TypeScript: Methods Are (Still) Bivariant

TypeScript compares function parameters bivariantly (either direction counts) for
compatibility - unsound, but it kept DOM handlers and comparators assignable. Since
TypeScript 2.6, `strictFunctionTypes` makes *function type positions*
contravariant-only, with a deliberate carve-out: method syntax (`handle(x: T): void`)
stays bivariant even under strict mode, while function *property* syntax
(`handle: (x: T) => void`) gets the strict rule. Method parameters are the
interoperability surface (`addEventListener`, sort comparators), so full
contravariance there broke real code; the cost is a soundness hole exactly the size
of the bivariance - demonstrated in section 3 of the demo. Because TypeScript's
typing is structural, variance emerges from shape comparison rather than from
declarations (see [TypeScript](../../languages/typescript/README.md)).
## Variance as a Sign Algebra

Collect the signs of *all* occurrences of the parameter - `{+}` gives covariance,
`{-}` contravariance, `{+,-}` invariance, and the empty set a phantom parameter with
no constraint. Composition multiplies signs along the access path; joining
occurrences takes the meet of their sign sets:

```text
              unconstrained (phantom / bivariant)
                 /                          \
         covariant (+)                contravariant (-)
                 \                          /
                  invariant ({+,-})  = meet of the two signs
```

Rust runs exactly this algebra over the one subtyping relation it actually has,
lifetimes (`'long <: 'short`): `Box`/`Vec` are covariant, `&mut T` and `Cell<T>`
invariant, `fn(T)` contravariant in `T`, and since a struct that never mentions `T`
is phantom (unsound under interior mutability), `PhantomData<T>` declares the
variance the struct should pretend to have (Rustonomicon, ch. "Subtyping and
Variance").
## The Runnable Checker: Infer, Then Refute

The harness models a generic class as a list of members with type expressions,
infers the sign of the parameter in every member, then tests claimed variances by
substituting the sample hierarchy into `F<S> <: F<T>`; refuted claims print the exact
failing sub-goal, and bivariance mode emulates pre-2.6 TypeScript methods.

```python
#!/usr/bin/env python3
# Variance inference + substitution-test harness (pure stdlib).
# Class = list of (member, type-expr); exprs are ('Leaf', n) atomic types,
# ('Arrow', a, r) fn type, ('Mut', t) read+write cell, ('Src', t)/('Snk', t)
# read-only / write-only wrapper, ('PA',)/('PB',) the params under test.
UNIT  = ('Leaf', 'Unit')
HIER  = {'Dog': 'Animal', 'Cat': 'Animal'}          # child -> parent edges
PAIRS = [('Dog', 'Animal'), ('Cat', 'Animal')]      # sampled S <: T, S != T
VAR   = {frozenset({1}): 'covariant', frozenset({-1}): 'contravariant',
         frozenset({1, -1}): 'invariant', frozenset(): 'phantom (unused)'}

def instantiate(t, m):
    if t[0] in m: return m[t[0]]
    if t[0] == 'Arrow': return ('Arrow', instantiate(t[1], m), instantiate(t[2], m))
    if t[0] in ('Mut', 'Src', 'Snk'): return (t[0], instantiate(t[1], m))
    return t

def sub(a, b, bi=False):  # a <: b; bi=True emulates pre-strictFunctionTypes methods
    if a == b: return True
    if a[0] == b[0] == 'Leaf': return HIER.get(a[1]) == b[1]
    if a[0] == b[0] == 'Arrow':
        return (sub(b[1], a[1]) or (bi and sub(a[1], b[1]))) and sub(a[2], b[2])
    if a[0] == b[0] == 'Mut': return sub(a[1], b[1]) and sub(b[1], a[1])
    if a[0] == b[0] == 'Src': return sub(a[1], b[1])
    if a[0] == b[0] == 'Snk': return sub(b[1], a[1])
    return False

def demands(t1, t2, tag):  # atomic leaf facts 'x <: y' with the constructor forcing them
    if t1[0] == 'Leaf': return [(tag, t1, t2)]
    if t1[0] == 'Arrow':
        return demands(t2[1], t1[1], 'fn-arg contra') + demands(t1[2], t2[2], 'fn-ret co')
    if t1[0] == 'Mut':
        return demands(t1[1], t2[1], 'cell-read co') + demands(t2[1], t1[1], 'cell-write contra')
    if t1[0] == 'Src':  return demands(t1[1], t2[1], 'src co')
    if t1[0] == 'Snk':  return demands(t2[1], t1[1], 'snk contra')
    return []

def sat(f): x, y = f[1], f[2]; return x == y or HIER.get(x[1]) == y[1]

def polarities(t, sign, acc):  # sign of every occurrence of each parameter
    k = t[0]
    if k in ('PA', 'PB'): acc.setdefault(k, set()).add(sign)
    elif k == 'Arrow': polarities(t[1], -sign, acc); polarities(t[2], sign, acc)
    elif k == 'Mut':   polarities(t[1], sign, acc); polarities(t[1], -sign, acc)
    elif k == 'Src':   polarities(t[1], sign, acc)
    elif k == 'Snk':   polarities(t[1], -sign, acc)
    return acc

def fmt(s):
    return '{%s}' % ','.join('+' if v > 0 else '-' for v in sorted(s, reverse=True))

def first_fail(members, p, claim, bi=False, fixed=None):
    fixed = fixed or {}
    for s, t in PAIRS:
        a = dict(fixed, **{p: ('Leaf', s) if claim == 'co' else ('Leaf', t)})
        b = dict(fixed, **{p: ('Leaf', t) if claim == 'co' else ('Leaf', s)})
        for nm, ty in members:
            t1, t2 = instantiate(ty, a), instantiate(ty, b)
            if not sub(t1, t2, bi):
                return s, t, nm, next(f for f in demands(t1, t2, '') if not sat(f))
    return None

BOX = [('get(): T',  ('Arrow', UNIT, ('PA',))),
       ('set(x: T)', ('Arrow', ('PA',), UNIT)),
       ('value: T',  ('Mut',  ('PA',)))]
RO  = [('get(): T',  ('Arrow', UNIT, ('PA',)))]
SNK = [('set(x: T)', ('Arrow', ('PA',), UNIT))]
FN  = [('apply(a: A): B', ('Arrow', ('PA',), ('PB',)))]
HDL = [('handle(x: T)',   ('Arrow', ('PA',), UNIT))]
ARR = [('a[i]: T',        ('Mut',  ('PA',)))]

print('== 1. Position inference: sign of every occurrence of the parameter ==')
for nm, ty in BOX:
    pol = polarities(ty, 1, {}).get('PA', set())
    print('  Box<T>.%-10s occurrences %-7s member forces: %s' % (nm, fmt(pol), VAR[frozenset(pol)]))
allpol = frozenset().union(*[polarities(ty, 1, {}).get('PA', set()) for _, ty in BOX])
print('  join over members: %-7s => Box<T> must be %s' % (fmt(allpol), VAR[allpol]))

print('== 2. Substitution harness over sampled Dog <: Animal, Cat <: Animal ==')
CASES = [('Box<T>', BOX, 'PA', None), ('RoCell<T>', RO, 'PA', None),
         ('Sink<T>', SNK, 'PA', None),
         ('Fn<A,B> on A', FN, 'PA', {'PB': ('Leaf', 'Animal')}),
         ('Fn<A,B> on B', FN, 'PB', {'PA': ('Leaf', 'Dog')})]
for label, mem, p, fx in CASES:
    co = first_fail(mem, p, 'co', fixed=fx) is None
    ca = first_fail(mem, p, 'contra', fixed=fx) is None
    print(('  %-14s covariant: %-8s contravariant: %-8s'
           % (label, 'sound' if co else 'REFUTED', 'sound' if ca else 'REFUTED')).rstrip())
    for ok, claim in [(co, 'co'), (ca, 'contra')]:
        if not ok:
            s, t, nm, bad = first_fail(mem, p, claim, fixed=fx)
            print('      %s refuted: %s <: %s, member %-14s %s needs %s <: %s FAIL'
                  % (claim, s, t, nm, bad[0], bad[1][1], bad[2][1]))
    only = 'invariant only' if not (co or ca) else 'covariant' if co else \
           'contravariant' if ca else 'unconstrained'
    print('      => sound choice for this class: %s' % only)

print('== 3. TypeScript methods before strictFunctionTypes (bivariant args) ==')
co = first_fail(HDL, 'PA', 'co', bi=True) is None
ca = first_fail(HDL, 'PA', 'contra', bi=True) is None
print('  Handler<T>.handle(x: T): bivariance admits covariant %s / contravariant %s'
      % ('yes' if co else 'no', 'yes' if ca else 'no'))
print('  unsound: Handler<Dog> used as Handler<Animal>; handle(Cat): Cat <: Dog = %s -> fault'
      % sub(('Leaf', 'Cat'), ('Leaf', 'Dog')))

print('== 4. Java arrays: declared covariant (JLS 4.10.3), checked at runtime ==')
s, t, nm, bad = first_fail(ARR, 'PA', 'co')
print('  covariant T[]: sample %s <: %s, member %s: %s needs %s <: %s FAIL'
      % (s, t, nm, bad[0], bad[1][1], bad[2][1]))
print('  this unsound store is exactly the java.lang.ArrayStoreException path')
```

Output, executed and byte-identical across reruns:

```text
== 1. Position inference: sign of every occurrence of the parameter ==
  Box<T>.get(): T   occurrences {+}     member forces: covariant
  Box<T>.set(x: T)  occurrences {-}     member forces: contravariant
  Box<T>.value: T   occurrences {+,-}   member forces: invariant
  join over members: {+,-}   => Box<T> must be invariant
== 2. Substitution harness over sampled Dog <: Animal, Cat <: Animal ==
  Box<T>         covariant: REFUTED  contravariant: REFUTED
      co refuted: Dog <: Animal, member set(x: T)      fn-arg contra needs Animal <: Dog FAIL
      contra refuted: Dog <: Animal, member get(): T       fn-ret co needs Animal <: Dog FAIL
      => sound choice for this class: invariant only
  RoCell<T>      covariant: sound    contravariant: REFUTED
      contra refuted: Dog <: Animal, member get(): T       fn-ret co needs Animal <: Dog FAIL
      => sound choice for this class: covariant
  Sink<T>        covariant: REFUTED  contravariant: sound
      co refuted: Dog <: Animal, member set(x: T)      fn-arg contra needs Animal <: Dog FAIL
      => sound choice for this class: contravariant
  Fn<A,B> on A   covariant: REFUTED  contravariant: sound
      co refuted: Dog <: Animal, member apply(a: A): B fn-arg contra needs Animal <: Dog FAIL
      => sound choice for this class: contravariant
  Fn<A,B> on B   covariant: sound    contravariant: REFUTED
      contra refuted: Dog <: Animal, member apply(a: A): B fn-ret co needs Animal <: Dog FAIL
      => sound choice for this class: covariant
== 3. TypeScript methods before strictFunctionTypes (bivariant args) ==
  Handler<T>.handle(x: T): bivariance admits covariant yes / contravariant yes
  unsound: Handler<Dog> used as Handler<Animal>; handle(Cat): Cat <: Dog = False -> fault
== 4. Java arrays: declared covariant (JLS 4.10.3), checked at runtime ==
  covariant T[]: sample Dog <: Animal, member a[i]: T: cell-write contra needs Animal <: Dog FAIL
  this unsound store is exactly the java.lang.ArrayStoreException path
```

Read the refutations against the prose: `Box<T>` dies both ways through the two cell
legs (setter = write path, getter = read path), so only invariance survives; `Fn`
reproduces the function-space rule mechanically; section 3 shows bivariance admitting
the direction `strictFunctionTypes` later closes; section 4 is the
`ArrayStoreException` story - a checker rejecting statically what the JVM defers.

## Interview Flash Questions

1. Why are parameters contravariant? Callers supply arguments, so the subtype must accept everything the supertype accepted (Liskov preconditions).
2. Why must a read/write cell be invariant? Covariance falls to the write path, contravariance to the read path; both at once forces S = T.
3. Where does Java pay for array covariance? `ArrayStoreException` per store; sound alternatives are invariance or read-only views.
4. Kotlin `out T` vs Java `? extends T`? Same math; checked per declaration vs per use (via capture conversion).
5. Why do TypeScript methods stay bivariant under `strictFunctionTypes`? DOM and callback interop; only function-property positions got the strict rule.
6. A struct never uses its type parameter - what variance? Phantom/unconstrained; in Rust, declare intent with `PhantomData<T>`.

## References

1. Liskov, Wing - *A Behavioral Notion of Subtyping*, ACM TOPLAS 16(6), 1994 - <https://doi.org/10.1145/197320.197383>
2. Cook, Hill, Canning - *Inheritance Is Not Subtyping*, POPL 1990 - <https://doi.org/10.1145/96709.96721>
3. Java Language Specification, SE 21, sec. 4.10.3 Subtyping among Array Types - <https://docs.oracle.com/javase/specs/jls/se21/html/jls-4.html#jls-4.10.3>
4. `java.lang.ArrayStoreException`, Java SE 21 API Specification - <https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ArrayStoreException.html>
5. Java Language Specification, SE 21, sec. 5.1.10 Capture Conversion - <https://docs.oracle.com/javase/specs/jls/se21/html/jls-5.html#jls-5.1.10>
6. Kotlin Documentation - Generics: declaration-site variance, projections, star-projections - <https://kotlinlang.org/docs/generics.html>
7. TypeScript Handbook - Type Compatibility (parameter bivariance, `strictFunctionTypes`) - <https://www.typescriptlang.org/docs/handbook/type-compatibility.html>
8. TypeScript 2.6 Release Notes - strictFunctionTypes - <https://www.typescriptlang.org/docs/handbook/release-notes/typescript-2-6.html>
9. The Rustonomicon - Subtyping and Variance - <https://doc.rust-lang.org/nomicon/subtyping.html>
10. Microsoft C# Guide - Variance in Generic Interfaces - <https://learn.microsoft.com/en-us/dotnet/csharp/programming-guide/concepts/covariance-contravariance/variance-in-generic-interfaces>
