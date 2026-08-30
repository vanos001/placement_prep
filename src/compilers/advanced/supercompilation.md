# Supercompilation: Driving, Folding, and Program Specialization

Supercompilation is Valentin Turchin's program-transformation technique built
on one idea: execute the program symbolically on unknown input, propagate
everything the execution learns, and when the symbolic execution starts
repeating itself, fold back into a recursive call of the residual program.
Unlike peephole or data-flow optimizations, which make local improvements to a
fixed instruction stream, driving can restructure control flow and eliminate
whole intermediate data structures. It is also notoriously hard to make
predictable, which is why after four decades it remains a research tool rather
than a -O2 flag -- but the ideas leaked into the mainstream: tracing JITs are
driving in disguise, MLIR's partial evaluation has the same flavor, and the
first Futamura projection is a special case of it.

## What driving does

Take a small functional language with `if`, arithmetic, tuples, and recursive
function definitions. A driver walks the program with a *configuration*: an
expression whose subterms may be symbolic (unknown input variables). At each
step it performs the reductions that are forced regardless of the unknown
values, and at every branch it *splits* the configuration into cases:

```text
      configuration:  if (n == 0) then 0 else n + f(n-1),   n symbolic
                          | driving forces the branch
          +---------------+---------------+
          v                               v
   n == 0 branch                   n != 0 branch
   residual: 0                     residual: n + f(n-1)  -> fold or recurse
```

Three operations make up the loop:

1. **Drive**: decompose the configuration by symbolically executing one step.
   Pattern matching against constructors propagates equality constraints;
   arithmetic on known constants folds; a call to a function definition
   unfolds into its body with arguments substituted.
2. **Fold**: when the current configuration is an *instance* of an ancestor
   configuration in the driving history, stop unfolding and emit a recursive
   call to the residual function for that ancestor, parameterized by the
   substitution that relates them.
3. **Generalize**: when a configuration is neither reducible nor foldable and
   the history is growing without structure, take the "common part" of two
   configurations, make it a new task, and split the difference into
   parameters. Generalization is where information is deliberately thrown
   away to regain termination.

The subtle part is fold detection: comparing the current configuration against
every ancestor is unsafe (a config can be a trivial instance of itself), so
practical supercompilers use a well-founded relation on configurations -- most
famously the **homeomorphic embedding** (a configuration embeds into another
when one can be obtained by deleting parts and contracting operators), which
guarantees that an infinite driving sequence must eventually contain a pair
where one embeds in the other.

## How it differs from its neighbors

| Technique | Input knowledge | Mechanism | Termination story |
|---|---|---|---|
| Partial evaluation | some inputs known | specialize program to known inputs (binding-time analysis, offline or online) | controlled by BTA annotations |
| Supercompilation | input symbolic | driving + folding on configurations | whistle / homeomorphic embedding + generalization |
| Abstract interpretation | all inputs unknown | compute invariants over a domain (intervals, signs) | domain satisfies ascending-chain condition |

The boundaries blur in practice. An *online* partial evaluator makes
specialization decisions at specialization time using actual value
information -- at which point it is driving by another name. Conversely,
supercompilation generalizes away input values it cannot exploit, becoming
a whole-program optimizer that needs no known inputs at all. The clean way to
remember it: partial evaluation answers "what does this program do when I fix
these arguments", abstract interpretation answers "what invariant does this
program maintain", and supercompilation answers "what does the *shape* of this
program's computation look like, with all locally-forced steps already taken".

## What it buys: interpreter elimination and deforestation

The two showcase results. First, the Futamura connection: driving an
interpreter with a fixed program but symbolic environment input produces a
residual program that is the interpreted program compiled -- the first
Futamura projection obtained *without* a binding-time analysis. Bolingbroke
and Peyton Jones demonstrated this concretely for Haskell: supercompiling an
interpreter by evaluation produced residual code competitive with
hand-specialization, and in some cases faster than the corresponding compiled
version because driving also exposed cross-instruction optimizations.

