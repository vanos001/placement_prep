# kcmp(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 312 / 349 / 272 / 378 (cached kernel tables; hub agrees) |
| Since (kernel) | 3.5 (man VERSIONS; hub agrees). Before Linux 5.12 the call exists only with `CONFIG_CHECKPOINT_RESTORE`; since 5.12 it is unconditional (man NOTES) |
| Man page | man2/kcmp.2 (local cache, dated 2021-03-22) |
| glibc wrapper | None; call via `syscall(SYS_kcmp, ...)` (man page; nm -D on glibc 2.41 shows no kcmp symbol) |
| Aliases covered | none |
| Ledger ID | SC-kcmp |

## Purpose

`kcmp()` compares two processes identified by `pid1` and `pid2` to determine
whether they share a kernel resource: file descriptors, address space, signal
handler table, and so on. It was created for the checkpoint/restore (CRIU) use
case, where the alternative of exposing the same facts through procfs was
rejected for security reasons (man NOTES).

## Synopsis

    #include <linux/kcmp.h>
    int syscall(SYS_kcmp, pid_t pid1, pid_t pid2, int type,
                unsigned long idx1, unsigned long idx2);

## Arguments and behavior

`type` selects the resource (values from the `enum kcmp_type` in installed
linux/kcmp.h):

| Type | Value | Compares |
|---|---|---|
| `KCMP_FILE` | 0 | whether fd `idx1` of `pid1` and fd `idx2` of `pid2` refer to the same open file description |
| `KCMP_VM` | 1 | same address space (CLONE_VM) |
| `KCMP_FILES` | 2 | same set of open file descriptors (CLONE_FILES); `idx1`/`idx2` ignored |
| `KCMP_FS` | 3 | same fs info: umask, cwd, root (CLONE_FS); idx ignored |
| `KCMP_SIGHAND` | 4 | same signal disposition table (CLONE_SIGHAND); idx ignored |
| `KCMP_IO` | 5 | same I/O context (CLONE_IO); idx ignored |
| `KCMP_SYSVSEM` | 6 | same System V semaphore undo list (CLONE_SYSVSEM); idx ignored |
| `KCMP_EPOLL_TFD` | 7 (since 4.13) | whether fd `idx1` of `pid1` is registered in the epoll instance of `pid2` described by `idx2`, a pointer to `struct kcmp_epoll_slot { __u32 efd; __u32 tfd; __u32 toff; }` (installed header). Discrepancy: the cached man page prints toff as __u64; the installed uapi header says __u32 |
| `KCMP_TYPES` | 8 | sentinel count, not a type |

## Return value and errors

The result is an arithmetic comparison of the kernel pointers of the two
resources, designed to be usable for sorting: 0 = same resource (shared), 1 =
v1 < v2, 2 = v1 > v2, 3 = not equal but ordering unavailable. On error -1 with
`errno`: `EBADF` (KCMP_FILE with a non-open descriptor), `EFAULT` (epoll slot
outside the address space), `EINVAL` (invalid type), `ENOENT` (target file not
in the epoll instance), `EPERM`, `ESRCH`.

## Flags and constants

None.

## Security and notes

Permission is governed by ptrace access mode `PTRACE_MODE_READ_REALCREDS` checks
against both processes (man page). `CAP_SYS_PTRACE` is required to inspect
processes you do not own; other ptrace restrictions apply, e.g. with
`CONFIG_SECURITY_YAMA` and `/proc/sys/kernel/yama/ptrace_scope` = 2 kcmp() is
limited to child processes. The comparison is not protected against false
positives while the processes are running -- send `SIGSTOP` first (man page).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/kcmp.2`
- Header: installed `/usr/include/linux/kcmp.h` (enum values, epoll slot struct)
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (312), `syscall_32.tbl`
  (349), `syscall_generic.tbl` (272), `syscall_arm.tbl` (378)
- Online: https://man7.org/linux/man-pages/man2/kcmp.2.html
