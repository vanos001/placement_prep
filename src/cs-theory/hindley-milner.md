# Hindley-Milner Type Inference

Hindley-Milner (HM) is the type discipline that lets a compiler deduce the types of a
whole program from almost no annotations, yet still reject every program that could go
wrong at runtime. It is the engine inside ML, Standard ML, OCaml, Haskell, F#, and Elm,
and its unification half also powers Rust's trait inference. The name honors two
independent discoveries: Roger Hindley proved the principal-type property for
combinatory logic (1969), and Robin Milner designed the inference algorithm for ML
(1978), which Damas and Milner proved sound and complete (POPL 1982). Interviews probe
three things: why `let` generalizes but lambda binders do not, why mutable references
forced the value restriction, and why the same algorithm cannot extend to subtyping or
higher-rank functions.

> Related: [Lambda Calculus](./lambda-calculus.md) (syntax reused below, not re-taught),
> [Programming Language Theory](./programming-language-theory.md) (survey context),
> [Type Inference](../compilers/advanced/type-inference.md) (Robinson unification,
> bidirectional checking), [Subtyping and Variance](../compilers/advanced/subtyping-variance.md)
> (the algebra HM omits), [Curry-Howard](./curry-howard.md) (the logic HM embeds).

## The goal: a principal type, without annotations

For the simply-typed lambda calculus `fun x -> x` has infinitely many types
(`int -> int`, `bool -> bool`, ...). HM's central object is the **principal type**: the
most general one, of which every other typable instance is a substitution instance.
`fun f -> fun x -> f (f x)` has principal type `(a -> a) -> a -> a`; supply an
`int -> int` function and you get `int -> int`, nothing more. Hindley (1969) proved
principal types exist (for combinators; Milner lifted the result to a polymorphic
calculus with `let`), and Damas-Milner (1982) proved Algorithm W terminates with the
principal type scheme exactly when the program is typable. Principality is what makes
inference *modular*: each function's most general type is a stable interface that call
sites specialize, so separate compilation and library signatures work without global
analysis.

## Algorithm W: the rules

Types are built from variables `a, b, ...`, base types (`int`, `bool`), and the arrow
`->`. A **type scheme** `forall a1 ... an. t` quantifies variables; an environment maps
names to schemes. W processes one node at a time and composes substitutions as it goes:

| Case | What W does |
|------|-------------|
| `x` (variable) | look up its scheme, instantiate quantified vars with fresh vars |
| `fun x -> e` | fresh var `a` for `x`, infer `e`, return `a -> t(e)` |
| `e1 e2` | infer both; fresh `a`; unify `t(e1) = t(e2) -> a`; return `a` |
| `let x = e1 in e2` | infer `t(e1)`; **generalize** its free vars not free in the environment; infer `e2` under `x : forall ... t(e1)` |
| `if e1 then e2 else e3` | unify `t(e1) = bool`; unify `t(e2) = t(e3)`; return `t(e2)` |

Everything rides on **unification** (Robinson, 1965): find the most general substitution
making two type terms equal. W unifies while it descends; Algorithm J, Milner's second
presentation in the same 1978 paper, yields the same principal types but pushes
substitutions eagerly through the environment instead of composing them -- the shape
real implementations take.

## Unification, the occurs check, and complexity

Type terms form a free algebra, so a most general unifier exists and is unique up to
renaming; a union-find over unification variables computes it in near-linear time
(Tarjan, 1975: amortized `O(alpha(n))` per operation with path compression and union by
rank). One guard is mandatory:

```text
   infer:  fun x -> x x
   x : a   (fresh)
   unify a = a -> b        occurs check: does a occur in a -> b?  YES
   reject: infinite type a = a -> b        (no finite type solves this)
```

Without the occurs check the engine "succeeds" with an infinite, unrepresentable type;
production unifiers run it (OCaml's `-rectypes` is the explicit opt-out, admitting
regular recursive types). The overall worst case is still exponential -- Mairson (1990)
proved ML typability is DEXPTIME-complete, since nested `let`s can duplicate constraints
exponentially -- but unification itself never is; real code type-checks near-linearly.

