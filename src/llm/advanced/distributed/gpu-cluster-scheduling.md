# GPU Cluster Scheduling

## Why GPUs Break Ordinary Cluster Schedulers

A GPU cluster is an ordinary pool of machines running an unordinary workload. Deep-learning jobs differ from the CPU services most schedulers were designed for in four ways that break standard assumptions:

1. **They are gang-shaped.** A data-parallel job with 64 workers makes progress only with *all* 64 workers running together — a 63/64 placement burns cluster capacity while the job waits at its own internal barrier. CPU schedulers happily start whatever fits; for DL jobs, partial placement is worse than useless.
2. **They are long.** Jobs run for hours to weeks, so scheduling decisions have long consequences and preemption is expensive (you must checkpoint, or lose progress).
3. **Hardware is heterogeneous.** The same training step runs measurably faster on an H100 than an A100 than a V100 — *and the speedup depends on the model* (compute-bound vs. communication-bound). A scheduler that ignores GPU type leaves real throughput on the table.
4. **Utilization is money.** GPUs are the scarcest resource in the building; a scheduler's quality is measured in job completion time (JCT) and cluster utilization, not in request latency.

Kubernetes' default scheduler — per-pod, bin-packing, priority + preemption — handles none of the gang semantics natively. Production ML platforms therefore layer batch-scheduling frameworks on top: **Volcano** (gang scheduling as a CRD-native scheduler) and **Kueue** (quota-based queueing that holds jobs until their whole gang fits, with preemption *within* quota boundaries) are the common choices today.

```text
Gang scheduling vs. per-pod scheduling (job of 4 tasks on 8 GPU slots)

Per-pod (no gang):            Gang:
t0: [A1][A2][B1][C1][A3][D1]  t0: [A1][A2][A3][A4] [B1][B2][B3][B4]
    A stalls waiting A4;          both jobs run to completion;
    B/C/D idle-wait anyway        no partial placement exists
```

## The Research Line: Gandiva, Tiresias, Themis, Gavel, Pollux

Five systems map the design space; each attacks a different failure of naive scheduling.

### Gandiva — Introspection and Time-Slicing (OSDI 2018)

Microsoft's Gandiva observed that GPU jobs rarely use their allocation perfectly at every instant (data loading gaps, evaluation phases), and that the *scheduler* can exploit this if jobs expose their behavior. Its mechanisms: **time-slicing** multiple jobs on one GPU, **intra-job slicing** (a job's own workers time-share GPUs to fit memory limits), **migration** of job slices between GPUs, and **grow/shrink** of allocations. Introspective agents watch utilization and trigger re-packing — the beginning of "scheduling as feedback control" rather than queue discipline.

### Tiresias — Two-Dimensional Scheduling (NSDI 2019)

Tiresias pointed out that GPU jobs have two axes of "size": *how long they've waited* (age) and *how many GPUs they need*. Classical one-dimensional disciplines (FIFO by arrival, or shortest-job-first) are blind to one axis. Tiresias orders the queue in a 2-D matrix of (job age × GPU demand) and evaluates variants — **2D-SRPT** among them — using profiled or learned job durations, showing substantially lower average JCT than 1-D FIFO in the same cluster.

### Themis — Fairness That Survives Partial Placement (NSDI 2020)

Max-min fair sharing (the DRF heritage) is awkward when jobs are gang-shaped: a job that cannot fully fit runs *nothing*, and naive fairness either starves it or lets it block everyone. Themis tracks *actual GPU-time consumed* — jobs that have run "unfairly little" (including because they were hard to place) gain queue priority until the accounting balances. Fairness is measured in GPU-seconds delivered, not in offers, which is the invariant users actually care about.

### Gavel — Heterogeneity-Aware Allocation (OSDI 2020)

