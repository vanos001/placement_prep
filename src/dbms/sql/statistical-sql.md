# Statistical SQL: Percentiles, Ranking, and Correlation in Queries

Analytics questions are statistical questions wearing SQL syntax: what is
p95 latency, how do deployments rank against history, do two metrics move
together, is this value anomalous for a Tuesday. SQL's answer is a family
of ordered-set aggregates and statistical window functions that most
engineers never learn — and reimplement badly in application code. This
page covers the percentile family (and the continuous/discrete distinction
that produces off-by-one medians), the statistical ranking functions
(`PERCENT_RANK`, `CUME_DIST`), windowed statistics (`STDDEV`, `VAR`,
z-scores), and correlation/regression in pure SQL.

The memory-bounded algorithms behind approximate percentiles (t-digest,
KLL) and cardinality are in [Sketch Algorithms](../advanced/sketch-algorithms.md);
this page is the *exact* computation layer.

## Percentiles: PERCENTILE_CONT vs PERCENTILE_DISC

The two percentile functions differ in one word and one whole semantic:

```sql
-- CONTinuous: interpolates between rows; the result may not be any row
SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50
FROM requests;

-- DISCrete: returns an actual stored value (the first value at/above CDF)
SELECT percentile_disc(0.5) WITHIN GROUP (ORDER BY latency_ms) AS p50_med
FROM requests;
```

Over latencies `(10, 20, 1000)`:

- `PERCENTILE_CONT(0.5)` → 20 (the middle by interpolation) — the honest
  "median latency."
- `PERCENTILE_DISC(0.5)` → 20 here, but over `(10, 20, 21, 1000)` it
  returns 21 while CONT returns 20.5.

The interview-grade points:

- **`WITHIN GROUP` is required syntax** — these are *ordered-set
  aggregates*; the ORDER BY is part of the function, not the query. A
  percentile without a defined order is a syntax error, which is the
  standard's way of saying percentiles are not order-independent like
  `SUM`.
- **For even counts, CONT interpolates; DISC picks.** Dashboards mixing
  the two across panels show "the median changed" when only the function
  changed. Pick one per metric, forever.
- **Extreme quantiles and small groups don't mix.** p99.9 within a
  100-row group is interpolation between two specific samples — every
  regression test hiding in the tail shows up. Report the group size next
  to the percentile (`count(*)`) so readers can calibrate.
- **Multiple percentiles in one pass** (PostgreSQL):
  `percentile_cont(ARRAY[0.5, 0.95, 0.99]) WITHIN GROUP (...)` — one sort,
  all quantiles; crucial for per-group SLA panels that would otherwise
  sort the group three times.

As window functions, the percentile family answers "what is this row's
latency relative to its group" without collapsing rows:

```sql
SELECT service, endpoint, latency_ms,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)
         OVER (PARTITION BY service)                    AS svc_p95,
       percent_rank() OVER (PARTITION BY service ORDER BY latency_ms) AS pct_rank,
       cume_dist()    OVER (PARTITION BY service ORDER BY latency_ms) AS cume
FROM requests;
```

## PERCENT_RANK vs CUME_DIST: relative position, two definitions

Both map a row to (0, 1] within its partition; they disagree exactly at
ties, and the disagreement is the definition:

- **`PERCENT_RANK()`** = `(rank − 1) / (rows − 1)` — "how many rows are
  strictly worse than this one, as a fraction of the others." The lowest
  row is always 0. Ties share the *minimum* rank, so all tied rows get the
  same, lower value.
- **`CUME_DIST()`** = `rows ≤ this value / total rows` — "what fraction of
  the distribution is at or below me." Ties share the *maximum* cumulative
  position, so all tied rows get the same, higher value.

For grading/leaderboards where ties should not penalize, `CUME_DIST`;
for "beat N% of peers" semantics, `PERCENT_RANK`. `NTILE(n)` belongs to
the same family but partitions rows into *buckets by count* — deciles for
histogram binning, not a statistical measure (bucket membership shifts
with row count, a subtlety that bites fixed-threshold consumers).

## Windowed statistics: variance, z-scores, and anomaly flags

The statistical aggregates work as window functions, which turns
deviation-from-history into a single query:

```sql
-- Is today's failure rate anomalous vs the trailing 28 days?
WITH daily AS (
  SELECT day,
         failures::numeric / NULLIF(attempts, 0) AS rate
  FROM service_daily
),
stats AS (
  SELECT day, rate,
         avg(rate) OVER w28                       AS mean,
         stddev_samp(rate) OVER w28               AS sd
  FROM daily
  WINDOW w28 AS (
    ORDER BY day
    ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING     -- exclude today
  )
)
SELECT day, rate, mean, sd,
       (rate - mean) / NULLIF(sd, 0) AS z,
       abs((rate - mean) / NULLIF(sd, 0)) > 3 AS is_anomaly
FROM stats;
```

Details that decide whether this is statistics or astrology:

- **The frame excludes the current row** (`28 PRECEDING AND 1 PRECEDING`)
  — including today in its own baseline hides exactly the anomalies you
  are hunting (the same self-inclusion bug as the
  [default-frame trap](../interview-problems/interview-traps.md), now
  affecting a baseline).
- **`stddev_samp` vs `stddev_pop`**: sample (n−1) for a window of
  *observations* of an ongoing process; population (n) when the window is
  genuinely the whole population. With n = 1 the sample version is NULL —
  the first day of any series has no z-score, by definition.
- **Rates need `NULLIF` guards** on both denominators (zero attempts, zero
  variance) — division-by-zero NULLs that silently remove the most
  interesting days from the report.
