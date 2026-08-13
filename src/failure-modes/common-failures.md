# Common Failure Modes in Production Systems

A catalog of real-world failure modes, how to detect them, prevent them, and recover from them.

---

## 1. Database Outage

### What Happens
The primary database becomes unavailable — crashed, unreachable, or unresponsive. All services that depend on it start failing. Reads fail, writes fail, and the application returns errors to users.

### How to Detect
- Application error rates spike (500 errors, connection timeout exceptions)
- Database connection pool metrics show all connections in use or failed
- Database server monitoring shows it's down (no heartbeat, no process)
- Replica lag metrics go to infinity
- Alert: "Database connection refused" or "Connection timeout"

### How to Prevent
- **Replication**: Set up primary-replica replication with automatic failover
- **Connection pooling**: Use PgBouncer or similar to manage connections gracefully
- **Health checks**: Monitor database health from the application layer
- **Backups**: Regular automated backups with tested restore procedures
- **Read replicas**: Route read traffic to replicas to reduce primary load
- **Multi-region**: For critical systems, deploy databases across regions

### How to Recover
1. Check if it's a crash (restart) or hardware failure (failover to replica)
2. If using automatic failover, verify the replica promoted correctly
3. If manual failover, promote the replica and update connection strings
4. Check for data loss (replication lag at time of failure)
5. Investigate root cause (OOM, disk full, corrupt WAL, etc.)
6. Restore from backup if data is corrupted

---

## 2. Cache Outage / Cache Stampede

### What Happens
The cache layer (Redis, Memcached) goes down or a popular cache key expires simultaneously. All requests hit the database directly, overwhelming it.

### How to Detect
- Cache hit rate drops to near zero
- Database CPU and connection count spike
- Application latency increases dramatically
- Cache server monitoring shows it's down
- Pattern: latency spike correlates with cache TTL expiration

### How to Prevent
- **Cache redundancy**: Run Redis in cluster mode or Sentinel for automatic failover
- **Stale-while-revalidate**: Serve stale cache while refreshing in background
- **Cache locking**: When a cache miss occurs, only one request fetches from DB
- **Circuit breaker**: If cache is down, skip it rather than failing
- **Jittered TTLs**: Add random jitter to cache TTLs to prevent synchronized expiration
- **Rate limiting**: Limit how many requests can bypass the cache

### How to Recover
1. Restart the cache server or failover to a replica
2. Implement request coalescing to prevent stampede on the database
3. Enable rate limiting on the database temporarily
4. Warm the cache with the most frequently accessed keys
5. Monitor database load and scale if necessary

---

## 3. DNS Outage

### What Happens
DNS resolution fails — services cannot resolve hostnames to IP addresses. Internal service discovery breaks, external API calls fail, and users cannot reach your application.

### How to Detect
- Services report "host not found" or "DNS resolution failed" errors
- Health checks fail for all external dependencies simultaneously
- Network connectivity exists (ping by IP works) but hostname resolution fails
- All services fail at the same time (suggests shared infrastructure failure)

### How to Prevent
- **DNS redundancy**: Use multiple DNS providers (e.g., Route53 + Cloudflare)
- **Local DNS caching**: Cache DNS results at the application and OS level
- **IP fallback**: For critical dependencies, have IP addresses as fallback
- **Short TTLs for changes, long TTLs for stability**: Balance between agility and resilience
- **Internal DNS**: Run your own DNS for internal services (Consul, CoreDNS)
- **DNS monitoring**: Monitor DNS resolution from multiple locations

### How to Recover
1. Switch to backup DNS provider
2. Clear local DNS caches if records are stale
3. Use IP addresses directly for critical connections
4. Contact DNS provider for status updates
5. Implement DNS-over-HTTPS as an alternative resolution path

---

## 4. Certificate Expiry

### What Happens
TLS/SSL certificates expire, causing HTTPS connections to fail. Browsers show security warnings, API calls fail with certificate errors, and service-to-service TLS handshakes break.

### How to Detect
- Certificate expiry monitoring (check days until expiry for all certs)
- Browser warnings about expired certificates
- API clients report SSL handshake failures
- Automated alerts: "Certificate expires in X days"
- Health checks that verify TLS certificate validity

