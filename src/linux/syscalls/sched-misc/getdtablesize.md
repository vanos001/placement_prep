# getdtablesize(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (SPARC slot only; syscalls(2): "SPARC (removed in 2.6.26)") |
| Since (kernel) | 2.0 |
| Man page | man2/getdtablesize.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | getdtablesize(3) W @@GLIBC_2.2.5 (nm -D, glibc 2.41) -- a pure library function on Linux: "The glibc version of getdtablesize() calls getrlimit(2) and returns the current RLIMIT_NOFILE limit, or OPEN_MAX when that fails" (getdtablesize.2, NOTES) |
| Aliases covered | none |
| Ledger ID | SC-getdtablesize |

## Purpose

getdtablesize() returns the maximum number of files a process can have open -- one more than the largest possible file descriptor value (getdtablesize.2, DESCRIPTION). On Linux the libc implementation never issues a syscall: it wraps [getrlimit](../process/getrlimit.md)/RLIMIT_NOFILE (getdtablesize.2, NOTES). A real kernel entry existed only on SPARC until 2.6.26 removed it.

## Synopsis

```c
#include <unistd.h>
int getdtablesize(void);
```

Feature-test macro history: `_DEFAULT_SOURCE` (glibc >= 2.19; older _BSD_SOURCE rules) (getdtablesize.2, SYNOPSIS).

## Arguments and behavior

No arguments. The value is exactly the RLIMIT_NOFILE soft limit -- changeable with setrlimit(2) and visible in /proc/[pid]/limits (getdtablesize.2, NOTES).

## Return value and errors

Returns the current open-files limit; on Linux it can return any error getrlimit(2) would (getdtablesize.2, RETURN VALUE/ERRORS, NOTES).

## Flags and constants

None.

## Security and notes

Portable code uses sysconf(_SC_OPEN_MAX) -- the man page's own guidance ("It is not specified in POSIX.1; portable applications should employ sysconf(_SC_OPEN_MAX) instead", getdtablesize.2, CONFORMING_TO). Interview angle: this is the 4.2BSD-era API (CONFORMING_TO: "first appeared in 4.2BSD") that Linux kept as a library shim while the kernel-side slot died on the one architecture that had it. Cross-reference: [getrlimit](../process/getrlimit.md), [dup](../descriptors-io/dup.md), [close](../descriptors-io/close.md), [ulimit](ulimit.md).

## References

- https://man7.org/linux/man-pages/man2/getdtablesize.2.html
- man-pages syscalls(2) ("SPARC (removed in 2.6.26)")
- worklog: wrapper symbol getdtablesize W @@GLIBC_2.2.5 verified with nm -D (2026-10-17)
