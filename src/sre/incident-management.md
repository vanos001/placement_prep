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


## Scope: Where This Page Ends and Its Siblings Begin

This chapter covers the *live* incident command lifecycle: severity under pressure, role division, the detect→declare→mitigate→resolve loop, communications, timelines, and multi-team coordination. It does not re-teach its neighbors: rotation design and alert quality live in [./on-call.md](./on-call.md); SLI/SLO math and budget burn in [./slo-error-budget.md](./slo-error-budget.md); blameless postmortem craft in [./postmortem-culture.md](./postmortem-culture.md). Here is how the machine runs while the page is down.

## Severity Assignment Under Pressure

The table above maps severities to response times; the craft is applying it cold at 3 a.m. PagerDuty: "The first step... is to determine what actually constitutes an incident... with the lower numbered severities being more urgent... you are able to take more risky moves to resolve a higher severity issue." Two rules prevent the classic failure modes:

- **Tie-breaking:** "If you are unsure which level an incident is (e.g. not sure if SEV-2 or SEV-1), treat it as the higher one. During an incident is not the time to discuss or litigate severities, just assume the highest and review during a postmortem." This kills SEV deflation; inflation is countered in review.
- **Major-incident trigger:** "Anything above a SEV-3 is automatically considered a 'major incident'" — severity decides whether you page an IC and open an incident channel, not just how fast you type.

A SEV-1 also changes *what you may do*: public notification, executive liaison, and riskier mitigations — all of which need IC authorization.

## Roles: Why the Incident Commander Does Not Fix Things

Google's system "is based on the Incident Command System," and its first principle is "Recursive Separation of Responsibilities": "It's important to make sure that everybody involved in the incident knows their role and doesn't stray onto someone else's turf."

- **Incident Commander** — "The incident commander holds the high-level state about the incident. They structure the incident response task force, assigning responsibilities according to need and priority. De facto, the commander holds all positions that they have not delegated." PagerDuty is blunt: "Delegate all repair actions, the Incident Commander is NOT a resolver." The reason is cognitive, not ceremonial: the IC is the single source of truth of what is happening and what happens next — a person debugging a kernel cannot also sequence mitigations, approve risky actions, and answer executives. Google's "unmanaged incident" parable names the failure this prevents — "Freelancing": an engineer ships an uncoordinated fix and kills the remaining servers.
- **Operations Lead** — "The Ops lead works with the incident commander to respond to the incident by applying operational tools to the task at hand. The operations team should be the only group modifying the system during an incident."
- **Communications Lead** — "the public face of the incident response task force," owning "periodic updates to the incident response team and stakeholders (usually via email)" plus the status page — so engineers never write prose to customers at 3 a.m.
- **Scribe / Planning** — the scribe captures the timeline live; "The planning role supports Ops by dealing with longer-term issues, such as filing bugs... arranging handoffs, and tracking how the system has diverged from the norm so it can be reverted once the incident is resolved." Small teams merge the two, but timeline capture must survive.

## The Lifecycle: Detect → Declare → Mitigate → Resolve

**Declare (after detection).** Detection is mechanical; *declaration is human judgment*. Google's three tests: "Do you need to involve a second team in fixing the problem? Is the outage visible to customers? Is the issue unsolved even after an hour's concentrated analysis?" Late declaration is the expensive mistake — "It is better to declare an incident early and then find a simple fix and close out the incident than to have to spin up the incident management framework hours into a burgeoning problem." Exit criteria: severity assigned, IC named in-channel, incident channel + live incident state document open — "The incident commander's most important responsibility is to keep a living incident document."

**Mitigate.** Policy: *revert first, diagnose later*. Google's first best practice: "Prioritize. Stop the bleeding, restore service, and preserve the evidence for root-causing." The argument is an MTTR-vs-knowledge trade: users pay for every minute of impact, while root cause is reconstructible afterward *if evidence survives* — so mitigation steps are logged, and destructive options (failovers that erase state) weigh evidence loss against user harm. Exit criteria: symptoms contained (back inside SLO — burn math in [./slo-error-budget.md](./slo-error-budget.md)); no unapproved changes in flight.

