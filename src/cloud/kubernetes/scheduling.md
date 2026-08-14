# Kubernetes Scheduling Deep Dive

## Scheduler Architecture

The kube-scheduler is a control plane component responsible for assigning newly created Pods to nodes. It watches the API server for Pods with no `nodeName` assigned and makes placement decisions through a well-defined pipeline.

The scheduler runs as a single active instance (leader-elected) and does NOT place containers directly—it writes the `nodeName` field to the Pod spec via the API server, and the target node's kubelet handles the actual container creation.

## Scheduling Cycle

```
Unscheduled Pod
    │
    ▼
┌─────────────────────┐
│  Scheduling Queue    │  Pods waiting to be scheduled (priority sorted)
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Filtering Phase     │  Eliminate infeasible nodes
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Scoring Phase       │  Rank feasible nodes
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Binding Phase       │  Write nodeName to Pod spec
└─────────────────────┘
```

### Filtering Phase

Each registered filter plugin evaluates every node. If ANY plugin rejects a node, it is removed from candidacy. Default filters include:

| Filter | Purpose |
|--------|---------|
| `NodeUnschedulable` | Skip nodes with `Unschedulable: true` (cordoned) |
| `NodeResourcesFit` | Check CPU/memory requests fit within allocatable resources |
| `NodePort` | Ensure required NodePorts are available |
| `NodeAffinity` | Match node labels against required affinity rules |
| `TaintToleration` | Pod must tolerate all node taints |
| `PodTopologySpread` | Check topology constraints (zone, rack) |
| `VolumeBinding` | Ensure PVCs can be bound (or are already bound) |
| `InterPodAffinity` | Check pod-to-pod affinity/anti-affinity rules |

### Scoring Phase

Feasible nodes are scored by each scoring plugin. Scores are normalized and summed. Default scorers:

| Scorer | Weight | Logic |
|--------|--------|-------|
| `NodeResourcesFit` | 1 | Least requested resource allocation wins |
| `NodeAffinity` | 1 | Prefer matching preferred affinity terms |
| `InterPodAffinity` | 1 | Prefer nodes satisfying pod affinity |
| `ImageLocality` | 1 | Prefer nodes that already have the image |
| `TaintToleration` | 1 | Prefer fewer taints on the node |

The node with the highest total score is selected. Ties are broken randomly.

## Taints and Tolerations

Taints are applied to nodes to repel pods; tolerations are applied to pods to absorb taints.

```bash
# Add a taint to a node
kubectl taint nodes node1 dedicated=gpu:NoSchedule

# Pod spec with toleration
tolerations:
  - key: "dedicated"
    operator: "Equal"
    value: "gpu"
    effect: "NoSchedule"
```

| Taint Effect | Behavior |
|--------------|----------|
| `NoSchedule` | Pod not scheduled unless it tolerates the taint |
| `PreferNoSchedule` | Scheduler tries to avoid; soft constraint |
| `NoExecute` | New pods not scheduled; existing pods are evicted if they don't tolerate |

Built-in taints (automatically applied by controllers):
- `node.kubernetes.io/not-ready` — Node not ready (kubelet unhealthy)
- `node.kubernetes.io/unreachable` — Node unreachable from control plane
- `node.kubernetes.io/memory-pressure` — Node under memory pressure
- `node.kubernetes.io/disk-pressure` — Node under disk pressure

## Node Affinity and Pod Affinity

### Node Affinity

Constrains pod scheduling based on node labels. Two types:

```yaml
# Required (hard constraint) - must match
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
        - matchExpressions:
            - key: topology.kubernetes.io/zone
              operator: In
              values: ["us-east-1a", "us-east-1b"]

# Preferred (soft constraint) - scheduler tries to satisfy
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 80
        preference:
          matchExpressions:
            - key: node-type
              operator: In
              values: ["high-memory"]
```

### Pod Affinity / Anti-Affinity

Constrains scheduling based on labels of already-running pods:

```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app: web
        topologyKey: topology.kubernetes.io/zone
    # Ensures web pods spread across zones
```

| Affinity Type | Schedules Based On | Use Case |
|---------------|-------------------|----------|
| Node Affinity | Node labels | Zone/rack placement, GPU nodes |
| Pod Affinity | Labels of running pods | Co-locate cache with app |
| Pod Anti-Affinity | Labels of running pods | Spread replicas across failure domains |

## Pod Topology Spread Constraints

Topology spread constraints provide more predictable spreading than anti-affinity. They enforce max skew across topology domains.

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule  # hard constraint
    labelSelector:
      matchLabels:
        app: api
  - maxSkew: 2
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: ScheduleAnyway  # soft constraint (best-effort)
    labelSelector:
      matchLabels:
        app: api
```

**Max skew** is the difference between the number of pods on any two topology domains. With `maxSkew: 1` and 5 pods across 3 zones, the distribution would be 2-2-1 (max diff = 1), never 3-1-1.

## Resource Requests and Limits

```yaml
resources:
  requests:        # Used by scheduler for placement decisions
    cpu: "250m"     # 0.25 CPU cores
    memory: "256Mi"
  limits:          # Enforced by kubelet (hard cap)
    cpu: "500m"     # Throttled if exceeded
    memory: "512Mi" # OOMKilled if exceeded
