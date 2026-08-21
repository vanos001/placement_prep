# Flux CD

Flux CD is an open-source GitOps continuous delivery tool for Kubernetes, originally developed by Weaveworks in 2016 and donated to CNCF (graduated in 2022). It is the GitOps counterpart to ArgoCD — both implement GitOps, but Flux is lighter (controller-only, no UI) and uses a different architectural model. This page covers the architecture, the source model, the reconciliation loop, and the comparison to ArgoCD.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Flux Controllers (in the cluster, in flux-system namespace)│
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Source Controller                                       │ │
│  │  - Watches GitRepository/Bucket/HelmChart CRs           │ │
│  │  - Clones/fetches and stores artifacts in a bucket       │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Kustomize Controller                                    │ │
│  │  - Watches Kustomization CRs                              │ │
│  │  - Renders Kustomize from source                          │ │
│  │  - Applies to cluster                                     │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Helm Controller                                         │ │
│  │  - Watches HelmRelease CRs                                │ │
│  │  - Runs Helm install/upgrade                              │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Notification Controller                                 │ │
│  │  - Sends notifications (Slack, Discord, GitHub)         │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

Flux is split into multiple controllers, each handling a different aspect (source, kustomize, helm, notifications). Each runs as a Deployment in the cluster.

## The Source Model

A "source" is a CRD defining where manifests come from:

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata:
  name: my-app
  namespace: flux-system
spec:
  url: https://github.com/my-org/my-app-deploy
  ref:
    branch: main
  secretRef:
    name: my-git-secret  # for private repos
  interval: 1m  # poll every 1 minute (or use webhook)
```

The source controller clones the Git repo, stores the latest commit's manifests in an internal bucket, and updates the GitRepository's status with the latest revision.

Other source types:
- `Bucket`: S3/GCS bucket.
- `HelmChart`: a Helm chart from a registry.

## The Kustomization Model

A "Kustomization" defines how to apply manifests:

```yaml
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: my-app
  namespace: flux-system
spec:
  sourceRef:
    kind: GitRepository
    name: my-app
  path: ./manifests/production
  interval: 1m
  prune: true  # delete resources not in Git
  timeout: 5m
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: my-app
      namespace: production
```

The Kustomize controller:
1. Reads the source's manifests.
2. Renders Kustomize (if `kustomization.yaml` exists).
3. Applies the manifests to the cluster.
4. Optionally runs health checks.
5. Reports status (Ready, Reconciling, Failed).

## The HelmRelease Model

For Helm-based deployments:

```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: my-app
  namespace: production
spec:
  interval: 1m
  chart:
    spec:
      chart: my-app
      version: "1.0.0"
      sourceRef:
        kind: HelmRepository
        name: my-repo
        namespace: flux-system
  values:
    replicaCount: 3
    image:
      repository: my-app
      tag: v1.0.0
```

The Helm controller:
1. Pulls the chart from the source.
2. Renders Helm with the provided values.
3. Installs/upgrades the release.
4. Reports status.

## The Reconciliation Loop

Flux's core pattern:
1. **Interval-based polling**: each Kustomization/HelmRelease polls the source every N minutes (default 1m).
2. **Webhook-based (optional)**: configure a webhook receiver; Git pushes trigger immediate reconciliation.
3. **Drift detection**: if the cluster's state differs from Git, Flux reconciles.
4. **Pruning**: if `prune: true`, Flux deletes resources that exist in the cluster but not in Git.

## Production Use Cases

### Multi-Tenant Cluster

```text
Team A's Git repo → flux-system namespace → team-a namespace (in cluster)
Team B's Git repo → flux-system namespace → team-b namespace (in cluster)
```

Each team has its own GitRepository + Kustomization; Flux syncs them independently. Use RBAC to limit what each team can deploy.

### Multi-Cluster

```text
Cluster A: runs Flux, syncs from cluster-a branch
Cluster B: runs Flux, syncs from cluster-b branch
```

Each cluster has its own Flux instance; the same Git repo has per-cluster branches.

### Helm Chart Distribution

For organizations that publish Helm charts:
- Source: a HelmRepository pointing to the chart registry.
- HelmRelease: installs the chart in the cluster.

When the chart is updated in the registry, Flux can auto-upgrade (with `version: "*"` or by pinning).

## Comparison to ArgoCD

| Aspect | Flux | ArgoCD |
|--------|------|--------|
| Architecture | Multiple controllers | Single process (API + controller + repo server) |
| UI | None (CLI only) | Built-in web UI |
| Reconciliation | Polling (or webhook) | Polling + webhook |
| Sources | Git, Bucket, HelmChart | Git only (with Helm/Kustomize rendering) |
| Multi-cluster | One Flux per cluster | One ArgoCD manages many clusters |
| Resource model | GitRepository/Kustomization/HelmRelease CRs | Application CRs |
| Best for | Lightweight, CLI-driven | GUI, multi-cluster visibility |

Both implement GitOps; the choice is often stylistic (CLI vs. UI). For teams that want a UI, ArgoCD wins. For teams that want a lightweight, CLI-driven flow, Flux.

## Common Pitfalls

1. **Forgetting that Flux doesn't have a UI.** Operations are via `flux` CLI or kubectl. Some teams find this limiting.

2. **Forgetting that Flux's reconciliation interval matters.** A 1-minute interval means drift can persist for 1 minute; a 5-minute interval saves resources but is slower. Use webhooks for instant reconciliation.

3. **Forgetting that pruning can delete resources.** If you `kubectl apply` a resource that's not in Git, Flux deletes it (with `prune: true`). Use `prune: false` for namespaces with manual operations, or commit the resource to Git.

4. **Forgetting that Flux needs cluster-admin to apply manifests.** The `flux-system` service account has cluster-admin. Restrict access to the flux-system namespace.

5. **Forgetting that HelmRelease upgrades can be slow.** A large Helm chart with many dependencies takes time to render and install. Set appropriate `timeout` values.

6. **Forgetting that Flux's notification controller needs configuration.** By default, no notifications are sent. Configure a Provider (Slack, Discord, GitHub) to get alerts on sync failures.

## References

- [Flux documentation](https://fluxcd.io/flux/)
- [Flux GitHub](https://github.com/fluxcd/flux2)
- [GitOps with Flux (CNCF)](https://github.com/fluxcd/flux2)
- [Flux vs ArgoCD comparison](https://www.weave.works/blog/gitops-tool-argo-cd-vs-flux-cd-comparison)
- [Flux Multi-tenancy](https://fluxcd.io/flux/flux-multi-tenancy/)
- [Flux Notifications](https://fluxcd.io/flux/components/notification/)
- [LWN: Flux CD overview (2022)](https://lwn.net/Articles/856775/)
