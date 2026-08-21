# Kubernetes Controller-Manager

The Kubernetes controller-manager (formally `kube-controller-manager`) is a binary that runs the cluster's "controllers" — the reconciliation loops that drive the cluster toward a desired state. Each controller watches the API server for changes to resources (pods, deployments, services, etc.) and takes action to converge the cluster's actual state with the desired state. This page covers the architecture, the controller pattern, the major built-in controllers, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Controller Manager (single process, HA via leader election)│
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Controllers (each is a reconciliation loop)             │ │
│  │  - ReplicaSet controller                                  │ │
│  │  - Deployment controller                                  │ │
│  │  - Node controller                                       │ │
│  │  - Service controller                                     │ │
│  │  - EndpointSlice controller                              │ │
│  │  - Job controller                                        │ │
│  │  - CronJob controller                                     │ │
│  │  - DaemonSet controller                                   │ │
│  │  - StatefulSet controller                                 │ │
│  │  - ServiceAccount controller                              │ │
│  │  - ResourceQuota controller                              │ │
│  │  - Namespace controller                                   │ │
│  │  - ... (~30 controllers)                                  │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Shared Informer Factory                                  │ │
│  │  - Watches API server for resource changes              │ │
│  │  - Distributes events to controllers                     │ │
│  │  - Caches resource state locally (avoid repeated reads) │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
        │                              │
        │ watch/list API              │ leader election via leases
        ▼                              ▼
    API server                      etcd (or Lease resources)
```

The controller-manager runs as a single process; for HA, multiple replicas run, but only the elected leader actively controls.

## The Controller Pattern

Every controller follows the same pattern:

```go
for {
    desiredState := getDesiredState()  // e.g., "I want 3 replicas of this Deployment"
    actualState := getActualState()    // e.g., "I see 2 running pods"
    if actualState != desiredState {
        takeAction(desiredState, actualState)  // e.g., create 1 more pod
    }
    // wait for the next event or periodic resync
}
```

This is the "reconciliation loop" — the controller constantly compares desired vs. actual and takes action to converge. The loop is **level-triggered** (idempotent — running twice produces the same state), not edge-triggered (reacts to events).

## The Major Controllers

### ReplicaSet Controller

Watches ReplicaSets. For each ReplicaSet, ensures N pods exist (where N is `spec.replicas`). If fewer pods than desired, creates new pods. If more, deletes extras.

```text
ReplicaSet says: replicas=3.
Actual state: 2 pods running.
→ Controller creates 1 pod.

Actual state: 4 pods running (after manual scale-up).
→ Controller deletes 1 pod.
```

### Deployment Controller

Watches Deployments. A Deployment wraps a ReplicaSet; when the Deployment's spec changes (e.g., new image), the controller creates a new ReplicaSet and gradually scales it up while scaling the old ReplicaSet down.

```text
Deployment: image=v1 (current), replicas=3
User changes to: image=v2
→ Controller creates new ReplicaSet with image=v2 (replicas=0)
→ Controller scales new ReplicaSet to 1, old ReplicaSet to 2 (1/3 progress)
→ Controller scales new ReplicaSet to 2, old ReplicaSet to 1
→ Controller scales new ReplicaSet to 3, old ReplicaSet to 0 (rollback target)
```

This is the "rolling update" — zero-downtime pod replacement.

### Node Controller

Watches Nodes. If a Node stops reporting (heartbeats stop), the controller marks the Node as `NotReady` after 40 seconds (default), then evicts pods after 5 minutes (`pod-eviction-timeout`).

```text
Node N stops sending heartbeats.
→ 0-40 seconds: status is "Unknown".
→ 40-300 seconds: status is "NotReady"; pods are scheduled to be evicted.
→ 300+ seconds: pods on N are evicted (deleted), rescheduled elsewhere.
```

This is the basis for handling node failures — pods on a dead node are rescheduled automatically.

### Service Controller

Watches Services. For each Service of type `LoadBalancer`, the controller provisions a cloud load balancer (ELB, GLB, etc.) and configures it to route traffic to the service's pods.

For type `ClusterIP`, no cloud interaction — just creates an in-cluster IP.

For type `NodePort`, opens a port (default 30000-32767) on all nodes.

### EndpointSlice Controller

Watches Services and Pods. For each Service, the controller maintains an "EndpointSlice" listing the pod IPs that the Service should route to.

```text
Service "myapp" (selector: app=myapp)
Pods with label app=myapp:
  - pod-1 (10.0.0.1)
  - pod-2 (10.0.0.2)
  - pod-3 (10.0.0.3)

