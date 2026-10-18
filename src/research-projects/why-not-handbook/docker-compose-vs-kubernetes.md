# Docker Compose vs Kubernetes: One Host's Contract vs a Fleet's Control Plane

## Overview

Docker Compose and Kubernetes both take a declarative YAML file and turn it into running containers, and the resemblance is exactly what makes the comparison treacherous. They look like the same product at two price points; they are actually two different answers to the question **"what is the unit of scheduling?"** Compose schedules on one host: its `restart: always` policy, its networks, its volumes, and its scaling knob (`scale: 5`) all resolve to processes managed by a single Docker daemon on a single machine. Kubernetes schedules on a cluster: its "restart a container" is a reconciliation loop distributed across a scheduler, a kubelet per node, and an etcd-backed desired-state store, and its replica sets place pods wherever resources fit. Compose is a process manager with a schema; Kubernetes is a control plane with an API.

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **Compose buys you dev-prod parity of *artifacts* (the same images) and loses parity of *behavior* (restarts, placement, networking, secrets all behave differently on one host); Kubernetes gives behavioral parity and charges you a control plane to operate.** The choice is rarely either-or in practice — compose files dominate local development and CI, Kubernetes dominates anything with more than one node or more than one team — and the interesting engineering lives at the seam: the edge case where teams run compose in CI, or run a full Kubernetes inside Docker (kind, minikube) on a laptop to chase parity, each trade paying in a different currency.

## Step 1: The Problem and Its Constraints

The abstract shape: a set of containers — app, sidecars, database, cache — must run, restart on failure, discover each other, and eventually scale. Constraints that decide the answer:

- **Node count.** One machine, forever? Compose's ceiling is that machine. Two machines with a network between them, and Compose has nothing to say — its model simply does not span hosts.
- **Who operates it.** A developer running a stack locally wants zero-moving-parts. A platform team wants an API others can build on: controllers, operators, admission policies. Compose exposes no API beyond `docker compose up`.
- **Failure behavior contract.** What happens when the host reboots, when a container OOMs, when a disk fills? On one host these have one-host answers; in a fleet they have scheduling answers (reschedule elsewhere, drain, evict).
- **Scaling semantics needed.** "More replicas of a stateless web container behind a port" is trivial in both. "Replicas *placed by resource fit* across heterogeneous nodes with anti-affinity and autoscaling" is Kubernetes-shaped; Compose's `scale` cannot even see another node.
- **Environment fidelity.** Does the team need production to behave like development, or is development allowed to be a caricature of production? The cost of divergence: "works on my machine" incidents that are really "works on my *single* machine" incidents.

## Step 2: The Mechanisms

### Compose: the single-host contract

Compose parses a YAML spec and asks one Docker daemon to create networks, volumes, and containers. The mechanisms that matter:

