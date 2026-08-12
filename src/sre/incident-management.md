# Incident Management

## Severity Levels

| Level | Impact | Response Time | Example |
|---|---|---|---|
| SEV-1 | Critical (revenue/data loss) | 15 min | Site down, data breach |
| SEV-2 | Major (degraded service) | 30 min | High error rate, slow response |
| SEV-3 | Minor (single user/feature) | 4 hours | Bug in non-critical feature |
| SEV-4 | Low (cosmetic/minor) | Next business day | UI typo |

## On-Call

- Primary + secondary on-call (1 week rotations)
- Respond within SLA (15 min for SEV-1)
- Runbook access required
- Escalation path defined
- Compensation for on-call (per company policy)

## Incident Response

```
Detection → Triage → Mitigate → Resolve → Postmortem
```

1. **Detection**: Alert fires, user report, monitoring
2. **Triage**: Assess severity, assign IC (Incident Commander)
3. **Mitigate**: Stop the bleeding (rollback, failover, scale)
4. **Resolve**: Fix root cause, verify recovery
5. **Postmortem**: Blameless review, action items

## Runbooks

Step-by-step procedures for common incidents:

```
# Runbook: High Error Rate

## Symptoms
- Error rate > 5% for 5 minutes
- PagerDuty alert fires

## Diagnosis
1. Check Grafana dashboard for error breakdown
2. Check recent deployments (last 30 min)
3. Check upstream dependencies
4. Check resource utilization (CPU, memory, disk)

## Mitigation
1. If recent deploy → rollback
2. If dependency down → enable circuit breaker
3. If resource exhaustion → scale up, check for leaks

## Resolution
1. Identify root cause
2. Fix and test
3. Deploy with monitoring
```

## Postmortems (Blameless)

```markdown
# Incident Postmortem: API Outage 2024-01-15

## Summary
API returned 500 errors for 23 minutes due to database connection exhaustion.

## Impact
- 12,000 failed requests
- ~$5,000 estimated revenue impact
- 3 enterprise customers affected

## Timeline (UTC)
- 14:00 Alert: error rate > 5%
- 14:05 IC assigned, investigating
- 14:10 Identified: connection pool exhausted
- 14:15 Mitigation: increased pool size
- 14:23 Error rate normalized

## Root Cause
New feature added a query that held connections for 30s instead of typical 100ms.

## Action Items
1. [P1] Add connection pool monitoring (owner: @alice)
2. [P1] Set query timeout to 5s (owner: @bob)
3. [P2] Load test new features before deploy (owner: @team)
```

## Interview Questions

**Q: What is a blameless postmortem?**
A: A postmortem that focuses on systemic causes, not individual blame. The assumption: people make reasonable decisions with the information they have. Focus on: what happened, why, how to prevent it. NOT: who messed up.

**Q: How do you handle a production incident?**
A: (1) Assess severity and page appropriate people, (2) assign an IC, (3) mitigate first (rollback, failover), (4) communicate status to stakeholders, (5) resolve root cause, (6) write blameless postmortem, (7) track action items to completion.

## References

- [Google SRE Book — Managing Incidents](https://sre.google/sre-book/managing-incidents/)
- [PagerDuty Incident Response](https://response.pagerduty.com/)
