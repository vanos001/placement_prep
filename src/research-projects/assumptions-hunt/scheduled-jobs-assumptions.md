# Scheduled Job Assumptions: What "It Runs Every Night at 2" Silently Promises

## Overview

Cron is the oldest and most trusted scheduler in computing, and that trust hides a pile of unstated preconditions: that the machine is up at the scheduled minute, that the previous run finished, that local time means the same thing twice a year, and that "the cron server" is one machine rather than every replica in a fleet. Each of these assumptions fails in a characteristic, low-drama way — a job silently skipped during a deploy window, two overlapping runs corrupting an aggregation, a twice-yearly 2:30 AM job that simply never fires on clock-change nights — and none of them produces an error message, because from the scheduler's point of view everything worked exactly as specified.

This chapter audits the scheduling family with the collection's five-step pattern. The contract citations come from the POSIX `crontab` specification (which defines five-field matching and says nothing about catch-up runs), the systemd timer documentation (whose `Persistent=` option exists precisely because cron does not catch up), and the Kubernetes CronJob controller documentation (whose `startingDeadlineSeconds` and `concurrencyPolicy` fields encode the same two assumptions as explicit, configurable behavior). The overlap and double-fire scenarios are worked as concurrency problems, which is what they are: a schedule is a trigger, and triggers know nothing about the lifetime of the work they start.

## Assumption 1: "Cron Runs Exactly at the Scheduled Time"

### The taught rule

A job scheduled for `30 2 * * *` runs at 02:30, every night, on the minute.

### The hidden assumptions

- Cron's matching granularity is the minute, but its *delivery* granularity is not: `crond` wakes, matches jobs, and spawns them — under load, that spawn competes with everything else on the machine, and nothing in the contract bounds the delay.
- The scheduled minute is the *start of eligibility*, not a deadline. POSIX defines when a job matches the time; it does not promise the job started within any interval of that time. A busy box (page-cache pressure, a backup saturating I/O, a thousand other jobs landing at 02:00 because everyone picked round numbers) delays the fork.
- Downstream, the delay compounds: a job that starts late writes data late, and every consumer that assumes "02:30 data is there by 02:35" inherits an unstated dependency on machine load at 02:30.
- Clock discipline interacts here too: an NTP step backward can make crond either skip or repeat a wall-clock minute, which the clocks-and-time chapter treats as a general property rather than a cron quirk.

### Counterexample

A reporting cluster runs 400 cron jobs, most scheduled on the hour and half-hour because humans picked round times. At 02:00 each night, 220 of them fire at once on a machine also running a filesystem backup. The scheduler spawns them within seconds, but I/O contention stretches the last job's start to 02:07, and an aggregation job that reads a table the earlier jobs write starts before its inputs are complete. Nobody configured a dependency; the "02:00" schedule silently encoded both a timing promise and an ordering promise, and only the first was even approximately kept. The standard fixes: spread schedules deliberately (jitter the minutes the way retry jitter spreads load), move inter-job ordering into the job orchestrator where it is stated, and monitor *start-time drift* (actual minus scheduled) as a first-class metric, not an accident discovered by a confused analyst.

### What changes when the assumption is removed

Corrected statement: *a cron line expresses eligibility per minute, not execution at that minute; latency from schedule to start is a load-dependent property you must measure and budget.* Concretely: spread minute fields across the fleet, set explicit deadlines and alerting on start drift, and treat "the 02:30 report" as a data-availability SLO with its own numbers instead of a side effect of a crontab line.

### Consequences

The interview probe "your nightly job started at 02:07 — is that a bug?" separates candidates who know cron's actual contract from those who repeat it. The follow-up — "what if it started at 02:25?" — is Assumption 2 in disguise, and the strong answer covers both drift within the minute's long tail and skips.

## Assumption 2: "Missed Runs Execute Later"

### The taught rule

If the machine was down at 02:30, the job just runs when it comes back — cron would not miss it.

