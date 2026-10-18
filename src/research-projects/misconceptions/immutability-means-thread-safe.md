# "Immutability means thread-safe"

## Overview

"Make it immutable and you can forget about thread safety" is the most
repeated concurrency advice of the last fifteen years, inherited from
genuinely great sources — *Java Concurrency in Practice* lists
immutability as the strongest form of thread safety, and Rust built a
compiler around "aliasing XOR mutability". The advice is right, and the
slogan built from it is wrong in two specific places: constructing an
immutable object does not publish it safely (the Java memory model's
final-field guarantee is conditional on `this` not escaping
construction), and "immutable" frequently turns out to mean *shallow*
immutable — a `final` reference to a mutating list, a `const` C++ object
with `mutable` fields, or a configuration object wrapped around a live
cache. This page states the claim fairly, walks the three classic
failure classes with code-shaped examples, explains what the Java memory
model does and does not promise, and identifies the regime where the
slogan is exactly right — immutable data that is safely published is
freely shareable with zero synchronization.

## The Claim, Stated Fairly

The strongest common form is: "I made the fields `final`/`const` and the
object immutable, so any number of threads can use it without locks."
The claim deserves fairness because it is, in a precise form, the
strongest statement in concurrent design: truly immutable state cannot
race, cannot deadlock, and scales linearly with readers on every
architecture. The experience behind the claim is also real — the vast
majority of "immutable" objects in production *are* used safely across
threads, because most are published through channels that happen to be
safe (static initializers, hand-off through a synchronized queue, a
join boundary). The audit question is whether the *keywords* did the
work, or whether safe publication and deep immutability quietly did it
for them — and what happens on the day one of those two invisible
preconditions is missing.

## Verdict

**Incomplete.** Immutability removes the *mutation* half of a data race;
it does not remove the *visibility* half. An object whose fields are
`final` can still be observed half-constructed by another thread if
`this` escapes during construction, a "final" collection reference can
hide a mutating list behind it, and C++ `const` is a contract about the
type system, not about memory visibility — it supplies no
synchronization at all. The correct formulation is a conjunction: *deep
immutability AND safe publication* yields lock-free shareability. The
claim is incomplete rather than false because the missing preconditions
are usually satisfied by accident: objects are typically published
through channels that establish happens-before edges, which is why the
slogan survives production — until a refactor moves construction
somewhere the edge disappears.

## Why People Believe It

The kernel of truth is the deepest one in the field: state that cannot
change cannot have a stale, torn, or interleaved *value*. Every memory
model subtlety — happens-before, store buffers, cache coherence —
exists to answer "what value does a read see after writes?", and for a
field whose value never changes, the question collapses. That is why
the best concurrency textbooks converge on immutability, why
`java.lang.String` and `Integer` are shared across every thread in
every JVM without locks, and why functional languages advertise
immutability as a concurrency strategy rather than a style.

Three props hold the belief up. First, the publication is usually
invisible: object construction and first use are typically separated by
a synchronized hand-off, a thread start/join, an executor submit, or a
static initializer — each of which establishes the happens-before edge
that makes the object visible. The developer credited the keyword; the
hand-off did the work. Second, the x86 memory model is forgiving:
total-store ordering makes most unsafely-published final fields visible
anyway, so the failure requires an ARM machine, a JIT reorder, or a
deliberately racy pattern — rare enough to feel mythical. Third, the
word "immutable" does double duty in everyday speech: developers mean
"immutable *reference*" (a `final` field), "shallow-immmutable object"
(final fields pointing at mutables), and "deeply immutable value"
(the real thing) interchangeably, and only the third is what the
thread-safety theorem is about.

What is lost is that thread safety is a property of a *relationship* —
between an object, the threads touching it, and the memory model — not
a property of a declaration. The declaration removes one party's ability
to write; it says nothing about when the other parties may read, or
what they will see.

## The Correct Formulation

| Guarantee | What it actually covers | What it does not cover |
|---|---|---|
| Java `final` field (JLS 17.5) | If the object is *properly constructed* (no `this` escape), every thread that sees the reference sees the final field's constructed value | Safe publication of the *object itself* — you still need a happens-before edge to see the reference; nothing about referenced mutable state |
| Java non-final field | Nothing across threads without synchronization | Everything — store reordering can publish a reference before its contents |
| C++ `const` | A type-system contract: this expression won't modify through this path | Visibility, ordering, or mutual exclusion; `mutable` fields and `const_cast` mutate freely; data races are undefined behavior regardless |
| Shallow immutability (`final List`) | The reference is fixed | The list's contents — `final` on the field, mutable on the object |
| Rust ownership/`Send`/`Sync` | Compile-time proof that aliases don't mutate concurrently | Runtime re-entrancy through shared resources (files, globals behind `unsafe`) |

