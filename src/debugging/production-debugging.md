# Production Debugging

Debugging in production is fundamentally different from local development. You cannot attach a debugger, add print statements, or restart at will. Production debugging requires observability infrastructure, safe diagnostic techniques, and rigorous postmortem practices.

## Production Debugging Challenges

| Challenge | Why It Matters | Mitigation |
|----------|---------------|------------|
| No breakpoints | Cannot pause execution in a live system | Distributed tracing, logging, profiling agents |
| Data sensitivity | Cannot inspect real user data | Synthetic requests, anonymized logs, shadow traffic |
| Scale | Cannot manually inspect individual instances | Aggregated metrics, alerting, automated analysis |
| Time pressure | Users are affected right now | Runbooks, pre-built diagnostic dashboards |
| Non-determinism | Issue may not be reproducible on demand | Replay-based debugging, detailed telemetry |
| Risk of harm | Debugging actions can worsen the incident | Read-only diagnostics first, canary shadowing |

---

## Structured Logging for Debugging

Unstructured log messages ("something went wrong with user 123") are nearly useless in production at scale. Structured logging makes logs machine-queryable and debuggable.

### Principles

1. **Log as JSON**: Every log entry is a JSON object with consistent fields.
2. **Include context**: Request ID, user ID, service name, trace ID, timestamp, severity.
3. **Log decisions, not just events**: "Rejecting request because rate limit exceeded" > "Request rejected."
4. **Avoid logging sensitive data**: Never log passwords, tokens, PII, or full request bodies with user data.
5. **Use appropriate levels**: DEBUG (development), INFO (normal operations), WARN (degraded), ERROR (failures), FATAL (unrecoverable).

### Structured Log Entry Example
```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "ERROR",
  "service": "payment-service",
  "trace_id": "abc123def456",
  "span_id": "span789",
  "user_id": "user_456",
  "message": "Payment processing failed",
  "error_code": "GATEWAY_TIMEOUT",
  "payment_id": "pay_789",
  "attempt": 3,
  "duration_ms": 5002,
  "gateway": "stripe"
}
```

### Querying for Debugging
With structured logs, you can query: "Show me all ERROR logs for payment-service where `error_code` is `GATEWAY_TIMEOUT` and `duration_ms` > 3000 in the last hour." This is impossible with unstructured logs.

---

## Correlation IDs and Distributed Tracing

In microservices, a single user request traverses multiple services. Without correlation, you cannot trace a request's path through the system.

### Correlation IDs
A unique identifier (often UUID or ULID) propagated with every request across all services.

- **Propagation mechanism**: HTTP header (`X-Request-ID` or `X-Correlation-ID`), message metadata in queues.
- **Logging**: Every log entry includes the correlation ID.
- **Debugging workflow**: User reports an error → look up the correlation ID from their request → query all logs with that ID across all services.

### Distributed Tracing
Extends correlation IDs with timing and parent-child relationships.

- **Spans**: Each unit of work (HTTP call, DB query, cache lookup) is a span.
- **Trace**: A tree of spans representing the full request lifecycle.
- **Tools**: Jaeger, Zipkin, AWS X-Ray, OpenTelemetry SDK.

```
Trace: abc123def456
├── Span: API Gateway (0ms - 5002ms)
│   ├── Span: Auth Service (2ms - 15ms)
│   ├── Span: Payment Service (18ms - 5002ms)
│   │   ├── Span: DB Query (20ms - 4500ms)
│   │   └── Span: Cache Lookup (4501ms - 4502ms)
│   └── Span: Notification Service (5003ms - 5010ms)
```

**Interview tip**: When asked about debugging microservices, always mention distributed tracing first. It is the single most important tool for production debugging in distributed systems.

---

## Shadow Debugging / Mirroring Traffic

Replay production traffic to a non-production environment for safe debugging.

