# Observability

Observability is the ability to understand the internal state of a system from its external outputs. The three pillars — logs, metrics, and traces — give you complete visibility into production systems.

## In This Section

- [Logging](./logging.md) — Structured logging and the ELK stack
- [Monitoring](./monitoring.md) — Metrics, dashboards, and alerting
- [Tracing](./tracing.md) — Distributed tracing with OpenTelemetry

## Three Pillars of Observability

| Pillar | What | Tools |
|--------|------|-------|
| **Logs** | Discrete events | ELK, Loki, Fluentd |
| **Metrics** | Aggregated numbers | Prometheus, Grafana |
| **Traces** | Request flow | Jaeger, Zipkin, Tempo |

## Why All Three?

- **Logs** tell you *what* happened
- **Metrics** tell you *how much* and *how fast*
- **Traces** tell you *where* the time went

You need all three to debug production issues effectively.
