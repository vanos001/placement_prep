# Follow-up Tree: Kubernetes Pod Lifecycle

## Overview

"What happens when a pod is created?" is the container-era successor to "what happens when you run `./a.out`" — the same kernel-to-process story with a control plane wrapped around it — and it escalates along exactly the axes Kubernetes interviews actually probe: the division of labor between the control plane and the kubelet, the probe system that decides whether your pod receives traffic and whether it lives, the shutdown contract that decides whether deploys drop requests, and the scheduler's queueing and preemption behavior that decides whether the pod runs *at all*. A candidate who recites "the scheduler binds the pod to a node" has answered rung one; the rungs below build the mechanism under that sentence and its failure modes. This page treats the container layer itself (namespaces, cgroups) as linked context rather than re-explained material — see [Process Lifecycle](./process-lifecycle.md) for the underlying chain and [Containers Are VMs](../misconceptions/containers-are-vms.md) for the isolation misconception it rides on. The book-level treatments are [Kubernetes Pods](../../cloud/kubernetes/pods.md), [Kubelet](../../cloud/kubernetes/kubelet.md), and [Kubernetes Scheduling](../../cloud/kubernetes/scheduling.md). Each level states what a weak answer sounds like, what the strong answer adds, and the follow-up that escalates.

## The Opening Question

**"What happens when a pod is created?"**

The expected core answer: the API server validates and stores the pod object in etcd (the pod is just an API resource at this point — nothing is running); the *scheduler* watches for pods with no assigned node, runs its filtering-and-scoring pass, and binds the pod to a chosen node by writing the assignment back to the API server; the *kubelet* on that node — the node's local agent, not a control-plane component — watches for pods assigned to it, drives the container runtime (via the CRI) to create the containers, mounts volumes, and manages the pod through its phases: `Pending` (accepted but not yet running — often waiting on scheduling or images), `Running` (at least one container started), `Succeeded`/`Failed` (all containers terminated with status). The senior framing: the control plane *decides*, the kubelet *acts*, and every part of the ladder below is a question about one half or the other.

A weak answer blurs the control plane and the node into "Kubernetes starts the pod," with no actors and no phases. The strong answer names the actors (API server, scheduler, kubelet, runtime), the watch/informers reconciliation pattern that connects them (declarative state, no imperative pipeline), and init containers — which run to completion *before* app containers start, sequencing setup work inside the pod. The follow-up that escalates: **"How does Kubernetes know the container is actually healthy?"** — which moves from creation mechanics to the probe system.

## Level 2: Probes — Startup, Readiness, Liveness, and Their Failure Modes

**What it tests:** whether the three probe types are distinct mechanisms with distinct consequences in your head, and whether you can predict what a misconfigured probe does in production.

**Weak answer:** "You set a health check so Kubernetes restarts bad pods" — one mechanism, one consequence, three distinctions missing.

**Strong answer:** separates the three: *startup* gates the other probes until the app is up (protecting slow-booting apps from premature kills); *readiness* gates **traffic** (a failing probe removes the pod from Service endpoints, but nothing restarts); *liveness* gates **existence** (a failing probe restarts the container); and can name the classic failures — liveness probes that depend on downstream services, causing restart cascades during dependency outages.

**Escalation trigger:** "Your dependency database slows down — walk me through what a wrong liveness probe does to your fleet."

**Answer.** The probe mechanics: each probe type is a periodic check (HTTP endpoint, TCP connect, or exec command) with thresholds — `initialDelayPeriod`/`periodSeconds`/`failureThreshold` — evaluated by the *kubelet* locally; probes are node-local health logic, not cluster-wide monitoring. The failure modes are where the rung earns its keep. A **liveness probe that checks downstream dependencies** turns any dependency slowdown into a fleet-wide restart storm: every pod fails liveness, gets killed, restarts, re-warms, and hammers the recovering dependency — turning a degradation into an outage. A **readiness probe on the same dependency** is often right (don't route traffic to a pod that can't serve) but must be paired with liveness *decoupled* from dependencies, so pods are drained of traffic but not killed. A **missing startup probe** with a slow-booting app (JVM warmup, big caches) gets killed by liveness before it ever becomes healthy — the classic flapping deployment.

