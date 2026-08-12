# Data Quality

Data quality is the discipline of making data trustworthy enough for decisions,
models, APIs, and downstream automation. A pipeline can be available and fast
while still producing incorrect data; quality must therefore be measured as
part of the data product.

## Quality dimensions

| Dimension | Question | Example check |
|---|---|---|
| Completeness | Did expected records and fields arrive? | Row count and null-rate thresholds |
| Validity | Does the value follow the domain rule? | Currency code is in an allow-list |
| Accuracy | Does it represent reality? | Compare to authoritative source |
| Consistency | Do systems agree? | Order total matches line items |
| Uniqueness | Are duplicates absent? | Unique key and idempotency checks |
| Timeliness | Is it fresh enough? | Source watermark within SLO |
| Integrity | Are relationships preserved? | Foreign-key/orphan checks |

## Quality gates in a pipeline

```text
source → ingest contract → quarantine invalid rows → transform → assertions
       → publish trusted dataset → monitor drift and freshness
```

Separate **hard gates** from **soft alerts**. A broken primary key should stop
publication; a small change in a normally variable distribution may alert and
continue while an owner investigates.

## Contract and schema checks

A data contract should state ownership, schema, semantics, allowed values,
retention, freshness, privacy classification, and compatibility rules. Validate
at the boundary where data enters a system rather than discovering all failures
inside a downstream dashboard.

Example SQL checks:

```sql
-- Completeness and validity
SELECT
  COUNT(*) AS rows,
  COUNT(order_id) AS non_null_ids,
  COUNT(*) FILTER (WHERE amount >= 0) AS valid_amounts
FROM orders
WHERE created_at >= CURRENT_DATE;

-- Uniqueness and duplicate detection
SELECT order_id, COUNT(*)
FROM orders
GROUP BY order_id
HAVING COUNT(*) > 1;
```

## Freshness and pipeline monitoring

Track source watermark, ingestion delay, transformation duration, publish time,
row counts, null rates, distribution changes, and rejected/quarantined records.
A freshness alert without a source watermark cannot distinguish an empty source
from a stalled pipeline.

Use a stable baseline and seasonality-aware thresholds. “Exactly 1,000 rows per
hour” is usually worse than a range tied to expected traffic and a separate
anomaly detector.

## Drift and backfills

Data drift can be:

- **Schema drift:** fields added, removed, or changed type.
- **Value drift:** distributions, categories, or null rates change.
- **Concept drift:** the relationship between inputs and outcomes changes.
- **Pipeline drift:** a transformation or dependency changes behavior.

Backfills should be reproducible, isolated from the live path when possible,
versioned by code and input snapshot, and idempotent. Replaying a partition
must not double-count facts or emit duplicate external events.

## Privacy and security

Quality checks must not create a second data leak. Mask or hash sensitive fields
in logs, limit sample payloads, restrict quarantine access, and define retention
for rejected records. A check that copies an entire customer record into an
unprotected error table is a security regression.

## Interview questions

**How do you stop bad data from reaching a dashboard?**

Define an owner and contract, validate at ingestion, quarantine invalid records,
apply hard publication gates for invariant failures, monitor freshness and
quality metrics, and make the dashboard show data freshness and quality state.

**How do you handle a late-arriving event?**

Use event time and watermarks, allow a bounded lateness window, update affected
aggregates or issue corrections, and make the processing idempotent.

**What is the difference between data validation and data quality?**

Validation checks a record or batch against explicit rules. Quality includes
validity plus completeness, accuracy, timeliness, consistency, ownership,
observability, and recovery processes.

## Cross-references

- [Data Engineering Fundamentals](./fundamentals.md)
- [Batch Processing](./batch-processing.md)
- [Stream Processing](./stream-processing.md)
- [CDC and Transactional Outbox](../backend/patterns/cdc-outbox.md)
- [Testing and test strategy](../testing/test-strategy.md)
- [OpenTelemetry](../backend/observability/opentelemetry.md)

## References

- [Great Expectations documentation](https://docs.greatexpectations.io/)
- [dbt data tests](https://docs.getdbt.com/docs/build/data-tests)
- [Apache Deequ](https://github.com/awslabs/deequ)
- [OpenLineage](https://openlineage.io/docs/)
- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)
