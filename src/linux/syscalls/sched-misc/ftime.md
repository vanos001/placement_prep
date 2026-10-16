# ftime(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / 35 / -- / -- |
| Since (kernel) | -- (syscalls(2) lists ftime(2) among the never-implemented set) |
| Man page | man2/unimplemented.2 (man-pages 6.19 HTML set, fetched 2026-10-17) lists ftime(2) among the unimplemented system calls; man2/ftime.2 does not exist |
| glibc wrapper | ftime(3) exists as a deprecated library routine -- the syscalls(2) NOTES point says exactly that: "ftime(3), profil(3), and ulimit(3) are implemented as library functions" |
| Aliases covered | grouped topic page: [unimplemented](unimplemented.md) |
| Ledger ID | SC-ftime |

## Purpose

ftime(2) is the reserved i386 slot (number 35) for the SVr2-era ftime call -- a millisecond-granularity wall-clock read that classic UNIX kept and Linux never implemented. The slot exists for table stability; unimplemented.2's contract applies: any invocation returns -ENOSYS. The name survives in libc as the deprecated ftime(3) library function built on gettimeofday.

## Synopsis

```c
/* no kernel implementation; libc provides the deprecated ftime(3) */
#include <sys/timeb.h>
[[deprecated]] int ftime(struct timeb *tp);
```

## Arguments and behavior

Nothing at the kernel level: the slot always returns -ENOSYS (unimplemented.2, RETURN VALUE). The library routine fills `struct timeb { time_t time; unsigned short millitm; short timezone; short dstflag; }` from gettimeofday.

## Return value and errors

Kernel slot: always -1 with errno ENOSYS. Library ftime(3): 0 on success, -1 on error (deprecated; use clock_gettime(2)).

## Flags and constants

None.

## Security and notes

Interview angle: ftime is the clean example of "the name is in the syscall table AND the libc symbol table, but only the libc one does anything" -- the table slot is a placeholder, the function is userspace. The struct it fills (16-bit millitm) is also a y2.038-adjacent fossil. Cross-reference: [unimplemented](unimplemented.md), [time](../signals-time/time.md), [gettimeofday](../signals-time/gettimeofday.md).

## References

- https://man7.org/linux/man-pages/man2/unimplemented.2.html (ftime listed)
- Ledger row SC-ftime (i386 35)

