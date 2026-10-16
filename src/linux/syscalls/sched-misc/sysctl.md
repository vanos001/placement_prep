# _sysctl(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 156 / 149 / -- / 149 |
| Since (kernel) | 2.0 (4.4BSD lineage; man-pages HISTORY: "4.4BSD, Linux 1.3.57") |
| Man page | man2/sysctl.2 (man-pages 6.19 HTML set, fetched 2026-10-17): "This system call no longer exists on current kernels!" |
| glibc wrapper | sysctl(3) T @GLIBC_2.2.5 still exported as a leftover compat symbol (nm -D, glibc 2.41), while sysctl.2 HISTORY records wrapper support removed in glibc 2.32; the man page's guidance is syscall(2) on kernels that still had it |
| Aliases covered | none; the /proc/sys interface replaced it |
| Ledger ID | SC-_sysctl |

## Purpose

_sysctl() read and wrote kernel parameters through a structured name-vector addressing the same tree /proc/sys exposes: `struct __sysctl_args { int *name; int nlen; void *oldval; size_t *oldlenp; void *newval; size_t newlen; }`, where `name` is an integer path such as `{CTL_KERN, KERN_OSTYPE}` (sysctl.2, DESCRIPTION). It was the programmatic ancestor of the /proc/sys sysctl(8) interface.

## Synopsis

```c
#include <unistd.h>
#include <linux/sysctl.h>
[[deprecated]] int _sysctl(struct __sysctl_args *args);
```

## Arguments and behavior

One argument: the args structure above. A pure read sets `oldval`/`oldlenp` and leaves `newval` NULL; a write sets `newval`/`newlen`; the kernel overwrites `*oldlenp` with the actual value size (sysctl.2, DESCRIPTION). Warnings were logged on every use since 2.6.24, the call was gated behind CONFIG_SYSCTL_SYSCALL on kernels that still carried it, and Linux 5.5 removed it entirely (sysctl.2, NOTES/HISTORY).

## Return value and errors

0 on success; -1 with errno (sysctl.2, RETURN VALUE). Errors: EACCES/EPERM (search/read/write permission on the tree node), EFAULT (`oldval` requested but `*oldlenp` allowed zero room), ENOTDIR (name vector not found) (sysctl.2, ERRORS).

## Flags and constants

CTL_KERN, KERN_OSTYPE and the rest of the naming constants lived in <linux/sysctl.h> (sysctl.2, EXAMPLES).

## Security and notes

The security story is why it died: the integer-vector addressing bypassed the per-file permission model /proc/sys has, and the name space varied between kernel versions ("The object names vary between kernel versions, making this system call worthless for applications", sysctl.2, BUGS). Anything you would have done with _sysctl() goes through /proc/sys today, with the path components as strings. Interview angle: _sysctl is the canonical example of an ABI retired because its permission model and its stability model were both wrong. Cross-reference: [syslog](syslog.md), [sysinfo](sysinfo.md), [getrandom](getrandom.md).

## References

- https://man7.org/linux/man-pages/man2/sysctl.2.html
- man-pages syscalls(2) version table (2.0)
- worklog: leftover glibc symbol sysctl @GLIBC_2.2.5 verified with nm -D against glibc 2.41 (2026-10-17)