### How to Prevent
- **Automated renewal**: Use Let's Encrypt with certbot for automatic renewal
- **Certificate monitoring**: Track expiry dates for all certificates
- **Alerting**: Alert at 30, 14, 7, and 1 day before expiry
- **Centralized management**: Use a certificate management platform (Vault, AWS ACM)
- **Long-lived certs for internal services**: Use private CAs with longer validity
- **Automated rotation**: Rotate certificates automatically before expiry

### How to Recover
1. Renew the expired certificate immediately
2. Deploy the new certificate to all affected services
3. Clear certificate caches if applicable
4. Verify all services are using the new certificate
5. Set up automated renewal to prevent recurrence

---

## 5. Disk Full

### What Happens
A server's disk fills up — logs, temp files, data growth, or a runaway process consumes all available space. Services crash, writes fail, and the system becomes unstable.

### How to Detect
- Disk usage monitoring alerts at 80%, 90%, 95%
- Application errors: "No space left on device"
- Log rotation failures
- Database write failures
- Container eviction in Kubernetes (ephemeral storage limits)

### How to Prevent
- **Log rotation**: Implement proper log rotation with size and time limits
- **Monitoring**: Alert on disk usage trends, not just thresholds
- **Auto-scaling**: Use cloud storage that scales automatically
- **Cleanup jobs**: Scheduled jobs to remove old files, temp data, and logs
- **Separate partitions**: Keep logs, data, and temp files on separate volumes
- **Quotas**: Set disk quotas for users and applications

### How to Recover
1. Identify what's consuming disk space (`du -sh /* | sort -rh`)
2. Remove unnecessary files (old logs, temp files, core dumps)
3. Move data to a larger volume or expand the disk
4. Fix the root cause (log rotation, cleanup job, data archival)
5. Set up monitoring to alert before it happens again

---

## 6. Memory Leak

### What Happens
A service gradually consumes more memory over time until it runs out, gets killed by the OOM killer, or causes the system to swap heavily, making everything slow.

### How to Detect
- Memory usage steadily increases over time (sawtooth pattern in graphs)
- Service restarts correlate with memory exhaustion
- OOM killer entries in system logs (`dmesg | grep -i oom`)
- Application becomes slow before crashing (swapping)
- Container restarts due to memory limits

### How to Prevent
- **Memory profiling**: Regularly profile your application for memory leaks
- **Heap dumps**: Configure automatic heap dumps before OOM
- **Resource limits**: Set memory limits on containers and processes
- **Restart policies**: Configure automatic restarts when memory exceeds threshold
- **Code review**: Look for common leak patterns (unclosed connections, growing caches, event listeners)
- **Monitoring**: Track memory usage trends and alert on growth patterns

### How to Recover
1. Restart the affected service (immediate relief)
2. Analyze heap dumps to find the leak source
3. Fix the leak in code and deploy the fix
4. If the leak is in a dependency, update or replace it
5. Implement periodic restarts as a temporary workaround

---

## 7. CPU Saturation

### What Happens
CPU usage reaches 100% — the server can't process requests fast enough. Response times increase, requests timeout, and the system becomes unresponsive.

### How to Detect
- CPU usage consistently above 80-90%
- Request latency increases proportionally to CPU usage
- Request queue depth increases
- Thread pool exhaustion (all threads busy)
- Load average exceeds number of CPU cores

### How to Prevent
- **Horizontal scaling**: Add more instances behind a load balancer
- **Auto-scaling**: Scale based on CPU metrics
- **Profiling**: Identify CPU-intensive operations and optimize them
- **Caching**: Cache expensive computations
- **Async processing**: Move CPU-intensive work to background queues
- **Rate limiting**: Limit request rate to match processing capacity

### How to Recover
1. Scale horizontally (add more instances)
2. Identify the CPU-intensive process (`top`, `htop`, `pidstat`)
3. Check for runaway processes or infinite loops
4. Implement load shedding to drop low-priority requests
5. Optimize the hot code path

---

## 8. Connection Exhaustion

### What Happens
The database or service runs out of available connections. New requests can't get a connection and fail with "too many connections" errors.

### How to Detect
- Database metrics: active connections at or near `max_connections`
- Application errors: "connection pool exhausted" or "too many connections"
- Connection pool metrics: all connections in use, requests waiting for connections
- Latency increase as requests wait for available connections