→ EndpointSlice contains [10.0.0.1, 10.0.0.2, 10.0.0.3]
→ kube-proxy programs iptables/IPVS to route "myapp" service IP to these pods.
```

When pods are added/deleted, the EndpointSlice controller updates the list, and kube-proxy updates the routing.

### Job Controller

Watches Jobs. A Job runs N pods to completion; the controller ensures all N pods complete successfully (with retries).

### CronJob Controller

Watches CronJobs. At the scheduled time, the controller creates a Job (which the Job controller then handles).

### DaemonSet Controller

Watches DaemonSets. A DaemonSet ensures one pod runs on every node (or a subset, by node selector). The controller creates pods on new nodes as they join the cluster.

### StatefulSet Controller

Watches StatefulSets. A StatefulSet runs N pods with stable identities (pod-0, pod-1, ...) and stable persistent volumes. The controller creates pods sequentially (pod-0 first, then pod-1, etc.), ensuring order.

## The Informer Pattern

The Shared Informer Factory is the controller's connection to the API server:

```go
informer := informers.NewSharedInformerFactory(client, 30*time.Second)
podInformer := informer.Core().V1().Pods().Informer()
podInformer.AddEventHandler(cache.ResourceEventHandlerFuncs{
    AddFunc: func(obj interface{}) {
        // pod was added
    },
    UpdateFunc: func(old, new interface{}) {
        // pod was updated
    },
    DeleteFunc: func(obj interface{}) {
        // pod was deleted
    },
})
podInformer.Run(stopCh)
```

The informer:
1. Lists all resources of a type (initial).
2. Watches for changes (subscribe to API server's watch endpoint).
3. Maintains a local cache of the resources (so controllers don't read from API server).
4. Distributes events to handlers.

The cache avoids overwhelming the API server with reads. Controllers read from the local cache, which is always eventually consistent.

## Leader Election

Multiple controller-manager replicas run for HA. Only one is the "leader"; the others are standbys.

```text
1. Replicas compete for a "Lease" resource (kube-system/kube-controller-manager).
2. The winner (first to acquire) becomes the leader.
3. The leader renews the lease every 2 seconds (default).
4. If the leader fails (lease not renewed), a new election starts.
5. The new leader takes over.
```

During the leader transition, no controllers run — there's a brief outage (~10 seconds). For most controllers, this is acceptable (reconciliation is idempotent and resumes).

## Production Deployment

The controller-manager is typically deployed as a static pod on master nodes (along with the API server and etcd). For HA clusters, multiple master nodes each run a controller-manager; leader election ensures only one is active.

```bash
# /etc/kubernetes/manifests/kube-controller-manager.yaml (static pod)
apiVersion: v1
kind: Pod
metadata:
  name: kube-controller-manager
  namespace: kube-system
spec:
  containers:
    - name: kube-controller-manager
      image: registry.k8s.io/kube-controller-manager:v1.28
      command:
        - kube-controller-manager
        - --allocate-node-cidrs=true
        - --cluster-cidr=10.244.0.0/16
        - --leader-elect=true
        - --v=2
```

## Production Performance

Controller-manager's typical performance on a 100-node cluster:
- CPU: 5-10% of one core.
- Memory: 200-500 MB.
- Reconciliation latency: <1 second (event-driven) to 30 seconds (periodic).

For larger clusters (1000+ nodes), the controller-manager needs more resources; consider sharding (running multiple controller-managers, each handling a subset of resources).

## Common Pitfalls

1. **Forgetting that controllers are level-triggered.** A controller that fires on every event may double-process; the level-triggered design (compare desired vs. actual each time) is safer.

2. **Forgetting that informers cache everything.** A controller that watches all pods uses significant memory (10K pods × 5 KB each = 50 MB). Use a label selector to filter.

3. **Forgetting that leader election has a failover delay.** A 10-second gap during failover may cause issues for high-frequency reconciliation. Tune `--leader-elect-renew-deadline`.

4. **Forgetting that controllers don't handle errors with retries.** A controller that fails to create a pod (e.g., quota exceeded) doesn't retry — the pod stays in "pending" until the next event triggers reconciliation. The user must investigate.

5. **Forgetting that the Node controller evicts pods after 5 minutes.** A flapping node can cause unwanted evictions; tune `--pod-eviction-timeout`.

6. **Forgetting that the EndpointSlice controller is critical for services.** If it's down, new pods aren't added to services; traffic stops. Monitor controller-manager health.

## References

- [Kubernetes: kube-controller-manager](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/)
- [Kubernetes: Controller pattern](https://kubernetes.io/docs/concepts/architecture/controller/)
- [Kubernetes: Custom Controllers](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/)
- [Client-go: Informers](https://github.com/kubernetes/client-go/blob/master/informers/)
- [Kubernetes Controller-Manager flags](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/)
- [Operator SDK (extends controller pattern for custom resources)](https://sdk.operatorframework.io/)
- [LWN: Kubernetes controllers (2020)](https://lwn.net/Articles/815575/)
