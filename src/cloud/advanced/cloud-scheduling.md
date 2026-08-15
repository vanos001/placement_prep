# Cloud Scheduling and Resource Optimization

## Cloud Scheduling Fundamentals

Cloud scheduling is the process of mapping workloads (pods, VMs, functions) to physical resources (machines, GPUs, network paths) while respecting constraints (CPU, memory, affinity, topology) and optimizing for objectives (utilization, latency, cost).

**Scheduling is an NP-hard bin-packing problem** in its general form. Real-world schedulers use heuristics that run in milliseconds rather than optimal algorithms that might take hours.

**Scheduling decision flow (Kubernetes default scheduler):**

```
Pending Pod
    │
    ▼
┌─────────────────────┐
│  Filtering Phase     │  (eliminate infeasible nodes)
│                      │
│  - Node resources    │
│    sufficient?       │
│  - Node selectors    │
│    match?            │
│  - Taint/toleration  │
│    satisfied?        │
│  - Pod affinity/     │
│    anti-affinity     │
│    satisfiable?      │
│  - Node affinity     │
│    satisfied?        │
└──────────┬──────────┘
           │ (feasible nodes remain)
           ▼
┌─────────────────────┐
│  Scoring Phase       │  (rank feasible nodes)
│                      │
│  - Resource fit      │
│    (least requested) │
│  - Node affinity     │
│    (prefer match)    │
│  - Pod affinity      │
│    (prefer co-loc)   │
│  - Image locality    │
│    (prefer cached)   │
│  - Taint toleration  │
│    (prefer fewer)    │
└──────────┬──────────┘
           │ (highest score wins)
           ▼
     Bind pod to node
```

The default K8s scheduler evaluates each pod independently (greedy). This can lead to suboptimal global placement — for example, placing all pods of a deployment on the same node because it has the most resources, rather than spreading them.

## Kubernetes Scheduler Deep Dive

### Scheduling Framework

The K8s scheduler is extensible via the **Scheduling Framework**, which defines a plugin architecture with these extension points:

| Extension Point | Called When | Example Plugins |
|----------------|------------|-----------------|
| **PreEnqueue** | Before adding to queue | Priority sorting |
| **QueueSort** | When ordering the queue | DefaultPrioritySort |
| **PreFilter** | Before filtering | NodeUnschedulable, GPUFit |
| **Filter** | During filtering | NodeResourcesFit, NodePorts, PodTopologySpread |
| **PostFilter** | After filtering fails | DefaultPreemption |
| **PreScore** | Before scoring | InterPodAffinity |
| **Score** | During scoring | NodeResourcesBalancedAllocation, ImageLocality, TaintToleration |
| **NormalizeScore** | After scoring | (normalize to 0–100 range) |
| **Reserve** | Before binding (resources reserved) | VolumeBinding |
| **Permit** | Before binding (can delay/allow/deny) | (custom admission control) |
| **PreBind** | Before API call to bind | VolumeBinding (attach volumes) |
| **Bind** | Bind pod to node | DefaultBinder |
| **PostBind** | After binding | (cleanup, metrics) |

### Pod Topology Spread

**Topology spread constraints** control how pods are distributed across failure domains (zones, nodes, racks). This is critical for high availability.

```yaml
# Example: Spread pods across zones
apiVersion: v1
kind: Pod
spec:
  topologySpreadConstraints:
  - maxSkew: 1                    # At most 1 more pod per zone than any other
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule  # Hard constraint
    labelSelector:
      matchLabels:
        app: web
```

**maxSkew: 1** with **3 zones** means if zone-a has 3 pods, zone-b and zone-c must each have at least 2 pods. This prevents all pods from landing in a single zone.

### Scheduling Gates

Scheduling gates (K8s 1.27+) allow pods to be marked as "not ready for scheduling" until external controllers remove the gate. This enables custom admission control patterns: a pod waits for a volume to be provisioned, or for a security policy check, before it's eligible for scheduling.

> **Interview Angle**: "How does the Kubernetes scheduler decide where to place a pod?" Walk through the two-phase process: (1) Filtering eliminates nodes that don't meet hard constraints (resources, taints, affinity), (2) Scoring ranks remaining nodes by soft preferences (resource balance, image locality, zone spread). The highest-scoring node wins. Mention that this is a greedy, per-pod algorithm — it doesn't do global optimization across all pending pods.

## Volcano Scheduler

The default K8s scheduler is designed for long-running services (web servers, APIs). It handles each pod independently and doesn't understand job-level semantics (e.g., "these 100 pods form a single training job and must all be scheduled together or not at all").

**Volcano** is a batch scheduling system for Kubernetes that addresses these gaps:

