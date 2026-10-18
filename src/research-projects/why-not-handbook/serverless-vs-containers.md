# Serverless vs Containers: Renting Invocations vs Operating a Fleet

## Overview

A container deployment and a serverless function platform both take your code and run it somewhere you do not manage, and from that shared sentence teams conclude the choice is about operational laziness. The real fork is the **billing and execution model**: containers sell you capacity — instances that run, and bill, whether or not requests arrive, which you size, autoscale, and keep warm; functions sell you invocations — the platform starts your code per event, bills per millisecond of execution, and takes on the idle cost you would otherwise pay. Everything that distinguishes them in practice — cold starts, execution limits, state, observability, vendor coupling — is a consequence of that one shift: **who owns the idle time.**

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **FaaS converts your provisioned-but-idle capacity into someone else's problem and charges you only for work — but imposes cold starts, execution ceilings, and a runtime contract you do not control; containers give you a stable process with full environment control and charge you for the privilege of waiting.** Neither dominates: a spiky image-processing API is a textbook function, a websocket gateway holding a million open connections is a textbook container workload, and the interesting production pattern is the hybrid — queue-triggered functions doing bursty work behind long-lived container services, each part where its cost curve fits.

## Step 1: The Problem and Its Constraints

The abstract shape: code must run in response to events — HTTP requests, queue messages, schedules. Constraints that decide the answer:

- **Traffic shape.** Steady 24/7 load makes per-invocation pricing expensive and idle capacity cheap to own; spiky or rare traffic makes provisioned containers mostly-idle waste and per-invocation billing a bargain. Plot traffic before opinions.
- **Latency contract.** Is a 200 ms–2 s initialization tail acceptable per cold instance? Interactive APIs with single-digit-millisecond budgets usually cannot absorb it; asynchronous workers usually can.
- **Execution profile.** Duration, memory, and concurrency per invocation. Functions enforce hard ceilings (15 minutes and staged memory tiers on AWS [Lambda](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)); containers enforce whatever you configure — or nothing.
- **State and connection model.** Does the code hold open sockets, connection pools, caches, or websockets across requests? Functions are initialized per (scaled) instance with an unfreezable lifetime; containers own their process lifetime.
- **Operational depth and portability.** Who debugs at 3 a.m., with which tools, and can the workload move to another provider or an on-prem cluster without a rewrite?

## Step 2: The Mechanisms

### FaaS: the invocation as the unit

The platform keeps no process of yours running. On an event, it either reuses a warm sandbox or provisions one: fetch a [microVM](../../cloud/virtualization/firecracker.md) image (Firecracker-style microVMs are what most FaaS sandboxes run — isolation without VM boot times), initialize the runtime, run your handler, freeze or reap it. The mechanisms that matter:

- **Cold starts are a scheduling and initialization tax, not a network tax.** The latency is runtime boot, framework import, connection pool warm-up — plus the platform's placement round trip. It appears precisely when scale-out happens (new instance count), so it strikes at burst onset — the worst moment. Provisioned-concurrency options exist and reintroduce, metered, exactly the idle-billing FaaS removed.
- **Concurrency is per-instance and managed by the platform.** Each sandbox handles one request at a time (most FaaS runtimes); the platform scales instance count, and downstream systems experience your concurrency as a step function — which is why an unthrottled function fan-out can DoS a database, and the fix (reserved concurrency) is a quota, not a pool.
- **Execution limits are contractual.** Duration ceilings, memory tiers (which scale CPU proportionally), payload sizes, and the statelessness assumption: local disk is ephemeral, background work after return is undefined — a killed sandbox after the response is normal operation, not an incident.
- **Observability comes from the platform's vantage.** Per-invocation logs, structured metrics, distributed traces to the platform boundary — but no long-lived process means no profile across requests, no flame graph of a warm worker, and memory-leak hunting becomes a statistics problem across instance lifetimes.

### Containers: the process as the unit

You ship a runnable image to a fleet that keeps it running; a load balancer and an autoscaler decide how many instances face the traffic. The mechanisms that matter:

