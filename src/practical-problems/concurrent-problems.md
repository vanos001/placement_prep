# Concurrent Programming Problems

## Producer-Consumer Pattern

### Problem
Producers generate data and put it in a shared buffer. Consumers take data from the buffer and process it. The buffer has a fixed capacity.

### Python Implementation (threading)

```python
import threading
import queue
import time
import random

class ProducerConsumer:
    def __init__(self, buffer_size=10):
        self.buffer = queue.Queue(maxsize=buffer_size)
        self.running = True
    
    def producer(self, producer_id):
        while self.running:
            item = random.randint(1, 100)
            self.buffer.put(item)  # Blocks if full
            print(f"Producer {producer_id} produced: {item}")
            time.sleep(random.uniform(0.1, 0.5))
    
    def consumer(self, consumer_id):
        while self.running:
            item = self.buffer.get()  # Blocks if empty
            print(f"Consumer {consumer_id} consumed: {item}")
            self.buffer.task_done()
            time.sleep(random.uniform(0.1, 0.3))
    
    def run(self, num_producers=2, num_consumers=3):
        threads = []
        for i in range(num_producers):
            t = threading.Thread(target=self.producer, args=(i,))
            t.start()
            threads.append(t)
        for i in range(num_consumers):
            t = threading.Thread(target=self.consumer, args=(i,))
            t.start()
            threads.append(t)
        return threads
```

### Java Implementation

```java
import java.util.concurrent.*;

public class ProducerConsumer {
    private final BlockingQueue<Integer> queue;
    
    public ProducerConsumer(int capacity) {
        this.queue = new ArrayBlockingQueue<>(capacity);
    }
    
    public void producer(int id) throws InterruptedException {
        while (true) {
            int item = ThreadLocalRandom.current().nextInt(100);
            queue.put(item);  // Blocks if full
            System.out.printf("Producer %d produced: %d%n", id, item);
        }
    }
    
    public void consumer(int id) throws InterruptedException {
        while (true) {
            int item = queue.take();  // Blocks if empty
            System.out.printf("Consumer %d consumed: %d%n", id, item);
        }
    }
}
```

## Thread Pool

### Problem
Execute tasks concurrently with a fixed number of worker threads.

### Python Implementation

```python
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

# Simple thread pool
class SimpleThreadPool:
    def __init__(self, num_threads):
        self.tasks = Queue()
        self.threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self.threads.append(t)
    
    def _worker(self):
        while True:
            func, args, kwargs = self.tasks.get()
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(f"Task failed: {e}")
            finally:
                self.tasks.task_done()
    
    def submit(self, func, *args, **kwargs):
        self.tasks.put((func, args, kwargs))
    
    def wait(self):
        self.tasks.join()

# Using stdlib
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(process, item) for item in items]
    results = [f.result() for f in futures]
```

## Connection Pool

### Problem
Manage a pool of reusable database connections to avoid the overhead of creating/destroying connections.

### Python Implementation

```python
import threading
import time
from queue import Queue, Empty

class Connection:
    def __init__(self, conn_id):
        self.conn_id = conn_id
        self.in_use = False
        self.created_at = time.time()
    
    def execute(self, query):
        # Simulate query execution
        time.sleep(0.01)
        return f"Result from conn {self.conn_id}: {query}"

class ConnectionPool:
    def __init__(self, min_size=2, max_size=10, max_idle_time=300):
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.pool = Queue(maxsize=max_size)
        self.lock = threading.Lock()
        self.current_size = 0
        
        # Create minimum connections
        for i in range(min_size):
            self.pool.put(Connection(i))
            self.current_size += 1
    
    def get_connection(self, timeout=5):
        try:
            conn = self.pool.get(timeout=timeout)
            conn.in_use = True
            return conn
        except Empty:
            # Create new connection if under max
            with self.lock:
                if self.current_size < self.max_size:
                    conn = Connection(self.current_size)
                    self.current_size += 1
                    conn.in_use = True
                    return conn
            raise TimeoutError("No connections available")
    
    def release_connection(self, conn):
        conn.in_use = False
        self.pool.put(conn)
    
    def __enter__(self):
        self.conn = self.get_connection()
        return self.conn
    
    def __exit__(self, *args):
        self.release_connection(self.conn)
```

