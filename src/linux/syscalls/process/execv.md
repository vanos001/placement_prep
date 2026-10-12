# execv(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | none on any architecture -- execv has no syscall entry anywhere (ledger numbers columns all `none`, generated from the four cached per-arch tables) |
| Since (kernel) | -- (the name is a libc-level interface, not a kernel entry point) |
| Man page | man2/execve.2 documents the kernel calls; execv(3) is documented in man3/exec.3 (not in the sparse cache's man2/); the ledger's syscalls(2) scan found no man2/execv.2 |
| glibc wrapper | execv@@GLIBC_2.2.5 (nm -D, glibc 2.41); declared in /usr/include/unistd.h line 584 as `extern int execv (const char *__path, char *const __argv[])` |
| Aliases covered | none (this page is the ledger's landing page for the name `execv`) |
| Ledger ID | SC-execv |

## Purpose

execv() is the classic exec* interface that replaces the calling process image with a new program, passing arguments as a NULL-terminated vector -- but on Linux it exists only as a libc function layered on the execve(2) syscall, which it invokes with the caller's environment (exec-family contract: execv(p, argv) == execve(p, argv, environ)). It is inventoried here because the ledger tracks every name in the per-arch syscall tables and in the syscalls(2) history, and execv appears there as a userspace-visible exec name with no numbers.

## Synopsis

```c
#include <unistd.h>
int execv(const char *path, char *const argv[]);
```

## Arguments and behavior

`path` must be an executable path (no PATH search -- that is execvp/execvpe's job at libc level); `argv` is a NULL-terminated array of argument strings, and by convention argv[0] is the program name. The kernel entry point actually invoked is execve(2) with `environ` as the third argument; every semantic -- permission checks, script/ELF handling, `ptrace`, rlimits preserved across exec -- is described in [execve.md](execve.md) and is identical for execv.

## Return value and errors

Returns only on failure, -1 with `errno` set exactly as execve (EACCES, EFAULT, EINVAL, EIO, EISDIR, ELOOP, ENAMETOOLONG, ENOENT, ENOEXEC, ENOMEM, ENOTDIR, ETXTBSY, E2BIG per execve.2 ERRORS). Success replaces the process, so nothing returns.

## Security and notes

The exec-family split (kernel execve/execveat vs. libc exec/execl/execle/execlp/execv/execvp/execvpe/fexecve) is a load-bearing example of the encyclopedia's naming rule: an application-visible interface, a kernel implementation, and the syscall-table name are three different things that must not be conflated (see interface-encyclopedia.md). execv is also a historical portability marker: 4.3BSD provided execv; POSIX.1-2001 kept execv() but XSI-shaded; POSIX.1-2008 removed it from the standard C set and moved it to XSI, while Linux libcs keep it for compatibility. musl implements it in src/process/execv.c (verified in musl-clone). Full kernel-side coverage: [execve.md](execve.md), [execveat.md](execveat.md).

## References

- /usr/include/unistd.h (execv declaration)
- nm -D /lib/x86_64-linux-gnu/libc.so.6 (execv@@GLIBC_2.2.5)
- musl: source-cache/musl-clone/musl/src/process/execv.c
- Kernel tables: source-cache/kernel/{syscall_64,syscall_32,syscall_generic,syscall_arm}.tbl (no execv row -- verified absence)
- Ledger row SC-execv
