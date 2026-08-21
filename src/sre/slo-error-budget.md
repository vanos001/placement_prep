# SLO, SLA, SLI, and Error Budgets

> "100% is the wrong reliability target. If you have 100% reliability, you are not shipping features fast enough." — Paraphrase of the Google SRE Book, Chapter 3 (Embracing Risk).

The single most useful idea Google's SRE practice exported to the rest of the industry is the **error budget**. It reframes reliability from a moral binary ("we must always be up") to a quantitative one ("we have 43.8 minutes of unreliability this month; how do we want to spend it?"). The error budget sits on top of three primitives — SLI, SLO, SLA — and connects them to a fifth: the alert that fires when the budget burns too fast. This chapter covers all five in the form they actually take in production, with Prometheus config and the multi-window alerting math.

## SLI: Service Level Indicator

An SLI is a quantitative measurement of service reliability. It is a *number*, not a goal. The canonical form is:

```
SLI = (number of good events) / (total number of events)   ∈ [0, 1]
```

What counts as "good" is the hard design decision. The SRE Book gives four common shapes:

| SLI class | Definition of "good" | Example |
|---|---|---|
| **Availability / latency pair** | requests with `status < 500` *and* `latency < threshold` | 99.9% of `POST /checkout` requests return non-5xx within 800 ms |
| **Throughput** | successful units of work per unit time | `ingest_events_processed_total / wall_time > 10_000/s` |
| **Durability** | data records retrievable after `N` years | 99.999999999% (the famous "11 nines" S3 SLA) |
| **Correctness / freshness** | data in downstream store < N minutes stale | `now() - max(event_time)` over the last 5 min < 60s |

The biggest mistake teams make is choosing an SLI that is **easy to game**. A classic trap: "p99 latency." Once that becomes the SLO, the team routes slow requests to a separate queue / sheds them at the edge, and the SLI looks great while users are unhappy. The defense is to choose **user-journey-based SLIs** (below) and to define "good" in terms that an unsophisticated customer would also define as good.

### Choosing percentiles

Latency is reported as a percentile — p50, p95, p99, p99.9. The choice matters:

```
       p50   ←  half of users see this or faster
       p90   ←  1 in 10 users see this or faster
       p99   ←  1 in 100 users see this or faster   ←  SRE default
       p99.9 ←  1 in 1000 users see this or faster
       max   ←  the worst single request (not a percentile — a maximum)

Averages lie: 1000 requests at 100 ms + 1 request at 100 s
       → average = 200 ms, median = 100 ms, p99 = 100 s
```

Two rules: (1) **never alert or set SLOs on averages** — they hide the long tail that is the actual user experience. (2) **Pick the percentile that captures the worst user you care about.** p99 is the SRE default because it catches the slowest 1% of users — typically your most engaged customers, the ones with the largest carts.

## SLO: Service Level Objective

An SLO is the *target value* for an SLI over a *window*. Both parts matter. "99.9% availability" is not an SLO; "99.9% availability over a rolling 30-day window" is.

```
SLO = SLI  ≥  target   over   window

   Availability SLO:   (good_requests / total_requests) ≥ 0.999  over 30d
   Latency SLO:        fraction of requests with p99 < 800 ms ≥ 0.99  over 30d
```

The single most useful number to memorize is the **error budget per SLO level**, assuming a 30-day window (≈ 43,200 minutes):

```
  SLO 99.0%   →  432 min / month      →  ~7h 12m  of allowed unavailability
  SLO 99.5%   →  216 min / month      →  3h 36m
  SLO 99.9%   →   43.2 min / month    →  ~43 min  ←  the typical web-SRE target
  SLO 99.95%  →   21.6 min / month
  SLO 99.99%  →    4.32 min / month   →  the typical "platform DB" target
  SLO 99.999% →    0.432 min / month  →  ~26 s    ←  extremely expensive
  SLO 99.9999% →   0.0432 min / month →  ~2.6 s   ←  effectively unattainable
```

A few rules of thumb on SLO selection, from the SRE Workbook:

1. **Start loose, tighten over time.** The opposite — starting tight and loosening — gives users a worse experience than they were promised and signals an undisciplined team.
2. **Don't pick an SLO you cannot measure.** "Correctness of all data pipelines" sounds great until you try to instrument it.
3. **Differentiate internal vs external.** Internal-only SLOs are usually one 9 looser than user-facing ones.
4. **Revisit quarterly.** User expectations and business models change; an SLO that is 18 months old is usually wrong in one direction.
5. **Don't tie performance reviews to SLO attainment.** That creates perverse incentives to under-report incidents.

## SLA: Service Level Agreement

