# Dagster

Dagster is an open-source data orchestration platform, developed by Dagster Labs since 2018. It is a modern alternative to Airflow, with a stronger focus on the data engineering workflow (asset-centric, not task-centric) and a more opinionated model for managing dependencies, types, and resources. This page covers the architecture, the asset-based model, the IO Manager, and the comparison to Airflow.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Dagster Webserver (UI)                                    │
│  - View runs, assets, schedules                             │
│  - Trigger runs, view logs                                  │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Dagster Daemon                                             │
│  - Schedules runs based on schedules and sensors            │
│  - Submits runs to the run launcher                         │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Run Launcher (determines where runs execute)               │
│  - DefaultRunLauncher (in-process)                          │
│  - CeleryK8sRunLauncher (Kubernetes with Celery)            │
│  - K8sRunLauncher (Kubernetes, one Pod per run)             │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Compute (one or more processes, per run)                   │
│  - Executes operations in dependency order                 │
│  - Uses the IO Manager to materialize outputs               │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Storage                                                    │
│  - Run history (PostgreSQL/MySQL/SQLite)                    │
│  - Computed assets (filesystem, S3, GCS, etc.)              │
└─────────────────────────────────────────────────────────────┘
```

Dagster separates the daemon (scheduling), the webserver (UI), and the run launcher (execution). All three can run on different machines.

## The Asset-Centric Model

Dagster's key innovation over Airflow: the "asset" abstraction. An asset is a logical data artifact (e.g., a Parquet file in S3, a table in Snowflake, a machine learning model).

```python
from dagster import asset

@asset
def raw_orders():
    """Raw orders extracted from the source database."""
    return extract_from_source_db()

@asset
def cleaned_orders(raw_orders):
    """Orders cleaned and deduplicated."""
    return clean(raw_orders)

@asset
def daily_order_summary(cleaned_orders):
    """Per-day summary of orders."""
    return summarize(cleaned_orders)
```

The asset decorator:
- Defines a function that materializes the asset.
- The asset's dependencies are inferred from the function signature (`cleaned_orders` depends on `raw_orders`).
- The asset is registered in the asset graph (visible in the UI).

The asset graph is a DAG of data artifacts, not tasks. The model emphasizes what data exists, not how it's computed.

## The Software-Defined Asset (SDA)

Dagster's Software-Defined Asset (SDA) model:

```python
from dagster import asset, SourceAsset, AssetKey

# Source asset: data that exists outside Dagster
source_orders = SourceAsset(
    AssetKey("source_orders"),
    description="Orders in the source PostgreSQL database."
)

# Derived asset: produced by Dagster
@asset
def cleaned_orders(source_orders):
    return clean(source_orders)

# Asset with explicit dependencies and group
@asset(
    deps=[AssetKey("cleaned_orders")],
    group_name="analytics"
)
def daily_order_summary():
    cleaned = load_from_storage("cleaned_orders")
    return summarize(cleaned)
```

The asset graph in the UI shows all assets and their dependencies. Clicking an asset shows its materialization history, last run, and lineage.

## IO Manager

Dagster's IO Manager handles asset persistence:

```python
from dagster import io_manager, IOManager

class S3ParquetIOManager(IOManager):
    def handle_output(self, context, obj):
        # obj is the function's return value
        path = f"s3://my-bucket/{context.asset_key.to_string()}.parquet"
        obj.to_parquet(path)
        context.log.info(f"Materialized to {path}")
    
    def load_input(self, context):
        path = f"s3://my-bucket/{context.asset_key.to_string()}.parquet"
        return pd.read_parquet(path)

@io_manager
def s3_parquet_io_manager():
    return S3ParquetIOManager()
```

The IO Manager abstracts persistence: the asset function just returns the data, and the IO Manager handles storing and loading it. Different IO Managers can use S3, Snowflake, BigQuery, etc.

## Resources

Dagster's "resources" are typed external services (databases, APIs, ML models):

```python
from dagster import resource, ConfigurableResource

class PostgreSQLResource(ConfigurableResource):
    host: str
    port: int
    database: str
    
    def query(self, sql):
        # connect and execute
        ...

@asset
def daily_orders(postgres: PostgreSQLResource):
    return postgres.query("SELECT * FROM orders WHERE date = current_date")
```

Resources are configured at deployment time (different config for dev vs. prod). They're injected into asset functions via type hints.

## Schedules and Sensors

```python
from dagster import schedule, sensor, RunRequest