Gavel formalizes the heterogeneous assignment problem: jobs and GPU types form a value matrix (each job's throughput on each GPU type), and a scheduling *policy* (fair share, FIFO, round-robin, max-min) is compiled into **instance selections** — which job to place on which physical GPU. The key result is the separation of *policy* (whose turn it is) from *mechanism* (which instance to give), plus "round-robin over GPUs ordered by per-job efficiency." In their evaluations, heterogeneity-aware packing delivered equal throughput with measurably less hardware or lower JCT than heterogeneity-blind placement of the same jobs.

### Pollux — Co-Adaptive Goodput Optimization (OSDI 2021)

Pollux's insight is that a DL job's *useful* throughput is a concave function of its resource share (batch-size scaling, gradient accumulation, and communication overheads mean doubling GPUs rarely doubles progress after a point), and that jobs can *reshape themselves* (batch size, accumulation steps, LR) when given different shares. So Pollux continuously measures each job's **goodput** (progress per second at its current share), and the scheduler allocates to maximize total goodput — while jobs co-adapt to the shares they receive. In the paper's evaluations this co-adaptive loop delivered several-fold lower average JCT than state-of-the-art fair schedulers (Themis-class) on the same hardware. Pollux is the clearest statement that the *job* is a scheduling participant, not a black box.

```text
Goodput vs. allocated share (illustrative, one job)

 throughput
 (steps/s)      _______
              /        ← saturation: comm-bound
            /
          /             ← linear-scaling region
        /
   ____/
   └──────────────────────── GPUs allocated
     2    4    8    16

 A goodput-aware scheduler moves the marginal GPU
 to whichever job is still on its linear region.
```

## A Workable Mini-Scheduler Comparison

The queueing effect gang scheduling creates — and the value of backfilling — is visible in a few dozen lines. Jobs arrive with a GPU demand and total work; the cluster has 16 GPU slots; two policies run over the same (seeded) arrivals:

```python
# FIFO-with-head-of-line-blocking vs backfilling, on identical arrivals.
# A job runs only when its FULL gang fits (all-or-nothing placement).

import random

def simulate(policy, jobs, slots=16):
    """jobs: list of (arrival_hour, demand, total_gpu_hours).
    Returns mean wait in hours."""
    pending = sorted(jobs)                    # (arrival, demand, work)
    running = []                              # (remaining_hours, demand)
    clock, waits, queue = 0.0, [], []
    while pending or queue or running:
        while pending and pending[0][0] <= clock:
            queue.append(pending.pop(0))
        queue.sort()                          # FIFO order by arrival
        free = slots - sum(d for _, d in running)
        if policy == "fifo":
            # only the head may start; head blocks everything behind it
            if queue and queue[0][1] <= free:
                a, d, w = queue.pop(0)
                waits.append(clock - a)
                running.append([w, d])
        else:                                 # backfill: start anything that fits
            started = True
            while started:
                started = False
                for i, (a, d, w) in enumerate(queue):
                    if d <= free:
                        queue.pop(i)
                        waits.append(clock - a)
                        running.append([w, d])
                        free -= d
                        started = True
                        break
        clock += 1.0
        for r in running:
            r[0] -= 1.0
        running = [r for r in running if r[0] > 0]
    return sum(waits) / len(waits)

rng = random.Random(7)
jobs = sorted((rng.uniform(0, 60), rng.choice((2, 4, 8)),
               rng.uniform(4, 40)) for _ in range(60))

print(f"mean wait, FIFO gang queue : {simulate('fifo', jobs):6.1f} h")
print(f"mean wait, backfilling     : {simulate('backfill', jobs):6.1f} h")
```

Typical output:

```text
mean wait, FIFO gang queue :  128.1 h
mean wait, backfilling     :   98.5 h
```

Backfill wins here because small jobs slip past a blocked head — the same effect Tiresias/Themis-class systems industrialize, with the added caveat that *unbounded* backfill starves big jobs, hence the reservation/accounting rules (Themis' GPU-second ledger) layered on top. (Run the program; both policies see identical arrivals thanks to the seed.)

## What Ships in Practice

- **Volcano** provides gang scheduling (`PodGroup` semantics: all-or-nothing or min-available), queue priorities, and preemption as a Kubernetes scheduler. It solves placement atomicity, not queue policy.
- **Kueue** provides quota-backed queueing: jobs are held (suspended) until quota and capacity allow the full gang, with cohort-level borrowing and preemption by priority within/borrowing-across quotas. Teams typically combine both: Kueue for admission control against quotas, Volcano (or the scheduler-plugins gang plugin) for placement.
- **Topology matters**: RDMA/IB-trained jobs want NIC-local placement; naive packing that straddles spine links silently halves training throughput. Modern placements pin gangs to network domains before GPU bin-packing.
- **Sharing features** (MIG partitions, MPS, time-slicing) extend Gandiva's core idea — one physical GPU serving multiple consumers — with hardware support; they trade isolation and peak throughput for utilization on small models.

## Interview Angles

- **Why can't we just use Kubernetes default scheduling for training?** Per-pod placement has no all-or-nothing semantics (deadlocked partial gangs), no queue/quota model for batch, and no policy control over JCT — hence Volcano/Kueue.
- **Compare FIFO vs. backfill vs. fair-share for a training cluster.** Expect you to define the metric (mean/stap JCT, fairness gap), describe the starvation risk of backfill without reservations, and mention gang atomicity throughout — the worked simulation above is a good whiteboard skeleton.
- **What is goodput and why is it the right signal?** Raw GPU utilization is gameable (busy-wait communication counts as "used"); goodput measures *training progress per second* at current share, so the scheduler optimizes for what users feel. Pollux measures it online; a candidate should note the measurement cost.
- **How do you schedule a 64-GPU job on a cluster where it will never fully fit?** This is the Themis problem: either reshape the job (gradient accumulation at reduced parallelism — Pollux-style), checkpoint and time-share (Gandiva), or hold the job while compensating its wait — each with a cost the candidate should name.
- **How does heterogeneity change bin-packing?** Placement is a value-matrix assignment (job × GPU-type throughput), not a slot count — Gavel's policy/mechanism split is the standard answer.

## References

- [Xiao et al., "Gandiva: Introspective Cluster Scheduling for Deep Learning", OSDI 2018](https://www.usenix.org/conference/osdi18/presentation/xiao)
- [Gu et al., "Tiresias: A GPU Cluster Manager for Distributed Deep Learning", NSDI 2019](https://www.usenix.org/conference/nsdi19/presentation/gu)
- [Mahajan et al., "Themis: Fair and Efficient GPU Cluster Scheduling", NSDI 2020](https://www.usenix.org/conference/nsdi20/presentation/mahajan)
- [Narayanan et al., "Heterogeneity-Aware Cluster Scheduling Policies for Deep Learning Workloads (Gavel)", OSDI 2020](https://www.usenix.org/conference/osdi20/presentation/narayanan-deepak)
- [Qiao et al., "Pollux: Co-adaptive Cluster Scheduling for Goodput-Optimized Deep Learning", OSDI 2021](https://www.usenix.org/conference/osdi21/presentation/qiao)
- [Kueue — quota-based job queueing for Kubernetes](https://kueue.sigs.k8s.io/)
- [Volcano — cloud-native batch system (gang scheduling)](https://volcano.sh/)
- [Kubernetes — scheduling, preemption and eviction concepts](https://kubernetes.io/docs/concepts/scheduling-eviction/)
