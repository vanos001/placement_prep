# Apache Airflow

Apache Airflow is an open-source workflow orchestration platform, originally developed at Airbnb in 2014 by Maxime Beauchemin and donated to Apache in 2016. It is the de facto standard for scheduling and monitoring data pipelines, used by Airbnb, Netflix, Lyft, PayPal, and many other companies. This page covers the architecture, the DAG model, the executor types, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────┐
│  Web Server (Flask-based UI)                            │
│  - View DAGs, runs, task instances                       │
│  - Trigger runs, view logs                              │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Scheduler (one process)                                 │
│  - Scans DAGs in the DAGs folder                         │
│  - Schedules tasks based on dependencies                 │
│  - Submits tasks to the executor                         │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Executor (determines where tasks run)                  │
│  - SequentialExecutor (default, single-threaded)         │
│  - CeleryExecutor (distributed, via Celery)              │
│  - KubernetesExecutor (one Pod per task)                │
│  - LocalExecutor (multi-process on one machine)         │
│  - CeleryKubernetesExecutor (hybrid)                    │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  Metadata Database (PostgreSQL or MySQL)               │
│  - DAG runs, task instances, XComs                       │
│  - Variables, connections                                │
└─────────────────────────────────────────────────────────┘
```

The web server, scheduler, and executor are stateless processes; the metadata DB holds the state.

## The DAG Model

A DAG (Directed Acyclic Graph) is a Python file that defines a workflow:

```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'email': ['data-team@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'daily_etl',
    default_args=default_args,
    description='Daily ETL pipeline',
    schedule_interval='0 1 * * *',  # Daily at 1am
    start_date=datetime(2026, 1, 1),
    catchup=False,  # don't backfill
    tags=['etl'],
) as dag:
    
    extract = BashOperator(
        task_id='extract',
        bash_command='python /opt/etl/extract.py --date {{ ds }}',
    )
    
    transform = PythonOperator(
        task_id='transform',
        python_callable=transform_function,
        op_kwargs={'date': '{{ ds }}'},
    )
    
    load = BashOperator(
        task_id='load',
        bash_command='python /opt/etl/load.py --date {{ ds }}',
    )
    
    extract >> transform >> load  # define dependencies
```

Key concepts:
- **DAG**: a workflow with a name, schedule, and dependencies.
- **Task**: a single operation in the DAG (Bash command, Python function, etc.).
- **Task instance**: a specific run of a task (for a specific schedule date).
- **XCom**: cross-task communication (small data, like a filename).
- **Variable**: global configuration (stored in the metadata DB).

## The Scheduler

The scheduler runs continuously (one process), scanning the DAGs folder every N seconds (default 5):

1. Find new DAGs (parse Python files).
2. Find new DAG runs (based on schedule_interval).
3. For each task instance, check dependencies and queue it for execution.
4. Update task instance states as executors report results.

The scheduler's main loop is single-threaded; this can be a bottleneck for large DAGs (>1000 tasks). Airflow 2.4+ added a multi-process scheduler (still experimental).

## Executor Types

### SequentialExecutor

Single-threaded; one task at a time. Used for development only.

### LocalExecutor

Multi-process on one machine; uses Python's `multiprocessing`. Useful for testing small DAGs on a single node.

### CeleryExecutor

Distributed via Celery (a Python task queue). Tasks are submitted to a Celery broker (Redis or RabbitMQ); Celery workers pick them up. Production choice for many Airflow deployments.

```python
# airflow.cfg
executor = CeleryExecutor
broker_url = 'redis://redis:6379/0'
result_backend = 'redis://redis:6379/1'

# Start Celery workers
celery -A airflow.executors.celery_executor.app worker
```

### KubernetesExecutor

One Kubernetes Pod per task. Each task runs in its own isolated Pod with its own resources. Best for:
- Tasks with different resource requirements (CPU, memory, GPU).
- Tasks that need isolation (different Python environments, secrets).
- Clusters that already have Kubernetes.

```python
# airflow.cfg
executor = KubernetesExecutor
kubernetes_config = '/home/airflow/.kube/config'

# Per-task resources
@task(
    executor_config={
        "KubernetesExecutor": {
            "resources": {
                "requests": {"cpu": "2", "memory": "4Gi"},
                "limits": {"cpu": "4", "memory": "8Gi"},
            }
        }
    }
)
def train_model():
    ...
```

### CeleryKubernetesExecutor

Hybrid: Celery for short tasks, Kubernetes for resource-intensive tasks. The scheduler picks the executor per task.

## Backfilling

When a DAG's start_date is in the past and `catchup=True`, Airflow runs the DAG for every missed schedule between start_date and now. This is "backfilling":

```python
# Run daily from 2025-01-01 to 2026-01-01 (365 runs, one per day)
with DAG('backfill_etl', start_date=datetime(2025, 1, 1), catchup=True) as dag:
    ...
