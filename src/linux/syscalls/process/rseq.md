# rseq(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 334 / 386 / 293 / 398 |
| Since (kernel) | 4.18 |
| Man page | none on man7.org (no man2/rseq.2 in the 6.19 HTML set fetched 2026-10-17); documented from kernel/rseq.c and /usr/include/linux/rseq.h -- source-limited on prose |
| glibc wrapper | no exported rseq() function (glibc 2.41, nm -D); since 2.35 glibc registers the rseq area for every thread itself via the `__rseq` ABI, so applications normally read `__rseq` rather than calling the syscall |
| Aliases covered | rseq_slice_yield (471 / 471 / 471 / 471) has its own page: [rseq_slice_yield](rseq_slice_yield.md) |
| Ledger ID | SC-rseq |

## Purpose

rseq() registers a restartable sequence area for the calling thread: a userspace-visible `struct rseq` (plus an optional `struct rseq_cs` critical-section descriptor) that the kernel keeps coherent across preemption and migration. Code inside a declared critical section either runs to completion or the kernel aborts it by writing the abort tag into the area, giving lock-free algorithms a cheap fallback path without CAS loops on shared flags (kernel/rseq.c; /usr/include/linux/rseq.h). It is the interface behind per-CPU counters, resizable lock-free structures, and glibc/TLS fast paths that must not pay an atomic per access.

## Synopsis

```c
#include <linux/rseq.h>   /* struct rseq, RSEQ_FLAG_* (uapi header) */
long syscall(SYS_rseq, struct rseq *rseq, uint32_t rseq_len,
             int flags, uint32_t sig);
```

## Arguments and behavior

`rseq` points to the thread's area (32-byte aligned in practice via the ABI), `rseq_len` is its length (must match `sizeof(struct rseq)`), `sig` is a 32-bit signature written into abort events so userspace can distinguish aborts from its own code, and `flags` selects the operation (kernel/rseq.c, SYSCALL_DEFINE4(rseq)). Registration uses flags 0; unregistering passes RSEQ_FLAG_UNREGISTER (value 1 << 0, /usr/include/linux/rseq.h enum). Re-registering without unregistering fails with EBUSY; registering with the wrong length fails with EINVAL; a mismatched `sig` on re-registration fails with EPERM (kernel/rseq.c, rseq registration checks). The kernel updates `cpu_id`, `node_id`, `mm_cid` and the critical-section state on every return to userspace; on abort it sets `rseq_cs` to the signature ORed with the abort flag bits (RSEQ_CS_FLAG_NO_RESTART_ON_PREEMPT/SIGNAL/MIGRATE select which events abort, /usr/include/linux/rseq.h).

## Return value and errors

0 on success; a negated error on the raw path. Documented in the source: EINVAL (bad flags, wrong rseq_len, unaligned area), EFAULT (area unreadable), EBUSY (already registered), EPERM (sig mismatch on re-registration), ENOSYS on kernels without CONFIG_RSEQ (kernel/rseq.c).

## Flags and constants

| Flag | Value | Note |
|---|---|---|
| RSEQ_FLAG_UNREGISTER | 1 << 0 | unregister the thread's area (/usr/include/linux/rseq.h) |
| RSEQ_CS_FLAG_NO_RESTART_ON_PREEMPT | 1U << 0 (bit 0) | per-CS: do not abort on preemption |
| RSEQ_CS_FLAG_NO_RESTART_ON_SIGNAL | 1U << 1 (bit 1) | per-CS: do not abort on signal delivery |
| RSEQ_CS_FLAG_NO_RESTART_ON_MIGRATE | 1U << 2 (bit 2) | per-CS: do not abort on CPU migration |

## Security and notes

One registered area per thread; the area is per-thread state even though the struct lives in shared memory by convention. The signature (`sig`) exists so a jumped-to abort handler can verify the abort came from the expected registration -- a hardening against stray memory corruption rather than a security boundary. glibc 2.35+ registers the area itself; libraries must detect and reuse the registered area (the `__rseq` symbol) instead of calling rseq() again, or they will hit EBUSY. The 6.x-era follow-up syscalls in this family: rseq_slice_yield (see [rseq_slice_yield](rseq_slice_yield.md)). This page is source-limited: kernel/rseq.c (master, fall 2026) and the uapi header were the reachable sources; no man page is hosted on man7.org. Cross-reference: [futex](futex.md), [getcpu](../sched-misc/getcpu.md), [sched_setaffinity](../sched-misc/sched_setaffinity.md), [membarrier](../memory/membarrier.md).

## References

- Kernel source: kernel/rseq.c (SYSCALL_DEFINE4(rseq), torvalds/linux master, fetched 2026-10-17)
- UAPI header: /usr/include/linux/rseq.h (struct rseq, RSEQ_FLAG_UNREGISTER, RSEQ_CS_FLAG_*)
- man-pages syscalls(2) version table (4.18)
- worklog: no exported rseq() wrapper symbol (nm -D, glibc 2.41)
