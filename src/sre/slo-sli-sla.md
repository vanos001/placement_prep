# SLI, SLO, SLA, and Error Budgets

## SLI (Service Level Indicator)

A quantitative measure of service reliability:

```
SLI = Good events / Total events × 100%
```

Common SLIs:
| SLI | Definition | Example |
|---|---|---|
| Availability | Successful requests / Total requests | 99.9% |
| Latency | Requests faster than threshold | p99 < 200ms |
| Throughput | Requests per second | > 1000 rps |
| Error rate | Failed requests / Total | < 0.1% |
| Durability | Data not lost | 99.999999999% (11 9s) |

## SLO (Service Level Objective)

Target for an SLI:

```
Availability SLO: 99.9% of requests succeed over 30 days
Latency SLO: 99% of requests complete in < 200ms
```

**Tips:**
- Start tight, loosen over time (not the reverse)
- 99.9% = 43.8 min downtime/month
- 99.99% = 4.38 min downtime/month
- 99.999% = 26.3 sec downtime/month

## SLA (Service Level Agreement)

Legal contract with consequences (credits, penalties) for missing SLOs. SLAs are external; SLOs are internal targets that are stricter than SLAs.

## Error Budget

```
Error Budget = 100% - SLO

SLO = 99.9% → Error Budget = 0.1% → 43.8 min/month of allowed downtime
```

### How Error Budgets Work

- **Budget remaining**: Ship features faster, take more risks
- **Budget depleted**: Freeze features, focus on reliability
- **Budget overdrawn**: Incident response, postmortem, reliability work

### Burn Rate

How fast the error budget is being consumed:

```
Burn rate = Actual error rate / Allowed error rate

If SLO = 99.9% (0.1% allowed errors):
  Current error rate = 0.5%
  Burn rate = 0.5 / 0.1 = 5x
  
  At 5x burn rate, budget exhausted in 6 days (30/5)
```

### Alerting on SLOs

| Burn Rate | Alert | Action |
|---|---|---|
| 1x | Normal | Monitor |
| 3x | Warning | Investigate |
| 6x | Page | Immediate action |
| 14x | Critical | Incident declared |

## Interview Questions

**Q: What is the difference between SLI, SLO, and SLA?**
A: SLI = metric (what you measure: 99.95% success rate). SLO = target (what you aim for: 99.9%). SLA = contract (what you promise: 99.5%, with penalties for missing). SLOs are tighter than SLAs to provide a safety margin.

**Q: What is an error budget and how do you use it?**
A: Error budget = 1 - SLO. If SLO is 99.9%, you have 0.1% (43.8 min/month) of allowed unreliability. When budget is available, ship features. When depleted, focus on reliability. This balances innovation with reliability.

**Q: How do you choose SLOs?**
A: (1) Measure current performance (SLIs), (2) understand user expectations, (3) consider business requirements, (4) start conservative and loosen, (5) don't set SLOs you can't measure, (6) review regularly. Too tight = too much reliability work. Too loose = unhappy users.

## References

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [Google SRE Workbook](https://sre.google/workbook/table-of-contents/)
- [Alerting on SLOs — Google](https://sre.google/workbook/alerting-on-slos/)