## Let-polymorphism, and why mutable references broke it

The `let` rule is HM's one act of polymorphism. Because `e1` is fully typed *before* the
body, its free variables can be safely quantified, and each use of `x` instantiates them
independently. Lambda binders get no such treatment: their type variable is fixed before
the body is examined, so both uses of a lambda-bound `id` must agree:

```ocaml
let id = fun x -> x in if id true then id 1 else 0    (* ok: id used at bool and int *)
(fun id -> if id true then id 1 else 0)               (* rejected: bool vs int *)
```

Quantifying only at `let` keeps every scheme **rank-1** (all quantifiers at the front).
That is the decidability price; the soundness price arrives with references:

```ocaml
let r = ref (fun x -> x)      (* naive reading: r : forall a. (a -> a) ref *)
let _ = r := (fun x -> x + 1) (* this use: a := int *)
let _ = !r true               (* this use: a := bool -- applies x + 1 to true *)
```

Under naive generalization this type-checks, yet the last line applies an integer
successor to a boolean. Nothing is wrong with unification; `forall a. (a -> a) ref` is a
lie about *sharing*. Generalizing a **value** copies it, so independent instantiations
are honest; generalizing a ref cell leaves one mutable cell wearing many types. Wright
(1995) fixed this with the **value restriction**: generalize only syntactic values
(constants, variables, lambdas, constructors applied to values); anything else keeps a
monomorphic "weak" type -- OCaml prints the unsolved variables as `'_weak1` -- whose
variables are fixed up if they never escape. Garrigue (2004) relaxed the rule: a
non-value generalizes anyway when its free variables cannot reach mutable state
(`List.rev []` generalizes; `ref []` does not). Standard ML adopted the value
restriction in its 1997 definition; Haskell, whose references live inside `ST`/`IO`,
instead needs the differently-motivated monomorphism restriction for overloaded
bindings.

## What Damas-Milner soundness means

Milner's 1978 slogan -- "well-typed programs cannot go wrong" -- is a subject-reduction
statement: evaluation of a well-typed program never gets stuck, and types survive
reduction. Damas-Milner (1982) proved W sound and complete for the *pure* language;
references came later, and it was Wright (1995) who restored type safety for the
imperative fragment by restricting generalization. Note the division of labor:
soundness is a property of the type system, W only *finds* its types, and the value
restriction is a change to the type system that inference must respect -- one that
genuinely rejects programs a permissive system would accept. That conservatism is the
fee for having both zero annotations and mutable state.

## The constraint-based view

Algorithm W is one presentation of a deeper fact: HM typing is **equality-constraint
solving** over first-order type terms. Each application emits an equation; the principal
type is the most general unifier projected back onto the variables of interest:

```text
      source term              equations emitted               union-find state
   ------------------   ---------------------------------   ----------------------------
   fun f -> fun x ->    (1)  a = b -> c        (f x)        a ~ (b -> c)
      f (f x)           (2)  a = c -> d        (f (f x))    merge: b ~ c ~ d
                                                             principal type: (b -> b) -> b -> b
```

W unifies as it descends; constraint-based engines (Algorithm J in spirit; GHC's
OutsideIn(X) since 7.0) generate the full constraint set first, then solve with a
worklist over union-find. The split matters once constraints stop being plain
equalities: type classes add predicate constraints and GADTs add local equalities, and
the solver then needs suspension, improvement, and explanations that interleaved W
cannot provide.

## Where ML-style inference breaks: subtyping and higher rank

- **Subtyping**: unification demands *equality*, but subtyping is an ordering
  (`int <: Number`). Constraints like `a <: int` have no principal solution, and
  type-directed coercion insertion is not inferable by unification, so languages either
  annotate (Java generics, Scala, TypeScript) or keep HM and refuse the feature (core
  OCaml). The variance algebra that governs the annotations is in
  [Subtyping and Variance](../compilers/advanced/subtyping-variance.md).
