# On-Call Best Practices for SRE

## On-Call Rotation Design

A well-structured on-call system protects both the service and the engineers.

### Rotation Models

| Model | Description | Best For |
-------|-------------|----------|
| **Primary + Secondary** | Primary responds first, secondary backs up | Most teams (standard) |
| **Follow-the-Sun** | Rotates across time zones | Global teams (US → EU → APAC) |
| **Swarm** | Alerts go to entire team, whoever picks up responds | Small teams, low alert volume |
| **Tiered** | Tier 1 (triage) → Tier 2 (deep expertise) → Tier 3 (engineering) | Large organizations |

### Healthy Rotation Principles

- **1-week maximum** primary rotations (longer causes burnout)
- **At least 1-2 weeks off** between on-call shifts
- **Maximum 2 alerts per shift** as a target (more = too many alerts)
- **No on-call during vacation** — hard handoff required
- **Compensate** on-call time: pay, time off, or both

## Alert Quality: Signal vs. Noise

The single most impactful on-call improvement is reducing alert noise.

### Alert Maturity Model

| Level | Alert Type | Action Required | Example |
-------|-----------|----------------|----------|
| 1 | **Symptom** | Yes, immediately | "Payment success rate below 95%" |
| 2 | **Cause** | Yes, soon | "Database replication lag > 30s" |
| 3 | **Diagnostic** | Maybe | "CPU > 80% on node-5" |
| 4 | **Noise** | No | "Job completed successfully" |

**Rule of thumb**: If you wouldn't wake someone up at 3 AM for it, it shouldn't page.

### Reducing Noise

```
Total alerts received per week
─────────────────────────────── = Alert-to-incident ratio (target: < 5:1)
  Incidents requiring action
```

Techniques:
1. **Eliminate actionable-but-not-urgent alerts** — move to ticketing/Slack
2. **Aggregate correlated alerts** — one alert per incident, not per symptom
3. **Add hysteresis** — alert after 5 minutes sustained, not on a single spike
4. **Suppress during maintenance** — use maintenance windows in your alerting system
5. **Threshold based on SLOs** — alert when error budget is being burned, not at arbitrary thresholds
6. **Regular alert review** — monthly audit: which alerts were never actionable? Delete them.

### SLO-Based Alerting

Instead of alerting on CPU > 80%, alert when the **burn rate** of the error budget is dangerous:

| Burn Rate | Time to Exhaust 30-Day Budget | Action |
-----------|------------------------------|--------|
| 1x | 30 days | Normal
| 14.4x | 2 days | Page immediately |
| 6x | 5 days | Page during business hours |
| 1x | 30 days | Ticket |

## Runbooks

A runbook is a documented, step-by-step procedure for responding to a specific alert or incident.

### Structure of a Good Runbook

```markdown
# Alert: DatabaseReplicationLag

## What this means
Replication lag between primary and replica exceeds 30 seconds.

## Impact
Read queries served from replicas return stale data.

## Immediate Triage (5 minutes)
1. Check lag: `SHOW SLAVE STATUS` → `Seconds_Behind_Master`
2. Check replica load: `top`, `iostat -x 1`
3. Check for long-running queries: `SELECT * FROM pg_stat_activity WHERE state = 'active' ORDER BY query_start`

## Resolution Steps
1. If long-running query: KILL the query ID
2. If replica overloaded: Increase replica instance size
3. If network issue: Check cross-AZ network metrics

## Escalation
If unresolved in 15 minutes → escalate to DBA team (#dba-oncall)

## Prevention
- Add query timeout of 30 seconds at the application layer
- Set up slow query alerting (>5s)
```

### Runbook Best Practices

- **Link directly from the alert** — the alert should include the runbook URL
- **Keep updated** — runbooks rot if not reviewed quarterly
- **Automate steps** — if a step can be scripted, script it (even a one-liner helps)
- **Include diagnostic commands** — copy-paste ready
- **Store in version control** — git, Confluence, or a dedicated runbook platform

## Incident Escalation

### Escalation Path

```
Level 0: Automated (auto-remediation, retry)
  ↓ Unresolved in 5 min
Level 1: On-call engineer (page)
  ↓ Unresolved in 15 min / SEV-1
Level 2: Secondary on-call + team lead
  ↓ Unresolved in 30 min / SEV-1
Level 3: Engineering manager + subject matter expert
  ↓ Unresolved in 60 min / SEV-1
Level 4: VP Engineering / Incident Commander
```

Key principle: **escalate the problem, not the person**. The next level should bring additional expertise or authority, not just another pair of eyes.

