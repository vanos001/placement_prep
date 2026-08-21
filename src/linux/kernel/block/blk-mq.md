# blk-mq

`blk-mq` (block multi-queue) is the Linux block layer I/O path introduced in kernel 3.13 (2014) and made default in 3.16. It replaced the legacy single-queue block layer (`blk`) with a per-CPU submission queue and per-hardware-queue dispatch design, allowing NVMe devices with thousands of hardware queues to be driven at line rate without lock contention. This page covers the queue hierarchy, the request life cycle, the scheduler interface, and the practical trade-offs of the available I/O schedulers.

## Why blk-mq Exists

The legacy block layer (introduced in 2.x) used a single `request_queue` per device with a single `queue_lock` to protect it. On a 16-core host driving an HDD or SATA SSD, the lock was fine. On a 64-core host with an NVMe device capable of 2M IOPS, the single queue became the bottleneck: every `submit_bio` had to take the lock, and contention dominated the cycle budget.

NVMe changed the model: the device exposes one or more **submission queue / completion queue pairs**, and the host can dispatch to each independently. The natural mapping is one submission queue per CPU, with no shared lock. blk-mq makes this explicit.

## Queue Hierarchy

blk-mq has two levels of queues:

```text
         Per-CPU Software Queues (software staging area)
         ───────────────────────────────────────────────
                  ┌──────┬──────┬──────┬──────┐
                  │ CPU0 │ CPU1 │ CPU2 │ CPU3 │  ... (one per CPU)
                  └──┬───┴──┬───┴──┬───┴──┬───┘
                     │      │      │      │
                     ▼      ▼      ▼      ▼
         I/O Scheduler (mq-deadline/bfq/none/kyber)
         ───────────────────────────────────────────
                  dispatches by deadline / class / etc.
                     │      │      │      │
                     ▼      ▼      ▼      ▼
         Hardware Dispatch Queues (hctx) — one per IRQ/CPU group
         ───────────────────────────────────────────
                  ┌──────┬──────┬──────┬──────┐
                  │ hctx0│ hctx1│ hctx2│ hctx3│  ...
                  └──┬───┴──┬───┴──┬───┴──┬───┘
                     │      │      │      │
                     ▼      ▼      ▼      ▼
         NVMe Submission Queues (NVMe SQ/CQ pairs)
         ───────────────────────────────────────────
                  ┌──────┬──────┬──────┬──────┐
                  │ SQ0  │ SQ1  │ SQ2  │ SQ3  │  ...
                  └──────┴──────┴──────┴──────┘
                          │
                          ▼
                       NVMe Device
```

`blk_mq_alloc_tag_set` allocates the tag set, which represents the device's hardware queue configuration. The driver specifies `set->nr_hw_queues`, `set->queue_depth`, and `set->cmd_size` (driver-private data per request). The framework allocates `nr_hw_queues` software staging queues (one per CPU as a default; can be more for IRQ-affinitized configurations).

The mapping from CPU → hardware queue is determined by `blk_mq_map_queues`, which respects the device's IRQ affinity (e.g., on a 4-socket NUMA machine, a NIC with 8 MSI-X vectors gets 2 vectors per socket; CPUs on each socket map to that socket's vectors to avoid cross-socket IRQ traffic).

## Request Life Cycle

A `request` in blk-mq is allocated from a per-hardware-queue tag set:

1. **Allocation**: `bio` is submitted via `submit_bio()`. `blk_mq_submit_bio` calls `blk_mq_alloc_request`, which acquires a tag from the per-hctx tag set. Tags are bit positions in a bitmap; allocation is O(1) via `sbitmap_get`.

2. **Initialization**: The driver's `init_request` callback (if present) initializes the driver-private area of the request. For NVMe, this is the NVMe Submission Queue Entry (SQE).

3. **Queuing**: The request is queued either to the active I/O scheduler (if one is attached) or directly to the hctx dispatch list. `blk_mq_sched_insert_request` is the entry point.

4. **Dispatch**: `blk_mq_run_hw_queue` is called either explicitly by `submit_bio` or from a worker thread. It pulls requests from the scheduler and calls the driver's `queue_rq` callback for each one. `queue_rq` writes the SQE to the device's submission queue and rings the doorbell.

5. **Completion**: When the device completes an I/O, it posts a CQE (completion queue entry). The IRQ handler (`nvme_irq`, etc.) calls `blk_mq_complete_request`, which calls the per-request `end_io` callback. The request and its tag are returned to the pool.

```c
/* Simplified bio → request → tag → SQE flow */
static blk_status_t nvme_queue_rq(struct blk_mq_hw_ctx *hctx,
                                  const struct blk_mq_queue_data *bd) {
    struct nvme_queue *nvmeq = hctx->driver_data;
    struct request *req = bd->rq;
    struct nvme_command *cmd = blk_mq_rq_to_pdu(req);

    /* Fill the NVMe SQE from the request's bio chain */
    nvme_setup_cmd(nvmeq, req, cmd);

    if (bd->last && nvmeq->sq_tail == nvmeq->last_cq_tail)
        nvme_write_sq_doorbell(nvmeq, 0);  /* coalesce */
    else
        nvme_write_sq_doorbell(nvmeq, 1);

    return BLK_STS_OK;
}
```

## I/O Schedulers

blk-mq schedulers are pluggable. The default depends on the device class:

