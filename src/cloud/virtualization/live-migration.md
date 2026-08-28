# Live Migration: Moving Running Machines Across Hosts

Live migration is the operational trick that turned VMs from pets into
cattle: move a *running* VM (or checkpointed container) between hosts with
sub-second unavailability. It works because memory changes much slower
than memory can be copied - usually. The engineering problem is a race:
the guest dirties pages while you copy them, and the migration converges
only if the copy rate beats the dirtying rate. This page builds the
pre-copy/post-copy machinery, the convergence math, and the container
variant.

Foundation pages: [virtualization internals](./virtualization.md) for
the shadow/EPT context that dirty tracking rides on, [CRIU
checkpoint/restore](../advanced/criu-checkpoint-restore.md) for the
container-state serialization this composes with, and
[seccomp/TEE](../../security/advanced/remote-attestation.md) for the
confidential-compute migration flow.

## Pre-copy: iterative transfer with a shrinking dirt set

```text
  phase 0: freeze-1-shadow, copy full memory (the "warm" rounds)
           dirty tracking (EPT-violation -> bitmap) continues
  phase 1..n: copy only pages dirtied during the previous round
           round n transfers D_n pages; guest dirties D_n * r during it
           => D_{n+1} = D_n * r (r = dirty-rate / copy-rate ratio)
  stop when D_n < threshold or after N rounds
  stop-and-copy: brief pause, copy final delta, transfer CPU/device state
  downtime ~= final-delta transfer + device handshake
```

The convergence condition is the whole story: **dirty rate < copy rate**
(else rounds never shrink). The demo below simulates it with the classic
formula from the Clark et al. NSDI 2005 paper, including the pathological
case (a guest that touches memory faster than the network can drain it)
and the operational answer: throttle the guest, or switch strategy.

## Post-copy: transfer CPU first, page on demand

Pre-copy wastes bandwidth on pages that keep changing and prolongs the
*pre-migration* window; post-copy inverts it: migrate CPU state
immediately (short stop), resume the guest on the destination with all
memory absent, and serve page faults from the source over the network.
First-touch latency spikes; total migration time drops; and if the
network dies, the VM is stranded with no source of truth - the failure
mode that keeps conservative operators on pre-copy. Hybrid schemes
(pre-copy a subset, post-copy the hot set) trade between them.

| dimension        | pre-copy                  | post-copy                   |
|------------------|---------------------------|------------------------------|
| total time       | long (iterative rounds)   | short (one pass + faults)    |
| downtime         | small, at the end         | small, at the start          |
| worst-case latency | bounded                 | first-touch fault storm      |
| network failure  | safe (source still whole) | stranded VM                  |
| dirty-heavy guests | may never converge      | unaffected by dirty rate     |

## Storage and state

Memory is the hard part; the rest is bookkeeping with sharp edges:

- **Block devices**: shared storage (SAN/Ceph RBD) needs no disk
  migration; local disks need block-level pre-copy or storage live
  migration, where the same dirty-tracking race reappears on the disk.
- **Device state**: virtio queues migrate cleanly (they are memory);
  passed-through PCI devices need SR-IOV failover or interrupt
  re-injection, and NVMe live migration remains the classic exception.
- **Confidential VMs**: SEV-SNP/CCA migration requires the guest's keys
  to travel via a migration agent with attested handshakes - the
  measurement story in [remote attestation](../../security/advanced/remote-attestation.md)
  extends to the destination host.

## The demo: pre-copy convergence and downtime