- **Higher rank**: `fun f -> (f 1, f true)` uses `f` at two types inside one body --
  rank 2. Typability in System F (rank-n) is undecidable (Wells, 1999), so no inference
  algorithm can cover it. **Bidirectional checking** (Pierce and Turner, 2000) is the
  practical answer: check-mode consumes annotations, synthesize-mode does the rest,
  recovering rank-n plus better error positions (see
  [Type Inference](../compilers/advanced/type-inference.md)). HM's genius is picking the
  fragment where inference is *both* decidable *and* principal; everything past it
  trades annotations for expressiveness.

## How real compilers do it

| Language | Inference core | Deviations from vanilla W |
|----------|----------------|---------------------------|
| OCaml | W variant with unification variables and levels | value restriction with `'_weak` vars, relaxed value restriction; polymorphic methods/variants need annotations |
| Haskell (GHC) | constraint generation + OutsideIn(X) solver (since GHC 7.0) | type classes, GADTs, type families; monomorphism restriction |
| Standard ML | W as formalized in the 1997 Definition | value restriction; equality types |
| F# | HM over .NET nominal types | generalizes only values; OO subtyping handled separately |
| Elm | plain HM, error messages as a feature | none, deliberately |
| Rust | unification over inference variables + trait obligations | annotation fallbacks (e.g. some closures) |

## Unification failures are the user interface

Most type errors are unification failures, and their weakness is *position*: the
unifier reports where two types collided, which can be far from where the wrong
assumption was introduced. The canonical messages have been stable for decades -- GHC's
`Couldn't match expected type 'Bool' with actual type 'Int'`, OCaml's
`This expression has type int but an expression was expected of type bool`, SML/NJ's
`operator and operand don't agree [tycon mismatch]` -- and the occurs check gets its own
phrasing (`Occurs check: cannot construct the infinite type: a = a -> b`). Compiler UX
work therefore targets the solver: keep a provenance span per unification variable,
remember which expression instantiated it, and re-derive the type step by step for the
user (Elm made this its selling point). The engine below emits these message shapes in
miniature.

## A complete tiny engine

This Python program is all of Algorithm W -- substitution, occurs check, unification,
generalization/instantiation, and a value-restriction switch -- running six programs:
two principal types, let- vs lambda-polymorphism, an occurs-check failure, and the
ref-cell unsoundness with and without the value restriction.

