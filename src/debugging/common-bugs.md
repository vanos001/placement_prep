# Common Bugs

Understanding common bug patterns is essential for both preventing and diagnosing defects. This guide covers the most frequent bugs encountered in production systems, along with detection strategies and interview questions.

## Off-by-One Errors

Accessing one element too many or too few. The most pervasive bug in array/string manipulation.

### Common Manifestations
- Loop runs from `0` to `n` instead of `0` to `n-1` (or vice versa).
- `substring(0, n)` vs `substring(0, n-1)` in different languages.
- Off-by-one in pagination (`LIMIT 10 OFFSET 10` skips the 11th item correctly, but `OFFSET 0` may be handled incorrectly).
- Fencepost errors: 10 fence posts need 9 fence sections, not 10.

### Detection
- **Code review**: Scrutinize all loop bounds and array indexing.
- **Testing**: Boundary tests with arrays of size 0, 1, and 2.
- **Sanitizers**: AddressSanitizer catches buffer overflows (read and write).

### Example
```python
# Bug: prints elements 0..9 but tries to access index 10
for i in range(len(arr)):       # i goes 0..9
    print(arr[i])               # Fine
print(arr[len(arr)])            # IndexError! Should be arr[len(arr)-1]

# Bug: processes one fewer element than expected
for i in range(1, len(arr)):    # Skips index 0!
    process(arr[i])
```

---

## Null / None Reference Errors

Attempting to use a null/None/undefined reference as if it were a valid object.

### Common Manifestations
- Dereferencing a null pointer in C/C++ (segfault).
- Calling methods on `null` in Java, `None` in Python, `nil` in Go.
- Accessing properties of `undefined` in JavaScript (TypeError).
- Missing optional fields in JSON responses parsed without null checks.

### Detection
- **Defensive programming**: Validate inputs at function boundaries.
- **Optional types**: Use `Optional<T>`, `?`, `Maybe`, or union types to make nullability explicit.
- **Testing**: Test with null/empty inputs systematically.
- **Static analysis**: Type systems that distinguish nullable from non-nullable (Kotlin, Swift, Rust).

### Prevention Strategies
| Language | Approach |
|----------|---------|
| Rust | `Option<T>` — compiler forces you to handle `None` |
| Kotlin | Nullable types (`String?`) with safe call (`?.`) |
| Java | `Optional<T>`, `@NonNull` annotations |
| Python | Type hints (`Optional[str]`), pyright/mypy |
| Go | Error return values (no null) |

---

## Race Conditions

Output depends on the timing of concurrent operations. Two common categories:

### Data Races
Concurrent unsynchronized access to shared mutable state.

```python
# Bug: counter++ is not atomic (read-modify-write)
counter = 0
# Thread 1: reads 0, writes 1
# Thread 2: reads 0, writes 1
# Result: counter is 1 instead of 2
counter += 1
```

### Time-of-Check to Time-of-Use (TOCTOU)
Checking a condition and acting on it without ensuring the condition still holds.

```python
# Bug: file could be deleted between check and use
if os.path.exists(filename):
    with open(filename) as f:  # FileNotFoundError!
        data = f.read()
```

### Detection
- **ThreadSanitizer**: Detects data races at runtime.
- **Race detectors**: Go's built-in `-race` flag.
- **Code review**: Identify all shared mutable state and verify synchronization.
- **Static analysis**: Tools that detect unsynchronized access patterns.

---

## Deadlocks

Two or more threads wait indefinitely for each other to release resources.

### Necessary Conditions (Coffman Conditions)
All four must hold simultaneously for a deadlock:
1. **Mutual exclusion**: Resources cannot be shared.
2. **Hold and wait**: Thread holds a resource while waiting for another.
3. **No preemption**: Resources cannot be forcibly taken.
4. **Circular wait**: Thread A waits for B's resource, B waits for C's, C waits for A.

### Prevention Strategies
- **Lock ordering**: Always acquire locks in a global order.
- **Timeout**: Use `try_lock` with timeouts instead of blocking indefinitely.
- **Deadlock detection**: Lockdep (Linux kernel), `Thread Deadlock` detection in JVM.
- **Minimize lock scope**: Hold locks for the shortest possible duration.
- **Avoid nested locks**: Refactor to avoid acquiring multiple locks.

---

## Memory Leaks

Memory allocated but never freed, gradually consuming all available memory.

### Common Causes
- **Unreleased references in GC languages**: Caching without eviction, holding references in collections, event listeners not removed.
- **Lost pointers in manual languages**: `malloc` without `free`, ownership confusion in C++.
- **Circular references**: Object A references B, B references A, neither can be collected (especially in reference-counted systems).
- **Global caches without bounds**: Maps that grow indefinitely.
- **Closure captures**: Anonymous functions capturing large objects unintentionally.

### Detection
- **Valgrind memcheck**: For C/C++ programs.
- **Heap profiling**: `gperftools`, `jemalloc` heap profiling.
- **GC logs**: Java verbose GC, Python `gc.get_stats()`.
- **Browser Memory panel**: Heap snapshots to find detached DOM nodes.
- **Production monitoring**: RSS/RSS-ratio alerts, OOM kill monitoring.

---

## Resource Leaks

Similar to memory leaks but for other finite resources.

