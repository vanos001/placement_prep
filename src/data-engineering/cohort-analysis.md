# Cohort Analysis

Cohort analysis groups users by a shared characteristic (sign-up date, first purchase, acquisition channel) and tracks their behavior over time. It is the primary tool for measuring **retention**, **churn**, and the effectiveness of product changes.

## Types of Cohorts

| Cohort Type | Grouping Criteria | Example Question |
|---|---|---|
| **Time-based** | Signup/purchase date | "Do users who joined in January retain better than February?" |
| **Behavioral** | Action taken (feature used, plan chosen) | "Do users who use search in week 1 have higher LTV?" |
| **Acquisition** | Marketing channel, campaign | "Which channel brings users with the best 30-day retention?" |
| **Size-based** | Company size, revenue tier | "Do enterprise accounts churn less than SMBs?" |

## Retention Table

A retention table is the canonical output — rows are cohorts, columns are time periods, values are percentages:

```
Cohort      Wk0   Wk1   Wk2   Wk3   Wk4   Wk5
Jan 01     100%  62%   48%   41%   37%   34%
Jan 08     100%  58%   45%   39%   35%   -
Jan 15     100%  65%   51%   43%   -     -
Jan 22     100%  60%   47%   -     -     -
Jan 29     100%  63%   -     -     -     -
```

## SQL Implementation

```sql
WITH cohorts AS (
    -- Define cohort: first activity date per user
    SELECT user_id,
           DATE_TRUNC('week', MIN(event_date)) AS cohort_week
    FROM events
    GROUP BY user_id
),
activity AS (
    -- Count active users per cohort per week
    SELECT c.cohort_week,
           DATE_TRUNC('week', e.event_date) AS activity_week,
           COUNT(DISTINCT c.user_id) AS active_users
    FROM cohorts c
    JOIN events e ON c.user_id = e.user_id
    GROUP BY 1, 2
),
cohort_sizes AS (
    SELECT cohort_week, COUNT(DISTINCT user_id) AS cohort_size
    FROM cohorts
    GROUP BY cohort_week
)
SELECT a.cohort_week,
       a.activity_week,
       a.active_users,
       cs.cohort_size,
       ROUND(100.0 * a.active_users / cs.cohort_size, 1) AS retention_pct
FROM activity a
JOIN cohort_sizes cs ON a.cohort_week = cs.cohort_week
ORDER BY a.cohort_week, a.activity_week;
```

## Churn Analysis

Churn is the inverse of retention. Common definitions:

| Metric | Definition | Typical Use |
|---|---|---|
| **Daily/Weekly/Monthly churn** | % of cohort inactive in period | Short-term product health |
| **Logo churn** | % of accounts lost | B2B SaaS |
| **Revenue churn** | % of MRR lost (more nuanced than logo churn) | Finance |
| **Net revenue retention** | (starting MRR + expansion - contraction - churn) / starting MRR | Growth indicator |

```sql
-- Monthly churn rate by cohort
SELECT cohort_month,
       COUNT(DISTINCT user_id) AS total_users,
       COUNT(DISTINCT CASE WHEN last_activity < last_day_of_month
                           THEN user_id END) AS churned_users,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN last_activity < last_day_of_month
                                         THEN user_id END)
            / COUNT(DISTINCT user_id), 1) AS churn_rate
FROM (
    SELECT user_id,
           DATE_TRUNC('month', MIN(event_date)) AS cohort_month,
           MAX(event_date) AS last_activity,
           LAST_DAY(DATE_TRUNC('month', MAX(event_date))) AS last_day_of_month
    FROM events
    GROUP BY user_id
) t
GROUP BY cohort_month;
```

## Key Metrics Derived from Cohorts

- **Retention curve shape** — flattening curve indicates a stable core user base
- **D1/D7/D30 retention** — standard benchmarks for consumer apps (good D7 is often 20-40%)
- **Time to value** — cohort with fastest activation often has highest long-term retention
- **Cohort payback period** — how many months until CAC is recovered from that cohort's revenue

## Interview Questions

**Q1: What is cohort analysis and how is it different from a simple retention metric?**
A: Cohort analysis groups users by a shared characteristic and tracks their behavior over time. A simple overall retention metric (e.g., "70% monthly retention") masks trends — cohorts reveal whether retention is improving or declining over time. A product change in February might only affect the Feb cohort, which cohort analysis surfaces.

**Q2: How would you design a cohort analysis to evaluate a new onboarding flow?**
A: Create two cohorts: users who went through the old onboarding (pre-launch date) and new onboarding (post-launch). Track D1, D7, D14, and D30 retention for both. Compare retention curves — if the new cohort retains significantly better, the onboarding change is effective. Ensure other variables (acquisition channel, seasonality) are controlled.

**Q3: What is the difference between logo churn and revenue churn?**
A: Logo churn counts the percentage of accounts lost. Revenue churn measures the percentage of recurring revenue lost. A company could lose 10 small accounts (high logo churn) but only 2% of revenue (low revenue churn). Net revenue retention accounts for expansion revenue from existing accounts — above 100% means growing revenue even with some churn.

**Q4: How do you handle users who have multiple sessions in a retention calculation?**
A: Retention is binary per user per period — a user is either active (at least one event) or churned. The SQL uses `COUNT(DISTINCT user_id)` to ensure each user is counted once. Whether to count a user as active if they have zero events but have a subscription active depends on the product definition.

## Cross-References

- [Data Quality](data-quality.md) — Ensuring event data is complete for accurate cohorts
- [Data Lineage](data-lineage.md) — Tracing metric definitions back to source events
- [Batch Processing](batch-processing.md) — Scheduling cohort computation jobs
- [Slowly Changing Dimensions](slowly-changing-dimensions.md) — Modeling user dimension history

## References

- [Cohort Analysis — Mixpanel](https://mixpanel.com/blog/what-is-cohort-analysis/)
- [SQL for Cohort Analysis — Mode Analytics](https://mode.com/sql-tutorial/sql-cohort-analysis)
- [Reforge: Retention and Engagement](https://www.reforge.com/)