### How to Prevent
- **Connection pooling**: Use PgBouncer, ProxySQL, or application-level pooling
- **Pool size tuning**: Set appropriate pool sizes (not too many, not too few)
- **Connection timeouts**: Set aggressive timeouts to release idle connections
- **Read replicas**: Distribute read connections across replicas
- **Monitoring**: Alert when connection usage exceeds 80% of max

### How to Recover
1. Identify which application is holding connections (`pg_stat_activity`)
2. Kill idle or long-running connections
3. Increase `max_connections` temporarily (requires restart)
4. Deploy a connection pooler (PgBouncer) if not already in use
5. Fix the application that's leaking connections

---

## 9. Thread Exhaustion

### What Happens
A service runs out of available threads — all threads are busy processing requests or waiting on I/O. New requests are queued or rejected.

### How to Detect
- Thread pool metrics: active threads at maximum, queue depth increasing
- Application stops accepting new connections
- Response times spike as requests wait in the queue
- Health checks fail (the service is alive but can't respond)

### How to Prevent
- **Async I/O**: Use non-blocking I/O (NIO, async/await) instead of thread-per-request
- **Thread pool tuning**: Set thread pools appropriately — roughly `CPU cores + 1` for CPU-bound work, and `CPU cores × (1 + wait/compute ratio)` (often 2×–10× cores) for I/O-bound work
- **Timeouts**: Set timeouts on all I/O operations to prevent threads from blocking indefinitely
- **Circuit breakers**: Fail fast when downstream services are slow
- **Load shedding**: Reject requests when the thread pool is nearly full

### How to Recover
1. Identify what threads are doing (thread dumps: `jstack`, `kill -3`)
2. If threads are blocked on a dependency, enable circuit breaker
3. Restart the service to clear the thread pool
4. Increase thread pool size as a temporary measure
5. Fix the root cause (slow dependency, missing timeout, connection leak)

---

## 10. File Descriptor (FD) Exhaustion

### What Happens
A process runs out of file descriptors — can't open new files, sockets, or connections. New connections are refused, and the service becomes unresponsive.

### How to Detect
- System errors: "Too many open files"
- `lsof -p <pid> | wc -l` shows FD count near the limit
- Connection failures with no apparent network issue
- Monitoring: FD usage approaching `ulimit -n`

### How to Prevent
- **Increase limits**: Set appropriate `ulimit` values in system configuration
- **Connection pooling**: Reuse connections instead of creating new ones
- **Close resources**: Ensure all files and sockets are properly closed
- **Monitoring**: Track FD usage per process
- **Leak detection**: Audit code for unclosed resources

### How to Recover
1. Identify which process is consuming FDs (`lsof -p <pid>`)
2. Check for leaked connections or unclosed files
3. Increase the FD limit temporarily (`ulimit -n 65536`)
4. Restart the affected process
5. Fix the resource leak in code

---

## 11. Network Partition

### What Happens
A network split separates parts of the system — nodes can't communicate with each other. This can cause split brain, data inconsistency, and service unavailability.

### How to Detect
- Services report connection timeouts to specific peers
- Cluster health checks show nodes as unreachable
- Data inconsistency between partitions
- Quorum-based systems report loss of quorum
- Monitoring: inter-node latency spikes or packet loss

### How to Prevent
- **Redundant network paths**: Multiple network interfaces, availability zones
- **Consensus algorithms**: Use Raft/Paxos for leader election
- **Health checks**: Detect partitions quickly with frequent heartbeats
- **Timeout configuration**: Set appropriate timeouts for inter-node communication
- **Network monitoring**: Monitor packet loss, latency, and connectivity between nodes

### How to Recover
1. Identify the partition (which nodes can't communicate)
2. If automatic failover is configured, verify it worked correctly
3. Manually intervene if needed (force quorum, restart minority partition)
4. After the partition heals, verify data consistency
5. Resolve conflicting writes if necessary

---

## 12. Clock Skew

### What Happens
Servers have different times — clocks are not synchronized. This causes issues with TLS handshakes, token validation, log correlation, distributed transactions, and event ordering.

### How to Detect
- TLS handshake failures: "certificate not yet valid" or "certificate has expired"
- JWT token validation failures: "token not yet valid" or "token expired"
- Log timestamps are inconsistent across servers
- Distributed transactions fail with timing-related errors
- Monitoring: NTP offset metrics show significant drift

### How to Prevent
- **NTP synchronization**: Run NTP on all servers and monitor offset
- **Cloud provider time**: Use cloud provider's time synchronization (AWS Time Sync, Google NTP)
- **Monitoring**: Alert when clock offset exceeds a threshold (e.g., 100ms)
- **Tolerance**: Build tolerance for small clock differences into your applications
- **Logical clocks**: Use vector clocks or Lamport timestamps for event ordering instead of wall clock time

### How to Recover
1. Force NTP sync on affected servers (`ntpd -g` or `chronyc makestep`)
2. Verify all servers are synchronized
3. Retry failed operations (TLS handshakes, token validations)
4. If using logical clocks, no recovery needed — the system is self-consistent

---

## 13. Corrupted Data

### What Happens
Data in the database or cache becomes corrupted — wrong values, missing fields, inconsistent state. This can be caused by bugs, hardware failures, or race conditions.

### How to Detect
- Application errors when reading data (unexpected nulls, type mismatches)
- Data validation checks fail
- Checksums don't match
- Users report incorrect data
- Inconsistencies between related records

### How to Prevent
- **Database constraints**: Use foreign keys, check constraints, and unique constraints
- **Application validation**: Validate data before writing
- **Transactions**: Use transactions for multi-step operations
- **Checksums**: Store checksums with critical data
- **Backups**: Regular backups with point-in-time recovery
- **Data integrity checks**: Scheduled jobs to verify data consistency

### How to Recover
1. Identify the scope of corruption (which tables, which records, which time range)
2. Stop the source of corruption (fix the bug, stop the race condition)
3. Restore from backup to a point before the corruption
4. Replay transactions from the write-ahead log if available
5. Verify data integrity after recovery

---

## 14. Partial Deployment

### What Happens
A deployment succeeds on some instances but fails on others, leaving the system in an inconsistent state — some instances running the old version, some the new version.

### How to Detect
- Version endpoints show different versions across instances
- Health checks pass on some instances, fail on others
- Users experience inconsistent behavior depending on which instance serves them
- Deployment pipeline reports partial failure
- Monitoring: error rate varies by instance

### How to Prevent
- **Rolling deployments**: Deploy to one instance at a time and verify
- **Health checks**: Include application-specific health checks in deployment
- **Rollback automation**: Automatically rollback if health checks fail
- **Immutable deployments**: Deploy new instances rather than updating existing ones
- **Canary deployments**: Deploy to a small percentage of instances first
- **Deployment verification**: Verify each instance before proceeding to the next

### How to Recover
1. Rollback all instances to the previous version
2. Identify why the deployment failed on some instances
3. Fix the issue and redeploy
4. Consider using blue-green deployments to avoid partial deployments

---

## 15. Rollback Failure

### What Happens
A deployment needs to be rolled back, but the rollback itself fails — the previous version can't be redeployed, database migrations can't be reversed, or the rollback process is broken.

### How to Detect
- Rollback command fails or times out
- System is stuck in a partially deployed state
- Database schema is incompatible with the previous version
- Health checks fail after rollback attempt

### How to Prevent
- **Forward-compatible migrations**: Never make breaking database changes in a single deployment
- **Test rollbacks**: Practice rollbacks in staging environments
- **Backward-compatible code**: Write code that works with both old and new database schemas
- **Separate schema and code changes**: Deploy schema changes separately from code changes
- **Rollback scripts**: Write and test rollback scripts as part of the deployment process
- **Blue-green deployments**: Keep the old environment running until the new one is verified

### How to Recover
1. If database rollback fails, manually fix the schema
2. Deploy a hotfix that's compatible with the current schema
3. If all else fails, restore from backup
4. Document what went wrong and improve the rollback process

---

## 16. Dependency Outage

### What Happens
A third-party service (payment gateway, email provider, CDN, authentication provider) goes down, and your system can't function without it.

### How to Detect
- Errors from the dependency's API (5xx, timeout, connection refused)
- Your service's error rate increases
- Users report specific functionality not working
- Dependency status page shows incidents

### How to Prevent
- **Circuit breakers**: Stop calling the dependency when it's failing
- **Fallbacks**: Provide degraded functionality when the dependency is down
- **Caching**: Cache dependency responses to survive brief outages
- **Multiple providers**: Have backup providers for critical dependencies
- **Async processing**: Queue requests and process them when the dependency recovers
- **SLA monitoring**: Track dependency SLAs and alert on degradation

### How to Recover
1. Enable circuit breaker to stop hammering the failing dependency
2. Switch to fallback behavior (cached data, degraded functionality)
3. Switch to backup provider if available
4. Monitor the dependency's status page
5. When the dependency recovers, gradually restore normal traffic

---

## 17. Cascading Failure

### What Happens
A failure in one component triggers failures in dependent components, creating a chain reaction. The system fails in a predictable order based on the dependency graph.

### How to Detect
- Error rates spike across multiple services simultaneously
- Services fail in dependency order (downstream first, then upstream)
- The root cause service may not be the one with the highest error rate
- Monitoring: service health dashboard shows a wave of failures

### How to Prevent
- **Circuit breakers**: Prevent failures from propagating
- **Bulkheads**: Isolate components so one failure doesn't affect others
- **Timeouts**: Set aggressive timeouts to prevent waiting for failed services
- **Load shedding**: Drop low-priority traffic to protect critical paths
- **Graceful degradation**: Serve partial results rather than failing completely
- **Chaos engineering**: Test failure scenarios regularly

### How to Recover
1. Identify the root cause service (the first one to fail)
2. Enable circuit breakers to stop the cascade
3. Implement load shedding to reduce pressure
4. Fix or restart the root cause
5. Gradually restore traffic as services recover

---

## 18. Retry Storm

### What Happens
When a service fails, callers retry aggressively, creating a self-inflicted DDoS that prevents the service from recovering.

### How to Detect
- Traffic spikes to many times normal after a brief failure
- The service can't recover despite being healthy
- Retry traffic dominates normal traffic in metrics
- Multiple services retry simultaneously

### How to Prevent
- **Exponential backoff with jitter**: Spread retries over time
- **Retry budgets**: Limit retries to a percentage of traffic
- **Circuit breakers**: Stop retrying after a threshold
- **Idempotency**: Make operations safe to retry
- **Server-side 429**: Tell callers to back off

### How to Recover
1. Enable circuit breakers to stop retries
2. Implement rate limiting at the load balancer
3. Wait for the service to recover
4. Gradually restore normal traffic flow

---

## 19. Thundering Herd

### What Happens
Many clients simultaneously try to access a resource — typically after a cache expires, a service recovers, or a scheduled job triggers at the same time.

### How to Detect
- Sudden traffic spikes at predictable intervals (cache TTL expiration)
- Load spikes correlated with specific events (service recovery, cron jobs)
- Database CPU spikes when cache misses occur
- Multiple instances of the same job running simultaneously

### How to Prevent
- **Jitter**: Add random delays to scheduled tasks and cache TTLs
- **Request coalescing**: Only one request fetches from the backend
- **Stale-while-revalidate**: Serve stale data while refreshing
- **Rate limiting**: Limit the rate of cache misses
- **Pre-warming**: Warm caches before they expire

### How to Recover
1. Enable rate limiting to protect the backend
2. Implement request coalescing if not already in place
3. Warm the cache with frequently accessed data
4. Add jitter to prevent the problem from recurring

---

## Summary: Quick Reference

| Failure | Key Symptom | First Action |
|---|---|---|
| Database Outage | Connection errors | Failover to replica |
| Cache Outage | Latency spike | Skip cache, protect DB |
| DNS Outage | Host not found | Use IP fallback |
| Cert Expiry | SSL errors | Renew certificate |
| Disk Full | Write failures | Clean up, expand disk |
| Memory Leak | OOM kills | Restart service |
| CPU Saturation | High latency | Scale horizontally |
| Connection Exhaustion | Pool exhausted | Kill idle connections |
| Thread Exhaustion | No response | Thread dump, restart |
| FD Exhaustion | Too many open files | Close leaks, restart |
| Network Partition | Partial connectivity | Verify quorum |
| Clock Skew | Token failures | Force NTP sync |
| Corrupted Data | Validation errors | Restore from backup |
| Partial Deployment | Inconsistent versions | Rollback all |
| Rollback Failure | Can't revert | Hotfix forward |
| Dependency Outage | Third-party errors | Circuit breaker |
| Cascading Failure | Wave of failures | Find root cause |
| Retry Storm | Traffic spike | Circuit breaker |
| Thundering Herd | Predictable spikes | Add jitter |
