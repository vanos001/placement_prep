# Backfilling: Filling Scheduler Gaps in HPC Queues

A batch scheduler that starts jobs strictly in submission order pays a utilization tax that grows with job-width diversity. When the queue head needs 6 of an 8-node machine and only 3 nodes are free, strict FIFO leaves 3 nodes idle — sometimes for hours — until the head can run. Backfilling is the family of scheduling disciplines that lets *later, smaller* jobs leapfrog the queue head into those idle nodes, subject to a promise: the leapfrogging must not delay the start time that earlier jobs have been *guaranteed* (a reservation). It is the workhorse behind most production batch systems — Slurm's default `sched/backfill` plugin, PBS Pro, LSF, and the schedulers of virtually every top-500 site — and its design space is a live case study in trading fairness, utilization, and predictability under uncertain information.

The scope split for this repo: [HPC Infrastructure](./hpc-infra.md) surveys batch systems as a whole (queuing, accounting, topology-aware placement), [GPU cluster scheduling](../llm/advanced/distributed/gpu-cluster-scheduling.md) covers the gang-scheduling and elasticity angle used for training fleets, and [Airflow](../data-engineering/airflow.md) handles DAG orchestration where "scheduling" means dependency triggering, not resource reservation, and [Slurm & HPC Scheduling](./slurm-scheduling.md) shows the operator-facing FIFO-vs-backfill picture with its own 256-node simulation. This page owns the backfilling decision itself: the reservation mechanics, the EASY-vs-conservative split, and what runtime-estimate inaccuracy does to all of it.

## The Utilization/Fairness Squeeze

The tension backfilling resolves is measurable. Under strict FIFO, average response time is optimal for jobs that arrive in size order, but real workloads mix 1-node 5-minute jobs with 512-node 20-hour jobs, so the head-of-line job starves everything behind it that could have used the idle fraction of the machine. Classic measurements from the IBM SP2 era (Feitelson & Weil, IPPS 1998, doi 10.1109/ipps.1998.669970) showed the SP2 scheduler losing double-digit fractions of utilization to head-of-line blocking, with the loss concentrated in exactly the wide-job/narrow-job interleave that characterizes real logs. The paradox is that pure SJFS (shortest-job-first) would fix utilization but is unworkable in a service scheduler: users game runtime estimates, and the queue loses any sense of order that site policy can enforce.

Backfilling's insight is that you can keep FIFO *accountability* while recovering most SJFS *utilization*, because the idle nodes are "free" in a specific sense: they are slack between now and the earliest time the blocked head job could possibly start. A job can consume that slack if, and only if, it is guaranteed to be gone — or its resource use accounted — by the time the head's reservation begins. Everything in this page is a way of defining and enforcing that guarantee under the one inescapable complication: nobody knows how long jobs actually run. Schedulers act on user-supplied estimates (or walltime limits), and the gap between estimate and reality is where both the wins and the pathologies of backfilling live.

## Reservations: EASY vs Conservative

