# SPDK: User-Space Storage I/O

The Storage Performance Development Kit (SPDK) is a set of tools and libraries for writing "high performance, scalable, user-mode storage applications." Its own README states the mechanism in one sentence: it moves "all of the necessary drivers into userspace and operate[s] in a polled mode instead of relying on interrupts, which avoids kernel context switches and eliminates interrupt handling overhead." SPDK is DPDK's design applied to block storage - the same EAL ancestry, the same VFIO/hugepage substrate, the same poll-mode doctrine - but with a whole storage stack built on top: a user-space NVMe driver, a block-device abstraction layer, a blob store and file system, and user-space NVMe-oF, iSCSI, and vhost targets. This page is the storage-side companion to [DPDK internals](./dpdk.md); the kernel-bypass family (DPDK, SPDK, io_uring) is surveyed in [Fast I/O](./fast-io.md), and the kernel machinery being bypassed is detailed in [I/O internals](./io-internals.md).

## What the kernel NVMe path charges

The Linux NVMe driver itself is excellent: submission/completion queues are plain DRAM rings, the command set is register-light, and blk-mq scales with hardware queues. The tax SPDK removes is everything wrapped *around* the hardware rings. One 4 KiB O_DIRECT read still crosses this machinery:

```text
Kernel NVMe path (one 4 KiB read, O_DIRECT)
  read(2) syscall: entry, arg validation, file lookup, exit
  blk-mq: request allocation, tag, scheduler (mq-deadline/kyber/bfq)
  nvme driver: build command in SQ, MMIO doorbell store
  controller DMA-writes data into a kernel buffer
  controller raises MSI-X interrupt -> hardirq
  softirq: blk_mq completion -> bio endio -> copyout to user buffer
  scheduler wakes the submitting thread (context switch, cache refill)

SPDK path (same read, from a user-space process)
  spdk_nvme_ns_cmd_read(): build command in a user-space SQ (plain DRAM)
  MMIO doorbell store to the SQ tail register - from user space
  controller DMA-writes data into the app's hugepage buffer (VFIO/IOMMU)
  poll loop: spdk_nvme_qpair_process_completions() reads the CQ in DRAM
  submit and completion are function calls; zero syscalls, zero IRQs,
  zero context switches, zero copies
```

