# Linear Types

Most type systems care about *what* values are. Linear types additionally care about *how often* a value is used. The core rule is shockingly simple: **a value of linear type must be used exactly once**. From that rule follows a remarkable family of guarantees — memory can be freed without a GC (no aliases exist), file handles are closed exactly once, locks are released, cryptographic keys are zeroed, and protocol channels are not duplicated.

Linear logic (Girard 1987) introduced the idea in proof theory; Wadler 1990 brought it into programming languages with the slogan "Linear types can change the world!" Since then it has surfaced in production in Rust (as affine types plus borrowing), in Haskell (Linear Haskell, GHC 9), in Clean, and in academic languages like Granule and Idris 2 (via Quantitative Type Theory).

## The `!` (exponential) modality

Linear logic distinguishes linear propositions from unrestricted ones using the **exponential modality `!`** (pronounced "bang"). A proposition `!A` can be used any number of times; `A` (without the bang) must be used exactly once.

In linear type theory, this shows up as a typing rule for two distinct arrows:

```
  Γ, x : A ⊢ e : B         (x used once in e)
  ──────────────────────────────────────── (⊸-intro, linear)
  Γ ⊢ (λx. e) : A ⊸ B

  Γ, x : !A ⊢ e : B         (x used 0+ times via dereliction)
  ──────────────────────────────────────── (→-intro, unrestricted)
  Γ ⊢ (λx. e) : A → B
```

The two arrows are different types. `A ⊸ B` ("lolli") is a **linear function** — it must be called once, with an argument used exactly once. `A → B` is a regular function — call it as many times as you like.

The exponential `!` is what lets us embed ordinary functional programming inside linear logic. `!A` marks the "shared" part of the world — typically anything that is garbage-collected (immutable heap values, functions, integers). Without it, you could not write `map : (a → b) → [a] → [b]`, because the function would need to be used once per list element. With `!`, the function argument has type `!(a → b)` and is reusable.

```
              Linear             Affine             Relevant        Unrestricted
use count:    exactly 1           0 or 1             1 or more       any
arrow:        A ⊸ B               (Rust: A -> B)     (no standard)   A → B
modality:     (no bang)           (no bang)           (no bang)       !A
languages:    Granule, Idris 2    Rust, Linear HS     (research)      Haskell, ML
```

## The linear function: must use exactly once

The defining constraint: if a variable `x : A` is linear (multiplicity 1), the body of the abstraction must reference `x` exactly once.

```haskell
-- Linear Haskell (GHC 9+). The ⊸ symbol is the linear arrow.
id :: a ⊸ a
id x = x                  -- OK: x used exactly once

const :: a -> b ⊸ b        -- non-linear in first arg, linear in second
const _ y = y            -- OK: y linear, the underscore is unrestricted

dup :: a ⊸ (a, a)          -- REJECTED by the type checker
dup x = (x, x)           -- x used twice
```

The third function is the kind of thing you constantly want in functional programming and is structurally impossible in linear land. To share a value you have to either (a) make it unrestricted with `!`, or (b) duplicate it via a primitive that consumes a resource token — e.g., `dup : Stateful a ⊸ (a, a)` where the state token is consumed in the duplication.

## Affine vs linear vs relevant

Three flavors of "use constraint":

```
  Linear:     use exactly once       -- the strongest; enables deterministic cleanup
  Affine:     use at most once        -- weaker; allows dropping
  Relevant:   use at least once       -- weaker; allows duplication
  Unrestricted: use any number of times
```

Linear implies both relevant and affine. Affine alone (Rust) gives you ownership transfer but not the *requirement* that you must consume. Most real systems choose affine because it is ergonomic — you can write `let _ = expensive_thing();` and the language still lets the value be dropped (with its destructor run).

The "use at least once" (relevant) variant is rare in production. Idris 2's QTT with multiplicity `0` vs `1` vs `ω` gets you both linear and affine by combining `1` with explicit dropping, but a *requirement* to use is hard to make ergonomic because you often want to abandon work.

```
                       used 0  used 1  used 2+
   Linear  (Bang-free)  ✗       ✓        ✗
   Affine              ✓       ✓        ✗
   Relevant            ✗       ✓        ✓
   Unrestricted        ✓       ✓        ✓
```

## Production use: Rust ownership as affine plus borrowing

Rust is the dominant industrial linearity-flavored system. The core rules:

1. Each value has exactly one **owner** at a time.
2. When the owner goes out of scope, the value is dropped (`Drop::drop` is called).
3. You can **move** ownership (transfer it to another binding); after that, the old binding is statically dead.
4. You can **borrow** via `&T` (shared, any number of readers) or `&mut T` (unique, one writer).

```rust
fn consume(s: String) -> usize { s.len() }

let s = String::from("hello");
let n = consume(s);
// println!("{}", s);  // ERROR: borrow of moved value: `s`
```

Rust's ownership is **affine, not linear**: you can drop a value without using it (`let _ = String::new();` compiles, and the destructor runs). The borrow checker enforces an alias-vs-mutation discipline:

```rust
let mut v = vec![1, 2, 3];
let r = &v[0];          // shared borrow
v.push(4);              // ERROR: cannot borrow `v` as mutable because it's also borrowed
println!("{}", r);
```

The key invariant: **a value either has one mutable reference or any number of shared references, never both at once.** This is the affine-strength version of "linear function arguments are not aliased."

Why affine and not strictly linear? Because forcing the user to consume every value would be awful ergonomically — you would have to explicitly `drop()` every error you didn't inspect, every intermediate buffer you didn't read, every lock you acquired. Affine plus borrow is the practical sweet spot: the compiler inserts the drops for you, and you only have to think about ownership transfer at API boundaries.