## Post-Incident Review

The PIR (also called postmortem) is the most valuable learning tool in SRE.

### Structure

1. **Timeline** — minute-by-minute account from first symptom to resolution
2. **Impact** — what broke, for how long, how many users affected, revenue impact
3. **Root cause analysis** — use **5 Whys** to trace from symptom to fundamental cause
4. **Contributing factors** — what made this worse (missing monitoring, unclear runbook, etc.)
5. **Action items** — specific, assigned, with deadlines
6. **Lessons learned** — what went well, what didn't, systemic improvements

### Blameless Culture

A blameless PIR focuses on **systemic failures**, not individual mistakes.

| Blameful Statement | Blameless Reframe |
--------------------|-------------------|
| "John deployed without testing" | "Our CI pipeline allowed untested code to reach production" |
| "Sarah misconfigured the firewall" | "There was no validation on firewall rule changes" |
| "The intern deleted the database" | "Our prod database was accessible with intern-level permissions" |

The question is never "who messed up?" but **"what in our systems, processes, or tooling allowed this to happen?"** People operate within the systems they're given. If a human error can cause an outage, the system is broken — fix the system.

## References

- [Google SRE Book — Handling Incidents](https://sre.google/sre-book/postmortem-culture/)
- [PagerDuty Alerting Best Practices](https://www.pagerduty.com/resources/learn/what-is-an-on-call/)
- [SLO-Based Alerting](https://sre.google/sre-book/slo-book/)

## Interview Questions

### Q1: How would you reduce alert fatigue on your on-call team?
**Answer**: First, audit all alerts: categorize each as symptom, cause, diagnostic, or noise. Eliminate noise alerts entirely. Convert diagnostic alerts (CPU > 80%) to dashboard panels or Slack notifications — they don't page. Implement SLO-based alerting: only page when the error budget burn rate indicates the SLO is at risk. Add hysteresis and aggregation so one incident generates one page, not five. Set a target of fewer than 2 pages per on-call shift. Review alerts monthly — any alert that wasn't actionable in the past month gets deleted or downgraded.

### Q2: What makes a good runbook?
**Answer**: A good runbook is linked directly from the alert so the on-call engineer finds it immediately. It starts with a brief explanation of what the alert means and its impact. It provides copy-paste-ready diagnostic commands for the first 5 minutes of triage. It lists ordered resolution steps, from most likely/lowest risk to most involved. It specifies when and how to escalate. And it includes prevention measures. Most importantly, it's kept in version control and reviewed quarterly — a stale runbook is worse than no runbook because it wastes time on incorrect steps.

### Q3: Explain blameless postmortems. Doesn't "blameless" mean no accountability?
**Answer**: Blameless does NOT mean no accountability. It means we hold the **system** accountable, not the individual. When someone makes a mistake that causes an outage, we ask: what in our processes, tooling, or culture allowed that mistake to reach production? If an engineer can deploy without tests, the CI system is broken. If an intern can delete production data, the access control system is broken. People will always make mistakes — resilient systems prevent individual mistakes from becoming outages. Accountability exists at the organizational level: we're accountable for building systems that are resilient to human error. Individuals are still responsible for following processes, but the postmortem focuses on systemic improvement.

### Q4: How do you design an on-call rotation for a global service?
**Answer**: For a global service, I'd use follow-the-sun rotation: US team covers Americas hours, EU team covers EMEA, APAC team covers Asia-Pacific. Each team has a primary and secondary on-call. Alerts are routed to the active time zone. For SEV-1 incidents, all three teams are notified. I'd use a single incident management tool (PagerDuty, Opsgenie) with timezone-aware routing. Handoff happens at the start of each shift with a brief status update. Runbooks must be comprehensive since the on-call engineer may not be the author. For very small teams, a single rotation with compensatory time off is more practical than follow-the-sun.

### Q5: What metrics do you track for on-call health?
**Answer**: Key metrics: (1) **Pages per shift** — target < 2 (above indicates alerting problems). (2) **Alert-to-incident ratio** — total alerts / actionable incidents (target < 5:1). (3) **MTTA (Mean Time to Acknowledge)** — how fast the on-call responds (target < 5 min for SEV-1). (4) **MTTR (Mean Time to Resolve)** — how fast incidents are resolved. (5) **On-call frequency** — how often each person is on-call (target: no more than 1 week per month). (6) **Runbook coverage** — % of alerts with linked runbooks (target: 100%). (7) **Engineer satisfaction** — quarterly survey on on-call experience (burnout indicator).