### The hidden assumptions

- Classic cron does exactly the opposite: it matches jobs against the current minute and moves on. A minute that passes while the machine is down (or crond is not running) is a minute no job will ever be matched against again. There is no queue, no backlog, no catch-up.
- The catch-up behavior people remember belongs to *other* tools: anacron runs missed daily jobs after boot, and systemd timers with `Persistent=true` store the last run time and fire on the next boot if the schedule was missed. Those are deliberate features with names — their existence is evidence the default does not have the property.
- Kubernetes CronJobs make the policy explicit: without `startingDeadlineSeconds`, missed schedules accumulate in a concurrency window and the controller may skip runs entirely (its documentation describes the counting rule); with a deadline, a run missed past it is marked missed and not started.
- Even where catch-up exists, "run later" can be wrong: a nightly report for Monday run on Tuesday afternoon may be meaningless, and an automatic catch-up of 14 missed runs after a long outage (anacron's behavior across many days) may be worse than skipping them.

### Counterexample

A maintenance window moves a database host for 20 minutes spanning 02:30. The nightly reconciliation job scheduled at 02:30 does not run that night — silently, with no error, because cron has no concept of a missed run to report. The reconciliation gap surfaces nine days later when balances drift far enough for a finance check to fail, and the on-call's first hypothesis ("the job failed") is wrong: the job never ran and never failed. The detection that would have caught it is a *heartbeat* assertion — "a successful run marker exists for every expected schedule slot" — which is a different check from job-failure alerting and is the one most teams do not have. The fix combines the heartbeat with an explicit policy: for catch-up-capable schedulers, decide per job whether a missed run should fire once late (anacron/`Persistent`), fire within a bounded deadline (Kubernetes `startingDeadlineSeconds`), or be skipped and flagged.

### What changes when the assumption is removed

Corrected statement: *classic cron skips missed minutes without record; catch-up is a named feature of specific schedulers with specific semantics, and the right policy — late-run, bounded-late, or skip-with-alert — is a per-job decision, not a default.* Operational form: every scheduled job writes a success marker with its scheduled slot, a monitor asserts marker presence per slot, and the runbook states the missed-run policy in one sentence.

### Consequences

"Your cron host reboots over the weekend. Which jobs run Monday?" is the complete interview probe, and the strong answer names three tools and three policies instead of one instinct. The background-jobs follow-up ladder treats scheduler choice as one of the job-system design axes, and this assumption is the fine print on that axis.

## Assumption 3: "Jobs Never Overlap"

### The taught rule

The job runs once a night and takes minutes; the schedule is generous; overlap is not a concern worth engineering for.

### The hidden assumptions

- Nothing in cron prevents concurrent instances. The schedule triggers; the previous instance's runtime is invisible to the trigger. A job that degrades from 5 minutes to 65 under a slow query silently starts running against itself at the next firing.
- Overlap damage scales with what the job touches: double-sent notifications (duplicate side effects), two writers to the same aggregate (lost updates), two readers-then-writers of a "current state" file (check-then-act races from the concurrency chapter, at cron timescale).
- The naive fix — a lockfile — has its own failure mode: a crashed run leaves a stale lock, and every subsequent run skips forever unless the lock has ownership (PID, boot ID, lease) and expiry. A lockfile without a liveness story converts overlap into silent skipping, which is frequently worse.
- Distributed schedulers multiply the trigger: every replica's crond fires the job, so a fleet of 10 runs the nightly job 10 times unless leadership or external locking exists — the double-fire problem, and the reason Kubernetes CronJobs are controller-managed singletons by design.

### Counterexample

A 5-minute data sync grows to 70 minutes after an upstream API adds latency. The cron schedule is every 30 minutes. From that week on, two instances always run concurrently: both read the same upstream page, both write, and the merge layer's last-write-wins makes the final state depend on finish order — which flips nightly, so downstream counts wobble with no error anywhere. The durable fix is a lease at job scope: acquire an advisory lock (flock on a shared volume for single-host, a lease-row or lock service for distributed) held for the job's duration with expiry tied to a heartbeat, make "could not acquire" a *normal* skip path logged at info level, and alert on skip-rate — a rising skip rate is the early-warning signal that runtime has outgrown schedule. `concurrencyPolicy: Forbid` is the same decision made declaratively in Kubernetes, with the controller owning the bookkeeping.

### What changes when the assumption is removed

Corrected statement: *a schedule triggers; exclusivity is a separate mechanism (lease with expiry and heartbeat) that must be designed for the job's concurrency damage, and in fleets the trigger itself must be made single-valued by leadership.* The design questions in order: what breaks if two run (nothing: allow; duplicates: idempotency; corruption: lock), who owns the lock lifecycle, and what does the system do when the lock is stale — and each answer belongs in the job's runbook.

### Consequences

"What happens if your cron job takes longer than its interval?" is the canonical probe; the memorable answer is that the two failure directions — overlap damage and stale-lock skipping — are different bugs requiring different fixes. This is the scheduling-timescale version of the check-then-act race from the concurrency chapter, and the lease mechanics are the same ones the consensus-leases chapter develops for infrastructure.

## Assumption 4: "DST Is Handled by Cron"

### The taught rule

Cron schedules in local time, and the OS handles daylight saving time, so the 2:30 AM job stays at 2:30 AM.

### The hidden assumptions

- The OS handling is exactly the bug. In the spring transition, local times 02:00–03:00 do not exist in many zones (for example, most of the US and EU): a job scheduled at 02:30 matches no wall-clock minute and is skipped — twice a year, silently, by the matching logic working as specified.
- In the fall transition, an hour occurs twice: depending on the implementation and the zone's ambiguity resolution, a 01:30 job may run twice, and jobs scheduled in the repeated hour interact with file timestamps and logs in ways no test exercises.
- Zone databases change: a government moves the transition date or abolishes DST, tzdata updates, and local-time schedules shift meaning on an OS package update nobody associates with the job system. The clock chapter's timezone-explicit-encoding assumption is the general case; cron lines are its most common unencoded instance.
- The fix direction is a trade: schedules in UTC are transition-immune but move the local wall-clock time each spring and fall (02:30 local becomes 01:30/03:30), which is wrong for human-anchored jobs (reports due "at start of business") and right for machine-anchored ones (cache warmups, log rotation).

### Counterexample

A compliance job must run "daily at 02:30 Europe/Berlin" to snapshot records before the business day. Its crontab line says `30 2 * * *` on a host in `Europe/Berlin`. On the spring-forward night, 02:30 Berlin does not exist; the job does not run; the snapshot gap is discovered at the next audit. On the fall-back night the picture inverts and is zone-dependent: the EU transition repeats the 02:00–03:00 hour, so 02:30 Berlin fires twice and the snapshot's "last write" is whichever run finished second, while in the United States the repeated hour is 01:00–02:00 and 02:30 fires exactly once. The honest engineering statement: both transitions create silent anomalies, and which one hits a given job depends on the zone's rules. The only robust choice is to know which of your jobs are human-anchored versus machine-anchored, encode the zone explicitly per job (many crons support `CRON_TZ`; systemd calendar events accept explicit timezones), and add the same per-slot heartbeat from Assumption 2 — which fires a "missing slot" alert on every transition night where a job was silently skipped, converting a twice-yearly surprise into a monitored event.

### What changes when the assumption is removed

Corrected statement: *cron matches wall-clock minutes in the job's configured zone; DST transitions delete and duplicate local times, so every schedule needs an explicit zone, an anchoring decision (human or machine time), and a per-slot heartbeat to catch the skipped run.* Operational form: `CRON_TZ` or scheduler-level zone per job line, UTC for machine-anchored jobs, and a documented twice-yearly check for human-anchored ones near the transition boundaries.

### Consequences

The interview probe "what happens to a 2:30 AM cron job on the night the clocks change?" has a precise two-part answer (skipped in spring in most zones; possibly duplicated in fall, zone-dependent) and a strong follow-through: the fix is not "use UTC" but "know which time you mean and monitor slots." The clocks-and-time chapter carries the general timezone-encoding assumption this one specializes to schedulers.

## Interview Questions

1. **Is it a bug that a 02:00 cron job started at 02:07?** No — the contract is per-minute eligibility, not execution at that minute; start drift is load-dependent and should be measured. The bug-shaped part is consumers assuming data availability tied to the nominal time without an SLO.
2. **The host reboots during a job's scheduled window. Does the job run later?** Not in classic cron — the minute is unmatched and gone. Catch-up is a named feature elsewhere (anacron, systemd `Persistent=true`, Kubernetes `startingDeadlineSeconds`), each with distinct semantics; the per-job policy (late-once, bounded, skip-and-alert) should be explicit.
3. **Your nightly job starts taking longer than its interval. What breaks and what do you build?** Overlapping instances with duplicate side effects and lost updates; build a lease with expiry and heartbeat, treat skip-on-conflict as a normal logged path, alert on skip rate, and consider `concurrencyPolicy: Forbid` in Kubernetes.
4. **Ten replicas each run crond. How many times does the nightly job fire?** Ten, absent leadership or external locking — the double-fire problem. Fix with leader election, a distributed lease, or a singleton scheduler (controller-managed CronJob).
5. **What happens to a 2:30 AM local-time job on DST transition nights, and what is your defense?** Spring: skipped, the local time does not exist in most zones; fall: possible duplication depending on zone. Defense: explicit zone per job, human-vs-machine anchoring decision, and a per-slot heartbeat to catch silent skips.

## Key Takeaways

- A cron line expresses per-minute eligibility, not execution timing: start drift is real and load-dependent, and missed minutes are skipped without record in classic cron.
- Catch-up behavior is a named feature of specific schedulers (anacron, systemd `Persistent`, Kubernetes deadlines), each with semantics you must choose per job, not a default you can assume.
- Exclusivity is a separate mechanism from scheduling: leases with expiry and heartbeat for overlap, leadership or singleton controllers for fleet double-fire, and skip-on-conflict as a monitored normal path.
- DST deletes and duplicates local wall-clock times: encode the zone explicitly, decide human- versus machine-anchoring, and monitor schedule slots rather than only job failures.
- The system-level detection for all four assumptions is the same artifact: a success marker per expected slot, asserted by a monitor — it catches late starts, skipped runs, and double-fires with one mechanism.

## Cross-References

- [Timeouts and retries](timeouts-and-retries.md) — the sibling audit of time-based assumptions in request paths.
- [Clocks and time](clocks-and-time.md) — the general timezone, monotonicity, and NTP assumptions cron inherits.
- [Concurrency and scheduling](concurrency-and-scheduling.md) — the check-then-act races that cron-scale overlap reproduces.
- [Background jobs escalation chain](../followup-tree/background-jobs.md) — job-system design axes, escalated question by question.
- [Message queues escalation chain](../followup-tree/message-queues.md) — queues versus schedulers as delivery mechanisms for deferred work.
- [Scheduling and queueing](../connection-atlas/scheduling-queueing.md) — the dependency map for deferred-execution mechanisms.
- [Consensus and leases](../connection-atlas/consensus-leases.md) — lease semantics reused as the job-exclusivity mechanism.
- [POSIX crontab specification](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/crontab.html) — the five-field matching contract, with no catch-up or exclusivity promises.
- [systemd.timer documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html) — `Persistent=` and calendar events with explicit timezone support.
- [Kubernetes CronJob concepts](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/) — `startingDeadlineSeconds` and `concurrencyPolicy` as explicit missed-run and overlap policies.