```

| Aspect | requests | limits |
|--------|----------|--------|
| **Used by** | Scheduler (filtering) | kubelet (enforcement) |
| **CPU behavior** | Guaranteed minimum | CFS quota throttling |
| **Memory behavior** | Minimum guaranteed | OOMKill if exceeded |
| **Quality of Service** | Burstable if set | — |

QoS Classes (derived from requests/limits):

| QoS Class | Condition | Eviction Priority |
|-----------|-----------|-------------------|
| Guaranteed | requests == limits for CPU and memory | Last to be evicted |
| Burstable | requests < limits, or only requests set | Medium priority |
| BestEffort | Neither requests nor limits set | First to be evicted |

## Scheduler Plugins

The scheduler uses a plugin architecture (since v1.19) with extension points:

| Extension Point | When It Runs | Purpose |
|----------------|-------------|---------|
| `PreFilter` | Before filtering | Pre-compute state, early rejection |
| `Filter` | Filtering phase | Eliminate infeasible nodes |
| `PostFilter` | After filtering | Handle no feasible nodes (e.g., preemption) |
| `PreScore` | Before scoring | Pre-compute scoring state |
| `Score` | Scoring phase | Rank nodes |
| `NormalizeScore` | After scoring | Normalize scores across plugins |
| `Reserve` | Before binding | Reserve resources (reduce double-scheduling) |
| `Permit` | Before binding | Approve/deny/delay binding |
| `PreBind` | Before binding | Execute pre-bind actions (e.g., volume provisioning) |
| `Bind` | Binding | Actually bind pod to node |
| `PostBind` | After binding | Cleanup, logging |

## Custom Schedulers

Run a second scheduler alongside the default one:

```yaml
apiVersion: kubescheduler.config.k8s.io/v1beta3
kind: KubeSchedulerConfiguration
clientConnection:
  kubeconfig: /etc/kubernetes/scheduler.conf
profiles:
  - schedulerName: my-custom-scheduler
    plugins:
      # Enable/disable/override plugins
```

Target pods at your custom scheduler:

```yaml
spec:
  schedulerName: my-custom-scheduler
```

Use cases for custom schedulers: GPU bin-packing, cost-aware scheduling, latency-sensitive workloads, gang scheduling (Volcano), topology-aware scheduling.

## References

- [Kubernetes Scheduler Documentation](https://kubernetes.io/docs/concepts/scheduling-eviction/)
- [Scheduler Framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduler-framework/)
- [Topology Spread Constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)

## Interview Questions

### Q1: How does the Kubernetes scheduler decide where to place a pod?
**Answer**: The scheduler runs a two-phase process. **Filtering** eliminates infeasible nodes (insufficient resources, taints not tolerated, node affinity mismatch, volume binding failure). **Scoring** ranks the remaining nodes using multiple plugins (resource fit, affinity, image locality). The highest-scoring node wins. Ties are broken randomly. The scheduler writes `nodeName` to the Pod spec—it never talks to kubelet directly.

### Q2: What is the difference between node affinity and pod anti-affinity?
**Answer**: Node affinity constrains scheduling based on node labels (e.g., schedule on nodes in `us-east-1a` or on GPU nodes). Pod anti-affinity constrains scheduling based on labels of already-running pods (e.g., don't schedule two replicas of the same app on the same node). Node affinity answers "where should this pod go?" Pod anti-affinity answers "where should this pod NOT go relative to other pods?"

### Q3: What happens when a pod exceeds its memory limit?
**Answer**: The container is **OOMKilled** by the kernel's OOM killer. The container is terminated with exit code 137. If the pod has a restart policy of `Always` or `OnFailure`, kubelet recreates it. CPU limits work differently—exceeding CPU limits causes **throttling** (CFS quota), not termination. This asymmetry is a common interview trap.

### Q4: Explain topology spread constraints vs. pod anti-affinity.
**Answer**: Topology spread constraints enforce a maximum skew (difference) in pod count across topology domains (zones, nodes). They give predictable, balanced distribution. Pod anti-affinity prevents scheduling if any matching pod already exists on a node/zone, which can lead to scheduling failures as the cluster fills. Topology spread is generally preferred for production because it's more flexible and provides better utilization while still ensuring spread.

### Q5: When would you use a custom scheduler?
**Answer**: Use a custom scheduler when the default scheduler's decisions are suboptimal for specialized workloads. Examples: GPU workloads needing bin-packing (pack GPU pods tightly to leave room for non-GPU work), gang scheduling (all pods of a job must start together, e.g., Spark, MPI via Volcano), cost-aware scheduling (prefer spot/preemptible instances), or latency-sensitive workloads that need NUMA-aware placement. You specify `schedulerName` in the pod spec to target the custom scheduler.
