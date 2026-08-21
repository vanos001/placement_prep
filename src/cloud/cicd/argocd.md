# ArgoCD (GitOps for Kubernetes)

ArgoCD is an open-source GitOps continuous delivery tool for Kubernetes, originally developed by Intuit in 2018 and donated to CNCF (graduated in 2022). It synchronizes Kubernetes manifests from a Git repository to a cluster, providing declarative deployments, drift detection, and a web UI for visibility. This page covers the architecture, the application model, the sync mechanism, and the comparison to Flux CD.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  ArgoCD (deployed in the cluster, in argocd namespace)      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  API Server (UI + REST + gRPC)                          │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Application Controller                                  │ │
│  │  - Watches Git repos for changes                         │ │
│  │  - Compares desired vs live state                        │ │
│  │  - Triggers syncs                                       │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Repo Server                                              │ │
│  │  - Clones Git repos                                      │ │
│  │  - Renders Helm/Kustomize/Jsonnet                        │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Application Controller                                  │ │
│  │  - Manages Application CRs                              │ │
│  │  - Coordinates sync operations                           │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ watches Git                  │ applies to cluster
        ▼                              ▼
    Git repositories              Kubernetes API
```

ArgoCD runs as a set of pods in the cluster it manages. It watches Git repos for changes and applies them to the cluster.

## The Application Model

An ArgoCD "Application" is a custom resource that defines what to deploy and where:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/my-org/my-app-deploy
    targetRevision: HEAD
    path: manifests/production
    # Or for Helm:
    # chart: my-app
    # helm:
    #   valueFiles:
    #     - values-production.yaml
    # Or for Kustomize:
    # kustomize:
    #   namePrefix: production-
  destination:
    server: https://kubernetes.default.svc
    namespace: production
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

The application:
- `source`: where to get the manifests (Git repo + path + revision).
- `destination`: where to apply (cluster + namespace).
- `syncPolicy.automated`: if true, ArgoCD auto-syncs on Git changes.

## The Sync Mechanism

```text
1. ArgoCD's Repo Server clones the Git repo (with credentials).
2. Renders manifests (Kustomize, Helm, plain YAML, Jsonnet).
3. Compares rendered manifests to live cluster state.
4. If they differ (drift detected):
   a. For manual sync: ArgoCD marks the app as "Out of sync".
   b. For auto-sync: ArgoCD applies the manifests.
5. On apply, ArgoCD uses Server-Side Apply (avoids conflicts with other controllers).
6. ArgoCD marks the app as "Healthy" or "Degraded" based on resource status.
```

The sync is **declarative**: ArgoCD declares the desired state (from Git) and converges the cluster to it. Manual changes to the cluster (e.g., `kubectl edit`) cause drift; ArgoCD's `selfHeal` option (default true) reverts manual changes.

## Sync Waves

ArgoCD supports sync waves for ordered resource deployment:

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "0"  # apply first
---
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"  # apply second
---
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "2"  # apply third
```

Resources with lower wave numbers are applied first; resources in the same wave are applied in parallel. Useful for dependencies (e.g., apply CRDs before CRs, apply namespaces before resources in them).

## Health Assessment

ArgoCD assesses each resource's health:

- **Healthy**: resource is ready (e.g., Deployment with all replicas ready).
- **Progressing**: resource is being created/updated.
- **Degraded**: resource has failed (e.g., CrashLoopBackOff).
- **Missing**: resource exists in Git but not in the cluster.
- **Suspended**: resource is paused (e.g., CronJob suspended).

