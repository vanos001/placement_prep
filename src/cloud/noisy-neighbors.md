# Noisy Neighbors & Performance Isolation

A noisy neighbor is another workload consuming a *shared* resource so heavily that your
latency degrades through no fault of your own code. It is the contention counterpart of
the failure modes in [tail latency](../distributed/fundamentals/tail-latency.md):
interference rarely moves the median - it moves the tail, which is where SLAs live.

## How One Tenant Becomes Everyone's Latency

```text
                 one physical host (cloud or your own fleet)
+-------------------------------------------------------------+
|  Tenant A pods | Tenant B pods | Tenant C pods | your pods  |  processes
+-------------------------------------------------------------+
      ^ containers: cgroup v2 (cpu.weight, cpu.max, io.max,
        io.latency, memory.high); shared page cache / LRU
+-------------------------------------------------------------+
|     LLC (L3)  ~~~  memory bandwidth (DIMM channels)         |  hw (RDT: CAT/MBA)
+-------------------------------------------------------------+
|  CPU cores (CFS)     block devices     NIC queues           |  blk-cgroup, qdiscs
+-------------------------------------------------------------+
|  hypervisor: vCPU scheduler, emulated IO, offload cards     |  VMs
+-------------------------------------------------------------+
  interference crosses every boundary unless some layer below
  the tenant enforces a limit on that resource
```

The defining property: **isolation is only as strong as the weakest layer that leaves a
resource unpartitioned.** Perfect cgroups cannot save you from a shared L3; a reserved
L3 way cannot save you from a saturated DIMM channel.

## The Interference Channels

| Channel         | Physical mechanism                         | Your symptom                    | Counter that confirms it        |
|-----------------|--------------------------------------------|---------------------------------|---------------------------------|
| CPU steal       | Hypervisor runs other VMs on your vCPU     | Uniform slowdown of everything  | `steal` field in `/proc/stat`   |
| Cache pollution | Tenant evicts your lines from shared LLC   | Stable median, fatter tail      | `perf` LLC-miss rate jump       |
| Mem bandwidth   | Saturated DIMM channels serialize accesses | Scales with your memory traffic | MBM counters via resctrl        |
| Disk I/O        | Shared device queue; co-tenant sync fsyncs | p99 write spikes on one device  | PSI `io` pressure, iostat await |
| Network         | Shared NIC rings, uplink, conntrack table  | Retransmits, periodic jitter    | ENA allowance-exceeded counters |

Two notes on the least visible ones. **CPU steal** is kernel accounting for "the vCPU
wanted to run but the hypervisor ran someone else": sustained steal above a few percent
means an oversubscribed host, and it inflates every request multiplicatively - unlike
your own GC pauses, which are additive and periodic. On EC2 the hypervisor is Nitro
(KVM-derived, offload cards), so neighbor effects appear more as enforced network and
EBS allowances than raw CPU steal. **Cache pollution** is the quiet one: no counter
"fails," but hot-path loads miss because a neighbor's scan keeps replacing your working
set - the worked model below shows how hard that hits the tail.

## Signatures and Variance Attribution

Read the shape of the latency distribution before concluding:

- **Median and tail inflate together** (multiplicative) - steal time, frequency
  throttling, or a saturated memory-bandwidth pool.
- **Median frozen, tail explodes, hit rate drops** - cache pollution: once more than 1%
  of requests take the slow path, p99 *is* the slow path. The signature most often
  misattributed to "the backend got slow."
- **Sawtooth on a period** - someone's cron or compaction, or your own burstable-credit
  exhaustion (T-family instances sink to baseline when credits run out).
- **Shapeless jitter** - queueing behind a co-tenant on an unshaped queue.