## Linear Haskell

GHC 9 introduced Linear Haskell (Bernardy et al. 2018). The proposal: add `a ⊸ b` as a primitive arrow type with multiplicity-1 semantics. The motivation is not memory (Haskell has a fine GC) but **safe in-place mutation**:

```haskell
-- A mutable array with a linear type — the only way to mutate it is linearly,
-- so the compiler can prove no other thread is reading it.
data UArray a = ...

read  :: UArray a ⊸ (a, UArray a)
write :: UArray a ⊸ a ⊸ UArray a
```

Because the array is linear, every read *consumes* the array and produces a new one; you cannot keep the old reference. This makes the array **safe to mutate in place** — no versioning, no copy-on-write, just destructive updates that the type system proves are invisible to the rest of the program.

The killer application for Linear Haskell is **safe zero-copy FFI**: a linear type proves that a `ByteArray#` passed to C is not aliased on the Haskell side, so C can mutate it without invalidating any Haskell-visible copy. This is exactly the kind of guarantee ordinary Haskell cannot give you, and it lets you write verified-FFI bindings to high-throughput C crypto libraries without a GC barrier.

## Comparison: linear types vs ownership/borrowing

| Aspect | Linear types (theory) | Rust (affine + borrow) |
|--------|------------------------|------------------------|
| Use count constraint | exactly 1 | 0 or 1 (affine) |
| Aliasing model | none | explicit via `&`/`&mut` |
| Memory strategy | region-based free, no GC | deterministic destructors |
| Destructors | must run on every linear value | runs on scope exit |
| Inference | decidable (multiplicity) | decidable (NLL, polonius) |
| Escape valves | `!` modality | `Rc`/`Arc`/`UnsafeCell` |

The fundamental difference: linear types forbid **aliasing**, Rust forbids **aliasing with mutation**. You can have as many `&T` shared borrows as you like; you just cannot mutate through them. That is a weaker invariant than "no aliases at all," but it is enough for memory safety and it is ergonomic.

The cost of Rust's relaxation is the need for the borrow checker to do non-trivial lifetime analysis — which is why Rust's borrow errors are notoriously hard for newcomers. The "non-lexical lifetimes" (NLL) refactor in 2018 and the experimental `polonius` algorithm that replaces it make the checker more permissive, but the fundamental analysis is still about *regions* and *control flow*, not just multiplicity.

Linear types avoid that complexity by forbidding aliases outright, at the cost of needing `!` everywhere you want to share. You trade one annoying annotation (`!`) for never having to think about lifetimes — a trade that has not yet won in industry but that Idris 2's QTT makes attractive by integrating it into the dependent framework.

## Why it matters: a small example

Consider a protocol where you have to send a request and then receive a reply on the same channel:

```
-- Linear: the channel is consumed by each operation.
request :: Channel ⊸ Request ⊸ (Channel, Reply)
```

You cannot accidentally use the channel twice (double-send) or forget to use it (the channel is leaked, the type error fires). Session types — the topic of the next chapter — are essentially linear types for channels; the linear constraint is what makes them statically safe.

A second example: a database handle that must be released exactly once.

```haskell
{-@ Linear Haskell: handle is linear -}
withDb :: (Db ⊸ IO a) ⊸ IO a
withDb action = bracket acquire release action
-- The continuation takes a linear Db. The library author
-- has statically ruled out "use after close" and "double close."
```

The `bracket` pattern's correctness traditionally rests on a runtime invariant (the release runs exactly once); with a linear type, it rests on the type system.

## Related: uniqueness types

Clean uses **uniqueness types**, a close cousin of linear types. The rule is inverted: a uniqueness-typed value can have at most one reference at a time, but use count is unconstrained. This is the "no aliasing" half of linear typing without the "use exactly once" half. The result is that uniqueness types give you safe in-place mutation (no other reader exists) without forcing explicit consumption — Clean uses this for high-performance graph rewriting and I/O.

Rust's `&mut T` is essentially uniqueness typing in affine clothing: the borrow is unique, you can use it as often as you like, but only one writer is permitted.

## Conclusion

Linear types are the type-theoretic answer to resource management. They generalize region-based memory, file-handle safety, lock safety, and channel safety into one unifying framework. Production use is dominated by Rust's affine-borrowed variant; Haskell's Linear Haskell is the research-y generalization; Idris 2's QTT shows that linear types can be a special case of dependent types with quantities.

The tradeoff: linear typing requires the programmer (or the inference engine) to track multiplicity. For 95% of programs that is overhead that does not pay for itself — a GC plus immutable data is enough. For the 5% where it does (systems programming, verified protocols, zero-copy FFI, lock-free data structures), it is the only static guarantee that actually works.

## References

- J.-Y. Girard, *Linear Logic* (1987) — https://www.sciencedirect.com/science/article/pii/0304397587900457
- P. Wadler, *Linear Types Can Change the World!* (1990) — https://homepages.inf.ed.ac.uk/wadler/papers/linear/linear.pdf
- J.-P. Bernardy et al., *Linear Haskell: Practical Linearity in the Presence of IO and Concurrency* (2018) — https://arxiv.org/abs/1805.07804
- The Linear Haskell GHC proposal — https://github.com/ghc-proposals/ghc-proposals/blob/master/proposals/0111-linear-types.rst
- The Rust Book, Chapter 4 (Ownership) — https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html
- P. Wadler, *A Taste of Linear Logic* (tutorial) — https://homepages.inf.ed.ac.uk/wadler/papers/taste/taste.pdf
- R. de Vries, E. Boucher, *Uniqueness Typing for Clean* (Clean language documentation) — https://clean.cs.ru.nl/Clean
