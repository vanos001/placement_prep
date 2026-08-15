# Fast I/O — Bypassing the Kernel for Extreme Throughput

Traditional Linux I/O (read/write, even [io_uring](../kernel/io-uring.md) basics) still involves the kernel as intermediary: system calls, buffer copies, interrupt handling, and context switches. For workloads requiring millions of IOPS — high-frequency trading, NVMe-oF storage targets, network function virtualization — even these overheads are prohibitive. This section covers the tools and architectures that bypass or minimize kernel involvement in the I/O path.

## DPDK — Data Plane Development Kit

DPDK (originally Intel, now Linux Foundation) is a set of user-space libraries and drivers for fast packet processing. It bypasses the Linux kernel network stack entirely by:

1. **PMD (Poll Mode Drivers)**: NIC drivers that poll for packets instead of using interrupts. The CPU continuously checks the NIC's receive descriptor rings, eliminating interrupt overhead and the associated context switch. No `softirq`, no `napi`, no sk_buff allocation.

2. **UIO / VFIO hugepage mapping**: The NIC's MMIO registers and DMA ring buffers are mapped directly into user space via VFIO with IOMMU protection (see [virtualization.md](./virtualization.md#vfio--virtual-function-i-o)). The application reads and writes NIC registers directly.

3. **Huge pages**: All memory used for packet buffers comes from huge pages (2 MB or 1 GB), eliminating TLB misses that would be catastrophic at 10+ Mpps.

4. **Lockless ring buffers (rte_ring)**: Multi-core-safe SPSC/MPSC ring buffers for passing packets between cores without locks, using single-producer single-consumer semantics where possible.

```c
// Simplified DPDK packet receive loop
#include <rte_eal.h>
#include <rte_ethdev.h>

struct rte_mbuf *pkts[BURST_SIZE];
uint16_t nb_rx;

// Poll for packets (no interrupt, no syscall)
while (1) {
    nb_rx = rte_eth_rx_burst(port_id, queue_id, pkts, BURST_SIZE);
    if (nb_rx == 0) continue;  // pure polling, no sleep
    
    for (i = 0; i < nb_rx; i++) {
        // Process packet — pkts[i]->pkt.data points to NIC DMA buffer
        // Zero-copy: no skb allocation, no copy
        process_packet(pkts[i]);
    }
    rte_pktmbuf_free_bulk(pkts, nb_rx);
}
```

Performance: DPDK achieves 40-80 Mpps (million packets per second) on a single core with modern NICs (Intel E810, NVIDIA ConnectX-6). Compare to the Linux kernel stack: ~1-2 Mpps with interrupts and ~5-10 Mpps with busy-poll (`SO_BUSY_POLL`). The cost is dedicating CPU cores to polling (wasted cycles when idle) and giving up the kernel's protocol stack (TCP, routing, firewall).

## SPDK — Storage Performance Development Kit

SPDK applies DPDK's philosophy to storage: user-space NVMe drivers, zero-copy I/O, and lockless queuing. The key components:

- **NVMe driver (spdk_nvme)**: User-space NVMe driver that maps the NVMe controller's PCIe BAR (containing submission and completion queues) directly into the process address space. Submissions are written directly to the hardware SQ; completions are polled from the hardware CQ. No kernel block layer, no SCSI layer, no `blk_mq`.

- **Bdev layer**: A block device abstraction that presents virtual block devices (RAID, encryption, compression) built on top of physical NVMe devices, all in user space.

- **nvmf target**: A user-space NVMe-oF (NVMe over Fabrics) target that serves NVMe devices over RDMA or TCP, achieving millions of IOPS.

```c
// SPDK NVMe read — no syscall, direct hardware access
struct spdk_nvme_qpair *qpair = spdk_nvme_ctrlr_alloc_io_qpair(ctrlr, NULL, 0);

struct spdk_nvme_ns *ns = spdk_nvme_ctrlr_get_ns(ctrlr, nsid);
void *buf = spdk_dma_zmalloc(4096, 4096, NULL);

// Submit directly to hardware SQ
int rc = spdk_nvme_ns_cmd_read(ns, qpair, buf, lba, 1,
    /* cb_fn */ NULL, /* cb_arg */ NULL, 0);

// Poll for completion
while (!spdk_nvme_qpair_process_completions(qpair, 0))
    ;  // spin until done
```