The design judgments to volunteer: readiness failures should be *cheap and dependency-aware*, liveness failures should mean "this process is unrecoverable — deadlocked, out of fds," and startup probes exist precisely to buy slow apps time without weakening liveness. The second-order effect worth naming: probes interact with connection pooling and load — a pod removed from endpoints keeps its in-flight requests, and a pod re-added cold (empty caches, unwarmed JIT) receives full traffic instantly, which is why real systems add warmup logic after readiness flips. The official mechanics live in the [Kubernetes pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) and [probe configuration](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/) documentation; the deployment-level rollout interaction is in [Deployments](../../cloud/kubernetes/deployments.md).

## Level 3: Graceful Termination — SIGTERM, Grace Periods, and PID 1

**What it tests:** whether you can narrate the *shutdown* sequence precisely — the half of the lifecycle every rolling deploy exercises — and whether you know who translates signals for your process.

**Weak answer:** "Kubernetes sends SIGTERM and then kills it" — no grace period semantics, no preStop hook, no endpoint-propagation race, no PID 1 subtlety.

**Strong answer:** sequences it: pod marked terminating, endpoints removed (propagation takes time), `preStop` hook runs, SIGTERM delivered with `terminationGracePeriodSeconds` counting down, then SIGKILL; and knows the two classic bugs — apps that ignore SIGTERM (because PID 1 never wired a handler) and the endpoint-propagation race where the pod stops serving before the LB stops sending.

**Escalation trigger:** "Every deploy drops a handful of requests. Where in the shutdown sequence is the bug?"

**Answer.** The termination sequence, in order: the pod is marked `Terminating` and removed from Service endpoints *asynchronously* (other components learn via watch — this propagation is not instantaneous); the kubelet runs the `preStop` hook (a sleep here is the standard, slightly inelegant fix for endpoint propagation lag); SIGTERM goes to the container's process **as PID 1** (or to whatever handles signals in the container's PID namespace); the grace period (`terminationGracePeriodSeconds`, default 30 s) ticks; on expiry, SIGKILL — uncatchable, by design. The two classic bugs live at the ends of that sequence. First, **the app that never sees SIGTERM**: many images run shell wrappers or apps that do not install handlers, and PID 1 has no default SIGTERM disposition in most runtimes — the process ignores the signal, the grace period expires, everything is SIGKILLed mid-request. The diagnosis and the handler-wiring patterns (exec-form entrypoints, signal forwarding, init as PID 1) are in [PID 1 Signals in Containers](../../linux/process-exit-signal/containers/pid1-signals.md) and [Signals in Kubernetes](../../linux/process-exit-signal/containers/kubernetes.md).

Second, **the propagation race**: readiness removal and SIGTERM are near-simultaneous, but load balancers and client-side connection pools hold existing connections and in-flight requests — so a correct app must (a) stop *accepting* new work when SIGTERM arrives, (b) finish or drain in-flight work within the grace period, and (c) stay *readiness-failing* so the endpoint removal wins the race with the traffic still arriving. A `preStop` sleep of a few seconds papers over slow endpoint propagation, but the principled version is an app-level drain. The judgment coda: grace period sizing is a contract — it must cover your longest in-flight request plus drain overhead, and setting it huge means node drains and preemptions wait on it. Where the killed process's exit status goes (137, 143) and how to read it is the debugging skill in [Kubernetes Debugging](../../cloud/kubernetes/debugging.md).

## Level 4: Scheduling, Pending, and Preemption

**What it tests:** the capacity rung — whether you can diagnose a stuck `Pending` pod, sketch how the scheduler chooses a node, and reason about PriorityClass and preemption as explicit policies rather than magic.

**Weak answer:** "Pending means not enough resources" — right one time in three, with no diagnosis tree and no idea how preemption fits.