Each kernel transition costs roughly 0.5-2 us and, worse, evicts the working set of the submitting core. At the 1-3M IOPS a single PCIe Gen4 SSD serves, even a 1.5 us per-I/O kernel tax exceeds one full core before the application has done any work - and interrupt-driven completion adds latency jitter: the wakeup path takes a variable route through hardirq, softirq, and scheduler queues. The [kernel NVMe driver's internals](../../linux/kernel/drivers/nvme.md) are worth knowing precisely because SPDK keeps the protocol and replaces the plumbing.

## The user-space NVMe driver: DPDK's PMD pattern, applied to storage

NVMe is unusually friendly to user-space drivers because the spec already puts the data path in memory: an application that can read/write host memory and issue two MMIO stores can drive a controller. With the device bound to `vfio-pci` (or UIO on legacy hosts), the controller's BAR maps into the process address space, and the SPDK NVMe driver - a library, not a kernel module - owns admin and I/O queue pairs directly:

```text
SPDK process                          NVMe controller
+---------------------------+         +------------------+
| hugepage buffers (DMA)    |<--DMA-->| DMA engine       |
| io qpair: SQ ring (DRAM)  |         |                  |
|           CQ ring (DRAM)  |<--IRQ---| (unused: pollers |
| doorbell: MMIO store ->SQ |---MMIO->|  read the doorb) |
+---------------------------+         +------------------+
        ^ VFIO maps BAR + pins memory with the IOMMU
```

Completion is poll-mode by default: `spdk_nvme_qpair_process_completions(qpair, max)` walks the CQ for phase-bit flips, exactly like a DPDK PMD's RX burst. No interrupt handler runs; there is nothing to wake because the thread that submitted the I/O is still spinning on the core that owns the qpair. SPDK reuses DPDK's EAL for what it is good at - core pinning, hugepage-backed DMA memory, PCI enumeration - so the storage app inherits the networking kit's memory and affinity model rather than reinventing it; see [DPDK: EAL and the lcore model](./dpdk.md). Multi-queue SSDs map naturally: one qpair per core, submitted and completed on the same core, no locks anywhere on the path.

## Application framework: reactors, threads, pollers, messages

SPDK ships an event framework because a driver is not an application. The documented concurrency model is message passing, chosen explicitly to avoid locks and even atomic instructions in the hot path (the docs target *linear* scaling with cores, NICs, and SSDs):

- **Reactor** - one pinned core (by default one per application core mask entry). A reactor runs a loop that executes its threads' pollers and delivers messages; this loop *is* the scheduler, and it only yields on request (the framework also supports an interrupt-driven hybrid mode for sparse workloads).
- **spdk_thread** - a lightweight, stackless execution context that a reactor runs for a timeslice via `spdk_thread_poll()`. Pollers (`spdk_poller`) are functions repeatedly called on their thread: the NVMe qpair poller, the RDMA completion poller, timeouts, background reclaim.
- **Messages** - `spdk_thread_send_msg()` moves a function pointer plus context to the thread that *owns* a data structure, over lockless rings. The rule of thumb from the docs: assign data to a single thread instead of locking it; for read-mostly I/O-path state, copy it per-thread and broadcast updates, because cache locality beats sharing.

```text
core 0 (pinned reactor)             core 1 (pinned reactor)
+----------------------------+      +----------------------------+
| spdk_thread: app + RPC     |      | spdk_thread: nvmf target   |
|  poller: bdev nvme qpairs  |      |  poller: RDMA/TCP CQ       |
|  poller: blobfs journal    |      |  poller: bdev nvme qpair   |
+-------------+--------------+      +-------------+--------------+
              |  spdk_thread_send_msg(): fn ptr + ctx
              +-------- over lockless ring -------> (data stays owned by
                                                     one thread; no locks,
                                                     no atomics on hot path)
```

The result reads like Go/Erlang discipline rendered in C: thread-per-core shared nothing, queues instead of mutexes, and a main loop with no syscalls on the I/O path.

## The bdev layer, vbdevs, the blob store, and blobfs

Above the driver sits **bdev**, a C library documented as "equivalent to the operating system block storage layer" - the pluggable abstraction that lets one application talk to many backends:

| bdev module | What it fronts |
|---|---|
| `nvme` | the user-space NVMe driver (local PCIe) |
| `malloc` | ramdisk backed by hugepages - the test backend |
| `aio`, `uring` | pass-through to kernel block devices |
| `rbd` | Ceph RADOS block devices via librbd |
| `virtio-scsi`, `vhost-scsi` | guest/VM disk front-ends |
| `raid` | RAID0, concat, RAID5F composed from child bdevs |

Virtual bdevs (**vbdev**) stack *on top of* other bdevs the way device-mapper targets stack in-kernel: logical volumes, GPT partitioning, crypto (wired to SPDK's accel framework, which uses DPDK's cryptodev API and QAT hardware), compression, and raid modules. Configuration is JSON-RPC against a running target - there is no ioctl interface, because there is no kernel.

Below the filesystem-shaped world sits the **blobstore**: a crash-consistent, persistent allocator over a bdev that hands out blobs (variable-size, metadata-tracked objects) with O_DIRECT-style semantics and metadata you control. **blobfs** layers a minimal, single-application file system on the blobstore - no VFS, no page cache, no POSIX locking - so a user-space database gets namespaced files and a journal without kernel mediation; SPDK ships a RocksDB environment shim so RocksDB runs directly on blobfs. This is the user-space echo of the layering in [I/O internals](./io-internals.md): page cache, VFS, and block layer are replaced by blob metadata, allocator, and bdev - all library calls on pinned cores.

## The NVMe-oF target: a fabric front end with no kernel

SPDK's NVMe-oF target turns the framework inside out: instead of *consuming* an SSD, the application *serves* bdevs as NVMe namespaces over the fabric. The target runs entirely in user space; RDMA (RoCE/iWARP/InfiniBand) and TCP transports terminate in pollers on pinned cores, and each fabric connection's queues map to local qpairs on the owning core. Because a remote NVMe-oF read costs a network round trip of a few microseconds, a kernel target would spend as much in transitions as the fabric spends on the wire - which is the whole argument for a user-space target. The protocol itself (fabrics commands, namespaces, controllers) is the same one the kernel target implements; see [NVMe over Fabrics](../../linux/storage/nvme-of.md) for the wire protocol and discovery service.

## vhost-scsi and vhost-blk: VM disks without QEMU emulation

SPDK's vhost target implements the vhost-user protocol: QEMU maps the guest's virtqueue rings into the SPDK process via shared memory, and SPDK polls them directly. The guest sees standard virtio-scsi or virtio-blk devices; QEMU handles device setup but its emulated disk backend is bypassed - every guest I/O is a shared-memory ring walk plus a bdev submission on a pinned SPDK core, no QEMU process wakeups, no system calls, no SCSI emulation in the middle. For virtualized storage appliances this closes most of the gap between guest and host IOPS, and it composes with everything above the vhost layer (bdevs, vbdevs, NVMe-oF).

## Trade-offs: what polling and user-space drivers cost you

The bypass is not free, and the costs are architectural, not tuning constants:

- **Cores are the fuel.** Every polling qpair burns a core whether or not I/O arrives. That core cannot run anything else unless you explicitly add interrupt mode or timed pollers. Provisioning becomes arithmetic: capacity = cores x per-core IOPS.
- **Isolation is mandatory.** Pollers need `isolcpus`/`nohz_full`/cpusets and IRQ affinity to keep housekeeping kernels off their cores - which fragments the machine for every other workload in the same kernel.
- **The driver ships with your app.** A user-space NVMe driver is thousands of lines of register-level code maintained outside the kernel community. Bugs corrupt memory with only the IOMMU (VFIO) as a containment fence; you own updates for new controller features, error recovery, and hotplug.
- **The kernel's storage services vanish.** No page cache (bdev is raw), no dm, no cgroup I/O control, no cohabitation with random processes. You rebuild what you need as vbdevs - or accept the loss.
- **The ecosystem counterattack.** io_uring with SQPOLL and registered files/buffers removed most of the syscall tax SPDK was born to dodge, and NVMe polling queues exist in-kernel (`HIPRI`). The kernel does not need to win on raw IOPS-per-core; it needs to be close enough that retaining page cache, cgroups, and 30 years of tooling wins the decision.

| Dimension | Kernel NVMe + io_uring | SPDK poll mode |
|---|---|---|
| Syscalls in I/O path | batched to near-zero (SQPOLL: one thread) | none |
| Completion | IRQ -> softirq (or busy poll queues) | poller on owning core |
| Latency jitter | scheduler/IRQ noise, us-scale | minimal; you own every cycle |
| Idle CPU cost | none | one full core per polling thread group |
| Page cache, dm, cgroup I/O | full ecosystem | none - rebuild as vbdevs or go without |
| Driver maintenance | in-kernel, distro-shipped | ships inside the application |
| Isolation prerequisites | none | pinned/isolated cores, hugepages, VFIO |
| Sweet spot | multi-tenant, mixed I/O, containers | dedicated appliances at millions of IOPS/core |

The honest selection rule: if the workload is sparse, shared, or feature-hungry, [io_uring](../kernel/io-uring.md) on the kernel NVMe driver is the right answer, and SPDK itself grew an interrupt-driven mode for exactly those cases. When a handful of processes must extract every IOPS-per-core and every microsecond from hardware they own outright - storage arrays, NVMe-oF gateways, vhost backends, hyperconverged data planes - the poll-mode arithmetic below shows where the crossover sits.

## Worked demo: the interrupt/poll crossover (T = a + b/n)

Batching is the interrupt path's only defense: per-I/O CPU cost `T = a + b/n`, where `a` is per-I/O driver work, `b` is the fixed per-IRQ bill (handler + softirq + context switch + wakeup), and `n` is the number of I/Os coalesced per interrupt (n grows with load until the device's coalescing cap). Polling deletes `b` but rents a core: `S/IOPS` microseconds of CPU per I/O. The crossover is where the rented core stops costing more than the interrupts it removes.

