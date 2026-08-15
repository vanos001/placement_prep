# Advanced Observability

## Overview

Advanced observability goes beyond dashboards and alerting to provide deep, continuous insight into system behavior. This chapter covers eBPF-based observability, continuous profiling, distributed tracing internals, high-cardinality metrics management, OpenTelemetry pipeline architecture, and SLO automation.

## eBPF Observability

**eBPF (extended Berkeley Packet Filter)** enables running sandboxed programs in the Linux kernel without modifying kernel source or loading modules. It has revolutionized observability by providing kernel-level tracing with near-zero overhead.

### How eBPF Works

```
User Space                    Kernel Space
──────────                    ────────────
                          ┌─────────────┐
eBPF program     ────────▶│  Verifier   │ (safety check: no infinite loops, no bad memory access)
(C compiled       (bpf()  └──────┬──────┘
 to BPF bytecode)  syscall)       │
                                   ▼
                          ┌─────────────┐
                          │   JIT/AOT   │ (compile BPF → native machine code)
                          └──────┬──────┘
                                 │
           ┌─────────────────────┼─────────────────────┐
           ▼                     ▼                     ▼
    ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
    │ kprobes     │      │ tracepoints │      │ perf_events │
    │ (function   │      │ (static     │      │ (hardware   │
    │  entry)      │      │  hooks)     │      │  counters)  │
    └─────────────┘      └─────────────┘      └─────────────┘
```

eBPF programs attach to hooks (kprobes, tracepoints, perf events) and collect data that is read back by user-space tools.

### eBPF Observability Tools

| Tool | Function | Use Case |
|------|----------|----------|
| bpftrace | High-level tracing language | Ad-hoc investigation, custom queries |
| BCC (BPF Compiler Collection) | Python/C tools | Production tracing (biosnoop, execsnoop, tcplife) |
| Cilium Hubble | eBPF-based network observability | Service mesh visibility, DNS tracing |
| Pixie | eBPF auto-instrumentation for K8s | Zero-instrumentation tracing for microservices |
|bcc/libbpf-tools | Compiled BPF tools | CPU profiling, latency tracing, I/O analysis |

eBPF's key advantage: no application code changes required. Trace any function (kernel or userspace), trace network packets, monitor system calls—all from a single, safe runtime.

## Continuous Profiling

**Continuous profiling** collects CPU, memory, and I/O profiles from all production instances continuously (not just during incidents), enabling performance regression detection, capacity planning, and root-cause analysis.

### Profiling Types

| Type | Data Collected | Tool |
|------|---------------|------|
| CPU profiling | Where CPU time is spent (function call stack + frequency) | Parca, Pyroscope, Go pprof, perf |
| Heap profiling | Memory allocation sizes, allocation sites, live objects | Pyroscope, Go pprof, Java Flight Recorder |
| Off-CPU profiling | Where threads are blocked (waiting for I/O, locks, network) | perf, bpftrace |
| Lock contention profiling | Lock wait times, holder identification | bpftrace, Linux perf lock |
| Allocation profiling | Allocation rate, object lifetimes, GC pressure | Go pprof, JFR, jemalloc profiling |

### Flame Graphs

Flame graphs visualize profiling data as a hierarchical stack of function calls, where bar width represents CPU time:

```
                     main()
            ┌──────────┼──────────┐
         handleReq()  process()  idle()
       ┌─────┼─────┐     │
   dbQuery() cache() render()
      │         │        │
    query()  lookup() template()
```

**Off-CPU flame graphs** show where time is spent waiting (blocked on I/O, locks, scheduling) instead of CPU-burn. They are critical for diagnosing latency issues that don't show up in CPU profiles.

### Tools: Parca & Pyroscope

- **Parca** (CNCF sandbox): standalone continuous profiling storage and query engine; pulls profiles via eBPF or SDK, stores them, and serves queries via the pprof API
- **Pyroscope** (Grafana Labs): continuous profiling platform with comparison views (diff two time ranges), flame graph explorer, and integration with Grafana

### Implementation Pattern

```
Every application instance → Profiling agent (Parca agent / Pyroscope SDK)
                              │
                              ▼
                     Central profiling store
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
             Ad-hoc query  Alerting   Dashboard
             (debugging)   (regression (team visibility)
                          detection)
```

**Regression detection**: set a baseline profile; alert when a new profile deviates significantly (increased CPU in a specific function, new allocation hotspots).

## Distributed Tracing

### Tracing Internals

A distributed trace records the path of a request through multiple services:

```
Service A ──▶ Service B ──▶ Service D
    │              │
    └──▶ Service C ────────┘
              │
         Service E

Span A (root, 100ms)
├── Span B (50ms) — called by A
│   ├── Span D (20ms) — called by B
│   └── Span C (40ms) — called by B (concurrent)
│       └── Span E (15ms) — called by C
```

Each **span** has: trace ID, span ID, parent span ID, service name, operation name, start/stop timestamps, status code, and attributes (key-value metadata). Spans form a tree within a trace.