- **Restart policy, not reconciliation.** `restart: always` is evaluated by the local daemon: if the container's process exits, start it again *on this host*. There is no notion of desired state elsewhere, no health-gated placement, no rescheduling. If the host is gone, the "policy" is gone with it. Kubernetes' ReplicaSet, by contrast, stores *desired count* in etcd and any surviving node can act on it — the difference between a `while` loop on one machine and a distributed invariant.
- **Networking is one bridge network.** Service names resolve via Docker's embedded DNS on a single subnet; localhost ports are published directly. This is why compose apps "just work" locally and why subtle differences bite in production: no NetworkPolicies, no ingress abstraction, no per-pod IP model, and DNS semantics that differ from kube-dns/CoreDNS behavior.
- **Secrets are files, and by default not secret at all.** Compose supports Docker secrets only in swarm mode; in plain compose, environment variables carrying credentials sit in the YAML file, in `docker inspect` output, and in shell history. Kubernetes [Secrets](https://kubernetes.io/docs/concepts/configuration/secret/) are API objects — mountable as tmpfs, RBAC-guarded, rotatable — with their own weaknesses (base64 ≠ encryption) but at least an ownership and access model.
- **`scale: N` is N processes on one host.** No scheduler decides placement, no resource bin-packing, no anti-affinity. Five replicas of a memory-hungry container on an 8 GB laptop is a swap storm, not a scaling story.

### Kubernetes: the reconciling control plane

Kubernetes stores desired state (Deployments, Services, ConfigMaps) in etcd; controllers continuously diff actual against desired. The mechanisms that matter:

- **Controllers are the runtime.** A [Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) does not "start containers"; it maintains a ReplicaSet, which maintains pods, and kubelets on whatever nodes the scheduler picks execute the containers. A node dying is not an event anyone handles — it is a divergence the controller erases by creating replacements elsewhere. That is the deep answer to "why not compose for prod": Compose *restarts things on the host they died on*; Kubernetes *replaces things wherever capacity exists*.
- **Scheduling is resource arithmetic.** Requests and limits feed bin-packing, affinity, and taints; scaling is additive (HPA on replicas, VPA on requests, [cluster autoscalers](../../cloud/autoscaling.md) on nodes). The pod lifecycle this machinery drives — pending, scheduling, liveness, termination grace, preemption — is walked rung by rung in [kubernetes pod lifecycle](../followup-tree/kubernetes-pod-lifecycle.md).
- **The API is the product.** Everything — a canary, a database, a cert-rotator — is a controller talking to the same API. That is what makes operators, GitOps, and admission control possible, and it is also the operational bill: etcd quorum, control-plane upgrades, RBAC, CRDs. Compose has no second consumer of its file format; Kubernetes' entire ecosystem is consumers of its API.
- **Parity tooling exists but is not free.** kind/minikube run a full control plane inside a container on your laptop — true API parity at the cost of a heavyweight dev loop, examined as this page's edge case.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Docker Compose | Kubernetes |
|----------|----------------|------------|
| Unit of scheduling | Container, on one host | Pod, on any node that fits |
| Failure of the host | Total: policy and workload die together | Rescheduling by controllers onto surviving nodes |
| Restart semantics | Daemon's restart policy, same host | Reconciliation loop: desired count vs actual, anywhere |
| Secrets | Env vars in YAML; swarm-only secrets | API objects with RBAC, tmpfs mounts, rotation paths |
| Scaling | `scale: N` processes on one machine | Replica placement by scheduler; HPA/VPA/autoscaling |
| Service discovery | Embedded DNS on one bridge network | Cluster DNS + Services + endpoints across nodes |
| Rolling updates / rollbacks | Manual or single-host stop/start | Deployment strategies, revision history, rollbacks |
| Resource guarantees | None beyond cgroup flags per container | Requests/limits, QoS classes, eviction ordering |
| Operational surface | One daemon | Control plane: etcd, API server, scheduler, kubelets, CNI |
| Time to first success | Minutes | Hours to days (and a permanently higher maintenance floor) |

The **parity gap** mechanism deserves the arrow drawn. Compose gives artifact parity — the *same images* run in dev and prod — but behavior diverges at every layer above the image: a container that dies in compose restarts in place, in k8s it is recreated by a different node with a different IP, subject to readiness gates, grace periods, and eviction; an env var in compose is a file on disk, in k8s it may be a projected volume with an update cadence. Applications break not because images differ but because **environmental promises differ**. The classic casualty is the app that never handles SIGTERM correctly: compose's stop is gentle and local, Kubernetes' termination is a grace-period race against the endpoint removal — the readiness/termination choreography in [canary vs blue-green](./canary-vs-blue-green.md) assumes behavior compose never taught your app.

## Step 4: When Each Wins

**Compose wins** when: the artifact is a developer or CI environment (run the whole stack, one command, throw it away); the deployment target is genuinely one machine — edge boxes, on-prem appliances, demo VMs — where a control plane is pure liability; the team is small and the "orchestration" need is restart-and-DNS. Compose is also the lowest-friction way to give an interviewer or new hire a runnable system: no cluster, no context switching, one file.

**Kubernetes wins** when: more than one node is load-bearing; multiple teams need a shared deployment substrate with policy and quotas; rolling updates, autoscaling, and self-healing are requirements rather than aspirations; you need the API as an extension point (operators, GitOps). Anything with a fleet and a platform team is Kubernetes territory because its primitive — reconciliation against desired state — is exactly the primitive fleet operations need. The horizontal-scaling arithmetic — and the serial remainders it cannot fix — are the territory of [scaling up vs out](./scaling-up-vs-out.md).

**The honest hybrid** — where most organizations land: compose for local dev and integration tests; Kubernetes for staging and prod; images as the shared artifact; and a documented divergence list (secrets, DNS, termination, resource limits) reviewed like code, because that list is where parity leaks.

## Step 5: Edge Cases and Counterexamples

- **Compose in CI: the fast trap.** Teams run the full stack with compose in CI because it is fast — and it is, until tests need to assert *orchestration* behavior: pod termination handling, readiness-probe-driven rollouts, secret rotation. Compose cannot test any of it, so CI stays green while prod rolls badly. The mature pattern is two tiers: compose for functional tests (fast, cheap), a kind cluster for a thin suite of orchestration-contract tests (slower, catches the SIGTERM-and-readiness class of bug). Teams that skip the second tier rediscover it during their first bad production rollout.
- **Kubernetes-in-Docker for dev: parity at a price.** kind gives a real API server, real scheduler, real pods — on a laptop. The non-obvious costs: the dev loop slows from seconds (compose up -d) to minutes (cluster boot, image loading); the laptop runs etcd and friends alongside the IDE; and behavior still diverges at the edges — LoadBalancer services don't get real IPs locally, node count is fiction, and resource-pressure behavior differs wildly from prod hardware. Parity of API is not parity of *behavior under failure*, which is the parity that matters most and cannot be simulated at 0.1× scale.
- **`scale: 5` that taught the wrong lesson.** A team validated "horizontal scaling works" by scaling a compose app to five replicas on a dev box — all five sharing one host's CPU. In prod on k8s, the same five replicas hit a per-node network-connection limit and a noisy-neighbor CPU steal they had never seen, because *placement* had never been part of their testing. Scaling semantics are not replica counts; they are replica counts plus placement plus per-instance resource isolation (the cgroup/namespace mechanics under both systems are unpacked in [containers, cgroups, namespaces](../connection-atlas/containers-cgroups-namespaces.md)).
- **The single-node k3s that outgrew its story.** An edge appliance team adopted Kubernetes "for future flexibility" via a single-node distro. They paid control-plane memory and upgrade complexity on a 2 GB box to get… restart policies compose already had. The reconciliation machinery only pays when desired state can be reconciled *elsewhere*; on a single node, Kubernetes is an expensive process manager. Future flexibility that never arrives is the most expensive kind.
- **Secrets divergence bites at the worst time.** A stack ran in compose with DB credentials as env vars for two years; migrating to k8s, the team mounted the secret as a file — and the app, which had only ever read env vars at boot, had no reload path when rotation landed. Parity work is application code work: the *consumption interface* of configuration, not the YAML, is what must match across environments.

## Step 6: Decision Framework

1. **Will the workload ever span more than one host?** Yes → Kubernetes (or another fleet orchestrator); Compose has no model for a second node, so this constraint decides before anything else.
2. **Is the artifact a developer/CI environment with a short lifetime?** Yes → Compose; a cluster in CI is minutes of boot tax per run for guarantees those tests don't assert.
3. **Do you need the deployment substrate to be programmable** (operators, GitOps, admission policy)? Yes → Kubernetes; the API is the feature, and Compose has none.
4. **Is "restart on the same host" sufficient failure handling?** Yes (appliances, edge boxes, demos) → Compose; buying a control plane for a single node buys cost, not capability.
5. **Do teams need secrets with access control and rotation?** Yes → Kubernetes secrets (or an external secret manager); compose env vars are plaintext artifacts.
6. **Default in doubt:** compose for dev and functional CI, Kubernetes for anything load-bearing, images as the shared artifact — and treat the divergence list as code, because it is the parity debt.

## Interview Questions

1. **"Compose and Kubernetes both run containers from YAML — why not compose in production?"** Compose's restart policy and scale knob resolve to a single Docker daemon on one host: no placement, no rescheduling on host loss, no resource-driven scheduling, no API for policy or extension. Kubernetes' primitive is a reconciling control plane over desired state stored in etcd, which is what fleet guarantees (self-healing, rolling updates, bin-packing) are built from. One host's process manager vs a cluster's control plane.
2. **What exactly does "dev-prod parity" mean under compose-plus-k8s, and where does it break?** Artifact parity (same images) is easy; behavioral parity is not. Restart semantics, DNS, secrets delivery, resource limits, and termination all differ. It breaks at SIGTERM handling, readiness gates, and config-reload paths — app-level behaviors that compose never exercises.
3. **Your CI runs the full stack via compose and everything is green, but production rollouts fail on pod termination. What happened and what do you change?** CI tested functionality, not orchestration contracts: termination grace vs endpoint removal, readiness-probe gating, secret updates. Add a thin orchestration-contract suite on a kind cluster (real control plane in Docker) covering rollout and termination behavior, keep compose for functional speed.
4. **When is choosing Kubernetes for a single node correct — and when is it cargo cult?** Correct when the node is a management-plane member of a larger fleet, or you need k8s APIs (operators, CRDs) on-device. Cargo cult when the real need is restart-and-DNS: a single-node k8s buys etcd and upgrade overhead for capabilities that only pay when state can be reconciled elsewhere.
5. **Explain why Compose's `scale: 5` and Kubernetes' `replicas: 5` are not the same promise.** Compose creates five containers on one daemon — no placement, no isolation budget, no cross-host failure domain. Replicas are scheduled pods: scheduler-placed by requests/limits, spread by anti-affinity, replaced on node loss, optionally autoscaled. The number is the same; the guarantees underneath differ in kind.

## Key Takeaways

- The fork is the **unit of scheduling**: Compose schedules containers on one host through a daemon; Kubernetes schedules pods across a fleet through a reconciling control plane. Everything else — restarts, secrets, scaling, updates — derives from that.
- Compose delivers artifact parity (same images) but not behavioral parity; the divergence list (termination, readiness, secrets, DNS) is where "works on my machine" incidents breed.
- Restart policy and reconciliation look similar and are not: one is a loop on a host, the other is an invariant over a cluster that survives the loss of any single machine.
- Compose's kingdom is developer experience and CI speed; Kubernetes' kingdom is the API as a platform. Cross the boundary only when the constraint list says so.
- Parity tools (kind, minikube) close the API gap at real cost and cannot simulate fleet failure behavior at laptop scale — reserve them for orchestration-contract tests, not the whole dev loop.

## Cross-References

- [Scaling Up vs Out: Why-Not Handbook](./scaling-up-vs-out.md) — the scaling arithmetic that motivates leaving one host, and the serial remainders orchestration cannot fix.
- [Canary vs Blue-Green: Why-Not Handbook](./canary-vs-blue-green.md) — rollout behavior that assumes Kubernetes-style readiness and termination semantics.
- [Stateless vs Stateful: Why-Not Handbook](./stateless-vs-stateful.md) — placement decisions change completely when replicas carry state.
- [Kubernetes Pod Lifecycle: Follow-up Tree](../followup-tree/kubernetes-pod-lifecycle.md) — the pending/scheduled/terminating ladder behind Deployment behavior.
- [Containers, cgroups, namespaces: Connection Atlas](../connection-atlas/containers-cgroups-namespaces.md) — the isolation mechanics both tools share underneath.
- [Containers and Resources: Assumptions Hunt](../assumptions-hunt/containers-and-resources.md) — the resource-limit assumptions requests and limits encode.
- [Docker](../../os/containers/docker.md) and [Kubernetes](../../os/containers/kubernetes.md) — the engine and the orchestrator in depth.
- [Deployments](../../cloud/kubernetes/deployments.md) — rolling-update mechanics, revision history, rollbacks.
- [Autoscaling](../../cloud/autoscaling.md) — HPA/VPA/cluster autoscaling: the scaling layer compose lacks entirely.
- [Infrastructure Trade-offs](../../trade-offs/infrastructure-tradeoffs.md) — the quick-reference table for this and adjacent platform choices.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