| Resource | Symptom | Detection |
|----------|---------|-----------|
| File descriptors | "Too many open files" error | `lsof -p <pid>`, `ulimit -n` |
| Database connections | Connection pool exhaustion | Pool metrics, "connection timeout" errors |
| Network sockets | "Address already in use" | `ss -s`, `netstat` |
| Thread pools | New tasks hang waiting | Thread count monitoring, pool queue depth |
| Goroutines/coroutines | Memory growth proportional to request rate | Runtime metrics (`runtime.NumGoroutine()`) |

### Prevention
- **Use `with` statements / RAII**: Ensure resources are released when they go out of scope.
- **Connection pooling with limits**: Prevent unbounded growth.
- **Resource monitoring**: Alert on growing resource counts.
- **Context managers**: Python `with`, Java try-with-resources, C++ RAII, Go `defer`.

---

## Encoding Issues (UTF-8)

Character encoding mismatches cause mojibake (garbled text), data corruption, and crashes.

### Common Manifestations
- `UnicodeDecodeError` in Python when binary data is decoded as UTF-8.
- Mojibake: "Ã©" instead of "é" (UTF-8 bytes interpreted as Latin-1).
- Database storing `?` for non-ASCII characters (charset mismatch).
- Truncated strings when byte-length is used instead of character-length.
- String comparison failures between different normalizations (NFC vs NFD).

### Prevention
- **Always use UTF-8**: For storage, transmission, and processing.
- **Decode at boundaries**: Decode bytes to strings at input, encode back at output.
- **Specify encoding explicitly**: Never rely on platform defaults (`sys.getdefaultencoding()`).
- **Normalize Unicode**: Use NFC normalization for comparison (especially for user-generated text).

---

## Timezone Issues

Time handling is one of the most bug-prone areas in software.

### Common Manifestations
- Using `localtime()` on servers (UTC assumed but local time varies).
- Daylight Saving Time transitions causing off-by-one-hour errors.
- Comparing timestamps without timezone context (naive vs. aware datetime).
- Storing local times in databases (breaks when server timezone changes).
- 30-day month calculations (February, months with 30 vs. 31 days).

### Prevention
- **Store and compute in UTC**: Convert to local time only for display.
- **Use aware datetimes**: Always attach timezone information.
- **Use interval arithmetic**: Add `timedelta` instead of manipulating months/days manually.
- **Use battle-tested libraries**: `datetime` with timezone, `java.time`, `moment.js`, `date-fns`.

---

## Floating Point Comparison

Direct equality comparison of floating-point numbers is unreliable due to representation errors.

```python
# Bug: this is False!
0.1 + 0.2 == 0.3  # False (0.30000000000000004)

# Correct approaches:
import math
math.isclose(0.1 + 0.2, 0.3)  # True

# Or with tolerance:
abs((0.1 + 0.2) - 0.3) < 1e-9

# For financial calculations: use Decimal
from decimal import Decimal
Decimal('0.1') + Decimal('0.2') == Decimal('0.3')  # True
```

### Key Rules
- Never use `==` for floating-point comparison.
- Use epsilon-based comparison (`fabs(a - b) < epsilon`).
- For financial calculations, use integer cents or `Decimal`.
- Be aware of cumulative floating-point error in loops and aggregates.

---

## Uninitialized Variables

Reading a variable before it has been assigned a value.

### Manifestations
- **C/C++**: Undefined behavior—garbage values, crashes, security vulnerabilities.
- **Java**: Compiler error (local variables) or default values (fields: 0, null, false).
- **Python**: `NameError` (undefined) or logic errors (variable defined in wrong scope).
- **Go**: Zero values (0, "", nil) — not a crash but can cause subtle logic errors.

### Prevention
- **Initialize at declaration**: `int count = 0;` not `int count;`.
- **Compiler warnings**: `-Wuninitialized` (GCC/Clang), `-Wall`.
- **Sanitizers**: MemorySanitizer detects use of uninitialized memory.
- **Static analysis**: Tools that warn on use-before-assign.

---

## Interview Questions

1. **"A multithreaded counter occasionally returns incorrect values. What is wrong?"**
   Classic data race: `counter++` is not atomic (read-modify-write). Fix with atomic operations (`std::atomic`, `sync/atomic`), a mutex, or use a channel/actor model to serialize access.

2. **"How would you find and fix a memory leak in a long-running Java service?"**
   Enable verbose GC logging, take a heap dump during high memory usage (`jmap -dump:live,format=b,file=heap.hprof <pid>`), analyze with Eclipse MAT or VisualVM to identify objects with the largest retained size. Look for unbounded collections, unclosed resources, and unintended object retention in caches.

3. **"Why is `0.1 + 0.2 != 0.3` in most programming languages?"**
   IEEE 754 double-precision floating-point cannot exactly represent 0.1 (it is a repeating fraction in binary). The tiny rounding errors accumulate. Use `math.isclose()` or `Decimal` for exact arithmetic.

4. **"How would you prevent deadlocks in a system that acquires multiple locks?"**
   Establish a global lock ordering (always lock A before B, never B before A). Use `try_lock` with timeouts. Minimize lock scope. Consider lock-free data structures or actor models that avoid shared state entirely.

5. **"A service runs fine for hours then crashes with 'too many open files'. What is happening?"**
   Resource leak: file descriptors are being opened but not closed. Check `lsof -p <pid>` during runtime to see open FDs. Common causes: missing `close()`, HTTP clients not closing response bodies, log files opened inside a loop without closing. Fix with context managers, RAII, or explicit cleanup in `finally` blocks.
