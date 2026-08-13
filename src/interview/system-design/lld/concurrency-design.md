# Concurrency in LLD

## Why Concurrency Matters

Modern applications handle multiple requests simultaneously. Understanding concurrency is essential for designing thread-safe, performant systems.

## Thread Safety

### The Problem

```python
# ❌ Not thread-safe
class Counter:
    def __init__(self):
        self.count = 0
    
    def increment(self):
        self.count += 1  # This is NOT atomic!
        # Read count → Add 1 → Write count
        # Thread A reads 5, Thread B reads 5
        # Thread A writes 6, Thread B writes 6
        # Expected: 7, Actual: 6 (race condition!)
```

### Solutions

#### 1. Locks (Mutex)
```python
import threading

class ThreadSafeCounter:
    def __init__(self):
        self.count = 0
        self._lock = threading.Lock()
    
    def increment(self):
        with self._lock:  # Only one thread can enter at a time
            self.count += 1
    
    def get_count(self) -> int:
        with self._lock:
            return self.count
```

#### 2. Reentrant Locks (RLock)
```python
import threading

class BankAccount:
    def __init__(self, balance: float):
        self.balance = balance
        self._lock = threading.RLock()  # Can be acquired multiple times by same thread
    
    def transfer(self, other: 'BankAccount', amount: float):
        with self._lock:
            self.balance -= amount
            other.deposit(amount)  # This also acquires lock - RLock allows re-entry
    
    def deposit(self, amount: float):
        with self._lock:
            self.balance += amount
```

#### 3. Read-Write Locks
```python
import threading

class ReadWriteLock:
    def __init__(self):
        self._readers = 0
        self._read_lock = threading.Lock()
        self._write_lock = threading.Lock()
    
    def acquire_read(self):
        with self._read_lock:
            self._readers += 1
            if self._readers == 1:
                self._write_lock.acquire()
    
    def release_read(self):
        with self._read_lock:
            self._readers -= 1
            if self._readers == 0:
                self._write_lock.release()
    
    def acquire_write(self):
        self._write_lock.acquire()
    
    def release_write(self):
        self._write_lock.release()

class ThreadSafeCache:
    def __init__(self):
        self._cache = {}
        self._rw_lock = ReadWriteLock()
    
    def get(self, key: str):
        self._rw_lock.acquire_read()
        try:
            return self._cache.get(key)
        finally:
            self._rw_lock.release_read()
    
    def set(self, key: str, value):
        self._rw_lock.acquire_write()
        try:
            self._cache[key] = value
        finally:
            self._rw_lock.release_write()
```

## Immutability

The simplest way to achieve thread safety — make objects immutable.

```python
from dataclasses import dataclass
from typing import Tuple

# Immutable data class
@dataclass(frozen=True)
class Point:
    x: float
    y: float
    
    def translate(self, dx: float, dy: float) -> 'Point':
        # Returns new instance instead of modifying
        return Point(self.x + dx, self.y + dy)

# Immutable with frozenset
@dataclass(frozen=True)
class User:
    user_id: int
    name: str
    email: str
    roles: frozenset  # Immutable set

# Usage
p1 = Point(1, 2)
p2 = p1.translate(3, 4)  # New point, p1 unchanged
print(p1)  # Point(x=1, y=2)
print(p2)  # Point(x=4, y=6)
```

### Java Immutable Class
```java
public final class Point {
    private final double x;
    private final double y;
    
    public Point(double x, double y) {
        this.x = x;
        this.y = y;
    }
    
    public double getX() { return x; }
    public double getY() { return y; }
    
    public Point translate(double dx, double dy) {
        return new Point(x + dx, y + dy);
    }
    
    // No setters - immutable!
}
```

## Concurrency Primitives

### Semaphore
```python
import threading

class ConnectionPool:
    def __init__(self, max_connections: int):
        self._semaphore = threading.Semaphore(max_connections)
        self._connections = []
    
    def get_connection(self):
        self._semaphore.acquire()  # Blocks if pool is empty
        return self._connections.pop()
    
    def release_connection(self, conn):
        self._connections.append(conn)
        self._semaphore.release()

# Usage - limits concurrent connections
pool = ConnectionPool(max_connections=5)
```

