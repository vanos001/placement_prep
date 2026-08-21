# Tekton

Tekton is an open-source framework for building CI/CD systems, originally developed at Google (as part of Knative) in 2018 and donated to CD Foundation (now Linux Foundation) in 2019. It provides Kubernetes-native building blocks (Tasks, Pipelines) for defining CI/CD workflows as Kubernetes resources. This page covers the architecture, the resource model, the runtime, and the comparison to Argo Workflows.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Tekton Controller (Tekton Pipelines)                       │
│  - Watches PipelineRun/TaskRun CRs                          │
│  - Creates Pods for each Task step                          │
│  - Tracks dependencies and status                            │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▼
        │ PipelineRun/TaskRun           │ Pod creation
        ▼                              ▼
    User submits CR               Kubernetes cluster
```

Tekton is a Kubernetes-native CI/CD framework. Workflows are defined as custom resources; the Tekton controller orchestrates them as Pods.

## The Resource Model

Tekton has a hierarchy of resources:

### Tasks

A Task is a sequence of steps:

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: build-and-push
spec:
  params:
    - name: image
      type: string
    - name: context
      type: string
      default: "."
  workspaces:
    - name: source
      mountPath: /workspace
  steps:
    - name: build
      image: gcr.io/kaniko-project/executor:latest
      command:
        - /kaniko/executor
      args:
        - --dockerfile=Dockerfile
        - --context=$(workspaces.source.path)/$(params.context)
        - --destination=$(params.image)
```

Each step runs in a container; steps in the same Task share a workspace (volume).

### Pipelines

A Pipeline is a DAG of Tasks:

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
  params:
    - name: image
      type: string
  workspaces:
    - name: shared-data
  tasks:
    - name: build
      taskRef:
        name: build-and-push
      params:
        - name: image
          value: $(params.image)
      workspaces:
        - name: source
          workspace: shared-data
    
    - name: test
      runAfter:
        - build
      taskRef:
        name: run-tests
      workspaces:
        - name: source
          workspace: shared-data
    
    - name: deploy
      runAfter:
        - test
      taskRef:
        name: deploy-to-k8s
      params:
        - name: image
          value: $(params.image)
```

Tasks can run sequentially (via `runAfter`) or in parallel (no `runAfter`).

### TaskRuns and PipelineRuns

A `TaskRun` or `PipelineRun` instantiates a Task/Pipeline with specific parameters:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: build-test-deploy-run-
spec:
  pipelineRef:
    name: build-test-deploy
  params:
    - name: image
      value: gcr.io/my-project/app:v1
  workspaces:
    - name: shared-data
      volumeClaimTemplate:
        spec:
          accessModes: [ReadWriteOnce]
          resources:
            requests:
              storage: 1Gi
```

The `PipelineRun` creates a PVC for the workspace, runs the pipeline, and cleans up.

## Workspaces

Workspaces are Tekton's mechanism for sharing data between Tasks:

```yaml
workspaces:
  - name: source
    mountPath: /workspace
```

A workspace can be backed by:
- **PersistentVolumeClaim**: a real PVC; data persists across Task steps.
- **VolumeClaimTemplate**: dynamically provisioned PVC.
- **ConfigMap**: read-only configuration.
- **Secret**: secrets.
- **EmptyDir**: ephemeral.

## Catalogs and Reusability

