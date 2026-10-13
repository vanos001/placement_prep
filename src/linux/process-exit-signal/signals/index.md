# Signals — Deep Reference

This section is the source-backed inventory of the Linux signal set itself: what each signal
means, how it is numbered on every architecture the kernel ships, what the kernel guarantees
about delivery, and how the real-time signal range behaves. It complements — and deliberately
goes deeper than — the overview chapter [Signals](../../sysprog/signals.md), which introduces
the programming model (handlers, masks, the self-pipe trick) at survey level.

The pages in this section are organized around the coverage ledger
([process-exit-signal-coverage.md](../../process-exit-signal-coverage.md)), which assigns
stable IDs `SIG-001` through `SIG-040` to every requirement in this area:

| Page | Coverage | IDs |
|------|----------|-----|
| [Standard signals](./standard-signals.md) | The 31 classic signals one by one (name, per-architecture number, purpose, default action, catchability, core-dump behavior, practical use and caveats), the full architecture numbering table, disposition rules, and generation-vs-delivery semantics (no queueing, pending set, blocking) | SIG-001 – SIG-034 |
| [Real-time signals](./real-time-signals.md) | `SIGRTMIN`–`SIGRTMAX` placement (kernel vs glibc vs musl), queuing and ordering guarantees, `RLIMIT_SIGPENDING` limits and `EAGAIN`, `sigqueue(3)`/`rt_sigqueueinfo(2)`, trade-offs and common misconceptions | SIG-035 – SIG-040 |

## Scope and verification

All signal numbers quoted in this section were verified directly against the Linux kernel UAPI
headers (`include/uapi/asm-generic/signal.h` and the per-architecture
`arch/*/include/uapi/asm/signal.h` in the `torvalds/linux` tree, checked at fetch time) and
cross-checked against [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html) from the
Linux man-pages project. Behavioral claims are cited to the man page that documents them, and
each chapter separates POSIX/C-standard guarantees from Linux-specific and libc-specific
behavior. The chapters state exactly which kernel tree version and architecture set the tables
cover; completeness beyond that set is not claimed.

## Related Topics

- [Signals overview](../../sysprog/signals.md) — the survey-level programming model
- [Interfaces](../interfaces/index.md) — the system calls and library functions that send, block, and catch these signals
- [Per-syscall pages: signals and time](../../syscalls/signals-time/overview.md) — kernel-level reference for `kill(2)`, `rt_sigaction(2)`, `tgkill(2)` and friends
- [Exit status and lifecycle](../../process-exit-signal-coverage.md) — the unified ledger this section maps to

## References

- *signal(7) — overview of signals*, Linux man-pages project, <https://man7.org/linux/man-pages/man7/signal.7.html>
- *Linux kernel UAPI signal headers*, torvalds/linux tree, <https://github.com/torvalds/linux/tree/master/include/uapi/asm-generic> and per-arch `arch/*/include/uapi/asm/signal.h`
- *POSIX.1-2017 (IEEE Std 1003.1-2017)*, The Open Group, <https://pubs.opengroup.org/onlinepubs/9699919799/>
