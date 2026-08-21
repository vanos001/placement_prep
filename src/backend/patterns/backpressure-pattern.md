# Backpressure Pattern

## Overview

Backpressure is the signal from a slower consumer to a faster producer that
says "slow down" — or, equivalently, "wait until I'm ready." It is the
generalisation of the producer-consumer pattern to the case where the two
ends run at different rates. The Reactive Manifesto puts it bluntly: a
system without backpressure is one whose unbounded queues will, eventually,
exhaust the heap.

The pattern lives wherever a producer can run faster than a consumer:
- A logger that writes 100k events/s to disk that flushes 10k/s.
- A Kafka consumer that polls faster than it can process.
- A streaming HTTP response that streams 1 GB/s into a client that reads
  100 MB/s.
- A UI that emits mouse-move events at 1000 Hz into a handler that takes
  50 ms each (max throughput 20 Hz).

Without backpressure, the producer's excess piles up somewhere — in a
queue, in a buffer, in the heap. With backpressure, the producer either
blocks, drops, or is *told* how many items the consumer can accept next.

## The Producer-Consumer Problem

A producer hands items to a consumer over a channel. Three coupling models:

```
   ┌──────────────────────────────────────────────────────────────────┐
   │ Push model  : producer → → → consumer                           │
   │              producer paces itself; consumer may overflow       │
   ├──────────────────────────────────────────────────────────────────┤
   │ Pull model  : producer ← ← ← consumer                           │
   │              consumer paces producer; producer may starve        │
   ├──────────────────────────────────────────────────────────────────┤
   │ Pull-push  : producer ↔ consumer                                 │
   │              (reactive streams)                                 │
   │              consumer requests N items; producer pushes up to N │
   └──────────────────────────────────────────────────────────────────┘
```

The push model is the natural fit for event sources that don't know their
consumers (a network socket, a UI event). The pull model fits when the
consumer is the active driver (a database query iterator, a `Scanner`).
The pull-push hybrid — *you tell me how many you want; I'll send that many*
— is what the Reactive Streams specification formalised, and it's the
standard for asynchronous stream processing in the JVM ecosystem.

## Bounded vs Unbounded Queues

The simplest "backpressure" is a queue between producer and consumer.

```
   producer ──▶ [queue] ──▶ consumer
```

If the queue is **unbounded**, the producer never blocks and the consumer
never misses an item, but slow consumers cause the queue to grow without
bound — eventually OOM. This is the default behaviour of every
`LinkedBlockingQueue` constructed without a capacity argument, of every
`asyncio.Queue()` constructed without `maxsize`, of every Go channel
created with `make(chan T)` instead of `make(chan T, N)`.

If the queue is **bounded**, two policies are possible:

- **Block the producer** when the queue is full. The producer slows to the
  consumer's rate. This is what `BlockingQueue.put()` and
  `asyncio.Queue.put()` do; it's also what a bounded Go channel does. The
  risk: if the consumer dies, the producer is stuck forever.
- **Drop excess** items when the queue is full. Useful when freshness
  matters more than completeness — a metrics sampler, a UI event stream.
  This is what `Queue.offer()` returns false for, and what
  `onBackpressureDrop` does.

The bounded-with-block policy is the textbook answer, but it has a
fatal flaw: **it only works if the consumer can actually slow the producer
down**. If the producer is, say, a network socket and the OS is filling
its own kernel buffer underneath you, blocking your application thread
doesn't slow the producer — it just moves the queue into the kernel. The
buffer overflows in the kernel; you get packet drops and retransmits at the
TCP layer rather than where you can see them. A backpressure strategy that
relies on blocking is only as good as the slowest link in the producer
chain.

The reactive streams protocol was designed to address exactly this: a
non-blocking, *asynchronous* signal from consumer to producer that
cooperatively slows the source.

## The Reactive Streams Protocol

The Reactive Streams specification (JDK `java.util.concurrent.Flow`,
Reactor, RxJava 3, Akka Streams, and small adaptations on the Kotlin,
Rust, and Swift ecosystems) defines four interfaces and three rules.