```python
"""Interrupt-driven vs poll-mode I/O cost model.

Per-I/O CPU cost in interrupt mode, T = a + b/n: every completion costs
a (driver work) plus the per-IRQ overhead b amortized over the n I/Os
that arrive during one interrupt-coalescing window. Poll mode removes
the IRQ entirely (per-I/O cost a' < a + b/n) but pays for a dedicated
spin core: S/IOPS microseconds of CPU per I/O.
"""

A_IRQ = 1.8       # us CPU per I/O: CQ walk, buffer copy (interrupt mode)
B_IRQ = 4.2       # us CPU per IRQ: handler + softirq + ctx switch + wakeup
A_POLL = 0.9      # us CPU per I/O: poll-loop work, no IRQ, no syscall
T_COAL = 10.0     # us interrupt-coalescing window
N_MAX = 32        # max I/Os coalesced into one IRQ
S_CORE = 1e6      # us of CPU per second burned by one dedicated spin core

def irq_cost(iops):
    n = max(1, min(N_MAX, int(iops * T_COAL / 1e6)))  # arrivals per window
    return A_IRQ + B_IRQ / n, n

def poll_cost(iops):
    return A_POLL + S_CORE / iops

# crossover: smallest IOPS where polling needs no more CPU than interrupts
lo, hi = 1_000, 5_000_000
while hi - lo > 1:
    mid = (lo + hi) // 2
    if poll_cost(mid) <= irq_cost(mid)[0]:
        hi = mid
    else:
        lo = mid
xover = hi

rows = [10_000, 50_000, 100_000, 250_000, 500_000, xover, 1_000_000, 1_500_000]
print(f"crossover: polling wins above {xover:>9,d} IOPS per core")
print()
print("      IOPS   batch  IRQ us/io  IRQ cores  poll us/io  poll cores  winner")
print("  --------  -----  ---------  ---------  ----------  ----------  ------")
for iops in rows:
    ci, n = irq_cost(iops)
    cp = poll_cost(iops)
    irq_cores = iops * ci / 1e6
    poll_cores = 1 + iops * A_POLL / 1e6
    win = "poll" if cp < ci else "irq"
    print(f"  {iops:>8,d}  {n:>5d}  {ci:>9.3f}  {irq_cores:>9.3f}  "
          f"{cp:>10.3f}  {poll_cores:>10.3f}  {win:>6}")

print()
c = irq_cost(xover)[0]
print(f"at crossover: IRQ {c:.3f} us/io -> {xover * c / 1e6:.2f} cores; "
      f"poll {poll_cost(xover):.3f} us/io -> {1 + xover * A_POLL / 1e6:.2f} cores")
big = 1_500_000
cb = irq_cost(big)[0]
print(f"at {big:,d} IOPS/core: IRQ needs {big * cb / 1e6:.2f} cores, "
      f"poll needs {1 + big * A_POLL / 1e6:.2f} cores "
      f"-> {100 * (1 - (1 + big * A_POLL / 1e6) / (big * cb / 1e6)):.0f}% CPU saved")
small = 10_000
print(f"at {small:,d} IOPS/core: IRQ needs {small * irq_cost(small)[0] / 1e6:.3f} cores, "
      f"poll idles 1 core for {poll_cost(small) - A_POLL:.1f} us/io of pure spin "
      f"-> {100 * (1 - small * irq_cost(small)[0] / 1e6 / 1):.1f}% of the poll core is waste")
print("verdict: kernel NVMe (+ io_uring) below the crossover; SPDK-style polling above it")
```

