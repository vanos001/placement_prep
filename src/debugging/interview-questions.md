# Debugging Interview Questions

This section collects debugging-focused interview questions organized by category. Use these to practice articulating your debugging approach out loud.

## Systematic Debugging Approach Questions

### Q1: "Walk me through how you would debug a production issue where users are seeing intermittent 500 errors."

**Expected approach:**
1. **Reproduce**: Check if the error is correlated with specific users, inputs, or times.
2. **Isolate**: Extract correlation IDs from error reports. Query logs and distributed traces to identify which service is failing and why.
3. **Hypothesize**: Is it a recent deployment? A dependency failure? A resource limit? A code path triggered by specific input?
4. **Verify**: Deploy a fix to canary, compare error rates, confirm with the original failing request if possible.
5. **Prevent**: Add regression tests, improve error handling, set up alerting for the root cause metric.

### Q2: "How do you decide between adding logging, writing a test, or using a debugger?"

**Key points:**
- **Debugger**: When the bug is reproducible locally and you need to inspect state interactively.
- **Logging**: When the bug is in production, non-reproducible, or needs historical context.
- **Testing**: When you understand the bug and want to prevent regression and document the expected behavior.
- Often the answer is "all three": use a debugger to understand, logging to confirm in production, and a test to prevent recurrence.

### Q3: "What is your approach when you cannot reproduce a bug?"

**Systematic approach:**
1. Gather more information from the reporter (exact steps, environment, input data).
2. Review logs, traces, and metrics from when the bug occurred.
3. Identify the code path that must have been executed.
4. Look for conditions that would make the bug intermittent (race conditions, resource exhaustion, specific input values, timing dependencies).
5. Write a stress test or fuzzer to increase the probability of reproduction.
6. Add defensive logging and deploy to canary to capture more data when it next occurs.
7. If the bug is rare but high-impact, fix it preventively based on code analysis even without full reproduction.

---

## "Why Is This Code Broken?" Questions

### Q4: "What is wrong with this code?"

```c
char* copy_string(const char* src) {
    char* dest = malloc(strlen(src));  // Bug
    strcpy(dest, src);                 // Bug
    return dest;
}
```

**Answer**: Two bugs. `strlen` does not include the null terminator, so `malloc(strlen(src))` allocates one byte too few. The correct size is `strlen(src) + 1`. Also, no null check on `src` and no check for `malloc` failure. Fix:
```c
char* copy_string(const char* src) {
    if (!src) return NULL;
    size_t len = strlen(src) + 1;
    char* dest = malloc(len);
    if (!dest) return NULL;
    memcpy(dest, src, len);
    return dest;
}
```

### Q5: "What is wrong with this code?"

```python
def process_items(items):
    results = []
    for i in range(len(items)):
        if items[i] % 2 == 0:
            results.append(items[i] * 2)
    return results[1:]  # Bug: intended to skip first?
```

**Answer**: This is a common pattern where `results[1:]` suggests skipping the first result, but this is almost certainly a bug from confusion between 0-indexed and 1-indexed thinking. If the intent is to skip the first result, document why. If not, it is an off-by-one error. Also, the function silently handles empty input (returns empty list) which may or may not be intentional.

### Q6: "What is wrong with this code?"

```java
public class Singleton {
    private static Singleton instance;
    
    public static Singleton getInstance() {
        if (instance == null) {          // Bug: not thread-safe
            instance = new Singleton();
        }
        return instance;
    }
}
```

**Answer**: Not thread-safe — two threads can both see `instance == null` and create two instances. Fix with double-checked locking (volatile + synchronized), use a `synchronized` method (simple but slower), or use an enum-based singleton (the recommended Java approach).

---

## Scenario-Based Debugging Questions

### Q7: "Your application has been running for weeks and gradually slows down. Memory usage increases linearly. How do you diagnose?"

**Approach:**
1. Take a heap dump during high memory usage.
2. Analyze with profiling tools (MAT for Java, Valgrind massif for C/C++, Chrome Memory for JS).
3. Look for the most common object types by retained size.
4. Identify growth patterns: unbounded caches, event listeners not removed, closures capturing large objects, collections with accumulation patterns.
5. Check for resource leaks (file descriptors, connections) which can also cause memory growth indirectly.
6. Fix: add eviction policies to caches, use weak references where appropriate, ensure cleanup in `finally`/`defer` blocks.

### Q8: "A newly deployed service works in staging but fails in production. What do you investigate?"

**Checklist:**
1. **Configuration differences**: Environment variables, secrets, endpoints, feature flags.
2. **Data differences**: Production data may have edge cases not present in staging (null values, unusual characters, very large payloads).
3. **Volume differences**: Connection pool limits, rate limits, timeouts behave differently under load.
4. **Network differences**: DNS resolution, SSL certificates, firewall rules, service discovery.
5. **Dependency versions**: Different library versions, different runtime versions.
6. **Infrastructure differences**: CPU architecture, OS kernel, disk I/O characteristics.
7. **Time-dependent behavior**: Production may trigger code paths at different times (cron jobs, expirations).

### Q9: "A database query that used to take 50ms now takes 5 seconds. How do you debug?"

**Approach:**
1. Check `EXPLAIN ANALYZE` output — has the query plan changed?
2. Check for missing or stale statistics (run `ANALYZE` / `VACUUM ANALYZE` in PostgreSQL).
3. Check if the table has grown significantly (larger index, more data to scan).
4. Check for lock contention (other queries blocking on the same rows).
5. Check for connection pool exhaustion (long-running queries preventing new ones).
6. Check for hardware issues (disk I/O degradation, CPU saturation).
7. Check recent schema changes (removed index, changed column type).
8. Check if the query now returns more data than before (application logic change).

### Q10: "How would you debug a hanging process that is completely unresponsive?"

**Approach:**
1. Check if the process is running (`ps aux`, `top`).
2. Check CPU usage: high CPU = infinite loop; zero CPU = blocked waiting.
3. If blocked, check what it is waiting on:
   - `strace -p <pid>`: What system call is it blocked in? (`futex` = waiting on lock, `read` = waiting on I/O, `poll`/`epoll_wait` = waiting for events).
   - `lsof -p <pid>`: What files/sockets are open?
4. Check for deadlocks (multiple threads blocked on each other).
5. If possible, attach GDB: `gdb -p <pid>` → `info threads`, `thread apply all bt`.
6. Check `/proc/<pid>/status` for process state, `/proc/<pid>/wchan` for wait channel.
7. If unkillable (`kill -9` does not work), it is in uninterruptible sleep (D state) — check for NFS hangs, I/O errors, kernel bugs.

---

## Tips for Debugging Interview Questions

1. **Think aloud**: The interviewer wants to see your reasoning process, not just the answer.
2. **Be systematic**: Start with observation (what do you know?), then hypothesis, then verification.
3. **Name tools**: Mentioning specific tools (GDB, strace, Valgrind, Chrome DevTools, distributed tracing) shows practical experience.
4. **Prioritize**: In time-limited scenarios, describe what you would check first and why.
5. **Admit uncertainty**: "I would start by checking X. If that did not reveal the issue, I would investigate Y." This is more impressive than pretending to know everything.
