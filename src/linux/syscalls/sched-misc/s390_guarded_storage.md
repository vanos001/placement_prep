# s390_guarded_storage(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (s390 table only) |
| Since (kernel) | 4.12 (s390_guarded_storage.2 HISTORY: "Linux 4.12, System z14") |
| Man page | man2/s390_guarded_storage.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | none -- "glibc provides no wrapper for s390_guarded_storage(), necessitating the use of syscall(2)" (s390_guarded_storage.2, SYNOPSIS) |
| Aliases covered | none |
| Ledger ID | SC-s390_guarded_storage |

## Purpose

s390_guarded_storage() enables and controls the z/Architecture Guarded Storage Facility for the calling task: up to 64 memory regions (as of z14) can be marked guarded, and the Load Guarded (LGG) / Load Logical and Shift Guarded (LLGFSG) instructions range-check the loaded value against those regions, invoking a userspace handler when one is affected (s390_guarded_storage.2, DESCRIPTION). The facility gives managed runtimes a hardware hook for write-barrier-style tracking of pointer stores.

## Synopsis

```c
#include <asm/guarded_storage.h>   /* GS_* constants, struct gs_cb */
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_s390_guarded_storage, int command, struct gs_cb *gs_cb);
```

## Arguments and behavior

`command` selects the operation per the man page's command list: GS_ENABLE (enable the facility for the task, allocating the guarded-storage control block), GS_DISABLE, GS_SET_BC_CB (set the broadcase-control block), GS_CLEAR_BC_CB, GS_RESTORE_THREAD / GS_LOAD... variants that save/restore or load the control block (s390_guarded_storage.2, DESCRIPTION). `gs_cb` carries or receives the Guarded Storage Control Block; its `gsepla` field points at the Guarded Storage Event Parameter List holding the userspace handler address (s390_guarded_storage.2, DESCRIPTION/NOTES).

## Return value and errors

0 on success; -1 with errno (s390_guarded_storage.2, RETURN VALUE). Errors: EFAULT (copying the gs_cb failed on GS_SET_BC_CB), EINVAL (bad command), ENOMEM (control-block allocation failed for GS_ENABLE/GS_SET_BC_CB), EOPNOTSUPP (hardware lacks the facility) (s390_guarded_storage.2, ERRORS).

## Flags and constants

GS_ENABLE, GS_DISABLE, GS_SET_BC_CB, GS_CLEAR_BC_CB and the save/restore commands (<asm/guarded_storage.h>).

## Security and notes

The facility exists for language runtimes (the Java/JIT use case is the public one), not for general programming -- hence s390-only, syscall-only access, and kernel-managed per-thread state that gets saved/restored across context switches. Interview angle: guarded storage vs page-protection-based write barriers (mprotect + SIGSEGV handlers) is the classic managed-runtime comparison; guarded storage avoids the fault cost but pins you to z14+. Cross-reference: [mprotect](../memory/mprotect.md), [userfaultfd](../memory/userfaultfd.md), [perf_event_open](perf_event_open.md).

## References

- https://man7.org/linux/man-pages/man2/s390_guarded_storage.2.html
- man-pages syscalls(2) (4.12, s390 only)
