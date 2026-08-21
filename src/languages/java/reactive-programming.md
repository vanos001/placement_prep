# Reactive Programming in Java

## Overview

The Reactive Manifesto, published in 2013-2014 by a group including Jonas Boner, Martin Thompson, and Dave Farley, popularized message-driven asynchronous systems whose defining trait is backpressure: a consumer asks for data, a producer sends only what was asked for, and when the consumer is overwhelmed the protocol slows the producer rather than buffering unboundedly. The Java realization has three layers:

- **Reactive Streams** (the spec, `org.reactivestreams.Publisher` etc.) — an SPI with four interfaces and roughly twenty rules.
- **Project Reactor** (Pivotal/VMware, ships with Spring) — `Flux` and `Mono`, the operators, the runtime.
- **RxJava** (Netflix, now RxJava 3.x community-maintained) — `Observable`, `Flowable`, the lineage of operators.

Both Reactor and RxJava implement the Reactive Streams interfaces. The spec alone gives you nothing runnable; it is a contract.

> Related: [Java Overview](./README.md), [Spring Boot Internals](./spring-boot-internals.md), [JVM Internals](./jvm.md), [Java Concurrency Deep Dive](./java-concurrent-deep.md), [Virtual Threads](./virtual-threads.md), [Quarkus and Micronaut](./quarkus-micronaut.md)

## The Reactive Streams Spec

Four interfaces, ~80 LOC of Java:

```java
public interface Publisher<T> {
    void subscribe(Subscriber<? super T> subscriber);
}

public interface Subscriber<T> {
    void onSubscribe(Subscription s);
    void onNext(T t);
    void onError(Throwable t);
    void onComplete();
}

public interface Subscription {
    void request(long n);
    void cancel();
}

public interface Processor<T, R> extends Subscriber<T>, Publisher<R> {}
```

The contract is in the spec rules (numbered, count has evolved). The interesting ones:

- **Rule 1.3** — `onSubscribe` MUST be called exactly once per `Subscriber`.
- **Rule 3** — `Subscription.request(n)` MUST place an upper bound on the number of `onNext` calls the publisher will emit. `request(3)` means at most three more items.
- **Rule 4** — A `Publisher` MUST NOT send more items than the sum of all `request(n)` calls. Sending more is a spec violation.
- **Rule 5** — `Subscription.cancel()` is the only release valve; the publisher MUST stop emitting and ideally release resources.
- **Rule 7** — `request(n)` for `n ≤ 0` is a programmer error; the publisher MUST signal it via `onError` and treat the subscription as cancelled.
- **Rule 9** — `request` and `cancel` MUST be serialized; concurrent invocation by two threads is illegal but the publisher must handle it (typically via a `ConcurrentLinkedQueue` of pending requests or a `LongAdder` for the count).
- **Rule 11** — A `Subscriber` MUST be prepared to receive `onNext` from any thread. The spec does not promise threading — the userland operator chain must do so via `publishOn`/`subscribeOn`.

The mental model is "the consumer is in charge". This is fundamentally different from a callback like `Consumer<T>` where the producer pushes whenever it likes.

## Project Reactor

`Flux<T>` is a publisher of 0..N items; `Mono<T>` is 0..1. Both implement `org.reactivestreams.Publisher`. The classic hello-world:

```java
Flux.range(1, 10)
    .map(i -> i * 10)
    .filter(i -> i < 50)
    .doOnNext(i -> log.info("emit {}", i))
    .subscribe();
```

What actually happens:

```
                       ┌─────────────────────┐
                       │  subscribe() call   │
                       │  at the bottom of   │
                       │  the chain          │
                       └──────────┬──────────┘
                                  │ triggers assembly backwards
                                  ▼
            ┌──────────────────────────────────────────┐
            │  FluxFilter ← FluxMap ← FluxRange        │
            │  Each operator wraps the upstream as     │
            │  its own Subscription when subscribe()   │
            │  is invoked. Subscription travels UP.    │
            └────────────────────┬─────────────────────┘
                                 │ data flows DOWN
                                 ▼
            ┌──────────────────────────────────────────┐
            │  FluxRange: source emits 1..10 on request │
            │  → FluxMap: applies i*10                  │
            │  → FluxFilter: passes <50                 │
            │  → doOnNext: logs                         │
            │  → Subscriber.onNext / onComplete         │
            └──────────────────────────────────────────┘
```

Two observations:

