# process_mrelease(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 448 / 448 / 448 / 448 |
| Since (kernel) | -- in the syscalls(2) version table and the ledger; merged by commit 884a7e5964 ("mm: introduce process_mrelease system call", 2021-09-02), i.e. Linux 5.15 |
| Man page | none on man7.org (no man2/process_mrelease.2 in the 6.19 HTML set fetched 2026-10-17); documented from mm/oom_kill.c -- source-limited on prose |
| glibc wrapper | no dedicated wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none |
| Ledger ID | SC-process_mrelease |

## Purpose

process_mrelease() asks the kernel to release the memory of a process that has already been selected to die, without waiting for the OOM reaper or the exiting thread to get there on its own. The caller holds a pidfd ([pidfd_open](pidfd_open.md)) on the target and the kernel reaps the target's address space the way the OOM reaper would (mm/oom_kill.c, SYSCALL_DEFINE2(process_mrelease)). It exists so that userspace OOM killers (systemd-oomd, oomd, container runtimes) can turn "kill" into "kill and reclaim immediately" instead of racing the victim's exit path.

## Synopsis

```c
/* no glibc declaration; called directly */
long syscall(SYS_process_mrelease, int pidfd, unsigned int flags);
```

## Arguments and behavior

`pidfd` is a file descriptor referring to the target process (pidfd conventions; PIDFD_SIGNAL applies). `flags` must be 0; any other value fails with EINVAL (mm/oom_kill.c, kernel constant check `if (flags) return -EINVAL;`). The kernel looks the task up from the pidfd, locks a thread that still has an `mm_struct` reference during group exit, and decides: if `task_will_free_mem(p)` is true the memory is reaped immediately; otherwise the call fails with EINVAL unless the work was already done (MMF_OOM_SKIP set on the mm) (mm/oom_kill.c, body). Reaping runs under `mmap_read_lock_killable()`, so a blocked caller can be interrupted with EINTR, and the MMF_OOM_SKIP check is repeated under the read lock to close the race with exit_mmap (commit 337546e83f, "prevent a race between process_mrelease and exit_mmap").

## Return value and errors

0 on success (memory of the dying process reclaimed or release work done); a negated error on the raw syscall path (no wrapper to translate it): EINVAL (flags nonzero, or the task is not going to die and the reaper has not run), ESRCH (the task no longer has an mm -- already exited), EINTR (mmap read lock acquisition killed), plus pidfd lookup errors from pidfd_get_task (EBADF for a bad descriptor) (mm/oom_kill.c, body).

## Flags and constants

None (flags must be 0).

## Security and notes

Permission model: the caller needs to signal the target the way [pidfd_send_signal](pidfd_send_signal.md) does (the pidfd was obtained with the appropriate access; kernel checks ptrace_may_access-style access on the pidfd lookup). The design goal from the merge commit 884a7e5964: userspace OOM killing should not leave the victim's memory pinned for long; on Android this cut low-memory-killer reclaim latency substantially. The companion semantic detail worth remembering: process_mrelease() never kills -- the target must already be dying (SIGKILL delivered via [pidfd_send_signal](pidfd_send_signal.md) or the OOM killer); otherwise EINVAL. This page is source-limited: the behavior above is read from mm/oom_kill.c (master, fall 2026) because no man page was reachable; a future man2/process_mrelease.2 should be reconciled against it. Cross-reference: [pidfd_open](pidfd_open.md), [pidfd_send_signal](pidfd_send_signal.md), [exit_group](_exit.md), [process_madvise](process_madvise.md).

## References

- Kernel source: mm/oom_kill.c (SYSCALL_DEFINE2(process_mrelease), torvalds/linux master, fetched 2026-10-17)
- Merge commit: 884a7e5964 "mm: introduce process_mrelease system call" (2021-09-02, 5.15); race fix 337546e83f (2021-10-28)
- https://man7.org/linux/man-pages/man2/pidfd_open.2.html (pidfd conventions)
- worklog: no glibc wrapper symbol (nm -D, glibc 2.41)