The canonical policies differ in how many guarantees they hand out. **Conservative backfilling** gives every queued job a reservation at the moment it enters the queue: walking the queue in FCFS order, each job's start time is the earliest minute when its node count can be assembled given running jobs' (estimated) finish times and the reservations already promised ahead of it. A backfill candidate may start now only if starting it cannot push *any* reservation later — checked by recomputing the reservation timeline with the candidate hypothetically occupying its nodes. **EASY backfilling** (the variant analyzed for the IBM SP2 by Mu'alem & Feitelson, IEEE TPDS 2001, doi 10.1109/71.932708) makes exactly one reservation — for the queue head — and lets any job backfill that does not delay it. EASY is what "production backfilling" almost always means; conservative buys stronger fairness guarantees at the price of a more rigid timeline that cannot exploit late-arriving slack.

```text
backfill window, 8-node machine, head job H needs 6 nodes at time T
     nodes: 8 7 6 5 4 3 2 1 0
running:  A A A A A A A A          (A ends ~T-20, frees 2)
free now:                    2 nodes
head H (6 nodes): reservation computed at T (when A ends + 4 more nodes free)
                    <---- slack window ---->
candidate B (2 nodes, est 15 <= T-now):  fits inside slack -> BACKFILL ok
candidate C (3 nodes, est 40 > T-now):   would still hold 3 nodes at T
                                          -> H would wait -> REJECT
candidate D (1 node,  est 60 > T-now):   2 free + D takes 1 = 1 short of 6
                                          -> H waits -> REJECT
rule: candidate may run iff (its estimated finish) fits inside the
      reservation slack, or leftover capacity at T still covers H
```

The two policy knobs interact with queue order. Both variants typically pair with FCFS ordering; pairing with SJFS ordering changes the reservation *pattern* (short jobs' reservations are near, so wide jobs backfill around them) and is the standard fix for SJFS's starvation problem. A third dimension is the **extra-nodes rule**: when a candidate would make the head's reservation *earlier* (by finishing before it), some schedulers allow it to start even if the head could have started sooner without it — the "gap-fill vs extra-nodes" distinction that shows up as measurable throughput differences on bursty logs in the Feitelson-group studies.

## Estimates Are the Fuel (and the Failure Mode)

Every reservation is computed from *claimed* runtimes, so estimate accuracy is a schedulability property, not a nicety. Under-estimates poison the machine: a job that blows its estimate holds nodes past its reservation, invalidating every promise made on top of it (production systems therefore kill at the walltime limit — an under-estimated job gets killed, not forgiven). Over-estimates waste differently: a head job claiming 10 hours with a 30-minute actual blocks (or delays) backfills that would have fit. The Feitelson & Weil IPPS'98 study found users systematically inflate estimates, and that *truncating* them (cap estimates at some multiple of the observed mean) measurably improved slowdown without touching user code. The standard fairness metric, bounded slowdown (BSLD = max(wait/run, c) with a small constant c to protect short jobs), is the lens all of these studies share — the demo below reports mean and max BSLD alongside makespan and utilization so the trade-offs are visible per policy.

| Failure mode | Mechanism | Classic remedy |
|--------------|-----------|----------------|
| Under-estimate | Job overruns reservation; promises downstream collapse | Kill at walltime; shrink backfill window |
| Over-estimate | Inflated reservations push backfills out | Estimate truncation; user feedback |
| Estimate inflation game | Users pad estimates to win reservations | Site caps; historical (measured) runtimes |
| Backfill starvation of wide jobs | Stream of small jobs keeps re-filling slack | bf_one_resv_per_job-style limits; partition minima |

## Backfilling in Production Schedulers

Slurm's backfill plugin exposes the design space directly as configuration (all names below verified from slurm.schedmd.com/sched_config.html):

| Parameter | Verified meaning (Slurm docs) |
|-----------|-------------------------------|
| `bf_window` | How long, in minutes, into the future to look when determining when and where jobs can start |
| `bf_max_job_user` | Maximum number of jobs to initiate per user in each backfill cycle |
| `bf_max_job_test` | Maximum number of jobs consider for backfill scheduling in each backfill cycle |
| `bf_max_time` | Maximum time in seconds the backfill scheduler can spend before discontinuing |
| `bf_resolution` | Time resolution of backfill scheduling |
| `bf_one_resv_per_job` | Disallow adding more than one backfill reservation per job |
| `bf_continue` | Resume an interrupted backfill cycle from where it stopped |
| `bf_interval` | Seconds between backfill scheduling attempts |

The knobs encode real failure experience: `bf_max_job_test` bounds the O(queue × timeline) cost of reservation recomputation, `bf_resolution` trades timeline granularity against CPU, and `bf_one_resv_per_job` prevents a single job from spawning multiple reservations as its shadow time moves. PBS Pro and LSF implement the same policy shape (dedicated time / reservation-based backfilling respectively) behind different names, and sites with gang-parallel or topology-constrained jobs add the wrinkle that a "reservation" is a multi-node *contiguous placement*, not just a node count — the point where backfilling meets topology-aware scheduling (see [HPC Infrastructure](./hpc-infra.md)).

## Worked Demo

```python
"""Backfilling sim: strict FCFS vs EASY backfill vs conservative backfill.
Deterministic discrete-time model, 8-node cluster, 1-minute steps.
Reservations are computed from USER ESTIMATES; completions happen at ACTUAL
runtimes -- exactly the mismatch backfilling lives with."""
JOBS = [  # (id, submit_min, est_min, actual_min, nodes)
    (1, 0, 100, 80, 4), (2, 0, 25, 25, 2), (3, 5, 40, 40, 3), (4, 10, 150, 150, 6),
    (5, 10, 20, 20, 1), (6, 20, 60, 60, 2), (7, 30, 30, 30, 4), (8, 45, 90, 90, 5),
    (9, 60, 25, 25, 1), (10, 75, 50, 50, 2),
]
N = 8

def shadow(acq, rel, free, need):
    """Earliest minute when `need` nodes are available. `rel` = (time, nodes)
    releases (running jobs' estimated finishes + reserved jobs' completions);
    `acq` = (time, nodes) acquisitions by previously reserved jobs."""
    for tt in sorted(set([0] + [x for x, _ in acq + rel])):
        avail = free + sum(n for x, n in rel if x <= tt) - sum(n for x, n in acq if x <= tt)
        if avail >= need:
            return tt
    return max(x for x, _ in acq + rel) if (acq or rel) else 0

def simulate(policy):
    t, free = 0, N
    running = []            # (job, end_actual, end_est, nodes)
    pend = sorted(JOBS, key=lambda j: (j[1], j[0]))
    queue, backfill, starts = [], 0, {}
    while pend or queue or running:
        for j in list(pend):
            if j[1] <= t:
                pend.remove(j); queue.append(j)
        for r in list(running):
            if r[1] <= t:
                running.remove(r); free += r[3]
        queue.sort(key=lambda j: (j[1], j[0]))
        est = {j[0]: j[2] for j in queue}
        rel_run = [(r[2] - t, r[3]) for r in running if r[2] > t]   # est releases
        def start(j):
            nonlocal free
            queue.remove(j)
            running.append((j, t + j[3], t + est[j[0]], j[4]))
            free -= j[4]
            starts[j[0]] = t
        progressed = True
        while progressed:
            progressed = False
            if policy == "fcfs":                    # head-of-line blocking only
                if queue and free >= queue[0][4]:
                    start(queue[0]); progressed = True
            elif policy == "easy":                  # protect the HEAD reservation only
                if not queue:
                    break
                head = queue[0]
                if free >= head[4]:
                    start(head); progressed = True; continue
                r_head = shadow([], rel_run, free, head[4])
                for j in queue[1:]:
                    if free < j[4]:
                        continue
                    r_after = shadow([(0, j[4])], rel_run + [(est[j[0]], j[4])],
                                     free - j[4], head[4])
                    if r_after <= r_head:           # head reservation unharmed
                        start(j); backfill += 1; progressed = True
                        break
            else:                                   # conservative: protect ALL reservations
                res, acq, rel = {}, [], list(rel_run)
                for j in queue:                     # reserve every queued job, FCFS
                    res[j[0]] = shadow(acq, rel, free, j[4])
                    acq.append((res[j[0]], j[4])); rel.append((res[j[0]] + est[j[0]], j[4]))
                for j in queue:
                    if free < j[4]:
                        continue
                    if res[j[0]] == 0:              # its reservation is NOW: normal start
                        start(j); progressed = True
                        break
                    other = [q for q in queue if q[0] != j[0]]
                    res2, acq2, rel2 = {}, [(0, j[4])], list(rel_run) + [(est[j[0]], j[4])]
                    ok = True
                    for q in other:
                        res2[q[0]] = shadow(acq2, rel2, free - j[4], q[4])
                        acq2.append((res2[q[0]], q[4])); rel2.append((res2[q[0]] + est[q[0]], q[4]))
                        if res2[q[0]] > res[q[0]]:
                            ok = False; break
                    if ok:                          # backfill: nobody's reservation slips
                        start(j); backfill += 1; progressed = True
                        break
        if running:
            t += 1
    makespan = max(starts[j[0]] + j[3] for j in JOBS)
    return makespan, backfill, starts

busy = sum(j[3] * j[4] for j in JOBS)
print(f"backfilling sim: {N} nodes, {len(JOBS)} jobs, busy work = {busy} node-min")
print(f"{'policy':<14}{'makespan':>9}{'util%':>7}{'backfill':>10}{'mean BSLD':>11}{'max BSLD':>10}{'max wait':>10}")
results = {}
for pol in ("fcfs", "easy", "conservative"):
    mk, bf, starts = simulate(pol)
    results[pol] = starts
    waits = {j[0]: starts[j[0]] - j[1] for j in JOBS}
    bsld = [max(waits[j[0]] / j[3], 1.0) for j in JOBS]
    print(f"{pol:<14}{mk:>9}{100 * busy / (N * mk):>7.1f}{bf:>10}{sum(bsld)/len(bsld):>11.2f}{max(bsld):>10.2f}{max(waits.values()):>10}")
print()
print("per-job wait (min):")
print(f"  job nodes submit actual  fcfs  easy  conservative")
for j in JOBS:
    jid, sub, est, act, nd = j
    w = {p: results[p][jid] - sub for p in results}
    print(f"  J{jid:<3}{nd:>5}{sub:>7}{act:>7}{w['fcfs']:>6}{w['easy']:>6}{w['conservative']:>13}")
```

```text
backfilling sim: 8 nodes, 10 jobs, busy work = 2225 node-min
policy         makespan  util%  backfill  mean BSLD  max BSLD  max wait
fcfs                350   79.5         0       2.96      8.00       215
easy                350   79.5         3       1.75      6.67       215
conservative        365   76.2         0       1.22      2.56       230

per-job wait (min):
  job nodes submit actual  fcfs  easy  conservative
  J1      4      0     80     0     0            0
  J2      2      0     25     0     0            0
  J3      3      5     40    20    20           20
  J4      6     10    150    70    70          115
  J5      1     10     20    70    15            0
  J6      2     20     60    80    65           45
  J7      4     30     30   200   200           50
  J8      5     45     90   215   215          230
  J9      1     60     25   200     0            0
  J10     2     75     50   185    70           10
```

Read the per-job table, not just the summary. EASY's three backfills are surgical: J5's wait drops 70 → 15, J9 starts the minute it submits (200 → 0), and J10 nearly halves — all without moving J1's start, i.e., without breaking the single guarantee EASY makes. Conservative instead pays *makespan* (365 vs 350) and *utilization* (76.2% vs 79.5%) on this workload: its every-job reservations froze a timeline computed from over-estimates (J1 claims 100 minutes, runs 80; J4 claims 150, runs 150), and the frozen timeline blocked an opportunistic start that strict FCFS and EASY both caught. That inversion — the "fairest" policy losing throughput — is exactly the estimate-accuracy coupling the literature keeps rediscovering, and the reason Slurm ships EASY-style backfilling with a reservation *window* rather than all-job guarantees. Note also that all three policies share the same busy work (2,225 node-min), so utilization differs only through makespan; backfilling changes *when* work runs, never *how much* there is.

## Interview Questions

1. **Why does backfilling need reservations at all — why not just "start anything that fits"?** Because without a reservation there is no notion of "later": a stream of small jobs could keep a wide head job waiting forever (starvation), and users cannot be told when their job will run. The reservation is the *contract* (fairness, predictability) that makes the opportunistic utilization recovery (backfilling) legitimate. EASY keeps one contract, conservative keeps one per job.
2. **Your site's backfill seems ineffective: utilization is fine but mean slowdown is high. What do you check first?** Estimate quality. If users inflate estimates, the head reservation is far in the future, the slack window looks empty, and nothing may backfill — or worse, everything backfills around a phantom-long reservation. Check the estimate/actual distribution, then consider truncation caps (`bf_window` shrinkage has similar effect) and `bf_one_resv_per_job` semantics.
3. **Why can conservative backfilling lose to strict FCFS on makespan, as in the demo?** Its reservations are computed from estimates and are *hard*: a wrong long estimate freezes slack that other policies would exploit, and the scheduler can neither use it nor reclaim it until completions invalidate the timeline. The guarantee has a price; whether it is worth paying depends on how accurate estimates are and how much you value wait-time predictability over raw throughput.
4. **How does gang scheduling or topology-aware placement complicate this?** The reservation stops being "N nodes at time T" and becomes "a placement": contiguous or switch-local nodes, possibly a synchronized slot across many nodes (gang). Reservation feasibility then depends on topology state, not just counts, and the backfill check must ask "does a candidate *placement* exist that doesn't invalidate promised placements?" — which is why GPU-fleet schedulers often disable classic backfilling entirely (see [GPU cluster scheduling](../llm/advanced/distributed/gpu-cluster-scheduling.md)).

## References

1. A. Mu'alem, D. G. Feitelson. *Utilization, predictability, workloads, and user runtime estimates in scheduling the IBM SP2 with backfilling*. IEEE Transactions on Parallel and Distributed Systems 12(6), 2001. https://doi.org/10.1109/71.932708 (Crossref-verified)
2. D. G. Feitelson, A. Weil. *Utilization and predictability in scheduling the IBM SP2 with backfilling*. Proc. IPPS/SPDP 1998. https://doi.org/10.1109/ipps.1998.669970 (Crossref-verified)
3. Slurm Documentation — *Scheduling Configuration Guide* (backfill plugin parameters, verbatim above). https://slurm.schedmd.com/sched_config.html
4. Feitelson et al. — *The Parallel Workloads Archive* (standard job logs with estimates used in backfilling studies). https://www.cs.huji.ac.il/labs/parallel/workload/
5. PBS Professional — scheduler and backfill documentation hub. https://openpbs.org/
