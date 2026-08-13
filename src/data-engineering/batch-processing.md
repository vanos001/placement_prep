# Batch Processing

## MapReduce

Programming model for processing large datasets in parallel:

```
Input → Split → Map → Shuffle → Reduce → Output
```

```python
# Word count (classic example)
def mapper(document):
    for word in document.split():
        emit(word, 1)

def reducer(word, counts):
    emit(word, sum(counts))

# MapReduce handles: splitting, shuffling, fault tolerance
```

**Phases:**
1. **Map**: Process input chunks, emit (key, value) pairs
2. **Shuffle**: Group by key, send to reducers
3. **Reduce**: Aggregate values per key

## Apache Spark

In-memory distributed computing framework:

### RDDs (Resilient Distributed Datasets)

```python
rdd = sc.textFile("data.txt")
counts = (rdd
    .flatMap(lambda line: line.split())
    .map(lambda word: (word, 1))
    .reduceByKey(lambda a, b: a + b))
```

### DataFrames (modern Spark)

```python
df = spark.read.csv("data.csv", header=True)
result = (df
    .filter(df.age > 25)
    .groupBy("city")
    .agg(avg("salary"), count("*"))
    .orderBy(desc("count"))
)
```

### Spark Architecture

```
Driver → Cluster Manager → Executors
         ├── Executor 1 (tasks)
         ├── Executor 2 (tasks)
         └── Executor 3 (tasks)
```

- **Driver**: Runs your application, creates SparkContext
- **Cluster Manager**: Allocates resources (YARN, Mesos, K8s)
- **Executors**: Run tasks, store data in memory

## Apache Airflow

Workflow orchestration platform:

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG('etl_pipeline',
         start_date=datetime(2024, 1, 1),
         schedule='@daily',
         default_args=default_args) as dag:
    
    extract = PythonOperator(
        task_id='extract',
        python_callable=extract_data)
    
    transform = PythonOperator(
        task_id='transform',
        python_callable=transform_data)
    
    load = PythonOperator(
        task_id='load',
        python_callable=load_data)
    
    extract >> transform >> load
```

**Key concepts**: DAGs (Directed Acyclic Graphs), operators, sensors, XComs (cross-communication), pools, connections.

## References

- [Spark Documentation](https://spark.apache.org/docs/latest/)
- [Airflow Documentation](https://airflow.apache.org/docs/)
- [MapReduce Paper — Dean & Ghemawat](https://research.google.com/archive/mapreduce.html)