## Worker Pool

### Problem
Process a stream of tasks with a fixed number of workers, collecting results.

### Go Implementation

```go
func workerPool(numWorkers int, jobs <-chan Job, results chan<- Result) {
    var wg sync.WaitGroup
    
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            for job := range jobs {
                result := process(job)
                results <- result
            }
        }(i)
    }
    
    wg.Wait()
    close(results)
}
```

## Interview Questions

**Q: What's the difference between a thread pool and a worker pool?**
A: Thread pool manages OS threads for reuse (avoids creation overhead). Worker pool is a pattern where workers process tasks from a queue. A thread pool often implements a worker pool, but worker pools can also use processes, coroutines, etc.

**Q: How do you handle backpressure in producer-consumer?**
A: (1) Blocking queue (producer blocks when full), (2) drop oldest/newest (lossy), (3) bounded buffer with timeout, (4) signal producer to slow down, (5) add more consumers, (6) spill to disk when buffer is full.

**Q: How do you prevent deadlocks in concurrent code?**
A: (1) Lock ordering — always acquire locks in the same order, (2) use timeouts on lock acquisition, (3) use trylock and back off on failure, (4) minimize lock scope, (5) prefer lock-free structures, (6) use deadlock detection tools.

## Interview Problem Set: Five Synchronization Gauntlets

The pages in [Concurrency](../concurrency/overview.md) teach the *patterns* ([Producer-Consumer](../concurrency/producer-consumer.md), [Readers-Writers](../concurrency/readers-writers.md), [Deadlock Detection](../concurrency/deadlock-detection.md)); this section is interview *terrain* — five canonical coding problems, each with the race named as an exact interleaving, a minimal fix, and a safety argument. Every solution was executed and its output recorded this session with python3 3.12.14 (Linux, `threading`); "verified" means literally run, not sketched.

### Problem 1 — Print Zero Even Odd (n threads, strict alternation)

**Problem**: one thread prints `0`, an `even` thread prints even numbers, an `odd` thread prints odd numbers; output for n=5 must be `0102030405`.

**The naive race**: with a shared "last printed" flag and no blocking, zero prints `0`, then *both* even and odd threads see `last=0` and race to the printer. Interleaving: zero writes 0 → scheduler preempts zero → odd checks flag (expects its turn at 1) but even wakes first, writes 2 → output `0201...`. A `time.sleep()` "fix" only narrows the odds — it schedules the race away instead of removing it.

**Correct solution** (three semaphores; the digit threads hand control back to zero):

```python
import threading
def zero(n):
    for i in range(1, n+1):
        s0.acquire(); print(0, end=""); (se if i%2==0 else so).release()
def even(n):
    for i in range(2, n+1, 2):
        se.acquire(); print(i, end=""); s0.release()
def odd(n):
    for i in range(1, n+1, 2):
        so.acquire(); print(i, end=""); s0.release()
n = 5
s0, se, so = threading.Semaphore(1), threading.Semaphore(0), threading.Semaphore(0)
ts = [threading.Thread(target=zero, args=(n,)), threading.Thread(target=even, args=(n,)), threading.Thread(target=odd, args=(n,))]
[t.start() for t in ts]; [t.join() for t in ts]; print()
```

**Freedom argument**: each semaphore starts with ≤1 permit and the release order is a fixed cycle `zero → {even|odd} → zero`, so at every instant at most one thread holds a permit — mutual exclusion by construction, no lock needed. **Verified output (5 runs identical)**: `0102030405`. **Variants**: four roles (chain four semaphores); the interviewer's twist — "no semaphores, only Condition": the predicate becomes `next_expected == i` with `notify_all()`.

### Problem 2 — Print FooBar Alternately (and why two locks in the wrong order deadlock)

**Problem**: thread A prints `foo` n times, thread B prints `bar` n times, strictly `foobarfoobar...`.

