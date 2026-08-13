# Architecture Anti-Patterns

A comprehensive catalog of architecture anti-patterns, their consequences, and how to fix them.

---

## 1. Distributed Monolith

### Description
A system that was split into multiple services but still has all the deployment, coupling, and coordination characteristics of a monolith. Services share databases, must be deployed together, and a change in one requires changes in many others.

### Symptoms
- Deploying one service requires deploying several others simultaneously
- A failure in one service brings down the entire system
- Services share the same database or message broker with tight schema dependencies
- Teams cannot work independently on their services
- Integration tests are massive and brittle

### Consequences
- Worst of both worlds: operational complexity of microservices with none of the benefits
- Deployment velocity drops because coordination is required
- Debugging becomes harder (distributed tracing needed, but the system wasn't designed for it)
- Team autonomy is an illusion

### Remediation
- Identify true service boundaries using Domain-Driven Design (DDD) bounded contexts
- Break shared databases: each service owns its data
- Introduce asynchronous communication (events, message queues) between services
- Implement API contracts and versioning
- Deploy services independently with backward-compatible changes
- Consider whether microservices are even needed — a well-structured monolith may be better

---

## 2. Premature Microservices

### Description
Decomposing a system into microservices before understanding the domain, before the team is large enough to benefit, or before having the operational maturity to manage distributed systems.

### Symptoms
- A small team managing 20+ services
- Most "services" are trivial CRUD wrappers
- Network calls between services dominate latency
- No observability, service mesh, or deployment automation
- Developers spend more time on infrastructure than business logic

### Consequences
- Enormous operational overhead for small teams
- Debugging distributed issues without proper tooling is nightmarish
- Network latency and failure handling dominate development time
- The system is harder to understand than a monolith would be

### Remediation
- Start with a well-structured monolith (modular monolith)
- Extract services only when you have a clear need: independent scaling, team autonomy, different technology requirements
- Ensure you have observability (tracing, metrics, logging) before decomposing
- Use the "monolith first" approach — Martin Fowler's recommendation
- Define clear criteria for when to extract a service

---

## 3. Shared Database

### Description
Multiple services or components read from and write to the same database, creating implicit coupling through the data layer.

### Symptoms
- Schema changes require coordinating across multiple teams
- One service's heavy query impacts another service's performance
- Cannot scale services independently because they share the database bottleneck
- Database becomes the single point of failure for the entire system
- Data ownership is unclear

### Consequences
- Tight coupling at the data layer defeats the purpose of service decomposition
- Schema migrations become dangerous and require downtime
- Performance tuning is a zero-sum game between services
- The database becomes the scaling bottleneck

### Remediation
- Each service owns its data (Database per Service pattern)
- Use API calls or events for cross-service data access
- Implement CQRS (Command Query Responsibility Segregation) where appropriate
- Use event sourcing to maintain data consistency across services
- For read-heavy cross-cutting queries, use dedicated read replicas or materialized views

---

## 4. God Service (God Object / God Class)

### Description
A single service (or class) that knows too much or does too much. It accumulates responsibilities over time until it becomes the central hub that everything depends on.

### Symptoms
- One service has hundreds of endpoints or thousands of lines of code
- Every feature request involves changing this service
- It's the most frequently deployed service and the most likely to break
- Team members specialize in different "parts" of the same service
- The service's database has hundreds of tables covering unrelated domains

### Consequences
- Extremely high change risk — any change could break unrelated functionality
- Slow development velocity due to merge conflicts and testing burden
- Cannot scale parts of the system independently
- Knowledge silos form around different parts of the god service
- Onboarding is difficult because the system is too complex to understand

### Remediation
- Apply the Single Responsibility Principle at the service level
- Use Domain-Driven Design to identify bounded contexts
- Extract capabilities into focused services incrementally
- Use the Strangler Fig pattern to gradually replace parts of the god service
- Refactor internally before extracting (clean up interfaces first)

---

## 5. Circular Dependencies

### Description
Two or more components depend on each other directly or transitively, creating a cycle that makes it impossible to understand, test, or deploy them independently.

### Symptoms
- Service A calls Service B which calls Service A
- Module A imports Module B which imports Module A
- Deploying one service requires deploying its dependency first, which requires deploying the first service
- Changes ripple through the cycle unpredictably
- Tests require mocking an entire chain of dependencies

### Consequences
- Impossible to reason about behavior in isolation
- Deployment order becomes a puzzle
- Changes create cascading failures around the cycle
- Testing requires complex setup or integration environments
- Refactoring one component requires understanding the entire cycle

### Remediation
- Identify the cycle and break it by introducing an abstraction layer
- Use dependency inversion: both components depend on an interface, not each other
- Introduce an event bus so components communicate asynchronously
- Merge tightly coupled components back into a single service
- Use architectural fitness functions to detect cycles automatically

---

## 6. Tight Coupling

### Description
Components that know too much about each other's internal implementation, making them impossible to change independently.

### Symptoms
- Changing one component's internal logic requires changes in others
- Components share data structures, internal IDs, or implementation details
- No clear interface contracts between components
- Testing requires instantiating or mocking many dependencies
- Technology choices in one component constrain others

### Consequences
- Changes are risky and expensive
- Cannot replace or upgrade components independently
- Testing is difficult and brittle
- Team velocity decreases as the codebase grows
- Innovation is stifled because changes are too risky

### Remediation
- Define clear interfaces (APIs, events, contracts) between components
- Use dependency injection and inversion of control
- Apply the Law of Demeter (only talk to your immediate neighbors)
- Implement anti-corruption layers between bounded contexts
- Use message queues or event buses for asynchronous decoupling

---

## 7. Chatty Services

### Description
Services that make many fine-grained calls to each other instead of using coarse-grained APIs, resulting in high network overhead and latency.

### Symptoms
- A single user action triggers dozens of service-to-service calls
- Network latency dominates response time
- Services call each other in tight loops
- API designs expose CRUD operations instead of business operations
- N+1 query patterns appear at the service level

### Consequences
- Latency multiplies with each service call
- Network failures become more likely with more calls
- Serialization/deserialization overhead accumulates
- The system becomes fragile under load
- Debugging requires tracing many small calls

### Remediation
- Design coarse-grained APIs that represent business operations
- Use the BFF (Backend for Frontend) pattern to aggregate calls
- Implement GraphQL for flexible data fetching, or gRPC for efficient binary RPC
- Use data denormalization to reduce cross-service queries
- Consider whether services should be merged if they communicate excessively
- Implement batching and caching at the API gateway level

---

## 8. Synchronous Chains

### Description
Long chains of synchronous service calls where each service waits for the next to respond, creating a fragile, slow pipeline.

### Symptoms
- A user request flows through 5+ services synchronously
- Total response time is the sum of all service latencies
- A slow or failing service in the chain blocks the entire request
- Timeout configuration is complex and often wrong
- Error propagation is unclear

### Consequences
- Overall availability is the product of each service's availability (99.9%^5 = 99.5%)
- Latency is additive across the chain
- One slow service degrades the entire user experience
- Retry logic becomes complex and can cause storms
- Timeout configuration requires deep understanding of each service's behavior

### Remediation
- Use asynchronous communication (events, message queues) where possible
- Implement circuit breakers to fail fast when a service is down
- Use the Saga pattern for distributed transactions instead of synchronous chains
- Define clear timeout budgets and propagate them through the chain
- Consider event-driven architecture to decouple services temporally

---

## 9. Retry Storms

### Description
When a service fails, callers retry aggressively, overwhelming the failing service and potentially causing cascading failures across the system.

### Symptoms
- After a brief service hiccup, load spikes to many times normal
- Multiple services retry simultaneously after a failure
- Retry logic uses fixed intervals without jitter
- No limit on retry attempts
- Retries create secondary failures in downstream services

### Consequences
- A minor failure amplifies into a major outage
- The failing service cannot recover because it's overwhelmed by retries
- Downstream services are hammered by retry traffic
- Recovery time is much longer than the original failure
- The system appears to be under a self-inflicted DDoS attack

### Remediation
- Implement exponential backoff with jitter for all retries
- Set maximum retry limits and circuit breakers
- Use idempotency keys to make retries safe
- Implement bulkheads to isolate retry traffic from normal traffic
- Monitor retry rates and alert on anomalies
- Return 429 (Too Many Requests) to signal callers to back off

---

## 10. Thundering Herd

### Description
Many processes or clients simultaneously attempt to access a resource, typically after a cache expiration or service recovery, causing a sudden spike in load.

### Symptoms
- Cache expiration causes a stampede of requests to the database
- A service recovering from downtime receives a flood of queued requests
- Multiple instances of the same job run simultaneously
- Load balancer health checks all fire at the same interval
- All clients refresh their tokens at the same time

### Consequences
- Database or backend service is overwhelmed
- Response times spike dramatically
- The system may enter a failure loop (cache miss → DB overload → slower responses → more cache misses)
- Service recovery is delayed by the stampede of requests

### Remediation
- Use cache locking or request coalescing (only one request fetches from DB)
- Add jitter to scheduled tasks, health checks, and client refresh intervals
- Implement stale-while-revalidate caching strategy
- Use rate limiting at the API gateway
- Pre-warm caches before they expire
- Implement exponential backoff for client reconnection

---

## 11. Cache Stampede

### Description
A specific form of the thundering herd where many requests simultaneously try to regenerate an expired cache entry, all hitting the backend.

### Symptoms
- When a popular cache key expires, all concurrent requests miss the cache
- Database load spikes at predictable intervals (when cache TTLs expire)
- Response times oscillate between fast (cache hit) and slow (cache miss)
- Multiple instances compute the same expensive result simultaneously

### Consequences
- Database overload during cache regeneration
- Increased latency for all users during the stampede
- Potential for cascading failures if the database cannot handle the load
- Wasted compute resources as multiple instances do the same work

### Remediation
- Use lock-based cache regeneration (only one process regenerates)
- Implement probabilistic early expiration (XFetch): each request has a small chance of early refresh
- Use stale-while-revalidate: serve stale data while refreshing in background
- Implement cache warming on deployment
- Use different TTLs with jitter to spread expiration times
- Consider write-through caching

---

## 12. Split Brain

### Description
In a distributed system, a network partition causes two or more parts of the system to believe they are the primary, leading to conflicting state changes.

### Symptoms
- Two nodes both accept writes during a network partition
- Data inconsistencies appear after the partition heals
- Clients connected to different partitions see different data
- Conflict resolution is manual or nonexistent
- The system cannot guarantee linearizability

### Consequences
- Data loss or corruption when conflicting writes are reconciled
- Clients may read stale or inconsistent data
- Manual intervention required to resolve conflicts
- Trust in the system's data integrity is compromised
- Regulatory and compliance issues in financial or healthcare systems

### Remediation
- Use consensus algorithms (Raft, Paxos) for leader election
- Implement fencing tokens to prevent stale leaders from accepting writes
- Choose appropriate consistency models (CP vs. AP) for your use case
- Use CRDTs (Conflict-free Replicated Data Types) where eventual consistency is acceptable
- Implement proper quorum-based reads and writes
- Design for partition tolerance from the start (CAP theorem awareness)

---

## 13. Cascading Failures

### Description
A failure in one component triggers failures in dependent components, which trigger further failures, creating a chain reaction that can bring down the entire system.

### Symptoms
- A single service failure causes multiple other services to fail
- Error rates spike across the system simultaneously
- Services fail in a predictable order (based on dependency chains)
- Recovery requires restarting services in a specific order
- The root cause is far removed from the most visible symptom

### Consequences
- Total system outage from a single component failure
- Recovery time is much longer than the original failure
- The blast radius of any failure is the entire system
- Post-mortems are complex because the failure path is hard to trace
- Confidence in the system erodes with each cascading failure

### Remediation
- Implement circuit breakers at every service boundary
- Use bulkheads to isolate components from each other
- Design for graceful degradation (serve partial results rather than fail completely)
- Implement timeouts and retry limits everywhere
- Use load shedding to protect overloaded services
- Practice chaos engineering to identify cascading failure paths
- Define and test fallback behaviors for every dependency

---

## 14. Single Point of Failure (SPOF)

### Description
A component whose failure causes the entire system to fail, with no redundancy or fallback.

### Symptoms
- One database, one load balancer, one message broker
- No replication or failover configured
- Disaster recovery plans are untested
- The system has no degraded mode of operation
- Component is not designed for horizontal scaling

### Consequences
- Any failure of the SPOF is a total system outage
- Maintenance requires downtime
- Scaling is limited by the SPOF's capacity
- The team is afraid to make changes to the SPOF
- Recovery depends on the SPOF's restoration time

### Remediation
- Add redundancy at every layer (database replicas, multiple load balancers, etc.)
- Implement automatic failover for critical components
- Use active-active or active-passive configurations
- Regularly test failover procedures
- Design the system to operate in degraded mode without any single component
- Use multi-region deployment for critical systems

---

## 15. Noisy Neighbor

### Description
In a shared environment (multi-tenant systems, shared infrastructure), one tenant or workload consumes a disproportionate share of resources, degrading performance for everyone else.

### Symptoms
- One tenant's traffic spike causes slow responses for all tenants
- Resource usage metrics show one tenant consuming most CPU/memory/disk
- Other tenants experience intermittent performance issues
- The problem is intermittent and hard to reproduce
- Shared resource pools are not isolated

### Consequences
- SLA violations for well-behaved tenants
- Customer complaints and churn
- Difficulty attributing costs to tenants
- System capacity planning becomes unreliable
- Support burden increases as tenants blame the platform

### Remediation
- Implement resource quotas and rate limiting per tenant
- Use resource isolation (separate databases, namespaces, or containers)
- Implement fair scheduling and priority queues
- Monitor per-tenant resource usage and alert on anomalies
- Consider tiered service levels with guaranteed resources
- Use separate infrastructure for high-traffic tenants

---

## 16. Configuration Drift

### Description
Over time, the configuration of supposedly identical environments (staging, production, different production instances) diverges, leading to "works in staging but not production" issues.

### Symptoms
- Staging and production behave differently despite identical code
- Different production instances have different configurations
- Manual configuration changes are not tracked in version control
- "Snowflake" environments that cannot be reproduced
- Deployment issues that only occur in specific environments

### Consequences
- Bugs that only manifest in specific environments
- Inability to reproduce issues locally
- Confidence in testing decreases
- Deployment becomes a game of chance
- Onboarding new team members is difficult because environments are undocumented

### Remediation
- Use Infrastructure as Code (IaC) — Terraform, Pulumi, CloudFormation
- Store all configuration in version control
- Use configuration management tools (Ansible, Chef, Puppet)
- Implement GitOps for infrastructure changes
- Regularly audit and reconcile environment configurations
- Use immutable infrastructure (replace, don't patch)
- Implement configuration validation in CI/CD pipelines

---

## 17. Snowflake Servers

### Description
Servers that are unique, hand-configured, and cannot be reproduced. Each server is a "snowflake" — beautiful and irreplaceable.

### Symptoms
- "Don't touch that server, nobody knows how it was configured"
- Server setup is documented in someone's head, not in code
- Different servers have different OS versions, patches, and configurations
- Recovery from failure requires manual reconfiguration
- No one dares to update or patch the server

### Consequences
- Disaster recovery is slow or impossible
- Scaling requires manual setup of new servers
- Security vulnerabilities persist because patching is risky
- Knowledge is lost when team members leave
- Compliance audits are difficult

### Remediation
- Use containerization (Docker) to package applications with their dependencies
- Implement Infrastructure as Code for all server provisioning
- Use configuration management tools for ongoing compliance
- Treat servers as cattle, not pets — replace rather than repair
- Implement automated provisioning and deprovisioning
- Use golden images (AMIs, VM images) as a starting point, then configure via code

---

## 18. Cargo Cult Architecture

### Description
Blindly copying architectural patterns from successful companies (Netflix, Google, Amazon) without understanding why those patterns were chosen or whether they apply to your context.

### Symptoms
- "Netflix uses microservices, so we need microservices" (with 5 developers)
- Implementing Kubernetes for a single-server application
- Using event sourcing for a simple CRUD application
- Building a service mesh for 3 services
- Adopting technologies because they're trendy, not because they solve a problem

### Consequences
- Massive complexity overhead for simple problems
- Team spends most time on infrastructure instead of business value
- The architecture doesn't fit the actual requirements
- Operational burden exceeds team capacity
- Technical debt accumulates because the team can't maintain the complexity

### Remediation
- Start with the simplest architecture that meets your requirements
- Understand the problem a pattern solves before adopting it
- Evaluate patterns against your team's size, skills, and operational capacity
- Use evolutionary architecture — start simple and add complexity as needed
- Ask "what problem does this solve for us specifically?"
- Read the original company's blog posts about why they made those choices

---

## Summary Table

| Anti-Pattern | Key Risk | Primary Fix |
|---|---|---|
| Distributed Monolith | Worst of both worlds | True service boundaries via DDD |
| Premature Microservices | Operational overhead | Modular monolith first |
| Shared Database | Tight coupling | Database per service |
| God Service | Too many responsibilities | SRP, extract focused services |
| Circular Dependencies | Can't reason or deploy independently | Dependency inversion, events |
| Tight Coupling | Can't change independently | Clear interfaces, DI |
| Chatty Services | High latency | Coarse-grained APIs, BFF |
| Synchronous Chains | Multiplicative unavailability | Async communication, sagas |
| Retry Storms | Self-inflicted DDoS | Exponential backoff + jitter |
| Thundering Herd | Spike on cache/recovery | Jitter, request coalescing |
| Cache Stampede | DB overload on cache miss | Lock-based regeneration |
| Split Brain | Conflicting state | Consensus algorithms, fencing |
| Cascading Failures | Total system outage | Circuit breakers, bulkheads |
| Single Point of Failure | No redundancy | Replication, automatic failover |
| Noisy Neighbor | Resource starvation | Quotas, isolation |
| Configuration Drift | Environment inconsistency | IaC, GitOps |
| Snowflake Servers | Can't reproduce | Containers, IaC |
| Cargo Cult Architecture | Unnecessary complexity | Start simple, evolve |
