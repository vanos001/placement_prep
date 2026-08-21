# Actor Model Deep Dive

## Overview

The actor model is a mathematical model of concurrent computation in which the
universal primitive is an **actor**: an entity that has a mailbox, that can
send asynchronous messages to other actors, that can spawn new actors, and
that can designate behaviour to be used for the *next* message it receives.
There is no shared memory, no locks, no condition variables — only messages
and message handlers. The model was defined by Carl Hewitt and collaborators
in 1973, predating both Communicating Sequential Processes (1978) and the
widespread deployment of threads with shared state. Erlang (1986), Akka
(2009) on the JVM, and Pony (2015) are the three production-grade systems
that take the model seriously enough that an interview question about "actor
model" usually means "tell me how these systems differ from threads+locks".

This page covers the Hewitt actor as a primitive, the message-delivery
semantics (at-most-once, no shared state), the mailbox as a FIFO queue,
location transparency, the implementations, and the actor-versus-CSP
debate that interviewers keep asking about.

## The Hewitt actor (1973)

In the 1973 paper *A Universal Modular Actor Formalism for Artificial
Intelligence*, Hewitt, Bishop, and Steiger defined an actor as an entity
that processes one message at a time and, in response, can perform exactly
three kinds of action:

```
                    +-----------------------------------------+
                    |             Actor A (state)             |
                    |                                         |
   send m1 to A  -> |  mailbox: [ m1 ]                        |
                    |                                         |
                    |  on message m1, perform:                |
                    |    1. send messages to known addresses   |
                    |    2. spawn new actors                  |
                    |    3. designate behaviour for next msg   |
                    +-----------------------------------------+
```

1. **Send** a finite number of messages to other actors (or itself).
2. **Spawn** a finite number of new actors.
3. **Become** a new behaviour that will be used to process the *next*
   message to arrive. This is the only way an actor's state changes.

Three things fall out of this definition that differ from
threads-with-locks:

- **No shared state.** State lives inside the actor; the only way to
  observe or mutate it is to send the actor a message.
- **Single-threaded processing.** An actor handles one message at a time.
  There is no concurrent access to its internal state and therefore no
  need for internal locks.
- **Pipelined, fair dispatch.** Messages arrive in a mailbox and are
  dispatched in arrival order (modulo fairness guarantees). The actor
  model requires that messages sent to the same actor be delivered in
  the order they were sent, *but only when sent from the same source*.

The "become" operation is the heart of actor state. A counter actor that
holds the integer `n` is not a struct with a field; it is a closure over
`n` whose behaviour, when invoked with `Inc`, is to *become* a closure
over `n+1`. This is why actor state is easy to reason about: it is
immutable from the outside and rebuilt one message at a time.

## Message-passing semantics

### At-most-once delivery

Actor semantics mandate **at-most-once delivery**: a message is either
delivered exactly once or not at all. There is no duplicate delivery and
no inherent guarantee of delivery. The model deliberately punts on
reliability: if you need *exactly-once* with a remote actor, you build it
on top with acknowledgements, sequence numbers, and idempotent receivers
(i.e. you build at-least-once + deduplication, which is what every
exactly-once system is under the hood).

This is the same trade-off TCP makes for the network layer, and for the
same reason: the only way to get exactly-once delivery over an unreliable
medium is to make the receiver remember what it has already seen, which
costs unbounded state if the sender can crash and retransmit forever.

### No shared state

Two actors share nothing but the addresses they hold for each other.
Concretely, in Akka this means an `ActorRef` is the only handle you have
to another actor; you cannot read its fields. In Erlang this is enforced
by the runtime — processes do not share heaps, so the abstraction is the
implementation. In Pony the type system partitions the heap by isolation
mode (`iso`, `val`, `tag`) so that the compiler can statically prove no
actor reads another actor's mutable storage.

```
        +----------+                       +----------+
        | Actor P  |   ---- msg {x} --->   | Actor Q  |
        | state:p  |   ---- msg {y} --->   | state:q  |
        +----------+                       +----------+
              |                                  |
              v                                  v
        only P reads p,                   only Q reads q,
        only P mutates p                  only Q mutates q

        The only thing crossing the boundary is an immutable message.
        No lock, no mutex, no atomic can live here.
```