### Sampling Strategies

Sampling reduces cost (traces have high cardinality—every unique request is a unique trace). Strategies:

| Strategy | Description | Trade-off |
|----------|------------|-----------|
| Head-based | Sample decision made at trace root (before children) | Simple, but can miss important slow traces |
| Tail-based | Buffer all spans; decide to keep/discard after root span completes | Captures error and slow traces, but requires buffering infrastructure |
| Adaptive | Dynamically adjust sample rate based on traffic volume | Keeps cost predictable while maximizing coverage |
| Priority/rules | Always sample traces matching rules (error, high latency, specific routes) | Targeted, but rule maintenance overhead |

### Trace Aggregation & Exemplars

**Exemplars** link metric data points to specific trace IDs, bridging metrics and traces:

```json
// Counter metric with an exemplar
http_requests_total{method="GET", path="/api/users"} 1523
  Exemplar: { trace_id: "abc123", span_id: "def456", timestamp: 1700000000 }
```

When a metric spike occurs, clicking the exemplar navigates directly to the trace that caused it—dramatically reducing time to root cause.

### OpenTelemetry Internals

**OpenTelemetry (OTel)** is the industry-standard observability framework, providing APIs, SDKs, and tools for generating, collecting, and exporting telemetry (traces, metrics, logs).

#### Collector Architecture

```
Receivers           Processors              Exporters
──────────          ──────────             ─────────
otlp/grpc     ──▶  batch          ──▶    otlp/http ──▶ Backend (Tempo, Jaeger)
otlp/http     ──▶  memory_limiter ──▶    prometheus ──▶ Prometheus
zipkin        ──▶  k8s_attributes ──▶    elasticsearch ──▶ Elasticsearch
jaeger        ──▶  filter         ──▶    file ──▶ Debug
prometheus    ──▶  tail_sampling  ──▶
              ──▶  attributes
              ──▶  span_metrics
```

Key components:

- **Receivers**: ingest telemetry in multiple formats (OTLP gRPC/HTTP, Jaeger, Zipkin, Prometheus)
- **Processors**: transform, filter, batch, enrich, and sample telemetry
- **Exporters**: send processed telemetry to backends

**Tail sampling processor**: buffers completed traces, then applies rules (sample all errors, sample traces > 1s, sample 1% of normal traces). This is the production implementation of tail-based sampling.

## High-Cardinality Metrics & Cardinality Control

**Cardinality** = number of unique time series for a metric. Each unique combination of label values creates a new time series:

```
http_requests_total{method="GET", path="/api/users/{id}", user_id="12345"}

If user_id is a label → potentially infinite cardinality (one per user) → storage explosion
```

### The Cardinality Problem

| Cardinality | Time Series Count | Storage/Month | Query Performance |
|------------|-------------------|---------------|-------------------|
| Low (< 100 series) | < 100 | Negligible | Fast |
| Medium (1K–100K) | 1K–100K | Manageable | Moderate |
| High (100K–10M) | 100K–10M | Expensive | Slow |
| Uncontrolled (> 10M) | 10M+ | Critical | Broken |

Uncontrolled cardinality has caused major outages (Datadog cardinality spikes billing, Prometheus OOM kills on high-cardinality labels).

### Cardinality Control Strategies

1. **Label curation**: only include labels that are useful for querying. Remove high-cardinality values (user IDs, request IDs, IP addresses)
2. **Bucketing**: use histogram buckets instead of raw values (e.g., latency bucket `le="1.0"` instead of `duration_ms="847"`)
3. **Cardinality limits**: enforce maximum cardinality per metric (OTel SDK cardinality limiter, Prometheus `tsdb.cardinality-limit`)
4. **Value groups**: map high-cardinality values to groups (e.g., `region="us-east"` instead of `zone="us-east-1a"`)
5. **Pre-aggregation**: aggregate at the edge (e.g., count per endpoint per minute, drop per-request labels)

## Structured Logs & Log Sampling

### Structured Logging

