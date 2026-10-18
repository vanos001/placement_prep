# "A deadlock involves heavy CPU usage"

## Overview

This claim comes from monitoring practice: dashboards default to CPU graphs,
so "something is wrong" becomes "CPU is high", and the two get fused. The
fused version is wrong for deadlock specifically — the canonical liveness
failure is *silent*: blocked threads burn no cycles while the system dies.
This page separates the liveness failures (deadlock, livelock, starvation) by
their CPU signatures, works through what a deadlocked system actually looks
like on a monitoring dashboard, and explains why detection means thread-state
analysis rather than utilization graphs.

## The Claim, Stated Fairly

The strongest common form: "A deadlocked system is thrashing — the threads
are fighting over resources, so the box runs hot; if CPU were low, the system
would be fine. Deadlock is just extreme contention." This is a real mental
model, not a straw man: it correctly describes *livelock* and busy-wait bugs,
which do saturate cores, and it correctly describes systems where deadlock
and CPU saturation coexist as effects of a common cause (overload leading to
pool exhaustion). The error is the direction of causation: deadlock itself
consumes nothing.

## Verdict

**False.** Deadlocked threads are blocked, not running — the scheduler never
schedules them, so CPU usage attributable to the deadlock is near zero while
threads, locks, connections, and memory are consumed invisibly.

## Why People Believe It

The kernel of truth has three pieces. First, *livelock* genuinely burns CPU:
threads that repeatedly acquire, conflict, back off, and retry are running at
100% while making no progress — "spinning on nothing" looks exactly like the
claim. Second, busy-wait implementation bugs (polling a flag without
sleeping) produce hot, stuck systems that get labeled "deadlock" in
retrospective. Third, correlation: an overloaded service can saturate CPU and
separately exhaust a connection pool into deadlock; the dashboard then shows
both at once, and the CPU spike gets the blame.

What the model misses is the scheduler's role. A blocked thread is not on any
run queue; it costs nothing until it is woken. The resources a deadlock
consumes are *pooled capacity* — threads, locks, database connections, memory
for stacks — and those do not appear on a CPU graph.

## The Correct Formulation

| Failure | State of the involved threads | CPU signature | Progress |
|---|---|---|---|
| Deadlock | Blocked in a wait-for cycle | ~0% attributable | None, silently |
| Livelock | Running, retrying, conflicting | ~100% | None, loudly |
| Starvation | Runnable but never chosen (or always losing races) | Low to high depending on cause | None for the victim |
| Busy-wait bug | Running, polling | ~100% on one or more cores | None until flag flips |

The correct statement: a deadlock is a cycle in the wait-for graph — each
thread holds a resource the next one needs. The threads are all *blocked*,
so the operating system spends zero cycles on them. What is consumed is the
held resources and the threads themselves: a request-handling thread deadlocked
on a lock is a request-capacity unit removed from the pool, permanently, and
with 8 MB of stack reserved behind it. Two hundred deadlocked request threads
remove two hundred capacity units and hold roughly 1.6 GB of stack memory —
with CPU at idle levels.