The SLA is the *contractual* version of the SLO, written into a contract with customers, with explicit penalties (typically service credits) when missed. The relationship is:

```
   ┌────────────────────────────┐
   │  SLA   99.5%  ← contractual │   ← written into the contract
   ├────────────────────────────┤       breach → financial penalty
   │  SLO   99.9%  ← internal   │   ← target the team is held to
   ├────────────────────────────┤       miss → process (postmortem, freeze)
   │  SLI   measured           │   ← the actual number
   └────────────────────────────┘
```

The SLO is *tighter* than the SLA on purpose. The gap between the SLA and SLO is the **safety margin** — the room the team has to absorb an incident before customers can claim contractual breach. If your SLA is 99.5% and your SLO is 99.5%, your first incident puts you in contractual breach territory.

A real example (AWS S3 SLA, paraphrased): the SLA promises monthly availability of 99.9% with service credits scaled to the shortfall (10% credit if 99% < monthly uptime < 99.9%, 25% if < 99%, etc.). AWS's *internal* SLO on S3 is famously the "11 nines of durability" — many orders of magnitude tighter than what they promise customers.

## Error Budget

The error budget is the *remaining* allowed unreliability:

```
Error Budget (fraction)  =  1 - SLO
Error Budget (minutes)    =  (1 - SLO) × window_minutes

SLO = 99.9% over 30d  →  Error Budget = 0.001 × 43,200 = 43.2 minutes / month
```

The cultural reframing is the heart of the matter: **the error budget is a resource, not a failure**. SREs and product teams share it. The rules (canonicalized in the SRE Book):

- **Budget positive (or healthy)** → ship features, take risks, do aggressive deploys.
- **Budget depleting (under 1x burn rate, but trending down)** → keep shipping, watch the trend.
- **Budget exhausted** → freeze features; reliability work becomes the team's top priority.
- **Budget overdrawn** → trigger incident response; freeze all non-reliability deploys; postmortem; allocate capacity to paying back the budget over the next window.

This is the mechanism by which SLOs become *policy*, not just *metrics*. Without the error-budget policy, an SLO is a number on a dashboard and engineers can ignore it. With the policy, a "freeze" is the consequence of burning the budget too fast, and product managers have a structural reason to invest in reliability work.

### Burn Rate

The burn rate is the **speed** at which the budget is being consumed, expressed as a multiple of the "sustainable" rate. The sustainable rate is the rate at which, if maintained, exactly consumes the budget over the window.

```
Sustainable error rate  =  1 - SLO             (for SLO 99.9% → 0.1%)
Actual error rate      =  measured bad / total
Burn rate              =  Actual / Sustainable

If SLO = 99.9% and current error rate = 0.5%:
   burn rate = 0.5 / 0.1 = 5x
   → budget exhausted in (window / burn_rate) = 30 / 5 = 6 days
```

A burn rate of 1x means "spending exactly the budget, on track to consume it all by end of window." 5x means "spending 5× faster than sustainable — at this rate the budget is gone in 6 days." The math matters because the *alert you write* is on burn rate, not on absolute error rate — see below.

## Multi-Window, Multi-Burn-Rate Alerting

The biggest practical win in SLO-based alerting is **multi-window, multi-burn-rate alerting**, codified in the Google SRE Workbook (B. Beyer et al., "Alerting on SLOs" chapter) and now the standard implemented by Sloth, the Prometheus Sloth project, and OpenSLO.

The naive SLO alert — "alert if the 30-day SLI drops below the SLO" — is useless: it takes days to fire, by which time the budget is gone. The right alert is on **burn rate over short windows paired with longer windows**. Two windows because:

- A short window (e.g., 1 hour) catches fast-burn incidents early.
- A longer window (e.g., 6 hours) filters out transient noise.

And **both** must fire — the alert is the *conjunction*:

```
ALERT  if   burn_rate_over_1h  >= 14x   (fast burn)
   AND  burn_rate_over_6h  >= 14x   (sustained)

   → page on-call immediately

ALERT  if   burn_rate_over_6h  >= 3x    (slower burn)
   AND  burn_rate_over_1d  >= 3x    (sustained across a day)

   → ticket / slack, no page
```

The canonical thresholds from the SRE Workbook (for a 99.9% / 30-day SLO):