- **Non-stationary baselines**: z-scores against a 28-day window treat the
  mean as stable; for trending metrics use *differenced* rates (today vs
  yesterday's window mean) or detrend first — otherwise every growth
  curve is a permanent "anomaly."

## Correlation and regression: moving together, in SQL

```sql
-- Do cache hit rate and p99 move together, per service, per week?
SELECT service,
       date_trunc('week', day) AS week,
       corr(hit_rate, p99_ms)              AS pearson_r,
       regr_slope(p99_ms, hit_rate)        AS slope,
       regr_intercept(p99_ms, hit_rate)    AS intercept,
       regr_r2(p99_ms, hit_rate)           AS r2,
       corr(hit_rate, p99_ms) * corr(hit_rate, p99_ms) AS r_squared_eq,
       count(*)                            AS n
FROM service_daily
GROUP BY service, 2
HAVING count(*) >= 8;          -- correlation on 3 points is noise
```

The engineering interpretations:

- **`corr`** is Pearson's r ∈ [−1, 1]; its square equals `regr_r2` —
  reporting both is a cheap consistency check on the query itself.
- **`regr_slope/intercept`** are simple linear regression coefficients —
  usable for quick capacity models (e.g., "each +1% hit rate ≈ −6 ms
  p99"), with the standing warning that slope on *aggregated* buckets
  (weekly means) suffers aggregation bias versus row-level regression
  (Simpson's paradox lives here).
- **The `HAVING count(*) >= 8` guard** is the most-forgotten line in
  ad-hoc analytics: correlations computed over tiny groups look
  spectacular and mean nothing.
- **Correlation ≠ attribution**: both variables may be driven by a third
  (traffic volume). The regression vocabulary is there to *quantify*
  relationships, not to certify causation — worth one sentence in any
  interview answer that uses the word "because."

## Where exact ends: scale and approximations

Exact percentiles require the values (or a sort). At the point where the
sort dominates (per-group p99 over billions of events), the
[sketch family](../advanced/sketch-algorithms.md) — t-digest, KLL —
estimates quantiles with bounded error and mergeable state, which is what
monitoring systems (Prometheus histograms, Datadog, OpenTelemetry's
`Histogram`/`ExponentialHistogram`) run instead of exact SQL. The
decision rule: **interactive, per-group, sliceable → sketches or
pre-aggregated histograms; one-shot analytical → exact
`percentile_cont`.** Mixing the two in one dashboard without labeling
which panel is which produces the classic "p95 differs between the
overview and the drill-down" incident.

## Interview questions

1. **Median of an even-sized set — `percentile_cont` or `_disc`?** They
   differ by construction: CONT interpolates (20.5), DISC returns a real
   value (21). The question behind the question: consistency — pick one
   definition per metric across all reporting.
2. **Why does `WITHIN GROUP` exist?** Ordered-set aggregates need a sort
   key that belongs to the function, not the query; `SUM` is
   order-independent, percentiles are not. Knowing this reframes
   percentiles as "sorted aggregation" rather than "a special MAX."
3. **Flag anomalies against a trailing window — what frame and why?**
   `ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING` (self-excluded), sample
   stddev, NULL-guarded z; then mention non-stationarity (differencing or
   seasonal baselines) as the next-order correction.
4. **`corr(hit_rate, p99)` = −0.8 per service, but pooled across services
   it's +0.3. What happened?** Aggregation/Simpson's paradox: the pooled
   correlation is dominated by between-service variation (high-traffic
   services have both lower hit rates and higher p99), inverting the
   within-service relationship. Always state the unit of analysis.

## Key Takeaways

- `PERCENTILE_CONT` interpolates, `_DISC` returns stored values; `WITHIN
  GROUP` marks ordered-set aggregates; multi-quantile arrays make one sort
  serve a whole SLA panel.
- `PERCENT_RANK` (strictly-worse fraction) and `CUME_DIST` (at-or-below
  fraction) differ at ties by definition — pick per semantics, not by
  habit.
- Windowed `avg`/`stddev_samp` with a self-excluding frame turn anomaly
  detection into one query; guard denominators and remember non-stationary
  baselines.
- `corr`/`regr_*` quantify relationships inside SQL — with the standing
  caveats: minimum sample sizes, aggregation bias, and correlation's
  non-causal nature.

## Cross-References

- [Sketch Algorithms](../advanced/sketch-algorithms.md) — approximate quantiles and cardinality at scale.
- [Window Functions](./window-functions.md) — frame semantics powering the statistical windows.
- [Gaps and Islands](./gaps-and-islands.md) — sessionization feeding per-session statistics.
- [Funnel Analysis](./funnel-analysis.md) — the conversion side of event analytics.
- [Cohort Analysis](../../data-engineering/cohort-analysis.md) — retention as a statistical table.
- [Queueing Theory Fundamentals](../../queueing-theory/fundamentals.md) — the latency-distribution theory behind percentiles.

## References

- PostgreSQL Documentation, "[Statistical Aggregate Functions](https://www.postgresql.org/docs/current/functions-aggregate.html)" and "[Window Functions](https://www.postgresql.org/docs/current/functions-window.html)" — percentile_cont/disc, corr/regr_* family, and ordered-set aggregate syntax.
- Microsoft Learn, "[PERCENT_RANK (Transact-SQL)](https://learn.microsoft.com/en-us/sql/t-sql/functions/percent-rank-transact-sql)" — ranking semantics with tie behavior.
- S. Robertson, H. Zaragoza, "[The Probabilistic Relevance Framework: BM25 and Beyond](https://doi.org/10.1561/1500000019)" — background on rank-based statistics when SQL hands off to a search engine (see [Full-Text Search in SQL](./full-text-search.md)).
- Z. Karnin, K. Lang, E. Liberty, "[Optimal Quantile Approximation in Streams](https://arxiv.org/abs/1603.05346)", *FOCS 2016* — the KLL sketch behind the approximate-quantile alternative.
