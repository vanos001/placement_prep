# execve(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 59 / 11 / 221 / 11 |
| Since (kernel) | 1.0 |
| Man page | man2/execve.2 (cached roff, dated 2021-08-27); no aliases |
| glibc wrapper | execve(3) direct wrapper; part of the exec(3) family (execl, execvp, ...) built on it |
| Aliases covered | none |
| Ledger ID | SC-execve |

## Purpose

execve() replaces the current program image of the calling process with a new program: text, data, bss, heap, and stack are rebuilt from the executable, while the process (and its PID) survives. It is the standard way to run a program after fork(2)/clone(2); portability helpers such as posix_spawn(3) and the exec(3) wrappers sit on top.

## Synopsis

```c
#include <unistd.h>
int execve(const char *pathname, char *const argv[], char *const envp[]);
```

## Arguments and behavior

pathname must be a binary executable or a script whose first line is `#!interpreter [optional-arg]`; the interpreter is invoked as `interpreter [optional-arg] pathname arg...` using argv[1..] of the caller. argv and envp are NULL-terminated pointer arrays; the new program sees them via main(argc, argv, envp) (envp via environ(7) per POSIX). Linux accepts NULL for argv/envp (same as a single NULL pointer), but this is nonstandard and nonportable (execve.2, NOTES). On success the call never returns. All threads other than the caller are destroyed; caught-signal dispositions reset to default; alternate signal stacks, memory mappings, POSIX timers/semaphores/message queues, memory locks, directory streams, and atexit/on_exit handlers are not preserved; the fd table survives except FD_CLOEXEC descriptors; CLONE_FILES sharing is unshared; the process name is reset to the new executable's name; the termination signal resets to SIGCHLD (execve.2, Effect on process attributes). Since 2.6.28 an interpreter may itself be a script, recursively up to four levels.

Set-user-ID/set-group-ID transformation of the effective IDs is skipped when the no_new_privs attribute is set (prctl(2)), the filesystem is mounted nosuid, or the process is being ptraced; file capabilities are likewise ignored. Real UID/GID and supplementary groups are unchanged.

## Return value and errors

Does not return on success. On failure returns -1 with errno; main errors (execve.2): E2BIG (argv+envp too large), EACCES (search/execute permission, not a regular file, noexec mount), EAGAIN (since 3.1: above RLIMIT_NPROC after a set*uid change), EFAULT, EINVAL (multiple PT_INTERP), ELOOP (symlink or script-recursion limit; ENOEXEC before 3.8), EMFILE, ENAMETOOLONG, ENFILE, ENOENT, ENOEXEC (unrecognized or wrong-architecture format), ENOMEM, ENOTDIR, EPERM (nosuid/suid while traced, capability-dumb binaries), ETXTBSY (file open for writing). In rare point-of-no-return failures the kernel kills the process with SIGSEGV (SIGKILL until 3.17).

Argument/environment limits (execve.2): before 2.6.23 the limit was 32 pages (MAX_ARG_PAGES, 128 kB at 4 kB pages); since 2.6.23 the limit derives from RLIMIT_STACK (1/4 of the stack, capped at 3/4 of _STK_LIM = 8 MiB), with a 32-page floor since 2.6.25; per-string limit 32 pages (MAX_ARG_STRLEN); at most 0x7FFFFFFF strings. The `#!` line is limited to 127 characters before 5.1 and 255 since 5.1.

## Flags and constants

None on this syscall. FD_CLOEXEC (fcntl(2)) controls descriptor survival across the exec.

## Security and notes

If the process is being ptraced, SIGTRAP is delivered after a successful execve unless PTRACE_O_TRACEEXEC is set (execve.2). Set-user-ID processes cannot be ptraced. Files in /proc/[pid] may change ownership to root:root when the dumpable attribute is reset by a privileged exec. Cross-reference: [execveat](execveat.md), [fork](fork.md), [prctl](prctl.md), [_exit](_exit.md).

## References

- https://man7.org/linux/man-pages/man2/execve.2.html
- fs/exec.c (source file named in worklog 1-a)
- /usr/include/linux/fcntl.h (FD_CLOEXEC context)