```
┌────────────────────────┬─────────────┬─────────────┬──────────────────┐
│ Action                 │ Short win   │ Long window │ Result           │
├────────────────────────┼─────────────┼─────────────┼──────────────────┤
│ Page (immediate)       │ 1h  @ 14x   │ 5m  @ 14x   │ 2% of budget     │
│                        │             │             │ spent in 1h      │
│ Page (severe)          │ 6h  @ 6x    │ 30m @ 6x    │ 5% in 6h         │
│ Ticket                 │ 3d  @ 1x    │ 6h  @ 1x    │ 10% in 3d        │
│ Ticket (slow burn)     │ 2d  @ 3x    │ 1h  @ 3x    │ 5% in 1d (error  │
│                        │             │             │ rate creeping)   │
└────────────────────────┴─────────────┴─────────────┴──────────────────┘
```

The two-window AND prevents two pathological alerts:

1. **False positives from brief blips.** A 60-second deploy causing a 50% error rate spikes the 1-hour burn to 50× but the 6-hour burn is still ~3× — the AND does not fire the page.
2. **Slow-burn drift going unalerted.** A constant 3× burn over 6 hours is fine on the 1-hour window but alarming on the 6-hour window — the 3-day @ 1x alert catches it as a ticket before the budget is gone.

### Prometheus configuration (Sloth-style)

```yaml
version: "prometheus/v1"
service: "checkout-api"
slos:
  - name: "availability"
    objective: 99.9
    description: "Fraction of non-5xx responses"
    sli:
      events:
        total_query: 'sum(rate(http_requests_total{job="checkout-api"}[{{.window}}]))'
        error_query: 'sum(rate(http_requests_total{job="checkout-api",code=~"5.."}[{{.window}}]))'
    alerting:
      page_alert:
        disable: false
        labels:
          severity: page
      ticket_alert:
        disable: false
        labels:
          severity: ticket
    windows:
      - short: 5m
        long: 1h
        max_burn_rate: 14.0
      - short: 30m
        long: 6h
        max_burn_rate: 6.0
      - short: 2h
        long: 1d
        max_burn_rate: 3.0
      - short: 6h
        long: 3d
        max_burn_rate: 1.0
```