**Key features:**

1. **Gang scheduling (Queue-level co-scheduling)**: All pods in a job must be scheduled together, or none are scheduled. Prevents partial job deployment that wastes resources.

2. **Queue management**: Jobs are organized into queues with priorities and resource quotas. A high-priority queue can preempt jobs in a low-priority queue.

3. **Preemption with fairness**: When a high-priority job needs resources, Volcano can preempt lower-priority jobs. It selects victims that minimize disruption (e.g., preempt the job closest to completion first, or the one using the fewest resources).

4. **Task topology**: Define DAG dependencies between tasks in a job. Volcano ensures tasks are scheduled in topological order.

5. **Resource reservation**: When a node doesn't have enough resources for a pod, Volcano can "reserve" partial resources and wait for other pods on that node to finish, rather than immediately trying a different node.

``n
Volcano vs. Default K8s Scheduler:

| Feature | Default Scheduler | Volcano |
|---------|------------------|---------|
| Scheduling unit | Individual pod | Pod group / Job |
| Gang scheduling | No | Yes |
| Queue management | No | Yes (with priorities) |
| Preemption | Pod-level | Job/Queue-level |
| Task DAG | No | Yes |
| Resource reservation | No | Yes |
| Best for | Long-running services | Batch jobs, AI training |
```

Volcano is used by Huawei, Baidu, Tencent, and many Chinese cloud providers for AI training workloads on Kubernetes.

## Slurm vs. Kubernetes for AI/ML

Slurm and Kubernetes are the two dominant cluster managers, but they evolved for different communities:

| Dimension | Slurm | Kubernetes |
|-----------|-------|------------|
| Origin | HPC/supercomputing | Cloud-native/web services |
| Scheduling unit | Job (array of tasks) | Pod (container) |
| Native GPU support | Excellent (MIG, affinity, topology) | Good (device plugins, but add-on) |
| Job model | Batch: submit, run, exit | Services: long-running, auto-restart |
| Multi-tenant | Yes (partitions, QoS) | Yes (namespaces, resource quotas) |
| Elastic scaling | Limited | Excellent (cluster autoscaler, Karpenter) |
| Ecosystem | MPI, NCCL, InfiniBand tools | Helm, Istio, Prometheus |
| Learning curve | Steep (config files) | Moderate (YAML) |
| Fault tolerance | Checkpoint-restart | Self-healing (pod restart) |

**The trend**: Cloud-native ML platforms (Kubeflow, Ray on K8s, Flyte) use Kubernetes as the substrate. But for large-scale HPC training on bare-metal clusters, Slurm remains dominant (used by Meta, NVIDIA, most supercomputing centers). The convergence point: systems like **Kueue** (K8s native batch scheduler) and **Volcano** bring Slurm-like capabilities to Kubernetes.

## Cluster Autoscaling

### Kubernetes Cluster Autoscaler

The K8s Cluster Autoscaler (CA) adds nodes when pods are pending due to insufficient cluster resources and removes nodes when utilization is low. It operates at the node level — it doesn't add individual pods.

**CA scaling flow:**
1. CA monitors for unschedulable pods (pods stuck in `Pending` state after all scheduler attempts failed).
2. When detected, CA evaluates which node group to scale up.
3. CA provisions new node(s) via the cloud provider API.
4. New node registers with the K8s API server.
5. CA triggers the scheduler to retry pending pods on the new node.

**Scale-down flow:**
1. CA identifies underutilized nodes (resource usage below threshold, typically 50%).
2. CA checks if pods on the node can be migrated to other nodes.
3. CA cordons the node (marks unschedulable) and drains pods.
4. After all pods migrate, CA terminates the node.

### Karpenter (AWS) vs. Cluster Autoscaler

**Karpenter** is AWS's newer, faster node provisioner:

| Feature | Cluster Autoscaler | Karpenter |
|---------|-------------------|-----------|
| Provisioning speed | 1–5 minutes | 10–30 seconds |
| Instance type selection | Pre-configured node groups | Any instance type (provisioner-agnostic) |
| Node group model | Requires ASGs/MIGs | No node groups — direct instance launch |
| Consolidation | Basic (remove empty nodes) | Aggressive (replace with cheaper/larger) |
| Spot handling | Separate node group per type | Automatic spot diversification |
| Cloud provider | Multi-cloud | AWS-native (expanding) |

Karpenter's key advantage is **speed**. It provisions new instances in seconds by skipping the ASG/MIG abstraction and directly launching EC2 instances via the RunInstances API. For workloads with bursty traffic patterns (e.g., web services with diurnal patterns), Karpenter reduces the "underscaled" window from minutes to seconds.

## Predictive Autoscaling

Reactive autoscaling (scale up when at 80% CPU) always lags behind demand. By the time new instances are ready, the traffic spike may have already caused latency degradation.

**Predictive autoscaling** uses machine learning to forecast demand and pre-scale before the spike arrives:

``n
Reactive vs. Predictive Autoscaling:

  CPU %  ▲
         │         ╱╲ traffic spike
         │        ╱  ╲
         │       ╱    ╲
         │      ╱      ╲
         │     ╱        ╲
         │    ╱ Reactive: ╲
         │   ╱  scales HERE ╲
         │  ╱     (too late!) ╲
         │ ╱                    ╲
         │╱ Predictive:           ╲
         │ scales HERE (ready!)     ╲
         └──────────────────────────────► Time
            t-5min  t  t+2min  t+5min

  Reactive:  Detect at t+2min, provision at t+5min
  Predictive: Forecast at t-5min, provision at t-3min, ready at t
```

