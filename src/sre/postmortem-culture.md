# Postmortem and Incident Response Culture

> "Postmortems are the cultural mechanism that turns an outage into institutional memory." — adapted from the Google SRE Book, Chapter 15 (Postmortem Culture: Learning from Failure).

A postmortem is the written record of an incident: what happened, why, what the impact was, and what we are going to change so it does not happen again. The single document is the easy part. The hard part — and what this chapter is about — is the *culture* that surrounds it: blamelessness, psychological safety, an explicit severity matrix, a designated incident commander (IC), and an escalation matrix that everyone has memorized before the pager goes off.

## Why Blameless? The Argument from Psychological Safety

The defining property of a blameless postmortem is that **the postmortem never blames an individual**. It can blame a process, a missing check, a misleading dashboard, an unclear ownership boundary — but never "Alice pushed the bad commit." There are three reasons, and all of them are pragmatic rather than ethical:

1. **Failure is mostly systemic.** The person who clicked "deploy" was usually the last link in a long chain of decisions that *invited* the failure: a CI pipeline with no canary stage, a runbook reviewed 18 months ago, an ambiguous ownership boundary. Firing Alice and leaving the system untouched guarantees the next engineer triggers the same bug next quarter.
2. **Blame destroys the information you need.** If a postmortem is a search for "who to fire," every future incident report becomes a defense lawyer's brief: facts get scrubbed, timelines get massaged, the embarrassing diagnostic details disappear. The organization stops learning.
3. **Blame is correlated with worse reliability.** The Google SRE Book and SRE Workbook make the empirical observation that blameless cultures see *more* incidents reported — not because they break more, but because the fear of disclosure is gone. The DORA research program reports the same pattern measuring "blameless culture" as a predictor of elite delivery.

The phrase most often quoted is from John Allspaw (then at Etsy): **"If a postmortem is not blameless, it is not a postmortem."** The corollary is that blamelessness is not soft — it is the precondition for the rest of the engineering process to work.

### What Blameless Does *Not* Mean

A common misreading: "blameless" means "no accountability." It does not. Action items have named owners and due dates. Repeated identical failures, after the same fix has been agreed and not implemented, are a management problem, not an engineering one. The rule is: **blame the system, hold people accountable for fixing the system.**

## The Postmortem Template

A good template is short and rigid. The point is consistency, not creativity. Below is the template used in slightly different forms by Google, Etsy, GitHub, and most adopters of the SRE workbook.

```markdown
# Postmortem: <one-line summary>

- Date / Time (UTC): 2024-03-12 14:00 – 14:47 UTC
- Severity: SEV-2
- Authors: @alice, @bob
- Status: Resolved
- Stakeholders: Payments, Customer Support, Risk

## 1. Summary
Three sentences. What broke, for whom, for how long, and the headline cause.
A reader should understand the incident from this paragraph alone.

## 2. Impact
- User-visible impact: 12,471 failed checkout attempts (~3.1% of attempts in window)
- Business impact: ~$84k in blocked GMV, recovered ~$61k via retry queue
- External status page: posted at 14:09, resolved at 14:51
- Reports from customers: 47 support tickets, 2 social media posts

## 3. Timeline (UTC, with sources)
14:00  PagerDuty fires on `checkout_5xx > 1%` (source: PD-12345)
14:03  IC (@alice) acknowledges, opens #incident-3301
14:07  SRE on-call (@bob) confirms DB connection pool at 100%
14:12  Hypothesis: connection leak in payments-service v4.2.1, deployed 13:55
14:18  Rollback initiated (deploy rev 4.2.0)
14:23  Rollback complete, 5xx rate falling
14:31  Error rate below SLO threshold; IC declares mitigated
14:47  Last residual error clears; IC declares resolved

## 4. Root Cause
A short narrative section (200–500 words). Use "5 Whys" or a fishbone diagram.
Be specific. "The connection pool leaked" is not enough; "the pool's
`release()` path was bypassed when a 401 from the upstream auth service
threw an exception before the finally block executed" is.

## 5. Contributing Factors
- No integration test for the 401 path → leak not caught in CI
- Connection-pool gauge metric existed but alert threshold was 95% (too high)
- Deploy window: 13:55 UTC (peak EU checkout traffic)
- The runbook for this alert was last edited 11 months ago

## 6. What Went Well
- Detection: alert fired within 60s of first error
- Rollback completed in 5 min (Drain + Deploy < 5 min)

## 7. What Went Poorly
- Time to identify root cause: 18 min (should have been < 5)
- Status page update delayed 9 min (incident bridge confusion)

## 8. Action Items
| Priority | Action | Owner | Issue | Due |
|---|---|---|---|---|
| P1 | Add 401-path integration test | @payments-team | PAY-4471 | 2024-03-19 |
| P1 | Lower pool saturation alert threshold to 80% | @sre-alerts | SRE-8821 | 2024-03-14 |
| P2 | Runbook refresh for `checkout_5xx` | @alice | SRE-8830 | 2024-03-26 |
| P2 | Move deploy window to 09:00 UTC | @rel-eng | REL-2204 | 2024-03-21 |
| P3 | Add leak-detection canary to staging | @qa-platforms | QA-1192 | 2024-04-15 |

## 9. Appendices
- Grafana snapshot: https://grafana.example.com/d/checkout?from=...
- PagerDuty incident: PD-12345
- Slack archive: #incident-3301 (exported)
```

