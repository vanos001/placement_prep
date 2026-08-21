# Kubernetes Operator Pattern

An operator is a Kubernetes pattern where a custom controller manages a custom resource (CRD) that represents an application or service. The operator encapsulates the operational knowledge of running that application — installation, scaling, backups, upgrades, failover — in code that runs as a Kubernetes controller. The pattern was introduced by CoreOS in 2016 (the etcd operator) and has since become the standard way to run stateful applications on Kubernetes. This page covers the controller-reconcile loop, the CRD definition, the leader-election model, and the production operator ecosystems (OperatorHub, OLM).

## The Core Idea

A traditional Kubernetes controller (Deployment, StatefulSet, ReplicaSet) manages generic workloads. It doesn't know about the application's semantics — a Deployment doesn't know that a PostgreSQL primary needs to be promoted from a replica on failure, or that a backup should be taken before a major version upgrade.

An operator adds this domain knowledge:

```text
User creates CR:
  apiVersion: postgresql.example.com/v1
  kind: PostgresCluster
  metadata:
    name: prod-db
  spec:
    replicas: 3
    version: "16"
    backup:
      schedule: "0 2 * * *"
      retention: 30d

Operator observes CR:
  - Sees spec.replicas=3, creates StatefulSet with 3 Pods
  - Sees spec.version=16, uses postgres:16 image
  - Sees spec.backup.schedule, creates CronJob
  - On Pod failure, sees new Pod is a replica, promotes to primary

User updates CR:
  spec.version: "17"

Operator observes:
  - Sees version change 16 → 17
  - Performs rolling upgrade: one replica at a time, with health checks
  - Updates the spec.status field to reflect progress
```

The operator's logic is application-specific. A PostgreSQL operator handles Postgres-specific concerns; a Kafka operator handles Kafka-specific concerns. The Kubernetes control plane is generic; the operator adds the domain layer.

## The Controller-Reconcile Loop

The operator's core is the reconcile loop:

```text
Reconcile(ctx, request):
  1. Fetch the CR (e.g., PostgresCluster) for the request.
  2. Fetch child resources (StatefulSet, Services, Secrets, CronJobs).
  3. Compare desired state (from CR.spec) to actual state (from cluster).
  4. If they differ, take action to converge (create/update/delete child resources).
  5. Update CR.status to reflect the current state.
  6. Requeue the request if not yet converged, or wait for the next event.
```

The reconcile loop is **level-triggered**, not edge-triggered. The operator doesn't react to "the spec changed"; it reacts to "the actual state doesn't match the desired state". This means:

- If the operator misses an event (e.g., network hiccup), the next reconcile still catches the drift.
- If the operator restarts, the reconcile loop on startup re-establishes the desired state.
- The operator is idempotent: running reconcile twice produces the same state.

This is in contrast to imperative scripts that react to events ("on update, do X"). Imperative scripts can miss events and leave the cluster in a bad state; reconcile loops are self-healing.

## The CRD

A Custom Resource Definition (CRD) extends Kubernetes with a new resource type. The operator's CRD:

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: postgresclusters.postgresql.example.com
spec:
  group: postgresql.example.com
  names:
    plural: postgresclusters
    singular: postgrescluster
    kind: PostgresCluster
    shortNames: [pgc]
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            required: [replicas, version]
            properties:
              replicas:
                type: integer
                minimum: 1
                maximum: 9
              version:
                type: string
                enum: ["15", "16", "17"]
              backup:
                type: object
                properties:
                  schedule:
                    type: string
                  retention:
                    type: string
          status:
            type: object
            properties:
              phase:
                type: string
                enum: [Running, Upgrading, Failed]
              currentPrimary:
                type: string
              lastBackup:
                type: string
                format: date-time
```

The schema is enforced by the API server; invalid CRs are rejected at admission time.

## Subresources: /scale and /status

A CRD can declare subresources that the controller updates:

- `/status`: a separate endpoint for the `status` field. Updating status via this endpoint doesn't trigger a reconcile loop (avoiding infinite loops).
- `/scale`: a separate endpoint that exposes a `Scale` subresource, allowing `kubectl scale postgrescluster prod-db --replicas=5` to work without editing the full CR.

```yaml
  versions:
  - name: v1
    subresources:
      status: {}
      scale:
        specReplicasPath: /spec/replicas
        statusReplicasPath: /status/replicas
```

## Finalizers

A finalizer is a list of strings in `metadata.finalizers` that prevents deletion of the CR until the operator has run cleanup:

```text
User: kubectl delete postgrescluster prod-db

API server: marks CR for deletion (DeletionTimestamp set), but does NOT delete.
  metadata.finalizers: [postgresql.example.com/cleanup]

Operator reconcile:
  - Sees DeletionTimestamp, runs cleanup (drops database, deletes backups, removes secrets)
  - Removes "postgresql.example.com/cleanup" from finalizers

