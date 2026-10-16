# ulimit(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / 58 / -- / -- |
| Since (kernel) | -- (syscalls(2) lists ulimit(2) among the never-implemented set) |
| Man page | man2/unimplemented.2 lists ulimit(2) among the unimplemented system calls (fetched 2026-10-17); the library routine is man3/ulimit.3 (fetched: "ulimit - get and set process limits") |
| glibc wrapper | ulimit(3) W @@GLIBC_2.2.5 (nm -D, glibc 2.41) -- a pure library function on Linux |
| Aliases covered | grouped topic page: [unimplemented](unimplemented.md) |
| Ledger ID | SC-ulimit |

## Purpose

ulimit(2) is the reserved i386 slot (number 58) for the V7-era process-limits call; Linux never implemented it. The live interface is the ulimit(3) library routine -- which the man pages describe as obsolete -- and the real kernel mechanism is getrlimit/setrlimit(2) (see [getrlimit](../process/getrlimit.md)).

## Synopsis

```c
/* library routine (man3/ulimit.3) */
#include <ulimit.h>
[[deprecated]] long ulimit(int cmd, long newlimit);
/* the SYS_ulimit slot always returns -ENOSYS */
```

## Arguments and behavior

Kernel slot: no behavior, always -ENOSYS (unimplemented.2, RETURN VALUE). The library routine's UL_GETFSIZE/UL_SETFSIZE commands map onto the rlimit machinery.

## Return value and errors

Kernel slot: always -1 with ENOSYS. Library routine: per-command values, -1 on error.

## Flags and constants

UL_GETFSIZE, UL_SETFSIZE (<ulimit.h>).

## Security and notes

Interview angle: ulimit is the shell builtin everyone knows, backed by a libc shim, backed by getrlimit(2) -- the syscall slot itself is a fossil. The 4.2BSD lineage note in the getdtablesize page pairs with this one. Cross-reference: [unimplemented](unimplemented.md), [getrlimit](../process/getrlimit.md), [getdtablesize](getdtablesize.md).

## References

- https://man7.org/linux/man-pages/man2/unimplemented.2.html (ulimit listed)
- https://man7.org/linux/man-pages/man3/ulimit.3.html
- worklog: wrapper symbol ulimit W @@GLIBC_2.2.5 verified with nm -D (2026-10-17)