### The four interfaces

```java
// Publisher — produces items. Subscribe registers a Subscriber.
interface Publisher<T> {
    void subscribe(Subscriber<? super T> subscriber);
}

// Subscriber — consumes items. Subscriptions are tied 1:1 to a Publisher.
interface Subscriber<T> {
    void onSubscribe(Subscription s);   // called once, with the subscription
    void onNext(T t);                    // called 0..N times
    void onError(Throwable t);          // terminal: 1 time, after onNext
    void onComplete();                   // terminal: 1 time, no more onNext
}

// Subscription — the channel between one Publisher and one Subscriber.
interface Subscription {
    void request(long n);     // subscriber asks for n more items
    void cancel();            // subscriber stops the subscription
}

// Processor — a node that is both a Subscriber and a Publisher.
interface Processor<T, R> extends Subscriber<T>, Publisher<R> {}
```

### The contract

The crucial rule is **rule 3** of the spec:

> `Publisher.request` and `Subscription.cancel` MUST only be called
> inside of its `Subscriber` context. ... A Publisher MUST NOT send
> `onNext` items to a Subscriber before the latter has called `request`.

In other words: the publisher may not push items until the subscriber has
*asked* for them by calling `request(n)`. The subscriber controls the
demand; the publisher respects it. The publisher is contractually
forbidden to call `onNext` more times than the sum of `request(n)` calls
it has received.

This is **pull-push**: the subscriber *pulls* by requesting, the publisher
*pushes* the requested items. The subscriber controls the rate; the
publisher never floods.

### Why this is not just "calling request after each onNext"

You might think: "easy, I'll just call `request(1)` inside every `onNext`,
and the publisher will send me one item at a time." That works — it's the
"pull of 1" pattern — but it's slow: the round trip from `onNext` returning
to the publisher sending the next item takes a full network hop (or a full
thread-context-switch hop) per item. The throughput is bound by the
round-trip latency, not by either side's processing rate.

The protocol's idiom is **request N, get N, request N more**. The "N" is
the window — analogous to TCP's receive window. The bigger N, the higher
the throughput at the cost of more in-flight memory. Reactive Streams lets
you tune N per stage in the pipeline:

```java
source
    .publishOn(Schedulers.parallel(), 256)    // 256-item prefetch buffer
    .map(this::heavyTransform)
    .subscribe(new Subscriber<>() {
        private Subscription s;
        public void onSubscribe(Subscription s) {
            this.s = s;
            s.request(8);                  // start with 8 in flight
        }
        public void onNext(Integer i) {
            process(i);
            s.request(1);                  // one at a time afterwards
        }
        // onError, onComplete...
    });
```

The flow above is the reactive equivalent of TCP's window-based flow
control (see the comparison section below).

## Project Reactor: When the Source Can't Be Slowed

The protocol is great when the source is itself a Reactive Streams
publisher — the demand propagates back, the source slows. But not every
source cooperates. A database iterator, a UI event, a callback-based API,
a Kafka consumer — these *push* their items. You can't make a UI event
source "wait" because the user keeps moving the mouse.

For these push sources, Reactor provides the `onBackpressure*` operators:

### `onBackpressureBuffer`

```
   source ──▶ [bounded buffer] ──▶ subscriber
                  ▲                  │
                  │                  │ request(n)
                  └──────────────────┘
```

Items emitted by the source go into a bounded buffer; the subscriber pulls
from it. If the buffer fills, the policy depends on the variant:

- `onBackpressureBuffer()` — unbounded buffer; the source keeps emitting;
  you'd better be sure the consumer is faster or you'll OOM.
- `onBackpressureBuffer(int capacity)` — bounded; emits `OverflowException`
  when full.
- `onBackpressureBuffer(int, BufferOverflowStrategy)` — bounded; controls
  the overflow policy (`DROP`, `DROP_LATEST`, `DROP_OLDEST`).