Tekton has a "Catalog" of reusable Tasks and Pipelines (the Tekton Catalog, https://github.com/tektoncd/catalog). Common Tasks include:
- `git-clone`: clone a Git repo.
- `kaniko`: build a Docker image.
- `kubectl-deploy`: deploy to Kubernetes.
- `golang-test`: run Go tests.

You can install the catalog's Tasks via Tekton's CLI:
```bash
tkn hub install git-clone
```

For private Tasks, you can host your own catalog (a Git repo with Task YAMLs).

## Production Use Cases

### CI Pipeline

```yaml
# Tekton pipeline for CI
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: ci-pipeline
spec:
  workspaces:
    - name: source
  tasks:
    - name: clone
      taskRef:
        name: git-clone
      workspaces:
        - name: output
          workspace: source
      params:
        - name: url
          value: $(params.repo-url)
    
    - name: lint
      runAfter: [clone]
      taskRef:
        name: golangci-lint
      workspaces:
        - name: source
          workspace: source
    
    - name: test
      runAfter: [lint]
      taskRef:
        name: golang-test
      workspaces:
        - name: source
          workspace: source
    
    - name: build
      runAfter: [test]
      taskRef:
        name: kaniko
      workspaces:
        - name: source
          workspace: source
      params:
        - name: IMAGE
          value: $(params.image)
```

### CD Pipeline (with ArgoCD Integration)

Tekton can build images; ArgoCD can deploy them:

```yaml
- name: update-manifest
  runAfter: [build]
  taskRef:
    name: argocd-taskset-sync
  params:
    - name: application-name
      value: my-app
    - name: revision
      value: $(params.image)
```

Tekton updates the Git repo's image tag; ArgoCD detects the change and deploys.

### Multi-Arch Builds

For multi-architecture images (amd64, arm64):

```yaml
- name: build-amd64
  taskRef:
    name: kaniko
  params:
    - name: IMAGE
      value: $(params.image)-amd64
  # ...

- name: build-arm64
  taskRef:
    name: kaniko
  params:
    - name: IMAGE
      value: $(params.image)-arm64
  # ...

- name: manifest
  runAfter: [build-amd64, build-arm64]
  taskRef:
    name: manifest-tool
```

Parallel builds for each architecture; then a manifest list combines them.

## Comparison to Argo Workflows and Jenkins

| Aspect | Tekton | Argo Workflows | Jenkins |
|--------|--------|-----------------|---------|
| Origin | Google 2018 | BlackRock 2017 | Sun 2011 |
| Runtime | K8s Pods | K8s Pods | JVM + agents |
| Resource model | Tasks/Pipelines (CRDs) | Workflows (CRDs) | XML jobs |
| Reusability | Catalog (Tasks) | Templates | Plugins |
| Best for | Building CI/CD systems | Workflow execution | Legacy CI |

Tekton is more of a "framework for building CI/CD" than a complete CI/CD solution; teams often build their own CI/CD on top (e.g., Red Hat OpenShift Pipelines is Tekton-based).

## Common Pitfalls

1. **Forgetting that workspaces need to be configured.** Without a workspace, Tasks can't share data. Use `volumeClaimTemplate` for ephemeral data, real PVCs for persistent.

2. **Forgetting that Tasks must be installed.** Tekton doesn't ship Tasks; you install them from the catalog or write your own.

3. **Forgetting that retries are per-Task, not per-step.** Set retries at the PipelineRun level, not per step.

4. **Forgetting that Task steps share a workspace.** If one step writes a file and another reads it, ensure the order (steps are sequential within a Task).

5. **Forgetting that PVCs cost money.** A PipelineRun creates a PVC per workspace; many runs create many PVCs. Use `volumeClaimTemplate` with `storageClassName: standard` and a small `storage` request.

6. **Forgetting that Tekton doesn't have a UI by default.** Use `tkn` CLI or install Tekton Dashboard for a UI.

## References

- [Tekton documentation](https://tekton.dev/docs/)
- [Tekton GitHub](https://github.com/tektoncd/pipeline)
- [Tekton Catalog](https://github.com/tektoncd/catalog)
- [Tekton CLI (tkn)](https://github.com/tektoncd/cli)
- [OpenShift Pipelines (Tekton-based)](https://docs.openshift.com/container-platform/latest/cicd/pipelines/understanding-openshift-pipelines.html)
- [Tekton vs Argo Workflows comparison](https://www.cncf.io/blog/2021/05/26/tekton-vs-argo-workflows/)
- [LWN: Tekton overview (2022)](https://lwn.net/Articles/856775/)