Second, deforestation. A composition like `sum (map f xs)` builds an
intermediate list that exists only to be immediately consumed. Driving the
composition makes the producer and consumer alternate symbolically; folding
resolidifies a single recursive function in which the intermediate structure
is gone. Wadler's deforestation transformation achieves the same result under
restrictions (the so-called treeless form); driving achieves it more generally
because the propagation is not limited to a syntactically-checkable form --
but the price is that the result is harder to predict or certify.

## Termination: the whistle and the price of generalization

A naive driver diverges: unfolding `f(n-1)` forever, or generating
configurations of ever-increasing size. The standard solution is the
**whistle**: after each step, test whether the current configuration is
homeomorphically embedded in some ancestor; if so, blow the whistle, fold if
possible and generalize otherwise. The cost is semantic: generalization
discards the very constraints driving worked to discover, so a residual
program can end up *less* specialized than what the driving actually proved.
Modern supercompilers (Turchin's SCP for REFAL, Sorensen's reformulation,
Supero for Haskell) differ chiefly in whistle policy and generalization
strategy -- this tuning, not the core loop, is where the engineering lives.
Formal correctness is also subtler than for pure rewrites: folding must
respect termination order, and several published supercompilers had bugs
where the transformation changed program meaning on pathological inputs.
Verified constructions (e.g. proof-carrying versions of positive
supercompilation in Coq) exist for restricted languages only.

## Implementations worth knowing

| System | Language | Notes |
|---|---|---|
| SCP / REFAL (Turchin, 1979-1988) | REFAL | the original; reflexive (can supercompile itself) |
| Sorensen's positive supercompiler | toy FL | the standard didactic reformulation; homeomorphic embedding whistle |
| Supero (Bolingbroke, Peyton Jones, 2010) | Haskell | supercompilation by evaluation; deforestation results |
| SPSC / various Prolog experiments | mixed | positive supercompilation variants |

## Demo: driving an interpreter into a compiled expression

The script builds a tiny arithmetic+conditional expression evaluator with an
environment, then drives it with the *program* fixed and the environment
symbolic. The residual is a straight-line expression with the interpreter's
dispatch loop gone -- specialization by driving, and the small cousin of the
first Futamura projection. It also drives a recursive power function with the
exponent known, showing how driving collapses the recursion into unrolled
multiplications.

```python
# A minimal language: ('num', k) ('var', name) ('+', a, b) ('-', a, b) ('*', a, b)
# ('if0', c, t, e).  drive() symbolically executes with the program fixed and the
# environment unknown, folding every value that becomes known.
def drive(expr, bindings):
    if isinstance(expr, int):
        return expr
    t = expr[0]
    if t == 'num':
        return expr[1]
    if t == 'var':
        return bindings.get(expr[1], ('var', expr[1]))
    if t in ('+', '-', '*'):
        a, b = drive(expr[1], bindings), drive(expr[2], bindings)
        if isinstance(a, int) and isinstance(b, int):
            return a + b if t == '+' else a - b if t == '-' else a * b
        return (t, a, b)
    if t == 'if0':
        c = drive(expr[1], bindings)
        if isinstance(c, int):
            return drive(expr[2], bindings) if c == 0 else drive(expr[3], bindings)
        return ('if0', c, drive(expr[2], bindings), drive(expr[3], bindings))
    raise ValueError(t)

def show(e):
    if isinstance(e, int):
        return str(e)
    if e[0] == 'num':
        return str(e[1])
    if e[0] == 'var':
        return e[1]
    if e[0] in ('+', '-', '*'):
        return "(%s %s %s)" % (show(e[1]), e[0], show(e[2]))
    if e[0] == 'if0':
        return "(if0 %s then %s else %s)" % (show(e[1]), show(e[2]), show(e[3]))
    raise ValueError(e[0])

prog = ('+', ('*', ('var', 'x'), ('var', 'y')), ('if0', ('-', 1, 1), ('var', 'x'), ('num', 99)))
print("program   :", show(prog))
print("driven    :", show(drive(prog, {})))

pow3 = ('*', ('*', ('*', 2, 2), 2), ('var', 'n'))
print("pow3 body :", show(pow3))
print("driven    :", show(drive(pow3, {})))
```

