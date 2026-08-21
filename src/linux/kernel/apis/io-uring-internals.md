# io_uring Internals

`io_uring` is the Linux asynchronous I/O interface merged in kernel 5.1 (2019) and substantially extended in every release since. It replaced `aio`/`libaio` (which required unsafe pre-allocated buffers, blocking setup, and was widely considered broken) with a pair of shared-memory ring buffers shared between user space and the kernel — no system calls on the fast path. This page covers the internal data structures, the submission/completion queue protocol, polling modes, and the failure modes that have driven multiple CVEs.

## Core Data Structures

An io_uring instance is created with `io_uring_setup(entries, params)`, which returns a file descriptor. The kernel then maps two shared ring buffers into the process's address space:

```c
struct io_uring_params {
    __u32 sq_entries;       /* SQ ring size, always power of 2 */
    __u32 cq_entries;       /* CQ ring size, >= sq_entries */
    __u32 flags;            /* IORING_SETUP_IOPOLL, SQPOLL, etc. */
    __u32 sq_thread_cpu;   /* bind SQ polling thread to CPU */
    __u32 sq_thread_idle;  /* SQ poll thread idle timeout (ms) */
    __u32 features;        /* kernel feature flags */
    __u32 wq_fd;           /* worker pool fd (NAPI mode) */
    __u32 resv[3];
    struct io_sqring_offsets sq_off;   /* offsets into mmap'd region */
    struct io_cqring_offsets cq_off;
};
```

The submission queue (SQ) and completion queue (CQ) are single-producer, single-consumer rings with a `head`/`tail` index pair, free-running modular arithmetic, and an explicit memory ordering contract.

```text
              SQ (kernel consumes)               CQ (user consumes)
   +---+---+---+---+---+                      +---+---+---+---+---+
   | 0 | 1 | 2 | 3 | 4 |  ...                  | C | C | C | . | . |
   +---+---+---+---+---+                      +---+---+---+---+---+
     ^                                             ^
   sqes[] array indexed                       head/tail pair, monotonically
   by sq_array[] (indirection)                increasing mod mask
```

The SQ holds 8-byte indices into a separate `sqes[]` array of `struct io_uring_sqe`. This indirection lets the kernel reorder submissions and lets user space batch many SQEs without worrying about ordering.

## Submission Path

The user fills an SQE in the `sqes[]` array, then writes the SQE's index into `sq_array[sq_tail]` and advances `sq_tail` with a release store. The kernel observes the new tail via a `smp_load_acquire()` on the SQ ring's tail field and processes SQEs.

```c
struct io_uring_sqe {
    __u8    opcode;     /* IORING_OP_READV, WRITEV, SEND, RECV, ... */
    __u8    flags;      /* IOSQE_IO_LINK, IOSQE_BUFFER_SELECT, ... */
    __u16   ioprio;     /* for IOPRIO_CLASS_RT/BE/IDLE */
    __s32   fd;         /* file descriptor */
    union { __u64 off; __u64 addr2; };
    union { __u64 addr; __u64 splice_off_in; };
    __u32   len;        /* buffer length or count */
    union { /* accept, timeout, cancel args */ };
    __u64   user_data;  /* opaque — returned verbatim in the CQE */
    union { __u16 buf_index; __u16 buf_group; };
    __s16   personality;
    __s32   splice_fd_in;
    __u64   addr3;
    __u64   __pad2[1];
};
```

The `user_data` field is the contract that makes asynchronous dispatch tractable: the kernel returns it unchanged in the CQE, so the application matches completions to submissions without maintaining its own in-flight table.

## Completion Path

When an operation finishes, the kernel writes a CQE into the CQ ring:

```c
struct io_uring_cqe {
    __u64   user_data;  /* the value from the SQE */
    __s32   res;        /* result: bytes read, 0, or -errno */
    union { __u32 flags; __u32 cflags; };
};
```

