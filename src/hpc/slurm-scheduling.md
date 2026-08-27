# Slurm and HPC Scheduling

A 100,000-core cluster is a $200M machine that idle-wastes half a million dollars a day if scheduled badly. Slurm (Simple Linux Utility for Resource Management) is the scheduler that runs most of the world's top supercomputers and a huge population of university and industrial clusters, and its design answers a question Kubernetes was never forced to answer: how do you allocate *whole nodes* to *long, rigid* jobs fairly, when a single user's 4,000-node job would otherwise starve everyone?

## Architecture: The Parts That Matter

Slurm is a deliberately small set of daemons:

- **slurmctld** - the central controller (one active, one backup) holding the queue, the node state, and the scheduling policy. Its crash is survivable because state is checkpointed and the backup takes over.
- **slurmd** - one per compute node; forks the user's job steps, reports node health back.
- **munge** - credential-mustering daemon providing shared-nothing auth: every message carries a cryptographically signed credential with UID/gid embedded. HPC chose this over central token services because a scheduling cluster must not have a single auth service that can become a scheduling bottleneck.
- **slurmdbd** - the accounting DB (job history, fairshare data), the only stateful external dependency.

Users interact through `sbatch` (submit batch script), `srun` (launch parallel steps), `squeue` (inspect), and `sinfo` (node state). A batch job is a shell script annotated with `#SBATCH` resource requests: `-N 32 -n 1024 --mem=200G -t 04:00:00 -p gpu`. Time limits are mandatory input to the scheduler, which is a bigger cultural difference from cloud autoscaling than any implementation detail: HPC scheduling is *planning*, not reacting.

## FIFO, Backfill, and the Reason Backfill Exists

The naive policy is strict FIFO: jobs start in submission order when resources free up. FIFO is maximally fair by arrival and maximally wasteful in practice, because the queue head is usually the biggest job - while it waits for 256 free nodes, 200 idle nodes sit empty because a 32-node job behind it could have used them *without delaying anyone*.

**Backfill** is the fix: keep FIFO priority for the queue *reservation*, but let a later, smaller job start now if it will finish before it would delay the first job's reservation. The reservation is called the job's *shadow time*, computed from the scheduler's simulation of when the blocked job could start assuming nothing else is scheduled. This is "aggressive" (EASY) backfill as used by essentially every production site; "conservative" backfill instead reserves a shadow for *every* queued job, which prevents starvation of later jobs by floods of small ones but finds far fewer opportunities.

The simulation below shows the canonical effect on one 256-node day: same makespan (the big job dominates the tail either way - backfill does not and must not delay it), but mean bounded stretch (response time / service time) collapses because small interactive jobs stop waiting behind the whale:

```python
# FIFO vs EASY backfill on a 256-node cluster. Jobs: (submit_h, nodes, dur_h, name).
# Bounded stretch = (start - submit + duration) / duration.
import heapq, statistics

jobs = [
    (0, 96, 3, "J1"), (0, 96, 3, "J2"), (1, 64, 4, "J3"),
    (2, 256, 6, "J4-big"),           # arrives while cluster ~full: must queue
    (3, 16, 1, "J5"), (4, 8, 1, "J6"), (5, 32, 2, "J7"),
    (6, 8, 1, "J8"), (7, 16, 1, "J9"), (8, 32, 1, "J10"),
]
NODES = 256

def simulate(backfill):
    t = 0.0
    free = NODES
    running = []   # (end_time, nodes, name)
    queue = []     # FIFO list
    pending = sorted(jobs, key=lambda j: j[0])
    start = {}
    last_end = 0.0
    while pending or queue or running:
        while pending and pending[0][0] <= t:
            queue.append(pending.pop(0))
        while running and running[0][0] <= t:
            _, nodes, name = heapq.heappop(running)
            free += nodes
        # keep scheduling at the current instant while anything fits
        progressed = True
        while progressed:
            progressed = False
            if queue:
                st, nn, dur, name = queue[0]
                if nn <= free:
                    heapq.heappush(running, (t + dur, nn, name))
                    start[name] = t
                    free -= nn
                    queue.pop(0)
                    progressed = True
                elif backfill and running:
                    # first job's shadow: earliest start assuming no preemption
                    acc, shadow = free, t
                    for e, nodes, _ in sorted(running):
                        shadow, acc = e, acc + nodes
                        if acc >= nn:
                            break
                    need = nn - free
                    i = 1
                    while need > 0 and i < len(queue):
                        st2, nn2, d2, name2 = queue[i]
                        if nn2 <= need and t + d2 <= shadow:
                            heapq.heappush(running, (t + d2, nn2, name2))
                            start[name2] = t
                            free -= nn2
                            need -= nn2
                            queue.pop(i)
                            progressed = True
                        else:
                            i += 1
        if running:
            last_end = max(last_end, max(e for e, _, _ in running))
            next_done = min(e for e, _, _ in running)
        else:
            next_done = float("inf")
        next_arrival = pending[0][0] if pending else float("inf")
        nxt = min(next_done, next_arrival)
        if nxt == float("inf"):
            break
        t = nxt
    makespan = last_end
    stretch = statistics.mean((start[n] - st + d) / d for st, nn, d, n in jobs)
    return makespan, stretch

for label, bf in (("pure FIFO    ", False), ("backfill     ", True)):
    mk, st = simulate(bf)
    print(f"{label} makespan={mk:5.2f} h  mean bounded stretch={st:5.2f}")
```