The shape matters more than the wording. Every section should be answerable in under 30 minutes by a single author with help from chat logs and dashboards. If a section takes longer, it usually means the question is wrong — for example, "root cause" should never turn into a 5-page essay; if it does, the incident is too complex and needs a separate **analysis document** linked from the postmortem.

## Severity Matrix (SEV-1 through SEV-4)

Severity is decided at triage time and may be upgraded or downgraded by the IC. It determines who gets paged, how fast the response is, and how much senior review the postmortem needs.

```
┌────────┬──────────────────────────────┬──────────────┬──────────────┬──────────────────────┐
│ Sev    │ Definition                  │ Response SLO │ Escalation  │ Postmortem required? │
├────────┼──────────────────────────────┼──────────────┼──────────────┼──────────────────────┤
│ SEV-1  │ User-facing outage, data     │ 5 min ack    │ VP+         │ Yes, mandatory,      │
│        │ loss, or revenue loss > $X   │ 15 min page  │ Director+   │ reviewed by SRE lead │
│        │ across multiple regions      │              │ on call     │                      │
├────────┼──────────────────────────────┼──────────────┼──────────────┼──────────────────────┤
│ SEV-2  │ Major degradation: errors / │ 15 min ack   │ IC + team   │ Yes, mandatory       │
│        │ latency above SLO for a core │ 30 min page  │ lead        │                      │
│        │ user journey                 │              │             │                      │
├────────┼──────────────────────────────┼──────────────┼──────────────┼──────────────────────┤
│ SEV-3  │ Minor degradation, isolated  │ 4 hr         │ Team lead   │ Recommended          │
│        │ feature, or non-critical path│              │             │                      │
├────────┼──────────────────────────────┼──────────────┼──────────────┼──────────────────────┤
│ SEV-4  │ Cosmetic / annoyance /      │ Next         │ Ticket      │ No (ticket suffices) │
│        │ non-urgent bug               │ business day │             │                      │
└────────┴──────────────────────────────┴──────────────┴──────────────┴──────────────────────┘
```

Two common mistakes:

1. **SEV inflation.** Everything feels critical at 3am. The test is: *if this exact condition persisted for an hour, would the business lose real money or a real customer?* If yes, SEV-1; if not, downgrade.
2. **SEV deflation.** "Only 0.5% of users, ignore it" — that 0.5% may be your largest enterprise account. Severity is about *impact*, not the fraction of users affected.

## The Incident Commander Role

The IC is the single decision-maker during the response. The role has three properties that distinguish it from the on-call SRE:

- **The IC does not type fix commands.** The IC runs the bridge, asks questions, takes notes, and authorizes high-risk actions (failover, deploy rollback, customer comms). The person who is SSH'd into the box fixing the bug should *not* also be running the room.
- **The IC is the source of truth for status.** When leadership asks "are we down?", the answer comes from the IC, not from the engineer who happens to have Slack open.
- **The IC is replaceable.** Hand-off is explicit and timestamped in the chat log: `@alice handing IC to @carol at 14:30 UTC`.

The Google SRE Book's chapter on managing incidents (Chapter 14, "Managing Incidents") enumerates the IC's explicit responsibilities: *communicate, take directive responsibility, delegate, otherwise stay out of the way*. The "stay out of the way" is the most violated clause in practice — ICs who try to debug from the chair end up blocking the actual responders.

```
Incident org chart (during a SEV-1):

                ┌────────────────────┐
                │  Incident Commander│
                │  (single point of  │
                │  authority)        │
                └────────┬───────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼─────┐   ┌──────▼──────┐  ┌─────▼─────┐
   │ Ops /    │   │ Comms /     │  │ Scribe    │
   │ Resolve  │   │ Status page │  │ (timeline │
   │ lead     │   │ Updates     │  │  + log)   │
   └────┬─────┘   └─────────────┘  └───────────┘
        │
   ┌────▼─────────────────────────┐
   │ Individual subject-matter     │
   │ engineers (DB, network, app)  │
   └───────────────────────────────┘
```

Three roles worth naming explicitly:

- **Scribe**: writes the timeline as the incident unfolds. This is the cheapest insurance against the "what time did we roll back?" question that every postmortem needs. Many teams rotate this role to a junior on-call — it is the best training ground for future ICs.
- **Comms lead**: owns the public status page, executive updates, and customer-impact emails. At GitHub, a separate team ("Incident Response Coordinators") takes this role full-time so engineers never have to write to executives at 3am.
- **Ops lead**: actually driving the fix; works with the SMEs (database, network, application).

## The Escalation Matrix

The escalation matrix answers two questions before they need to be answered at 3am: *who do I page when this alert fires?* and *who do I page when I'm out of my depth?*

```
┌──────────────────────────────────────────────────────────────────────┐
│ Alert tier            │ Page                         │ If no ack in │
├──────────────────────────────────────────────────────────────────────┤
│ Tier 1 (SEV-1 path)  │ Primary SRE on-call           │ 5 min        │
│                      │ → Secondary SRE on-call       │ +5 min       │
│                      │ → SRE manager + IC on-call    │ +5 min       │
│                      │ → VP Eng + Director           │ +10 min      │
├──────────────────────────────────────────────────────────────────────┤
│ Tier 2 (SEV-2 path)  │ Team on-call (product team)   │ 15 min       │
│                      │ → Team lead                   │ +15 min      │
│                      │ → SRE on-call if infra        │ +15 min      │
├──────────────────────────────────────────────────────────────────────┤
│ Tier 3 (SEV-3 path)  │ Slack channel ping            │ 4 hr         │
│                      │ → Team email list             │ +4 hr        │
└──────────────────────────────────────────────────────────────────────┘
```

Two non-obvious rules:

1. **Always page up, not sideways.** If the primary on-call is unreachable, page the secondary, then the manager — not three other engineers in the hope one of them is awake. "Spray-paging" creates chat noise and slows down the response.
2. **Never escalate on the basis of "I don't know what to do."** Escalate when (a) you cannot ack the page in the required SLO, (b) you cannot identify which service is the source, or (c) you cannot safely roll back. *Can* but *unsure* — pull in a SME. *Can't* — escalate.

## Production Examples

### Google's Postmortems

Google publishes a curated set of postmortems at `https://sre.google/postmortems/`. The canonical case is the 2019 **Google Cloud Storage global outage** caused by a single malformed DNS update that propagated further than the test had predicted. The published postmortem is a near-textbook example: a short summary naming the user-visible impact; a timeline that includes the moment engineering declared "we are wrong about the cause" (a section most teams omit out of embarrassment); a root-cause section distinguishing the *triggering* bug (a tool that should have rejected a config) from the *amplifying* factor (a control-plane cache that propagated it globally before revalidation); and action items with named owners, including non-engineering ones ("update customer-communication playbook"). The Google SRE Book's Chapter 15 ("Postmortem Culture") is the canonical reference.

### GitHub Incidents

GitHub maintains `https://www.githubstatus.com/` and writes a follow-up post for major incidents. A frequently-cited example is the **January 2023 incident** in which a database migration locked the `pull_requests` table on a primary, blocking merges globally for ~2 hours. The published postmortem is notable for two things: it explicitly named the timeline of the *wrong* hypothesis (the team initially suspected a load-balancer change — naming the wrong hypothesis is a teaching device), and it separated **operational fixes** (kill the migration, fail over) from **preventative fixes** (require migration dry-runs against a restored prod-sized copy, with a kill-switch timeout).

### Etsy's Debriefing Guide

Etsy's public **Debriefing Guide** is the most operational document on running a blameless review. Three of its rules are now industry-standard:

1. **Facilitator ≠ participant.** The person running the debrief should not have been on the bridge. This eliminates defensiveness.
2. **No "you" in the room.** Re-frame every question to "the system" — "why did the deploy proceed without the canary check?" not "why did you skip the canary?"
3. **Defer fix-discussion to the end.** The first two-thirds of the meeting is *understanding*; the last third is *fixing*. Mixing them produces shallow analysis because engineers race to the safe ground of "we'll just add a test."

## Comparison to Military After-Action Review (AAR)

The corporate postmortem is a direct descendant of the **US Army's After-Action Review (AAR)**, formalized in the 1970s at the National Training Center (NTC) at Fort Irwin. The Army's version is structured around four questions:

1. *What was supposed to happen?*
2. *What actually happened?*
3. *Why were there differences?*
4. *What do we do next time?*

Those four questions map almost trivially onto the modern SRE postmortem template: Summary → Timeline → Root Cause → Action Items.