The user observes CQEs by reading `cq_head` with `smp_load_acquire()` on the CQ ring's tail. If `head < tail`, completions are available. The user processes them and advances `head` with a release store.

A typical completion loop:

```c
unsigned head;
struct io_uring_cqe *cqe;

io_uring_for_each_cqe(ring, head, cqe) {
    if (cqe->res < 0) {
        fprintf(stderr, "op %llx failed: %s\n",
                (unsigned long long)cqe->user_data,
                strerror(-cqe->res));
        /* handle failure — reschedule, retry, abort */
    } else {
        /* dispatch on user_data */
    }
}
io_uring_cq_advance(ring, head);  /* publish new head */
```

The barrier protocol is the trickiest part. The kernel uses `smp_store_release()` on `cq->tail` after writing CQEs, and the user uses `smp_load_acquire()` to observe them — guaranteeing that the user sees the CQE fields before seeing the new tail. Conversely, the user uses `smp_store_release()` on `sq->tail` after writing SQEs, and the kernel uses `smp_load_acquire()`.

## Polling Modes

io_uring's performance depends heavily on which polling mode is enabled.

### Default (interrupt-driven)

The kernel processes the SQ when the user explicitly calls `io_uring_enter(fd, to_submit, min_complete, flags)`. Each call is a system call; batching amortizes the cost.

### `IORING_SETUP_SQPOLL` (kernel polling thread)

The kernel spawns a dedicated kernel thread (`io_sq_thread`) that busy-polls the SQ. Submissions become visible to the kernel without any system call from user space. The thread parks after `sq_thread_idle` milliseconds of inactivity. This is the lowest-latency mode and is mandatory for the highest-throughput storage engines (ScyllaDB, RocksDB with `io_uring` async).

### `IORING_SETUP_IOPOLL` (interrupt-free storage)

For NVMe polled I/O, the kernel issues no interrupts. The user must call `io_uring_enter(IORING_ENTER_GETEVENTS)` to drain CQEs. This eliminates interrupt overhead but requires the device driver to support `IRQ_QUEUES` style polling (modern NVMe drivers do).

### `IORING_SETUP_SQPOLL | IORING_SETUP_IOPOLL`

The combo gives near-zero system calls on the fast path. ScyllaDB reports >2M IOPS per core in this configuration with NVMe devices.

## Registered Buffers and Pages

`IORING_REGISTER_BUFFERS` pins a fixed set of user buffers into kernel memory once, so subsequent `IORING_OP_READ_FIXED`/`WRITE_FIXED` operations avoid `get_user_pages()` on every I/O. This is critical for high-IOPS workloads because `gup()` is dominated by TLB shootdowns and page-table walks.

`IORING_REGISTER_BUFFERS` with `IORING_REGISTER_PBUF_RING` (kernel 5.19+) adds **buffer pools** that let the kernel pick a free buffer for a `IOSQE_BUFFER_SELECT` receive, removing the user's bookkeeping for recv-side pooling.

## The Cancel, Timeout, and Link Chains

SQEs support two chaining primitives:

- `IOSQE_IO_LINK` — the next SQE cannot start until this one completes. Used for ordering dependencies (e.g., write-after-read).
- `IOSQE_IO_HARDLINK` — same, but chain does not break on error.
- `IOSQE_IO_DRAIN` — this SQE cannot start until every previously submitted SQE has completed. Used for serializing barriers.

A linked chain is a single submission unit: the kernel inserts them together and propagates results along the chain.

## Why io_uring Has CVEs

`io_uring`'s attack surface is unusually large because every release adds new opcodes, and each opcode runs in kernel context with arbitrary user-controlled file descriptors, offsets, buffers, and registered resources. A 2022 audit found:

- `IORING_OP_OPENAT` allowed opening paths relative to a directory whose `struct file` had been freed, leading to use-after-free.
- `IORING_OP_SPLICE` against a non-spliceable file descriptor performed an unexpected file_operations dispatch.
- Poll entries (`IORING_OP_POLL_ADD`) survived file close, racing with `release()` and corrupting the file table.