The precise statement: an object is *effectively immutable* if its
observable state cannot change; it is *safely published* if some
happens-before edge separates full construction from concurrent
reading. Together they give lock-free sharing. The standard safe
publication idioms each supply the edge: publishing from a static
initializer, storing into a `volatile` field or `AtomicReference`,
putting into a `ConcurrentHashMap`, handing off through a
`synchronized` block or a `BlockingQueue`, or the thread start/join
protocol. Note the asymmetry that breaks the slogan: `final` fields
under JLS 17.5 are the one exception where the JMM gives partial
protection against unsafe publication — but only for fields set in the
constructor of a non-escaping `this`, which is why constructors must
never pass `this` to listeners, start threads, or register callbacks.

## Where It Breaks

**This-escape defeats the final-field guarantee.** The JMM's promise is
conditional, and the condition is written in code: `final` field values
are guaranteed visible only for objects whose constructor does not let
`this` escape. The canonical failure registers a listener inside the
constructor — `new EventSource().subscribe(handler)` where `subscribe`
stores `this` and another thread fires immediately — so the handler
thread can observe the final field's *default* value (`null`, `0`) even
though the constructor assigns it. This is not theoretical
compiler-abuse: it is a defined outcome the memory model permits, and
linters flag `this` in constructors for exactly this reason. The fix is
mechanical: finish construction, then subscribe — a factory method or
an `initialize()` step.

**Mutable state hiding behind immutable doors.** A `final
List<Rule>` configured once at startup is immutable as a reference;
every thread calling `rules.add(...)` or `Collections.sort(rules)`
mutates shared state that "immutable" was supposed to freeze. The same
trap wears nicer clothes: an "immutable" config object exposing
`getHeaders()` that returns its internal map (callers mutate it), a
`final Date` (Date is mutable), a deeply-immutable tree with one cached
lazy field filled on first read. The discipline is deep immutability:
defensive copies at the boundary, unmodifiable or persistent
collections inside, and no field whose type mutates in place. A useful
audit question: can any code path anywhere change what `equals()`
returns between two calls? If yes, the object is not thread-safe by
immutability.

**C++: `const` is not synchronization.** In C++, `const` constrains
what expressions may do through a type; it has no effect on memory
visibility or atomicity. A `const` member function may mutate `mutable`
caches (a benign-race pattern that is *not* benign in C++ — a data race
on a non-atomic `mutable` member is undefined behavior even if the
value is "logically" the same). The standard library gives one real
promise — const member functions of standard containers are safe to
call concurrently, because they do not modify the object — and that
promise is about *their* implementation, not a property `const`
transfers to your class. The C++ slogan therefore inverts: immutability
still helps (immutable data can be shared without locks), but the
`const` keyword is the weakest of the three languages' guarantees, and
`std::atomic`/mutexes still do the actual visibility work.

**When it accidentally works.** The slogan's regime is most production
code: objects are constructed before threads start, handed off through
executors and queues (every hand-off is a happens-before edge), or
published in static initializers (safe by class-initialization
semantics). On x86's strong memory ordering, even unsafely-published
final fields are *usually* visible because stores rarely reorder past
each other — so the failure needs the conjunction of a leaky
constructor, a publication without an edge, and (often) a weakly-ordered
architecture or a JIT optimization. Java's own `String.hashCode()`
shows the sanctioned version of the trick: it caches the hash lazily
without synchronization, accepting that multiple threads may compute it
and write racy values — safe because `int` writes are atomic and every
candidate value is correct. The pattern generalizes narrowly: racy
publication of a *monotonic* value is fine; racy publication of a
*composite* state is not.

## Practical Implications

- Treat immutability as two checks, not one: "can state change?" and
  "does a happens-before edge separate construction from sharing?"
  Answering only the first is how the race ships.
- Never let `this` escape a constructor: no listener registration, no
  thread starts, no calls to overridable methods. Publish via factory
  methods when wiring requires callbacks.
- Default to deep immutability at API boundaries: return unmodifiable
  or copied collections; wrap mutables (`Date` → the type system's
  immutable equivalent); freeze config objects before exposure.
- In Java, prefer `final` fields set in the constructor — it is the
  only field form with memory-model protection even under unsafe
  publication — and use `volatile`/`AtomicReference`/`ConcurrentMap`
  for the publication edge when threads pre-exist.
- In C++, `const` expresses interface intent; thread safety still
  comes from `std::atomic`, mutexes, or genuinely immutable data — and
  a `mutable` non-atomic cache in a const method is a latent UB bug.
- In interviews, the winning sentence is: "immutable *plus safely
  published* is thread-safe; the keywords alone are half of that."

## Interview Questions

### Under what conditions does the Java memory model guarantee visibility of final fields, and what breaks the guarantee?