### Condition Variables
```python
import threading

class BlockingQueue:
    def __init__(self, max_size: int):
        self._queue = []
        self._max_size = max_size
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
    
    def put(self, item):
        with self._not_full:
            while len(self._queue) >= self._max_size:
                self._not_full.wait()  # Wait until space available
            self._queue.append(item)
            self._not_empty.notify()  # Signal that queue is not empty
    
    def get(self):
        with self._not_empty:
            while len(self._queue) == 0:
                self._not_empty.wait()  # Wait until item available
            item = self._queue.pop(0)
            self._not_full.notify()  # Signal that queue is not full
            return item
```

### Atomic Operations
```python
import threading

class AtomicReference:
    def __init__(self, initial_value=None):
        self._value = initial_value
        self._lock = threading.Lock()
    
    def get(self):
        with self._lock:
            return self._value
    
    def set(self, new_value):
        with self._lock:
            self._value = new_value
    
    def compare_and_set(self, expected, new_value):
        with self._lock:
            if self._value == expected:
                self._value = new_value
                return True
            return False
```

## Thread-Safe Data Structures

### Thread-Safe Singleton
```python
import threading

class Singleton:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # Double-checked locking
                    cls._instance = super().__new__(cls)
        return cls._instance
```

### Thread-Safe Cache
```python
import threading
from collections import OrderedDict

class ThreadSafeLRUCache:
    def __init__(self, capacity: int):
        self._cache = OrderedDict()
        self._capacity = capacity
        self._lock = threading.Lock()
    
    def get(self, key: str):
        with self._lock:
            if key not in self._cache:
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return self._cache[key]
    
    def put(self, key: str, value):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self._capacity:
                self._cache.popitem(last=False)  # Remove oldest
```

## Async Patterns

### Producer-Consumer Pattern
```python
import threading
import queue
import time

class Producer(threading.Thread):
    def __init__(self, task_queue: queue.Queue, name: str):
        super().__init__()
        self.task_queue = task_queue
        self.name = name
    
    def run(self):
        for i in range(5):
            task = f"Task-{i}"
            self.task_queue.put(task)
            print(f"{self.name} produced {task}")
            time.sleep(0.1)

class Consumer(threading.Thread):
    def __init__(self, task_queue: queue.Queue, name: str):
        super().__init__()
        self.task_queue = task_queue
        self.name = name
        self.daemon = True  # Thread will exit when main program exits
    
    def run(self):
        while True:
            task = self.task_queue.get()
            if task is None:  # Poison pill to stop
                break
            print(f"{self.name} processing {task}")
            time.sleep(0.2)
            self.task_queue.task_done()

# Usage
task_queue = queue.Queue(maxsize=10)

producers = [Producer(task_queue, f"Producer-{i}") for i in range(2)]
consumers = [Consumer(task_queue, f"Consumer-{i}") for i in range(3)]

for p in producers:
    p.start()
for c in consumers:
    c.start()

for p in producers:
    p.join()

# Send poison pills to stop consumers
for _ in consumers:
    task_queue.put(None)
```

### Thread Pool
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def process_task(task_id: int) -> str:
    time.sleep(0.5)  # Simulate work
    return f"Task {task_id} completed"

# Create thread pool with 4 workers
with ThreadPoolExecutor(max_workers=4) as executor:
    # Submit tasks
    futures = [executor.submit(process_task, i) for i in range(10)]
    
    # Process results as they complete
    for future in as_completed(futures):
        result = future.result()
        print(result)
```

## Java Concurrency

### Synchronized Methods
```java
public class BankAccount {
    private double balance;
    
    public synchronized void deposit(double amount) {
        balance += amount;
    }
    
    public synchronized void withdraw(double amount) {
        if (balance >= amount) {
            balance -= amount;
        } else {
            throw new IllegalStateException("Insufficient funds");
        }
    }
    