```python
# Algorithm W. Types: ('var',n)|('con',n)|('fun',a,b)|('ref',a)
# AST: ('var',x)|('num',n)|('bool',b)|('abs',x,e)|('app',f,a)|('let',x,e1,e2)|('if',c,t,f)
import itertools

class HMError(Exception): pass
_subst, _letters = {}, 'abcdefgh'
_counter, _names, VALUE_RESTRICTION = itertools.count(), {}, True

def fresh(): return ('var', 't%d' % next(_counter))

def apply(t):                        # resolve substitution chains
    while t[0] == 'var' and t[1] in _subst: t = _subst[t[1]]
    if t[0] in ('fun', 'ref'):
        return t[:1] + tuple(apply(x) for x in t[1:])
    return t

def occurs(name, t):                 # occurs check: reject infinite types
    t = apply(t)
    return name == t[1] if t[0] == 'var' else any(occurs(name, x) for x in t[1:])

def unify(a, b):
    a, b = apply(a), apply(b)
    if a == b: return
    if a[0] == 'var':
        if occurs(a[1], b): raise HMError('infinite type: %s = %s' % (pp(a), pp(b)))
        _subst[a[1]] = b; return
    if b[0] == 'var': return unify(b, a)
    if a[0] == 'fun' and b[0] == 'fun':
        unify(a[1], b[1]); unify(a[2], b[2]); return
    if a[0] == 'ref' and b[0] == 'ref':
        unify(a[1], b[1]); return
    raise HMError('cannot unify %s with %s' % (pp(a), pp(b)))

def pp(t):                           # pretty-print, naming vars a,b,c,...
    t = apply(t)
    if t[0] == 'var': return _names.setdefault(t[1], _letters[len(_names) % len(_letters)])
    if t[0] == 'con': return t[1]
    if t[0] == 'ref': return '%s ref' % ('(%s)' % pp(t[1]) if t[1][0] == 'fun' else pp(t[1]))
    lhs = '(%s)' % pp(t[1]) if t[1][0] == 'fun' else pp(t[1])
    return '%s -> %s' % (lhs, pp(t[2]))

def fvs(t):                          # free type variables (post-substitution)
    t = apply(t)
    return {t[1]} if t[0] == 'var' else set().union(*[fvs(x) for x in t[1:]])

def inst(t, m):                      # instantiate: rename quantified vars to fresh
    return m.get(t[1], t) if t[0] == 'var' else (t[0],) + tuple(inst(x, m) for x in t[1:])

PRIMS = {'ref':    (['v'], ('fun', ('var', 'v'), ('ref', ('var', 'v')))),
         'deref':  (['v'], ('fun', ('ref', ('var', 'v')), ('var', 'v'))),
         'assign': (['v'], ('fun', ('ref', ('var', 'v')),
                            ('fun', ('var', 'v'), ('var', 'v')))),
         'succ':   ([],    ('fun', ('con', 'int'), ('con', 'int')))}

def W(env, e):
    tag = e[0]
    if tag == 'var':
        q, t = env[e[1]] if e[1] in env else PRIMS[e[1]]
        return inst(t, {v: fresh() for v in q})
    if tag == 'num': return ('con', 'int')
    if tag == 'bool': return ('con', 'bool')
    if tag == 'abs':
        tv = fresh()
        return ('fun', tv, W({**env, e[1]: ([], tv)}, e[2]))
    if tag == 'app':
        tr = fresh()
        unify(W(env, e[1]), ('fun', W(env, e[2]), tr))
        return tr
    if tag == 'if':
        unify(W(env, e[1]), ('con', 'bool'))
        tt, tf = W(env, e[2]), W(env, e[3])
        unify(tt, tf); return tt
    t1 = apply(W(env, e[2]))         # let: snapshot subst, then generalize unless restricted
    free = sorted(fvs(t1) - set().union(*[fvs(s[1]) for s in env.values()]))
    mono = VALUE_RESTRICTION and e[2][0] not in ('abs', 'var', 'num', 'bool')
    return W({**env, e[1]: (([], t1) if mono else (free, t1))}, e[3])

def check(label, e, vr=True):
    global _subst, _names, _counter, VALUE_RESTRICTION
    _subst, _names, VALUE_RESTRICTION, _counter = {}, {}, vr, itertools.count()
    try: return '  %-19s %s' % (label, pp(W({}, e)))
    except HMError as err: return '  %-19s TYPE ERROR: %s' % (label, err)

def V(x): return ('var', x)
ID = ('abs', 'x', V('x'))
twice = ('abs', 'f', ('abs', 'x', ('app', V('f'), ('app', V('f'), V('x')))))
unsound = ('let', 'r', ('app', V('ref'), ID),
           ('let', 'u', ('app', ('app', V('assign'), V('r')), V('succ')),
            ('app', ('app', V('deref'), V('r')), ('bool', True))))
CASES = [
    ('1) fn x -> x', 'principal type:', ID, True),
    ('2) fn f -> fn x -> f (f x)', 'principal type:', twice, True),
    ('3) let id = fn x -> x in if id True then id 1 else 0', 'type:',
     ('let', 'id', ID, ('if', ('app', V('id'), ('bool', True)),
                        ('app', V('id'), ('num', 1)), ('num', 0))), True),
    ('4) (fn id -> if id True then id 1 else 0)', 'type:',
     ('abs', 'id', ('if', ('app', V('id'), ('bool', True)),
                    ('app', V('id'), ('num', 1)), ('num', 0))), True),
    ('5) fn x -> x x', 'type:', ('abs', 'x', ('app', V('x'), V('x'))), True),
    ('6) let r = ref (fn x -> x) in let u = assign r succ in deref r True',
     'no restriction:', unsound, False),
    (None, 'value restriction:', unsound, True),
]
for title, label, e, vr in CASES:
    if title: print(title)
    print(check(label, e, vr))
```