Attribution loop: (1) cross-tenant correlation - unrelated tenants on the same host
degrading in the same minute while their own workloads are flat means the cause is
shared; (2) host-level neutral observers - steal time, PSI (the `some` line is "the
share of time in which at least some tasks are stalled on a given resource"), LLC-miss
rate, iostat await - which cannot be blamed on your own deploy; (3) victim
fingerprinting - p99 up plus steal up = hypervisor neighbor, p99 up plus LLC misses up
plus steal flat = cache neighbor, p99 up plus PSI io up = disk neighbor; (4) provider
counters - EC2 ENA fires metrics "when traffic exceeds the network allowances that
Amazon EC2 defines at the instance level" (packets per second, tracked connections),
and EBS exposes queue length and burst balance. Emit per-request per-tenant percentiles
and track the p99/p50 ratio as a first-class signal; never blend tenants into one
histogram, where the victim's tail hides inside the aggressor's volume. Rule out your
own periodic work before escalating.

## Enforcement: Which Layer Actually Bounds What

| Layer      | Mechanism                            | Bounds                             | Does NOT bound                      |
|------------|--------------------------------------|------------------------------------|-------------------------------------|
| cgroup CPU | `cpu.weight`, `cpu.max` (v2)         | Scheduler share / hard quota       | LLC, memory bandwidth               |
| cgroup mem | `memory.high`, `memory.min` (v2)     | Page cache and anon reclaim        | LLC, bandwidth                      |
| cgroup io  | `io.max`, `io.latency` (v2; v1 = blk-cgroup `blkio.throttle.*`) | Device BPS/IOPS, latency targets | Mem bandwidth, SSD controller queue |
| qdisc      | `fq_codel`, `CAKE`, `HTB` + filters  | Per-class queue depth, egress rate | Host uplink congestion, ingress     |
| Hardware   | Intel RDT: CAT (L3 ways), MBA (bw %) | Cache ways, bandwidth per class    | Device DMA, NIC queues              |
| Hypervisor | Weighted vCPU scheduling, offload    | vCPU shares, IO via dedicated HW   | In-guest cache pollution            |
| Provider   | Tenancy, QoS classes, placement      | Co-tenant identity, tiers          | Everything inside your instance     |

Key cgroup v2 semantics (kernel documentation): `cpu.weight` - "All weights are in the
range [1, 10000] with the default at 100" - is work-conserving, splitting CPU only
under contention, which is exactly when you need it; use `cpu.max` for a hard ceiling.
`io.max` "limits the maximum BPS and/or IOPS that a cgroup can consume on an IO device"
- the cap tool for a shared NVMe device. `io.latency` takes per-device targets in
microseconds and is work-conserving: "as long as everybody is meeting their latency
target the controller doesn't do anything. Once a group starts missing its target it
begins throttling any peer group that has a higher target than its own latency target"
- the neighbor with the loosest target yields first. `io.cost.qos`/`io.cost.model` are
root-only knobs, so platforms must expose per-tenant `io.max`/`io.latency`.

Network: classify tenant traffic (tc filters) into qdisc classes. `fq_codel` keeps
per-flow queues with CoDel drops so one bursty flow cannot monopolize the queue; `CAKE`
adds integrated shaping and per-host fairness; `HTB` gives explicit hierarchical rate
division. Qdiscs shape egress only - ingress needs ifb mirroring or enforcement at the
sender/hypervisor. Hardware: resctrl (the RDT interface) assigns L3 ways via CAT
schemata and bandwidth percentages via MBA per class of service - the only layer that
bounds a cache-polluting neighbor, and a core reason to run bare metal (see
[bare-metal clouds](./bare-metal-clouds.md)).

## Worked Model: One Scan Evicts a Working Set

Deterministic model (fixed seeds). Tenant A serves a stable 600-key Zipf hot set;
tenant B serves a 400-key hot set, then flips to a uniform scan over 25,000 keys at the
same request rate. Requests interleave strictly A,B,A,B. A hit costs 1.2 ms; a miss
adds a 24 ms backend round trip. Compare one shared 1200-slot LRU vs a static 50/50
partition (600 slots each).

```python
# MODEL: one shared LRU vs a static 50/50 partition. Tenant A keeps a stable
# Zipf hot set; tenant B flips from a small hot set to a uniform scan phase.
# Deterministic: fixed seeds, no wall-clock input.
import random
from bisect import bisect

SLOTS, HIT_MS, MISS_MS = 1200, 1.2, 24.0  # cache slots; hit/miss service (ms)
A_HOT, B_HOT, SCAN_KEYS = 600, 400, 25000
N_REQS, WARMUP = 20000, 4000

def zipf_cdf(n, alpha):
    w, cdf, acc = [1.0 / k ** alpha for k in range(1, n + 1)], [], 0.0
    for x in w:
        acc += x
        cdf.append(acc / sum(w))
    return cdf

class LRU:                                   # dict preserves insertion order
    def __init__(self, cap):
        self.cap, self.od = cap, {}
    def lookup(self, key):
        if key in self.od:
            self.od[key] = self.od.pop(key)  # refresh recency
            return True
        self.od[key] = True
        if len(self.od) > self.cap:
            self.od.pop(next(iter(self.od)))  # evict least recent
        return False

def run(shared):                             # one interleaved A/B request stream
    one = LRU(SLOTS)
    ca, cb = (one, one) if shared else (LRU(SLOTS // 2), LRU(SLOTS // 2))
    a_rng, a_cdf = random.Random(42), zipf_cdf(A_HOT, 1.1)
    a_reqs = [bisect(a_cdf, a_rng.random()) for _ in range(WARMUP + N_REQS)]
    b_rng, b_cdf = random.Random(7), zipf_cdf(B_HOT, 1.1)
    b_quiet = [bisect(b_cdf, b_rng.random()) for _ in range(WARMUP + N_REQS)]
    rng_scan = random.Random(99)
    breqs = {"quiet": b_quiet,
             "scan": [rng_scan.randrange(SCAN_KEYS) for _ in range(WARMUP + N_REQS)]}
    out = {}
    for phase, breq in breqs.items():
        jit = {"A": random.Random(1234), "B": random.Random(5678)}
        lat, hits = {"A": [], "B": []}, {"A": 0, "B": 0}
        for i in range(WARMUP + N_REQS):
            for who, reqs, cache in (("A", a_reqs, ca), ("B", breq, cb)):
                miss = not cache.lookup(reqs[i])
                svc = (HIT_MS * jit[who].uniform(0.9, 1.1)
                       + (MISS_MS * jit[who].uniform(0.9, 1.1) if miss else 0.0))
                if i >= WARMUP:
                    hits[who] += (not miss)
                    lat[who].append(svc)
        out[phase] = tuple(v for who in ("A", "B")
                           for v in (100.0 * hits[who] / len(lat[who]),
                                     sorted(lat[who])[int(0.99 * len(lat[who])) - 1]))
    return out

shared, parted = run(True), run(False)
print("One shared LRU (%d slots) vs static 50/50 partition; A hit set = %d keys; "
      "B flips from a %d-key hot set to a %d-key uniform scan at equal request rate."
      % (SLOTS, A_HOT, B_HOT, SCAN_KEYS))
print("scenario           mode         A hit%   A p99(ms)   B hit%   B p99(ms)")
for mode, res in (("shared", shared), ("partitioned", parted)):
    for label, (ha, pa, hb, pb) in res.items():
        print("%-18s %-12s %6.2f   %8.2f   %6.2f   %8.2f" % (label, mode, ha, pa, hb, pb))
print("A p99 amplification during the scan phase: shared %.1fx vs partitioned %.2fx"
      % (shared["scan"][1] / shared["quiet"][1], parted["scan"][1] / parted["quiet"][1]))
```

Real output:

```text
One shared LRU (1200 slots) vs static 50/50 partition; A hit set = 600 keys; B flips from a 400-key hot set to a 25000-key uniform scan at equal request rate.
scenario           mode         A hit%   A p99(ms)   B hit%   B p99(ms)
quiet              shared        99.58       1.32    99.97       1.32
scan               shared        86.95      27.22     4.77      27.57
quiet              partitioned   99.31       1.32    99.75       1.32
scan               partitioned  100.00       1.32     2.37      27.57
A p99 amplification during the scan phase: shared 20.6x vs partitioned 1.00x
```

A's p99 degrades **20.6x** under the shared LRU although A did nothing: the miss rate
crossed the 1% line, so p99 lands entirely in the miss branch. The static partition
caps the damage at 1.00x; the price is B's own hit rate halving (4.77% to 2.37%)
because it can no longer freeload on spare capacity - isolation trades wasted idle
capacity for bounded tails. The LLC version of this exact effect (hardware ways instead
of slots) is what a co-tenant does to your CPU caches; CAT is the partition, resctrl
the knob.

## Tenancy Ladder and Provider QoS Classes

| Tenancy option            | What is isolated                          | What still interferes              |
|---------------------------|-------------------------------------------|------------------------------------|
| Shared instance (default) | Nothing physical; tenants share the host  | Steal, LLC, bandwidth, IO, NIC     |
| Dedicated Instance        | Hardware "dedicated to a single AWS account" | Your own co-located instances   |
| Dedicated Host            | "a physical server that is fully dedicated for your use" | Only what you co-locate |
| GCP sole-tenant node      | VMs "don't share host with VMs from other projects unless you use shared sole-tenant node groups" | Your project's own VMs |
| Bare metal                | All cores, caches, channels, PMU          | Nothing - there are no co-tenants  |

AWS is explicit that Dedicated Instances are "physically isolated at the host hardware
level from instances that belong to other AWS accounts"; what Dedicated Hosts and bare
metal add is visibility (sockets/cores, licensing) and control (RDT, SMT, counters)
rather than a new isolation level. Provider QoS classes complete the ladder:

- **CPU**: burstable families give "a baseline CPU performance with the ability to
  burst above the baseline" via credits; exhausted credits sink you to baseline -
  which mimics a noisy neighbor but is your own quota.
- **Storage**: gp3 decouples provisioned IOPS from capacity (max 16,000 IOPS);
  io2/Block Express provisions "up to 256,000 IOPS" and is "designed to deliver an
  average latency of under 500 microseconds for 16KiB I/O operations." Moving a victim
  volume gp3 -> io2 is often the cheapest interference fix.
- **Network**: bandwidth is tiered - "a running instance earns network I/O credits
  whenever it uses less network bandwidth than its baseline bandwidth" - with hard
  allowances on pps and tracked connections; exceeding them silently drops packets,
  which surfaces as *your* retransmits.

## Shuffle Sharding: Isolation by Allocation

Tenancy is not the only lever; *allocation* is. Shuffle sharding assigns each customer
a small deterministic random subset of the fleet instead of routing everyone to every
worker. The AWS Builders' Library article "Workload isolation using shuffle sharding"
walks the arithmetic: with 8 workers and customers assigned pairs, there are C(8,2) =
28 distinct shards, so one poisoned worker's scope of impact is 1/28 of customers
instead of everyone; with enough workers "there can be more shuffle shards then there
are customers, and each customer can be isolated." The probability that two specified
customers share at least one shard is `1 - C(n-k, k)/C(n, k)` for k-of-n assignment -
small for small k, which is why a loud customer's blast radius stays local. The same
trick applies to your own rate-limit buckets, queue shards, cache partitions, and
replica assignments - far cheaper than dedicated tenancy (see
[rate limiting](../backend/api/rate-limiting.md), and
[Lambda reserved concurrency](./aws/lambda.md) as a managed per-function shard).

## Interview Framing

The question arrives as "p99 tripled and nothing deployed - now what?" Walk the ladder:
**detect** (compare victim tenants against host counters: steal, PSI, LLC misses,
allowance-exceeded), **attribute** (cross-tenant correlation on the same host,
change-point alignment with placement events, rule out your own periodic work),
**enforce** (cgroup weights and latency targets if you own the kernel; placement and
instance-family changes if the provider does; RDT partitions on bare metal), and
**escape** (dedicated tenancy or shuffle sharding when the neighbor is a permanent
workload shape, not a transient). Traps: blaming steal time for an additive periodic
tail (that is your GC); assuming dedicated instances fix all interference (they fix
co-account noise only); reflexive static partitions (they cap tails but strand idle
capacity - proportional weights are the default); and reading the provider's own QoS
mechanics (credit exhaustion, allowance drops) as neighbor noise.

## Cross-References

- [Cloud Internals](./cloud-internals.md) - virtualization/SDN/storage layers plus a
  noisy-neighbor diagnosis interview walkthrough.
- [Cloud Scheduling](./advanced/cloud-scheduling.md) - bin-packing, oversubscription,
  Kubernetes quotas, PriorityClasses, vCluster multi-tenancy.
- [Hypervisors](./virtualization/hypervisors.md) - VM isolation mechanics and
  resource-starvation failure modes.
- [Tail Latency](../distributed/fundamentals/tail-latency.md) - the general tail
  taxonomy; interference is the "shared hardware effects" cause there.

## References

1. Kernel cgroup v2 documentation (cpu, io, memory controllers) - <https://docs.kernel.org/admin-guide/cgroup-v2.html>
2. Kernel resctrl / Intel RDT interface (CAT, MBA) - <https://www.kernel.org/doc/Documentation/x86/resctrl_ui.rst>
3. Pressure Stall Information (PSI) - <https://docs.kernel.org/accounting/psi.html>
4. tc-fq_codel(8) - <https://man7.org/linux/man-pages/man8/tc-fq_codel.8.html>
5. tc-cake(8) - <https://man7.org/linux/man-pages/man8/tc-cake.8.html>
6. Amazon EC2 Dedicated Instances - <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/dedicated-instance.html>
7. Amazon EC2 Dedicated Hosts - <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/dedicated-hosts-overview.html>
8. Burstable performance instances - <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-performance-instances.html>
9. EC2 instance network bandwidth (credits, allowances) - <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-network-bandwidth.html>
10. Amazon EBS volume types (gp3 / io2 Block Express) - <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volume-types.html>
11. GCP sole-tenant nodes - <https://cloud.google.com/compute/docs/nodes/sole-tenant-nodes>
12. "Workload isolation using shuffle sharding," AWS Builders' Library - <https://aws.amazon.com/builders-library/workload-isolation-using-shuffle-sharding/>
13. J. Dean, L. A. Barroso, "The Tail at Scale," CACM 2013 - <https://research.google/pubs/pub40801/>
14. A. Verma et al., "Large-scale cluster management at Google with Borg," EuroSys 2015 - <https://research.google/pubs/pub43438/>