**The naive race and the deadlock variant**: a tempting design uses two plain locks, `fa` for foo's turn and `fb` for bar's, with each thread acquiring *both*. Give foo the order (A→B) and bar (B→A) and you get the classic deadlock — the same disease as the philosophers below: foo holds `fa` and blocks on `fb`; bar holds `fb` and blocks on `fa`; circular wait, neither ever releases. Verified demo (python3 3.12.14, 3/3 runs, 0.1s sleep widening the window):

```python
import threading, time
fa, fb = threading.Lock(), threading.Lock()
def foo():
    with fa:                  # foo: A then B
        time.sleep(0.1)
        with fb: print("foo", end="")
def bar():
    with fb:                  # bar: B then A — reversed order
        time.sleep(0.1)
        with fa: print("bar", end="")
a = threading.Thread(target=foo, daemon=True); b = threading.Thread(target=bar, daemon=True)
a.start(); b.start(); a.join(timeout=2.0); b.join(timeout=2.0)
print(f"| foo alive={a.is_alive()} bar alive={b.is_alive()}  (circular wait: foo holds A wants B, bar holds B wants A)")
```

Verified output: `| foo alive=True bar alive=True  (circular wait: foo holds A wants B, bar holds B wants A)` — the verdict line prints, the threads never do.

**Correct solution** (two semaphores — handoff, not holding):

```python
import threading
n = 5
sf, sb = threading.Semaphore(1), threading.Semaphore(0)
def foo():
    for _ in range(n):
        sf.acquire(); print("foo", end=""); sb.release()
def bar():
    for _ in range(n):
        sb.acquire(); print("bar", end=""); sf.release()
a = threading.Thread(target=foo); b = threading.Thread(target=bar)
a.start(); b.start(); a.join(); b.join(); print()
```

**Freedom argument**: no thread ever holds two resources — each acquires one semaphore, prints, releases the other. Deadlock needs a wait cycle over *held* resources; a thread blocked on `sf` holds nothing. Contrast with the deadlock variant: two semaphores acquired *one at a time* cannot deadlock even in "wrong order" — they yield a phase-shifted but complete output (also verified). **Verified output**: `foobarfoobarfoobarfoobarfoobar`. **Variants**: k threads in rotation (chain k semaphores); `acquire(timeout=)` + supervisor so a crashed thread can't wedge the cycle.

### Problem 3 — Building H2O (barrier + counting semaphores)

**Problem**: threads arrive as `hydrogen` or `oxygen`; every group of three that leaves the chamber must be exactly 2 H + 1 O.

**The naive race**: admit everyone and sort it out after — output groups form by arrival order, so `OOH`/`OHHHHO` mixtures escape the chamber; bonds never form. Interleaving: three hydrogens arrive before any oxygen → all three pass the door → invalid molecule.

**Correct solution** (counting semaphores cap each species per cycle; the barrier releases groups of three together):

```python
import threading
class H2O:
    def __init__(self):
        self.h, self.o = threading.Semaphore(2), threading.Semaphore(1)
        self.b = threading.Barrier(3)
    def hydrogen(self):
        with self.h: self.b.wait(); print("H", end="", flush=True)
    def oxygen(self):
        with self.o: self.b.wait(); print("O", end="", flush=True)
h2o = H2O()
threads = [threading.Thread(target=h2o.hydrogen) for _ in range(6)] + \
          [threading.Thread(target=h2o.oxygen) for _ in range(3)]
[t.start() for t in threads]; [t.join() for t in threads]; print()
```

**Freedom argument**: the barrier's contract is the bonding condition — `wait()` blocks *"until all of the threads have made their wait() calls"* then releases them simultaneously (Python docs, [threading — Barrier objects](https://docs.python.org/3/library/threading.html), fetched this session). The semaphores make each barrier *generation* exactly 2 H + 1 O: a third hydrogen can't acquire `h` (2 permits) until one prints and exits, and the next generation can't complete until the current oxygen releases `o` — prints may interleave *within* a molecule, never *across* molecules. **Verified output (5 runs)**: e.g. `OHHOHHOHH` — every consecutive triple is a permutation of `HHO`. **Variants**: N molecules (loop the class); the starvation twist — under sustained oxygen arrivals, can hydrogens starve? In principle yes: Python's semaphore promises no FIFO ordering (see [Locks & Starvation](../concurrency/lock-starvation.md)).

