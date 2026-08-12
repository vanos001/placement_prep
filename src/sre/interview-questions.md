# SRE Interview Questions

**Q: What is the difference between monitoring and observability?**
A: Monitoring tells you WHEN something is wrong (alerts, dashboards). Observability tells you WHY (logs, metrics, traces — the three pillars). Monitoring is predefined questions; observability enables ad-hoc exploration.

**Q: How do you reduce toil?**
A: (1) Identify repetitive manual tasks, (2) automate the most frequent/harmful ones first, (3) create self-service tools, (4) eliminate the root cause (not just automate the symptom), (5) track toil reduction as a metric.

**Q: What is graceful degradation?**
A: When a component fails, the system continues with reduced functionality rather than failing completely. Example: if the recommendation engine is down, show popular items instead. Use circuit breakers, fallbacks, and feature flags.

**Q: How do you handle cascading failures?**
A: (1) Circuit breakers to stop calling failing services, (2) bulkheads to isolate failures, (3) backpressure to prevent overload, (4) load shedding to drop low-priority requests, (5) timeouts to prevent resource exhaustion, (6) retries with exponential backoff + jitter.

**Q: What is the difference between RPO and RTO?**
A: RPO (Recovery Point Objective): how much data you can afford to lose (e.g., 1 hour). RTO (Recovery Time Objective): how long recovery can take (e.g., 30 minutes). RPO affects backup frequency; RTO affects failover architecture.

## References

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [Google SRE Workbook](https://sre.google/workbook/table-of-contents/)