    public synchronized double getBalance() {
        return balance;
    }
}
```

### ReentrantLock
```java
import java.util.concurrent.locks.ReentrantLock;

public class BankAccount {
    private double balance;
    private final ReentrantLock lock = new ReentrantLock();
    
    public void transfer(BankAccount other, double amount) {
        lock.lock();
        try {
            if (balance >= amount) {
                balance -= amount;
                other.deposit(amount);
            }
        } finally {
            lock.unlock();  // Always unlock in finally
        }
    }
}
```

### ConcurrentHashMap
```java
import java.util.concurrent.ConcurrentHashMap;

public class ThreadSafeCache<K, V> {
    private final ConcurrentHashMap<K, V> cache = new ConcurrentHashMap<>();
    
    public V get(K key) {
        return cache.get(key);
    }
    
    public void put(K key, V value) {
        cache.put(key, value);
    }
    
    public V computeIfAbsent(K key, Function<K, V> mappingFunction) {
        return cache.computeIfAbsent(key, mappingFunction);
    }
}
```

## Common Concurrency Issues

### 1. Race Condition
```python
# ❌ Race condition
def withdraw(self, amount):
    if self.balance >= amount:  # Thread A checks: balance = 100, amount = 80 ✓
                                # Thread B checks: balance = 100, amount = 80 ✓
        self.balance -= amount  # Thread A: balance = 20
                                # Thread B: balance = -60 (problem!)

# ✅ Fixed with lock
def withdraw(self, amount):
    with self._lock:
        if self.balance >= amount:
            self.balance -= amount
```

### 2. Deadlock
```python
# ❌ Deadlock potential
def transfer(account_a, account_b, amount):
    with account_a.lock:  # Thread 1: Lock A, Thread 2: Lock B
        with account_b.lock:  # Thread 1: Wait B, Thread 2: Wait A → Deadlock!
            account_a.balance -= amount
            account_b.balance += amount

# ✅ Fixed with consistent lock ordering
def transfer(account_a, account_b, amount):
    # Always lock in same order (by ID)
    first = min(account_a, account_b, key=lambda a: a.id)
    second = max(account_a, account_b, key=lambda a: a.id)
    
    with first.lock:
        with second.lock:
            account_a.balance -= amount
            account_b.balance += amount
```

### 3. Starvation
```python
# ❌ High-priority thread monopolizes lock
# ✅ Use fair lock (FIFO ordering)
self._lock = threading.Lock()  # Not guaranteed fair

# Java: fair lock
ReentrantLock lock = new ReentrantLock(true);  // Fair lock
```

## Interview Tips

1. **Identify shared state** — "What data is accessed by multiple threads?"
2. **Choose appropriate synchronization** — Lock, semaphore, atomic, immutable
3. **Consider performance** — Read-write locks for read-heavy workloads
4. **Mention deadlock prevention** — "We'll use consistent lock ordering"
5. **Discuss thread pools** — "Use a thread pool to limit concurrent connections"
6. **Consider immutability** — "Make this class immutable for thread safety"
7. **Show awareness of issues** — Race conditions, deadlocks, starvation

## Common Mistakes

- ❌ Not synchronizing shared state
- ❌ Using coarse-grained locks (performance)
- ❌ Not releasing locks (always use try-finally or context manager)
- ❌ Creating too many threads (use thread pools)
- ❌ Ignoring deadlock potential
- ❌ Not considering immutability as a solution

## Cross-References

- [SOLID Principles](./solid.md) — SRP for concurrent classes
- [Design Patterns](./design-patterns.md) — Singleton thread safety
- [Error Handling](./error-handling.md) — Error handling in async
- [LRU Cache](./cache-lld.md) — Thread-safe cache implementation
- [Notification Service](./notification-service.md) — Async notification delivery
- [Concurrency Overview](../../../concurrency/overview.md)
- [Producer-Consumer](../../../concurrency/producer-consumer.md)
- [Readers-Writers](../../../concurrency/readers-writers.md)
- [OS Synchronization](../../../os/synchronization/mutex.md)