SPDK is used in Ceph (BlueStore backend), MinIO, and cloud storage services. A single SPDK instance on an Intel Optane PM1733 NVMe SSD achieves ~3M read IOPS (4K random) on a single core — the kernel `io_uring` path achieves ~1.5M IOPS for comparison, due to syscall entry/exit overhead.

## io_uring Internals — SQ, CQ, and Zero-System-Call Completion

[io_uring basics](../kernel/io-uring.md) covers the API surface. Here we examine the internal ring buffer mechanism and how it achieves "zero syscall per completion."

### Ring Buffer Architecture

io_uring uses two shared ring buffers between kernel and user space, allocated via `mmap()` on the io_uring file descriptor:

```
User Space                              Kernel Space
┌──────────────────┐                  ┌──────────────────┐
│ Submission Ring  │◄───mmap────────►│  Reads SQE entries│
│ (SQ)             │                  │  from ring buffer │
│                  │                  │                  │
│ sq_tail ──►      │  (user writes)   │  sq_head ──►     │
│   [SQE][SQE]...  │                  │                  │
└──────────────────┘                  └──────────────────┘

┌──────────────────┐                  ┌──────────────────┐
│ Completion Ring  │◄───mmap────────►│  Writes CQE      │
│ (CQ)             │                  │  to ring buffer  │
│                  │                  │                  │
│ cq_head ──►      │  (kernel writes) │  cq_tail ──►     │
│   [CQE][CQE]...  │                  │                  │
└──────────────────┘                  └──────────────────┘
```

The SQ (Submission Queue) is an array of indices into a separate SQE (Submission Queue Entry) array. The CQ (Completion Queue) contains CQE (Completion Queue Entry) structures with the result. Both rings use **single-writer single-reader** discipline: only the user writes the SQ tail; only the kernel writes the CQ tail. This eliminates memory barriers between producer and consumer (only release on write, acquire on read).

### The Zero-Submission-Entry Fast Path

With `IORING_SETUP_SQE128` and `IORING_SETUP_CQE32`, SQEs are 128 bytes and CQEs are 32 bytes (extended for NVMe passthrough). The normal submission path:

1. User fills SQE with operation (read, write, openat, etc.)
2. User increments `sq->tail` and issues `io_uring_enter()` syscall
3. Kernel reads SQEs, processes them, writes CQEs

The **zero-syscall completion** optimization: after the initial `io_uring_enter()`, the user polls the CQ in a tight loop (for high-throughput servers). New SQEs can be submitted without `io_uring_enter()` by using `IORING_ENTER_GETEVENTS` with the SQ polling flag. The kernel can also be configured to poll the SQ from a kernel thread (`IORING_SETUP_SQPOLL`), completely eliminating user-initiated syscalls.

### io_uring vs. epoll

| Aspect | epoll | io_uring |
|--------|-------|----------|
| Operations supported | read/write (indirect) + network events | Any syscall (100+ registered ops) |
| Syscall per completion | 1 (`epoll_wait` returns, then `read`/`write`) | 0 (CQ polled from userspace) |
| Async read/write | No (edge-triggered still needs `read`/`write`) | Yes (submission-based) |
| Batch size | 1 syscall per operation | Up to 4096 SQEs per `io_uring_enter` |
| Zero-copy | No (kernel copies to/from buffers) | Yes (`IORING_OP_READ_FIXED` with registered buffers) |

## Async Systemcalls — io_uring Registered Operations

io_uring extends beyond file I/O to support asynchronous versions of many syscalls via registered operations. Each registered operation has an opcode (`IORING_OP_*`) that avoids the overhead of the traditional syscall ABI:

