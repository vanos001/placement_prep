# Slowly Changing Dimensions

Slowly Changing Dimensions (SCD) describe techniques for managing changes to dimension data in data warehouses. When a customer changes their name or a product moves to a new category, the warehouse must decide how to record the change.

## SCD Types

| Type | Strategy | History? | Complexity |
|---|---|---|---|
| **SCD 1** | Overwrite | No | Lowest |
| **SCD 2** | Add new row with versioning | Yes | Medium |
| **SCD 3** | Add previous value column | Partial | Low |
| **SCD 4** | Mini-dimension for rapid changes | Yes | High |
| **SCD 5/6** | Hybrid approaches | Yes | High |

## SCD Type 1: Overwrite

Simply update the existing row. No history retained.

```sql
UPDATE dim_customer
SET city = 'Austin'
WHERE customer_key = 42;
```

Use when: history is not needed (e.g., fixing a typo, updating a status flag).

## SCD Type 2: Add Row (Most Common)

Insert a new row with version metadata. The previous row is marked inactive.

```sql
-- Mark current row as expired
UPDATE dim_customer
SET is_current = FALSE, effective_end = CURRENT_DATE
WHERE customer_key = 42 AND is_current = TRUE;

-- Insert new version
INSERT INTO dim_customer (customer_key, name, city, effective_start, effective_end, is_current)
VALUES (42, 'Jane Smith', 'Austin', CURRENT_DATE, '9999-12-31', TRUE);
```

Key columns: `effective_start`, `effective_end`, `is_current`, and optionally `version_number` or `surrogate_key`.

## SCD Type 3: Previous Value Column

Add a `previous_city` column to track the prior value — only one level of history.

```sql
UPDATE dim_customer
SET previous_city = city, city = 'Austin'
WHERE customer_key = 42;
```

Use when: only the current and immediately previous values matter (e.g., tracking last promotion).

## SCD Type 4: Mini-Dimension

For attributes that change frequently (daily prices, scores), split them into a separate "mini-dimension" with its own surrogate key, joined at query time.

```text
dim_product: product_key, name, category (SCD 2)
dim_product_price: product_price_key, product_key, price, effective_date (SCD 2, rapid changes)
```

This avoids exploding the main dimension table with thousands of versions.

## ETL Implementation Pattern

```python
# Simplified SCD Type 2 merge (pyspark)
from pyspark.sql.functions import col, lit, current_date

# Find changed records
changes = staging.join(dim_table, ["natural_key"], "left_anti")

# Expire current records
existing = dim_table.filter(col("is_current") == True)
expired = existing.join(
    staging.select("natural_key"), ["natural_key"]
).withColumn("is_current", lit(False)) \
 .withColumn("effective_end", current_date())

# Insert new versions
new_rows = staging.withColumn("effective_start", current_date()) \
    .withColumn("effective_end", lit("9999-12-31")) \
    .withColumn("is_current", lit(True))
```

## When to Use Each

| Scenario | Recommended Type |
|---|---|
| Correcting data errors | SCD 1 |
| Customer address changes | SCD 2 |
| Tracking current + previous state | SCD 3 |
| Daily price changes | SCD 4 (mini-dimension) |
| Full audit trail required | SCD 2 |

## Interview Questions

**Q1: Explain SCD Type 2 and its implementation.**
A: SCD Type 2 adds a new row for each change, preserving full history. Each row has `effective_start`, `effective_end`, and `is_current` columns. On change, the existing row is expired (`is_current = FALSE`, `effective_end = today`) and a new row is inserted with `effective_start = today`. Fact tables join to dimension rows using `surrogate_key` and typically filter on `is_current = TRUE` or use a date range join.

**Q2: How do fact tables handle SCD 2 dimensions?**
A: Fact tables store the dimension's `surrogate_key` at the time of the transaction. This creates a point-in-time snapshot — querying a 2023 order joins to the dimension row that was current in 2023, giving the correct historical context. This is the "slowly changing" advantage over Type 1.

**Q3: When would you use SCD 4 over SCD 2?**
A: SCD 4 is for attributes that change very frequently. If a product's price changes daily, SCD 2 would create 365 rows per year per product. A mini-dimension separates these volatile attributes, keeping the main dimension compact while preserving price history.

**Q4: What is the performance impact of SCD 2 on queries?**
A: The dimension table grows over time, increasing scan sizes. Always filter on `is_current = TRUE` for current-state queries (index this column). Historical joins require range conditions on `effective_start`/`effective_end`, which are slower. Partitioning by `effective_start` date helps.

## Cross-References

- [Data Quality](data-quality.md) — Validating SCD data integrity
- [Batch Processing](batch-processing.md) — ETL jobs implementing SCD logic
- [Fundamentals](fundamentals.md) — Data warehouse architecture overview

## References

- [The Data Warehouse Toolkit — Ralph Kimball](https://www.kimballgroup.com/)
- [dbt SCD patterns](https://docs.getdbt.com/reference/resource-configs/postgres-scd)
