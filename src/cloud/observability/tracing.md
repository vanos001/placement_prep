# Distributed Tracing

## Introduction

Distributed tracing tracks requests as they flow through multiple services in a microservices architecture. It provides a visual map of the request path, identifies bottlenecks, and helps debug issues across service boundaries. Each request gets a unique trace ID, and each service operation creates a span.

## Why Distributed Tracing?

```mermaid
graph TB
    subgraph "Monolith - Easy to Debug"
        REQ_MONO[Request] --> MONO[Monolith - Single Process]
        MONO --> LOG_MONO[Single Log File]
        LOG_MONO --> DEBUG_MONO[Find issue in one place]
    end

    subgraph "Microservices - Hard to Debug"
        REQ_MICRO[Request] --> SVC1[Service A]
        SVC1 --> SVC2[Service B]
        SVC1 --> SVC3[Service C]
        SVC2 --> SVC4[Service D]
        SVC3 --> SVC4
        SVC4 --> DB[Database]

        LOG1[Log A] -.-> |Which log matches?| ISSUE[Where is the bottleneck?]
        LOG2[Log B] -.-> ISSUE
        LOG3[Log C] -.-> ISSUE
        LOG4[Log D] -.-> ISSUE
    end
```

**Without tracing:** You have logs from 5 services but no way to correlate them for a single request.

**With tracing:** One trace ID follows the request through all services—you can see exactly where time was spent.

## Core Concepts

### Trace

A trace represents the entire journey of a request through the system:

```mermaid
graph LR
    TRACE[Trace: abc123] --> S1[Span: API Gateway - 250ms]
    S1 --> S2[Span: Auth Service - 15ms]
    S1 --> S3[Span: Order Service - 200ms]
    S3 --> S4[Span: Payment Service - 150ms]
    S3 --> S5[Span: Inventory Check - 30ms]
    S4 --> S6[Span: DB Query - 50ms]
```

### Span

A span represents a single unit of work within a trace:

```mermaid
graph TB
    SPAN[Span] --> NAME[Operation Name]
    SPAN --> START[Start Time]
    SPAN --> DUR[Duration]
    SPAN --> TRACE_ID[Trace ID]
    SPAN --> SPAN_ID[Span ID]
    SPAN --> PARENT[Parent Span ID]
    SPAN --> ATTR[Attributes / Tags]
    SPAN --> EVENTS[Events / Logs]
    SPAN --> STATUS["Status (OK, ERROR)"]
```

| Span Field | Description | Example |
|-----------|-------------|---------|
| **Operation Name** | What this span represents | `HTTP GET /api/orders` |
| **Trace ID** | Unique ID for the entire trace | `abc123def456` |
| **Span ID** | Unique ID for this span | `span789` |
| **Parent Span ID** | Parent span (empty for root) | `span001` |
| **Start Time** | When the span started | `2024-01-15T10:30:45.123Z` |
| **Duration** | How long the span took | `150ms` |
| **Attributes** | Key-value metadata | `http.method=GET`, `db.system=postgresql` |
| **Events** | Timestamped annotations | `cache.miss`, `retry.attempt` |
| **Status** | OK, ERROR, UNSET | `ERROR` |

### Span Relationships

```mermaid
sequenceDiagram
    participant Client
    participant Gateway as API Gateway (Span A)
    participant Order as Order Service (Span B)
    participant Payment as Payment Service (Span C)
    participant DB as Database (Span D)

    Client->>Gateway: Request (Trace: abc123)
    Note over Gateway: Span A: start

    Gateway->>Order: Forward (propagate trace_id)
    Note over Order: Span B: start (parent: Span A)

    Order->>Payment: Charge card (propagate trace_id)
    Note over Payment: Span C: start (parent: Span B)

    Payment->>DB: Query (propagate trace_id)
    Note over DB: Span D: start (parent: Span C)
    DB-->>Payment: Result
    Note over DB: Span D: end (50ms)
    Note over Payment: Span C: end (150ms)

    Payment-->>Order: Payment complete
    Note over Order: Span B: end (200ms)

    Order-->>Gateway: Order confirmed
    Note over Gateway: Span A: end (250ms)

    Gateway-->>Client: 201 Created
```