Real output:

```text
crossover: polling wins above   574,713 IOPS per core

      IOPS   batch  IRQ us/io  IRQ cores  poll us/io  poll cores  winner
  --------  -----  ---------  ---------  ----------  ----------  ------
    10,000      1      6.000      0.060     100.900       1.009     irq
    50,000      1      6.000      0.300      20.900       1.045     irq
   100,000      1      6.000      0.600      10.900       1.090     irq
   250,000      2      3.900      0.975       4.900       1.225     irq
   500,000      5      2.640      1.320       2.900       1.450     irq
   574,713      5      2.640      1.517       2.640       1.517    poll
  1,000,000     10      2.220      2.220       1.900       1.900    poll
  1,500,000     15      2.080      3.120       1.567       2.350    poll

at crossover: IRQ 2.640 us/io -> 1.52 cores; poll 2.640 us/io -> 1.52 cores
at 1,500,000 IOPS/core: IRQ needs 3.12 cores, poll needs 2.35 cores -> 25% CPU saved
at 10,000 IOPS/core: IRQ needs 0.060 cores, poll idles 1 core for 100.0 us/io of pure spin -> 94.0% of the poll core is waste
verdict: kernel NVMe (+ io_uring) below the crossover; SPDK-style polling above it
```

Read the table as the whole SPDK decision in one view: at 50K IOPS per core, interrupt mode uses 0.3 cores while polling burns a full one - 96% of the poll core is pure spin. Above roughly 575K IOPS per core (with the model's 10 us coalescing window), the rented poll core is cheaper than the interrupt bill, and the gap widens with load because `b/n` can only amortize down to `b/32` while `S/IOPS` keeps falling. Add the latency column that the CPU numbers hide - interrupts inject variable wakeup jitter into every I/O, pollers do not - and the case for poll mode above the crossover is total. The constants are illustrative (measure `a`, `b`, and `S` on your hardware), but the shape is not: the crossover is why kernel storage serves desktops and containers while arrays and gateways poll.

## References

1. SPDK documentation portal (Doxygen + user guides): <https://spdk.io/doc/> (HTTP 200).
2. SPDK architecture overview and user-space rationale: <https://spdk.io/doc/overview.html>, <https://spdk.io/doc/userspace.html> (HTTP 200).
3. SPDK application framework - reactors, threads, pollers, message passing: <https://spdk.io/doc/app_overview.html>, <https://spdk.io/doc/concurrency.html> (HTTP 200).
4. SPDK user-space NVMe driver and NVMe spec summary: <https://spdk.io/doc/nvme.html>, <https://spdk.io/doc/nvme_spec.html> (HTTP 200).
5. SPDK bdev layer and module API: <https://spdk.io/doc/bdev.html>, <https://spdk.io/doc/bdev_module.html> (HTTP 200).
6. SPDK blobstore/blobfs guide: <https://spdk.io/doc/blob.html> (HTTP 200).
7. SPDK NVMe-oF and vhost targets: <https://spdk.io/doc/nvmf.html>, <https://spdk.io/doc/vhost.html> (HTTP 200).
8. SPDK interrupt-driven operation (hybrid mode): <https://spdk.io/doc/interrupt_mode.html> (HTTP 200).
9. SPDK GitHub repository and README (project scope, component list): <https://github.com/spdk/spdk> (HTTP 200).
10. SPDK project introduction announcement: <https://spdk.io/news/2016/03/02/spdk_intro/> (HTTP 200).
11. DPDK Environment Abstraction Layer (shared EAL substrate): <https://doc.dpdk.org/guides/prog_guide/env_abstraction_layer.html> (HTTP 200).