```java
eventSource
    .onBackpressureBuffer(1024, BufferOverflowStrategy.DROP_OLDEST)
    .map(this::transformEvent)
    .subscribe(this::process, this::onError);
```

### `onBackpressureDrop`

Drop items that arrive when the subscriber hasn't requested them.

```
   source ──▶ subscriber (if requested) else drop
```

```java
mouseEvents
    .onBackpressureDrop()
    .map(this::toVelocity)
    .subscribe(this::render);
```

Items are dropped silently; the operator calls a `Consumer<T>` if you pass
one, useful for logging.

### `onBackpressureDropLast`

Like `Drop` but keeps the last N items dropped, so when the subscriber is
ready you can replay them. Useful for: "the user was clicking; we couldn't
keep up; let's at least show the latest click they made."

```java
sensorSamples
    .onBackpressureDropLast(100)
    .map(this::aggregate)
    .subscribe(this::persist);
```

### `onBackpressureLatest`

Keep only the most recent item when the subscriber hasn't requested. When
the subscriber requests, deliver the latest one. Functionally equivalent to
"sample at the subscriber's rate" — the producer is unconstrained, the
subscriber sees the latest state whenever it pulls.

```java
clockTicks
    .onBackpressureLatest()
    .map(this::pollState)
    .subscribe(this::update);
```

The four strategies map to four real-world decisions:

| Operator            | When the subscriber is slow, ...           | Use case                       |
| ------------------- | ------------------------------------------- | ------------------------------ |
| `Buffer` (bounded)  | Drop or error                               | Need ordering; some loss ok    |
| `Buffer` (unbounded)| Never drop (but eventually OOM)             | Transient surges with known end |
| `Drop`              | Drop silently                                | Fire-and-forget events         |
| `DropLast`          | Drop but remember the last N                | User gestures; need final state|
| `Latest`            | Keep the latest, drop intermediate           | State polling; UI redraws      |

## Akka Streams: Backpressure as Graph Algebra

Akka Streams (the JVM Scala/Java implementation of the Reactive Streams
protocol) takes a different angle: streams are *graphs* of stages with
explicit input and output ports, and the backpressure is part of the graph's
type. Each `Shape` has input ports (`Inlet`) and output ports (`Outlet`),
and each stage declares how it propagates demand.

```scala
import akka.stream.scaladsl._

val source = Source(1 to 1000000)
val flow   = Flow[Int].map(_ * 2).filter(_ > 0)
val sink   = Sink.foreach[Int](n => Thread.sleep(10))  // slow consumer

val graph = source.via(flow).to(sink)
graph.run()   // the runtime wires up the demand; the slow sink pulls
              // demand from the filter, which pulls from source
```

The crucial difference from Reactor: the stages are *assembled* into a
graph and *then* materialised. The materialisation phase turns the graph
into running actors; until then, you have a *blueprint*. This means you
can compose graphs, fan-out, fan-in, and merge — all statically type-
checked — and the backpressure propagates through the graph topology.

The classic Akka idiom for "if the consumer is slow, do X":

```scala
source
  .map(this::expensive)
  .buffer(100, OverflowStrategy.fail)   // bounded buffer; fail if overflowed
  .throttle(100, 1.second)              // explicit rate limit
  .to(Sink.foreach(println))
  .run()
```

`OverflowStrategy` mirrors Reactor's `BufferOverflowStrategy`: `dropHead`,
`dropTail`, `dropBuffer`, `dropNew`, `fail`, `backpressure`.

Akka's notable addition is the `throttle` operator, which combines a rate
limiter with a burst size in a single stage — useful for shaping traffic
to a downstream that you know has its own limits.

## Comparison to TCP Flow Control

TCP solves the same problem at a different layer. A sender could flood a
receiver's buffer; the receiver's `ACK` packets include the **receive
window** — the amount of free buffer space available. The sender may not
have more bytes in flight than the receiver's window.

