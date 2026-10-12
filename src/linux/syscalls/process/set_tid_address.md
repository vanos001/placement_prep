# set_tid_address(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 218 / 258 / 96 / 256 |
| Since (kernel) | 2.6 (hub) - set_tid_address.2 VERSIONS says "present since Linux 2.5.48" with details valid since 2.5.49; both values recorded (worklog 1-a flags this table-vs-man-page difference) |
| Man page | man2/set_tid_address.2 (cached roff, dated 2021-06-20); no aliases |
| glibc wrapper | none: glibc provides no wrapper (set_tid_address.2 note); no set_tid_address symbol in installed glibc 2.41 (nm -D); glibc invokes it internally when starting threads |
| Aliases covered | none |
| Ledger ID | SC-set_tid_address |

## Purpose

set_tid_address() registers the address at which the calling thread's TID should be cleared (and a futex wake issued) when the thread exits. It is the mechanism behind CLONE_CHILD_CLEARTID: threading libraries rely on the exit-time "zero the word and wake one waiter" action for thread joining (set_tid_address.2; clone.2 CLONE_CHILD_CLEARTID).

## Synopsis

```c
#include <sys/syscall.h>
pid_t syscall(SYS_set_tid_address, int *tidptr);
```

## Arguments and behavior

tidptr is the new clear_child_tid value for the calling thread. Per set_tid_address.2, each thread carries two kernel-maintained addresses: set_child_tid (set from clone(2) CLONE_CHILD_SETTID; the new thread's first action is to store its TID there) and clear_child_tid (set from CLONE_CHILD_CLEARTID or by this syscall). When a thread with a non-NULL clear_child_tid terminates while sharing memory with other threads, the kernel writes 0 at that address and performs futex(clear_child_tid, FUTEX_WAKE, 1, NULL, NULL, 0) - waking exactly one waiter on that word; errors from the wake are ignored. The address may be changed later by another set_tid_address call.

## Return value and errors

Always returns the caller's thread ID (the TID, i.e. what gettid(2) returns). Always succeeds; no errno is defined (set_tid_address.2, RETURN VALUE/ERRORS).

## Flags and constants

None.

## Security and notes

The call is per-thread and cannot target another thread. The exit-time store+wake happens only when the thread shares memory with other threads; a lone process exit reaps through the wait(2) path instead (set_tid_address.2, DESCRIPTION). Because the wake is a plain FUTEX_WAKE with count 1, userspace join logic must re-check the word (0 means the thread is gone). Namespace note: the returned TID is the caller's TID in its PID namespace context (see getpid.2 for the TGID/TID split). Cross-reference: [clone](clone.md), [getpid](getpid.md), [futex](futex.md).

## References

- https://man7.org/linux/man-pages/man2/set_tid_address.2.html
- kernel/fork.c (exit-time clear_child_tid handling; source file named in worklog 1-a)
- /usr/include/linux/sched.h (CLONE_CHILD_SETTID / CLONE_CHILD_CLEARTID)
