# Anti-Pattern Interview Questions

Questions about architecture anti-patterns test your ability to recognize design problems and propose solutions.

---

## Recognition Questions

### Q1: You join a team where deploying any microservice requires deploying three others simultaneously. What anti-pattern is this, and how would you fix it?

**Answer**: This is a **Distributed Monolith**. The services are coupled at the deployment level despite being separate processes.

**Fix approach**:
1. Map the dependencies — why do they need simultaneous deployment?
2. Likely causes: shared database schemas, synchronous API contracts that break on change, shared libraries with breaking changes
3. Introduce backward-compatible API versioning
4. Break shared database dependencies — each service owns its data
5. Use consumer-driven contract tests to ensure compatibility
6. Move to asynchronous event-based communication where possible

**Key insight**: "If you can't deploy it independently, it's not really a separate service."

---

### Q2: A system has 30 microservices but only 4 developers. What's wrong?

**Answer**: This is **Premature Microservices**. The operational overhead of managing 30 services far exceeds what 4 developers can handle.

**Symptoms you'd expect**:
- Developers spend more time on DevOps than business logic
- Observability is poor (no distributed tracing, inconsistent logging)
- Services are trivially simple (CRUD wrappers)
- Deployment pipelines are fragile
- No one understands the full system

**Recommendation**: Consolidate into a modular monolith with 3-5 modules. Extract services only when there's a clear operational need (independent scaling, different tech stack, team boundary).

---

### Q3: How would you detect if a system has a distributed monolith problem?

**Answer**:
1. **Deployment coupling test**: Can you deploy each service independently without coordinating with other teams? If no, it's a distributed monolith.
2. **Failure blast radius**: When one service goes down, how many others are affected? If most, it's a distributed monolith.
3. **Database sharing**: Do multiple services read/write to the same database? If yes, shared database anti-pattern.
4. **Integration test scope**: Are integration tests massive and require all services running? If yes, tight coupling.
5. **Team autonomy**: Can a team make and deploy changes without asking other teams? If no, the boundaries are wrong.

---

## Design Questions

### Q4: Design a system that avoids the synchronous chain anti-pattern for an e-commerce checkout flow.

**Answer**: Instead of a synchronous chain (Order → Payment → Inventory → Shipping → Notification), use an **event-driven saga**:

```
1. Order Service creates order (PENDING) → emits OrderCreated event
2. Payment Service listens, processes payment → emits PaymentCompleted or PaymentFailed
3. Inventory Service listens, reserves stock → emits StockReserved or StockReservedFailed
4. Shipping Service listens, creates shipment → emits ShipmentCreated
5. Notification Service listens, sends confirmation email

On failure at any step:
- Compensating transactions undo previous steps
- PaymentFailed → cancel order, release stock
```

**Benefits**: No synchronous chain, each service operates independently, failures are handled gracefully, the system degrades partially rather than failing completely.

---

### Q5: How would you prevent retry storms in a microservices architecture?

**Answer**: Multi-layered approach:

1. **Exponential backoff with jitter**: `wait = min(base * 2^attempt + random_jitter, max_wait)`
2. **Circuit breakers**: Stop retrying after a threshold of failures (e.g., Hystrix, Resilience4j)
3. **Retry budgets**: Limit retries to a percentage of total requests (e.g., max 10% of traffic can be retries)
4. **Idempotency**: Make all operations idempotent so retries are safe
5. **Server-side 429 responses**: When overloaded, return 429 Too Many Requests
6. **Bulkheads**: Isolate retry traffic from normal traffic
7. **Monitoring**: Alert on retry rate spikes

**Code example**:
```python
import random
import time

def retry_with_backoff(func, max_retries=3, base_delay=1, max_delay=30):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)
            time.sleep(delay + jitter)
```

---

### Q6: How would you fix a shared database anti-pattern without downtime?

**Answer**: Gradual migration using the **Strangler Fig pattern**:

1. **Phase 1 — Shadow writes**: New service writes to both the shared DB and its own DB. Reads still come from the shared DB.
2. **Phase 2 — Dual reads**: New service reads from its own DB, falls back to shared DB if data is missing. Compare results.
3. **Phase 3 — Primary cutover**: New service reads/writes primarily from its own DB. Shared DB receives shadow writes for rollback safety.
4. **Phase 4 — Cleanup**: Remove shared DB dependency. Migrate remaining data.

**Key techniques**:
- Change Data Capture (CDC) to keep databases in sync during migration
- Feature flags to control the migration at each phase
- Data reconciliation jobs to detect and fix inconsistencies
- Rollback plan at each phase

---

## Trade-off Questions

### Q7: When is a shared database acceptable, and when is it an anti-pattern?

**Answer**: It's a spectrum:

