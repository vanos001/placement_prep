# Follow-up Tree: Kubernetes Scheduling

## Overview

"How does the Kubernetes scheduler decide where a pod runs?" is the opening question that separates candidates who have operated Kubernetes from candidates who have deployed to it, because the rehearsed answer — "the scheduler picks a node" — hides a two-phase optimization problem, a resource-accounting model, and a set of failure modes that every capacity incident eventually touches. The ladder here runs from the scheduling pipeline (filter, then score, then bind) through the requests-and-limits accounting that decides whether the cluster is real or fiction, into preemption and priority — where the scheduler becomes an eviction engine — and ends at the design judgment between bin-packing and spreading that every platform team argues about. The thread tying every rung together is *the cluster as a queue of pods competing for resources the scheduler must price*: each follow-up asks either how a node is scored, what a request actually reserves, or who gets evicted when the model was wrong. This chain deliberately stops where the pod's life on the node begins — [Kubernetes Pod Lifecycle](./kubernetes-pod-lifecycle.md) owns kubelet, probes, and termination — and the cgroup mechanics under the resource model live in [Containers, cgroups & Namespaces](../connection-atlas/containers-cgroups-namespaces.md). The book-level reference is [Scheduling](../../cloud/kubernetes/scheduling.md); the official scheduler and preemption pages ([kube-scheduler](https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/), [Pod Priority and Preemption](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)) are the primary sources every answer here paraphrases. Each level states what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates.

## The Opening Question

**"You `kubectl apply` a Deployment. How does a pod end up on a specific node?"**

The expected core answer: the Deployment controller creates a ReplicaSet, which creates Pod objects with `spec.nodeName` unset; these land in the API server's scheduling queue, where the kube-scheduler — a separate control-plane loop — watches for unscheduled pods and, per pod, runs a two-phase decision: *filtering*, which eliminates nodes that cannot legally host the pod (insufficient free CPU/memory after requests, taints without matching tolerations, failed affinity or anti-affinity, port conflicts), then *scoring*, which ranks the surviving nodes with weights (least-requested resources, image locality, topology spread, balanced resource usage); the highest-scoring node wins, and the scheduler writes the binding back to the API server — the kubelet on that node, watching the pod, then starts containers. If no node passes filtering, the pod sits `Pending` with a reason recorded in its events.

A weak answer says "the control plane assigns it to a node" or confuses the scheduler with the kubelet. The strong answer names both phases, states that scheduling is per-pod and asynchronous rather than a batch layout, and volunteers the queue detail: unschedulable pods back off and retry in a separate queue, which is why a Pending pod can start moving minutes after capacity appears. The follow-up that escalates: **"When the scheduler computes 'insufficient CPU,' what number is it comparing, and where did that number come from?"** — which moves the ladder from pipeline to resource model.

## Level 2: The Filter-then-Score Pipeline

**What it tests:** whether the two phases are decomposable mechanisms with names, weights, and extension points — or one blur called "scheduling."

**Weak answer:** "It checks if the node has enough resources and picks one" — no filtering/scoring distinction, no idea that predicates have hard-fail semantics while scores are soft preferences, no awareness that the pipeline is pluggable.

**Strong answer:** names the framework: filters are hard constraints with binary pass/fail (resource fit, taint/toleration, node affinity, pod anti-affinity, topology constraints), scores are soft preferences summed with configurable weights (LeastAllocated, BalancedAllocation, ImageLocality, pod-topology-spread scoring), and plugins compose in a profile — this is the Scheduling Framework, and custom placement policy is a plugin, not a fork.

**Escalation trigger:** "Two nodes pass filtering for every pod. What decides which one wins, and why does that choice matter more at 10,000 pods than at 10?"

**Answer.** The scoring function *is* the cluster's resource-policy statement. LeastAllocated spreads load — it prefers emptier nodes, which lowers per-node contention and blast radius but leaves half-empty nodes everywhere (higher cost, worse headroom utilization at the fleet edge). Its sibling, MostAllocated/bin-packing, prefers fuller nodes to shrink the fleet and cut cost, at the price of concentrating tenants and enlarging the failure domain of any node loss. BalancedAllocation avoids skew where one resource is nearly exhausted while the other idles, because skew blocks future pods that need the fuller resource. At 10 pods the choice is invisible; at 10,000 pods the score function decides whether a 5% demand increase needs new nodes, whether node failures strand whole categories of pods, and whether daily rescheduling churn (descheduler work) is constant. The senior detail is that scoring is per-pod greedy: the scheduler optimizes each pod against the current snapshot, not the whole batch, so a wave of 500 replicas can pack differently than 500 individual decisions would suggest — and the framework's snapshot semantics (the queue takes a node snapshot per scheduling cycle) is the precise reason two identical pods in the same wave can land on different nodes.

The design twist the strong candidate volunteers: *node order in the queue is not pod order in importance* — priority classes feed a preemption path that re-enters filtering with eviction rights, which is the next rung. The follow-up that escalates: **"A pod's containers sum to 'requests.' What is each of those numbers actually enforcing, and what happens when reality ignores them?"**