## Context Propagation

Context propagation is how trace information is passed between services:

### HTTP Headers (W3C Trace Context)

```mermaid
graph LR
    SVC_A[Service A] --> |traceparent: 00-abc123-span001-01| SVC_B[Service B]
    SVC_B --> |traceparent: 00-abc123-span002-01| SVC_C[Service C]
```

**W3C Trace Context Format:**
```
traceparent: 00-<trace-id>-<parent-span-id>-<trace-flags>
```

| Field | Description | Example |
|-------|-------------|---------|
| **Version** | Always `00` | `00` |
| **Trace ID** | 32 hex chars (128-bit) | `abc123def456789012345678` |
| **Parent Span ID** | 16 hex chars (64-bit) | `span00100000000` |
| **Trace Flags** | `01` = sampled | `01` |

**Other Propagation Formats:**

| Format | Header | Used By |
|--------|--------|---------|
| **W3C Trace Context** | `traceparent` | OpenTelemetry (standard) |
| **B3** | `X-B3-TraceId`, `X-B3-SpanId` | Zipkin, Istio |
| **Jaeger** | `uber-trace-id` | Jaeger |
| **AWS X-Ray** | `X-Amzn-Trace-Id` | AWS X-Ray |

### Message Queue Propagation

```mermaid
sequenceDiagram
    participant Producer
    participant Queue as Message Queue
    participant Consumer

    Producer->>Queue: Publish message
    Note over Queue: Message attributes:<br/>traceparent: 00-abc123-span001-01

    Consumer->>Queue: Consume message
    Note over Consumer: Extract traceparent from attributes
    Note over Consumer: Create child span (parent: span001)
```

## OpenTelemetry

OpenTelemetry (OTel) is the CNCF standard for observability instrumentation—providing a unified API and SDK for traces, metrics, and logs.

### OpenTelemetry Architecture

```mermaid
graph TB
    subgraph "Application"
        SDK[OTel SDK]
        TRACER[Tracer API]
        METER[Meter API]
        LOGGER[Logger API]
    end

    subgraph "OTel Collector"
        RECEIVER[Receivers]
        PROCESSOR[Processors]
        EXPORTER[Exporters]

        RECEIVER --> PROCESSOR
        PROCESSOR --> EXPORTER
    end

    subgraph "Backends"
        JAEGER[Jaeger]
        PROM[Prometheus]
        LOKI_T[Loki]
    end

    TRACER --> SDK
    METER --> SDK
    LOGGER --> SDK
    SDK --> RECEIVER
    EXPORTER --> JAEGER
    EXPORTER --> PROM
    EXPORTER --> LOKI_T
```

### OTel Collector Configuration

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024

  memory_limiter:
    check_interval: 1s
    limit_mib: 512

  attributes:
    actions:
      - key: environment
        value: production
        action: upsert

exporters:
  otlp/jaeger:
    endpoint: jaeger-collector:4317
    tls:
      insecure: true

  prometheus:
    endpoint: 0.0.0.0:8889

  logging:
    loglevel: info

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch, attributes]
      exporters: [otlp/jaeger, logging]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
```

### Instrumenting Applications

```python
# Python OpenTelemetry instrumentation
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# Setup
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="otel-collector:4317"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Auto-instrument Flask and requests
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# Manual instrumentation
tracer = trace.get_tracer(__name__)

def process_order(order_id):
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order_id)

        with tracer.start_as_current_span("validate_order"):
            validate(order_id)

        with tracer.start_as_current_span("charge_payment") as payment_span:
            payment_span.set_attribute("payment.method", "credit_card")
            result = charge(order_id)
            if not result.success:
                payment_span.set_status(StatusCode.ERROR)
                payment_span.record_exception(result.error)
```

```javascript
// Node.js OpenTelemetry instrumentation
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-grpc');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({
    url: 'http://otel-collector:4317',
  }),
  instrumentations: [getNodeAutoInstrumentations()],
});

