# Workload Forecasting for Capacity and Autoscaling

[Capacity planning](./capacity-planning.md) tells you what to do with a number:
apply headroom, respect lead times, buy commitments. This page produces the
number itself, for two decisions with incompatible clocks: "how many instances
do we reserve next quarter" and "what should `minReplicas` be tomorrow morning".
It feeds capacity planning, predictive autoscaling, and [FinOps](./finops-cloud-cost.md) coverage.

## Two clocks: procurement time and reaction time

A model validated for one loop is unvalidated for the other - mixing the two is
the most common interview failure.

| Decision | Horizon | Cost of a miss | Tolerated error | Typical method |
|----------|---------|----------------|-----------------|----------------|
| Node groups, reserved capacity, shard counts | weeks to months | lead time cannot be compressed: outage or stranded spend | low single-digit MAPE on peaks | Holt-Winters, Prophet, trend+profile |
| HPA `minReplicas` / `maxReplicas`, pre-warming | hours to a day | brief overload, absorbed by the reactive loop | 10-20% on peaks | same models, short horizon, refit often |
| React to load right now | seconds | sustained SLO breach | no forecast allowed | live metrics only (HPA, KEDA) |

```text
  traffic history ---> forecast model (weekly refit) ---> peaks, weeks out
  live load     ---> reactive autoscaler (HPA/KEDA) ----> replicas, seconds
  forecast sets min/max bounds and purchases; reactions fill the gap
```

A stale model then costs slack, not an outage - keep that property.

## Decompose the signal before modeling it

```text
observed  __/\__/\__/\__/\__/\__     daily teeth riding on a weekly box
trend     _____________/             slow compounding ramp (growth)
weekly    [][X][X][][]               weekend dips, weekday plateaus
daily     _/\/\/\/\/\/\/\/\/\_       24h wave, peak around 14:00
residual  ~~~~~~~~~~~~~~~~~~~~       noise, launches, incidents
```

- **Trend** belongs to the business (growth, launches, churn); procurement rides
  on it. **Weekly and daily seasonality** belong to users - stable enough to
  schedule against, which is what predictive autoscaling does. **Residuals**
  belong to SREs: incidents and deploys live there.

Two choices follow. Fit **one seasonal cycle of `m = 168` hours** (a full week)
instead of nested daily and weekly cycles: one 168-state cycle captures both
patterns with no multi-seasonal machinery. And pick **additive vs
multiplicative**: if the daily swing grows with the level, fit on `log(y)` and
exponentiate back - the tell is residuals fanning out at peak.

## Holt-Winters in three equations

Triple exponential smoothing keeps running estimates of level, trend, and `m`
seasonal states, updated by discounting the newest observation against the old
estimate. Additive form:

```text
level:    l(t) = a * (y(t) - s(t-m)) + (1-a) * (l(t-1) + b(t-1))
trend:    b(t) = c * (l(t) - l(t-1)) + (1-c) * b(t-1)
season:   s(t) = g * (y(t) - l(t-1) - b(t-1)) + (1-g) * s(t-m)
forecast: y(T+h) = l(T) + h * b(T) + s(T+h-m)      for T = last observation
```

- `a` (level) is reaction speed: high tracks launches fast but passes incidents
  into the forecast; low smooths them away.
- `c` (trend) stays tiny - the forecast extrapolates `h * b(T)` up to 168 steps,
  so a noisy trend estimate swings the whole horizon; `g` (season) is small when
  weekly patterns are stable. Initialize with two full cycles: level from cycle
  one's mean, trend from its mean-to-mean slope.

