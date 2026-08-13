# Failure Mode Interview Questions

Questions about failure modes test your operational experience and ability to design resilient systems.

---

## Detection & Diagnosis

### Q1: You notice that every day at 3 AM, response times spike for 5 minutes. How would you investigate?

**Answer**:
1. **Check for scheduled jobs**: Look at crontabs, batch jobs, or scheduled tasks that run at 3 AM
2. **Check cache expiration**: If cache TTLs are set to expire around that time, it could be a cache stampede
3. **Check backups**: Database backups can cause I/O spikes
4. **Check log rotation**: Log rotation and compression can spike CPU/disk
5. **Check for thundering herd**: If multiple instances run the same scheduled job at 3 AM
6. **Check external dependencies**: Maybe a third-party service has maintenance at that time

**Investigation tools**:
- APM traces during the spike window
- Correlate metrics: CPU, memory, disk I/O, network during the spike
- Check application logs for errors during that period
- Query slow query logs for the database

**Most likely fix**: Add jitter to scheduled jobs, move batch processing to a queue, or stagger cache TTLs.

---

### Q2: A service shows 100% CPU usage but normal request rates. What could be wrong?

**Answer**: Several possibilities:

1. **Infinite loop or tight loop bug**: A code path that spins without yielding
2. **Garbage collection thrashing**: Memory pressure causing constant GC
3. **Cryptocurrency miner**: Security breach — a process consuming CPU for mining
4. **Log processing**: Excessive logging or log shipping consuming CPU
5. **DNS resolution loop**: Misconfigured DNS causing constant resolution attempts
6. **Connection retry storm**: Rapidly retrying failed connections

**Investigation**:
```bash
# What's consuming CPU?
top -c -p $(pgrep -d',' java)

# Thread dump (Java)
jstack <pid>

# Profile the process
perf top -p <pid>

# Check for suspicious processes
ps aux --sort=-%cpu | head -20
```

---

### Q3: How would you diagnose a memory leak in a production Java service?

**Answer**: Systematic approach:

1. **Confirm the leak**: Monitor heap usage over time — look for sawtooth pattern where each GC cycle frees less memory
2. **Get a heap dump**: `jmap -dump:format=b,file=heap.bin <pid>` or configure `-XX:+HeapDumpOnOutOfMemoryError`
3. **Analyze the dump**: Use Eclipse MAT or VisualVM to find:
   - Objects with the most retained memory
   - Dominator trees showing what's keeping objects alive
   - Leak suspects report
4. **Common causes**:
   - Unclosed resources (connections, streams)
   - Growing caches without eviction
   - Event listeners not being removed
   - Thread-local variables not being cleaned
   - Static collections that grow over time
5. **Verify the fix**: Deploy to staging, run load tests, monitor heap usage

**Pro tip**: Use `-XX:+UseG1GC -XX:MaxGCPauseMillis=200` to make GC behavior more predictable while investigating.

---

## Prevention & Design

### Q4: How would you design a system to handle a database failover without dropping requests?

**Answer**: Multi-layer approach:

1. **Connection layer**: Use a connection pool that supports failover (PgBouncer, ProxySQL)
2. **Application layer**:
   - Retry logic with exponential backoff for transient failures
   - Circuit breaker to stop retrying if the database is down for extended periods
   - Read from replicas while primary is recovering
3. **Database layer**:
   - Streaming replication with synchronous commit for zero data loss
   - Automatic failover (Patroni, RDS Multi-AZ)
   - Health checks every few seconds
4. **Traffic layer**:
   - Queue writes during failover (accept the request, process later)
   - Return cached data for reads during failover
   - Return 202 Accepted for writes, process asynchronously

**Architecture**:
```
Client → Load Balancer → App Server → Connection Pool → Primary DB
                                     → Read Replica (for reads)
                                     → Queue (for writes during failover)
```

---

### Q5: How do you prevent cascading failures in a microservices architecture?

**Answer**: Defense in depth:

1. **Circuit breakers** (every service-to-service call):
   ```java
   @CircuitBreaker(name = "userService", fallbackMethod = "getUserFallback")
   public User getUser(String id) {
       return userServiceClient.get(id);
   }
   public User getUserFallback(String id) {
       return User.cached(id); // or default user
   }
   ```

2. **Bulkheads** (isolate thread pools per dependency):
   ```java
   @Bulkhead(name = "paymentService", type = Type.THREADPOOL)
   public PaymentResult processPayment(PaymentRequest req) {
       // ...
   }
   ```

3. **Timeouts** (every external call has a timeout):
   - Don't use infinite timeouts
   - Set timeouts based on the downstream service's p99 latency
   - Propagate timeout budgets through the call chain

4. **Load shedding** (drop low-priority traffic when overloaded):
   - Priority queues: process critical requests first
   - Rate limiting: reject excess traffic
   - Return 429 Too Many Requests

5. **Graceful degradation** (serve partial results):
   - If recommendation service is down, show popular items instead
   - If search is down, show cached results
   - If analytics is down, skip tracking

---

### Q6: How would you handle a situation where a third-party payment provider goes down?

**Answer**: Layered fallback strategy:

1. **Immediate (0-5 minutes)**:
   - Circuit breaker trips, stop sending requests to the failed provider
   - Queue payment requests for later processing
   - Show users: "Payment is being processed, you'll receive confirmation shortly"