**AWS Predictive Scaling** analyzes historical traffic patterns (using built-in ML models) to generate load forecasts for the next 48 hours. You configure a pre-scaling buffer (e.g., "scale up 5 minutes before predicted peak").

**Custom predictive scaling**: More sophisticated systems train their own forecasting models (ARIMA, Prophet, LSTM) on application-specific metrics (request rate, queue depth, business events like scheduled batch jobs).

## Carbon-Aware and Energy-Aware Scheduling

Data centers consume 1–2% of global electricity. Cloud providers and enterprises are increasingly prioritizing carbon efficiency.

**Carbon-aware scheduling** shifts workloads to times and locations where the electrical grid has lower carbon intensity (more renewable energy):

``n
Carbon Intensity by Hour:

  gCO2/kWh ▲
            │    ╱╲    Solar peak
            │   ╱  ╲   (clean)
            │  ╱    ╲
            │ ╱      ╲
            │╱        ╲     Wind peak (night)
            │          ╲   ╱ (clean)
            │           ╲ ╱
            │    Gas      ╲╱
            │    peak
            │   (dirty)
            └──────────────────────► Hour
             6am  12pm  6pm  12am

  Strategy: Schedule batch jobs at noon (solar) or midnight (wind)
            Avoid scheduling at 6pm (gas peakers)
```

**Implementation approaches:**

1. **Time-shifting**: Delay flexible batch jobs (ML training, data processing) to hours with lower grid carbon intensity. Requires job deadlines and carbon intensity forecast APIs (e.g., ElectricityMaps, WattTime).

2. **Location-shifting**: Route workloads to data center regions powered by more renewable energy. Google uses this — it shifts compute between data centers based on real-time carbon intensity.

3. **Right-sizing**: Use smaller instances for low-utilization workloads. An m5.large running at 20% CPU is more carbon-efficient than an m5.xlarge running at 10% CPU (less idle power waste).

4. **Spot + carbon**: Spot instances often run on older, less efficient hardware. Balance cost savings against higher per-computation carbon emissions.

## FinOps and Cloud Cost Optimization

**FinOps** (Financial Operations) is the practice of bringing financial accountability to cloud spending. It's a cultural + technical discipline involving engineering, finance, and product teams.

### Key FinOps Strategies

**1. Right-sizing**: Analyze actual resource utilization (CPU, memory) and downsize over-provisioned instances. Tools: AWS Compute Optimizer, Kubecost.

**2. Reserved instances and savings plans**: Commit to 1–3 year usage for 30–60% savings. The risk: if workload changes, you're paying for unused capacity. Savings plans (AWS) provide flexibility — they apply across instance types, regions, and even services (EC2, Lambda, Fargate).

**3. Spot/preemptible instances**: 60–90% savings for fault-tolerant workloads (see previous section).

**4. Auto-stopping/dev environments**: Non-production environments should be shut down outside business hours. Tools: AWS Instance Scheduler, Togglebox.

**5. Storage tiering**: Move infrequently accessed data to cheaper storage classes (S3 Glacier, GCP Nearline). Implement lifecycle policies that automatically transition objects.

**6. Data transfer optimization**: Minimize cross-region and cross-AZ data transfer. Use compression, caching, and co-locating services that communicate frequently.

``n
FinOps Cost Reduction Hierarchy (biggest to smallest impact):

  1. Architecture changes      ─── 50–80% savings
     (serverless, spot, right-sizing)

  2. Commitment discounts      ─── 30–60% savings
     (Reserved Instances, Savings Plans)

  3. Workload optimization     ─── 10–30% savings
     (caching, query optimization, compression)

  4. Storage tiering           ─── 5–20% savings
     (lifecycle policies, archive)

  5. Network optimization      ─── 5–15% savings
     (VPC endpoints, compression, caching)
```

