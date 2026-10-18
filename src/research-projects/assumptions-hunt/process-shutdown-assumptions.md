# Process Shutdown Assumptions: What "Kill It and Restart" Silently Promises

## Overview

Restart is the most common remediation in operations, and it rests on a shutdown story nobody audits: that SIGTERM stops the process, that in-flight work survives the stop, that shutdown code is the mirror image of startup code, and that the restarted process resumes cleanly from where its predecessor died. Each stage of that story has an unstated precondition — a handler that was actually installed, a grace period longer than the slowest request, hooks that run on the kill signal actually delivered, state that was actually durable — and each precondition fails in a specific, reproducible way: a process that ignores SIGTERM until SIGKILL erases it, requests killed mid-write at second 30 of a 30-second grace window, buffered data lost because shutdown hooks do not run on SIGKILL, and a restarted instance that meets the stale registrations and locks its dead predecessor left behind.

The deeper pattern is that *shutdown is a negotiated protocol between the process, the orchestrator, and the network*, not an event the process controls. The orchestrator's contract is a timeout and a final, unignorable signal; the network's contract is that established connections and registered addresses outlive the process by seconds to minutes; the process's contract is whatever its signal handlers, hooks, and flush paths actually implement — frequently less than the design document claims. This chapter audits the four assumptions in the collection's five-step pattern, complementing the sibling [concurrency and scheduling](concurrency-and-scheduling.md) chapter (startup and thread-lifetime assumptions) and the [containers and resources](containers-and-resources.md) audit (OOM kills as the shutdown nobody schedules).

## Assumption 1: "SIGTERM Stops the Process"

### The taught rule

To stop a process cleanly, send SIGTERM; the process terminates, and SIGKILL is only for runaways.

### The hidden assumptions