```python
#!/usr/bin/env python3
"""Pre-copy live migration simulator (Clark et al. NSDI'05 model).

M pages; round n transfers D_n pages at network rate; the guest dirties
pages at rate r (pages/second). D_{n+1} = min(M, D_n + dirty-during-round)
truncated to the WORP (working set) dynamics: pages dirty repeatedly
stay in the dirt set.

Worst case: r >= copy rate -> rounds never converge -> migration must
throttle the guest (cgroup/BitmapRate limiting) or switch to post-copy.

Deterministic; all quantities in pages and seconds."""


M = 4_194_304                  # 16 GiB in 4 KiB pages
COPY_RATE = 250_000            # pages/s (1 GB/s)
DIRTY_RATE = 60_000            # pages/s steady guest
DIRTY_RATE_HOT = 320_000       # pages/s hot loop (never converges!)
HOT_PAGE_SET = 300_000         # pages the hot loop touches (rotates)

def precopy(dirty_rate, max_rounds=30, stop_threshold=0.002):
    D = M
    rounds = []
    for n in range(1, max_rounds + 1):
        t = D / COPY_RATE                       # seconds this round takes
        newly_dirtied = min(dirty_rate * t, M)
        D = min(M, newly_dirtied)               # next round's dirt set
        rounds.append((n, D, t))
        if D <= M * stop_threshold:
            break
        if n == max_rounds:
            return rounds, False
    return rounds, True

print("=== A. converging guest (dirty 60k pages/s, copy 250k/s) ===")
rounds, ok = precopy(DIRTY_RATE)
for n, D, t in rounds[:6]:
    print(f"  round {n:>2}: transfer {D:>9,.0f} pages in {t:6.2f}s")
print(f"  ... converges after {len(rounds)} rounds ({ok})")
total_warm = sum(t for _n, _D, t in rounds)
final_pages, _ft = rounds[-1][1], rounds[-1][2]
downtime = final_pages / COPY_RATE + 0.05   # final delta + device handshake
print(f"  warm-up time {total_warm:6.1f}s, downtime ~{downtime*1000:.0f} ms")

print()
print("=== B. hot-loop guest (dirty 320k/s > copy 250k/s) ===")
rounds2, ok2 = precopy(DIRTY_RATE_HOT, max_rounds=12)
for n, D, t in rounds2[:5]:
    print(f"  round {n:>2}: transfer {D:>9,.0f} pages in {t:6.2f}s")
print(f"  converges? {ok2} -> dirty rate exceeds copy rate; rounds never shrink.")
print("  operational answers: throttle the guest, bump network (25/100GbE),")
print("  or post-copy (migrate CPU, demand-fault pages).")

print()
print("=== C. downtime math at 100GbE ===")
CR_100G = 3_100_000          # pages/s at 100GbE effective
for dr, name in ((DIRTY_RATE, "steady"), (DIRTY_RATE_HOT, "hot-loop")):
    D = M
    for _ in range(30):
        t = D / CR_100G
        D = min(M, dr * t)
        if D <= M * 0.002:
            break
    dt = D / CR_100G + 0.02
    print(f"  {name:>9}: downtime ~{dt*1000:5.1f} ms "
          f"(final delta {D:,.0f} pages)")
```

```text
=== A. converging guest (dirty 60k pages/s, copy 250k/s) ===
  round  1: transfer 1,006,633 pages in  16.78s
  round  2: transfer   241,592 pages in   4.03s
  round  3: transfer    57,982 pages in   0.97s
  round  4: transfer    13,916 pages in   0.23s
  round  5: transfer     3,340 pages in   0.06s
  ... converges after 5 rounds (True)
  warm-up time   22.1s, downtime ~63 ms

=== B. hot-loop guest (dirty 320k/s > copy 250k/s) ===
  round  1: transfer 4,194,304 pages in  16.78s
  round  2: transfer 4,194,304 pages in  16.78s
  round  3: transfer 4,194,304 pages in  16.78s
  round  4: transfer 4,194,304 pages in  16.78s
  round  5: transfer 4,194,304 pages in  16.78s
  converges? False -> dirty rate exceeds copy rate; rounds never shrink.
  operational answers: throttle the guest, bump network (25/100GbE),
  or post-copy (migrate CPU, demand-fault pages).

=== C. downtime math at 100GbE ===
     steady: downtime ~ 20.5 ms (final delta 1,571 pages)
   hot-loop: downtime ~ 21.5 ms (final delta 4,613 pages)
```

## Containers: CRIU-based migration

Container migration composes [CRIU](../advanced/criu-checkpoint-restore.md)
with the same strategies: checkpoint the process tree (memory, fds,
namespaces), transfer the image, restore on the destination. The
complications are container-specific - external connections need TCP
repair (CRIU's TCP_REPAIR mode snapshots socket state mid-stream), and
anything bound to host state (device handles, NVMe queues, GPU contexts)
does not migrate at all. Kubernetes-native approaches (Virtual Kubelet
style re-scheduling, or stateful failover with persistent volumes)
usually dodge live migration entirely: for stateless services, a fast
*reschedule* with persistent state in a shared store achieves the same
availability at a fraction of the complexity.

## Interview probes

- Derive the pre-copy convergence condition from the round recursion,
  and name the three knobs that change it.
- Why does post-copy have a *first-touch storm* and what mitigations
  exist (page prefetching, host-local caching)?
- A stateful database VM with a dirty rate of 2 GB/s on a 10 GbE
  network: walk your migration plan (throttle? post-copy? quiesce via
  storage snapshot?).
- Why is TCP_REPAIR required for CRIU container migration, and what
  breaks without it?

## References

1. Clark, Fraser, Hand, Hansen, Jul, Limpach, Pratt, Warfield, "Live
   Migration of Virtual Machines", NSDI 2005,
   [the paper](https://www.usenix.org/legacy/events/nsdi05/tech/full_papers/clark/clark.pdf)
   - the pre-copy design and the dirty-rate/copy-rate race this page
   models.
2. [KVM documentation](https://docs.kernel.org/virt/kvm/index.html) -
   the kernel dirty-tracking interfaces (dirty bitmap, ring) migrations
   consume.
3. [QEMU migration documentation](https://www.qemu.org/docs/master/devel/migration/main.html)
   - the shipped implementation: throttling, post-copy, TLS, and
   multifd parallel streams.
4. [CRIU checkpoint/restore (this repo)](../advanced/criu-checkpoint-restore.md)
   - the container-side serialization machinery.