Detection follows the definition: walk the thread states (thread dumps via
`jstack`, Go's goroutine profile, the runtime's blocked-state views) and look
for the cycle, or let the runtime do it (the JVM's deadlock detector,
Linux `lockdep` in debug, Go's all-goroutines-asleep detector). CPU graphs
detect livelock and busy-wait; they are blind to deadlock.

## Where It Breaks

**The dashboard scenario.** A service deadlocks at 03:00. The CPU graph is
flat and near-idle — nothing pages on CPU. Requests time out upstream, so
latency alerts fire late; meanwhile every worker thread is blocked holding
its database connection, so the pool empties and even *healthy* code paths
that need a connection start failing. Post-incident, the team that greps CPU
graphs finds nothing and concludes "no resource was exhausted" — when in fact
every resource except CPU was.

**The inverse trap.** A livelocked backoff loop (retry-after-conflict with
zero sleep) shows 100% CPU and no progress. The CPU-first mental model
concludes "deadlock with contention" and adds more threads — which makes the
livelock worse. The correct diagnosis (running-but-not-progressing) comes
from thread-state analysis, the same tool as for deadlock, which is why the
two failures must be distinguished *before* choosing a fix.

**The memory-only footprint.** 200 deadlocked threads at the Linux default
8 MB thread stack reserve ~1.6 GB of address space and pin 200 pool
connections to the database. The database sees 200 idle-in-transaction
sessions. Nothing spins; nothing heats; the bill is paid entirely in capacity.

## Practical Implications

- Alert on invariants, not on CPU: request latency percentiles, pool
  saturation, transaction age, and thread-state counts (blocked vs runnable)
  catch deadlocks; CPU catches livelock and busy-wait.
- Keep thread-dump capture wired up *before* the incident: `jstack`,
  goroutine dumps, or language-equivalents, taken on latency-alert triggers.
- Prevent by construction: global lock ordering, `try_lock` with timeouts,
  and transaction-level wait-die/wound-wait schemes break the Coffman
  conditions that every deadlock needs.
- Distinguish the three liveness failures by signature (blocked ~0% CPU;
  running-no-progress ~100%; victim-starved mixed) before changing
  concurrency parameters — the fixes are different and partially opposed.
- Model deadlock cost as capacity loss: threads, connections, and memory —
  not cycles.

## Interview Questions

### A service is deadlocked. What does its CPU usage look like, and why?

Near zero, attributable to the deadlock: every deadlocked thread is blocked,
so the scheduler never runs it. The consumption is in pooled capacity —
threads, locks, connections, stack memory — which CPU graphs do not show.

### How do deadlock, livelock, and starvation differ in cause and CPU signature?

Deadlock: a wait-for cycle; threads blocked; ~0% CPU. Livelock: threads
running, repeatedly conflicting and retrying; ~100% CPU, no progress.
Starvation: a runnable thread never scheduled or always losing races; CPU
varies with the cause. Deadlock is detected by state analysis, livelock by
progress metrics, starvation by fairness analysis.

### Your team's on-call runbook says "high CPU means deadlock; restart the box." When does that rule fail?

Two ways: a true deadlock shows *low* CPU, so the rule never fires —
detection must come from thread states and latency invariants; and a
livelock or busy-wait loop shows high CPU but restarting treats the symptom
while the fix (add backoff/sleep, remove the conflict loop) is in code.

## Key Takeaways

- Deadlocked threads are blocked: zero CPU, full cost — paid in threads,
  connections, locks, and memory.
- CPU graphs detect livelock and busy-wait, never deadlock; thread-state
  analysis detects all three.
- The three liveness failures have distinct signatures and distinct fixes;
  fusing them under "contention" leads to wrong remedies (more threads for a
  deadlock adds only more victims).
- Alerting on invariants (latency, pool saturation, blocked-thread counts)
  is the operational form of the correction.

## Cross-References

- [Deadlock Detection and Prevention](../../concurrency/deadlock-detection.md)
  — wait-for graphs, Coffman conditions, and the detectors named above
- [Lock Starvation](../../concurrency/lock-starvation.md) — the liveness
  failure with the mixed CPU signature
- [Why-Not Handbook: Concurrency Primitives](../why-not-handbook/concurrency-primitives.md)
  — avoiding the cycle by choosing the right primitive
- [Assumptions Hunt: Concurrency and Scheduling](../assumptions-hunt/concurrency-and-scheduling.md)
  — scheduler assumptions behind "blocked costs nothing"
- [Failure Casebook: Therac-25](../failure-casebook/therac-25.md) — a race
  condition whose cost was correctness, not cycles
- [OS Overview](../../os/overview.md) — where blocked threads live in the
  scheduler
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- E. G. Coffman, M. J. Elphick, A. Shoshani. *System Deadlocks*. ACM
  Computing Surveys, 1971. (The four conditions every deadlock satisfies.)
- Oracle. *jstack — Stack Trace* (the tool whose output reports
  "Found one Java-level deadlock").
  <https://docs.oracle.com/en/java/javase/21/docs/specs/man/jstack.html>