As a result, kernel 6.0 added `IORING_SETUP_NO_SQARRAY` and the `IORING_SETUP_DEFER_TASKRUN` mode (uses workqueue to defer completion processing to the user's task context), and io_uring is now disabled by default in unprivileged user namespaces on many distributions. See [CVE-2022-29582](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2022-29582) and the [Google Project Zero writeup](https://google.github.io/security-research/pocs/linux/cve-2022-29582/).

The defensive posture for io_uring in production: prefer `IORING_SETUP_SQPOLL` and pre-registered buffers, restrict opcodes to a known allow-list when the application permits it (kernel 6.0+ exposes `IORING_REGISTER_IOWQ_AFF` and `IORING_REGISTER_RESTRICTIONS`), and audit for kernel CVEs on every minor release.

## Comparison to Alternatives

| Mechanism | Syscalls per I/O | Memory model | Async? | Notes |
|-----------|-----------------:|--------------|--------|-------|
| `read`/`write` | 1 | Buffered through page cache | No | Default; works everywhere |
| `pread`/`pwrite` | 1 | Same as read/write | No | Position-aware |
| `aio_read`/`aio_write` | 1 setup + 1 reap | Requires buffer pre-pin, O_DIRECT only on most filesystems | Yes, broken | Hard 4 KB alignment; SIGEV_SIGNAL is racy |
| `epoll` + non-blocking sockets | 1 per event | Page cache | Event-based | Network only — no disk |
| `io_uring` default | 1 per batch | Page cache + registered buffers | Yes | 1 syscall per batch of N |
| `io_uring` SQPOLL | 0 fast path | Registered buffers only | Yes | Kernel thread polls SQ |
| `io_uring` SQPOLL + IOPOLL | 0 fast path, 0 IRQ | Registered buffers only | Yes | Maximum throughput, NVMe only |

## Common Pitfalls

1. **Forgetting `io_uring_submit()` after writing SQEs.** Without SQPOLL, the SQ is only drained when the user explicitly enters the kernel. A bug where the user fills the SQ and waits on the CQ will deadlock.
2. **Sharing `user_data` values across in-flight operations.** `user_data` must be unique among concurrently-in-flight SQEs, or the completion dispatch becomes ambiguous. Use a monotonically increasing counter.
3. **Closing registered file descriptors before `IORING_REGISTER_FILES_UPDATE` removes them.** The kernel holds a reference, but operations queued against the old index can fire after the user thought the slot was free. Use `IORING_REGISTER_FILES` with fixed-slot semantics and never mix fixed and normal `fd`s in the same ring.
4. **Assuming `res >= 0` means success.** For `IORING_OP_READ`, short reads are legal — `res` is the actual number of bytes, which may be less than requested. Handle short reads explicitly or use `IORING_OP_READV` with multi-vec semantics.
5. **Mixing SQPOLL and not-SQPOLL rings on the same thread.** Memory-ordering bugs across two rings can stall completion. Use one ring per thread.

## References

- Axel Dahlberg, "io_uring: A new Linux asynchronous I/O API" — [kernel documentation](https://docs.kernel.org/filesystem/io_uring.html)
- Jens Axboe, [`liburing`](https://github.com/axboe/liburing) — reference userspace library
- [LWN: "io_uring and asynchronous I/O" (2019)](https://lwn.net/Articles/776703/) and the four-part follow-up
- [Pavel Begunkov, Jens Axboe, "Efficient IO with io_uring" (2020)](https://kernel.dk/io_uring.pdf)
- [Google Project Zero: CVE-2022-29582 writeup](https://google.github.io/security-research/pocs/linux/cve-2022-29582/)
- [Phoronix: io_uring kernel changes per release](https://www.phoronix.com/scan.php?page=news_item&px=Linux-5.18-io_uring)
