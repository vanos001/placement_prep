# Incident Response

Incident response is the structured approach to handling production failures, security breaches, and service degradations. Effective incident response minimizes impact on users, reduces recovery time, and transforms failures into organizational learning. This document covers the frameworks, processes, and practices that production engineering teams use to manage incidents.

## What is an Incident?

An incident is any unplanned interruption or degradation of a service that impacts users or business operations. This includes:

- Complete service outages (HTTP 500 errors, service unreachable)
- Partial degradations (increased latency, elevated error rates)
- Data loss or corruption
- Security breaches or unauthorized access
- Performance degradation affecting user experience

Not every bug or anomaly is an incident. The distinction is impact: an incident affects users or business operations in a meaningful way.

## Severity Levels

Severity levels classify incidents by their impact and urgency. A well-defined severity framework ensures consistent response across the organization.

### Severity 1 (Critical / SEV-1)
- **Impact**: Complete service outage affecting all users, or data loss/corruption
- **Examples**: Production database is down, payment processing completely broken, security breach with data exfiltration
- **Response time**: Immediate (within minutes)
- **Resolution target**: 1 hour
- **Communication**: Executive notification, status page updated, all-hands response
- **Staffing**: All relevant engineers engaged, incident commander assigned

### Severity 2 (Major / SEV-2)
- **Impact**: Significant feature degradation affecting a large portion of users
- **Examples**: Search functionality down, mobile app crashing for 30% of users, major API endpoint returning errors
- **Response time**: Within 15 minutes
- **Resolution target**: 4 hours
- **Communication**: Team leads notified, status page updated
- **Staffing**: On-call engineer plus additional team members

### Severity 3 (Minor / SEV-3)
- **Impact**: Minor feature degradation affecting a small portion of users
- **Examples**: Non-critical feature broken, increased latency for specific endpoints, intermittent errors
- **Response time**: Within 1 hour
- **Resolution target**: 24 hours
- **Communication**: Team notified via normal channels
- **Staffing**: On-call engineer handles, may escalate if needed

### Severity 4 (Low / SEV-4)
- **Impact**: Cosmetic issues or bugs with workarounds available
- **Examples**: UI display issues, logging errors, non-critical alerts
- **Response time**: Within 24 hours
- **Resolution target**: Next sprint/weekly cycle
- **Communication**: Tracked in issue tracker
- **Staffing**: Normal development workflow

## On-Call

### On-Call Rotation
On-call rotations ensure that someone is always available to respond to incidents:

- **Primary on-call**: First responder; receives all pages and alerts
- **Secondary on-call**: Backup if primary doesn't respond within 5 minutes
- **Escalation**: If neither responds, the incident escalates to the team lead or manager

### On-Call Best Practices
- **Rotation length**: 1 week per person; shorter rotations cause context-switching fatigue, longer ones cause burnout
- **Handoff**: Include a summary of recent incidents, ongoing issues, and any known problems
- **Compensation**: On-call time should be compensated, either through pay or time off
- **Runbooks**: Every alert should have an associated runbook
- **Alert hygiene**: Regularly review and tune alerts to reduce false positives

### On-Call Schedule Example
```
Week 1: Alice (primary), Bob (secondary)
Week 2: Carol (primary), Dave (secondary)
Week 3: Eve (primary), Alice (secondary)
Week 4: Bob (primary), Carol (secondary)
```

### Alert Fatigue
Alert fatigue occurs when on-call engineers receive too many alerts, especially false positives. This leads to:
- Ignoring or delaying response to alerts
- Desensitization to real problems
- Burnout and turnover

**Preventing alert fatigue:**
- Every alert must be actionable; if there's nothing to do, it shouldn't alert
- Track alert frequency and investigate noisy alerts
- Implement alert suppression during known maintenance windows
- Use different severity levels for different alert types
- Regularly review and remove obsolete alerts

## Incident Response Process

### Phase 1: Detection
The incident is detected through monitoring, alerts, or user reports.

**Detection sources:**
- Automated monitoring and alerting (Prometheus, Datadog, PagerDuty)
- Customer support tickets
- Social media complaints
- Internal users or QA testing
- Synthetic monitoring (uptime checks, synthetic transactions)

**Key metrics:**
- **MTTD (Mean Time To Detect)**: How long from incident start to detection
- Goal: MTTD should be under 5 minutes for critical services

### Phase 2: Triage
Quickly assess the incident's scope and impact to determine the appropriate response.

