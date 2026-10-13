# iopl(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 172 / 110 / - / - (cached kernel tables; hub agrees) |
| Since (kernel) | 1.0 (hub; the cached man page states no version, so the hub value is kept) |
| Man page | man2/iopl.2 (local cache, dated 2021-03-22) |
| glibc wrapper | Declared in <sys/io.h> (and the i386-only <sys/perm.h>); iopl@@GLIBC_2.2.5 (nm -D on glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-iopl (researched/BRIEF) |

## Purpose

iopl() changes the x86 I/O privilege level (IOPL) of the calling thread to the two least significant bits of level: 0 for a normal thread up to 3 for full port access. Unlike ioperm(2) it is all-or-nothing over all ports rather than a bitmap, slower, and deprecated -- kept mainly for older X servers needing all 65,536 ports. It is mostly an i386 interface; on many other architectures it does not exist or always errors.

## Synopsis

```c
#include <sys/io.h>
int iopl(int level);
```

## Return value and errors

Returns 0 on success; -1 with errno: EINVAL (level greater than 3), ENOSYS (unimplemented), EPERM (raising the level requires CAP_SYS_RAWIO).

## Security and notes

- Before Linux 5.5 a raised IOPL also allowed disabling interrupts while running, which could crash the system; that side effect is gone.
- Before 3.7 permissions were inherited across fork(2) and preserved across execve(2) on some architectures; 3.7 removed that.
- Prefer ioperm(2) for scoped port access; IOPL 3 is the sledgehammer.

## References

- man2/iopl.2 in the cached man-pages tree (dated 2021-03-22).
- [Syscalls ledger](../ledger.md) row SC-iopl; [Domain hub](overview.md).
- Sibling: [ioperm](ioperm.md) (per-port bitmap).