**Strong answer:** walks the scheduler's two-phase decision (filter feasible nodes, score the survivors, bind the best), enumerates the Pending causes in order of frequency (unsatisfiable requests/limits, taints and affinities, PVC unbound, node selectors), and explains preemption: a high-priority pod evicts lower-priority pods when no node fits — making priority an explicit capacity policy, not a nicety.

**Escalation trigger:** "The cluster has free CPU but the pod stays Pending — now what?"

**Answer.** Scheduling is a queue plus a decision function: the scheduler maintains a priority queue of unscheduled pods, pops the highest-priority one, **filters** nodes that cannot fit it (insufficient CPU/memory against requests, node selectors, taints/tolerations, affinity rules, unbound volumes), then **scores** the feasible nodes (spreading vs bin-packing preferences, image locality) and binds to the winner. A pod stuck `Pending` has failed this pipeline, and `kubectl describe pod` prints *why* in the events — the diagnosis tree is: unschedulable-resource (requests too big; note requests, not current usage, are what must fit), constraint conflict (affinity/taints — "free CPU but wrong nodes"), volume binding (PVC pending, often zonal disk mismatch), or quota/limit-range rejection upstream. The resource-model subtlety that earns credit: scheduling runs on *requests* (guarantees) while node pressure uses *limits* — overcommit is legal, which is how "the cluster has free CPU" and "no node fits my requests" are simultaneously true; see [Kubernetes Scheduling](../../cloud/kubernetes/scheduling.md) for the full policy space.

**Preemption** closes the loop: each pod carries a `PriorityClass`, and when a pending high-priority pod fits nowhere, the scheduler may preempt — evicting lower-priority pods from a node until it fits. This makes priority the tool for capacity triage (batch below latency-critical services) and couples it to the spot-instance world: [Spot and Preemptible Instances](../../cloud/spot-preemptible.md) turn preemption from a policy into a routine event, which is why graceful termination (Level 3) is not optional. The multi-tenant coda: priority without quotas becomes a arms race — every team marks everything critical — so ResourceQuotas and limit ranges exist to keep the priority system honest, and the noisy-neighbor dynamics are treated in [Noisy Neighbors](../../cloud/noisy-neighbors.md).

## How to Approach Unfamiliar Variations

The template for pod-lifecycle variations — "debug a CrashLoopBackOff," "sidecars," "make deploys zero-downtime":

1. **Assign every behavior to an actor: control plane, kubelet, or the app itself.** Rollouts and scheduling are control plane; probes, mounts, and signal delivery are kubelet; bootstrapping and drain are the app. Most "Kubernetes did something weird" stories dissolve into "one actor's timing assumption was wrong."
2. **Treat every transition as a race and ask what gates it.** Creation (scheduling gates running), traffic (readiness gates endpoints), restart (liveness gates existence), shutdown (endpoint removal races SIGTERM). Naming the gate answers "why is it flapping" questions.
3. **Read the events before theorizing.** `kubectl describe pod` carries the scheduler's rejection reasons, probe failure counts, and restart timestamps — the diagnosis tree for Pending and CrashLoopBackOff is printed, not guessed.
4. **Convert reliability requirements into lifecycle configuration.** "Zero-downtime deploys" = readiness probes + preStop drain + adequate grace period + rollout strategy; "protect the payment service" = PriorityClass + quota; "survive dependency outages" = liveness decoupled from dependencies. Say the mapping explicitly in interviews.

## Interview Questions

**Q: A pod is CrashLoopBackOff. Walk me through your diagnosis.**
A: Read the events and previous logs first: `kubectl describe pod` shows restart counts and reasons, `--previous` shows the crashing process's last words. Common causes in order: app-level crash (config/secret missing, migration failing), failing startup or liveness probes (killed before ready), OOMKilled (exit 137 — requests/limits or a leak, check the OOM events), and image/runtime errors. The distinction matters because the first two need different fixes than the third, and all of them look identical from `kubectl get pods`.