## Level 3: Requests, Limits, and the QoS Contract

**What it tests:** whether requests/limits are a two-number contract you can trace to kernel enforcement — cgroups, OOM, throttling — or a YAML incantation.

**Weak answer:** "Requests are minimums and limits are maximums" — no account of what the scheduler does with requests, what the kubelet does with limits, or why a container with a memory limit gets OOM-killed at the limit.

**Strong answer:** states that *requests* are the scheduler's accounting units — the pod is placed as if it permanently occupies them, and node "allocatable" (capacity minus kubelet/system reservations minus eviction thresholds) is the budget they draw down; *limits* are runtime enforcement the kubelet applies via cgroups — CPU limits cause throttling (CFS bandwidth control), memory limits define the cgroup boundary beyond which the OOM killer fires. QoS classes fall out of the combination: Guaranteed (requests == limits for every container), Burstable, BestEffort (no requests at all) — and they order the eviction queue under node pressure.

**Escalation trigger:** "A team sets memory requests to 100 MiB with a 4 GiB limit for every service. What breaks, and when?"

**Answer.** The scheduler packs nodes believing each pod needs 100 MiB, so nodes fill to near capacity on paper while actual usage runs at multiples of the request — the cluster is overcommitted, and the failure arrives as memory pressure the scheduler never priced. The sequence: node memory climbs, the kubelet's eviction thresholds trip, and eviction begins — ordered by actual-usage-minus-request (pods using far more than requested are evicted first) with QoS as the tie-breaker, so BestEffort and loose-Burstable pods die while the node recovers. If pressure outruns eviction, the OOM killer terminates at the cgroup level. The insidious part earns the rung: every individual service "worked" in isolation; the failure is the *sum* of honest-looking per-service numbers, which is why capacity reviews audit the request-to-usage ratio fleet-wide rather than each service's YAML. CPU has a softer version: request below usage steals scheduling time from neighbors (noisy neighbor, visible as throttling when CPU limits are set), while setting CPU *limits* equal to usage on bursty services converts spare node capacity from gift to throttle — the reason many operators set CPU requests without limits and manage memory strictly. The general lesson — containers do not contain what cgroups do not enforce — is the atlas map [Containers, cgroups & Namespaces](../connection-atlas/containers-cgroups-namespaces.md), and the assumption audit ("requests are accurate," "usage is smooth") is [Containers and Resources](../assumptions-hunt/containers-and-resources.md).

The design twist: *right-sizing is a measurement program, not a YAML edit* — VPA-style recommendations or a utilization dashboard against requests, tuned so that requests track real usage while limits keep worst cases survivable. The follow-up that escalates: **"A critical pod is Pending because lower-priority pods filled the cluster. What does the scheduler actually do?"**

## Level 4: Priority, Preemption, and the Cost of Guarantees

**What it tests:** the expert rung — preemption as an eviction algorithm (victims, disruption budgets, priority floodgates), plus topology spread and the Pending-pod diagnosis path that ties the whole ladder together.

**Weak answer:** "Higher priority pods kick out lower priority pods" — no victim-selection semantics, no PodDisruptionBudget interaction, no awareness that preemption can cascade or that priority can starve batch workloads by design.

**Strong answer:** explains PriorityClass as a cluster-wide integer order; preemption as a second pass — when a pod cannot filter anywhere, the scheduler finds nodes where evicting a *lower-priority* victim set would make room, respecting PodDisruptionBudgets and graceful termination, then posts preemption victims and retries; and states the floodgate consequence: without discipline, urgent workloads accrete priority until everything is urgent and preemption storms churn the cluster.

**Escalation trigger:** "Design the capacity policy for a cluster running latency-critical APIs, nightly batch jobs, and experiments. What precedence do you encode, and where do you expect it to hurt?"

