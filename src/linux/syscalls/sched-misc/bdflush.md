# bdflush(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / 134 / -- / 134 |
| Since (kernel) | 1.2 (1.1.3 development series, man-pages HISTORY) |
| Man page | man2/bdflush.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | none in current glibc -- the header and prototype were removed in glibc 2.23 (bdflush.2, HISTORY); no bdflush symbol in glibc 2.41 (nm -D) |
| Aliases covered | none |
| Ledger ID | SC-bdflush |

## Purpose

bdflush() once turned the calling process into the buffer-dirty-flush daemon, tuned that daemon, or flushed "old" buffers -- the pre-journal userspace side of buffer cache writeback (bdflush.2, DESCRIPTION). The man page documents its decay bluntly: the functionality was progressively lost until the call did nothing, and Linux 5.15 removed it outright (bdflush.2, DESCRIPTION/HISTORY).

## Synopsis

```c
#include <sys/kdaemon.h>   /* header removed in glibc 2.23 */
int bdflush(int func, long data);
```

## Arguments and behavior

`func` selected the operation (daemonize, tune a parameter, flush), with `data` as its argument; the man page preserves the ABI quirk that for even `func` values `data` was actually a pointer (bdflush.2, HISTORY). For the exact per-func semantics the man page defers to fs/buffer.c in the kernel version of interest -- by the end, nothing was left to tune (bdflush.2, DESCRIPTION). The writeback role moved into the kernel: pdflush (2.6), then flush threads (bdi writeback), which need no userspace daemon at all.

## Return value and errors

-1 with errno on error; the documented error is ENOSYS ("this system call is unimplemented") (bdflush.2, RETURN VALUE/ERRORS).

## Flags and constants

None.

## Security and notes

The daemonization form is the historical interest: a userspace process entering kernel-flush duty was the design of its day (like the pre-2.6 kswapd model), and its death marks the transition to in-kernel writeback workers. Interview angle: bdflush -> pdflush -> per-bdi flush threads is the one-line history of Linux writeback. The i386/arm number 134 sits between the module-call block and the old select slots -- table archaeology worth mentioning when discussing syscall-number stability. Cross-reference: [syslog](syslog.md), [sync](../descriptors-io/sync.md), [reboot](reboot.md).

## References

- https://man7.org/linux/man-pages/man2/bdflush.2.html
- man-pages syscalls(2) ("Deprecated (does nothing)")
