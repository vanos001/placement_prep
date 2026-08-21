# Communicating Sequential Processes (CSP)

## Overview

Communicating Sequential Processes (CSP) is a calculus for concurrent
systems proposed by C. A. R. Hoare in 1978 and developed into a book
in 1985. Where the [actor model](./actor-model-deep.md) takes the
asynchronous mailbox as primitive, CSP takes the **synchronous channel
rendezvous** as primitive: a send blocks until a matching receive is ready
and vice versa. The two processes then exchange a value and both proceed.
This single design choice has consequences that ripple through the whole
calculus — and through every language that has borrowed from it,
including occam (1983), Newsqueak, Limbo, and Go.

This page covers the Hoare calculus: the channel/event primitive, the
prefix operator (`a -> P`), choice (`|`), parallel composition (`|||`),
the trace semantics, the Go channel as a CSP-inspired descendant, the
comparison to the actor model, and the occam language where CSP first
became a programming language.

## The Hoare calculus

### Events and processes

The fundamental entity in CSP is an **event** — a synchronisation point,
optionally carrying a value. A process is a behaviour over events. The
alphabet of a process is the set of events it can engage in. The two
most basic processes are:

```
   STOP    the process that engages in no event (deadlock)
   SKIP    the process that engages in one event (terminate) and stops
```

Every other process is built from a small algebra.

### Prefix: `a -> P`

The prefix operator `a -> P` denotes the process that is first willing to
engage in `a`, and after `a` has occurred, behaves like `P`. This is the
sequential combinator. In Go it is the channel send followed by the next
statement.

```
   cash -> coffee -> STOP

   is the process that
       1. waits to perform `cash`
       2. then waits to perform `coffee`
       3. then deadlocks
```

The send on an unbuffered Go channel is the canonical example:

```go
ch := make(chan int)   // unbuffered, synchronous
ch <- 42               // blocks here until a reader is ready
fmt.Println("sent")    // not reached until the rendezvous completes
```

The send and the receive together form a single atomic event — exactly
the CSP rendezvous. A buffered channel (`make(chan int, N)`) is *N*
synchronous rendezvous in a queue: each send blocks only when the queue
is full, each receive blocks only when it is empty.

### Choice: `|`

The external choice `P | Q` is a process willing to engage in any event
that either `P` or `Q` would engage in initially. Once an event from
`P` occurs, `P`'s continuation is selected and `Q` is discarded, and
vice versa. The environment chooses; the process is passive.

```
   vending =   (coin -> chocolate -> vending)
             | (coin -> toffee    -> vending)
```

The buyer decides whether the chocolate or toffee arm of the vending
machine fires by their next action. Internally to the process, both
arms look identical up to the chocolate/toffee step.

There is also an internal choice `P |~| Q` where the process picks; the
environment must be ready for whatever was chosen. Go does not have a
first-class choice operator, but it has the canonical pattern using
`select`:

```go
select {
case msg := <-incoming:
    handle(msg)
case <-time.After(timeout):
    return
}
```

The Go runtime chooses which ready case to fire; if both are ready, the
choice is uniform random. CSP's `|` would have the environment choose
deterministically; the Go `select` adds nondeterminism, which is
intentional because the runtime does not want to expose scheduler
decisions.

### Parallel: `|||`

The alphabetised parallel operator `P [A || B] Q` runs `P` and `Q`
concurrently, requiring them to synchronise on events in `A ∩ B` and
allowing them to proceed independently on events in their private
alphabets. The general parallel operator `|||` interleaves two
processes that share no events.

```
   P = a -> b -> STOP
   Q = c -> d -> STOP
   P ||| Q  interleaves; one valid trace: a c b d
                          another:    c a d b
   P [b || d] Q  forced synchronisation on {b,d}
```

This is the heart of CSP's compositionality. The trace semantics below
depends on it.

### Hiding: `P \ A`

`P \ A` behaves like `P` but the events in `A` become internal: they
still happen, but the environment cannot observe or synchronize on them.
Hiding turns observable events into τ-steps (silent moves). Hiding is
what makes a complex subsystem appear as a single event from the
outside; it is the abstraction operator of the calculus.

### Recursion

CSP processes are recursive equations: `P = a -> P` is the infinite
process that does `a` forever. The least-fixed-point semantics gives
this a meaning: `P` is the limit of the chain
`STOP ⊆ a -> STOP ⊆ a -> a -> STOP ⊆ ...`. Recursion plus prefix is
enough to express any finite-state behaviour.

## Trace semantics

The meaning of a CSP process is the set of finite traces it can perform
— the sequences of observable events that the environment can lead it
through. `traces(STOP) = { <> }`. `traces(a -> P) = { <> } ∪ { <a>^t : t
∈ traces(P) }`. Two processes are **trace-equivalent** iff their trace
sets are equal.