Output:

```text
pure FIFO     makespan=13.00 h  mean bounded stretch= 4.05
backfill      makespan=13.00 h  mean bounded stretch= 1.35
```

The subtle invariant that makes backfill safe: a backfilled job may never delay the shadow reservation of any higher-priority job. The simulator (and Slurm) enforce this by requiring `t + duration <= shadow`. In practice, sites bound the damage of *estimate error* - a job that lies about its duration can invalidate every reservation computed from it - by requiring accurate `-t` time limits and killing jobs that exceed them. This is why HPC users who write `-t 48:00:00` "to be safe" on 2-hour jobs actively harm their teammates' latency: the scheduler reserves against the declared 48 hours, so the shadow for the job behind it moves 46 hours into the future.

## Fairshare: Sharing by Historical Usage

Priority in Slurm is a weighted sum: `priority = w_fairshare*F + w_age*A + w_jobsize*J + w_partition*P`. The interesting term is fairshare: every user/association gets a target share of the cluster (configured in a hierarchical account tree), and their current *usage factor* decays over a configurable half-life (default 7 days via `PriorityDecayHalfLife`). A user who consumed 2x their share yesterday sees their priority sink below users who were recently idle; a user who has been idle for two half-lives has fully "healed" to their base share.

This is fundamentally different from Kubernetes' per-namespace quotas or YARN's queues: it is *proportional sharing with memory*, designed so that the right long-run behavior emerges without hard caps that would idle the machine. The classic failure mode is the half-life interacting with deadline-driven academic calendars: everyone heals during break, everyone submits at semester start, and the cluster thrashes - which is why sites tune decay half-life and add preemption QOS levels for high-priority classes.

## GPUs, Topology, and Whole-Node Semantics

Three HPC-flavored resource features matter in interviews because cloud systems have been reinventing them:

- **GRES** (generic resources) allocates GPUs/FPGAs per job: `--gres=gpu:a100:8`. The scheduler binds specific device files via cgroups; note that Slurm does fair allocation of the *requested* resource count, not utilization - a job asking for 1 of 8 GPUs on a node makes the node partially allocated, and the remaining 7 GPUs wait for jobs that fit the remaining memory/CPU envelope.
- **Topology-aware scheduling.** `topology.conf` describes the switch tree; Slurm prefers to pack a job's nodes under the common ancestor with the smallest bandwidth cost. Kubernetes met this need years later with NUMA/device plugin topology hints.
- **Whole-node/exclusive allocation.** `--exclusive` forbids sharing nodes at all, for jobs whose performance is sensitive to cache/interference. The HPC default is actually *shared-nothing nodes with exclusive CPU cores per job step*, enforced by cgroups - the same isolation goal cloud "dedicated instance types" solve commercially.

## Slurm vs Kubernetes: The Operational Comparison

| Dimension | Slurm | Kubernetes |
|---|---|---|
| Unit of scheduling | whole nodes (or sockets/cores), rigid | pods (elastic, co-located) |
| Job duration model | hours-days, declared time limit | service lifetime / short Jobs |
| Queue semantics | central queue + reservations + backfill | scheduler queue without backfill; batch via Volcano/Kueue add-ons |
| Fairness | historical fairshare with decay | namespace quotas / LimitRanges (static) |
| Network assumptions | dedicated fabric (InfiniBand/Slingshot), topology-aware placement | overlay/SDN, topology hints |
| Elasticity | none within a job (MPI ranks are fixed) | autoscaling native |
| Gang scheduling | native (all-or-nothing job start) | needs Volcano / coscheduling plugin |

The convergence trend is real: AI training workloads pushed Slurm to add container support (pyxis/enroot) and Kubernetes to add batch scheduling (Kueue, Volcano) - each adopting the other's core abstraction. The honest rule of thumb remains: tightly-coupled HPC (MPI, rigid ranks, topology-sensitive) stays on Slurm; loosely-coupled batch and services converge on Kubernetes; large ML shops increasingly run both, with Slurm owning the training cluster and Kubernetes owning inference and everything HTTP.

## References

- SchedMD Slurm documentation, "Quick Start Administrator" and `slurm.conf` man page (scheduler parameters, PriorityType): <https://slurm.schedmd.com/quickstart_admin.html>
- SchedMD documentation, "Scheduling Configuration Guide" (backfill and reservations): <https://slurm.schedmd.com/sched_config.html>
- SchedMD documentation, "Priority/multifactor" (fairshare, decay half-life): <https://slurm.schedmd.com/priority_multifactor.html>
- Mu'alem and Feitelson, "Utilization, predictability, workloads, and user runtime estimates in scheduling the NASA iPSC/860" (JPDC 2001 - the runtime-estimate/backfill foundation): <https://doi.org/10.1016/S0743-7315(00)00003-2>
- Parallel Workloads Archive (real HPC job traces used to validate schedulers): <https://www.cs.huji.ac.il/labs/parallel/workload/>
