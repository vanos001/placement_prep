# Follow-up Tree: SLOs and Error Budgets

## Overview

"What's the difference between an SLI, an SLO, and an SLA?" is the reliability opener that junior candidates answer with definitions and senior candidates answer with *decision rights*: who is allowed to trade reliability for velocity, on what evidence, and with what consequence when the trade runs out. The follow-up ladder is the standard interview for SRE, platform, and senior-backend roles because it tests a rare skill — reasoning about reliability as a *budgeted resource* rather than an aspiration. Each rung peels a layer: measuring the right indicator from the right vantage, converting the objective into decisions, alerting on the budget's *rate of loss* rather than symptoms, and — the judgment rung — what must never page a human and why budget politics, not mathematics, is where SLO programs die. This page walks the ladder: what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates. Handoffs are deliberate: the telemetry plumbing that turns raw events into SLI windows is the connection map in [Observability Pipeline](../connection-atlas/observability-pipeline.md), and the operational SRE canon this ladder condenses lives in [SLI, SLO, SLA](../../sre/slo-sli-sla.md) and [SLO Error Budget](../../sre/slo-error-budget.md). Primary external sources: Google's SRE book and workbook ([SRE Book](https://sre.google/sre-book/table-of-contents/), [Implementing SLOs](https://sre.google/workbook/implementing-slos/)).

## The Opening Question

**"What is the difference between an SLI, an SLO, and an SLA?"**

The expected core answer: an SLI is a *measurement* of a service quality dimension over a window — the fraction of requests that succeeded, the fraction served under 300 ms; an SLO is a *target* on that indicator — 99.9 percent of requests succeed over 30 days; an SLA is a *contract* with customers that attaches business consequences (credits, penalties) to missing an externally committed target, which is almost always looser than the internal SLO.

A weak answer recites the three definitions and stops — it cannot say why the distinction *exists*. The strong answer states the function of each: the SLI is chosen to reflect user experience (not infrastructure health), the SLO is chosen to leave an error budget (reliance margin you deliberately do *not* spend on perfection), and the SLA exists so the internal targets have room to fail without contractual damage. The sentence the rung wants: "the SLO is not the best you can do — it is the *deliberate* compromise that buys you the freedom to ship." The follow-up that escalates: **"Who decides what to do when the budget is spent?"**

## Level 2: Choosing SLIs — Measure What the User Experiences, from Where They Experience It

**What it tests:** whether the candidate can design an indicator rather than inherit one — the difference between "CPU is below 80 percent" (a resource proxy) and "the fraction of valid requests served correctly within the latency bound" (a user-facing result).

**Weak answer:** proposes infrastructure metrics as SLIs — CPU, memory, error counts from the server — without noticing these measure the *system's* comfort, not the *user's* outcome.

**Strong answer:** defines SLIs as request-shaped ratios (good events / valid events) across the four golden signals' user-facing subset — availability, latency (with a threshold, not an average — the mean-vs-tail misconception is documented in [Averages Don't Summarize Latency](../misconceptions/averages-summarize-latency.md)), correctness, freshness — and knows measurement *vantage* matters: client-side and prober-based measurement see DNS, TLS, CDN, and last-mile failure that server-side metrics structurally cannot.

**Escalation trigger:** "Your server-side success rate is 99.99 percent, but users complain constantly. How can both be true?"