- The chain is **declarative** until `subscribe()` is called. Without a subscriber, `Flux.range(...).map(...)` is a description of a computation, not a computation. The act of `subscribe()` triggers a backward pass that asks each operator to construct its `Subscription` to the operator above it; then a forward pass of `onNext` items flows down.
- Each operator is a small state machine with a `Subscription` to upstream and an inner `Subscriber` to downstream. The interesting work — fusion, backpressure arithmetic, prefetching — lives in `Operators` and `FluxHide`/`FluxOnAssembly`/`FluxBuffer` classes. Reactor has ~600 operator classes.

### Backpressure in Reactor

The default backpressure strategy is `request(cap) → emit(cap) → request(cap)`. (`OverflowStrategy.BUFFER` is one of four overflow options.)

```java
Flux.interval(Duration.ofMillis(10))   // producer: 100 items/sec
    .onBackpressureBuffer(1000)         // queue capacity 1000
    .subscribe(new BaseSubscriber<Long>() {
        @Override protected void hookOnSubscribe(Subscription s) {
            s.request(100);   // ask for 100, then trickle
        }
        @Override protected void hookOnNext(Long v) {
            try { Thread.sleep(100); } catch (Exception e) {}  // slow consumer
            request(1);  // ask for next only after processing
        }
    });
```

Five overflow strategies when queue fills:
- `onBackpressureBuffer(int)` — bounded queue, `IllegalStateException` when full.
- `onBackpressureDrop()` — drop new items silently.
- `onBackpressureDrop(Consumer<T>)` — drop with callback.
- `onBackpressureLatest()` — keep latest, evict older.
- `onBackpressureError()` — signal `Exceptions.failWithOverflow`.

## RxJava

RxJava 3.x reorganized the type hierarchy around backpressure-awareness:

| Type | Backpressure | Typical use |
|------|--------------|-------------|
| `Observable<T>` | No | UI events, clicks, hot streams where consumer can't keep up but items are dispensable |
| `Flowable<T>` | Yes (implements Reactive Streams `Publisher`) | Database, file, network I/O where data must not be lost |
| `Single<T>` | N/A — emits one or error | HTTP request, replaces `CompletableFuture<T>` |
| `Maybe<T>` | N/A — emits 0/1 or error | Optional-valued request |
| `Completable` | N/A — completes or errors | Side-effectful operation, fire-and-forget |

The reason for the split: the Reactive Streams contract requires backpressure handling on every operator, which adds overhead (atomic counters, request arithmetic). For UI-style events (mouse moves, key strokes), backpressure is meaningless — the consumer cares only about the most recent value, so the overhead is wasted. `Observable` skips the protocol; `Flowable` implements it.

```java
// Observable — no backpressure, fine for clicks
Observable<Click> clicks = clicksObservable();
clicks.throttleFirst(100, TimeUnit.MILLISECONDS).subscribe(...);

// Flowable — backpressure-aware, fine for a 1M-row DB cursor
Flowable<Row> rows = Flowable.generate(() -> db.cursor(), (c, emitter) -> {
    if (c.next()) emitter.onNext(new Row(c));
    else emitter.onComplete();
});
rows.map(this::toPo).subscribe(...);
```

## Scheduling: publishOn vs subscribeOn

Two operators control thread context:

```
   upstream   .subscribeOn(schedulerA)   .publishOn(schedulerB)   .subscribe()
       │              │                          │                       │
       │              │ affects where            │ affects where          │
       │              │ subscribe() is called    │ downstream onNext     │
       │              │ and thus where source    │ runs from this point  │
       │              │ emits                    │ downward              │
       ▼              ▼                          ▼                       ▼
   source ──── runs on schedulerA ────switch──── runs on schedulerB ─── onNext on B
```

The classic source of confusion: `subscribeOn` controls where the **upstream** chain subscribes (and thus where source emission happens, e.g., a `Flux.fromIterable` reads the iterable on `schedulerA`). `publishOn` controls where **downstream** `onNext` runs from that point in the chain. Multiple `publishOn`s cascade — each switches threads again.

```java
Flux<Integer> f = Flux.range(1, 100)
    .subscribeOn(Schedulers.boundedElastic())   // emission on boundedElastic
    .map(i -> i + 1)                              // still boundedElastic
    .publishOn(Schedulers.parallel())             // switch from here downward
    .map(i -> i * 2)                              // parallel
    .publishOn(Schedulers.single())               // switch again
    .subscribe(i -> log.info("{}", i));           // single
```

`Schedulers.boundedElastic()` is the (since Reactor 3.2) IO-style pool — 10× CPU cap, queued, suitable for blocking JDBC. `Schedulers.parallel()` is CPU-bound, fixed at CPU count, suitable for CPU work. `Schedulers.single()` is a single-thread executor.