Output (python3, identical across runs):

```text
1) fn x -> x
  principal type:     a -> a
2) fn f -> fn x -> f (f x)
  principal type:     (a -> a) -> a -> a
3) let id = fn x -> x in if id True then id 1 else 0
  type:               int
4) (fn id -> if id True then id 1 else 0)
  type:               TYPE ERROR: cannot unify bool with int
5) fn x -> x x
  type:               TYPE ERROR: infinite type: a = a -> b
6) let r = ref (fn x -> x) in let u = assign r succ in deref r True
  no restriction:     bool
  value restriction:  TYPE ERROR: cannot unify int with bool
```

Program 3 is the point of `let`: one `id`, used at `bool` *and* `int`. Program 6 is the
point of the value restriction: without it the engine returns `bool` for a program that
applies integer successor to `true`; with it, the silent unsoundness becomes an honest
`cannot unify int with bool`.

## Interview questions

**Q: Why does `let` generalize but `fun` not?**
A: `let` types its right-hand side completely before the body, so its variables can be
quantified and each use instantiated fresh. A lambda binder's type is fixed before the
body is checked, so both uses of a lambda-bound `id` constrain one variable. For pure
code generalizing lambdas would be sound but not inferable by unification; with
references it is outright unsound (program 6 above).

**Q: What exactly breaks if the value restriction is dropped?**
A: A non-value like `ref (fun x -> x)` gets `forall a. (a -> a) ref`, but all
instantiations denote one mutable cell: store through one instantiation, read through
another, and the runtime does something the types said was impossible. Wright's fix is
syntactic: only values are copied on binding, so only their types may be generalized.

**Q: Why can't HM infer `fun f -> (f 1, f true)`, and what do compilers do instead?**
A: That is a rank-2 requirement; HM schemes are rank-1, and rank-n typability (System F)
is undecidable (Wells, 1999). Compilers switch to bidirectional checking: an annotation
puts the checker in check-mode, where rank-n types are decidable to *verify* even though
they are not inferable.

## References

- R. Hindley, "The Principal Type-Scheme of an Object in Combinatory Logic", *Trans. Amer. Math. Soc.* 146 (1969) -- <https://doi.org/10.2307/1995158>
- R. Milner, "A Theory of Type Polymorphism in Programming", *J. Computer and System Sciences* 17(3) (1978) -- <https://doi.org/10.1016/0022-0000(78)90014-4>
- L. Damas, R. Milner, "Principal type-schemes for functional programs", *POPL '82* -- <https://doi.org/10.1145/582153.582176>
- A. K. Wright, "Simple imperative polymorphism", *LISP and Symbolic Computation* 8(4) (1995) -- <https://doi.org/10.1007/BF01018828>
- OCaml manual, "Polymorphism and its limitations" (weak type variables) -- <https://ocaml.org/manual/5.5/polymorphism.html>
- J. Garrigue, "Relaxed Value Restriction", *FIWFLP 2004* -- <https://caml.inria.fr/pub/papers/garrigue-value_restriction-fiwflp04.pdf>
- H. Mairson, "Deciding ML typability is complete for deterministic exponential time", *POPL '90* -- <https://doi.org/10.1145/96709.96717>
- R. E. Tarjan, "Efficiency of a good but not linear set union algorithm", *JACM* 22(2) (1975) -- <https://doi.org/10.1145/321879.321884>
- J. B. Wells, "Typability and type checking in System F are equivalent and undecidable", *Ann. Pure Appl. Logic* 98 (1999) -- <https://doi.org/10.1016/S0168-0072(98)00047-5>
- D. Vytiniotis, S. Peyton Jones, T. Schrijvers, M. Sulzmann, "OutsideIn(X)", *J. Functional Programming* 21(6) (2011) -- <https://doi.org/10.1017/S0956796811000098>
- B. C. Pierce, D. N. Turner, "Local type inference", *ACM TOPLAS* 22(1) (2000) -- <https://doi.org/10.1145/345099.345100>
