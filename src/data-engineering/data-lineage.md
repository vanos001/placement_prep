# Data Lineage

Data lineage tracks the **flow of data** from its origin through transformations to its final consumption. It answers: "Where did this metric come from? What transformations were applied? Who depends on this table?" — essential for compliance, debugging, and impact analysis.

## Types of Data Lineage

| Type | Granularity | Use Case |
|---|---|---|
| **Table-level** | Source → target table mapping | Impact analysis, dependency graphs |
| **Column-level** | Which source columns produce which target columns | Root cause analysis, compliance |
| **Row-level** | Which source rows produced which output rows | Audit trails, GDPR data subject requests |

Table-level is the most common and practical. Column-level adds precision for compliance. Row-level is expensive and used only when legally required.

## Lineage in Practice

```python
# Example: column-level lineage for a derived field
# source: orders.raw_amount, orders.currency, exchange_rates.usd_rate
# transform: raw_amount * usd_rate AS amount_usd
# target: fact_orders.amount_usd

# Lineage graph (simplified):
# orders.raw_amount ──┐
#                     ├─► fact_orders.amount_usd
# exchange_rates.rate ─┘
```

## Tools

| Tool | Type | Integration | Strengths |
|---|---|---|---|
| **Apache Atlas** | Metadata platform | Hadoop, Hive, Spark | Mature, Apache ecosystem |
| **OpenLineage** | Open standard | Spark, Airflow, dbt | Vendor-neutral, event-based |
| **dbt Lineage** | SQL transform lineage | dbt projects | Automatic from SQL parsing |
| **DataHub (LinkedIn)** | Data catalog | Multi-source | Modern UI, GraphQL API |
| **Marquez** | Open metadata | OpenLineage native | Lightweight, focused on lineage |

### OpenLineage

OpenLineage defines a standard event format for emitting lineage metadata from data processing jobs:

```json
{
  "eventType": "RUN_COMPLETE",
  "job": { "name": "transform_orders", "namespace": "production" },
  "inputs": [
    { "name": "raw_orders", "namespace": "warehouse" }
  ],
  "outputs": [
    { "name": "fact_orders", "namespace": "warehouse" }
  ]
}
```

## Use Cases

- **Impact analysis** — before dropping or modifying a column, trace all downstream consumers
- **Root cause analysis** — when a metric is wrong, trace upstream to find the bad transformation
- **Compliance** — GDPR/CCPA require knowing which systems hold personal data and how it flows
- **Data quality** — propagate quality scores along lineage to trust downstream metrics
- **Onboarding** — new engineers use lineage docs to understand data dependencies

## Interview Questions

**Q1: What is data lineage and why is it important?**
A: Data lineage tracks data flow from source to consumption. It enables impact analysis (what breaks if I change this table), root cause analysis (where did this bad data originate), regulatory compliance (GDPR data mapping), and onboarding (understanding data dependencies). Without lineage, data systems become opaque and fragile.

**Q2: How does column-level lineage differ from table-level?**
A: Table-level lineage maps source tables to target tables. Column-level traces which source columns feed into which target columns through transformations. Column-level is essential for precision — a table might have 50 columns, but only one column is affected by a schema change. Column-level requires parsing SQL or tracking transform logic.

**Q3: How would you implement lineage in an Airflow DAG?**
A: Airflow's `inlets` and `outlets` on operators define table-level lineage. For column-level, integrate OpenLineage — it emits lineage events automatically from Spark, dbt, and Airflow tasks. Marquez collects these events into a lineage graph with a UI.

**Q4: What is the difference between data lineage and data catalog?**
A: A data catalog is a searchable inventory of datasets with metadata (descriptions, owners, schema). Data lineage is the directed graph of data flow between datasets. Catalogs often include lineage as a feature, but lineage is a specific capability focused on tracing data movement and transformation.

## Cross-References

- [Data Quality](data-quality.md) — Propagating quality along lineage
- [Batch Processing](batch-processing.md) — Lineage in Spark and Airflow
- [Stream Processing](stream-processing.md) — Real-time lineage challenges
- [Data Formats](data-formats.md) — Schema evolution and lineage impact

## References

- [OpenLineage](https://openlineage.io/)
- [Apache Atlas](https://atlas.apache.org/)
- [DataHub](https://datahubproject.io/)