A common gotcha: `subscribeOn` has no effect if the source emits on a fixed thread regardless (e.g., `Flux.interval` emits on a daemon scheduler). The source's choice wins; you can override by inserting a `publishOn` immediately after.

## Hot vs Cold Publishers

```
                Cold Publisher                  Hot Publisher
                ───────────                     ────────────
                one source per                  one source for all
                  subscriber                      subscribers
                ───────────                     ────────────
  subscribe()  ↓                                ↓
                new generation starts           joins ongoing stream
                always gets full data           gets only data from now
                ───────────                     ────────────
  e.g.         Flux.fromIterable(...)           Sinks.many().multicast()
                Flux.fromCallable(...)          Flux.interval(...)
                HTTP request per subscriber     Live ticker (joined late,
                                                 misses first ticks)
```

Cold publishers are the default — every `Flux` we have written above is cold. Hot publishers in Reactor:

- `Sinks.many().multicast()` — a manually-driven hot publisher with multiple subscribers.
- `Sinks.many().replay().limitLast(N)` — replays the last N items to new subscribers.
- `Flux.interval(...)` — emits on a schedule, late subscribers miss items.
- `Flux.share()` (alias for `publish().refCount()`) — cold source becomes hot when first subscriber arrives, cold again when the last unsubscribes.

```java
// Stock ticker: every subscriber from now on sees new ticks only
Sinks.Many<Tick> ticker = Sinks.many().multicast().onBackpressureBuffer();
// elsewhere:
ticker.tryEmitNext(new Tick("AAPL", 175.4));
// elsewhere, in a different thread:
ticker.asFlux().subscribe(t -> log.info("got {}", t));  // misses past ticks
```

## Reactor Netty

Reactor Netty (`reactor-netty-core` + `reactor-netty-http`) is the HTTP server and client used by Spring WebFlux. It is built on Netty's channel pipeline but exposes a Reactor API:

```java
DisposableServer server = HttpServer.create()
    .host("0.0.0.0").port(8080)
    .route(routes -> routes
        .get("/users/{id}", (req, res) ->
            res.sendString(Mono.just("user " + req.param("id")))
        )
        .post("/echo", (req, res) ->
            res.send(req.receive().asString())  // echo body back
        ))
    .bindNow();

server.onDispose().block();
```

The interesting bit is that the request body itself is a `Flux<ByteBuf>` — backpressured all the way down to the socket. A slow handler automatically throttles the kernel TCP receive window. Compare to a Servlet `InputStream.read()` where backpressure is implicit (blocking read) but a single thread is consumed per connection; Reactor Netty runs thousands of concurrent connections on a handful of event-loop threads, with no thread per connection.

## Comparison to CompletableFuture

`CompletableFuture<T>` (Java 8) is the closest non-reactive analog. The comparison is sharp:

| Aspect | `CompletableFuture<T>` | `Flux<T>` / `Flowable<T>` |
|--------|--------------------------|----------------------------|
| Cardinality | 0 or 1 result | 0..N |
| Backpressure | None — push model | First-class — pull model |
| Cancellation | `cancel(true)` — best effort, no callback | `Subscription.cancel()` — contractually honored |
| Composition | `thenApply`, `thenCompose`, `allOf`, `anyOf` | 100+ operators (`map`, `flatMap`, `zip`, `merge`, `concat`, `combineLatest`) |
| Threading | `*Async` variants + `Executor` per call | `publishOn` / `subscribeOn` |
| Multi-source | Awkward (`allOf` blocks; no zip of streams) | `zip`, `merge`, `concat` are first-class |
| Backtraces | Stack from the chaining thread | Reactor's `onAssembly` (debug mode) — alternative stack |
| Hot/cold | Always "future" — fire on construction or on `complete` | Distinguishes cold/hot |
| Memory per pipeline | One CF per stage | One Subscription per operator per subscriber |

The rule of thumb: if you have a single async result (one HTTP call, one DB query), `CompletableFuture` is fine. If you have a stream of values, fan-out and merge, or backpressure concerns — use Reactor/RxJava. Mixing them is workable: `Mono.fromFuture(cf)` and `mono.toFuture()` bridge.

## When Not To Use Reactive

A contrarian view, increasingly common since Project Loom (see [Virtual Threads](./virtual-threads.md)):

- For I/O-bound services, virtual threads deliver reactive-style throughput with plain blocking code. The cost is ~1 µs per thread and a continuation on the heap; the benefit is no `flatMap`, no operator chain, no backpressure arithmetic.
- Reactive shines when you genuinely need streaming, multi-source composition, or when you cannot move off Netty's event loops. For request-response CRUD services, the cognitive tax of operator chains is rarely worth it.

