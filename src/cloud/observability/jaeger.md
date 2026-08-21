# Jaeger (Distributed Tracing)

Jaeger (pronounced "yay-ger", German for "hunter") is an open-source distributed tracing platform, originally developed at Uber in 2015 and donated to the CNCF (graduated in 2019). It is used to trace requests across microservices, identifying bottlenecks, errors, and latency contributors. This page covers the architecture, the OpenTelemetry integration, the span model, and the production deployment patterns.

## The Problem

A modern web request may flow through 5-20 microservices:

```text
User → API Gateway → Auth Service → Order Service → Inventory Service →
        ↓                                        ↓
        Metrics                                  Shipping Service
                                                  ↓
                                                Payment Service
                                                  ↓
                                                Notification Service
```

When the user sees a 5-second latency, which service is slow? Traditional per-service metrics (Prometheus, dashboards) show each service's P99 latency but don't show which service is on the critical path for this specific request.

Distributed tracing solves this by:
1. Assigning a unique trace ID to each request at the edge.
2. Each service records "spans" (time ranges) for its work.
3. Spans are correlated by trace ID, showing the full call tree.

The visualization: a "waterfall" timeline showing each service's span, with parent-child relationships.

## The Span Model

A span is a single operation within a trace:

```text
Span:
  - trace_id (16 bytes hex): identifies the entire trace
  - span_id (8 bytes hex): identifies this span
  - parent_span_id (8 bytes hex): the parent span (or null for root)
  - operation_name: e.g., "HTTP GET /api/orders"
  - start_time (microsecond precision)
  - duration (microseconds)
  - tags (key-value pairs): e.g., http.status_code=200, error=true
  - logs (timestamped events): e.g., "request received", "sending response"
  - baggage (key-value pairs): propagated across service boundaries
```

A trace is the tree of spans with the same `trace_id`:

```text
Trace 1:
  Span A (HTTP GET /api/orders, 1000 ms)
    ├── Span B (auth.verify_token, 50 ms)
    ├── Span C (orders.find_by_id, 100 ms)
    ├── Span D (inventory.check_stock, 300 ms)
    │     └── Span D1 (postgres.query, 250 ms)
    └── Span E (shipping.schedule, 500 ms)  ← bottleneck!
```

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Application (instrumented with OpenTelemetry SDK)          │
│  - Creates spans via SDK                                     │
│  - Sends spans to collector or directly to backend         │
└─────────────────────────────────────────────────────────────┘
        │
        │ OTLP (gRPC/HTTP)
        ▼
┌─────────────────────────────────────────────────────────────┐
│  OpenTelemetry Collector (optional, for batching)           │
│  - Batches spans                                            │
│  - Translates between formats (Zipkin, OTLP, etc.)         │
│  - Forwards to backend                                      │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Jaeger Backend                                              │
│  - jaeger-collector: receives spans, stores them           │
│  - jaeger-query: queries traces by trace_id, attributes    │
│  - jaeger-ui: web UI for viewing traces                    │
│  - Storage: Cassandra, Elasticsearch, Kafka, or in-memory  │
└─────────────────────────────────────────────────────────────┘
```

The Jaeger backend can run standalone (without the collector) or with the OpenTelemetry collector for batching.

## Instrumentation: OpenTelemetry SDK

The application is instrumented via the OpenTelemetry SDK:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

trace.set_tracer_provider(TracerProvider())

tracer = trace.get_tracer(__name__)

# Manual span creation
with tracer.start_as_current_span("process_order") as span:
    span.set_attribute("order_id", order.id)
    
    # The context (trace_id, span_id) is automatically propagated
    # to downstream calls via headers (W3C TraceContext)
    response = call_downstream_service(order)
    
    if response.status_code != 200:
        span.set_attribute("error", True)
        span.record_exception(response.exception)
```

The SDK also auto-instruments popular libraries:
- HTTP servers (Flask, Django, FastAPI).
- HTTP clients (requests, urllib).
- Databases (SQLAlchemy, psycopg2).
- Message queues (Kafka, RabbitMQ).

```python
# Auto-instrumentation
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()
SQLAlchemyInstrumentor().instrument(engine=engine)
```

## Context Propagation

For a trace to span multiple services, the trace context must propagate across the service boundary. The W3C TraceContext standard (RFC 9200) uses HTTP headers:

```http
GET /api/orders/123 HTTP/1.1
traceparent: 00-0af7654612834bcdef0123456789abcdef-0123456789abcdef-01
tracestate: vendor=value

# 00: version
# 0af7654612834bcdef0123456789abcdef: trace_id (32 hex chars)
# 0123456789abcdef: span_id (16 hex chars)
# 01: trace_flags (sampled=01, not sampled=00)
```

The receiving service extracts the trace context, creates a child span, and continues the trace.

## Sampling