@schedule(cron_schedule="0 1 * * *", job=my_job)
def daily_schedule(context):
    return RunRequest(run_key=str(context.scheduled_execution_time), run_config={...})

@sensor(job=my_job)
def new_file_sensor(context):
    files = list_new_files_in_s3()
    for f in files:
        yield RunRequest(run_key=f.key, run_config={"file": f.key})
```

Schedules trigger runs at fixed times; sensors trigger runs based on external events (new files, Kafka messages, etc.).

## Comparison to Airflow

| Aspect | Dagster | Airflow |
|--------|---------|---------|
| Model | Asset-centric (data artifacts) | Task-centric (operations) |
| Lineage | First-class (asset graph) | Manual (XComs) |
| Type system | Strong (Dagster types) | Weak (Python) |
| Configuration | Code-first (Python) | YAML/Python |
| IO management | IO Manager (typed) | XCom (untyped, DB-stored) |
| UI | Asset graph, lineage | DAG run, task logs |
| Best for | Data engineering, ML pipelines | General workflow orchestration |
| Production users | Modern data teams | Mature, broad ecosystem |

Dagster is more opinionated and asset-focused; Airflow is more flexible and task-focused. Both can do the same things; the choice is about which model fits your team.

## Production Use Cases

### ETL Pipelines

```python
# Multi-stage ETL
@asset
def raw_orders(postgres):
    return postgres.query("SELECT * FROM orders")

@asset
def cleaned_orders(raw_orders):
    return clean(raw_orders)

@asset
def daily_summary(cleaned_orders):
    return summarize(cleaned_orders)

@asset
def daily_summary_in_snowflake(daily_summary, snowflake):
    snowflake.execute("INSERT INTO daily_summary SELECT * FROM @stage")
```

### ML Pipelines

```python
@asset
def training_data(cleaned_orders):
    return build_training_set(cleaned_orders)

@asset
def trained_model(training_data):
    return train_model(training_data)

@asset
def model_metrics(trained_model, test_data):
    return evaluate(trained_model, test_data)

# Model is materialized when training_data is ready.
# Metrics are materialized when both model and test_data are ready.
```

### ELT with dbt Integration

Dagster integrates with dbt (the SQL transformation tool):

```python
from dagster_dbt import dbt_assets
from dagster import AssetSpec

# Import dbt models as Dagster assets
@dbt_assets(manifest=...)
def dbt_models(context):
    yield from DbtCliResource().stream(["run"], context=context)

# Reference upstream Dagster assets
upstream_specs = [
    AssetSpec("raw_orders", deps=[AssetKey("source_orders")]),
]

# The dbt model `cleaned_orders` is now an asset in Dagster
# It depends on `raw_orders` (a Dagster asset) and produces
# downstream dbt models.
```

This makes Dagster's UI show the full lineage from raw data through dbt SQL transforms to final dashboards.

## Common Pitfalls

1. **Forgetting that asset functions must be deterministic.** An asset that depends on `datetime.now()` won't materialize correctly across retries.

2. **Forgetting that IO Manager handles both input and output.** A function that returns a DataFrame has its output handled by the IO Manager; downstream functions receive the same DataFrame via the IO Manager.

3. **Forgetting that asset dependencies are inferred from function signature.** A function with no `deps` parameter has no dependencies.

4. **Forgetting that resources need configuration.** A `PostgreSQLResource` requires `host`, `port`, etc. set in `dagster.yaml` per environment.

5. **Forgetting that sensor functions can yield multiple RunRequests.** A sensor that finds 10 new files should yield 10 RunRequests (one per file).

6. **Forgetting that Dagster daemon must be running for schedules and sensors to work.** Without the daemon, schedules don't trigger.

## References

- [Dagster documentation](https://docs.dagster.io/)
- [Dagster GitHub repository](https://github.com/dagster-io/dagster)
- Nick Schrock, "[The Data Orchestrator](https://dagster.io/blog/data-orchestrator)" (Dagster blog)
- [Dagster vs Airflow comparison](https://docs.dagster.io/getting-started/why-dagster)
- [Dagster + dbt integration](https://docs.dagster.io/integrations/dbt)
- [Software-Defined Assets](https://docs.dagster.io/concepts/assets/software-defined-assets)
- [LWN: Dagster overview (2022)](https://lwn.net/Articles/888777/)