**Answer.** The policy is a priority lattice plus topology rules: system and latency-critical API workloads take high priority with Guaranteed-ish requests; batch jobs take low priority and are *expected* to be preempted — their contract is checkpointability, not protection; experiments run BestEffort as the cluster's elastic buffer. Topology spread constraints and pod anti-affinity then prevent the lattice from defeating itself — a high-priority service must not concentrate all replicas on one zone, so spread constraints act as scheduling-side fault isolation with a max-skew parameter. The places it hurts, named honestly: preemption waves (one high-priority scale-out evicts a wave of batch pods that retry, re-queue, and compete again — visible as batch throughput collapse), PDB-protected victims that block preemption entirely (the scheduler marks the pod unschedulable rather than violate the budget, so the "critical" pod stays Pending despite technically-preemptable nodes), and the cluster-autoscaler interplay — Pending pods trigger scale-up, but scale-up latency means the preemption decision already ran, so mixing autoscaling with aggressive preemption requires sequencing. The diagnosis path that closes the loop uses every rung: Pending → read events (filtering failed on what?) → check requests against allocatable (rung 3's accounting) → check taints/affinity/spread (rung 2's filters) → check preemption outcomes and PDBs (this rung).

## How to Approach Unfamiliar Variations

The template for scheduling variations — "batch and serving on one cluster," "GPU nodes are 8x the cost," "the scheduler adds 2 seconds at 50 pods/second":

1. **Reduce the variation to a constraint-vs-score question.** Anything that must always hold (zone spread, GPU affinity, license limits) belongs in filtering; anything that is a preference (cost, balance, locality) belongs in scoring weights. Misplacing a hard requirement into scoring is the classic bug.
2. **Answer capacity questions in the scheduler's units.** Requests vs allocatable vs usage — three different numbers; state which one each actor (scheduler, kubelet, autoscaler) reads, and the incident explains itself.
3. **Treat priority as a global economy.** Every priority assignment changes eviction outcomes cluster-wide; the question "who absorbs the burst" must have a named answer (usually: a designated low-priority elastic class), or preemption will find one by accident.
4. **Price guarantees before promising them.** Guaranteed QoS, PDBs, and dedicated node pools all convert variance into cost; say what you would measure (request-to-usage ratio, preemption rate, Pending duration) to tune each.

## Interview Questions

**Q: A pod has been Pending for an hour. Walk through the diagnosis.**
A: Read `kubectl describe pod` events, which name the failing filter. Most cases: requests exceed allocatable on every node (check the arithmetic, including per-pod overhead), or a taint/affinity/topology constraint excludes nodes. If events mention preemption: check PodDisruptionBudgets blocking victims. If nothing obviously fails: check whether the pod is in the unschedulable queue waiting for capacity (cluster autoscaler events) — the event history distinguishes "no node fits" from "no attempt yet."

**Q: Why can a node with "3 GB free memory" fail to schedule a pod requesting 3 GB?**
A: "Free" is not the scheduler's number. The scheduler compares pod requests against *allocatable* minus the sum of *requests* of existing pods — including system-reserved accounting and per-pod overheads a `free`-style view ignores. DaemonSets and eviction thresholds also carve out capacity. The gap between observed free memory and schedulable headroom is exactly why the request model exists.

**Q: Your platform team wants to cut cost by bin-packing harder. What do you monitor, and what is the first failure you expect?**
A: Watch request-to-usage ratio per node, node memory pressure and eviction events, and post-eviction restart latency. First failure: overcommitted nodes enter kubelet eviction under memory spikes, evicting pods whose requests understated usage — concentrated tenants mean bigger blast radius per node loss. Mitigate with accurate right-sizing, keep headroom for node drain, and let failure-domain rules (spread constraints) cap how much packing any single node absorbs.

**Q: What does the scheduler do when a high-priority pod can only fit if several PDB-protected pods are evicted?**
A: It will not violate the disruption budget: preemption selects victims among lower-priority pods, but PDB-protected ones are excluded, and if no viable victim set exists the scheduler leaves the pod Pending (or marks preemption as not helpful) and retries. The correct fix is policy-level — a reserved capacity pool, a revised PDB, or lower priority elsewhere — not expecting the scheduler to break the budget, since the PDB is precisely the contract that says "these evictions need a human."

## Key Takeaways

- Scheduling is filter-then-score-then-bind: hard constraints eliminate, soft scores rank, and the score weights are the cluster's de facto resource policy.
- Requests are the scheduler's accounting truth; limits are the kubelet's cgroup enforcement — conflating them is the root of most overcommit incidents.
- QoS classes and usage-versus-request gap order evictions under pressure; overcommit fails as a sum of individually reasonable YAML.
- Preemption is an eviction algorithm with victims, budgets, and cascade risks — priority needs a designated elastic class or it will invent one.
- Pending-pod diagnosis is the ladder in miniature: read the failed filter, then the resource accounting, then the preemption path.

## Cross-References

- [Kubernetes Pod Lifecycle](./kubernetes-pod-lifecycle.md) — the chain that owns what happens after binding: kubelet, probes, termination, and shutdown contracts.
- [Containers and Resources](../assumptions-hunt/containers-and-resources.md) — the assumption audit behind requests, limits, and "the container is the machine."
- [Containers, cgroups & Namespaces](../connection-atlas/containers-cgroups-namespaces.md) — the kernel enforcement layer under requests, limits, throttling, and OOM.
- [Scheduling & Queueing](../connection-atlas/scheduling-queueing.md) — the general queueing map this scheduler instance occupies.
- [Load Balancing](./load-balancing.md) — the traffic-side sibling: placement decides capacity; balancing decides who arrives.
- [Scheduling](../../cloud/kubernetes/scheduling.md) — the book-level treatment: scheduler components, profiles, and configuration.
- [Pods](../../cloud/kubernetes/pods.md) — pod spec anatomy, including the resource fields this ladder prices.
- [kube-scheduler](https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/) — the official pipeline, framework, and scoring-plugin reference.
- [Pod Priority and Preemption](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/) — the official preemption algorithm, victim selection, and PDB interaction.
