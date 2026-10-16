# s390_runtime_instr(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (s390 table only) |
| Since (kernel) | 3.7 (s390_runtime_instr.2 HISTORY: "Linux 3.7. System z EC12") |
| Man page | man2/s390_runtime_instr.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | none -- "glibc provides no wrapper for s390_runtime_instr(), necessitating the use of syscall(2)" (s390_runtime_instr.2, SYNOPSIS) |
| Aliases covered | none |
| Ledger ID | SC-s390_runtime_instr |

## Purpose

s390_runtime_instr() starts or stops z/Architecture CPU run-time instrumentation for the calling thread: the hardware collects instruction-level event records into a per-thread buffer (s390_runtime_instr.2, DESCRIPTION). On start the kernel assigns the thread a default run-time-instrumentation control block, which the caller then tunes and enables (s390_runtime_instr.2, RETURN VALUE).

## Synopsis

```c
#include <asm/runtime_instr.h>   /* S390_RUNTIME_INSTR_* constants */
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_s390_runtime_instr, int command, int signum);
```

## Arguments and behavior

`command` is S390_RUNTIME_INSTR_START (1) or S390_RUNTIME_INSTR_STOP (2) (s390_runtime_instr.2, DESCRIPTION). `signum` once named the real-time signal to raise on buffer-full or instrumentation-halt events; the feature "was never used", signaling support was removed in 4.4, and the argument is now ignored -- but for older-kernel compatibility callers should still pass a valid RT signal number and install a handler (s390_runtime_instr.2, DESCRIPTION/NOTES). The <asm/runtime_instr.h> header is available since 4.16 (s390_runtime_instr.2, NOTES).

## Return value and errors

0 on success (thread enabled with a default control block); -1 with errno (s390_runtime_instr.2, RETURN VALUE). Errors: EINVAL (invalid command; invalid signum on pre-4.4 kernels), ENOMEM (control-block allocation failed), EOPNOTSUPP (facility unavailable) (s390_runtime_instr.2, ERRORS).

## Flags and constants

S390_RUNTIME_INSTR_START (1), S390_RUNTIME_INSTR_STOP (2) (<asm/runtime_instr.h>).

## Security and notes

Instrumentation state is per-thread and kernel-managed -- the syscall is the enable knob, while all tuning happens through the control block the kernel hands back. The dead `signum` parameter is a compact case study in ABI inertia: three arguments where one remains meaningful, with the man page instructing callers to keep passing a plausible signal number for old kernels. Cross-reference: [perf_event_open](perf_event_open.md), [s390_guarded_storage](s390_guarded_storage.md), [s390_sthyi](s390_sthyi.md).

## References

- https://man7.org/linux/man-pages/man2/s390_runtime_instr.2.html
- man-pages syscalls(2) (3.7, s390 only)