### Order: per-pair FIFO, not global

If actor `A` sends `m1` then `m2` to actor `B`, `B` observes `m1` before
`m2`. This is the per-pair FIFO guarantee. But if `A` and `C` both send
to `B`, there is *no defined interleaving* between `A`'s messages and
`C`'s messages. The classic interview trap: in Akka, if `A` sends
`Init` then `Work`, and `B` receives `Work` before `Init` from two
different senders, that is legal; from one sender it is a bug. Erlang
makes the same guarantee. The implication is that any state-machine
initialization pattern needs to be done from a single sender or use an
explicit barrier.

## The mailbox: a FIFO queue

The mailbox is a bounded or unbounded FIFO queue of pending messages. The
runtime pulls messages one at a time and invokes the actor's behaviour on
each. Bounded mailboxes provide backpressure; unbounded mailboxes can
OOM a node under sustained write load, which is the most common production
failure mode in actor systems.

```
   producers                     mailbox (FIFO)              consumer
   ---------                     --------------              --------
                                                          +---------+
   actor A --msg1--->    [msg3][msg2][msg1]   --pop--->    | Actor X |
   actor B --msg2--->            ^                          | running |
   actor C --msg3--->            |                          +---------+
                          (back: enqueue)
   throughput limited by the rate at which X dispatches one msg at a time
```

Real implementations tune the queue: Akka uses a lock-free multi-producer
single-consumer queue (essentially an `ArrayBlockingQueue`-style structure
with `StampedLock` fallbacks for the dispatcher), while Erlang's BEAM
uses per-process heap messages stored in a linked list and consumed in
O(1) per receive. Pony's mailbox is a lock-free MPSC queue because the
language's GC requires provably single-consumer access for the actor's
heap.

When the mailbox fills, three policies are common: **drop** (Akka's
`Drop` bounded mailbox), **block the sender** (Erlang's send to a full
queue blocks the caller, which forces synchronous backpressure), or
**fail the actor** (Akka's `Fail` strategy — kill the actor and let the
supervisor restart it). Each has a cost: drop is silent data loss,
block can deadlock the system if the actor is itself trying to send to a
full mailbox, and fail makes the system more brittle unless paired with
supervision.

## Location transparency

A central claim of the actor model, explicit in Akka's design, is
**location transparency**: the address you hold (`ActorRef` in Akka,
`pid` in Erlang) does not tell you whether the target actor lives in
your process, on another process on the same host, or on a host across
the ocean. The same `tell` call works for all three.

```
              local dispatch
   tell(target, msg)  ----->  [dispatcher pulls from mailbox, runs behaviour]

              remote dispatch (Akka Classic / Cluster Sharding)
   tell(target, msg)  ----->  [serialize msg, ship over Aeron/TCP,
                                target node receives, deserializes,
                                enqueues in target's local mailbox]
```

This is attractive in theory and costs you something specific in
practice: every message must be serializable, every message crosses a
boundary that is on the failure path, and the abstraction hides a
network round-trip behind a function call. Erlang's runtime makes this
work transparently with binary term format (ETF) over TCP; Akka needs
you to configure a serializer (Protobuf, Jackson, custom) and a transport
(Artery over Aeron or TCP). Pony does *not* ship native location
transparency — Pony actors are in-process only — and this is a deliberate
choice to avoid paying the serialization tax.

The interview answer is: location transparency lets you write code that
scales from one process to a cluster without source changes, but it
makes latency invisible, hides the failure modes of distributed systems
behind local-looking calls, and forces every message to be serializable.
It is a useful tool for systems that already need distribution (Erlang
for telephony, Akka for event-sourced back ends) and a liability for
systems that do not.

## Implementations

### Erlang (BEAM)

Erlang actors are called *processes* and are preemptively scheduled across
scheduler threads. Each process has its own heap and its own mailbox;
the runtime guarantees that a process crashing does not corrupt another
process. Joe Armstrong's thesis *Making Reliable Distributed Systems in
the Erlang Style* lays out the design that produced the legendary "nine
nines" availability numbers for Ericsson's AXD301 ATM switch. Supervision
trees, `let it crash`, and `monitor`/`link` primitives are the load-bearing
parts of the Erlang style — the actor model is the substrate on which
the reliability story is built.

