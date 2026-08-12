# Production Engineering Interview Questions

Production engineering interviews test your ability to design, operate, and troubleshoot systems at scale. They combine systems knowledge, operational thinking, and problem-solving under pressure. This document covers common interview questions organized by topic, with detailed answers and follow-up discussion points.

## Deployment and Release Management

### Q1: Explain the difference between blue-green and canary deployments. When would you use each?

**Answer:**

Blue-green deployment maintains two identical environments. Traffic is routed entirely to one (blue) while the other (green) receives the new version. Once green is verified, traffic switches atomically. Canary deployment routes a small percentage of traffic to the new version and gradually increases it while monitoring for issues.

**Use blue-green when:**
- You need instant rollback capability
- You can afford the cost of duplicate infrastructure
- Your application has no persistent state that complicates switching
- You want a simple, well-understood deployment model

**Use canary when:**
- You want to validate the new version with real production traffic before full rollout
- You have good observability and automated canary analysis
- You want to minimize infrastructure costs
- You are deploying to a large fleet where gradual rollout reduces risk

**Follow-up:** How would you handle database migrations with blue-green deployments?
The key is backward-compatible migrations using the expand-and-contract pattern. Add new columns without removing old ones, write to both, switch reads, then remove old columns. Both blue and green must work with the current database schema.

### Q2: How do feature flags work, and what are the risks of using them?

**Answer:**

Feature flags are conditional statements in code that enable or disable features without deployment. They are stored in a configuration service and evaluated at runtime. Flags can be toggled for specific users, percentages, or conditions.

**Benefits:** Decouple deployment from release, enable A/B testing, allow quick disabling of problematic features, and support gradual rollouts.

**Risks:**
- **Technical debt**: Stale flags that are never removed create code complexity
- **Testing explosion**: Each flag doubles the number of code paths to test
- **Configuration drift**: Different environments may have different flag states, making debugging harder
- **Performance overhead**: Evaluating many flags on every request adds latency
- **Coupling**: Business logic becomes scattered across flag evaluation points

**Mitigations:** Establish flag lifecycle policies (creation, activation, cleanup), use a flag management service with audit trails, and automate flag removal after full rollout.

### Q3: What is zero-downtime deployment, and what challenges does it present?

**Answer:**

Zero-downtime deployment means releasing new code without any period where the service is unavailable to users. Challenges include:

1. **Backward compatibility**: Old and new code must coexist during the rollout, requiring backward-compatible APIs and database schemas
2. **Database migrations**: Schema changes must follow expand-and-contract patterns
3. **Session management**: Users may hit different versions during rollout; sessions must be externalized
4. **Connection draining**: Old instances must complete in-flight requests before termination
5. **Cache invalidation**: Cached data from the old version may be incompatible with the new version
6. **Load balancer deregistration delay**: There is a gap between when an instance starts shutting down and when the load balancer stops sending traffic

## Graceful Shutdown and Health Checks

### Q4: What is the difference between a liveness probe and a readiness probe? Give examples of what each should check.

**Answer:**

**Liveness probe**: Determines if the process is alive and can make progress. If it fails, the orchestrator restarts the container. It should check for deadlocks, unresponsive threads, or fatal internal states.

Example check: Is the main event loop responsive? Can the process handle a simple internal request? Is a critical background thread still running?

**Readiness probe**: Determines if the process is ready to serve traffic. If it fails, the orchestrator removes it from the load balancer but does not restart it. It should check for dependencies and initialization state.

Example check: Is the database connection pool healthy? Has the cache been warmed? Are downstream dependencies reachable?

**Key insight**: A process can be alive but not ready (e.g., still initializing, database temporarily unavailable). A process should never be ready but not alive (that indicates a misconfigured probe).

### Q5: How do you implement graceful shutdown in a microservices architecture?

**Answer:**

The graceful shutdown sequence:
1. Receive SIGTERM from the orchestrator
2. Mark the instance as shutting down in service discovery
3. Stop accepting new requests (remove from load balancer)
4. Wait for in-flight requests to complete (with a timeout, e.g., 30 seconds)
5. Close external connections (database pools, message queue consumers)
6. Flush buffered data (logs, metrics, pending writes)
7. Exit with code 0

**Challenges in microservices:**
- **Race condition**: The load balancer may still send traffic after SIGTERM. Use a pre-stop hook with a small delay (e.g., `sleep 5`) to give the load balancer time to deregister.
- **Cascading shutdowns**: If service A calls service B, and both are shutting down, implement circuit breakers and set appropriate timeouts.
- **Message consumers**: Stop polling for new messages immediately, finish processing the current message, commit offsets, then exit.
- **Long-running requests**: Set a hard timeout; do not wait indefinitely. Return 503 to clients if new requests arrive during shutdown.