**Triage questions:**
1. What is the impact? (How many users affected? What functionality is broken?)
2. What changed recently? (Deployments, configuration changes, infrastructure changes)
3. Is it getting worse? (Escalating, stable, or self-healing?)
4. What is the blast radius? (Single service, multiple services, entire platform?)

### Phase 3: Response
Assemble the response team and begin working on resolution.

**Incident Commander (IC):**
The IC is the most critical role in incident response. They:
- Coordinate the response effort
- Make decisions about escalation and resource allocation
- Communicate with stakeholders
- Ensure the response stays focused and productive
- Do NOT necessarily fix the problem themselves

**Communication:**
- Open a dedicated incident channel (Slack, Teams)
- Post regular updates (every 15-30 minutes for SEV-1/2)
- Update the status page for user-facing incidents
- Notify affected teams and stakeholders

**Incident Channel Template:**
```
🚨 INCIDENT: [Brief Description]
Severity: SEV-X
Impact: [What's broken and who's affected]
IC: @[name]
Status: Investigating / Identified / Fixing / Monitoring / Resolved

--- Updates ---
[timestamp] Update 1: ...
[timestamp] Update 2: ...
```

### Phase 4: Resolution
Apply fixes to restore service. Resolution strategies include:

- **Rollback**: Revert the most recent deployment or configuration change
- **Failover**: Switch to a backup system or region
- **Scale up**: Add capacity to handle increased load
- **Feature flag**: Disable the problematic feature
- **Hotfix**: Apply a targeted code fix
- **Manual intervention**: Direct database fixes, cache clears, etc.

### Phase 5: Recovery
Verify that the service has returned to normal operation:

- Confirm metrics are back to baseline
- Verify all health checks are passing
- Monitor for recurrence
- Gradually restore normal capacity if scaled up

### Phase 6: Postmortem
Conduct a thorough review of the incident (covered in detail below).

## Runbooks

A runbook is a step-by-step guide for responding to a specific type of incident or alert. Good runbooks reduce MTTR by eliminating the need for on-call engineers to figure out what to do under pressure.

### Runbook Structure
```markdown
# Runbook: High Error Rate on Payment Service

## Alert Description
Error rate on payment-service exceeds 5% for 5 minutes.

## Impact
Users cannot complete purchases. Direct revenue impact.

## First Steps (5 minutes)
1. Check the payment service dashboard: [link]
2. Verify the error types: 500s? 429s? Timeouts?
3. Check recent deployments: `kubectl rollout history deployment/payment-service`

## Common Causes and Fixes

### Cause: Bad Deployment
- Check if a deployment happened in the last 30 minutes
- If yes, rollback: `kubectl rollout undo deployment/payment-service`
- Verify error rate returns to normal

### Cause: Database Connection Pool Exhaustion
- Check database connections: [dashboard link]
- If connections are maxed, check for connection leaks
- Temporary fix: restart pods one at a time
- Permanent fix: investigate connection leak in code

### Cause: Third-Party Payment Provider Down
- Check provider status page: [link]
- Check circuit breaker metrics: [dashboard link]
- If provider is down, enable fallback provider via feature flag
- Notify customers of potential delays

## Escalation
If not resolved within 15 minutes, escalate to:
- Payment team lead: @name
- Database team: @name (if database-related)
```

## Postmortems

A postmortem (also called a post-incident review or retrospective) is a structured review of an incident conducted after resolution. The goal is to learn from the incident and prevent recurrence.

### Blameless Culture
The most important principle of postmortems is blamelessness. The goal is to understand what happened and why, not to find someone to blame. Blame discourages honest reporting and hides systemic issues.

**Instead of**: "Bob deployed buggy code that caused the outage"
**Say**: "The deployment pipeline did not catch the regression because integration tests did not cover this edge case"