```erlang
%% A counter actor in Erlang
-module(counter).
-export([start/0, loop/1]).

start() -> spawn(?MODULE, loop, [0]).

loop(N) ->
    receive
        inc       -> loop(N + 1);
        {get, From} -> From ! N, loop(N);
        stop      -> ok
    end.
```

### Akka (JVM)

Akka ports the Erlang model to the JVM. Actors are JVM objects
encapsulated in `ActorRef`s; dispatchers (the `ExecutionContext` of the
actor system) multiplex them onto thread pools. The Typed Actor API
(introduced in Akka 2.6) gives you a typed `ActorRef[T]` instead of the
classic untyped `Any => Unit` receive, which closes the gap with Pony and
with Erlang's dialyzer.

```scala
// Akka Typed counter
import akka.actor.typed.*
import akka.actor.typed.scaladsl.Behaviors

object Counter:
  sealed trait Command
  case object Inc extends Command
  case class Get(replyTo: ActorRef[Int]) extends Command

  val apply: Behavior[Command] = Behaviors.setup { ctx =>
    def loop(n: Int): Behavior[Command] =
      Behaviors.receiveMessage {
        case Inc       => loop(n + 1)
        case Get(r)    => r ! n; loop(n)
      }
    loop(0)
  }
```

Akka Cluster, Cluster Sharding, and the Akka Persistence journal turn the
local actor abstraction into a distributed, event-sourced system. The
trade-off is complexity: the typed API surface, the persistence
protocol, and the cluster membership rules all need to be learned.

### Pony

Pony is the strictest implementation of the model: it bakes actor
semantics into the type system. An actor is a syntax-level construct
with its own heap; the type system's reference capabilities
(`iso`/`val`/`tag`/`ref`/`box`) prove at compile time that no mutable
storage is shared between actors. There is no runtime serializer
because the language guarantees no alias crosses actor boundaries.
Pony's selling point is "no data races, no runtime errors, fast" —
the actor model is the means by which the no-data-races claim is
discharged without a garbage collector's stop-the-world.

## Actor vs CSP

The interview question that comes up: what is the difference between the
actor model and Communicating Sequential Processes (see
[the CSP page](./csp-model.md))?

```
   Actor model                          CSP
   ------------                         --------
   Async mailbox, decoupled send        Synchronous rendezvous
   Sender doesn't block                 Both sides block until handshake
   Anonymous receiver, addressed       Named channels, not addressed
   No inherent ordering across senders  Order defined by the calculus
```

- In CSP, a send `c!v` blocks until a matching receive `c?x` happens. This
  is **rendezvous** semantics. The Go runtime's *unbuffered* channels are
  the most widely deployed CSP in the world.
- In the actor model, a send returns immediately; the receiver's mailbox
  grows. This is **asynchronous** semantics. Erlang and Akka are async by
  default; Pony's send is also non-blocking.

Both can simulate the other: a synchronous channel is a one-slot
mailbox with an acknowledgement; an asynchronous mailbox is a chain of
buffered channels. The difference is which semantics is the default and
which is constructed. The debate — see Hewitt's "Actor Model of
Computation: Scalable Robust Information Systems" and Roscoe's *Theory
and Practice of Concurrency* — has been running for forty years and
hinges on whether you want the language to expose the blocking point
(CSP) or hide it (actor). In practice, the actor model wins when you
need distribution and supervision; CSP wins when you want static
compositional reasoning about a fixed pipeline of stages.

## Actor vs threads+locks

```
                Threads + locks             Actors
  unit          thread (kernel-scheduled)   actor (runtime-scheduled)
  state         shared, mutated under locks private, only this actor sees it
  communication read & write shared memory   send immutable messages
  failure        partial state corruption    whole actor crashes, supervised restart
  scaling        bounded by contention       bounded by message throughput
  composability  low — lock ordering leak    high — actors compose by composition
  determinism    none without heroic effort   message order is local, still racy
  debugging      hard (data races, deadlocks) hard (message reordering, lost msgs)
```