## Cloud Performance Isolation

### Noisy Neighbors

In shared cloud infrastructure, one tenant's workload can degrade another's performance. This "noisy neighbor" problem manifests at multiple levels:

- **CPU steal time**: The hypervisor allocates CPU time to another VM, causing your VM's vCPU to wait. Visible in `top` as `%st`. High steal time (>5%) indicates a noisy neighbor at the hypervisor level.
- **Memory bandwidth contention**: Multiple VMs on the same physical host compete for DRAM bandwidth. A memory-intensive neighbor can reduce your memory bandwidth by 30–50%.
- **Disk I/O contention**: Shared EBS volumes (on older generation instances) or shared EBS backend infrastructure can cause I/O latency spikes.
- **Network contention**: Oversubscribed NICs and switches cause packet loss and latency jitter.

### Mitigation Strategies

| Level | Strategy | Effectiveness |
-------|----------|---------------|
 | Hypervisor | Dedicated instances (no multi-tenancy) | Eliminates hypervisor-level noise |
 | Hypervisor | CPU pinning / dedicated vCPUs | Eliminates CPU steal |
 | Memory | Memory bandwidth QoS (Intel RDT/CAT) | Limits memory bandwidth per tenant |
 | Network | Network bandwidth limits (AWS vCPU → network BW mapping) | Prevents network hogging |
 | Storage | Provisioned IOPS (EBS io2) | Guarantees minimum I/O performance |
 | Application | Request rate limiting, circuit breakers | Application-level isolation |

**AWS dedicated instances/hosts** eliminate the noisy neighbor problem at the hypervisor level but cost ~30% more than shared instances. AWS Nitro System (their custom hypervisor) significantly reduces noisy neighbor impact by offloading I/O to dedicated hardware.

### Tenant Isolation

Multi-tenant cloud systems need isolation at multiple layers:

```
Isolation Layers (from hardware to application):

  ┌─────────────────────────────────┐
  │ Application Isolation            │  (per-tenant rate limits,
  │                                  │   resource quotas, RBAC)
  ├─────────────────────────────────┤
  │ Data Isolation                   │  (row-level security,
  │                                  │   encryption at rest)
  ├─────────────────────────────────┤
  │ Network Isolation                │  (VPC, network policies,
  │                                  │   service mesh mTLS)
  ├─────────────────────────────────┤
  │ Compute Isolation                │  (dedicated instances,
  │                                  │   confidential compute)
  ├─────────────────────────────────┤
  │ Physical Isolation               │  (dedicated hosts,
  │                                  │   bare metal, air-gap)
  └─────────────────────────────────┘
```

**Kubernetes multi-tenancy approaches:**

1. **Namespace-based isolation**: Each tenant gets a namespace with ResourceQuotas and LimitRanges. Lightweight but weak isolation — pods in different namespaces share the same node kernel.

2. **Node-based isolation**: Each tenant (or group of tenants) gets dedicated nodes via node selectors/taints. Stronger isolation but lower resource utilization.

3. **Virtual cluster (vCluster)**: Each tenant gets their own K8s control plane (API server, scheduler, controller manager) running as pods inside a shared host cluster. Strong logical isolation with good resource efficiency. The tenant sees a "full" K8s cluster but it's actually a namespace in the host cluster.

> **Interview Angle**: "How do you prevent one team's workload from degrading another's in a shared Kubernetes cluster?" Use namespace-based isolation with ResourceQuotas (hard limits) and LimitRanges (default resource requests/limits). Use PodPriority and PriorityClasses to ensure critical workloads aren't starved. For stronger isolation, use node pools with taints so each team has dedicated nodes. Monitor for noisy neighbor signals (CPU throttling, network latency spikes) using Prometheus metrics.

## Key Takeaways

1. **K8s scheduling is greedy and per-pod** — it doesn't do global optimization. Volcano adds job-level, gang, and queue-based scheduling for batch/AI workloads.
2. **Karpenter is 5–10x faster than Cluster Autoscaler** because it bypasses the ASG abstraction and directly provisions instances.
3. **Predictive autoscaling eliminates the reactive lag** — forecast demand and pre-scale before spikes arrive.
4. **Carbon-aware scheduling is becoming a requirement** — EU regulations and corporate sustainability goals are driving workload time-shifting and location-shifting.
5. **FinOps is a cultural practice, not just a tool** — the biggest savings come from architectural changes, not just reserved instances.
6. **Noisy neighbors are real but mitigable** — dedicated instances, Nitro, and resource QoS (Intel RDT) address isolation at different layers.
