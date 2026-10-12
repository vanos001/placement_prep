# acct(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 163 / 51 / 89 / 51 |
| Since (kernel) | 1.0 |
| Man page | man2/acct.2 (cached roff, dated 2021-03-22) |
| glibc wrapper | acct(3) @@GLIBC_2.2.5 (nm -D, glibc 2.41); gates: _DEFAULT_SOURCE since glibc 2.21, _BSD_SOURCE (or _XOPEN_SOURCE < 500) before (acct.2, SYNOPSIS) |
| Aliases covered | none |
| Ledger ID | SC-acct |

## Purpose

acct() switches BSD process accounting on or off: with a file name, the kernel appends an accounting record as each process terminates; NULL turns it off. Brief entry.

## Synopsis

```c
#include <unistd.h>
int acct(const char *filename);
```

## Arguments and behavior

A filename of an existing regular file enables accounting; records are appended as each process terminates (acct.2, DESCRIPTION). ENOSYS when the kernel was built without CONFIG_BSD_PROCESS_ACCT. The record layout is acct(5)'s subject, per acct.2 NOTES. No accounting is produced for processes running at a system crash, and never-terminating processes are never accounted (acct.2, NOTES).

## Return value and errors

0 on success, -1 with errno (acct.2, RETURN VALUE). Errors: EACCES, EFAULT, EIO, EISDIR, ELOOP, ENAMETOOLONG, ENFILE, ENOENT, ENOMEM, ENOSYS, ENOTDIR, EPERM, EROFS, EUSERS -- EPERM being insufficient privilege, on Linux the CAP_SYS_PACCT capability (acct.2, ERRORS).

## Flags and constants

CAP_SYS_PACCT is capability 20 (/usr/include/linux/capability.h).

## Security and notes

The caller needs CAP_SYS_PACCT plus write access to the chosen accounting file; acct() is SVr4/4.3BSD origin and not POSIX (acct.2, CONFORMING TO). Cross-reference: [wait4](wait4.md) for the termination observation most programs use instead.

## References

- https://man7.org/linux/man-pages/man2/acct.2.html
- /usr/include/linux/capability.h (CAP_SYS_PACCT value 20)
- acct(5) (record format pointer per acct.2 NOTES; not in the sparse cache)
