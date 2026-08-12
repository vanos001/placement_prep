# Data Engineering Fundamentals

## ETL vs ELT

| Aspect | ETL | ELT |
|---|---|---|
| Order | Extract → Transform → Load | Extract → Load → Transform |
| Transform | Before loading (middleware) | After loading (in warehouse) |
| Best for | Traditional data warehouses | Cloud data warehouses |
| Tools | Informatica, Talend, SSIS | dbt, Spark, BigQuery SQL |
| Flexibility | Schema-on-write | Schema-on-read |

## Data Warehouse vs Data Lake vs Lakehouse

| Aspect | Data Warehouse | Data Lake | Lakehouse |
|---|---|---|---|
| Data | Structured | Raw (all types) | All types |
| Schema | Schema-on-write | Schema-on-read | Both |
| Format | SQL tables | Files (Parquet, JSON) | Tables + files |
| Users | Analysts | Data scientists | Both |
| Cost | Expensive (storage + compute) | Cheap storage | Optimized |
| Examples | Snowflake, Redshift | S3, ADLS | Delta Lake, Iceberg |

## OLTP vs OLAP

| Aspect | OLTP | OLAP |
|---|---|---|
| Purpose | Transaction processing | Analytics |
| Queries | Simple, frequent | Complex, aggregations |
| Data | Current, operational | Historical, analytical |
| Schema | Normalized (3NF) | Denormalized (star/snowflake) |
| Row count | Thousands-millions | Millions-billions |
| Response | Milliseconds | Seconds-minutes |

## Star Schema

```
       ┌──────────┐
       │  Fact    │
       │ Table    │
       │(sales)   │
       └──┬──┬──┬─┘
          │  │  │
    ┌─────┘  │  └─────┐
    ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐
│ Dim  │ │ Dim  │ │ Dim  │
│ Time │ │Prod  │ │Store │
└──────┘ └──────┘ └──────┘
```

- **Fact table**: Measurements (sales amount, quantity)
- **Dimension tables**: Context (time, product, store, customer)
- **Star**: One level of dimensions around fact
- **Snowflake**: Dimensions normalized into sub-dimensions

## References

- [Designing Data-Intensive Applications — Kleppmann](https://dataintensive.net/)
- [Fundamentals of Data Engineering — Reis & Housley](https://www.oreilly.com/library/view/fundamentals-of-data/9781098108298/)