The guarantee (JLS 17.5) holds for an object that is *properly
constructed*: `this` does not escape during construction, and fields
are assigned in the constructor. Then any thread that sees the object
reference sees the final fields' constructed values — even without a
publication edge. It breaks when `this` escapes (listener registered
in the constructor, thread started inside), letting another thread
observe default values, and it says nothing about mutable objects the
final fields reference. A strong answer names both the condition and
the shallow-immutability boundary.

### An "immutable" object exposes `getEntries()` returning its internal `ArrayList`. Why is this unsafe with concurrent readers, and what are two fixes?

The internal list is mutable shared state; a caller can add, remove,
or sort it while other threads iterate, producing `ConcurrentModificationException`
or torn reads — the `final` keyword on the field froze the reference,
not the contents. Fix one: return a defensive copy or unmodifiable
wrapper (`List.copyOf`, `Collections.unmodifiableList`) built from an
immutable source. Fix two: store an immutable/persistent collection
internally so no mutating API exists. The deeper point: immutability
must be transitive through everything the object exposes.

### Is `const` in C++ the same kind of guarantee as `final` in Java? Compare.

No. Java's `final` field participates in the memory model: it can
*create* a visibility guarantee for properly-constructed objects.
C++ `const` is a type-system contract with no memory-model effect — it
does not publish, order, or atomize anything, and `mutable` fields
plus `const_cast` allow writes through it. The closest C++ analogue to
Java's guarantee is `std::atomic` with release/acquire ordering or
`std::memory_order` discipline on immutable data publication. The
only thread-safety promise in the C++ standard library is that const
operations on standard containers may be called concurrently.

### Your service publishes a config object built at startup into a plain (non-volatile) static field, read by request threads. Is it safe?

Probably, but for reasons the code does not state, and that is the
bug-in-waiting: if the field is written before request threads start
(class initialization, or thread starts after construction), the
thread-start happens-before edge makes it safe. If a reload path
assigns the field while threads run, the publication is unsafe —
readers may see a reference before its contents, or a stale reference
indefinitely. Fix: `volatile`, `AtomicReference`, or
`ConcurrentHashMap` for the reloadable case, and document which edge
protects the startup case. This is the slogan's failure mode in
miniature: correctness by accidental ordering.

## Key Takeaways

- Thread safety via immutability is a conjunction: deep immutability
  AND safe publication. The keywords deliver the first half only.
- The JMM's final-field guarantee is conditional on no `this` escape —
  constructors that register listeners or start threads can let other
  threads see default values.
- Shallow immutability is the common impostor: a `final` reference to
  mutable contents is not immutable state, and defensive copies or
  persistent collections are the fix.
- C++ `const` is a type-system contract, not a synchronization
  mechanism; `mutable` caches in const methods are latent data races,
  and only standard-container const operations carry a concurrency
  promise.
- The slogan accidentally works because most publication paths
  (static init, executors, queues, thread starts) supply the missing
  happens-before edge — audit which edge protects your object before
  relying on it.

## Cross-References

- [Assumptions Hunt: Memory Model](../assumptions-hunt/memory-model.md)
  — the hidden assumptions in memory-model reasoning, including
  happens-before and reordering
- [Assumptions Hunt: Concurrency & Scheduling](../assumptions-hunt/concurrency-and-scheduling.md)
  — the scheduling assumptions interleaved with visibility claims
- [Misconception: Adding More Threads Always Improves Performance](./more-threads-faster.md)
  — the sibling concurrency myth this page's escape from locks feeds
- [Concurrency: Memory Model](../../concurrency/memory-model.md) —
  happens-before, publication, and the Java model in depth
- [JVM Memory Model](../../languages/java/jvm-memory-model.md) — the
  language-spec view of the guarantees cited above
- [Memory Barriers](../../os/synchronization/memory-barriers.md) — the
  hardware layer that publication idioms ultimately compile to
- [Atomic Primitives](../../concurrency/atomic-primitives.md) — the
  CAS/volatile toolbox for explicit publication edges
- [Rust Ownership](../../languages/rust/ownership.md) — the
  compile-time enforcement of aliasing-XOR-mutability, with `Send`/`Sync`

## References

- J. Gosling et al. *The Java Language Specification, Java SE 17*,
  §17.5 "final Field Semantics".
  <https://docs.oracle.com/javase/specs/jls/se17/html/jls-17.html>
- B. Goetz, T. Peierls, J. Bloch, J. Bowbeer, D. Holmes, and D. Lea.
  *Java Concurrency in Practice*. Addison-Wesley, 2006 — chapters on
  immutability and safe publication, cited by title.
- ISO/IEC 14882 (C++ Standard), *Res on data races* and [dcl.const] —
  const member functions and the standard-library thread-safety
  contract, cited by standard clause name.
- The Go Memory Model. The Go Project.
  <https://go.dev/ref/mem> — for the "happens-before is the only
  guarantee" formulation this page leans on.
- Oracle. *Class String* javadoc — the documented lazy, unsynchronized
  `hashCode` caching discussed in this page.
  <https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/String.html>
