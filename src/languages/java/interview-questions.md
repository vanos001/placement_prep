# Java Interview Questions

## JVM and Memory

### Q1: Explain the JVM memory areas.

| Area | Contents | Thread |
|------|----------|--------|
| **Heap** | Objects, arrays | Shared |
| **Stack** | Frames, local variables | Per-thread |
| **Method Area** | Class metadata, constant pool | Shared |
| **PC Register** | Current instruction address | Per-thread |
| **Native Stack** | Native method calls | Per-thread |

### Q2: What is the String Pool?

A special area in the heap (and since JDK 7, in the heap itself) that stores string literals. When you create a string literal, Java checks the pool first. If it exists, the existing reference is returned. This saves memory.

```java
String a = "hello"; // Pooled
String b = "hello"; // Same reference
String c = new String("hello"); // New object
a == b; // true
a == c; // false
a.intern() == b; // true
```

### Q3: How does garbage collection work?

1. **Mark** — Find all reachable objects (GC roots: local vars, static vars, threads)
2. **Sweep** — Deallocate unreachable objects
3. **Compact** — Move live objects together (optional, reduces fragmentation)

Generational hypothesis: Most objects die young. Young gen uses copying collector. Old gen uses mark-sweep-compact.

### Q4: What is a memory leak in Java?

Despite GC, memory leaks can occur:
- **Static collections** — Objects added to static maps/lists never removed
- **Unclosed resources** — Connections, streams not closed
- **Inner classes** — Holding reference to outer class
- **ThreadLocal** — Not cleaned up after use
- **Caching without eviction** — Unbounded caches

### Q5: How to tune GC?

```bash
# Common JVM flags
-Xms512m          # Initial heap size
-Xmx2g            # Maximum heap size
-Xss512k          # Stack size
-XX:NewRatio=2    # Old:Young ratio
-XX:MaxGCPauseMillis=200  # G1 target pause
-XX:+UseG1GC      # Use G1 collector
-XX:+UseZGC       # Use ZGC
```

## Concurrency

### Q6: What is the Java Memory Model (JMM)?

The JMM defines:
- **Visibility** — When writes by one thread are visible to others
- **Ordering** — When operations can be reordered
- **Atomicity** — Which operations are atomic

```java
// volatile: guarantees visibility and ordering
private volatile boolean running = true;

// synchronized: establishes happens-before
synchronized (lock) {
    // All changes visible to next synchronized block
}
```

### Q7: What is a deadlock?

```java
// Classic deadlock
Thread 1: lock(A) → lock(B)
Thread 2: lock(B) → lock(A)
// Circular wait → deadlock

// Prevention: always lock in same order
Thread 1: lock(A) → lock(B)
Thread 2: lock(A) → lock(B)
```

### Q8: CountDownLatch vs CyclicBarrier?

| CountDownLatch | CyclicBarrier |
|----------------|---------------|
| One-time use | Reusable |
| One thread waits for N | N threads wait for each other |
| countDown() + await() | await() |
| Asymmetric | Symmetric |

### Q9: What is CompletableFuture?

```java
CompletableFuture.supplyAsync(() -> fetchData())
    .thenApply(data -> transform(data))
    .thenAccept(result -> save(result))
    .exceptionally(ex -> handleError(ex));

// Combining futures
CompletableFuture.allOf(future1, future2, future3).join();
```

### Q10: ThreadLocal and its pitfalls?

```java
ThreadLocal<User> currentUser = ThreadLocal.withInitial(() -> null);
currentUser.set(user);
User u = currentUser.get();

// Pitfalls:
// 1. Memory leak if not removed (especially in thread pools)
// 2. Can cause stale data in thread pools
// 3. Hard to debug

// Best practice: always clean up
try {
    currentUser.set(user);
    doWork();
} finally {
    currentUser.remove();
}
```

## Collections

### Q11: How does HashMap work internally?

```java
// Structure: Array of Nodes (buckets)
// Hash: (h = key.hashCode()) ^ (h >>> 16)
// Index: (n - 1) & hash

// Collision resolution:
// Java 7: Linked list
// Java 8+: Linked list → Red-Black tree (threshold: 8 entries)

// Resizing: doubles capacity when size > capacity * loadFactor (0.75)
```

### Q12: ArrayList vs LinkedList?

