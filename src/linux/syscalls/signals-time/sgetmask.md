# sgetmask(2) / ssetmask(2) (obsolete)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | sgetmask -- / 68 / -- / --; ssetmask -- / 69 / -- / -- |
| Since (kernel) | 1.0 (obsolete; man-pages: "These system calls are obsolete. Do not use them; use sigprocmask(2) instead", sgetmask.2 DESCRIPTION) |
| Man page | man2/sgetmask.2 (man-pages 6.19 HTML set, fetched 2026-10-17) covers both calls |
| glibc wrapper | none (no sgetmask/ssetmask symbols exported by glibc 2.41, nm -D); declared with [[deprecated]] for direct syscall(2) use |
| Aliases covered | ssetmask (i386 69, SC-ssetmask) |
| Ledger ID | SC-sgetmask |

## Purpose

sgetmask() and ssetmask() are the original pre-POSIX signal-mask calls: sgetmask() returns the calling process's signal mask and ssetmask() replaces it, returning the previous mask (sgetmask.2, DESCRIPTION). They are brief entries here because the modern interface is [rt_sigprocmask](rt_sigprocmask.md) ([sigprocmask](rt_sigprocmask.md) for the POSIX layer); these calls survive only for i386-legacy binaries.

## Synopsis

```c
#include <sys/syscall.h>
#include <unistd.h>
[[deprecated]] long syscall(SYS_sgetmask, void);
[[deprecated]] long syscall(SYS_ssetmask, long newmask);
```

## Arguments and behavior

The masks are plain bit masks over the 32 classic signal numbers, not sigset_t; sigmask(3) builds and inspects them (sgetmask.2, DESCRIPTION). ssetmask() sets the mask to `newmask` and returns the previous value; there is no way to atomically block-then-restore a set with the sigset granularity of sigprocmask(2). The calls operate on the process-wide legacy mask -- the same object sigprocmask(2) manages per thread on modern kernels.

## Return value and errors

sgetmask() returns the current mask; ssetmask() returns the previous mask. Neither documents error returns (sgetmask.2, RETURN VALUE).

## Flags and constants

None (plain bitmask; sigmask(3) helpers).

## Security and notes

No capability involved. Do not use in new code: the man page's one-line summary is "obsolete -- use sigprocmask(2)". Interview trivia value: these two entries (i386 68/69) predate sigaction(2) and are why signal-mask state was historically process-wide rather than per-thread; the rt_* 2.2 calls introduced the modern per-thread sigset_t model. Cross-reference: [rt_sigprocmask](rt_sigprocmask.md), [rt_sigpending](sigpending.md), [rt_sigaction](rt_sigaction.md).

## References

- https://man7.org/linux/man-pages/man2/sgetmask.2.html
- man-pages syscalls(2) version table
- worklog: no sgetmask/ssetmask symbols in glibc 2.41 (nm -D, 2026-10-17)