**Resolve.** Mitigation is not resolution: resolved means the trigger is fixed or guarded, recovery is confirmed by monitoring, and temporary measures (scaled capacity, disabled features) are ticketed for reversion. Then the handoff to [./postmortem-culture.md](./postmortem-culture.md).

## Communications: Cadence and Audience

PagerDuty's guidance is effectively a template spec. Initial post: "The first communication should indicate that an incident is under investigation. The goal here is to avoid a customer experiencing symptoms of the incident, checking status pages or social media accounts, and not seeing awareness of the issue from the business." Updates: "delivered at least every 20 minutes from the scoping update during the first two hours," then a reduced "long incident communication model" — each update should "Provide an expectation of when the next update will be posted." Resolution: "Your final communication should be posted when full recovery of the incident has been confirmed by the Incident Commander."

Atlassian compresses the same doctrine: "1. Communicate early... 2. Communicate often — Provide updates every 30 minutes (or whatever cadence is appropriate for the situation)... 3. Communicate precisely... 4. Stay consistent across channels... 5. Own the problem — While an incident may technically be caused by another provider, in your customers' eyes, it's a problem with your service."

**Audience abstraction** — one incident, three renderings: users get symptoms and workarounds (no service names, no blame); executives get business impact and the decisions they owe (credits, disclosure); engineers get service names, dashboards, mitigation state. The comms lead maintains all three from one timeline. The fastest trust-killer is the information vacuum: silence reads as incompetence or concealment.

## Timeline Reconstruction

Postmortem timelines rot: memories drift, chat scrolls, everyone timestamps in their own zone. Rules that survive audit: capture *live* — the scribe appends, never rewrites; anchor entries to machine sources of truth (alert timestamps, deploy events, on-call ack logs); one timezone, UTC; chat logs as tiebreaker — Google: IRC "can be used as a log of communications about this event, and such a record is invaluable... We've also written bots that log incident-related traffic (which is helpful for postmortem analysis)." If the timeline disagrees with a machine timestamp, the machine wins.

## Coordination at Scale

