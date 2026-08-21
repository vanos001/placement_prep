# Argo Workflows

Argo Workflows is an open-source workflow engine for Kubernetes, originally developed at BlackRock in 2017 and donated to CNCF. It executes DAGs (Directed Acyclic Graphs) and step-based workflows as Kubernetes pods, with parallelism, retries, and artifact passing. This page covers the architecture, the workflow spec, the artifact handling, and the comparison to Apache Airflow.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Argo Workflows Controller (in cluster)                    │
│  - Watches Workflow CRs                                     │
│  - Creates Pods for each step                                │
│  - Tracks dependencies                                       │
│  - Manages retries                                           │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ Workflow CR                  │ artifact passing
        ▼                              ▼
    User submits workflow        Pod 1's output → Pod 2's input
```

Argo Workflows is installed in a Kubernetes cluster. Workflows are defined as custom resources (CRs); the controller orchestrates them as Pods.

## The Workflow Spec

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: hello-world-
spec:
  entrypoint: main
  templates:
    - name: main
      steps:
        - - name: step1
            template: hello
        - - name: step2
            template: goodbye
    
    - name: hello
      container:
        image: alpine:latest
        command: [echo]
        args: ["Hello, World!"]
    
    - name: goodbye
      container:
        image: alpine:latest
        command: [echo]
        args: ["Goodbye!"]
```

The workflow:
- `entrypoint`: the template to start with.
- `templates`: reusable units of work.
- `steps`: a list of steps (each step is a list; the list runs in parallel, the next list runs sequentially).

## DAGs vs Steps

Argo supports two ways to define execution order:

### Steps

```yaml
- name: main
  steps:
    - - name: extract
        template: extract-task
    - - name: transform
        template: transform-task
    - - name: load
        template: load-task
```

Sequential by default; nested lists are parallel.

### DAG

```yaml
- name: main
  dag:
    tasks:
      - name: extract
        template: extract-task
      - name: transform
        dependencies: [extract]
        template: transform-task
      - name: load
        dependencies: [transform]
        template: load-task
```

DAGs are more expressive — you can have fan-out (one task depends on multiple) and fan-in (multiple tasks feed into one).

## Parallelism

```yaml
- name: parallel-process
  dag:
    tasks:
      - name: process-1
        template: process-template
      - name: process-2
        template: process-template
      - name: process-3
        template: process-template
  parallelism: 2  # max 2 tasks running at once
```

`parallelism` limits concurrent executions. Useful for resource constraints or external API rate limits.

## Artifacts

Argo supports passing artifacts (files) between steps:

```yaml
- name: produce-artifact
  container:
    image: alpine
    command: [sh, -c]
    args: ["echo 'Hello' > /tmp/hello.txt"]
  outputs:
    artifacts:
      - name: hello
        path: /tmp/hello.txt

- name: consume-artifact
  inputs:
    artifacts:
      - name: hello
        path: /tmp/hello.txt
  container:
    image: alpine
    command: [cat]
    args: ["/tmp/hello.txt"]
```

Artifacts are stored in an artifact repository (S3, GCS, etc.) between steps. The first step writes to `/tmp/hello.txt`; Argo uploads it; the second step downloads it before starting.

## Retries

```yaml
- name: retry-task
  retryStrategy:
    limit: "3"
    retryPolicy: "Always"  # or "OnFailure" or "OnError"
  container:
    image: my-image
    command: [my-script]
```

On failure, Argo retries up to `limit` times. The retry policy controls when to retry (e.g., `OnFailure` retries on exit non-zero; `OnError` retries on pod errors).

## Production Use Cases

### ETL Pipelines

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
spec:
  entrypoint: etl
  templates:
    - name: etl
      dag:
        tasks:
          - name: extract
            template: extract
          - name: transform
            dependencies: [extract]
            template: transform
            withItems:  # fan-out
              - { region: "us-east" }
              - { region: "eu-west" }
              - { region: "ap-south" }
          - name: load
            dependencies: [transform]
            template: load
```

ETL pipeline with fan-out (3 parallel transforms per region) and fan-in (single load after all transforms).

### ML Training

```yaml
- name: ml-pipeline
  dag:
    tasks:
      - name: preprocess
        template: preprocess-data
      - name: train
        dependencies: [preprocess]
        template: train-model
        withItems:  # hyperparameter sweep
          - { lr: 0.01 }
          - { lr: 0.001 }
          - { lr: 0.0001 }
      - name: evaluate
        dependencies: [train]
        template: evaluate-model
      - name: deploy
        dependencies: [evaluate]
        template: deploy-best-model
```

ML pipeline with hyperparameter sweep (3 parallel training runs), evaluation, deployment.

### CI/CD Pipelines

Argo Workflows can be used as a CI/CD engine (alternative to Jenkins, GitLab CI). Each step is a container; artifacts pass between steps; the workflow is triggered by a Git webhook.

## Comparison to Apache Airflow

| Aspect | Argo Workflows | Airflow |
|--------|----------------|---------|
| Origin | BlackRock 2017 | Airbnb 2014 |
| Runtime | Kubernetes pods | Celery workers |
| Workflows | YAML/CRD | Python DAG files |
| Parallelism | K8s-native (pods) | Celery workers (processes) |
| Artifacts | Built-in (S3, GCS) | XComs (limited) |
| Best for | K8s-native, container-heavy | Python-centric, broad ecosystem |

For Kubernetes-native deployments, Argo is the natural choice. For Python-heavy teams, Airflow is familiar.

## Common Pitfalls

1. **Forgetting that workflows create many pods.** A workflow with 100 parallel tasks creates 100 pods; the cluster needs capacity. Use `parallelism` and resource quotas.

2. **Forgetting that artifact repositories need configuration.** The default is emptyDir (lost on pod completion). For persistent artifacts, configure S3/GCS.

3. **Forgetting that workflows can fail to clean up.** A workflow that crashes mid-execution leaves Pods behind. Set `ttlStrategy` (default: delete after 3 days).

4. **Forgetting that retries can amplify side effects.** A task that sends an email will resend on retry. Make tasks idempotent.

5. **Forgetting that DAGs can have cycles in user code.** A typo in `dependencies` can create a cycle; Argo detects and rejects it. Use the `argocd workflow lint` command.

6. **Forgetting that large artifacts can be slow to pass.** A 1 GB artifact takes minutes to upload/download. Use S3 directly and pass the S3 URI.

## References

- [Argo Workflows documentation](https://argoproj.github.io/argo-workflows/)
- [Argo Workflows GitHub](https://github.com/argoproj/argo-workflows)
- [Workflow Examples](https://github.com/argoproj/argo-workflows/tree/master/examples)
- [Argo Workflows vs Airflow (CNCF blog)](https://www.cncf.io/blog/2021/05/26/argo-workflows-vs-apache-airflow/)
- [ArgoCD: the related CD tool](https://argo-cd.readthedocs.io/)
- [LWN: Argo Workflows overview (2022)](https://lwn.net/Articles/856775/)