**Acceptable**:
- Early-stage startup where speed matters more than scalability
- Read-only shared data (e.g., a shared reference/lookup database)
- When services are genuinely tightly coupled by nature (e.g., order and order-items)
- When the team is small and the operational overhead of separate databases isn't justified

**Anti-pattern**:
- When services need to evolve independently
- When schema changes require coordination across teams
- When one service's queries impact another's performance
- When you need independent scaling

**Key insight**: "The shared database isn't the anti-pattern — the coupling it creates is."

---

### Q8: A colleague suggests adding a circuit breaker to every service call. Is this always a good idea?

**Answer**: Not always. Trade-offs to consider:

**Good cases**:
- Calls to external services (payment gateways, third-party APIs)
- Calls to services with known reliability issues
- Services that are not critical for the current operation (can gracefully degrade)

**Bad cases**:
- Calls to critical internal services where failure is not an option
- When the circuit breaker state machine adds complexity that the team can't monitor
- When the fallback behavior is worse than waiting (e.g., returning incorrect data)
- If the team doesn't have monitoring for circuit breaker state changes

**Key insight**: A circuit breaker without monitoring and alerting is just adding complexity. You need to know when it trips and why.

---

## Scenario Questions

### Q9: You're called into an incident where the system is cascading. What's your immediate approach?

**Answer**:
1. **Stop the bleeding**: Enable circuit breakers or rate limits to prevent the cascade from spreading
2. **Identify the root cause**: Check the dependency graph — which service failed first?
3. **Isolate**: Take the failing component out of the path (disable the feature, redirect traffic)
4. **Communicate**: Tell stakeholders what's happening and the estimated recovery time
5. **Fix or rollback**: Apply the fix or rollback the last deployment
6. **Verify**: Confirm the cascade has stopped and normal traffic is flowing
7. **Post-mortem**: Document the cascade path and add circuit breakers/bulkheads at each point

**Tools you'd use**:
- Distributed tracing (Jaeger, Zipkin) to find the cascade path
- Service mesh (Istio) for circuit breaker configuration
- Load shedding at the API gateway
- Kill switch / feature flags to disable non-critical features

---

### Q10: How would you prevent the "noisy neighbor" problem in a multi-tenant SaaS platform?

**Answer**: Layered approach:

1. **Resource quotas**: CPU, memory, and I/O limits per tenant (cgroups, Kubernetes resource limits)
2. **Rate limiting**: Per-tenant request rate limits at the API gateway
3. **Database isolation**: Connection pool limits per tenant, query timeout limits
4. **Queue isolation**: Separate queues or priority levels per tenant
5. **Monitoring**: Per-tenant resource usage dashboards
6. **Auto-scaling**: Scale up when aggregate demand increases
7. **Tiered architecture**: Premium tenants get dedicated resources

**Implementation example** (Kubernetes):
```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```

---

### Q11: Your team wants to adopt event sourcing because a big tech company uses it. How do you evaluate this decision?

**Answer**: This is a potential **Cargo Cult Architecture** situation. Evaluate with these questions:

1. **What problem does event sourcing solve for us?**
   - Do we need an audit trail? (Maybe use a simple audit log instead)
   - Do we need temporal queries? (Maybe use database snapshots)
   - Do we have complex domain events? (Maybe event sourcing fits)

2. **What's the cost?**
   - Team needs to learn a new paradigm
   - Event schema versioning is complex
   - Rebuilding state from events is slow for large event streams
   - Debugging is harder (you can't just query current state)

3. **What's the team's capacity?**
   - Can they maintain this infrastructure?
   - Do they have experience with eventual consistency?

4. **Alternative**: Start with a traditional database + audit log. If you outgrow it, add event sourcing for specific bounded contexts.

**Key insight**: "Just because Netflix does it doesn't mean your 10-person startup should."

---

## Rapid-Fire Questions

| Question | Answer |
|---|---|
| What's the difference between a circuit breaker and a retry? | Retry attempts the same request again; circuit breaker stops trying entirely after failures. |
| When should you use synchronous vs. asynchronous communication? | Sync for queries and operations needing immediate response; async for commands and events where eventual consistency is OK. |
| What's the strangler fig pattern? | Gradually replacing a legacy system by routing new traffic to the new system while keeping the old one running. |
| How do you detect configuration drift? | Regular automated audits comparing actual state to desired state (IaC plan, config drift detection tools). |
| What's a bulkhead pattern? | Isolating components so a failure in one doesn't affect others, like bulkheads in a ship. |
| How do you prevent split brain? | Use consensus algorithms (Raft/Paxos), fencing tokens, and quorum-based writes. |
| What's the difference between tight coupling and a distributed monolith? | Tight coupling is a general concept; a distributed monolith is a specific case where services are tightly coupled despite being separate processes. |
| When is a god service acceptable? | In early stages when the domain is unclear and the team is small, but plan for decomposition as the system grows. |