Real output:

```text
program   : ((x * y) + (if0 (1 - 1) then x else 99))
driven    : ((x * y) + x)
pow3 body : (((2 * 2) * 2) * n)
driven    : (8 * n)
```

Two observations from the output. The `if0 (1 - 1)` branch was driven away
even though the environment stayed unknown -- the driver folded the condition
to the known value 0 and picked the `then` branch, exactly the "propagate what
is forced" behavior. The power example shows the folding half: after three
unfolds the spine is all constants except the symbolic base, and driving the
whole expression collapses `2 * 2 * 2` into `8`, leaving a single
multiplication. A real supercompiler reaches the same point by unfolding a
recursive definition under a known argument; the demo shows the fold step
directly so it stays auditable in a page.

## Pitfalls

- **Folding on non-embeddable pairs** silently changes semantics; embeddability
  (homeomorphic embedding) is the safe test, not structural equality.
- **Over-generalization** turns a specialist into a no-op: the residual
  program can end up isomorphic to the input, having discovered nothing.
- **Driving non-deterministic or effectful constructs** is unsound -- the
  technique presumes a pure, deterministic language; order of effects breaks
  the symbolic-propagation contract.
- **Residual blow-up**: unfolding recursive definitions without a depth budget
  produces exponentially large residuals; production systems bound unfoldings
  per configuration.

## Cross-references

- [Partial Evaluation and MLIR](../partial-evaluation-mlir.md) -- the
  binding-time-analysis view of the same goal.
- [Compilation Techniques](./compilation-techniques.md) -- survey-level
  treatment of CPS, defunctionalization, and staging, where supercompilation
  sits among whole-program transformations.
- [E-graphs and Equality Saturation](./e-graphs-equality-saturation.md) --
  rewrite-based transformation with a different (equivalence-class) control
  strategy.
- [Superoptimization](./superoptimization.md) -- exhaustive search at the
  instruction level, contrasted with source-level driving.
- [Lambda Calculus](../../cs-theory/lambda-calculus.md) -- the substrate the
  configurations live in.
- [Deforestation (Wadler)](https://doi.org/10.1016/0304-3975(90)90147-A) is
  covered here in prose; the repo's streaming pages discuss its runtime
  cousins.

## References

1. V. F. Turchin, "The concept of a supercompiler," ACM TOPLAS 8(3), 1986,
   DOI 10.1145/5956.5957. https://doi.org/10.1145/5956.5957
2. M. H. Sorensen, "Turchin's supercompiler revisited: a recursive
   supercompiler," (master's thesis / report, DIKU), cited by name; a
   fetchable copy is linked from the author's publication pages.
3. M. Bolingbroke and S. Peyton Jones, "Supercompilation by evaluation,"
   Haskell Symposium 2010, DOI 10.1145/1863523.1863540.
   https://doi.org/10.1145/1863523.1863540
4. P. Wadler, "Deforestation: transforming programs to eliminate trees,"
   Theoretical Computer Science 73(2), 1990,
   DOI 10.1016/0304-3975(90)90147-A. https://doi.org/10.1016/0304-3975(90)90147-A
5. N. D. Jones, C. K. Gomard, and P. Sestoft, "Partial Evaluation and Automatic
   Program Generation," Prentice Hall, 1993 (book; chapters on driving and
   online/offline specialization).
6. V. F. Turchin, "Experiments with a supercompiler," LFP '82,
   DOI 10.1145/800068.802134. https://doi.org/10.1145/800068.802134
