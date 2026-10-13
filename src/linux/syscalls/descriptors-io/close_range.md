# close_range(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 436 / 436 / 436 / 436 |
| Since (kernel) | 5.9 (glibc 2.34) |
| Man page | man2/close_range.2 |
| glibc wrapper | close_range() declared via <linux/close_range.h>; host glibc 2.41 exports close_range@@GLIBC_2.34 (nm -D); before glibc 2.34 use syscall(2) |
| Aliases covered | none |
| Ledger ID | SC-close_range |

## Purpose

close_range() closes every open file descriptor numbered first through last, inclusive, in a single system call. It exists to replace the two traditional ways of sweeping descriptors before exec: iterating /proc/self/fd/ and closing each entry (needs /proc mounted, and is several syscalls per descriptor), and blindly looping close() over the whole possible range (each invalid descriptor is a wasted syscall). Errors closing an individual descriptor are ignored -- the sweep does not stop for them. The flags argument extends this in two directions: CLOSE_RANGE_UNSHARE detaches the caller from a shared descriptor table first, making the operation race-free against threads that share the table, and CLOSE_RANGE_CLOEXEC (5.11) marks descriptors close-on-exec instead of closing them, so a seccomp(2) profile installed afterwards can still police their fate across exec.

## Synopsis

```c
#include <linux/close_range.h>
int close_range(unsigned int first, unsigned int last, unsigned int flags);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| first | Lowest descriptor number to process. |
| last | Highest descriptor number to process; ~0U means "to the top of the range" and is the usual exec-preparation idiom. first > last is EINVAL. |
| flags | 0, or OR of CLOSE_RANGE_UNSHARE and CLOSE_RANGE_CLOEXEC (table below); anything else is EINVAL. |

CLOSE_RANGE_* values from /usr/include/linux/close_range.h: CLOSE_RANGE_UNSHARE (1U << 1), CLOSE_RANGE_CLOEXEC (1U << 2).

## Return value and errors

0 on success; on error -1 and errno: EINVAL (invalid flags, or first > last), EMFILE (with CLOSE_RANGE_UNSHARE: rebuilding the descriptor table would exceed /proc/sys/fs/nr_open -- possible when that limit was lowered before the call), ENOMEM (with CLOSE_RANGE_UNSHARE: kernel memory exhausted constructing the new table).

## Flags and constants

| Flag | Value | Since | Meaning |
|---|---|---|---|
| CLOSE_RANGE_UNSHARE | (1U << 1) | 5.9 | Unshare the fd table from other processes before closing the range, avoiding races with threads sharing it. Conceptually unshare(CLONE_FILES) + close_range(first, last, 0), but cheaper: when the range extends past the highest allocated descriptor (common with last = ~0U), the kernel copies only up to first and no per-descriptor close is needed. The cached man page does not date this flag; it is present in the UAPI header at kernel tag v5.9 (tag-probed: include/uapi/linux/close_range.h exists at v5.9, absent at v5.8), consistent with status/1-c dating it 5.9. |
| CLOSE_RANGE_CLOEXEC | (1U << 2) | 5.11 | Set FD_CLOEXEC on the range instead of closing; descriptors survive until a successful execve. |

## Security and notes

- Exec preparation: close_range(3, ~0U, CLOSE_RANGE_UNSHARE) before execve() is the man page's own idiom for "keep 0, 1, 2, close the rest".
- CLOSE_RANGE_CLOEXEC ordering trick: closing fds before installing a seccomp profile starves the profile setup; closing after lets the profile block the close_range() fallbacks. Marking CLOEXEC early solves both: the seccomp filter still controls close_range(), and the descriptors die at exec (man2/close_range.2, "Closing files on exec").
- Per-descriptor close errors (EBADF on holes in the range) are silently ignored by design; this is a sweep, not a checked teardown.
- UNSHARE semantics matter for multithreaded callers: without it, closing a range races with threads that share the fd table; with it, the caller gets a private table for the operation.
- close_range() is nonstandard but also present on FreeBSD (man2/close_range.2 CONFORMING TO); individual closes remain close(2), whose EINTR-in-doubt semantics the [domain hub](overview.md) close row covers.

## References

- man2/close_range.2 in the cached man-pages tree (dated 2021-08-27).
- Constants: /usr/include/linux/close_range.h; v5.9 vs v5.8 UAPI header tag probe (this session) for CLOSE_RANGE_UNSHARE's kernel window.
- [Syscalls ledger](../ledger.md) row SC-close_range; status/1-c row (5.9, UNSHARE + CLOEXEC 5.11, glibc 2.34); siblings [dup](dup.md), [open](open.md); [domain hub](overview.md).