**Answer.** Both are true because they measure different journeys: the server's 99.99 percent conditions on *requests that reached it* — failures in DNS, TLS, the CDN, the last mile, or a silently dropping middlebox never appear in the denominator (the full hop-by-hop surface is the chain in [URL to Page](./url-to-page.md)). The measurement vantage defines the SLI's blind spots, and the fix is layering vantages: synthetic probes (whole path, thin sampling), client-side telemetry (true, but lossy and delayed), and server-side metrics (precise, but conditional on arrival). The strong answer also pins the SLI *definition* details that later rungs depend on: what counts as a valid request, what counts as good (which status codes, which latency threshold — chosen from user-observed behavior, not round numbers), and over what window (28-day rolling is the SRE-book convention because it tolerates deployment schedules and weekly cycles — [Implementing SLOs](https://sre.google/workbook/implementing-slos/)). The senior framing: an SLI is a *contract about measurement* — the moment the team argues about what the number means is the moment the definition was under-specified.

## Level 3: The Error Budget — Reliability as a Spent Resource

**What it tests:** whether the candidate understands the budget as an *organizational instrument* — the quantified answer to the feature-velocity-versus-stability fight — rather than a dashboards-and-percentages exercise.

**Weak answer:** "The error budget is 100 minus the SLO, so 0.1 percent" — arithmetic without a decision model, which is how budgets become wall decorations.

**Strong answer:** states the budget's role as decision currency: the SRE-book rule that when the budget is exhausted, feature releases pause in favor of reliability work, and when budget is plentiful, risk-taking is *licensed*; knows who the parties are (product owns the target's business level, engineering owns meeting it, SRE owns the review), what spends it (failed requests, and — the part juniors miss — *changes*: deploys, migrations, experiments are the largest planned spenders), and why the 99.9 target leaves room for the product's release cadence.

**Escalation trigger:** "Product wants weekly launches; operations wants three nines. How does the budget resolve this without a meeting that never ends?"

**Answer.** Convert the dispute to arithmetic: a 99.9 percent SLO over 28 days permits about 40 minutes of unavailability-equivalent error per window — and every deploy carries expected risk (a 0.2 percent chance of a 10-minute incident costs roughly 1.2 seconds of budget). Now the conversation is quantitative: the *number of deploys* the budget can absorb at your observed per-deploy risk is computable, and either the SLO loosens, the release risk shrinks (canaries, staged rollouts — the discipline in [Canary Releases](../../sre/canary-releases.md)), or the cadence drops. This is the budget's actual function — replacing recurring negotiation with a shared, measured constraint ([SLO Error Budget](../../sre/slo-error-budget.md) carries the policy mechanics). The senior details that earn the rung: budgets are consumed by *all* errors, not just outages — chronic 1-in-200 slow responses spend budget invisibly, which is why latency SLOs matter as much as availability SLOs; and multi-window multi-burn alerting (next rung) exists because the *policy* ("pause releases at zero budget") needs an *early warning* to fire before exhaustion. The judgment sentence: "the budget is the mechanism that lets you be reliably imperfect on purpose — exhaust it and the system's constitution says what happens next, no meeting required."

## Level 4: Burn Rates and Multi-Window Alerting — Paging on the Budget, Not the Symptoms

**What it tests:** the quantitative rung: whether the candidate can design alerting on budget *consumption rate* and explain why naive per-symptom alerting fails at scale.

**Weak answer:** "Alert when the error rate exceeds 0.1 percent" — confuses the SLO with a threshold, pages constantly on harmless blips, and misses slow bleeds.

**Strong answer:** explains burn rate — the ratio of actual consumption to the consumption pace that would exactly exhaust the window's budget — and the standard multi-window pairing (fast burn: high rate over a short window *and* confirmed over a slightly longer one, to page for things that can exhaust the month's budget in hours; slow burn: lower rate over long windows, to file tickets for chronic leaks); knows the pairing exists to cut false pages (the short window alone fires on every blip) and to catch both cliff-falls and slow bleeds.

**Escalation trigger:** "A 5-minute full outage burns how much of a 28-day 99.9 budget — and which alert should have caught it?"