### Problem 4 — Dining Philosophers (deadlock demo, then two fixes)

**Problem**: five philosophers, five forks between them; each needs left + right forks to eat; think, eat, repeat.

**The deadlock, demonstrated**: everyone grabs the left fork before trying the right. Exact interleaving: all five start together, each holds its left fork, each blocks on its right fork — the neighbor's left fork, held. A perfect cycle of holds-and-waits; nobody eats. Verified demo (python3 3.12.14; join-with-timeout as the deadlock detector):

```python
import threading, time
N = 5
forks = [threading.Lock() for _ in range(N)]
ate = [0]*N
def phil(i):
    l, r = forks[i], forks[(i+1) % N]
    for _ in range(3):
        with l:              # grab left fork
            time.sleep(0.1)  # widens the race window
            with r: ate[i] += 1
ts = [threading.Thread(target=phil, args=(i,), daemon=True) for i in range(N)]
[t.start() for t in ts]
t0 = time.time()
for t in ts: t.join(timeout=1.0)
print(f"after {time.time()-t0:.1f}s: {sum(t.is_alive() for t in ts)}/5 philosophers still blocked, meals eaten: {ate}")
```

Verified output: `after 5.0s: 5/5 philosophers still blocked, meals eaten: [0, 0, 0, 0, 0]` — reproducible; without the `sleep` the deadlock is timing-dependent (sometimes one philosopher wins and the cycle never closes), which is why unsleeped tests pass locally and hang in production.

**Fix 1 — resource hierarchy** (number the forks; the last philosopher takes them in reverse):

```python
def phil(i):
    first, second = i, (i+1) % N
    if i == N-1: first, second = second, first   # break the cycle
    for _ in range(3):
        with forks[first]:
            with forks[second]: ate[i] += 1
```

Verified output: `done, blocked=0, meals=[3, 3, 3, 3, 3]`. The argument is Dijkstra's: acquire resources in a globally ascending order — a cycle would need some thread holding a *higher*-numbered fork while waiting for a *lower* one, which the rule makes impossible. It kills **deadlock at zero communication cost**, but guarantees nothing about *starvation* (an unlucky philosopher can lose every race — no fairness property).

**Fix 2 — arbitrator (the waiter)** (cap concurrency at N−1 so a philosopher can always get both forks):

```python
waiter = threading.BoundedSemaphore(N-1)   # at most 4 seated
def phil(i):
    l, r = forks[i], forks[(i+1) % N]
    for _ in range(3):
        with waiter:
            with l, r: ate[i] += 1
```

Verified output: `done, blocked=0, meals=[3, 3, 3, 3, 3]`. With at most four philosophers competing for five forks, someone always gets both — deadlock is structurally impossible, not just unlikely. But like Fix 1 this does **not** prevent starvation; a fair arbitrator (mutex + Condition with FIFO wake order) does. Randomized backoff avoids the *livelock* of fixed-interval retry loops (all philosophers releasing in lockstep). **Variants**: asymmetric grabbing (odd left-first, even right-first); the hold-and-wait cycle as a wait-for graph (see [Deadlock Detection](../concurrency/deadlock-detection.md)).

### Problem 5 — Rate-Limited Logger (token bucket shared across threads)

**Problem**: many threads log; the system as a whole may emit at most N messages per second, no matter which thread asks.

**The naive race**: `if time.time() - last > 1/N: emit()` on a shared variable — two threads read the same stale timestamp and both pass the check. Interleaving: T1 reads `last`, T2 reads `last` (same value) → both compute "allowed" → both emit → 2 messages in one slot. Even an atomic check-and-set fixes only the *counting*, not the *rate*: nothing reconstructs "messages in the last second" after a burst.