The actor model's pitch is composability: two actors that work in
isolation compose by sending messages, and there is no global lock order
to discover. The pitch of threads+locks is raw speed: a mutex has lower
overhead than a message round-trip, and shared state in a single cache
line is unbeatable for hot paths. The actor model is the right default
when the system is distributed, when supervision and fault-tolerance
matter more than per-call latency, and when the domain is naturally
event-driven. Threads+locks remain the right default for compute-bound
kernels and for any code where a 50 ns critical section is cheaper than a
1 µs mailbox enqueue.

## Interview questions

### What are the three actions an actor can take on receiving a message?

Send a finite number of messages to known actors, spawn a finite number
of new actors, and become a new behaviour for the next message. The
third is the only way an actor's state changes.

### Does the actor model guarantee message delivery?

No. The model guarantees at-most-once delivery: a message is delivered
zero or one times, never twice. Building exactly-once requires
acknowledgements and idempotent receivers on top of the model.

### What ordering does the actor model guarantee?

Per-sender FIFO ordering on a per-recipient basis. If `A` sends `m1`
then `m2` to `B`, `B` observes `m1` before `m2`. There is no guarantee
on the interleaving of messages from different senders.

### Why does Erlang get "let it crash"?

Because actor processes are isolated — separate heaps, separate
mailboxes — a process crashing cannot corrupt another process.
Supervision trees restart the failed process from a known good state.
The actor model's no-shared-state property is what makes supervision
correct, not just convenient.

### When is the actor model the wrong default?

When per-call latency dominates (a hot cache-line mutex is faster than
a mailbox enqueue), when the workload is single-process and
compute-bound, when the system cannot tolerate the serialization tax
that location transparency imposes, and when you need shared mutable
state because the problem is fundamentally a single data structure
being touched by many producers.

## Cross-references

- [CSP Model](./csp-model.md) — synchronous channels and the actor/CSP debate
- [Transactional Memory](./software-transactional-memory.md) — a
  different composability story based on optimistic execution
- [Deadlock Detection](./deadlock-detection.md) — why the actor model
  sidesteps the four Coffman conditions by construction
- [Futures and Promises](./futures.md) — the other async primitive
- [Memory Model](./memory-model.md) — what actor systems still rely on
  at the runtime level for their own queues
- [Producer-Consumer](./producer-consumer.md) — the mailbox pattern
  across one producer and one consumer
- [Work-Stealing Scheduler](./work-stealing.md) — the runtime underneath
  Erlang and Akka dispatchers

## References

- Carl Hewitt, Peter Bishop, Richard Steiger. *A Universal Modular Actor
  Formalism for Artificial Intelligence*. IJCAI 1973.
  <https://arxiv.org/abs/1008.1459> (republished 2019 with commentary)
- Carl Hewitt. *Actor Model of Computation: Scalable Robust Information
  Systems*. 2015. <https://arxiv.org/abs/1008.1459>
- Joe Armstrong. *Making Reliable Distributed Systems in the Erlang
  Style*. PhD thesis, KTH, 2003.
  <https://www.erlang.org/download/armstrong_thesis_2003.pdf>
- Akka documentation: Actor Typed API.
  <https://doc.akka.io/docs/akka/current/typed/actors.html>
- Akka documentation: Location transparency and clustering.
  <https://doc.akka.io/docs/akka/current/typed/distributed-data.html>
- Erlang reference: Processes and message passing.
  <https://www.erlang.org/docs/system/processes>
- Pony language tutorial: Actors.
  <https://tutorial.ponylang.io/actors/actors.html>
- Sylvan Clebsch, Sophia Drossopoulou. *The Pony type system: "to
  fearless concurrency and beyond"*. SCALA 2013.
  <https://www.ponylang.io/media/pdf/pony_oopsla2013.pdf>
- Philipp Haller and Martin Odersky. *Scala Actors: Unifying
  thread-based and event-based programming*.
  <https://lampwww.epfl.ch/~odersky/papers/actors-cacm.pdf>