Not every request can be traced — for high-throughput services, tracing every request is too expensive. Sampling picks a subset:

- **Head-based sampling**: at trace creation, decide whether to sample. Random (e.g., 1% of traces) or rule-based (e.g., all errors). Simple but can miss interesting traces.
- **Tail-based sampling**: at trace completion, decide whether to keep. Rule-based (e.g., keep all traces >1s, all errors, all traces with specific attributes). More accurate but expensive (all traces must be buffered).

```yaml
# Tail-based sampling configuration
processors:
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow
        type: latency
        latency: { threshold_ms: 1000 }
      - name: random-10-percent
        type: probabilistic
        probabilistic: { sampling_percentage: 10 }
```

Tail-based sampling is essential for production: it ensures errors and slow requests are always traced, while sampling only 1-10% of normal traffic.

## Production Use Cases

### Performance Analysis

When a user reports a slow request:
1. Get the trace ID from the user's logs or HTTP response header.
2. Search Jaeger UI for the trace.
3. View the waterfall, identify the slow span.
4. Drill into the span's tags/logs to find the root cause.

### Error Diagnosis

When monitoring reports an error spike:
1. Filter Jaeger traces by `error=true`.
2. Group by service / endpoint.
3. Examine the error traces to find the pattern.

### Capacity Planning

Aggregate traces over time:
- Per-service span durations → which service is getting slower over time?
- Per-endpoint throughput → which endpoint is the bottleneck?

## Production Deployment

```yaml
# jaeger.yaml (Kubernetes deployment)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: jaeger
          image: jaegertracing/all-in-one:1.51
          env:
            - name: SPAN_STORAGE_TYPE
              value: elasticsearch
            - name: ES_SERVER_URLS
              value: http://elasticsearch:9200
            - name: ES_TAGS_AS_FIELDS_ALL
              value: "true"
          ports:
            - { containerPort: 16686, name: ui }       # UI
            - { containerPort: 4317, name: otlp-grpc }  # OTLP gRPC
            - { containerPort: 4318, name: otlp-http }  # OTLP HTTP
```

The `all-in-one` image is for dev/testing. For production, use separate `jaeger-collector` and `jaeger-query` deployments with shared storage (Cassandra or Elasticsearch).

## Comparison to Other Tracers

| Aspect | Jaeger | Zipkin | OpenTelemetry native | Datadog |
|--------|--------|--------|------------------------|---------|
| Origin | Uber 2015 | Twitter 2012 | CNCF 2019 | Datadog |
| Backend | Standalone | Standalone | OTel Collector | Cloud |
| UI | Waterfall + flame graph | Waterfall | Standardized | Rich |
| Storage | Cassandra, ES, Kafka | MySQL, ES, in-memory | Pluggable | Datadog Cloud |
| Production users | Uber, Reddit, Apple | Netflix, Microsoft | Newer | Datadog customers |
| Best for | Self-hosted, open-source | Self-hosted simple | Future standard | Cloud-managed |

Zipkin is older and simpler; Jaeger has more features. OpenTelemetry is the standard for instrumentation; the storage/UI backend is Jaeger, Zipkin, or a commercial product.

## Common Pitfalls

1. **Tracing every request in production.** For high-throughput, the trace volume overwhelms the backend. Use sampling.

2. **Forgetting to propagate the trace context.** If a service doesn't extract the trace context from headers, its spans are orphaned (no parent). Use auto-instrumentation where possible.

3. **Forgetting that traces are sampled.** A trace may not exist for a specific request. Don't rely on traces for compliance audits.

4. **Forgetting that span tags are indexed.** High-cardinality tags (e.g., user IDs) bloat the storage and slow queries. Use low-cardinality tags (e.g., service.name).

5. **Forgetting that Jaeger UI is single-tenant.** For multi-tenant deployments, use one of the commercial Jaeger SaaS offerings (e.g., Uptrace, Lightstep).

6. **Forgetting to retain traces for long enough.** Traces are useful for forensics; a 7-day retention is the minimum for production. Tune based on storage cost.

## References

- [Jaeger documentation](https://www.jaegertracing.io/docs/)
- [Jaeger GitHub repository](https://github.com/jaegertracing/jaeger)
- Sigelman et al., "[Dapper, a Large-Scale Distributed Systems Tracing Infrastructure](https://research.google.com/pubs/pub36356/)" (Google 2010) — the original distributed tracing paper
- [OpenTelemetry documentation](https://opentelemetry.io/docs/)
- [W3C TraceContext specification](https://www.w3.org/TR/trace-context/)
- [OpenTelemetry Collector](https://github.com/open-telemetry/opentelemetry-collector)
- [Zipkin documentation](https://zipkin.io/)
- [LWN: Distributed tracing (2020)](https://lwn.net/Articles/815575/)