**Correct solution** (token bucket under a Condition — the bucket is the shared rate state, the Condition is the wait room):

```python
import threading, time
class TokenBucket:
    def __init__(self, rate, cap=1):
        self.rate, self.cap, self.tokens, self.t0 = rate, cap, float(cap), time.monotonic()
        self.cv = threading.Condition()
    def acquire(self):
        with self.cv:
            while True:
                now = time.monotonic()
                self.tokens = min(self.cap, self.tokens + (now - self.t0)*self.rate)
                self.t0 = now
                if self.tokens >= 1:
                    self.tokens -= 1; return
                self.cv.wait((1 - self.tokens)/self.rate)
bucket = TokenBucket(rate=3, cap=1)   # strict 3 msg/s, no burst
def worker(i):
    for _ in range(2): bucket.acquire()
```

**Freedom argument**: all reads/writes of `tokens` happen inside the Condition's lock, so refill-then-decide is atomic; the predicate loop survives spurious wakeups; `wait((1-tokens)/rate)` sleeps exactly until one token accrues — no busy-wait (and `time.monotonic()` is immune to NTP steps). Verified run (python3 3.12.14, 6 threads × 2 messages, rate=3/s; timestamps from a tiny emit-harness elided from the listing): `+0.000, +0.334, +0.667, +1.001, +1.334, +1.668, +2.001, +2.335, +2.668, +3.002, +3.335, +3.669` s from the first message — dripped at ~1/3s, post-run audit `max messages in any 1.0s sliding window: 3 (cap=3)`. **Variants**: `cap=3` permits a 3-message burst then a drip — the honest contract is "≤ b + r·T messages in any window of length T"; per-key buckets (see [Hot Keys & Sharded Counters](../distributed/advanced/hot-keys-and-sharded-counters.md)); the lossy variant (`acquire(blocking=False)`) for telemetry.

### Key Takeaways

- Every race here is a missing *happens-before edge*: semaphores, barriers, and Conditions draw the edge; sleeps only make races rarer.
- Deadlock requires a cycle of held resources — forbid holding-while-waiting (handoff semaphores, H2O), break the cycle (resource ordering), or bound contention (waiter). Ordering is cheapest; only the fair arbitrator extends to starvation.
- `time.sleep()` in a demo is a measurement instrument (widening an interleaving so it reproduces), never a fix.
- Condition variables need a predicate loop, `notify_all` for multi-predicate waiters, and `time.monotonic()` for timing math.
- Token bucket: state and refill must update under the same lock, and the honest guarantee is a windowed one (b + r·T).

## Cross-References

- [Producer-Consumer](../concurrency/producer-consumer.md) — the bounded-buffer pattern these problems specialize
- [Readers-Writers](../concurrency/readers-writers.md) — the other classic synchronization problem family
- [Deadlock Detection](../concurrency/deadlock-detection.md) — wait-for graphs, detection vs prevention
- [Locks & Starvation](../concurrency/lock-starvation.md) — why semaphores don't promise FIFO fairness
- [CSP Model](../concurrency/csp-model.md) — channel-based alternatives to shared-state handoff
- [Python GIL](../concurrency/python-gil.md) — what the GIL does and doesn't synchronize
- [Hot Keys & Sharded Counters](../distributed/advanced/hot-keys-and-sharded-counters.md) — scaling the token bucket to per-key rate limiting

## References

- [Python threading](https://docs.python.org/3/library/threading.html) — Python Software Foundation (fetched this session): semaphore counter semantics ("atomic counter representing the number of release() calls minus the number of acquire() calls..."), Barrier release semantics, Condition/lock pairing
- [Python concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html)
- [Java BlockingQueue](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/BlockingQueue.html)
- "Print Zero Even Odd", "Print FooBar Alternately", "Building H2O" — LeetCode 1116/1115/1117; "Dining Philosophers" — Dijkstra's classic formulation. Problem pages block automated fetching (403 verified this session), so cited by name per this book's verification policy.
