# rseq_slice_yield(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 471 / 471 / 471 / 471 |
| Since (kernel) | -- in the syscalls(2) version table and the ledger (post-4.18 addition to kernel/rseq.c; asm-generic table number 471) |
| Man page | none (no man2/rseq_slice_yield.2 in the man-pages 6.19 HTML set; no man page exists yet) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; base rseq registration is on [rseq](rseq.md) |
| Ledger ID | SC-rseq_slice_yield |

## Purpose

rseq_slice_yield() is the query/clear side of the rseq time-slice-extension feature: a task that was granted a slice extension yields the CPU once it has finished the critical work, and this syscall reports -- and resets -- whether the yield actually happened in the granted window (kernel/rseq.c, comment above SYSCALL_DEFINE0(rseq_slice_yield)). It exists so the extension stays side-effect free: the kernel needs a cheap, explicit handshake to know the task gave the CPU back inside the extension rather than being forced out.

## Synopsis

```c
/* no glibc declaration; called directly */
long syscall(SYS_rseq_slice_yield);
```

## Arguments and behavior

No arguments. The kernel reads `current->rseq.slice.yielded`, clears it, and returns `!!yielded` (kernel/rseq.c, body). The comment in the source states the contract: returns 1 if the task successfully yielded the CPU within the granted slice; returns 0 if the slice extension was never granted, was revoked by going over the granted extension, by issuing a syscall other than this one, or by being scheduled out earlier due to an interrupt. The syscall itself does not schedule -- the syscall-entry work immediately relinquishes the CPU and reschedules if required (kernel/rseq.c, comment). The extension length is tunable through the rseq_slice_ext sysfs knob, bounded by rseq_slice_ext_nsecs_min/max (kernel/rseq.c, rseq_slice_ext_show/rseq_slice_ext_write).

## Return value and errors

1 (yielded inside the granted slice) or 0 (extension not granted/revoked). No error returns are defined in the implementation -- the syscall cannot fail (kernel/rseq.c, body).

## Flags and constants

None.

## Security and notes

This is a cooperative-scheduling knob, not a correctness primitive: misreporting cannot corrupt the kernel, and the 0/1 contract is deliberately trivial. The feature as a whole is gated by the rseq slice-extension config/sysfs knob, so ENOSYS is possible on kernels without it -- callers must treat any nonzero negative return as "feature absent". This page is source-limited: the sole reachable primary source is kernel/rseq.c (master, fall 2026); no man page exists yet, so the behavior section quotes the implementation's own contract comment. Cross-reference: [rseq](rseq.md), [sched_yield](../sched-misc/sched_yield.md).

## References

- Kernel source: kernel/rseq.c (SYSCALL_DEFINE0(rseq_slice_yield) and the contract comment above it, torvalds/linux master, fetched 2026-10-17)
- asm-generic numbering: scripts/syscall.tbl line `471 common rseq_slice_yield sys_rseq_slice_yield`
- worklog: no glibc wrapper symbol (nm -D, glibc 2.41)