**Q: Why would you use an init container instead of application startup logic?**
A: Separation of concerns with different failure semantics: init containers run to completion before app containers start, so credential fetching, schema-wait loops ("wait for the DB to accept connections"), and setup tools run as isolated, restartable units with their own images — the app image stays minimal and the failure messages name the init step. They also gate the probes: readiness is not evaluated until init completes, which cleanly separates "environment ready" from "application ready."

**Q: terminationGracePeriodSeconds is 30 and your longest request takes 45 seconds. What happens during a rolling update?**
A: At grace expiry the kubelet sends SIGKILL regardless of in-flight work, so requests crossing the 30-second boundary are killed with their clients seeing connection resets. Fix the contract, not just the number: either raise the grace period to cover p100 request time plus drain, or make the work resumable/idempotent so clients retry safely — and check that endpoint removal plus preStop drain fits inside the same budget.

**Q: A team wants their batch jobs to never be preempted by the payment service. What do you tell them?**
A: Preemption follows PriorityClass — the payment service's higher priority is exactly what lets it evict batch workloads under pressure, and that is usually the correct trade. The honest options: lower batch priority and make jobs checkpoint-and-resume (preemption becomes routine, not catastrophic), isolate capacity pools with quotas or separate node pools/taints so competition for resources is structural, or negotiate the SLO that justifies the priority. "Never preempted" is a capacity guarantee, not a YAML field.

## Key Takeaways

- Pod creation is a pipeline of actors — API server stores, scheduler binds, kubelet acts — driven by watch-and-reconcile, with phases (Pending, Running, Succeeded, Failed) that name where a pod is stuck.
- The three probes gate three different things: startup gates the other probes, readiness gates traffic, liveness gates existence — confusing them causes restart cascades during dependency outages.
- Liveness should mean "process unrecoverable," never "dependency down"; readiness may check dependencies; startup probes buy slow apps time.
- Termination is a sequence with a race: endpoint removal propagates asynchronously while SIGTERM (via PID 1) starts the grace period — correct apps stop accepting, drain, and outlive the propagation lag.
- PID 1 without a signal handler ignores SIGTERM; the grace period then ends in SIGKILL mid-request — the classic image bug behind "deploys drop requests."
- Scheduling runs on requests, pressure runs on limits; Pending diagnosis starts with `describe` events, and preemption makes PriorityClass a capacity policy rather than a label.

## Cross-References

- [Process Lifecycle](./process-lifecycle.md) — the fork/exec/signals chain this ladder builds on; containers are its wrapper.
- [Containers Are VMs](../misconceptions/containers-are-vms.md) — what containerization does and does not isolate, claim by claim.
- [Kubernetes Pods](../../cloud/kubernetes/pods.md) — pod spec, init containers, and sidecars in full.
- [Kubelet](../../cloud/kubernetes/kubelet.md) — the node agent that evaluates probes and drives termination.
- [Kubernetes Scheduling](../../cloud/kubernetes/scheduling.md) — filtering, scoring, priorities, and preemption policy space.
- [Deployments](../../cloud/kubernetes/deployments.md) — rollout strategies that make the shutdown contract load-bearing.
- [Kubernetes Debugging](../../cloud/kubernetes/debugging.md) — events, exit codes, and the CrashLoopBackOff workflow.
- [Namespaces](../../os/containers/namespaces.md) and [Cgroups](../../os/containers/cgroups.md) — the view/budget halves beneath every pod.
- [PID 1 Signals in Containers](../../linux/process-exit-signal/containers/pid1-signals.md) — signal translation and handler wiring for containers.
- [Signals in Kubernetes](../../linux/process-exit-signal/containers/kubernetes.md) — SIGTERM/SIGKILL behavior in orchestrated environments.
- [The OOM Killer](../../os/modern/oom-killer.md) — what exit 137 and cgroup memory pressure mean underneath.
- [Spot and Preemptible Instances](../../cloud/spot-preemptible.md) — when preemption is a routine event, not a policy corner case.
- [Kubernetes Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) — official phases, conditions, and container states.
- [Configure Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/) — official probe semantics and configuration.