API server: finalizers empty, deletes CR.
```

Finalizers are how operators ensure cleanup runs before Kubernetes garbage-collects the CR. Without a finalizer, the API server would delete the CR immediately, and the operator's cleanup might never run (e.g., if the operator was down at the time).

## Leader Election

A typical operator runs as a Deployment with 1 replica. If that replica fails, the operator restarts — but if both replicas happen to be alive (during a rolling restart), only one should be reconciling.

Kubernetes provides leader election via a `Lease` resource:

```go
leaderElectionConfig := leaderelection.LeaderElectionConfig{
    Lock: &resourcelock.LeaseLock{
        Client: clientset,
        LockName: "postgres-operator.example.com",
        Namespace: "operator-ns",
    },
    LeaseDuration: 15 * time.Second,
    RenewDeadline: 10 * time.Second,
    RetryPeriod: 2 * time.Second,
    Callbacks: leadereader.LeaderCallbacks{
        OnStartedLeading: func(ctx) { startReconciler(ctx) },
        OnStoppedLeading: func() { os.Exit(1) },
    },
}

leaderelection.RunOrDie(ctx, leaderElectionConfig)
```

The operator that wins the lease becomes the leader; others wait. If the leader fails (Lease isn't renewed for `RenewDeadline`), a new leader is elected.

## Common Operator Patterns

### Pattern 1: Stateful Application Operator

For databases (PostgreSQL, MySQL, MongoDB, Cassandra): the operator manages a StatefulSet, handles version upgrades, backups, and failover. Examples: CrunchyData Postgres operator, MongoDB operator, Cassandra operator.

### Pattern 2: Stream Processing Operator

For Kafka, NATS, RabbitMQ: the operator manages the broker cluster, topic lifecycle, and consumer groups. Examples: Strimzi Kafka operator, NATS operator.

### Pattern 3: CI/CD Operator

For Jenkins, Argo CD: the operator manages the build agent pool, the deployment pipeline, and the secrets for connecting to source control. Examples: Jenkins operator, Argo CD operator.

### Pattern 4: Machine Learning Operator

For Kubeflow, MLflow, JupyterHub: the operator manages training jobs, model deployments, and experiment tracking. Examples: Kubeflow TFJob operator, KServe operator.

## Operator Frameworks

Building an operator from scratch is significant work. Three frameworks reduce the boilerplate:

- **Operator Framework (CoreOS/Red Hat)**: Go-based, the original. Generates boilerplate via `operator-sdk new`.
- **Kubebuilder**: Go-based, the upstream for `controller-runtime`. Less opinionated than Operator Framework.
- **kopf (Python)**: Python-based, for operators that need Python's ecosystem (e.g., a Python ML library).

```bash
# Operator Framework: scaffold a new operator
operator-sdk init --domain example.com --repo=github.com/example/postgres-operator
operator-sdk create api --group postgresql --version v1 --kind PostgresCluster --resource --controller

# Kubebuilder: equivalent
kubebuilder init --domain example.com --repo=github.com/example/postgres-operator
kubebuilder create api --group postgresql --version v1 --kind PostgresCluster
```

## Operator Lifecycle Manager (OLM)

OLM is the package manager for operators, originally from CoreOS/Red Hat. It installs and upgrades operators from OperatorHub:

```bash
# Install an operator from OperatorHub
operator-sdk run bundle <operator bundle image>
```

OLM handles:
- Installing the CRD and the operator's Deployment.
- Managing operator upgrades (with semantic versioning).
- RBAC (the operator's service account and cluster roles).
- Dependency resolution (operators that depend on other operators).

OLM is bundled with OpenShift; on vanilla Kubernetes, it's an optional install.

## Common Pitfalls

1. **Reconcile loop not idempotent.** A reconcile that creates a child resource on every run (instead of checking if it exists first) creates duplicates. Always check-then-create.

2. **Status update triggering reconcile.** Updating the CR's status triggers a reconcile event. If the reconcile updates the status, you have an infinite loop. Update status only when it has changed.

3. **Long-running reconcile.** A reconcile that takes more than the lease duration (typically 15 seconds) loses leadership mid-run. Keep reconcile under 10 seconds; use worker queues for long tasks.

4. **Not handling the deletion timestamp.** An operator that ignores finalizers leaves orphaned resources (e.g., the database is gone but the operator's PVCs and Secrets remain).

5. **Trusting the spec without validating.** A CR with `spec.replicas=-1` or `spec.version="invalid"` may crash the operator. Validate at admission time (webhook) or in reconcile.

6. **Not testing upgrade paths.** An operator that works for installing fresh may fail on upgrade from version N-1 to N. Test the upgrade path in CI.

7. **Forgetting that the operator itself is stateful.** If the operator's Deployment is in the namespace it manages, deleting the namespace can delete the operator mid-cleanup. Use a separate operator namespace.

## References

- [Kubernetes: Operator pattern](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)
- [Operator Framework documentation](https://sdk.operatorframework.io/)
- [Kubebuilder book](https://book.kubebuilder.io/)
- [kopf (Python operator framework)](https://kopf.readthedocs.io/)
- [OperatorHub.io — operator catalog](https://operatorhub.io/)
- [OLM: Operator Lifecycle Manager](https://olm.operatorframework.io/)
- Brandon Phillips et al., "[Introducing Operators](https://coreos.com/blog/introducing-operators.html)" (CoreOS blog, 2016) — the original announcement
- [CrunchyData Postgres operator](https://github.com/CrunchyData/postgres-operator)
- [Strimzi Kafka operator](https://strimzi.io/)