```
   TCP sender                          TCP receiver
   ─────────────                       ─────────────
   unacked bytes ≤ window              window = free buffer space
                                       ↓
                                       ACK packet carries the window
   sender adjusts send rate            on every ACK
```

The Reactive Streams protocol is the same algorithm:

| TCP flow control            | Reactive Streams              |
| --------------------------- | ------------------------------ |
| Receive window (bytes)      | `request(n)` (items)           |
| ACK carries window          | `request` call carries demand  |
| Sender must respect window  | Publisher must respect demand  |
| RST closes the connection  | `cancel()` ends subscription   |
| Slow-start / congestion     | (No equivalent — out of scope) |

Two important differences:

1. **TCP counts bytes; Reactive Streams counts items.** A Reactive Streams
   item is opaque — a 1-byte or a 1-MB object both count as 1 toward the
   demand. For variable-size items this can be a problem: requesting 1000
   items with a 1-MB object each = 1 GB of in-flight memory. Reactor's
   `limit(n)` operator is the standard mitigation — it caps the actual
   in-flight buffer even when `request(n)` asked for more.
2. **TCP has congestion control too; Reactive Streams doesn't.** TCP's
   congestion control (Reno, CUBIC, BBR) responds to *loss* as well as to
   the receiver's window — it slows the sender when intermediate routers
   are dropping packets, not just when the receiver is slow. Reactive
   Streams has no concept of "intermediate router"; the protocol assumes a
   direct producer-consumer relationship. If your topology has multiple
   stages, each stage handles its own backpressure; there's no end-to-end
   congestion signal.

The Reactive Streams protocol is closer to a **TCP between two endpoints
without congestion control** than to a fully general flow-control scheme.
For end-to-end flow control with intermediate queues, you have to think
about every stage.

## Common Pitfalls

1. **Unbounded buffers everywhere.** `LinkedBlockingQueue()`, `asyncio.Queue()`,
   unbounded Go channels — all hide backpressure until you OOM. Audit every
   queue with a capacity.
2. **`request(Long.MAX_VALUE)` and forgetting.** Many tutorials start with
   `request(Long.MAX_VALUE)` to disable backpressure. It works for a demo
   and fails on the first production-sized source.
3. **Blocking inside `onNext`.** The Reactive Streams rule 3 forbids
   blocking in `onNext`. If you need to call a blocking API, `publishOn` a
   bounded-elastic scheduler first.
4. **Variable-size items, fixed demand.** A `request(1000)` on a source
   that emits 1-MB items is asking for 1 GB. Use `limit` or request
   smaller batches.
5. **Push sources without a strategy.** Calling `Flux.fromIterable`
   cooperates with backpressure natively, but `Flux.create` doesn't unless
   you handle `BackpressureDrop`/`Buffer`/`Latest` in the `FluxSink`.
6. **Assuming the source can be slowed.** A mouse, a sensor, a Kafka topic
   — these will push regardless of your subscription. You *will* need a
   strategy; pick `Drop`, `DropLast`, `Latest`, or `Buffer`.
7. **Forgetting that cancellation propagates.** When you `cancel()` a
   subscription, the upstream stage may keep running briefly. The protocol
   allows this; your code must be idempotent and tolerate late `onNext`
   calls.

## Interview Questions

### Q: What is the difference between backpressure and rate limiting?

Backpressure is *consumer-driven* — the consumer tells the producer "send
me N more when ready." Rate limiting is *gate-driven* — a separate
component says "you may only send N per second." Both bound throughput,
but they operate in opposite directions: backpressure slows the producer
in response to the consumer's actual capacity; rate limiting enforces a
policy irrespective of capacity. They compose: a rate limiter at the edge
of a service bounds the request rate; backpressure inside the service
bounds the in-flight work.

### Q: Why is the Reactive Streams protocol called "pull-push"?

