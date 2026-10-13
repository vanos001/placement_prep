# get_robust_list(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 274 / 312 / 100 / 339 |
| Since (kernel) | 2.6.17 |
| Man page | man2/get_robust_list.2 (cached roff, dated 2021-03-22); man2/set_robust_list.2 is a one-line .so alias to get_robust_list.2 |
| glibc wrapper | none: "glibc provides no wrappers for these system calls" (get_robust_list.2); nm -D on glibc 2.41 confirms no get_robust_list/set_robust_list symbols |
| Aliases covered | set_robust_list (273 / 311 / 99 / 338, SC-set_robust_list) |
| Ledger ID | SC-get_robust_list |

## Purpose

get_robust_list() and set_robust_list() read and register a thread's robust futex list head -- the user-space list the kernel walks when a thread dies holding a futex. Brief entry.

## Synopsis

```c
#include <linux/futex.h>
#include <sys/syscall.h>
#include <unistd.h>
long syscall(SYS_get_robust_list, int pid,
             struct robust_list_head **head_ptr, size_t *len_ptr);
long syscall(SYS_set_robust_list, struct robust_list_head *head, size_t len);
```

## Arguments and behavior

The list is managed in user space; the kernel records only the head (get_robust_list.2, DESCRIPTION). set_robust_list(head, len) registers the calling thread's head; len must be sizeof(struct robust_list_head). get_robust_list(pid, head_ptr, len_ptr) stores the head of thread pid's list (0 = caller) and its size at *len_ptr. If a thread terminates -- or, since Linux 2.6.28, execve's -- without unlocking a futex, the kernel sets FUTEX_OWNER_DIED (0x40000000, /usr/include/linux/futex.h) in the futex word and performs a futex(2) FUTEX_WAKE on a waiter. Both calls were added in Linux 2.6.17 (VERSIONS).

## Return value and errors

Zero on success (get_robust_list.2, RETURN VALUE). set_robust_list(): EINVAL, wrong len. get_robust_list(): EFAULT, EPERM (no permission and no CAP_SYS_PTRACE), ESRCH (ERRORS).

## Flags and constants

FUTEX_OWNER_DIED 0x40000000 (/usr/include/linux/futex.h); CAP_SYS_PTRACE is 19 (/usr/include/linux/capability.h).

## Security and notes

get_robust_list() is governed by a ptrace access mode PTRACE_MODE_READ_REALCREDS check on the target (get_robust_list.2, DESCRIPTION). A thread may have only one robust list, so applications should use glibc's robust mutexes (pthread_mutexattr_setrobust(3)) -- the page says these calls are "not needed by normal applications" (NOTES). Cross-reference: [futex](futex.md) documents FUTEX_WAKE; the IDs involved are kernel TIDs ([clone](clone.md)).

## References

- https://man7.org/linux/man-pages/man2/get_robust_list.2.html
- /usr/include/linux/futex.h (struct robust_list_head, FUTEX_OWNER_DIED)
- /usr/include/linux/capability.h (CAP_SYS_PTRACE 19)
- worklog Task 1-a (researched brief entries SC-get_robust_list/SC-set_robust_list)