2. **Short-term (5-30 minutes)**:
   - Switch to backup payment provider (Stripe → Adyen fallback)
   - Process queued payments through the backup
   - Notify operations team

3. **Long-term (30+ minutes)**:
   - If no backup, offer alternative payment methods (bank transfer, invoice)
   - Send status updates to affected users
   - Coordinate with the provider for ETA

4. **Design for this from the start**:
   - Abstract payment logic behind an interface
   - Implement multiple payment provider integrations
   - Use feature flags to switch providers
   - Queue all payment operations for retry capability

---

## Incident Response

### Q7: You're paged at 2 AM because the system is down. Walk me through your process.

**Answer**: Structured incident response:

1. **Assess (2 minutes)**:
   - What's the blast radius? (All users? Specific region? Specific feature?)
   - What changed recently? (Deployment? Config change? Traffic spike?)
   - Is it getting worse or staying stable?

2. **Communicate (1 minute)**:
   - Open an incident channel
   - Notify stakeholders: "We're aware of the issue, investigating"
   - Assign roles: incident commander, communicator, investigator

3. **Mitigate (5-15 minutes)**:
   - **Rollback** if there was a recent deployment
   - **Failover** if a component is down
   - **Scale** if it's a capacity issue
   - **Enable circuit breakers** if it's a cascading failure
   - **Implement load shedding** if it's an overload

4. **Investigate (parallel with mitigation)**:
   - Check dashboards: error rates, latency, traffic, resource usage
   - Check recent changes: deployments, config changes, infrastructure changes
   - Check dependencies: are third-party services healthy?
   - Check logs: what errors are being reported?

5. **Resolve**:
   - Apply the fix
   - Verify the system is recovering
   - Monitor for regression

6. **Post-mortem (next day)**:
   - Document the timeline
   - Identify root cause
   - Create action items to prevent recurrence

---

### Q8: How would you handle a situation where a deployment causes data corruption?

**Answer**: Critical incident — highest priority:

1. **Stop the bleeding**:
   - Immediately rollback the deployment
   - Stop all writes to the affected tables/database
   - Enable read-only mode if possible

2. **Assess the damage**:
   - When did the corruption start? (correlate with deployment time)
   - How many records are affected?
   - Is the corruption still spreading?

3. **Recover the data**:
   - **Best case**: Point-in-time recovery to just before the deployment
   - **If that's not possible**: Restore from the most recent clean backup
   - **If backup is too old**: Use write-ahead logs (WAL) to replay transactions up to the corruption point

4. **Verify**:
   - Run data integrity checks on the restored data
   - Compare record counts and checksums
   - Verify with users that their data is correct

5. **Prevent recurrence**:
   - Add data validation to the code that caused corruption
   - Implement database constraints (CHECK, FOREIGN KEY)
   - Add integration tests for the specific scenario
   - Implement canary deployments to catch issues before full rollout

---

### Q9: What would you do if you discover that your system has been running with split brain for hours?

**Answer**: This is a serious data consistency issue:

1. **Stop both partitions from accepting writes immediately**
2. **Assess the damage**:
   - How many writes went to each partition?
   - Is there overlap (same records written to both)?
   - What's the time window of the split?

3. **Choose a primary**:
   - Which partition has the most recent data?
   - Which partition has the most writes?
   - Which partition is more trustworthy (was it the original primary)?

4. **Reconcile data**:
   - For non-conflicting writes: merge both sets
   - For conflicting writes (same record, different values):
     - Use last-write-wins (if timestamps are trustworthy)
     - Use the primary partition's version
     - Flag for manual review if the data is critical

5. **Recover**:
   - Promote the chosen primary
   - Apply reconciled data
   - Restart the other partition as a replica
   - Verify data consistency

6. **Prevent recurrence**:
   - Implement proper fencing tokens
   - Use consensus algorithms (Raft/Paxos)
   - Set up monitoring for split brain detection
   - Reduce the time to detect partitions

---

## Rapid-Fire Questions

| Question | Answer |
|---|---|
| What's the OOM killer? | Linux kernel process that kills processes when the system runs out of memory. |
| How do you find what's using all disk space? | `du -sh /* \| sort -rh` or `ncdu /` for interactive exploration. |
| What's a health check vs. a readiness check? | Health = "is the service alive?"; Readiness = "is the service ready to receive traffic?" |
| How do you detect a memory leak? | Monitor heap usage over time; look for sawtooth pattern where baseline keeps increasing. |
| What's the difference between a hotfix and a rollback? | Rollback = revert to previous version; Hotfix = deploy a new fix forward. |
| How do you handle a thundering herd on startup? | Add jitter to startup delay, use readiness probes, gradually ramp up traffic. |
| What's graceful degradation? | Serving partial/best-effort results instead of failing completely. |
| How do you test for cascading failures? | Chaos engineering — kill services, inject latency, simulate network partitions. |
| What's a write-ahead log (WAL)? | A log of all database changes before they're applied, used for recovery and replication. |
| How do you prevent data loss during failover? | Synchronous replication — don't acknowledge writes until replicas confirm. |
| What's the difference between RPO and RTO? | RPO = how much data you can lose; RTO = how long recovery takes. |
| How do you handle backpressure? | Rate limiting, queue depth limits, load shedding, tell senders to slow down. |
