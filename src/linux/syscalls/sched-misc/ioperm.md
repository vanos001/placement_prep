# ioperm(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 173 / 101 / - / - (cached kernel tables; hub agrees) |
| Since (kernel) | 1.0 (hub; man page states no version) |
| Man page | man2/ioperm.2 (local cache, dated 2021-03-22) |
| glibc wrapper | Declared in <sys/io.h> (and the i386-only <sys/perm.h>, which the man page says to avoid); ioperm@@GLIBC_2.2.5 (nm -D on glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-ioperm (researched/BRIEF) |

## Purpose

ioperm() sets the per-thread x86 I/O-port access permission bits for num ports starting at from: turn_on nonzero enables access (and requires CAP_SYS_RAWIO), zero disables it. Before Linux 2.6.8 only the first 0x3ff ports could be managed this way (above that, iopl(2) level 3 was needed); since 2.6.8 all 65,536 ports can be. Permissions are inherited by fork(2) children (not before Linux 2.4) and preserved across execve(2), which is how a privileged loader can hand port access to an unprivileged program.

## Synopsis

```c
#include <sys/io.h>
int ioperm(unsigned long from, unsigned long num, int turn_on);
```

## Return value and errors

Returns 0 on success; -1 with errno: EINVAL (invalid from or num), EIO (PowerPC: unsupported), ENOMEM (I/O bitmap allocation), EPERM (insufficient privilege).

## Security and notes

- x86-centric: mostly for i386; on many other architectures it does not exist or always errors.
- /proc/ioports shows which ports the system has allocated.
- Granting port access across execve(2) is a deliberate privilege handoff; scope it tightly.

## References

- man2/ioperm.2 in the cached man-pages tree (dated 2021-03-22).
- [Syscalls ledger](../ledger.md) row SC-ioperm; [Domain hub](overview.md).
- Sibling: [iopl](iopl.md) (whole-privilege-level alternative).