The subscriber *pulls* — it calls `request(n)` to declare demand. The
publisher *pushes* — it sends up to N items via `onNext`. So the model has
both: a pull from consumer to producer (declaring demand), and a push from
producer to consumer (delivering items). This is distinct from a pure push
model (publisher decides rate) and a pure pull model (subscriber polls the
publisher, which doesn't know how many to send until asked).

### Q: How would you handle a source that doesn't natively support backpressure
— e.g., a Java `Iterator` wrapped as a `Flux`?

You can't slow the iterator from the outside; calling `next()` is the only
way to get items. The standard pattern is to wrap it in `Flux.create` with
an explicit backpressure strategy: the `FluxSink` is the bridge between
the push-style iterator and the pull-style subscriber. You decide what
happens when the subscriber hasn't requested but the iterator has a next
item — `Buffer`, `Drop`, `DropLast`, or `Latest`. `Buffer` is the
closest to "respect demand," but it's bounded; pick the policy that
matches your use case.

### Q: How does TCP flow control compare to Reactive Streams?

Both use a sliding window: the receiver advertises its capacity (receive
window / `request(n)`); the sender/publisher must not have more in flight
than the window; the window is updated on every ACK / `request` call; the
connection can be torn down (`RST` / `cancel()`). The differences: TCP
counts bytes (so a window of 64 KB can hold one 64-KB packet or 1000 64-byte
packets — same window, different counts); Reactive Streams counts items.
And TCP has congestion control (slow-start, CUBIC, BBR) for the
intermediate routers, which Reactive Streams lacks — every stage handles
its own backpressure, and there's no end-to-end congestion signal.

## References

- Reactive Streams specification: full contract, including the four
  interfaces and the rules (esp. rule 3, the demand rule).
  https://github.com/reactive-streams/reactive-streams-jvm
- Java `java.util.concurrent.Flow` — the JDK adoption of the Reactive
  Streams interfaces, with the same four interfaces under different
  package names.
  https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/Flow.html
- Project Reactor reference: *Handling Errors* — covers the `onError`
  terminal signal and its interaction with backpressure operators.
  https://projectreactor.io/docs/core/release/reference/#error.handling
- Project Reactor Javadoc: `Flux.onBackpressureBuffer` and friends —
  detailed contract for each operator and its overflow strategy.
  https://projectreactor.io/docs/core/release/api/reactor/core/publisher/Flux.html
- Akka Streams documentation: *Basics and working with Flows* — covers
  the graph algebra, the stages, and the `OverflowStrategy` enum.
  https://doc.akka.io/docs/akka/current/typed/stream/stream-flows-and-basics.html
- Akka Streams documentation: *Built-in stages* — covers `throttle`,
  `buffer`, and the demand propagation through composed graphs.
  https://doc.akka.io/docs/akka/current/typed/stream/stream-graphstage.html
- Erik Bruchez, "Designing for Backpressure" — a walkthrough of how a
  pull-based pipeline can be designed without Reactive Streams, useful as
  a contrast.
  https://blog.bruchez.dev/posts/designing-for-backpressure/
- The Reactive Manifesto — places backpressure as one of the four
  defining properties of a "reactive" system.
  https://www.reactivemanifesto.org/

## Related Topics

- [Bulkhead Deep Dive](./bulkhead-deep.md) — the per-call-site cousin of
  backpressure: a bulkhead caps *this* call site's concurrency; backpressure
  caps *this* stream's in-flight items.
- [Rate Limiting Pattern](./rate-limiting-pattern.md) — the time-windowed
  cousin of backpressure; rate limiting is about *rate*, backpressure is
  about *capacity*.
- [TCP Flow Control](../../networks/tcp/flow-control.md) — the network-layer
  ancestor of the Reactive Streams protocol.
- [Circuit Breaker Deep Dive](./circuit-breaker-deep.md) — what to do when
  the downstream is the slow consumer *because it's failing*.
- [Streaming Pipeline](../../interview/system-design/real-world/streaming-pipeline.md)
  — where backpressure across multiple stages becomes a real engineering
  problem rather than a tutorial exercise.
