# execveat(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 322 / 358 / 281 / 387 |
| Since (kernel) | 3.19 (execveat.2 VERSIONS); glibc wrapper since 2.34 (installed glibc exports execveat@@GLIBC_2.34) |
| Man page | man2/execveat.2 (cached roff, dated 2021-08-27); no aliases |
| glibc wrapper | execveat(3), symbol version GLIBC_2.34 (execveat.2 VERSIONS; verified via nm -D on glibc 2.41) |
| Aliases covered | none (fexecve(3) is a library function, not a syscall alias) |
| Ledger ID | SC-execveat |

## Purpose

execveat() executes a program identified by a directory file descriptor plus a pathname, or by a bare file descriptor with AT_EMPTY_PATH. It behaves exactly like execve(2) except for the dirfd-relative resolution and the flags argument, and it exists so fexecve(3) can work without /proc mounted (execveat.2, NOTES).

## Synopsis

```c
#include <linux/fcntl.h>   /* AT_* constants */
#include <unistd.h>
int execveat(int dirfd, const char *pathname,
             const char *const argv[], const char *const envp[], int flags);
```

## Arguments and behavior

If pathname is relative it is resolved against dirfd (AT_FDCWD means the caller's current working directory); if absolute, dirfd is ignored. If pathname is an empty string and AT_EMPTY_PATH is set, dirfd itself names the executable (it may have been opened with O_PATH). flags is a bit mask of AT_EMPTY_PATH and AT_SYMLINK_NOFOLLOW. Semantics, attribute preservation, suid rules, and errors otherwise match execve(2) (execveat.2, DESCRIPTION). When a script is executed, the interpreter receives argv[0] of the form /dev/fd/N (AT_EMPTY_PATH) or /dev/fd/N/P (dirfd + pathname). The natural idiom is to set close-on-exec on dirfd, but that triggers the ENOENT bug for script files (below).

## Return value and errors

Does not return on success; -1 with errno on failure. In addition to all execve(2) errors (execveat.2, ERRORS):

| Error | Meaning |
|---|---|
| EINVAL | Invalid flag in flags; or pathname relative but dirfd neither AT_FDCWD nor a valid fd |
| ELOOP | AT_SYMLINK_NOFOLLOW set and the target is a symbolic link |
| ENOENT | The program needs an interpreter (script) but dirfd was opened O_CLOEXEC, so the interpreter cannot access the file (execveat.2, BUGS) |
| ENOTDIR | pathname relative and dirfd refers to a non-directory |

## Flags and constants

| Flag | Value | Meaning (source: /usr/include/linux/fcntl.h) |
|---|---|---|
| AT_EMPTY_PATH | 0x1000 | empty pathname means "use dirfd itself" |
| AT_SYMLINK_NOFOLLOW | 0x100 | do not follow a final symbolic link (ELOOP) |
| AT_FDCWD | -100 | special dirfd: resolve relative to cwd |
| AT_SYMLINK_FOLLOW | 0x400 | exists in the same header for other *at calls, but is NOT an execveat flag; passing it fails with EINVAL (verified by previous agent, worklog 1-a: execveat accepts only AT_EMPTY_PATH/AT_SYMLINK_NOFOLLOW) |

## Security and notes

AT_EMPTY_PATH plus an O_PATH fd allows executing a file whose name is not otherwise reachable, subject to normal exec permission checks; an O_CLOEXEC fd leaks through script execution (ENOENT case), wasting a descriptor and potentially leading to fd exhaustion with recursive scripts (execveat.2, BUGS). Cross-reference: [execve](execve.md).

## References

- https://man7.org/linux/man-pages/man2/execveat.2.html
- fs/exec.c (source file named in worklog 1-a)
- /usr/include/linux/fcntl.h (AT_* values)