- `IORING_OP_OPENAT` / `IORING_OP_OPENAT2`: Async file open (v5.15+)
- `IORING_OP_STATX`: Async stat (v5.15+)
- `IORING_OP_ACCEPT`: Async socket accept (v5.16+)
- `IORING_OP_SENDMSG` / `IORING_OP_RECVMSG`: Async sendmsg/recvmsg (v5.3+)
- `IORING_OP_PROVIDE_BUFFERS` / `IORING_OP_REMOVE_BUFFERS`: Buffer registration for zero-copy network I/O
- `IORING_OP_SOCKET`: Async socket creation (v5.19+)
- `IORING_OP_RENAMEAT` / `IORING_OP_UNLINKAT`: Async filesystem operations

**Registered buffers** (`io_uring_register_buffers`) pin user pages and create a mapping table. When a `READ_FIXED` or `WRITE_FIXED` operation uses a registered buffer index, the kernel skips page fault handling and copy verification — the pages are already pinned and DMA-mapped. This saves ~200-500 ns per I/O operation.

## Completion-Based vs. Position-Based I/O

Traditional Linux AIO (`libaio`, `io_submit`/`io_getevents`) is **position-based**: each I/O request specifies the file offset. This requires the kernel to track per-request state and match completions to submissions by request ID. It also limits batching.

io_uring is **completion-based** (inspired by Windows IOCP): the CQ is a simple ring buffer. The kernel writes completions in order; the user reads them in order. There is no need for request ID matching, no out-of-order completion handling, and the ring buffer provides natural backpressure (when the CQ is full, the kernel stops processing). This is simpler, faster, and enables better batch processing.

## Performance Numbers

| I/O Mechanism | 4K Random Read IOPS (NVMe) | Syscalls per I/O | Latency (p99) |
|---------------|---------------------------|-------------------|---------------|
| `pread()` blocking | ~200K | 2 (read + return) | ~15 µs |
| `libaio` (`io_submit`) | ~500K | 2 (submit + getevents) | ~10 µs |
| `epoll` + `pread` | ~800K | 2 | ~8 µs |
| `io_uring` (default) | ~1.5M | ~0.5 (batched) | ~5 µs |
| `io_uring` (SQPOLL + registered bufs) | ~2.5M | ~0.05 | ~3 µs |
| SPDK (user-space NVMe) | ~3M | 0 | ~2 µs |

## Interview Questions

1. **"Why does DPDK use polling instead of interrupts?"** Answer hint: At 10+ Mpps, interrupt overhead (context switch, IPI delivery, NAPI scheduling) dominates. Each packet arriving as an interrupt costs ~2-5 µs of CPU time just in interrupt handling. Polling at 40 Mpps costs ~25 ns per empty poll (checking a single memory location). The breakeven is ~1-2 Mpps — below that, polling wastes CPU.

2. **"How does io_uring avoid syscalls on completion?"** Answer hint: The CQ is a shared ring buffer in memory mapped between kernel and userspace. The kernel writes CQEs directly; the user reads them by checking `cq->tail`. No syscall is needed — it's just a memory read with an acquire barrier. The `io_uring_enter` syscall is only needed to wake the kernel when submitting new work.

3. **"What's the trade-off between SPDK and io_uring for a database?"** Answer hint: SPDK gives higher raw IOPS but requires the entire storage stack in userspace (no filesystem, no LVM, no kernel caching). io_uring gives 50-70% of SPDK's performance while keeping the kernel's filesystem, caching, and security model. For a database with its own buffer pool (PostgreSQL, RocksDB), io_uring with `O_DIRECT` is often the better practical choice.

## References
- DPDK Programmer's Guide: https://doc.dpdk.org/guides/
- SPDK Documentation: https://spdk.io/doc/
- Axboe, J. "Efficient IO with io_uring." Linux Kernel Documentation, 2019.
- Rizzo, L. "netmap: A Novel Framework for Fast Packet I/O." USENIX ATC 2012.
