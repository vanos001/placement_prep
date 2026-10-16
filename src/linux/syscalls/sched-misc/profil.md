# profil(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / 98 / -- / -- |
| Since (kernel) | -- (syscalls(2) lists profil(2) among the never-implemented set) |
| Man page | man2/unimplemented.2 lists profil(2) among the unimplemented system calls (fetched 2026-10-17); the library routine is man3/profil.3 (fetched: "profil - execution time profile") |
| glibc wrapper | profil(3) W @@GLIBC_2.2.5 (nm -D, glibc 2.41) -- a pure library function on Linux |
| Aliases covered | grouped topic page: [unimplemented](unimplemented.md) |
| Ledger ID | SC-profil |

## Purpose

profil(2) is the reserved i386 slot (number 98) for the classic UNIX sampling-profiler hook; Linux never implemented it as a syscall. The actual profiling surface is the profil(3) library routine (built on setitimer(2) ITIMER_PROF and a SIGPROF handler), which is exactly the split syscalls(2) documents: "ftime(3), profil(3), and ulimit(3) are implemented as library functions".

## Synopsis

```c
/* library routine (man3/profil.3) */
#include <sys/profil.h>
int profil(unsigned short *samples, size_t size,
           size_t offset, unsigned int scale);
/* the SYS_profil slot always returns -ENOSYS */
```

## Arguments and behavior

Kernel slot: no behavior, always -ENOSYS (unimplemented.2, RETURN VALUE). The library routine registers a sample buffer over [offset, offset+size) in the text segment and arms the ITIMER_PROF sampling tick at a rate derived from `scale` (man3/profil.3, DESCRIPTION).

## Return value and errors

Kernel slot: always -1 with ENOSYS. Library routine: 0 on success, -1 on error.

## Flags and constants

None (the scale encoding belongs to the library routine's contract).

## Security and notes

Interview angle: the SVr3 profiling lineage -- profil(3) -> gprof's -pg instrumentation -> perf(1) -- is a good architecture-evolution question; the dead i386 slot is the reminder that the kernel never had a profil(2). Cross-reference: [unimplemented](unimplemented.md), [ftime](ftime.md), [ulimit](ulimit.md), [setitimer](../signals-time/setitimer.md).

## References

- https://man7.org/linux/man-pages/man2/unimplemented.2.html (profil listed)
- https://man7.org/linux/man-pages/man3/profil.3.html
- worklog: wrapper symbol profil W @@GLIBC_2.2.5 verified with nm -D (2026-10-17)