| Scheduler | Algorithm | When to use |
|-----------|-----------|-------------|
| `none`       | FIFO, no reordering | Maximum throughput on fast devices (NVMe) when fairness doesn't matter |
| `mq-deadline`| Read priority + per-write deadline | Mixed read/write workloads, especially databases |
| `bfq`        | Budget fair queuing | Desktop, single-user workloads where interactive responsiveness matters |
| `kyber`      | Token-based latency-critical | Workloads requiring bounded latency, with smaller throughput |

`none` is the default on most NVMe installations. `mq-deadline` is the default for SATA/SAS. `bfq` is the default on workstation Ubuntu installations.

Switch schedulers at runtime:

```bash
# View current scheduler
cat /sys/block/nvme0n1/queue/scheduler

# Switch
echo mq-deadline > /sys/block/nvme0n1/queue/scheduler

# Affects all I/O submitted after the switch — not in-flight I/O
```

The trade-offs:
- `none` has no per-request reordering cost. Maximum throughput, but a sustained writer can starve readers.
- `mq-deadline` adds bounded latency by tracking per-request deadlines (default 500 ms read, 5 s write) and reordering to meet them. The reordering cost is ~10% throughput loss in the worst case.
- `bfq` is latency-bound: it gives every process a "budget" of disk time, ensuring no process starves another. The cost is throughput — `bfq` loses 20-50% of theoretical max on highly contended NVMe.
- `kyber` is newer (4.12+), designed for the lowest-tail-latency workloads. It limits the number of in-flight synchronous requests per direction, achieving latency bounded by `max_read_latency_ns` and `max_write_latency_ns`.

## Per-CPU Software Queues and Batch Submission

The per-CPU software queues exist for batching: when many `submit_bio` calls happen on the same CPU in the same jiffy (10 ms by default), blk-mq defers dispatching to the hardware queue until either the software queue fills or a softirq timeout fires. This batching amortizes the per-dispatch cost over multiple I/Os.

For high-IOPS workloads (e.g., RocksDB compaction), the batching is critical: a single `fsync()` triggers many `submit_bio` calls in the same jiffy, and batching reduces them from N driver dispatches to one. The default `BLK_DEV_DEF_HW_QUEUE_DEPTH` is 256, but production systems often raise it to 1024:

```bash
echo 1024 > /sys/block/nvme0n1/queue/nr_requests
```

## Multi-Queue Block IO Accounting

`/proc/diskstats` and `/sys/block/<dev>/stat` report aggregate I/O counts. blk-mq exposes per-hctx statistics:

```bash
/sys/kernel/debug/block/nvme0n1/hctx0/stats/
├── io_ticks           # time spent doing I/O
├── inflight           # requests in flight
├── io_cycles          # cycles spent in queue_rq
├── dispatched         # per-class counters
├── runqueue_to        # how often run_hw_queue fired from timeout
├── runqueue_shared    # how often run_hw_queue fired from another hctx
└── ...
```

These debugfs entries are the source for `iostat -x` and per-queue performance analysis tools.

## Poll Queues and Hybrid Polling

NVMe polling mode bypasses interrupts: the kernel busy-polls the completion queue instead of waiting for an IRQ. This trades CPU for latency.

Two variants:

1. **`poll_queue`**: dedicated hardware queues for polled I/O. Application calls `io_uring_enter(IORING_ENTER_GETEVENTS)` or `aio_pgetevents()` which busy-polls. Throughput is unaffected; latency drops by IRQ latency (~10 µs).
2. **Hybrid polling**: the kernel sleeps for half the expected completion time, then busy-polls for the other half. Reduces CPU waste while bounding latency.

Enable with `nvme.poll_queues=N` kernel command-line option, or:

```bash
echo 1 > /sys/block/nvme0n1/device/poll_queues
```

## Common Pitfalls

1. **`nr_requests` too low for the workload.** The default 256 is too low for NVMe databases — they queue 4 KB × thousands of in-flight I/Os and stall when the queue fills. Raise to 1024–2048.
2. **`queue_depth` exceeding device capability.** Setting `queue_depth` above the device's actual hardware queue depth just wastes memory. NVMe supports 1024+ entries per SQ; SATA supports 32; SCSI supports 256. Verify with `nvme id-ctrl /dev/nvme0` (`sqes` field).
3. **CPU misalignment with IRQ affinity.** If CPU 0 submits I/O but the IRQ fires on CPU 64, the request completion crosses NUMA boundaries and adds ~2 µs latency. Use `irq_set_affinity_hint` from the driver, or set `/proc/irq/<n>/smp_affinity` so submission and completion happen on the same NUMA node.
4. **Forgetting `blkcg` interactions.** blk-mq honors the `io.max` cgroup controller, but only if `blk-cgroup` is enabled. Cgroup I/O limits are silently ignored otherwise. Check `cat /sys/fs/cgroup/io.stat` for nonzero values.
5. **`none` scheduler + heavy read/write mix.** Without a scheduler, a 100% writer can starve readers indefinitely. Use `mq-deadline` for any workload that has interactive or query-path reads.

## References

- [kernel.org: Block layer documentation](https://docs.kernel.org/block/blk-mq.html)
- [LWN: "Multi-queue block IO queueing mechanism (blk-mq) v5" (2014)](https://lwn.net/Articles/555098/)
- [LWN: "blk-mq: The future of the Linux block layer" (2013)](https://lwn.net/Articles/603931/)
- Jens Axboe, "[blk-mq design](https://www.kernel.org/doc/Documentation/block/blk-mq.txt)"
- Björn Töpel, "[Linux NVMe polling internals](https://lpc.events/event/4/contributions/457/)"
- [Linux source: `block/blk-mq.c`](https://github.com/torvalds/linux/blob/master/block/blk-mq.c)