| ArrayList | LinkedList |
|-----------|------------|
| Random access O(1) | Sequential access O(n) |
| Insert/remove at end O(1) | Insert/remove anywhere O(1) if at position |
| Memory efficient (array) | More memory (node pointers) |
| Cache friendly | Cache unfriendly |

### Q13: What is ConcurrentHashMap?

```java
// Java 8+: fine-grained locking
// No full synchronization
// CAS operations for updates
// Synchronized only on specific bins

ConcurrentHashMap<String, Integer> map = new ConcurrentHashMap<>();
map.put("key", 1);
map.computeIfAbsent("key", k -> expensiveComputation());
```

### Q14: Comparable vs Comparator?

```java
// Comparable: natural ordering (in the class)
class Student implements Comparable<Student> {
    public int compareTo(Student other) {
        return this.name.compareTo(other.name);
    }
}

// Comparator: custom ordering (external)
Comparator<Student> byAge = Comparator.comparingInt(s -> s.age);
students.sort(byAge);
```

## OOP and Design

### Q15: Abstract class vs Interface?

| Abstract Class | Interface |
|----------------|-----------|
| Can have state | No state (only constants) |
| Constructor | No constructor |
| Single inheritance | Multiple implementation |
| Partial implementation | Contract only (Java 7) |
| Default methods (Java 8+) | Default methods (Java 8+) |

### Q16: SOLID principles in Java?

```java
// S - Single Responsibility
class UserAuth { /* only auth logic */ }
class UserRepo { /* only data access */ }

// O - Open/Closed
// Extend behavior without modifying existing code
interface Payment { void pay(double amount); }
class CreditCard implements Payment { /* ... */ }
class PayPal implements Payment { /* ... */ }

// L - Liskov Substitution
// Subtypes must be substitutable for base types

// I - Interface Segregation
interface Readable { void read(); }
interface Writable { void write(); }

// D - Dependency Inversion
class Service {
    private final Repository repo; // Depend on abstraction
    Service(Repository repo) { this.repo = repo; }
}
```

### Q17: What is dependency injection?

```java
// Without DI (tight coupling)
class Service {
    private Repository repo = new DatabaseRepo(); // Hard-coded
}

// With DI (loose coupling)
class Service {
    private final Repository repo;
    Service(Repository repo) { this.repo = repo; } // Injected
}

// Spring DI
@Service
public class UserService {
    private final UserRepository repo;
    
    @Autowired
    public UserService(UserRepository repo) {
        this.repo = repo;
    }
}
```

## Modern Java

### Q18: What are records?

```java
// Immutable data carrier (Java 16+)
public record Point(int x, int y) {}

// Auto-generates:
// - Constructor
// - Getters (x(), y())
// - equals(), hashCode(), toString()
// - Cannot be extended (final)

Point p = new Point(1, 2);
p.x(); // 1
```

### Q19: What are sealed classes?

```java
// Restrict which classes can extend (Java 17+)
public sealed class Shape 
    permits Circle, Rectangle, Triangle {}

public final class Circle extends Shape { /* ... */ }
public final class Rectangle extends Shape { /* ... */ }
public non-sealed class Triangle extends Shape { /* ... */ }

// Pattern matching (Java 21+)
double area = switch (shape) {
    case Circle c -> Math.PI * c.radius() * c.radius();
    case Rectangle r -> r.width() * r.height();
    case Triangle t -> 0.5 * t.base() * t.height();
};
```

### Q20: What are virtual threads?

```java
// Java 21+: lightweight threads managed by JVM
// Millions of virtual threads on few platform threads

Thread.startVirtualThread(() -> {
    System.out.println("Running on virtual thread");
});

// Structured concurrency (Preview)
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    Future<String> user = scope.fork(() -> fetchUser());
    Future<Order>  order = scope.fork(() -> fetchOrder());
    scope.join();
    return new Response(user.resultNow(), order.resultNow());
}
```

## Related Topics

- [JVM Internals](./jvm.md) — JVM architecture deep dive
- [Java GC](./gc.md) — Garbage collection algorithms
- [Concurrency](../../concurrency/) — General concurrency concepts
- [Spring Boot](../../frameworks/spring-boot/) — Enterprise framework
- [OS Threads](../../os/threads/) — OS-level threading