Sloth (the open-source SLO generator for Prometheus) expands this template into ~30 alert rules and recording rules; the actual Prometheus rule file is too long to write by hand, which is why Sloth (or similar: the OpenSLO spec, Nobl9, Pyrra) exists. The pattern above is taken directly from the [Sloth documentation](https://sloth.dev/).

## User-Journey-Based SLOs

The biggest mistake in SLO design is measuring what is easy rather than what matters. A service has dozens of endpoints; an average latency SLI across all of them tells you nothing about what users experience.

The right unit of an SLO is the **user journey**: the end-to-end sequence of requests a user performs to accomplish a task. For a checkout flow:

```
Journey:  "customer completes checkout"
  ↓
  POST /cart/checkout         (must be 2xx, < 800ms)
  POST /payments/charge       (must be 2xx, < 1500ms)
  POST /orders/confirm        (must be 2xx, < 500ms)
  ↓
SLI = good journeys / total journeys attempted
SLO = 99.5% of checkout journeys succeed end-to-end within 2 s budget
```

The journey-based SLO is harder to instrument (you need a correlation ID across the three services), but it has three properties the per-endpoint SLO does not:

1. It **cannot be gamed** by routing slow requests off the SLI's path — a slow `/payments/charge` makes the journey fail, full stop.
2. It **matches user experience** — a customer who clicks "Place Order" and gets an error in any of the three calls has a failed journey, exactly what the SLO measures.
3. It **prioritizes the right reliability work** — improving `/cart/checkout` p99 from 800ms to 500ms does not move the SLO if `/payments/charge` is the bottleneck.

## Comparison to "Uptime Monitoring"

Before SLOs, the standard reliability metric was **uptime**: "the service was reachable." Tools like Pingdom and UptimeRobot still report this. Uptime is conceptually simpler but operationally wrong in three specific ways:

| Property | Uptime monitoring | SLO + error budget |
|---|---|---|
| Definition of "down" | Synthetic probe got a 200 / no response | SLI over a window dropped below SLO |
| Granularity | Binary (up / down), per minute | Continuous (a fraction between 0 and 1) |
| Slow-degradation detection | Misses it (200 OK is still "up") | Catches it (latency SLI degrades) |
| Partial outage detection | Misses it (1% of users 500'ing looks "up") | Catches it (availability SLI degrades) |
| User-perceived reliability | Rough proxy | Directly tied to user journeys |
| Actionability | "It's down — go look" | "Burn rate is 6× — investigate checkout journey" |
| Tie to feature velocity | None (uptime ≠ faster shipping) | Error-budget policy gates deploys |

A common pattern: keep synthetic uptime monitoring for the executive dashboard and the status page, but drive engineering alerting and policy on SLOs + error budgets. They serve different audiences.

## Common Anti-Patterns

- **The "aspirational" SLO.** Picking 99.99% because the CEO wants it, when the team's actual measured SLI is 99.7%. The SLO should be at or slightly above the current SLI; otherwise the team lives in permanent error-budget debt.
- **SLOs with no policy.** A dashboard with no consequence. Without the budget-burn → freeze policy, SLOs are decoration.
- **Averaging percentiles.** "Average p99 across all endpoints" is a meaningless number. Use the journey-based SLI or a per-endpoint SLO set.
- **Alerting on the absolute error rate.** A 0.5% error rate is fine at the start of a 30-day window and catastrophic at day 29. Alert on burn rate, not absolute rate.
- **No "what to do when budget is gone" runbook.** When the budget hits zero, the team has to know what to do — freeze, prioritize reliability work, communicate to PM. Without the runbook, the budget policy has no teeth.

## Interview Questions

**Q1: Define SLI, SLO, SLA, and error budget and how they relate.**
A: An SLI is a *measurement* — the fraction of events that are "good" (e.g., successful requests). An SLO is a *target* for the SLI over a window (e.g., 99.9% over 30 days). An SLA is a *contractual* version of the SLO with penalties (typically service credits) for breach — it is looser than the SLO to leave a safety margin. The error budget is `1 - SLO` expressed in time or fraction (e.g., 99.9% over 30d → 43.2 minutes of allowed unavailability per month). The error budget is a *resource* shared between SRE and product — when positive, ship features; when exhausted, freeze features and do reliability work.

**Q2: Why do we alert on burn rate rather than on the absolute error rate?**
A: Because the absolute error rate is meaningless without time-context: 0.5% errors is fine at the start of the window and catastrophic near the end. Burn rate (actual error rate / sustainable error rate) measures *speed of budget consumption* and is time-invariant — a 5× burn rate means "the budget will be exhausted in window/5 days" regardless of when in the window it occurs. The alerting pattern that uses this is multi-window, multi-burn-rate: a short window catches fast burns early, a longer window filters out transient noise, and the alert fires only when both windows are over the threshold.

**Q3: Walk me through setting up an SLO alert for a checkout API.**
A: First, pick the SLI as a user journey: fraction of checkout journeys (cart → payments → confirm) that succeed end-to-end within a 2-second latency budget. Pick the SLO at or slightly above the current measured SLI — say 99.5% over a 30-day rolling window. Generate alerting rules with Sloth using the multi-window, multi-burn-rate pattern: 1h @ 14x AND 5m @ 14x → page; 6h @ 6x AND 30m @ 6x → page (severe); 3d @ 1x AND 6h @ 1x → ticket. Record the SLI as a Prometheus recording rule so dashboards can show the rolling 30-day value. Tie the SLO to a policy: when budget is below 25%, freeze non-reliability deploys; when below 0, all reliability work becomes top priority until budget is replenished.

**Q4: How do you choose the latency percentile (p50, p99, p99.9) for an SLO?**
A: Pick the percentile that captures the worst user you care about. p99 is the SRE default because it catches the slowest 1% — typically your most engaged users, the ones with the largest carts and highest LTV. p50 (median) hides the long tail entirely. p99.9 is stricter but requires much more traffic to be statistically stable; for a service at 100 RPS, p99.9 is noisy. Never use averages for SLOs — they hide the long tail that is the actual user experience.

**Q5: How is an SLO-based alert different from uptime monitoring?**
A: Uptime monitoring is binary per-minute (up or down) and misses slow degradation and partial outages — a service 500'ing for 1% of users still looks "up" to a synthetic probe. SLOs are continuous (a fraction 0–1) measured over a window, catch slow latency degradation, catch partial outages, and tie directly to user journeys. Uptime monitoring is fine for the public status page; engineering alerting should be SLO-based because it's actionable ("burn rate 6× — investigate checkout journey") instead of vague ("it's down").

## References

- [Google SRE Book — Chapter 4: SLOs (Service Level Objectives)](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Book — Chapter 3: Embracing Risk](https://sre.google/sre-book/embracing-risk/)
- [Google SRE Workbook — Alerting on SLOs (chapter)](https://sre.google/workbook/alerting-on-slos/)
- [Google SRE Workbook — Implementing SLOs (chapter)](https://sre.google/workbook/implementing-slos/)
- [Sloth — Prometheus SLO generator documentation](https://sloth.dev/)
- [OpenSLO — specification](https://github.com/OpenSLO/OpenSLO)
- [Pyrra — SLO-based alerting for Prometheus](https://pyrra.dev/)
- [Prometheus — recording rules and SLO patterns](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/)
- [Nobl9 — SLO platform engineering guide](https://nobl9.com/resources)