- **Warm by construction.** The process, its JIT, its pools, its caches persist across requests; the "cold start" is a deploy or scale-out event you control and can engineer around (pre-warming, readiness gates, keep-alive) — the same warm-path reasoning Kubernetes' probes formalize, per the [pod lifecycle](../followup-tree/kubernetes-pod-lifecycle.md) ladder.
- **You pay for the shape you provision.** Idle containers bill like idle servers; autoscaling reacts in tens of seconds to minutes (metrics → decision → boot → readiness), so bursts either over-provision headroom (paying idle) or absorb queueing latency. The scale-out arithmetic — and why coordination-heavy workloads resist it — is the territory of [scaling up vs out](./scaling-up-vs-out.md).
- **The environment is yours.** Any runtime, any daemon, sidecars, custom kernels of behavior via libraries; also every patch, every base-image CVE, every dependency. The isolation substrate — namespaces and cgroups — is shared with FaaS sandboxes and dissected in [containers, cgroups, namespaces](../connection-atlas/containers-cgroups-namespaces.md), with the resource-limit assumptions unpacked in [containers and resources](../assumptions-hunt/containers-and-resources.md).
- **State is possible but dangerous.** A long-lived process *can* memoize, pool, and hold websockets — and if the load balancer distributes unevenly, per-instance state becomes per-instance inconsistency, the fleet-level trap analyzed in [stateless vs stateful](./stateless-vs-stateful.md).

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | FaaS (serverless) | Long-running containers |
|----------|-------------------|--------------------------|
| Billing unit | Invocation × duration × memory tier | Provisioned instance-hours (idle included) |
| Cold start | Per scale-out instance; 100 ms–seconds; strikes at burst onset | Only on deploy/scale-out; engineered via readiness and pre-warming |
| Execution ceiling | Hard (e.g., 15 min; memory tiers) | Your limits or none; long jobs are normal |
| Concurrency model | Platform-managed, typically 1 request/instance; scale = instance count | Your server's model: threads, async, multiplexing on one process |
| State across requests | None guaranteed; ephemeral disk; background work after return undefined | Possible (pools, caches, websockets) — and an inconsistency risk under uneven routing |
| Burst behavior | Scales near-instantly to a concurrency cap; downstream sees a step function | Scale-out in tens of seconds–minutes; needs headroom or queues |
| Observability | Per-invocation logs/metrics/traces; platform boundary | Full process access: profiles, heap dumps, per-connection debugging |
| Vendor coupling | Runtime contract, event shapes, platform services — deep | Image + orchestration API; portable across clouds and on-prem |
| Cost at zero traffic | ~0 | Full price of provisioned min |
| Characteristic failure | Timeout-invisible work stoppage; downstream stampede from fan-out | Idle-cost creep; autoscaler lag under burst; per-instance state drift |

The **cost curve crossover** deserves the arrow drawn. Cost is roughly `rate × duration × price-per-unit-time` for functions versus `instances × hour-price` for containers, and the crossover sits wherever your average utilization makes provisioned capacity cheaper than per-invocation premiums. Steady 70% utilized containers beat functions by multiples; a 2 a.m. cron or a 1% percentile traffic spike sees functions at pennies against a 24/7 container fleet. Neither curve is "cheaper" — the workload's utilization *is* the answer, which is why cost questions in interviews must start with traffic shape.

## Step 4: When Each Wins

**FaaS wins** when: traffic is spiky, rare, or diurnal (zero-cost idle is the product); work is short, stateless, and parallelizable (image thumbnailing, webhook handling, ETL steps — the pipeline placements in [serverless internals](../../cloud/advanced/serverless.md)); the team wants the platform's operational depth (scaling, patching, placement) over its own; glue between managed services (queue → function → storage) is the whole architecture.

**Containers win** when: latency budgets are tight and steady (warm JIT, connection pools, in-process caches); the workload holds state or long-lived connections (websockets, gRPC streams, game sessions); jobs exceed function ceilings or need custom runtimes; observability depth (profiling, heap analysis) is an operational requirement; portability across providers or hybrid/on-prem deployment matters — the constraint layer summarized in [infrastructure trade-offs](../../trade-offs/infrastructure-tradeoffs.md).