| Aspect | Military AAR | SRE Postmortem |
|---|---|---|
| Frequency | Every mission, every training rotation | Every SEV-1/SEV-2 incident |
| Audience | Closed (the unit that executed) | Whole engineering org (open, indexed, searchable) |
| Timescale | Same day, ≤ 4 hours after action | 1–5 days after incident |
| Facilitator | Unit's own observer/controller | A non-participating SRE or facilitator |
| Format | Verbal, then recorded | Written first, then verbal review |
| Link to promotion | Formally decoupled but culturally coupled | Explicitly decoupled |

The most important cultural inheritance is the AAR's rule — codified in the 1980s — that the review must happen *close to the event, by the people who were there, with the facilitator distinct from participants*. The biggest divergence: SRE postmortems are *written and indexed*, while the AAR is spoken. The reason SREs write theirs down is that an outage can recur across years and across teams; the lessons need to outlive the people who were on the bridge.

## Anti-Patterns

- **"Human error" as a root cause.** This is not a root cause; it is a symptom of a system that allowed an unsafe action. Ask "why was the unsafe action reasonable given what the operator knew?" until you reach a process gap.
- **Action items without owners and due dates.** These are wishes, not commitments.
- **The postmortem that ships and is never read again.** A postmortem that nobody references after week 1 has zero ROI. Treat postmortems as a searchable knowledge base; promote relevant ones during onboarding.
- **Skipping the postmortem for "small" incidents.** The pattern of small incidents is where the next SEV-1 lives.

## Interview Questions

**Q1: What is a blameless postmortem and why does blamelessness matter?**
A: A postmortem that focuses on systemic causes, not individual blame. The assumption is that the operator made a reasonable decision given the information and tools available at the time. Blamelessness matters for three pragmatic reasons: (1) failures are mostly systemic, so punishing individuals does not fix the system; (2) blame destroys disclosure — engineers stop surfacing the embarrassing diagnostic details the org needs to learn; (3) blame correlates with worse reliability because incidents get under-reported. The cultural rule, attributed to John Allspaw, is "if it's not blameless, it's not a postmortem."

**Q2: Walk me through how you would structure a postmortem.**
A: I use a rigid template: one-line summary, impact (user-visible + business + external status), timeline with UTC timestamps and sources, root cause as a 200–500 word narrative using 5-Whys, contributing factors, "what went well" and "what went poorly", action items in a table with priority / owner / ticket / due date, and appendices (Grafana snapshots, PagerDuty ID, Slack export). The shape matters more than the wording. The postmortem is "done" only when all P1 action items have shipped or have explicit deferral dates.

**Q3: What is the role of the Incident Commander, and how is it different from the on-call SRE?**
A: The IC is the single decision-maker during the response. Three distinguishing properties: (1) the IC does *not* type fix commands — they run the bridge, ask questions, take notes, and authorize high-risk actions; (2) the IC is the source of truth for status to leadership; (3) the IC is replaceable with explicit, timestamped hand-off. The on-call SRE is one of the responders. IC and on-call can be the same person only for very small incidents; for anything SEV-1 the roles should be split so the responder isn't also answering "are we down?" every 3 minutes.

**Q4: How do you decide if something is SEV-1 vs SEV-2?**
A: Two tests: (1) Is the impact user-visible on a core user journey? (2) If this condition persisted for an hour, would the business lose real money or a real customer? SEV-1 is a user-facing outage, data loss, or revenue loss above the company's threshold; SEV-2 is major degradation (errors or latency above SLO on a core path) but not a full outage. Both require a postmortem. The most common failure mode is "SEV inflation" — at 3am everything feels SEV-1 — so the test has to be applied cold.

**Q5: How does the SRE postmortem compare to a military After-Action Review?**
A: The SRE postmortem is a direct descendant of the US Army's AAR formalized in the 1970s. Both share the four-question structure: what was supposed to happen, what happened, why the difference, what to do next time. The key differences: AARs are verbal and closed-audience; SRE postmortems are written, indexed, and open to the whole engineering org. The reason for the difference is that an outage can recur across years and team boundaries, so the lessons need to outlive the people who were on the bridge. Both inherit the rule that the review must happen close to the event, by the people who were there, with the facilitator distinct from the participants.

## References

- [Google SRE Book — Chapter 15: Postmortem Culture: Learning from Failure](https://sre.google/sre-book/postmortem-culture/)
- [Google SRE Book — Chapter 14: Managing Incidents](https://sre.google/sre-book/managing-incidents/)
- [Google SRE Workbook — Postmortems chapter](https://sre.google/workbook/postmortems/)
- [Google — Collected Postmortems archive](https://sre.google/postmortems/)
- [Etsy Debriefing Facilitation Guide](https://github.com/etsy/debriefing-facilitation-guide) — John Allspaw and colleagues
- [GitHub Engineering Blog — Incident postmortems](https://github.blog/category/engineering/) and [GitHub Status](https://www.githubstatus.com/)
- [PagerDuty — Incident Response documentation](https://response.pagerduty.com/)