### Q6: A pod keeps restarting in Kubernetes. How do you debug it?

**Answer:**

Systematic debugging approach:

1. **Check pod status**: `kubectl describe pod <name>` — look at Events, Last State, and Restart Count
2. **Check logs**: `kubectl logs <name> --previous` — see logs from the crashed container
3. **Check resource limits**: Is the container OOMKilled? Check memory limits vs actual usage
4. **Check liveness probe**: Is the liveness probe failing too aggressively? Check `initialDelaySeconds` (app might need more startup time), `failureThreshold`, and `timeoutSeconds`
5. **Check node resources**: `kubectl describe node <node>` — is the node under memory/disk pressure?
6. **Check dependencies**: Is the app crashing because it cannot connect to a database or external service?

**Common causes:**
- OOMKill: Increase memory limits or fix memory leaks
- Liveness probe too aggressive: Increase initialDelaySeconds
- Application crash on startup: Check configuration, environment variables, secrets
- Crash loop: Application code bug causing immediate exit

## Incident Response

### Q7: You receive an alert that the error rate on your service has spiked to 15%. Walk me through your response.

**Answer:**

**Minute 0-2 (Triage):**
1. Check the monitoring dashboard to understand the scope: Is it all endpoints or specific ones? All users or a subset?
2. Check recent deployments: `kubectl rollout history` or deployment pipeline — did something change recently?
3. Check dependencies: Are downstream services healthy? Database, cache, third-party APIs?

**Minute 2-5 (Diagnosis):**
4. If a recent deployment correlates with the spike, initiate a rollback
5. If no recent deployment, check infrastructure: node health, network issues, DNS problems
6. Check error logs for patterns: specific error messages, affected user segments, geographic distribution

**Minute 5-15 (Resolution):**
7. Apply the most likely fix:
   - Recent deployment → rollback
   - Dependency down → failover to backup or enable circuit breaker
   - Resource exhaustion → scale up or restart affected pods
   - Configuration change → revert the change
8. Monitor metrics to confirm recovery

**Minute 15+ (If not resolved):**
9. Escalate to team lead and additional team members
10. Open an incident channel and assign an incident commander
11. Update the status page if user-facing impact is confirmed

### Q8: What is a blameless postmortem, and why is it important?

**Answer:**

A blameless postmortem is a structured review of an incident that focuses on understanding what happened and why, without assigning personal blame. It examines systemic factors that allowed the incident to occur and identifies improvements to prevent recurrence.

**Why blameless:**
- **Psychological safety**: Engineers are more likely to report incidents honestly if they won't be punished
- **Systemic thinking**: Incidents are usually caused by multiple contributing factors, not a single person's mistake
- **Better learning**: Blame focuses on the past; systemic improvement focuses on the future
- **Prevention**: Punishing individuals doesn't fix the processes, tools, or gaps that enabled the incident

**Example:**
- **Blameful**: "Alice deployed buggy code and caused the outage"
- **Blameless**: "The integration test suite did not cover this edge case, and the deployment pipeline did not include a canary analysis step that would have caught the regression"

The postmortem should produce concrete action items with owners and due dates to address the identified systemic gaps.

## Monitoring and Observability

### Q9: What is the difference between metrics, logs, and traces? When do you use each?

**Answer:**

**Metrics**: Numerical measurements aggregated over time (e.g., request rate, error rate, latency percentiles, CPU usage). Best for dashboards, alerting, and trend analysis. Stored in time-series databases (Prometheus, InfluxDB).

**Logs**: Discrete event records with timestamps and context (e.g., request logs, error logs, audit logs). Best for debugging specific issues, understanding what happened during an incident, and compliance. Stored in log aggregation systems (ELK, Loki, CloudWatch).

**Traces**: Distributed traces that follow a request across multiple services, showing the full path and timing. Best for debugging latency issues in microservices, understanding service dependencies, and identifying bottlenecks. Stored in tracing systems (Jaeger, Zipkin, Datadog APM).

**The three pillars together:**
- Metrics tell you **something is wrong** (error rate spiked)
- Logs tell you **what went wrong** (specific error message and stack trace)
- Traces tell you **where it went wrong** (which service in the call chain is slow)

### Q10: How do you design effective alerts?

**Answer:**

Effective alerts follow the ** actionable alert ** principles:

1. **Every alert must be actionable**: If there is nothing to do when the alert fires, it should not be an alert. It can be a dashboard metric.
2. **Alert on symptoms, not causes**: Alert on "error rate > 5%" rather than "CPU > 80%". High CPU might not matter; user-facing errors always matter.
3. **Use appropriate thresholds**: Set thresholds based on SLOs and historical data, not arbitrary numbers.
4. **Include context**: The alert message should include what is wrong, the current value, the threshold, and a link to the dashboard/runbook.
5. **Avoid flapping**: Use evaluation windows (e.g., "error rate > 5% for 5 minutes") to avoid alerts that fire and resolve repeatedly.
6. **Severity alignment**: Match alert severity to business impact. A 1% error rate on payments is more critical than a 10% error rate on a non-critical feature.

## Capacity Planning

### Q11: How do you plan for a traffic spike (e.g., Black Friday)?

**Answer:**

1. **Forecast**: Analyze historical traffic patterns. If this is a known event, estimate peak traffic based on previous years plus growth.
2. **Load test**: Run load tests at expected peak traffic levels. Identify the breaking point of each service.
3. **Scale infrastructure**: Pre-scale stateless services (add more replicas). For stateful services (databases), ensure read replicas are available and consider sharding.
4. **Optimize hot paths**: Review and optimize the most critical code paths. Cache aggressively, pre-compute expensive results.
5. **Implement graceful degradation**: Define what features can be disabled under extreme load (e.g., recommendations, search suggestions) to protect core functionality (e.g., checkout).
6. **Set up auto-scaling**: Configure horizontal auto-scaling with appropriate metrics (requests per second, CPU, custom metrics).
7. **Test failover**: Verify that failover mechanisms work: database failover, region failover, CDN failover.
8. **Staff on-call**: Ensure experienced engineers are on-call during the event with clear escalation paths.
9. **Monitor closely**: During the event, watch dashboards for anomalies and be prepared to intervene manually if auto-scaling isn't keeping up.

### Q12: What is an error budget, and how does it influence decision-making?

**Answer:**

An error budget is the allowed amount of unreliability based on the SLO. If the SLO is 99.9% availability, the error budget is 0.1% (approximately 43 minutes per month).

**How it influences decisions:**
- **Budget remaining**: The team can take calculated risks—deploy frequently, experiment with new features, try aggressive optimizations
- **Budget exhausted**: The team must prioritize reliability over features—focus on fixing bugs, improving monitoring, adding redundancy, and reducing deployment velocity
- **Budget tracking**: Regular reviews of error budget consumption drive conversations about the right balance between reliability and feature velocity

This framework removes subjective arguments about "should we deploy?" and replaces them with data-driven decisions based on the remaining error budget.

## Troubleshooting

### Q13: Users report that the API is slow. How do you investigate?

**Answer:**

1. **Confirm the issue**: Check latency dashboards (p50, p95, p99). Is it all endpoints or specific ones?
2. **Check the full stack**:
   - **Load balancer**: Is there a connection queuing? Check active connections and request rates
   - **Application**: Check application-level metrics—thread pool saturation, garbage collection pauses, connection pool exhaustion
   - **Database**: Check query latency, slow query logs, connection counts, lock waits
   - **External dependencies**: Check latency and error rates of downstream services
3. **Use distributed tracing**: Find the trace for a slow request and identify which service/operation is the bottleneck
4. **Check for recent changes**: Deployments, configuration changes, traffic pattern shifts
5. **Check resource utilization**: CPU, memory, disk I/O, network bandwidth on all relevant nodes
6. **Check for noisy neighbors**: In shared infrastructure, other workloads might be consuming resources

### Q14: A service is consuming more memory than expected and getting OOMKilled. How do you debug?

**Answer:**

1. **Confirm OOMKill**: `kubectl describe pod` shows OOMKilled status; `dmesg` on the node shows the OOM killer invocation
2. **Check memory limits**: Are the container memory limits appropriate for the workload?
3. **Profile memory usage**: Use language-specific profilers:
   - Java: Heap dumps with `jmap`, analyze with Eclipse MAT
   - Go: `pprof` heap profiles
   - Python: `tracemalloc`, `memory_profiler`
4. **Look for common causes**:
   - **Memory leaks**: Objects allocated but never freed, growing collections, unclosed resources
   - **Large caches**: In-memory caches that grow without bounds
   - **Connection pools**: Too many database connections, each consuming memory
   - **Large request/response payloads**: Processing very large payloads in memory
5. **Check patterns**: Does memory grow linearly over time (leak)? Does it spike at certain times (traffic pattern)? Does it jump after a deployment (code change)?
6. **Mitigate**: Increase memory limits temporarily, fix the leak, add memory monitoring and alerting