sdk.start();
```

## Jaeger

Jaeger is an open-source distributed tracing system originally developed by Uber.

### Jaeger Architecture

```mermaid
graph TB
    subgraph "Jaeger Components"
        JAGENT[Jaeger Agent - UDP receiver]
        JCOLLECTOR[Jaeger Collector - processes & stores]
        JQUERY[Jaeger Query - API & UI]
        JSTORE[Storage Backend]
    end

    subgraph "Application"
        APP_TRACER[OTel SDK / Jaeger Client]
    end

    subgraph "Storage Backends"
        CASSANDRA[Cassandra]
        ELASTICSEARCH_J[Elasticsearch]
        BADGER[Badger - In-memory]
    end

    APP_TRACER --> |UDP/HTTP| JAGENT
    JAGENT --> JCOLLECTOR
    JCOLLECTOR --> JSTORE
    JSTORE --> CASSANDRA
    JSTORE --> ELASTICSEARCH_J
    JSTORE --> BADGER
    JQUERY --> JSTORE
    JQUERY --> |UI| USER[Developer]
```

### Jaeger UI Features

```mermaid
graph TB
    UI[Jaeger UI] --> SEARCH[Search Traces]
    UI --> TRACE_VIEW[Trace Timeline View]
    UI --> DEPEND[Service Dependency Graph]
    UI --> COMPARE[Compare Traces]

    SEARCH --> |Filter by service, duration, tags| SEARCH_D[Find specific traces]
    TRACE_VIEW --> |Waterfall diagram| TRACE_D[See span timing and relationships]
    DEPEND --> |Service map| DEPEND_D[Visualize service topology]
    COMPARE --> |Side by side| COMPARE_D[Compare good vs bad traces]
```

## Trace Analysis

### Reading a Trace

```mermaid
gantt
    title Trace: Order Request (abc123)
    dateFormat X
    axisFormat %Lms

    section API Gateway
    HTTP POST /orders       :a1, 0, 250

    section Order Service
    Create Order            :a2, 20, 200

    section Payment Service
    Process Payment         :a3, 30, 150

    section Database
    INSERT transaction      :a4, 40, 50

    section Inventory
    Check stock             :a5, 30, 30
```

**What to look for in traces:**
1. **Long spans**: Which operation takes the most time?
2. **Sequential operations**: Can they be parallelized?
3. **Error spans**: Where did errors occur?
4. **Retry spans**: Are there unnecessary retries?
5. **Missing spans**: Are there gaps in the trace?

### Common Patterns

```mermaid
graph TB
    subgraph "Good: Parallel Execution"
        PARENT[Parent Span] --> CHILD1[Child 1: 50ms]
        PARENT --> CHILD2[Child 2: 60ms]
        PARENT --> CHILD3[Child 3: 40ms]
        NOTE1["Total: ~60ms (parallel)"]
    end

    subgraph "Bad: Sequential Execution"
        PARENT2[Parent Span] --> C1[Child 1: 50ms]
        C1 --> C2[Child 2: 60ms]
        C2 --> C3[Child 3: 40ms]
        NOTE2["Total: 150ms (sequential)"]
    end
```

## Sampling Strategies

```mermaid
graph TB
    SAMPLING[Sampling] --> HEAD[Head-based Sampling]
    SAMPLING --> TAIL[Tail-based Sampling]

    HEAD --> |Decision at trace start| HEAD_D[Agent decides: sample X%]
    TAIL --> |Decision at trace end| TAIL_D[Collector decides: keep errors, slow traces]