## Interview Questions

**Q: What are the four Reactive Streams interfaces?**
`Publisher<T>` (one method, `subscribe`), `Subscriber<T>` (four methods — `onSubscribe`, `onNext`, `onError`, `onComplete`), `Subscription` (`request`, `cancel`), and `Processor<T,R>` which is both a `Subscriber<T>` and a `Publisher<R>` — a transform stage.

**Q: Explain backpressure.**
A consumer signals how many items it wants via `Subscription.request(n)`; the producer MUST NOT emit more than the sum of all `request(n)` calls. The downstream is in charge. Strategies when the producer cannot slow down (e.g., time-driven source): buffer (bounded or unbounded), drop, drop-oldest, drop-latest, or signal error.

**Q: What is the difference between `Flux` and `Mono`?**
Cardinality. `Flux<T>` emits 0..N; `Mono<T>` emits 0 or 1 then completes (or errors). `Mono` has optimizations like `Mono.toFuture()` and a single-item fast path; it is the right choice when the semantics are "the result of this async operation".

**Q: `subscribeOn` vs `publishOn`?**
`subscribeOn` affects where the chain subscribes to the source (and thus where the source emits, if it does so synchronously on subscription). `publishOn` switches the thread that downstream `onNext` runs on, from the point in the chain where `publishOn` appears. `subscribeOn` has one effective location (the closest to source wins for source emission); `publishOn` can appear multiple times and each switches the downstream thread.

**Q: Hot vs cold publisher?**
Cold: a new source per subscriber — `Flux.fromIterable` re-reads the iterable per `subscribe()`. Hot: one source shared by all subscribers — a `Sinks.Many` late subscriber misses past emissions. `Flux.share()` converts a cold publisher to hot when the first subscriber arrives and back to cold when the last leaves.

**Q: Why does `Flux.interval` ignore `subscribeOn`?**
Because `Flux.interval` is implemented in terms of an internal scheduler (a daemon `ScheduledExecutorService`); it emits on that scheduler regardless of where the chain subscribes. `subscribeOn` only affects operators that emit on the subscribing thread; for sources that choose their own thread, the only override is `publishOn` placed after the source.

**Q: Why does RxJava have both `Observable` and `Flowable`?**
Because Reactive Streams requires backpressure support, which adds overhead (atomic counters, request arithmetic) on every operator. For UI events and other "missable" streams, the overhead is wasted. `Observable` skips the protocol; `Flowable` implements it. Choose by whether losing items is acceptable.

**Q: Why is Reactor Netty's backpressure "real" backpressure?**
Because the response body is a `Flux<ByteBuf>` that does not read ahead of consumption. When the handler's `onNext` is slow, the operator chain stops requesting, the Netty channel stops reading, the TCP receive window closes, and the sender's writes block. Backpressure propagates from the application's `onNext` all the way back to the TCP layer.

## Cross-References

- [Java Overview](./README.md)
- [Spring Boot Internals](./spring-boot-internals.md) — WebFlux is built on Reactor
- [JVM Internals](./jvm.md)
- [Java Concurrency Deep Dive](./java-concurrent-deep.md) — `CompletableFuture`, `Flow.Subscriber` (Java 9's stdlib reactive)
- [Virtual Threads](./virtual-threads.md) — when blocking is cheap again, the reactive tax matters less
- [Quarkus and Micronaut](./quarkus-micronaut.md) — both ship reactive runtimes (Vert.x and Netty respectively)

## References

- Reactive Streams Specification — https://www.reactive-streams.org/
- Reactive Streams Javadoc (org.reactivestreams) — https://www.reactive-streams.org/reactive-streams-1.0.3-javadoc/
- Project Reactor Reference — https://projectreactor.io/docs/core/release/reference/
- Project Reactor Javadoc — https://projectreactor.io/docs/core/release/api/
- RxJava Wiki — https://github.com/ReactiveX/RxJava/wiki
- RxJava Javadoc (3.x) — https://reactivex.io/RxJava/3.x/javadoc/
- Reactor Netty Reference — https://projectreactor.io/docs/netty/release/reference/
- The Reactive Manifesto — https://www.reactivemanifesto.org/
- "Reactive Design Patterns" by Roland Kuhn with Brian Hanafee and Jamie Allen (Manning, 2016) — the canonical patterns reference
- Lightbend — What is Reactive? (Roland Kuhn) — https://www.lightbend.com/blog/what-is-reactive