Fit by minimizing one-step-ahead error on a grid, or via the ETS state-space
likelihood (statsmodels `ExponentialSmoothing`, reference below;
[Prophet](https://facebook.github.io/prophet/), repo page
[../ml/time-series/prophet.md](../ml/time-series/prophet.md), is the
decomposable-regression alternative). Canonical text: Hyndman & Athanasopoulos,
[FPP3 ch. 8](https://otexts.com/fpp3/expsmooth.html).

## Forecast a quantile, not the mean

Sizing on the mean forecast guarantees peak breaches: half of all peak hours
land above it. Two fixes, in increasing sophistication:

1. **Point forecast + residual quantile.** Take the empirical p95 of one-step
   residuals and add it before sizing. Prices in observation noise, not model
   bias - which is why signed error is tracked separately.
2. **Model the quantile series directly.** If the constraint is really p95
   latency or per-minute peak load, forecast *that* series (hourly p95 of
   per-minute rates); its seasonal shape is sharper than the mean's. Quantile
   regression (pinball loss) generalizes this.

Then put [capacity-planning](./capacity-planning.md) headroom and redundancy
rules *on top* of the quantile: forecast error and zone loss get separate margins.

## Error metrics and how they lie

| Metric | Definition | How it lies | Use it when |
|--------|-----------|-------------|-------------|
| MAPE | mean of abs(err) / actual | divides by the actual: near-zero troughs explode it, and overshooting a small actual costs far more than undershooting it (Hyndman & Koehler 2006) | traffic never approaches zero; you need one percentage to broadcast |
| MAE | mean absolute error, in req/h | not scale-free: 50k req/h is noise at 3M, fatal at 80k | comparing models on the same series |
| wMAPE | sum(abs(err)) / sum(actual) | hides per-trough blowups inside the volume-weighted total | default for 24/7 series with deep night troughs |
| signed bias | mean of err | says nothing about scatter | catching systematic under-forecast, the capacity killer |

Evaluate on rolling holdouts (backtesting), never in-sample: a fit reported
against its own training window flatters you by exactly what you cannot afford.

## Drift and retraining cadence

- **Refit weekly** on a trailing 8-12 week window - two full seasonal cycles per
  parameter regime, short enough to track a changed growth rate - and on
  changepoints (a launch moved the level, a campaign changed the weekly shape).
- **Alert on forecast error itself.** A rolling wMAPE SLO on the model is a
  production SLI; persistently negative bias means growth outran the trend
  estimate - exactly when procurement needs the most warning.
- **Holidays are regime changes**, not noise: regressors (Prophet's `holidays`)
  or exclusion, or they corrupt 168 seasonal states for months. Version refits
  like config changes - deploys shift the demand curve too.

## Linear projection vs Holt-Winters

Why not fit a line and add a weekly profile? On the demo data below:

| Method | Trend handling | Seasonality | Free parameters | Holdout MAPE | Fails when |
|--------|---------------|-------------|-----------------|--------------|------------|
| Seasonal naive | none, copies last cycle | exact copy of last week | 0 | 3.81% | any growth: misses the trend by a full cycle |
| Linear trend + weekly profile | one global least-squares line | fixed per-slot residual means | 2 + m | 2.35% | compounding or bending trend; the line is an average of a moving target |
| Additive Holt-Winters | discounted local line, re-estimated every step | 168 states, continuously updated | a, c, g + m | 1.82% | abrupt level shifts between refits; events with no regressors |

Linear projection is not a strawman - it wins on stable, straight-line growth.
Holt-Winters wins wherever the trend compounds or the level moves.

## A runnable week-ahead forecast

Pure-stdlib demo: 8 weeks of synthetic hourly traffic (compounding trend, daily
wave, weekend dip, noise), additive HW with `m = 168` grid-fitted on one-step
SSE, 168-hour forecast, fleet sized at 65% utilization.

```python
import math, random

M = 24 * 7          # seasonal cycle: 168 hourly slots (daily + weekly shape)
TRAIN = 7 * M       # fit on weeks 1-7; week 8 (168 h) is the holdout
INST_RPS, UTIL = 150.0, 0.65   # per-instance capacity, sizing utilization

rng = random.Random(48)
y = [2_000_000 * (1.0002 ** t)                              # compounding trend
     + 620_000 * math.cos(2 * math.pi * (t % 24 - 14) / 24)  # daily wave
     + (-420_000 if (t // 24) % 7 >= 5 else 0)               # weekend dip
     + rng.gauss(0, 45_000)                                  # noise
     for t in range(8 * M)]

def hw_fit(y, m, a, b, g):
    c1, c2 = sum(y[:m]) / m, sum(y[m:2 * m]) / m
    l, tr = c1, (c2 - c1) / m
    seas = [y[i] - c1 for i in range(m)]
    res = []
    for t in range(m, len(y)):
        idx = t % m
        res.append(y[t] - (l + tr + seas[idx]))     # one-step-ahead error
        l2 = a * (y[t] - seas[idx]) + (1 - a) * (l + tr)
        tr2 = b * (l2 - l) + (1 - b) * tr
        seas[idx] = g * (y[t] - l - tr) + (1 - g) * seas[idx]
        l, tr = l2, tr2
    return l, tr, seas, res

def hw_fc(l, tr, seas, m, n, h):
    return [l + k * tr + seas[(n + k - 1) % m] for k in range(1, h + 1)]

def mape(act, fc):
    return 100 * sum(abs(v - f) / v for v, f in zip(act, fc)) / len(act)

best = min((sum(r * r for r in hw_fit(y[:TRAIN], M, a, b, g)[3]), a, b, g)
           for a in (0.05, 0.1, 0.2, 0.4) for b in (0.0, 0.01, 0.05)
           for g in (0.05, 0.2, 0.5))
l, tr, seas, res = hw_fit(y[:TRAIN], M, best[1], best[2], best[3])
fc, act = hw_fc(l, tr, seas, M, TRAIN, M), y[TRAIN:]

# baseline: least-squares linear trend + mean weekly residual profile
xs = range(TRAIN); sx, sxx = sum(xs), sum(x * x for x in xs)
sy, sxy = sum(y[:TRAIN]), sum(x * v for x, v in zip(xs, y[:TRAIN]))
sl = (TRAIN * sxy - sx * sy) / (TRAIN * sxx - sx * sx)
ic = (sy - sl * sx) / TRAIN
prof, cnt = [0.0] * M, [0] * M
for t in range(TRAIN):
    prof[t % M] += y[t] - (ic + sl * t); cnt[t % M] += 1
lin = [ic + sl * (TRAIN + k) + prof[(TRAIN + k) % M] / cnt[(TRAIN + k) % M]
       for k in range(M)]

res.sort()
q95 = res[int(0.95 * len(res))]                     # one-step residual, req/h
pk_fc, pk_act = max(fc), max(act)
rps, per = pk_fc / 3600, INST_RPS * UTIL

print(f"train: {TRAIN} obs (7 weekly cycles), m={M}, holdout: 168 obs")
print(f"best HW params (grid on one-step SSE): alpha={best[1]} beta={best[2]} gamma={best[3]}")
print(f"holdout MAPE:  HW {mape(act, fc):.2f}%  | linear+profile {mape(act, lin):.2f}%  | seasonal-naive {mape(act, y[TRAIN - M:TRAIN]):.2f}%")
print(f"holdout wMAPE: HW {100 * sum(abs(v - f) for v, f in zip(act, fc)) / sum(act):.2f}%")
print(f"peak hour: forecast {pk_fc:,.0f} req/h vs actual {pk_act:,.0f} req/h ({100 * (pk_fc - pk_act) / pk_act:+.2f}%)")
print(f"q95 one-step residual: {q95:+,.0f} req/h ({q95 / 3600:+.0f} rps)")
print(f"sizing: peak {rps:,.0f} rps / ({INST_RPS:.0f} rps x 65% util) = {math.ceil(rps / per)} instances; with q95 buffer {math.ceil((rps + q95 / 3600) / per)}")
```

Output (this exact code, Python 3.11, deterministic via `random.Random(48)`):

```text
train: 1176 obs (7 weekly cycles), m=168, holdout: 168 obs
best HW params (grid on one-step SSE): alpha=0.05 beta=0.0 gamma=0.2
holdout MAPE:  HW 1.82%  | linear+profile 2.35%  | seasonal-naive 3.81%
holdout wMAPE: HW 1.76%
peak hour: forecast 3,197,115 req/h vs actual 3,233,264 req/h (-1.12%)
q95 one-step residual: +91,902 req/h (+26 rps)
sizing: peak 888 rps / (150 rps x 65% util) = 10 instances; with q95 buffer 10
```

Read the numbers like an SRE: 1.82% MAPE is not 1.82% at the peak - the
peak-hour miss is -1.12% and structural, because an additive model extrapolates
a straight line while the true trend compounds (expect under-forecast bias on
growing systems; that is what the utilization margin is for). The q95 buffer
did not cross an instance boundary but buys margin (59% vs 61% peak utilization
of the 10-instance pool) - check the margin, not just the ceiling function.

## Forecasts set bounds, reactions close the gap

Every production predictive-scaling design keeps the reactive loop sovereign:

- **AWS predictive scaling** forecasts load and creates scheduled scaling
  actions ahead of the curve, paired with dynamic scaling for anything the
  forecast missed ([AWS docs](https://docs.aws.amazon.com/autoscaling/ec2/userguide/predictive-scaling.html)).
- **Kubernetes HPA** keeps its live-metric replica arithmetic (covered in
  [Autoscaling](../cloud/autoscaling.md); nothing about it changes here). The
  forecast contributes `minReplicas` (pre-warmed floor for the predicted peak)
  and `maxReplicas`; KEDA cron scales are the poor-man's version of the idea.
- **Scale-up stays fast, scale-down stays stabilized**: a wrong forecast wastes
  money in one direction and must stay recoverable in the other.
- **Burn rates are the reactive counterpart.** The multi-window burn-rate alerts
  in [SLOs and error budgets](./slo-error-budget.md) fire on *realized* errors -
  they tell you the budget is dying while it dies. Load forecasting is the
  preventive sibling: you forecast the demand that would have started a burn,
  and a predicted peak above tested capacity becomes a budget-policy
  conversation before the event, not a page during it.
- **Commitments follow the forecast too.** [FinOps](./finops-cloud-cost.md)
  converts the baseline component (trend + weekly floor) into reserved
  coverage: over-forecast strands commitments, under-forecast pays on-demand
  rates at peak. Match refit cadence to commitment cadence.

## Interview-grade checks

**Q: We have autoscaling that reacts in seconds. Why forecast at all?**
A: The reactive loop cannot cover: (1) lead-time-bound resources (node groups,
shards, database connections, commitments) with weeks of response time;
(2) cold-start economics - a reactive scale-up arrives too late for the spike
and thrashes min/max bounds; (3) stateful tiers that cannot scale out. The
forecast sets floors, ceilings, and purchases; HPA fills the gap in seconds.

**Q: Your week-ahead MAPE was 2%, yet you tipped over at peak. What happened?**
A: Walk the failure ladder: (1) weekly MAPE says nothing about the peak hour -
the demo's peak error (-1.12%) is worse than its average; (2) sized the mean
instead of a quantile, so half the peaks breach by construction; (3) regime
change outside the training window; (4) summed per-service forecasts instead of
the joint peak (correlated diurnal peaks add); (5) no zone-loss margin at the
utilization target.

## References

1. Google SRE Workbook, "Managing Load" - <https://sre.google/workbook/managing-load/> (probed: HTTP 200)
2. Google SRE Book, "Handling Overload" - <https://sre.google/sre-book/handling-overload/> (probed: HTTP 200). Note: neither book has a chapter titled "Capacity Planning"; the often-circulated URL `sre.google/sre-book/forward-facing-capacity-planning/` returns 404 (verified Aug 2026) - the two chapters above are the real on-topic sources, and `sre/capacity-planning.md` in this repo cites the dead URL.
3. Hyndman & Athanasopoulos, *Forecasting: Principles and Practice*, 3rd ed., ch. 8 "Exponential smoothing" - <https://otexts.com/fpp3/expsmooth.html> (site serves a bot challenge to curl; path verified by search: "Chapter 8 Exponential smoothing")
4. statsmodels `ExponentialSmoothing` (Holt-Winters) API docs - <https://www.statsmodels.org/stable/generated/statsmodels.tsa.holtwinters.ExponentialSmoothing.html> (probed: HTTP 200)
5. Prophet documentation - <https://facebook.github.io/prophet/> (probed: HTTP 200)
6. Kubernetes HPA task docs - <https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/> (probed: HTTP 200)
7. AWS EC2 Auto Scaling, "Predictive scaling" - <https://docs.aws.amazon.com/autoscaling/ec2/userguide/predictive-scaling.html> (probed: HTTP 200)