**The honest hybrid** — the production norm: long-running container services for the always-on core (APIs, gateways, stateful daemons), queue-triggered functions for bursty async work (media processing, notifications, batch fan-out), with queues as the shock absorber that converts function cold starts from user-facing latency into invisible lag. Knative-class platforms (per [Knative](https://knative.dev/docs/)) blur the line deliberately: containers with scale-to-zero semantics, inheriting the cold-start trade in exchange for idle-cost relief.

## Step 5: Edge Cases and Counterexamples

- **The hybrid that works, and why: queue-triggered functions behind container services.** A video platform kept its API on containers but moved transcode fan-out to queue-triggered functions. Burst of 10,000 uploads → queue depth spikes → platform scales functions to thousands of instances in seconds → downstream transcode farm (containers) receives a throttled, concurrency-capped stream because reserved concurrency bounded the functions. The design took FaaS's instant scale for the *spiky* part, containers' warmth for the *steady* part, and put a queue between them so cold starts never touched a user-facing path. The same queue-mediated pacing analysis as [push vs pull](./push-vs-pull.md), at fleet scale.
- **The cron job that was cheaper on Lambda — until the payload grew.** A nightly 40-second report job ran for pennies as a function. Six months later inputs grew: 18-minute runtime against the 15-minute ceiling, memory tier maxed, and the "cheap" function now cost more per run than the reserved container it replaced — while also risking silent timeout failure. Cost curves are functions of input size and time; a workload that drifts across the execution ceiling flips the economics *and* adds a correctness hazard, because timeouts in FaaS surface as missing outputs, not error pages.
- **Cold starts that only happen during incidents.** A function-backed API was warm at steady traffic; a downstream slowdown caused requests to queue, retries to multiply, and instance count to burst — every new instance paid cold start *while the system was already degraded*, adding hundreds of milliseconds of tail latency at the worst moment. Cold start is not an average-case tax; it is a tail-and-crisis tax, concentrated exactly when the system can least afford it.
- **The websocket gateway that could not be serverless.** A chat backend was rewritten onto functions "to save cost"; the platform's one-request-per-instance model meant one sandbox per *connection*, each billed for wall-clock duration — a persistent connection is 100% "utilization" by definition. Costs exploded ~40×, because functions bill waiting, and holding a connection open *is* waiting. Workloads that hold resources open are structurally container-shaped, whatever the marketing says.
- **Vendor coupling discovered during a migration.** Years of functions meant event-shape assumptions, IAM wiring, platform log sinks, and step-function orchestration woven through the codebase. The "portable code" moved; the integration fabric did not. Containers couple you to a thinner contract (image + API) that both clouds and on-prem clusters speak — coupling is a spectrum, and per-invocation platforms sit at the deep end.

## Step 6: Decision Framework

1. **What does the traffic shape look like?** Spiky/rare/diurnal → FaaS-leaning; steady and predictable → container-leaning. Plot utilization first; the cost crossover follows it.
2. **Is the latency budget per request small and contractual?** Yes → warm containers (or paid provisioned concurrency, which is containers' billing wearing a function's badge).
3. **Does the code hold connections, pools, or state across events?** Yes → containers; per-invocation billing on held-open resources is structurally ruinous.
4. **Does any invocation risk the execution ceiling (duration, memory, payload)?** Yes → containers; a workload that can outgrow the ceiling inherits a correctness hazard, not just a cost change.
5. **Is burst scale-out the dominant requirement, and is the work queue-shaped?** Yes → FaaS behind a queue, with reserved concurrency protecting downstreams.
6. **Default in doubt:** container services for the always-on core, queue-triggered functions for bursty async edges, and a standing rule that any function whose inputs grow quarterly gets re-costed — the crossover moves.

## Interview Questions

1. **"Serverless is cheaper than running containers" — when is this true, when false?** True when utilization is low and bursty: you pay only per work unit, idle cost vanishes. False as utilization rises (per-invocation premiums exceed provisioned cost), for workloads holding open connections (billed for waiting), for long jobs near execution ceilings, and when provisioned-concurrency is needed to kill cold starts — which reintroduces idle billing deliberately.
2. **Explain cold starts as a mechanism, not a slogan.** An invocation arriving with no warm sandbox triggers: platform placement, microVM boot, runtime init, framework import, pool warm-up. It concentrates at scale-out moments — burst onset and incident-time fan-out — so it is a tail tax, not an average tax. Mitigations (provisioned concurrency, keep-warm, lighter runtimes) each reintroduce some idle cost or complexity.
3. **Why does one-request-per-instance concurrency make a websocket gateway structurally wrong on FaaS?** Persistent connections hold the sandbox open, so every idle minute of a held connection is billed at full rate, and connection count equals instance count — the worst of both models: container-style always-on cost with none of a container's multiplexing (thousands of connections on one process).
4. **Your function calls a database; traffic multiplies 20× and the database falls over. What happened and what are the fixes?** Platform-managed scale-out turned 20× traffic into 20× concurrent connections in seconds — a step function no pool on the DB side absorbed. Fixes: reserved concurrency as a quota, a proxy/pooler layer, or moving the write path behind a queue with consumer-paced draining — the downstream-protection layer FaaS removes by default.
5. **What exactly do you give up portability-wise by going deep on FaaS?** The runtime contract (event shapes, lifecycle rules like "no background work after return"), platform identity/IAM wiring, log and trace sinks, and orchestration primitives — all re-implemented per provider. Containers couple you to an image plus an orchestration API that clouds, on-prem clusters, and edge runtimes all speak; the coupling delta is the portability delta.

## Key Takeaways

- The fork is **who owns idle time**: FaaS bills work and absorbs idle; containers bill capacity and hand idle cost (and warm-start latency freedom) to you.
- Cold starts are a tail-and-crisis tax concentrated at scale-out; they are bought away with provisioned concurrency, which is idle billing reintroduced — the trade is explicit, not eliminated.
- Execution ceilings and the one-request-per-instance model are contractual shapes: long jobs, held connections, and custom runtimes are structurally container workloads regardless of price.
- Cost is a curve, not a constant: utilization and input-size drift move the crossover, so re-cost workloads whose traffic or payload shape changes.
- The production answer is usually hybrid — warm container services for the steady core, queue-triggered functions for the spiky edge — with queues ensuring cold starts land as lag, never as user-facing latency.

## Cross-References

- [Scaling Up vs Out: Why-Not Handbook](./scaling-up-vs-out.md) — the horizontal-scaling arithmetic both models rely on, and its limits.
- [Stateless vs Stateful: Why-Not Handbook](./stateless-vs-stateful.md) — why per-instance state changes the fleet math for containers.
- [Push vs Pull: Why-Not Handbook](./push-vs-pull.md) — the queue pacing that makes the hybrid pattern safe.
- [Serverless Internals](../../cloud/advanced/serverless.md) — the platform mechanics behind scale-to-zero.
- [Lambda](../../cloud/aws/lambda.md) — the canonical FaaS contract: limits, lifecycle, pricing.
- [Firecracker](../../cloud/virtualization/firecracker.md) — the microVM substrate most function sandboxes run on.
- [Autoscaling](../../cloud/autoscaling.md) — the reactive scale-out loop containers depend on.
- [Spot and Preemptible Capacity](../../cloud/spot-preemptible.md) — the other "cheap capacity" model and its eviction semantics.
- [Containers, cgroups, namespaces: Connection Atlas](../connection-atlas/containers-cgroups-namespaces.md) — the shared isolation substrate.
- [Containers and Resources: Assumptions Hunt](../assumptions-hunt/containers-and-resources.md) — resource-limit assumptions behind both models.
- [Kubernetes Pod Lifecycle: Follow-up Tree](../followup-tree/kubernetes-pod-lifecycle.md) — warm-path startup, readiness, and termination mechanics.
- [Infrastructure Trade-offs](../../trade-offs/infrastructure-tradeoffs.md) — the quick-reference table for platform choices.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