- SIGTERM's default action is termination, but *default* means "when no handler is installed". Any process that installs a handler — which graceful shutdown, by definition, does — has taken over the signal's meaning, and nothing enforces that the handler finishes or even runs to completion.
- The orchestrator's enforcement is a deadline, not a guarantee: Docker stop sends SIGTERM and SIGKILL after a default of 10 seconds; Kubernetes sends SIGTERM and SIGKILL when `terminationGracePeriodSeconds` (default 30) expires, as the [pod lifecycle documentation](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) specifies. The grace period is the only cleanup budget the design gets, and teams routinely budget nothing against it.
- SIGKILL is untrappable and unignorable — the [signal(7) manual](https://man7.org/linux/man-pages/man7/signal.7.html) lists it among the signals that cannot be caught, blocked, or handled — so everything past the deadline happens without any application code.
- Standard signals do not queue: a second SIGTERM sent while one is pending coalesces into one delivery, so the operator reflex of "sending more SIGTERMs" adds no urgency, and real-time queueing signals are a different, opt-in mechanism.

### Counterexample

A consumer service traps SIGTERM to drain its work queue and exits when the queue is empty. Under an incident, a poisoned message sends the drain loop into a retry stall; the orchestrator's SIGTERM arrives, the handler notes it but cannot finish, and at second 30 of the 30-second grace period SIGKILL terminates the process mid-`write()` — half a batch flushed, no error logged, because SIGKILL leaves no application trace. The restart resumes from the last checkpoint and reprocesses the half-batch, and the duplicate output is discovered downstream by a customer, not by the logs. The defenses are budget arithmetic and observability: drain must have a deadline strictly inside the grace period (say, 25 seconds of the 30), the handler must log entry and exit so "stuck in drain" is visible, and shutdown must be rehearsed under load exactly as [graceful-degradation](../followup-tree/graceful-degradation.md) drills rehearse degradation — the failure mode only appears when a real drain is slow.

### What changes when the assumption is removed

Corrected statement: *SIGTERM is a request whose handling the process owns and whose enforcement is a deadline; the contract is "finish or be killed at T", so cleanup paths must be bounded well under T, must log their progress, and must be idempotent because SIGKILL can cut them at any instruction.* "Clean shutdown" is a property of the slowest cleanup path relative to the grace period, not of the handler's existence.

### Consequences

The interview question "what happens when Kubernetes deletes a pod?" expects the sequence — preStop hook, SIGTERM, grace timer, SIGKILL — and the senior follow-up is budget arithmetic: name the grace period, the drain deadline, and what dies at the boundary. The [process lifecycle follow-up](../followup-tree/process-lifecycle.md) escalates the same sequence from signals to process states.

## Assumption 2: "In-Flight Requests Survive the Shutdown"

### The taught rule

Graceful shutdown means: stop accepting new requests, finish the ones in flight, then exit. Every framework offers it; the flag is one line.

### The hidden assumptions

- "Stop accepting" closes the listener, but *established* connections and *load balancer state* are outside the process: client-side connection pools hold keep-alive connections open for minutes, and a load balancer that was told nothing routes new requests down existing pooled connections until its own health check flips.
- Deregistration lags: removing the pod from endpoints, updating the load balancer's pool, and letting DNS TTLs expire each take their own interval, and they run concurrently with — not before — the SIGTERM clock (the [kubernetes-pod-lifecycle follow-up](../followup-tree/kubernetes-pod-lifecycle.md) walks the sequencing; the [DNS assumptions](dns-assumptions.md) chapter audits the TTL half).
- The grace period must exceed the slowest in-flight request, not the average: a p99 of 45 seconds under a 30-second grace period guarantees a tail of requests killed mid-response, which clients experience as connection resets exactly during deploys.
- Requests killed after the deadline do not fail loudly on the server: the response never completes, the client may retry, and whether that retry is safe is a property the [idempotency assumptions](idempotency-assumptions.md) chapter audits — shutdown quietly creates the duplicate-request traffic that retry design was supposed to handle.

### Counterexample

A compute-heavy endpoint has p50 of 3 seconds and p99 of 45 seconds (cold caches, large payloads). Deploys are routine: the orchestrator stops accepting at t=0, sends SIGTERM, and the handler waits for in-flight work. At t=30 SIGKILL fires while 6% of requests — the p99 tail — are still running; every one of those clients sees a reset connection, and the retry wave doubles load on the replacement pod just as it warms up. The fix is sequencing plus budgeting: a preStop hook that sleeps a few seconds (or deregisters and waits for endpoint propagation) *before* SIGTERM so pools stop sending, a drain deadline under the grace period, and — the part most designs skip — measuring the deploy window's reset rate so the mismatch between p99 and grace is a number, not a rumor.

### What changes when the assumption is removed

Corrected statement: *in-flight survival is a three-party negotiation — the process stops listening, the routing layer stops sending, and the grace period exceeds the slowest request — and all three must be configured, because the process controls only the first.* The load the shutdown sheds does not disappear; it is retried or re-routed, and the [backpressure](../connection-atlas/backpressure.md) atlas page covers where that pressure lands.

### Consequences

"Why do error rates spike during every rolling deploy?" is the canonical probe: the answer that names connection-pool lag, endpoint propagation, and the p99-versus-grace mismatch is the senior one, and it reframes deploys as a load event rather than a neutral swap.

## Assumption 3: "Startup and Shutdown Are Symmetric"

### The taught rule

If startup registers listeners, opens connections, and loads state, shutdown runs the same list backwards: deregister, close, flush. The code exists; therefore it runs.

### The hidden assumptions

- Shutdown code runs only under conditions the runtime defines. The [JVM's shutdown-hook contract](https://docs.oracle.com/javase/8/docs/api/java/lang/Runtime.html) is explicit: hooks run on normal exit and on SIGTERM-style termination, but not when the VM aborts, not under `Runtime.halt`, and not on SIGKILL — so the flushing logic that makes the design review pass is exactly the code SIGKILL skips.
- "Flush" is not "durable": data written into the page cache before exit survives process death but not host or power loss; only `fsync` (and `fsync` on the containing directory) makes shutdown writes durable — the distinction the [filesystem durability](filesystem-durability.md) chapter owns.
- In containers, the process is PID 1 with different rules: the kernel does not apply default signal dispositions to PID 1, so an application that never installs a SIGTERM handler ignores `docker stop` until the deadline, and PID 1 must also reap orphaned children or the container fills with zombies — the [zombie-and-orphan mechanics](../../os/processes/zombie-orphan.md) the OS book documents and the [containers-cgroups-namespaces atlas](../connection-atlas/containers-cgroups-namespaces.md) connects to resource limits.
- Asymmetry in the other direction: `atexit` handlers and destructors do not run on `_exit`, threads are killed mid-section without unwinding, and locks held at death are simply gone — the process does not "clean up", the operating system does.

### Counterexample

A telemetry service buffers events in memory and flushes to storage via a shutdown hook: 10,000 events buffered at steady state, flush takes about 4 seconds. An OOM kill (the unscheduled shutdown the [containers and resources](containers-and-resources.md) chapter audits) or a grace-period SIGKILL ends the process without running any hook; 10,000 events — roughly 40 seconds of telemetry at peak — vanish with no error, because the loss happened below the logging layer. After the third "gap" complaint, the fix reframes the design: periodic durable flushes every 5 seconds sized against the loss budget, an at-least-once handoff to a queue for anything that must not vanish, and the hook demoted from "the durability mechanism" to a latency optimization. The corrected rule: anything that must survive shutdown must already be durable *before* SIGTERM arrives, not written during it.

### What changes when the assumption is removed

Corrected statement: *shutdown code is best-effort by contract — it runs on the exits the runtime grants and is skipped everywhere else — so durability must not depend on it: flush periodically, treat the hook as an optimization, and assume SIGKILL between any two instructions when reasoning about state.* Startup/shutdown symmetry is a nice-to-have; state-on-kill correctness is the requirement.

### Consequences

"Your shutdown hook didn't run — when does that happen?" is a probing interview question with a compact answer: abort, halt, SIGKILL, OOM, host loss. It also explains a production pattern: services that must not lose data flush on intervals and treat shutdown as a final, opportunistic drain.

## Assumption 4: "A Restart Resumes Where the Process Left Off"

### The taught rule

Restarting is safe: the process holds its state in durable storage or an audit log, so the new instance picks up where the old one stopped — that is what write-ahead logs and checkpoints are for.

### The hidden assumptions

- The durable state lags the process by design: a WAL records what *will* be applied, a checkpoint freezes a moment that was current at flush time, and replay re-derives the gap — so "resume" means "re-execute", and re-execution is only safe if the work is idempotent or fenced (the [idempotency assumptions](idempotency-assumptions.md) chapter carries that half).
- Identity does not transfer: the dead instance's entries in service registries, lock tables, and leader elections outlive it by TTLs — a lock held until expiry, a registry entry until the heartbeat deadline, a DNS record until TTL — and the restarted instance coexists with its predecessor's ghost (the [distributed lock assumptions](distributed-lock-assumptions.md) chapter works the lock case; the [service-discovery audit](service-discovery-assumptions.md) works the registry case).
- Overlapping deploys run two instances concurrently: the old one drains while the new one starts, so "resume" includes a window where both process the same queues, cache the same keys, and write the same tables — the design must tolerate cooperation between a dying process and a newborn one.
- Cold-start economics differ from steady state: caches empty, JITs cold, connection pools at size zero, so the restarted instance is slower exactly when retries from Assumption 2 arrive — a compound load event that turns "restart" into the traffic spike the [timeouts and retries](timeouts-and-retries.md) audit measures.

### Counterexample

A scheduler service holds a 60-second-TTL lock on its work partition and dies at t=0; the replacement starts at t=5, sees the lock still held, and idles — correct so far. But the *old* instance's in-flight job, started at t=−1, completes at t=8 and writes its result, while the replacement, having misread the lock table's clock skew, also claims the partition at t=7 and re-runs the same job: two writes, one notification pipeline, and a duplicate report delivered to customers. The resume worked; the *overlapping ghosts* did not. Defenses: fencing tokens that make stale claimants detectable, generation numbers in written records, startup that verifies the predecessor is truly gone (drained or dead) before claiming, and treating every TTL — lock, lease, registration — as part of the restart budget.

### What changes when the assumption is removed

Corrected statement: *a restart resumes from durable state plus re-execution, coexists with the predecessor's TTL-bound ghosts (locks, registrations, DNS), and overlaps the new instance with the old one's tail — so correctness requires idempotent work, fenced claims, and a startup path that accounts for all three.* The [interrupts-and-async atlas](../connection-atlas/interrupts-async.md) frames the general principle: the system's reaction to interruption is designed at the boundaries, not in the handler.

### Consequences

The interview probe "walk me through what happens between the old pod dying and the new one serving" is Assumptions 1–4 in sequence, and the strongest answers volunteer the ghost period — locks, registry entries, DNS — that naive designs skip. The general lesson closes the chapter: shutdown and restart are one distributed-systems transaction with a messy overlap window, not two independent events.

## Interview Questions

1. **What exactly happens when Kubernetes terminates a pod, and where do designs usually go wrong?** preStop hook, SIGTERM, grace timer (default 30 s), SIGKILL. Designs go wrong by budgeting no drain deadline inside the grace period, assuming endpoints update before SIGTERM, and putting durability in shutdown hooks that SIGKILL skips.
2. **Why does a JVM shutdown hook not guarantee data durability?** Hooks run on normal exit and SIGTERM-style termination but are skipped on abort, halt, and SIGKILL; and "flushed" without `fsync` still dies with the host. Durable state must be written periodically before shutdown, not during it.
3. **Error rates spike during every rolling deploy. Give three mechanisms.** Pooled keep-alive connections keep sending after the listener closes; endpoint/registry propagation lags the SIGTERM clock; and the p99 exceeds the grace period, so the tail is killed and retried — doubling load onto the warming replacement.
4. **A restarted instance duplicates its predecessor's work. Name the state that outlived the process.** Held locks until TTL expiry, registry/DNS entries until heartbeat and TTL deadlines, in-flight work still completing, and durable logs that replay re-executes — requiring fencing tokens, idempotency, and overlap-tolerant startup.

## Key Takeaways

- SIGTERM is a request, the grace period is a deadline, and SIGKILL is the real guarantee: cleanup must be bounded well inside the grace period, logged, and idempotent under interruption at any instruction.
- In-flight survival is a three-party negotiation — stop listening, stop routing, and grace exceeds p99 — and deploys are load events because the shed traffic is retried.
- Shutdown code is best-effort by contract (skipped on SIGKILL, abort, and OOM), so durability lives in periodic flushes, not in exit hooks.
- A restart inherits its predecessor's ghosts: locks until expiry, registry and DNS entries until TTL, in-flight work still finishing — correctness needs fencing, idempotency, and overlap-aware startup.
- The auditable question for any service is arithmetic, not intention: grace period versus drain deadline versus p99, flush interval versus loss budget, TTL versus restart time.

## Cross-References

- [Follow-up tree: Kubernetes pod lifecycle](../followup-tree/kubernetes-pod-lifecycle.md) — the orchestrator-side escalation of the termination sequence audited in Assumptions 1 and 2.
- [Follow-up tree: process lifecycle](../followup-tree/process-lifecycle.md) — states, signals, and reaping from the process side, the ground under Assumption 3.
- [Connection atlas: backpressure](../connection-atlas/backpressure.md) — where the traffic shed at shutdown lands, and how the retry wave is absorbed.
- [Connection atlas: interrupts and async](../connection-atlas/interrupts-async.md) — signals and asynchronous interruption as the general mechanism behind Assumption 1.
- [Concurrency and scheduling](concurrency-and-scheduling.md) — the sibling audit of thread lifetimes, timeouts as guarantees, and instant-startup beliefs.
- [Containers and resources](containers-and-resources.md) — OOM kills as unscheduled shutdowns and PID 1 under cgroup limits.
- [Filesystem durability](filesystem-durability.md) — the flush-versus-fsync distinction that decides whether shutdown writes survive.
- [Distributed lock assumptions](distributed-lock-assumptions.md) — locks that outlive their holders, the ghost-state half of Assumption 4.
- The [signal(7) manual](https://man7.org/linux/man-pages/man7/signal.7.html), the [Kubernetes pod lifecycle documentation](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), and the [JVM Runtime shutdown-hook contract](https://docs.oracle.com/javase/8/docs/api/java/lang/Runtime.html) are the primary sources above; all were fetched and verified this session.
