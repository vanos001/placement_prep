# io_uring

## Overview

**io_uring** is Linux's high-performance asynchronous I/O interface, introduced by Jens Axboe in **Linux 5.1 (2019)**. It replaces the traditional "submit a syscall per operation" model with **shared memory rings**: applications submit I/O requests into a submission queue (SQ) and reap results from a completion queue (CQ), batching many operations with very few system calls.

```mermaid
graph LR
    APP["Application"] -->|"writes request"| SQ["Submission Queue (SQ)<br/>(shared mmap ring)"]
    SQ --> KERN["Kernel (io_uring)"]
    KERN -->|"async I/O via<br/>io-wq or poll"| DEV["Block device / socket / file"]
    DEV -->|"completes"| CQ["Completion Queue (CQ)<br/>(shared mmap ring)"]
    CQ --> APP2["Application reaps results"]
```

## Why It Matters: The Problem with epoll + read/write

The classic non-blocking model (`epoll` + `read`/`write`) has two costs:

1. **Per-operation syscalls** — every read/write is a syscall even with epoll.
2. **No true async for regular files** — reads on disk files block (or need thread pools).

io_uring removes both: one `io_uring_enter` can submit **many** operations at once (amortizing the syscall), and the kernel performs the I/O asynchronously in the background (`io-wq` worker threads or poll-based), completing via the CQ ring. Result: high IOPS and low latency for storage-heavy workloads.

## The API (briefly)

```text
io_uring_setup(entries, params)   → creates SQ/CQ rings + returns fd
mmap the rings (IORING_OFF_SQ, IORING_OFF_CQ)
io_uring_enter(fd, to_submit, min_complete)  → submit SQEs, wait for CQEs
io_uring_register(fd, ...)        → register files/buffers for reuse
```

Key features that make it fast:

- **Fixed buffers** (`IORING_REGISTER_BUFFERS`) — avoid repeated `get_user_pages`/pinning per op.
- **Registered files** (`IORING_REGISTER_FILES`) — skip file-descriptor table lookups per op.
- **Poll mode** (`IOSQE_ASYNC` / provided buffers) — busy-poll or event-driven completion with low latency.
- **Multishot** — one SQE delivers many completions (useful for accept/recv).
- **Provided buffers** — the app pre-registers a buffer pool the kernel fills.

## Use Cases

| Area | Examples |
|---|---|
| **Storage engines** | RocksDB, ScyllaDB, SeaweedFS, SPDK-adjacent user-space stacks |
| **Databases** | Postgres (experimental io_uring support), MySQL (proposed) |
| **File servers / proxies** | nginx (experimental), custom high-throughput servers |
| **Network servers** | Combining sockets with io_uring for a unified async model |
| **Libraries** | liburing (C), tokio-uring (Rust), glommio (Rust), io_uring support in Node/libuv experiments |

## io_uring vs Alternatives

| Model | Syscalls | True async for files | Complexity |
|---|---|---|---|
| Blocking threads | 1+ per op | No (threads) | Simple |
| epoll + non-blocking | 1+ per op | No (files still block) | Medium |
| io_uring | ~1 per batch | Yes | Higher (ring management, kernel version gating) |
| DPDK / SPDK (userspace) | None (bypass kernel) | Yes | Very high, requires dedicated NICs/disks |

## Limitations and Risks

- **Kernel version gating** — features land incrementally; older kernels lack poll mode, fixed buffers, multishot, etc. Production code must feature-detect.
- **Not every operation is async** — some paths still fall back to blocking (e.g., certain fsync/file types).
- **Security scrutiny** — the attack surface has had CVEs; keep kernels patched (this is why some distros gate io_uring for unprivileged use).
- **Complexity** — ring synchronization, memory ordering (SMP barriers), and the learning curve are real costs.
- Not available/stable on all container runtimes without seccomp allowances.

## Interview Questions

### Q: How does io_uring achieve lower latency than epoll + read?

Three ways: (1) **batching** — one `io_uring_enter` submits many ops, amortizing syscall cost; (2) **true asynchrony for files** — the kernel runs the I/O in the background (io-wq/poll) and completes via the CQ ring, so the app doesn't block on disk reads; (3) **reduced overhead per op** — registered files and fixed buffers skip per-op setup (fd lookups, page pinning).

### Q: What are the SQ and CQ rings?

The SQ (submission queue) is a shared-memory ring where the app writes **SQEs** (submission queue entries describing each I/O: fd, offset, length, flags). The kernel consumes them and, on completion, posts **CQEs** (completion queue entries) to the CQ ring the app reads. Sharing via `mmap` means no per-operation syscall — only an occasional `io_uring_enter` to submit and/or wait.

### Q: When would you NOT use io_uring?

When the workload is latency-insensitive, simple, or must run on old kernels/restricted sandboxes (containers with seccomp filters may block it). For most web apps, epoll + thread pools is sufficient; io_uring pays off for storage-heavy, high-IOPS, or low-latency-file workloads where its complexity is justified.

## References

- io_uring official docs — https://github.com/axboe/liburing
- Kernel documentation: io_uring — https://docs.kernel.org/io_uring/
- Jens Axboe, *Efficient IO with io_uring* (LWN series) — https://lwn.net/Articles/810414/
- The xz paper: *io_uring and the kernel interface* — https://kernel.dk/io_uring.pdf

## Related Topics

- [Linux Kernel Internals](./README.md) — where io_uring lives
- [I/O Systems](../io/README.md) — the syscall model it replaces
- [DMA](../io/dma.md) — how the kernel moves data underneath
- [Interrupts](../io/interrupts.md) — completion notification path
- [Virtual Memory](../virtual-memory/README.md) — pinned buffers and mmap