Structured logs use a consistent format (JSON, logfmt) with typed fields:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "service": "payment-service",
  "trace_id": "abc123def456",
  "span_id": "789ghi",
  "message": "Payment processing failed",
  "user_id": "usr_456",
  "error_code": "INSUFFICIENT_FUNDS",
  "amount": 99.99,
  "currency": "USD",
  "latency_ms": 234
}
```

Benefits: machine-parseable, queryable with logQL/LogQL/KQL, correlate with traces via trace_id/span_id.

### Log Sampling

Log volume at scale can be enormous (TB/day). Sampling reduces cost:

| Strategy | How | What You Lose |
|----------|-----|---------------|
| Rate limiting | Max N logs per service per second | High-frequency events |
| Error-first | Always keep ERROR/WARN; sample INFO | Volume of normal events |
| Route-based | Keep all logs for flagged routes/users | Some coverage |
| Intelligent | ML-based anomaly detection keeps unusual logs | Simplicity |

## Event Correlation & Anomaly Detection

### Event Correlation

Correlate signals across metrics, traces, and logs to identify root cause:

- **Metric spike** → **which traces** are slow → **which logs** show errors → **root cause**
- **Log pattern** (e.g., "connection refused") → **affected services** (metric) → **downstream impact** (trace)

Tools: Grafana (correlate dashboards), Datadog (trace → log → metric), Coralogix (log-based correlation).

### Anomaly Detection

Automated detection of unusual patterns:

- **Statistical**: 3-sigma alerts, MAD (Median Absolute Deviation), IQR-based
- **ML-based**: ARIMA, Prophet (time series), isolation forests (multivariate)
- **Business-logic**: "if error rate > 2x baseline AND latency > 2x baseline, page on-call"

### Automated Root Cause Analysis (RCA)

Approaches to automated RCA:

- **Topology-based**: map service dependencies; when a failure propagates, trace back through the dependency graph
- **Causal debugging**: hypothesis generation and testing—propose potential causes, test against telemetry, narrow down
- **Knowledge graphs**: encode known failure modes and their telemetry signatures; match current incident against historical patterns

## Telemetry Cost Optimization

Telemetry collection is expensive at scale. Cost optimization strategies:

| Technique | Savings | Implementation |
|-----------|---------|----------------|
| Cardinality control | 50-90% | Label curation, bucketing, pre-aggregation |
| Log sampling | 60-90% | Error-first, rate limiting |
| Tail-based trace sampling | 80-95% | OTel tail_sampling processor |
| Tiered storage | 50-70% | Hot/warm/cold tiers (different query latency and cost) |
| Agent-side filtering | 30-60% | OTel filter processor, drop low-value telemetry |
| Telemetry budget per service | Predictable | Assign quota; alert on overage |

## SLO Automation

### SLO Framework

An SLO (Service Level Objective) defines a reliability target: "99.9% of API requests complete in < 200ms over a 30-day window."

**Error budget** = 1 - SLO target. For 99.9% SLO: error budget = 0.1% = 43.2 minutes of downtime per month.

### SLO Automation Components

```
SLI Definition ──▶ SLI Calculation ──▶ SLO Status ──▶ Error Budget ──▶ Action
                                                                           │
                  ┌────────────────────────────────────────────────────┘
                  │
            ┌─────┴──────┐
            ▼            ▼
       Alerting     Release velocity
       (burn rate)  (slow down when
                    budget is low)
```

**Burn rate alerts** detect error budget consumption velocity:

| Alert Condition | Meaning | Action |
|----------------|---------|--------|
| Burn rate > 14.4x in 5 min | Entire monthly budget consumed in 5 min | Page immediately |
| Burn rate > 6x in 30 min | Entire monthly budget consumed in 30 min | Page immediately |
| Burn rate > 1x in 6 hours | Budget consumed at normal rate for the window | Page during business hours |
| Burn rate > 0.5x in 3 days | Budget being consumed slowly | Ticket/notification |

**Error-budget automation**: link error budget to deployment velocity. When budget is healthy (consumed < 50%), deploy freely. When budget is depleting (> 80% consumed), require additional review or slow deployments.

### Incident Correlation

When multiple SLO breaches occur simultaneously, correlate:

- **Common root cause**: do degraded services share a dependency?
- **Cascading failure**: is one service's failure causing downstream SLO breaches?
- **Coincidence**: independent failures occurring simultaneously

Automated correlation reduces noise: instead of 15 pages for one incident, correlate into a single incident with full context.

## Interview Angle

> **"How would you design an observability pipeline for a system with 10,000 microservices?"**

Discuss: (1) OpenTelemetry SDK auto-instrumentation for traces + metrics + logs, (2) sidecar or daemonSet collectors per node with load balancing, (3) central collector cluster with tail sampling (keep errors + slow traces, sample 1% of normal), (4) cardinality control at the SDK level (drop user IDs, use histogram buckets), (5) tiered storage (hot for 7 days, warm for 30, cold for 1 year), (6) SLO per service with burn-rate alerts, (7) exemplars bridging metrics and traces, (8) cost per service as a chargeback metric.

> **"What is cardinality explosion and how do you prevent it?"**

Cardinality explosion occurs when a metric has too many unique label combinations, creating millions of time series that overwhelm storage and break queries. Example: including `user_id` or `request_id` as a label. Prevention: (1) audit labels for cardinality, (2) remove or aggregate high-cardinality labels, (3) use histograms instead of raw values for latency, (4) enforce cardinality limits at the SDK/collector level, (5) monitor cardinality as its own metric and alert on unexpected growth.

## Key References

- OpenTelemetry specification and documentation (opentelemetry.io)
- Grafana Pyroscope documentation (grafana.com/pyroscope)
- Parca project (parca.dev)
- Google SRE Book, Chapter 4 (SLOs)
- "The Practical Guide to SLOs" (Slisett, 2020)
- eBPF.io documentation (ebpf.io)