```

Backfilling can be paused, resumed, and selective (run only specific date ranges).

## Airflow 2.x: TaskFlow API

Airflow 2.0 (2020) introduced the TaskFlow API, a more Pythonic way to define tasks:

```python
from airflow.decorators import task, dag

@dag(schedule='0 1 * * *', start_date=datetime(2026, 1, 1), catchup=False)
def daily_etl():
    
    @task
    def extract(date: str) -> dict:
        data = fetch_data(date)
        return {'date': date, 'records': data}
    
    @task
    def transform(extract_output: dict) -> dict:
        transformed = transform_data(extract_output['records'])
        return {'date': extract_output['date'], 'transformed': transformed}
    
    @task
    def load(transform_output: dict):
        load_to_warehouse(transform_output['transformed'])
    
    extract_output = extract('{{ ds }}')
    transform_output = transform(extract_output)
    load(transform_output)

daily_etl_dag = daily_etl()
```

XCom (cross-task communication) is implicit — function return values are automatically passed to the next task. This is much cleaner than the manual XCom API in Airflow 1.x.

## Production Patterns

### Pattern 1: Idempotent Tasks

Tasks should produce the same output for the same input, regardless of how many times they run. This is critical for retries:

```python
@task
def load_to_warehouse(date: str):
    # Delete existing data for this date, then insert
    db.execute(f"DELETE FROM fact_orders WHERE date = '{date}'")
    db.execute(f"INSERT INTO fact_orders SELECT * FROM staging_orders WHERE date = '{date}'")
```

Without the DELETE, retrying the task would insert duplicates.

### Pattern 2: Small Tasks for Better Restartability

A 1-hour task that fails at minute 50 must retry the entire 60 minutes. Split into 5 tasks of 12 minutes each — retries only repeat the failed task.

### Pattern 3: Use XCom for Small Data Only

XCom is stored in the metadata DB. Large XComs (e.g., a DataFrame) bloat the DB. Use a file path or a key in object storage instead.

### Pattern 4: Separate Task Logic from Execution

The DAG file should only define the workflow (dependencies, schedule). The task logic should be in a separate Python module (imported by the DAG).

## Common Pitfalls

1. **Forgetting to set `catchup=False` for new DAGs.** Without this, Airflow backfills from `start_date` to now, which can be days of catch-up runs.

2. **Setting `start_date` to a dynamic value (e.g., `datetime.now()`).** This causes the DAG to re-evaluate the start_date on every scheduler run, causing issues. Use a fixed date.

3. **Forgetting that the DAG file is parsed by the scheduler every 5 seconds.** Heavy imports in the DAG file slow the scheduler. Use `pendulum` for time handling; avoid heavy libraries at top level.

4. **Forgetting that tasks must be idempotent.** A task that fails after partial completion and is retried must produce the same result as a clean run.

5. **Forgetting that XComs are stored in the DB.** Large XComs bloat the DB. Use S3 paths instead.

6. **Trusting the scheduler to retry on transient failures.** Airflow's retry mechanism only kicks in for task failures (exceptions). Network blips that hang need explicit timeout handling.

## Comparison to Other Orchestrators

| Aspect | Airflow | Dagster | Prefect | Argo Workflows |
|--------|---------|---------|---------|-----------------|
| Origin | Airbnb 2014 | Dagster 2018 | Prefect 2018 | Argo 2017 |
| Domain | Data pipelines | Data pipelines | Data + general | Kubernetes-native |
| Language | Python | Python | Python | YAML |
| DAG model | Python code | Python code | Python code | YAML |
| Best for | Mature, broad ecosystem | Data-aware (asset-centric) | Modern, easy | K8s, CI/CD pipelines |
| Production users | Many large companies | Modern data teams | Smaller companies | K8s-centric |

Airflow remains the most popular; Dagster and Prefect are newer alternatives. Argo Workflows is for Kubernetes-native environments.

## References

- [Apache Airflow documentation](https://airflow.apache.org/docs/apache-airflow/stable/)
- [Airflow GitHub repository](https://github.com/apache/airflow)
- Maxime Beauchemin, "[The Rise of the Data Engineer](https://medium.com/rise-of-the-data-engineer)" (2017)
- [Airflow 2.0 TaskFlow API](https://airflow.apache.org/docs/apache-airflow/stable/tutorial_taskflow_api.html)
- [CeleryExecutor configuration](https://airflow.apache.org/docs/apache-airflow/stable/executor/celery.html)
- [KubernetesExecutor configuration](https://airflow.apache.org/docs/apache-airflow/stable/executor/kubernetes.html)
- [Airflow vs Dagster vs Prefect comparison](https://www.astronomer.io/guides/airflow-dagster-prefect-comparison/)