```
   P = a -> b -> STOP         traces(P) = { <>, <a>, <a,b> }
   Q = a -> b -> STOP         traces(Q) = same; P and Q are equivalent
   R = a -> STOP | a -> c -> STOP   traces(R) = { <>, <a>, <a,b>, <a,c> }
```

Traces capture safety — what can happen — but not liveness. For liveness
CSP adds the **failures** model (pairs of `(trace, refusal)` — what the
process can refuse to do after a trace) and the **failures-divergences**
model, which also records infinite internal computation (divergence).
Roscoe's *Theory and Practice of Concurrency* is the canonical reference
for the failures-divergences model and the refinement ordering that
underpins it.

The payoff is compositional refinement: you write an abstract
specification `SPEC` and a concrete implementation `IMPL`, and you prove
`SPEC [T= IMPL` (IMPL refines SPEC) by showing `traces(IMPL) ⊆
traces(SPEC)`. This is the basis of FDR, the CSP refinement checker,
which has been used to find bugs in real-world protocols including
TCP, the IEEE 1355 bus, and parts of the PCIe standard.

## The Go channel as CSP-inspired

Go is the most widely deployed CSP descendant. The
[Go channels documentation](https://go.dev/ref/spec#Channel_types)
defines channels as typed conduits synchronising goroutines, and the
[Pike CSP blog post](https://go.dev/blog/pipelines) (referenced in Go's
concurrency FAQ) explicitly cites Hoare's work. The mapping is:

```
   CSP concept                Go construct
   ------------               -----------
   event                      channel send/receive
   a -> P                     ch <- v; P
   P | Q                      select with multiple cases
   P ||| Q                    go func() { P }(); go func() { Q }()
   hiding P \ A               the body of a goroutine (private channel)
   recursion                  for { ... } / recursive goroutine
   STOP                       select {}  (no cases, blocks forever)
   SKIP                       return
```

Three things Go departs from CSP on:

1. **Nondeterministic choice.** A `select` with multiple ready cases
   picks uniformly at random; CSP `|` is deterministic, chosen by the
   environment. Go's choice is internal, not external.
2. **Buffered channels.** A buffered channel `make(chan int, N)` is `N`
   synchronous rendezvous buffered. Hoare's CSP has unbuffered channels
   in the original calculus; buffering appears as the *parallel
   composition with an intermediate process* that has internal storage.
3. **Closing channels.** `close(ch)` makes future receives complete
   immediately with the zero value; this is a Go-specific extension to
   the calculus with no direct CSP analogue, useful for fan-out
   teardown.

The canonical CSP pattern in Go is the **pipeline**: stages connected
by channels, each stage a goroutine. The Go blog's *Go Concurrency
Patterns: Pipelines and cancellation* (referenced below) is the
canonical example. It is also where CSP shows its weakness: when stages
need to fan out to N workers, the unbuffered channel semantics give
you backpressure for free, but they make the cancellation story hard
(you need a `done` channel propagated through every stage, or
`context.Context` since Go 1.7).

## CSP vs the actor model

```
   CSP                          Actor model
   ---                          ------------
   rendezvous (sync)            mailbox (async)
   named channels               addressed actors
   anonymous receiver           explicit identity
   process identity is fluid    actor identity is persistent
   calculus defines order        only per-sender FIFO is defined
   compositional trace theory   no equivalent formal theory (yet)
```

The two models can simulate each other. A synchronous channel is a
one-slot mailbox whose send completes only on acknowledgement. An
asynchronous mailbox is a chain of `N` buffered channels whose send
returns immediately because the buffer absorbs it. The question is
which semantics the language makes the default and which the
programmer must construct.

CSP's strength is compositional reasoning. Because channels are named
and processes are anonymous, you can prove that a network of processes
refines a specification, using the failures-divergences model. CSP was
designed to be reasoned about; the actor model was designed to be
scaled. Erlang and Akka's reliability story comes from supervision, not
from a refinement proof. The trade-off shows up in production: CSP
systems (Go programs, occam programs) tend to have fewer concurrency
bugs and more subtle correctness arguments; actor systems tend to scale
farther but reason less well about interleavings.

The historical debate between Hoare and Hewitt is well documented in
Hewitt's *Actor Model of Computation* (2015) and Roscoe's *Theory and
Practice of Concurrency* (Chapter 14 of the second edition). Hewitt's
position is that the actor model is the more general substrate; Hoare's
position, sharpened by Roscoe, is that CSP's refusal to admit
asynchronous communication is what gives it compositional proofs.
Neither argument has settled the other in forty years.

## occam

occam (1983) is the programming language that transcribed CSP directly
onto the transputer, a parallel microprocessor designed at Inmos for
the UK's 1980s parallel-computing push. occam's syntax reads as CSP:

```occam
-- A vending machine in occam
PROC vending =
  WHILE TRUE
    SEQ
      coin ? ANY          -- wait for a coin
      ALT                 -- external choice
        chocolate ? ANY
          SKIP
        toffee ? ANY
          SKIP
:
```

`SEQ` is sequential composition; `ALT` is the external choice `|`;
`PAR` is the parallel composition `|||`; channels are declared with
`CHAN OF INT` and read with `?` and written with `!`. The transputer
executed occam at the silicon level — there were hardware
instructions for channel input and output, so a rendezvous was a
single-cycle handshake on a wire between two transputers. This is the
closest any production system has come to "CSP on bare metal."

The transputer failed commercially in the early 1990s, and occam died
with it, but the language design carried through to Java (the original
JCSP library by Peter Welch, an occam veteran, gives Go channels in
Java) and from there to Go. The current line of CSP descendants in
production is Go, Clojure's `core.async`, and Rust's `crossbeam-channel`
crate; each differs from CSP in the same kinds of ways Go does
(nondeterministic select, buffering as a first-class option).

## Interview questions

### What is the primitive operation in CSP?

Synchronous channel rendezvous: a send on a channel completes only when
a matching receive is ready. Both processes synchronise on the event and
exchange a value atomically.

### What is the difference between `|` and `|||`?

`|` is external choice: the environment picks which arm fires. `|||`
is parallel interleaving: the two processes run concurrently, sharing
no events, and their traces interleave. The first is a control-flow
combinator; the second is a concurrency combinator.

### What is the trace of `a -> b -> STOP`?

`{ <>, <a>, <a,b> }`. The empty trace (the process before doing
anything), the trace after `a`, and the trace after `a` then `b`. The
process cannot engage in any further event.

### How does an unbuffered Go channel relate to CSP?

It is direct syntactic sugar for a CSP event. A send `ch <- v` and a
receive `<-ch` form a single rendezvous; both block until the other is
ready, then they exchange `v` and both unblock. A buffered channel is
`N` rendezvous in a queue.

### Why does CSP compose better than the actor model?

Because channels are named, processes are anonymous, and the trace
semantics is closed under parallel composition. You can compute the
trace set of `P ||| Q` from the trace sets of `P` and `Q` alone. In the
actor model the receiver's mailbox order is not a function of the
sender's send order alone, so the compositional trace story does not
exist without further restriction.

## Cross-references

- [Actor Model Deep Dive](./actor-model-deep.md) — the asynchronous
  alternative to CSP and the historical Hoare-vs-Hewitt debate
- [Go Channels and Goroutines](./go-channels.md) — the most widely
  deployed CSP descendant, with departures documented
- [Transactional Memory](./software-transactional-memory.md) —
  composability without rendezvous, via optimistic execution
- [Coroutines](./coroutines.md) — the cooperative scheduling layer
  underneath Go's goroutines and Kotlin's `select`
- [Producer-Consumer](./producer-consumer.md) — the simplest channel
  pipeline
- [Deadlock Detection](./deadlock-detection.md) — the Coffman
  conditions, applied to CSP networks
- [Memory Model](./memory-model.md) — happens-before for channels in
  Go, Java, C++, and Rust

## References

- C. A. R. Hoare. *Communicating Sequential Processes*. CACM 1978.
  <https://www.cs.cmu.edu/~crary/819-f09/Hoare78.pdf>
- C. A. R. Hoare. *Communicating Sequential Processes*. Prentice Hall,
  1985. Full text free online:
  <https://www.usingcsp.com/cspbook.pdf>
- A. W. Roscoe. *The Theory and Practice of Concurrency*. Prentice Hall
  1997; second edition 2024.
  <https://www.cs.ox.ac.uk/oucl/courses/undergrad92-93.html> and
  <https://www.cs.ox.ac.uk/people/bill.roscoe/publications/97.pdf>
- Go language specification: Channel types.
  <https://go.dev/ref/spec#Channel_types>
- Go blog: Share Memory By Communicating.
  <https://go.dev/blog/codelab-share>
- Go blog: Go Concurrency Patterns: Pipelines and cancellation.
  <https://go.dev/blog/pipelines>
- Peter H. Welch. *Process Oriented Design for MIMD Parallel
  Processing*. 1996. <https://www.cs.kent.ac.uk/pubs/1996/543/>
- Geraint Jones. *occam 2.1 Reference Manual*.
  <https://www.cs.kent.ac.uk/research/groups/sysjo/occam/>
- JCSP — Communicating Sequential Processes for Java.
  <https://www.cs.kent.ac.uk/projects/ofa/jcsp/>