### How It Works
1. Duplicate incoming requests at the load balancer or service mesh level.
2. Forward copies to a shadow environment (staging, canary).
3. The shadow environment processes requests but responses are discarded.
4. Debugging tools can be attached to the shadow environment safely.

### Use Cases
- Reproducing a production-only bug in a debuggable environment.
- Testing a code change against real traffic before deployment.
- Performance profiling under realistic load.

### Cautions
- **Side effects**: Shadow requests must not write to production databases, send real emails, or call external APIs. Use request deduplication IDs and read-only DB replicas.
- **Cost**: Doubles infrastructure for the shadowed service.
- **Non-determinism**: Shadow environment may behave differently due to timing, data state, and configuration differences.

---

## Feature Flags for Debugging

Feature flags serve double duty: they control feature rollout AND enable targeted debugging.

### Debugging Patterns with Feature Flags
1. **Error isolation**: Disable a suspicious feature globally to confirm it is causing the issue.
2. **Targeted enablement**: Enable verbose logging or debugging mode for a specific user or request path without affecting others.
3. **A/B debugging**: Enable a potential fix for 1% of users and compare error rates.
4. **Kill switches**: Emergency off switch for any feature suspected of causing issues.

### Implementation Considerations
- Flags must be evaluable with minimal latency (in-memory, not database lookup per request).
- Flag changes should propagate quickly (<10 seconds) for emergency debugging.
- Audit trail: who changed what flag and when.

---

## Canary Debugging

Deploy a suspected fix or debugging instrumentation to a small subset of production.

1. Deploy the instrumented version to canary instances (1-5% of traffic).
2. Compare error rates, latency, and log patterns between canary and baseline.
3. If the hypothesis is confirmed (canary shows improvement), gradually expand.
4. If not, roll back and investigate further.

This is safer than deploying to 100% of production and hoping for the best.

---

## Postmortem Analysis

After an incident is resolved, a structured postmortem prevents recurrence.

### Postmortem Template

1. **Incident Summary**: What happened, when, impact (users affected, revenue lost, duration).
2. **Timeline**: Chronological events with timestamps (detection, escalation, mitigation, resolution).
3. **Root Cause Analysis**: The chain of events that led to the incident (5 Whys technique).
4. **What Went Wrong**: Failures in detection, response, or systems.
5. **What Went Well**: Effective processes, tools, or decisions that helped.
6. **Action Items**: Specific, assigned, time-bound tasks to prevent recurrence.

### Blameless Culture
Postmortems must be blameless. The goal is to understand system failures, not assign individual blame. A culture of blame causes people to hide incidents, slowing response and preventing learning.

> "Human error is not the root cause. It is the effect of a system that allowed the error to reach production."

---

## Interview Questions

1. **"A user reports a 500 error. How do you debug this in production?"**
   Extract the correlation ID from the user's request, query logs across all services for that ID, inspect the distributed trace to identify which service failed and why, check recent deployments or config changes, review metrics for anomalies.

2. **"How would you set up observability for a new microservice?"**
   Structured JSON logging with correlation IDs, OpenTelemetry SDK for distributed tracing, Prometheus metrics (request rate, error rate, latency — the RED method), Grafana dashboards, and PagerDuty alerts on error rate spikes.

3. **"A production service is slow but not failing. How do you diagnose?"**
   Check distributed traces for high-latency spans, identify the slow operation (DB query? external API call?), check if it correlates with load (connection pool exhaustion?), check cache hit rates, and review recent schema or index changes.

4. **"You suspect a race condition in production. How do you confirm?"**
   Enable ThreadSanitizer or race detection logging, add detailed logging around the suspicious shared state, use distributed tracing to correlate concurrent requests, and attempt to reproduce in staging with high concurrency load testing.

5. **"What is the most important practice for production debugging?"**
   Observability as a first-class concern. If you build with structured logging, tracing, and metrics from day one, you can debug any production issue. If you add them later, you will be blind when the first incident hits.