Pick a model deliberately for multi-team SEV-1s: **swarming** (everyone self-organizes — fast to start, chaotic past ~3 teams) vs **command with subincidents** (Google's recursion: a role leader might delegate "creating subincidents" or components that "report high-level information back up to the leaders"). Channel hygiene: one channel per incident; every action stated as *action → expected effect → timestamp*; hypotheses in threads, decisions in-channel; backseat debugging and "VP suggestions" get parked by the IC.

**Shift handoffs** are the highest-risk moment. Google requires a "Clear, Live Handoff": the outgoing commander states, "'You're now the incident commander, okay?', and should not leave the call until receiving firm acknowledgment of handoff. The handoff should be communicated to others working on the incident so that it's clear who is leading the incident management efforts at all times." Rotation design: [./on-call.md](./on-call.md).

## Metrics: TTD, TTA, TTR — and How They Get Gamed

- **Time to Detect (TTD):** impact start → page. Gamed by redefining "impact start"; anchor to the first bad user event.
- **Time to Acknowledge (TTA):** page → human ack. Gamed by auto-ack scripts; require a substantive first message.
- **Time to Resolve/Restore (TTR):** impact start → impact ends. Gamed by measuring from ack or calling "mitigated" resolved.

Every TTR slice burns error budget ([./slo-error-budget.md](./slo-error-budget.md)); action items from the review are how the next TTR shrinks ([./postmortem-culture.md](./postmortem-culture.md)). Rehearse in game days ([./chaos-engineering.md](./chaos-engineering.md)) — Google: "Incident management proficiency atrophies quickly when it's not in constant use."

## Interview Scenarios (Worked)

**1. Data-loss-adjacent SEV-1 mid-migration.** A migration script is corrupting rows while writes continue. Strong answer: declare SEV-1, name an IC (not the person fixing it); stop the bleeding *without destroying evidence* — pause migration and dual-writes before any failover, snapshot affected tables; quantify the loss window from WAL/binlogs before choosing rollback vs forward-fix; comms lead drafts the customer notice, data-exposure line cleared by exec/legal; postmortem within 48h. *Rubric:* 5 = evidence-preserving mitigation + explicit IC/Ops split + quantified loss window; 3 = mitigates but deletes evidence or skips declaration; 1 = "re-run the script."

**2. Distributed incident, two teams each think the other owns it.** Payments sees failures and blames ledger; ledger's dashboards are green. Strong answer: the responder who cannot localize escalates fast — "Do you need to involve a second team?" is a declaration trigger, not a failure; a single IC owns the cross-team *response* even before anyone owns the cause; subincidents per team, one shared timeline; both on-calls pulled in by the IC, not by peer-to-peer Slack. *Rubric:* 5 = early declaration + named IC + parallel subincidents; 3 = escalates without taking command (bystander incident); 1 = "ping the other team and wait."

**3. Comms failure worsening customer trust.** A 40-minute outage handled well technically, but the status page said "Investigating" for 35 minutes and support promised ETAs the bridge never gave. Strong answer: name the mechanism — silence during a visible incident reads as concealment; the comms lead posts on a fixed clock ("every 20 minutes... during the first two hours") and *no one else* promises ETAs; support scripts derive from the same timeline ("Stay consistent across channels"); the resolution post owns the problem (Atlassian). *Rubric:* 5 = separated comms role + fixed cadence + one source of truth; 3 = fixes the status page ad hoc; 1 = "engineers should have posted more."

## Key Takeaways

- Severity is impact-based, tie-broken upward, and sets response speed *and* risk authorization.
- The IC delegates every repair action; Ops is "the only group modifying the system"; comms owns non-engineer audiences; the scribe owns the truth.
- Declare early (the three tests): late command turns an outage into an unmanaged spiral.
- Revert first, diagnose later — but preserve evidence.
- Communicate on a clock (initial → every 20–30 min → resolution), audience-appropriate, one source of truth.
- Timelines are captured live from machine sources in UTC; chat logs break ties.
- Multi-team incidents need a named IC over the response, subincidents, and live handoffs.
- TTD/TTA/TTR feed error-budget burn and the postmortem loop; rehearse in game days.

## References

- [Google SRE Book — Chapter 14: Managing Incidents](https://sre.google/sre-book/managing-incidents/) — Incident Command System roles, declaration tests, best practices (quoted verbatim; fetched this session).
1. PagerDuty, "[Incident Response Documentation](https://response.pagerduty.com/)" — process overview and role training index.
2. PagerDuty, "[Severity Levels](https://response.pagerduty.com/before/severity_levels/)" — SEV definitions, tie-breaking rule, major-incident threshold.
3. PagerDuty, "[Different Roles for Incidents](https://response.pagerduty.com/before/different_roles/)" — "the Incident Commander is NOT a resolver."
4. PagerDuty, "[During an Incident](https://response.pagerduty.com/during/during_an_incident/)" — bridge conduct, stakeholder comms.
5. PagerDuty, "[External Communication Guidelines](https://response.pagerduty.com/during/external_communication_guidelines/)" — initial/periodic/resolution cadence.
6. Atlassian Statuspage, "[Incident communication tips](https://support.atlassian.com/statuspage/docs/incident-communication-tips/)" — early/often/precise/consistent/own-it.

## Cross-References

- [./on-call.md](./on-call.md) — rotation design, alert quality, escalation paging.
- [./slo-error-budget.md](./slo-error-budget.md) — burn-rate math turning TTR slices into budget.
- [./postmortem-culture.md](./postmortem-culture.md) — blameless review, template, severity/escalation matrices.
- [./chaos-engineering.md](./chaos-engineering.md) — game days and failure-injection rehearsals.
- [./slo-sli-sla.md](./slo-sli-sla.md) — SLI/SLO/SLA definitions underlying severity decisions.
