# perfmonctl(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (IA-64 only) |
| Since (kernel) | 2.4; removed in 5.10 (perfmonctl.2 HISTORY: "This system call was broken for many years, and was ultimately removed in Linux 5.10") |
| Man page | man2/perfmonctl.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | none -- "glibc does not provide a wrapper for this system call; on kernels where it exists, call it using syscall(2)" (perfmonctl.2, HISTORY) |
| Aliases covered | none |
| Ledger ID | SC-perfmonctl |

## Purpose

perfmonctl() drove the IA-64 PMU (performance monitoring unit): it applied a command (`cmd`) with `narg` arguments against a perfmon context identified by `fd`, where PMD/PMC registers gather the hardware statistics (perfmonctl.2, DESCRIPTION). The command set ranged from PFM_CREATE_CONTEXT (returning the context fd) through event-set programming, start/stop, and readout commands (perfmonctl.2, DESCRIPTION).

## Synopsis

```c
#include <syscall.h>
#include <perfmon.h>
long perfmonctl(int fd, int cmd, void arg[narg], int narg);
```

## Arguments and behavior

`fd` selects the context (ignored for PFM_CREATE_CONTEXT, which returns the new context fd in ctxt->ctx_fd); `cmd` selects the operation; `arg`/`narg` pass the per-command argument vector (perfmonctl.2, DESCRIPTION). On success it returns 0; -1 with errno otherwise (perfmonctl.2, RETURN VALUE). The interface was IA-64-only, was broken for years, and was removed in 5.10; the generic successor already documented in this encyclopedia is [perf_event_open](perf_event_open.md).

## Return value and errors

0 on success; -1 with errno on error (perfmonctl.2, RETURN VALUE). The per-command error set was never exhaustively documented in the man page -- itself part of the interface's decline story.

## Flags and constants

PFM_* command constants (<perfmon.h>): PFM_CREATE_CONTEXT and the context/event-control family (perfmonctl.2, DESCRIPTION).

## Security and notes

Two interview-ready lessons: (1) hardware-performance interfaces carry privilege requirements (PMU programming is CPU-wide state), which perf_event_open addresses with per-event CAP checks and the perf_event_paranoid sysctl; (2) a syscall tied to one dying architecture gets removed once its userspace evaporates -- exactly the 5.10 outcome here. Cross-reference: [perf_event_open](perf_event_open.md), [getrusage](../process/getrusage.md), [modify_ldt](modify_ldt.md).

## References

- https://man7.org/linux/man-pages/man2/perfmonctl.2.html
- man-pages syscalls(2) (2.4, IA-64 only, removed)