```

| Strategy | Decision Point | Pros | Cons |
|----------|---------------|------|------|
| **Head-based** | At trace creation (agent) | Simple, low overhead | May miss interesting traces |
| **Tail-based** | At trace completion (collector) | Keeps errors and slow traces | Higher memory, more complex |
| **Adaptive** | Dynamic rate based on load | Balances cost and coverage | Complex to configure |
| **Always-on** | 100% sampling | Complete visibility | Expensive at scale |

**Tail-based sampling is preferred** for production—it keeps all error traces and slow traces while sampling normal ones.

## Interview Questions

### Q1: What is distributed tracing and why is it needed?
**Answer**: Distributed tracing tracks requests as they flow through multiple microservices. Each request gets a unique trace ID, and each service operation creates a span with timing information. It's needed because in microservices, a single request may touch 5-20 services—without tracing, debugging latency issues or errors requires correlating logs across multiple services manually. Tracing provides a visual timeline showing exactly where time was spent, which services were involved, and where errors occurred.

### Q2: Explain trace, span, and context propagation.
**Answer**: A trace is the complete journey of a request (identified by trace_id). A span is a single operation within that trace (has span_id, parent_span_id, start time, duration, attributes). Context propagation passes trace context between services—typically via HTTP headers (`traceparent` in W3C format). When Service A calls Service B, it includes the trace context in headers; Service B creates a child span linked to the parent. This creates a tree of spans showing the full request path.

### Q3: What is OpenTelemetry and how does it relate to tracing?
**Answer**: OpenTelemetry (OTel) is a CNCF standard providing vendor-neutral APIs and SDKs for traces, metrics, and logs. It replaces proprietary instrumentation (Jaeger client, Zipkin client) with a single standard. Components: (1) API—defines how to create spans/metrics, (2) SDK—implements the API, (3) Collector—receives, processes, and exports telemetry data. Benefits: instrument once, export to any backend (Jaeger, Zipkin, Datadog), auto-instrumentation for popular frameworks, unified observability.

### Q4: What is the difference between head-based and tail-based sampling?
**Answer**: Head-based sampling decides whether to sample at trace creation (first span). The agent samples X% of traces randomly. Simple but may miss error traces. Tail-based sampling decides at trace completion—the collector keeps all error and slow traces while sampling normal ones. More intelligent but requires the collector to buffer complete traces. Recommendation: tail-based sampling for production—it ensures you never lose error traces while controlling costs.

### Q5: How do you propagate trace context across message queues?
**Answer**: For HTTP, trace context goes in headers (`traceparent`). For message queues (Kafka, RabbitMQ, SQS): (1) Producer extracts trace context from active span, (2) Serializes it into message headers/attributes (Kafka headers, SQS MessageAttributes), (3) Consumer extracts trace context from message headers, (4) Creates a child span linked to the producer's span. OpenTelemetry provides instrumentations for popular message queue clients that handle this automatically.

## Common Mistakes

1. **No auto-instrumentation**: Manually instrumenting every function is error-prone and tedious
2. **Sampling too aggressively**: Missing important error traces with 1% sampling
3. **No context propagation**: Forgetting to propagate headers in HTTP clients or message queues
4. **High-cardinality attributes**: Using user_id or request_id as span attributes overwhelms storage
5. **No correlation with logs**: Traces and logs in separate systems with no trace_id in logs
6. **Tracing everything**: Internal utility functions don't need spans—trace service boundaries
7. **Ignoring trace overhead**: 100% sampling with no batching adds significant latency

## Summary

| Concept | Key Takeaway |
|---------|-------------|
| **Trace** | Complete request journey across services |
| **Span** | Single operation within a trace |
| **Context Propagation** | Passing trace info via HTTP headers |
| **OpenTelemetry** | Vendor-neutral standard for traces, metrics, logs |
| **Jaeger** | Open-source distributed tracing backend |
| **Sampling** | Head-based (simple) vs Tail-based (intelligent) |

## Cross-References

- **Observability Overview**: [README](./README.md) — Three pillars
- **Logging**: [Correlation IDs](./logging.md) — Link logs to traces via trace_id
- **Monitoring**: [Prometheus](./monitoring.md) — Metrics alongside traces
- **Kubernetes Ingress**: [Controllers](../kubernetes/ingress.md) — Trace propagation through Ingress
- **Microservices**: Service boundaries where tracing is most valuable
- **CI/CD**: [Pipelines](../cicd/pipelines.md) — Tracing in deployment pipelines