Custom health checks can be added for CRDs (e.g., for a database operator's `Database` CRD).

## Multi-Cluster Deployment

ArgoCD can deploy to multiple clusters:

```yaml
spec:
  destination:
    server: https://kubernetes.default.svc  # local cluster
    # or:
    # server: https://my-other-cluster-api:6443  # registered cluster
    # name: my-other-cluster  # by name
```

To register a cluster:
```bash
argocd cluster add my-other-cluster
```

ArgoCD stores the cluster's credentials in a Secret; it uses them to apply manifests to the cluster.

## The App-of-Apps Pattern

For managing many applications, use the "app-of-apps" pattern:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root-app
spec:
  source:
    repoURL: https://github.com/my-org/apps
    path: apps
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
```

The `apps/` directory contains other Application manifests; ArgoCD deploys the root app, which in turn deploys all the leaf apps. This is a hierarchical deployment model.

## Production Use Cases

### GitOps Deployment

The standard pattern: developers commit to Git; ArgoCD auto-deploys:

```text
Developer commits to deploy repo
  ↓ (Git push)
Git server
  ↓ (webhook)
ArgoCD detects the change
  ↓ (sync)
Cluster updates
```

No `kubectl apply` from CI; Git is the source of truth.

### Multi-Environment Promotion

```text
Dev env (auto-sync from main branch)
  ↓ (promotion PR to staging branch)
Staging env (auto-sync from staging branch)
  ↓ (promotion PR to production branch)
Production env (auto-sync from production branch, with approval gate)
```

Each environment has its own branch; promotion is a PR. Production requires manual approval (a click in the ArgoCD UI).

### Disaster Recovery

```text
Cluster A dies (production)
  ↓ (failover)
ArgoCD re-points to Cluster B
  ↓ (sync)
Cluster B has the same manifests
```

Git is the source of truth; restoring to a new cluster is just "re-sync from Git".

## Common Pitfalls

1. **Forgetting that auto-sync can break production.** A bad commit auto-deploys; production breaks. Use manual sync (or sync windows) for production.

2. **Forgetting that selfHeal reverts manual changes.** A `kubectl edit` to debug an issue is reverted by ArgoCD. Disable selfHeal temporarily or commit the change to Git.

3. **Forgetting that the repo server caches Git repos.** Large repos take time to clone; subsequent reads are fast. Don't worry about clone latency.

4. **Forgetting that ArgoCD's RBAC is granular.** A user can have read access to one project and write to another. Configure RBAC carefully.

5. **Forgetting that sync waves are per-resource.** A resource with a wave of 0 is applied before all wave-1 resources. Set waves for dependent resources (e.g., namespace=0, secret=1, deployment=2).

6. **Forgetting that ArgoCD needs cluster admin to apply manifests.** The `argocd-application-controller` service account has cluster-admin (or equivalent). Restrict access to the argocd namespace.

## Comparison to Flux CD

| Aspect | ArgoCD | Flux CD |
|--------|--------|---------|
| Origin | Intuit 2018 | Weaveworks 2016 |
| Architecture | One process, controller + repo server + API | Controller only (lighter) |
| UI | Built-in web UI | Limited (via capabilities) |
| Helm | Built-in | Built-in |
| Kustomize | Built-in | Built-in |
| Multi-cluster | First-class | Yes (via Flux instances per cluster) |
| Best for | Visibility, multi-cluster, GUI-driven | Lightweight, CLI-driven |

Both are GitOps tools; ArgoCD has a richer UI and multi-cluster story; Flux is lighter. For most deployments, either works.

## References

- [ArgoCD documentation](https://argo-cd.readthedocs.io/)
- [ArgoCD GitHub](https://github.com/argoproj/argo-cd)
- [GitOps Principles (OpenGitOps)](https://opengitops.dev/)
- [ArgoCD + Helm](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/)
- [ArgoCD + Kustomize](https://argo-cd.readthedocs.io/en/stable/user-guide/kustomize/)
- [App-of-Apps pattern](https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/)
- [ArgoCD vs Flux comparison](https://www.weave.works/blog/gitops-tool-argo-cd-vs-flux-cd-comparison)
- [LWN: ArgoCD overview (2022)](https://lwn.net/Articles/856775/)