**Answer.** The arithmetic: 28 days is 40,320 minutes, and 0.1 percent budget is 40.3 error-minutes — a 5-minute total outage spends one-eighth of the month's budget, a 14.4× burn rate. The alert that catches it: fast-burn alerting at 14.4× (a 1-hour window that, sustained, would exhaust 30 days of budget in an hour) confirmed over a 5-minute window — page immediately, because two more such events end the month's tolerance. The complement: slow-burn at 6× over 6 hours (would exhaust in ~5 days) confirmed over 30 minutes — a ticket, not a page, for the chronic bleed that never trips the fast window. The strong answer also states *why* multi-window: the short window provides speed, the longer window provides confirmation — requiring both collapses the false-positive rate that made static thresholds unbearable (the SRE workbook's alerting chapter is the canonical source; the evaluation plumbing is [Observability Pipeline](../connection-atlas/observability-pipeline.md)). The senior detail: burn-rate alerts are *symptom-based and SLO-relative* — they fire on user-visible error regardless of cause, which is precisely the property that keeps page volume bounded: you page on the budget, not on every component's complaints.

## Level 5: What Not to Alert On — and the Politics of Spent Budgets

**What it tests:** the judgment rung: the negative space of alerting (causes versus symptoms, alert fatigue, the human cost) and the organizational failure modes of SLO programs — budgets nobody enforces, targets nobody chose, pages nobody thanks you for.

**Weak answer:** "More alerts equal more reliability" — the inverse of the truth, and the sentence that produces pager burnout and normalized snoozing.

**Strong answer:** states the doctrine — alert on *symptoms the user feels*, reserve pages for actionable-and-urgent, let causes be dashboarded and ticketed; and names the political realities: an SLO set by engineering alone (too strict) starves the roadmap, a budget policy with no enforcement is theater, and the fix is the review cadence — budget reviews with product at the table, quarterly recalibration, and the honesty to delete alerts that page without action.

**Escalation trigger:** "Your on-call gets 30 pages a week; 25 are acknowledged without action. What do you change, concretely?"

**Answer.** Triage the pages by two axes — *did a human need to act*, and *was the urgency real* — and expect the outcome the SRE book predicts: most alerts are cause-proxies that belong on dashboards, with SLO-relative burn alerts carrying the pager ([On-Call](../../sre/on-call.md) carries the human-factors detail). The concrete program: every alert must document the symptom it protects, the action it expects, and its page-to-action ratio; alerts below the bar demote to tickets or dashboards. Then rebuild the page set from the SLOs: one fast-burn and one slow-burn rule per user-facing SLI, causes relegated below. The politics rung completes the chain: if the 30-page regime persists, the real failure is governance — nobody owns the decision to *stop* alerting — which is why SLO programs install a review cadence (weekly budget reports, quarterly target review, post-incident budget accounting — the culture mechanics in [Postmortem Culture](../../sre/postmortem-culture.md) and [Incident Management](../../sre/incident-management.md)). The judgment sentence the rung wants: "an alert is a demand on a human's sleep; the burn-rate design is how you make each demand one the budget justifies — and the review cadence is how the program survives its own success."

## How to Approach Unfamiliar Variations

The template for SLO variations — "SLO for a batch pipeline," "SLO for a dependency you don't own," "multi-tenant budgets," "SLO for cost":

1. **Find the user-facing event and define good/valid.** Every SLI is a ratio over events; batch pipelines have *freshness* SLIs (data age at read time), APIs have latency/availability ratios, queues have consumer lag (the lag-SLO discipline appears in [Message Queues](./message-queues.md)). Name the event before arguing the target.
2. **Convert the target to budget arithmetic immediately.** Any percentage becomes error-minutes per window; the budget is what makes the SLO *decidable*. If a variation gives you a target, compute what it permits per day/hour before discussing policy.
3. **Separate what you page on from what you track.** Pages: user-symptom burn rates with multi-window confirmation. Tickets/dashboards: causes, capacities, resource proxies. A variation asking "should we alert on X" is asking which class X belongs to.
4. **For governance questions, name the cadence.** SLO programs fail by defaulting: no owner for targets, no consequence for empty budgets. The answer is review machinery — who recalibrates, who enforces the pause, who signs off — the same ownership discipline as the [Capacity Planning](../../sre/capacity-planning.md) loop.

## Interview Questions

**Q: A 99.99 availability SLO on a service is proposed. Push back or accept?**
A: Do the arithmetic and ask what it buys: 99.99 over 28 days permits ~4 error-minutes per month — one typical deploy mishap consumes it. Accept only if the service's failure cost justifies near-zero tolerance *and* the release cadence is correspondingly glacial or the change process is exceptionally engineered. Otherwise propose 99.9 with a burn-rate alerting program: the honest question is not "highest nine" but "what risk does the product want to run, stated in budget."

**Q: Your fast-burn alert fires; investigation shows the cause is a dependency's degradation you cannot fix. What should the runbook and the SLO design have prepared?**
A: The runbook: mitigate at your layer (shed load, serve stale, disable the feature — the bulkhead patterns in [Bulkheads](../../sre/bulkheads.md)) while escalation proceeds, because the page's job is protecting the budget, not fixing the dependency. The SLO design: dependencies' failure contribution should be visible in the SLI decomposition — if a vendor dependency makes 99.9 structurally unreachable, either the SLO is renegotiated or the dependency is isolated behind a fallback; an SLO that ignores a known lossy dependency is a number, not a plan.

**Q: Product asks to spend the entire quarter's budget on a launch-day experiment. What framework do you use to answer?**
A: Price it and scope the blast: compute the expected spend (probability × duration × affected traffic share), compare against remaining budget and the quarter's other committed spends, and require reversibility (feature-flagged, the mechanism in [Feature Flags](../../sre/feature-flags.md)) with pre-agreed abort criteria. The answer is rarely "no" — it is "yes, for this slice of traffic, with these guards, and here is what the budget looks like if it goes wrong." That is the budget functioning as decision currency rather than a veto.

**Q: Why does the SRE doctrine prefer paging on error-budget burn over paging on causes like high CPU or full disks?**
A: Because causes only matter when they become user-visible symptoms, and the mapping is many-to-one: dozens of causes can produce one symptom, so cause-based paging scales alert count with system complexity while symptom-based paging scales it with user-facing SLOs — bounded by design. CPU at 90 percent may be a healthy busy system; the budget-burn alert fires only when requests actually fail or stall, which is the moment a human adds value. Causes get dashboards and capacity planning ([Capacity Planning](../../sre/capacity-planning.md)); symptoms get the pager.

## Key Takeaways

- SLI is the measurement (user-outcome shaped, vantage-dependent), SLO the target chosen to leave a spendable margin, SLA the contractual outer bound — the hierarchy exists to protect the interior from business consequences.
- An SLO is a deliberate compromise, not a maximum: its purpose is to license releases, and its level should be derived from the release cadence the product needs.
- The error budget converts the velocity–stability dispute into arithmetic; exhausting it triggers a pre-agreed policy (release pause, reliability priority) instead of a negotiation.
- Burn-rate alerting pages on the budget's rate of loss with multi-window confirmation — fast burn for cliff-falls, slow burn for bleeds — keeping page volume bounded as complexity grows.
- Alert on symptoms users feel; causes belong on dashboards and in capacity plans. Every page should name the symptom it protects and the action it expects.
- SLO programs live or die on governance: owned targets, enforced budget policy, quarterly recalibration, and postmortems that account for budget.

## Cross-References

- [Message Queues](./message-queues.md) — consumer lag as an SLO'd symptom, the queue-flavored instance of this ladder.
- [Connection Pooling](./connection-pooling.md) — the queueing arithmetic behind latency SLOs.
- [URL to Page](./url-to-page.md) — the hop-by-hop surface behind vantage-dependent blind spots.
- [Observability Pipeline](../connection-atlas/observability-pipeline.md) — the coupling map: the telemetry plumbing that evaluates SLI windows and burn rates.
- [SLI, SLO, SLA](../../sre/slo-sli-sla.md) — the book chapter defining the three contracts this ladder builds on.
- [SLO Error Budget](../../sre/slo-error-budget.md) — the book chapter on budget policy and enforcement.
- [Canary Releases](../../sre/canary-releases.md) — the staged-rollout discipline that shrinks the per-deploy budget spend.
- [Feature Flags](../../sre/feature-flags.md) — the control plane that makes risky spends reversible.
- [On-Call](../../sre/on-call.md) — the human factors of paging, alert fatigue, and actionability.
- [Incident Management](../../sre/incident-management.md) — how budget spend is triaged and declared during incidents.
- [Postmortem Culture](../../sre/postmortem-culture.md) — where budget accounting meets organizational learning.
- [Capacity Planning](../../sre/capacity-planning.md) — the cause-side complement: resource signals that feed planning, not pagers.
- [SRE Book](https://sre.google/sre-book/table-of-contents/) and [Implementing SLOs](https://sre.google/workbook/implementing-slos/) — the primary sources for the doctrine cited throughout.