### Postmortem Template
```markdown
# Postmortem: [Incident Title]

## Metadata
- **Date**: YYYY-MM-DD
- **Duration**: X hours Y minutes
- **Severity**: SEV-X
- **Incident Commander**: @name
- **Author**: @name
- **Status**: Draft / Reviewed / Action Items Complete

## Summary
[2-3 sentence summary of what happened, the impact, and how it was resolved]

## Impact
- **Users affected**: X users (Y% of total)
- **Duration**: X hours Y minutes
- **Revenue impact**: $X estimated
- **Data impact**: None / Describe any data loss or corruption

## Timeline (all times in UTC)
- HH:MM - [Event] Description
- HH:MM - [Detection] Alert fired for high error rate
- HH:MM - [Response] IC assigned, incident channel opened
- HH:MM - [Diagnosis] Root cause identified: ...
- HH:MM - [Resolution] Fix deployed, error rate returning to normal
- HH:MM - [Recovery] Service fully recovered, monitoring stable

## Root Cause
[Detailed explanation of the root cause. Go beyond "what" to "why".]

## Contributing Factors
- Factor 1: [What made this incident possible or worse?]
- Factor 2: [What delayed detection or resolution?]

## What Went Well
- [ ] Fast detection due to good monitoring
- [ ] Clear communication during the incident
- [ ] Effective rollback procedure

## What Went Poorly
- [ ] No runbook existed for this type of failure
- [ ] Took 20 minutes to identify root cause
- [ ] Status page was not updated promptly

## Lessons Learned
- Lesson 1: ...
- Lesson 2: ...

## Action Items
| Action | Owner | Priority | Due Date | Status |
|--------|-------|----------|----------|--------|
| Add integration test for edge case | @name | P1 | YYYY-MM-DD | Open |
| Create runbook for this failure mode | @name | P2 | YYYY-MM-DD | Open |
| Add monitoring for database connection pool | @name | P1 | YYYY-MM-DD | Open |
```

### Postmortem Best Practices
- **Conduct within 48-72 hours** of the incident while details are fresh
- **Include all participants** in the review, not just the on-call engineer
- **Focus on systems, not people**: What process or tooling gap allowed this?
- **Assign action items**: Every lesson learned should have a concrete, trackable action
- **Follow up**: Review action item progress in subsequent weeks
- **Share broadly**: Postmortems are learning opportunities for the entire organization

## MTTR and Its Components

MTTR (Mean Time To Recovery) is the most important metric for incident response effectiveness. It breaks down into:

### MTTD - Mean Time To Detect
How long from when the incident starts to when it is detected.

**Improving MTTD:**
- Comprehensive monitoring with meaningful alerts
- Synthetic monitoring that simulates user journeys
- Anomaly detection that catches unusual patterns
- Customer feedback channels that are monitored

### MTTA - Mean Time To Acknowledge
How long from detection to when someone starts working on it.

**Improving MTTA:**
- Clear on-call rotations with reliable paging
- Escalation policies that ensure someone always responds
- Mobile alerts that wake on-call engineers for critical issues

### MTTR - Mean Time To Recovery (Resolution)
How long from acknowledgment to service restoration.

**Improving MTTR:**
- Detailed runbooks for known failure modes
- Automated rollback capabilities
- Feature flags for quick feature disabling
- Well-practiced incident response procedures
- Good observability for fast diagnosis

### MTTF - Mean Time To Fix (Permanent)
How long until a permanent fix is deployed (not just a mitigation).

**Improving MTTF:**
- Prioritized postmortem action items
- Dedicated time for reliability improvements
- Technical debt tracking and reduction

```
Total Incident Duration = MTTD + MTTA + MTTR

Example Timeline:
├── 3 min (MTTD) ──┤── 5 min (MTTA) ──┤── 25 min (MTTR) ──┤
│                   │                    │                    │
Issue starts      Alert fires         IC responds        Service restored
```

## Incident Metrics and Trends

Track these metrics over time to measure and improve incident response:

- **Incident frequency**: Number of incidents per week/month (should decrease over time)
- **MTTD/MTTA/MTTR trends**: Are response times improving?
- **Incidents by severity**: Distribution across severity levels
- **Incidents by root cause**: Categories like deployment, infrastructure, dependency, code bug
- **Repeat incidents**: Same root cause appearing multiple times (indicates unresolved systemic issues)
- **Postmortem action item completion rate**: Are we actually fixing the things we identify?

## Chaos Engineering

Proactive incident response through controlled experiments:

- **Chaos Monkey** (Netflix): Randomly terminates production instances to test resilience
- **Game Days**: Scheduled exercises where teams practice responding to simulated incidents
- **Failure Injection**: Deliberately introduce failures (latency, errors, resource exhaustion) to test system behavior

The goal is to discover weaknesses before they cause real incidents and to keep incident response skills sharp.

## Summary

Effective incident response requires:

1. **Clear severity definitions** so everyone knows the urgency
2. **Reliable on-call rotations** with well-maintained runbooks
3. **Structured response process** with defined roles (IC, communications, resolver)
4. **Blameless postmortems** that turn incidents into organizational learning
5. **Metrics tracking** (MTTD, MTTA, MTTR) to measure improvement
6. **Proactive testing** through chaos engineering and game days

The goal is not to prevent all incidents—that is impossible in complex systems. The goal is to detect incidents quickly, resolve them efficiently, learn from them thoroughly, and prevent their recurrence systematically.
