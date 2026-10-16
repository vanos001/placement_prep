# spu_create(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (PowerPC Cell table only) |
| Since (kernel) | 2.6.16 (syscalls(2): Cell/B.E. era) |
| Man page | man2/spu_create.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | none -- "glibc provides no wrapper for spu_create(), necessitating the use of syscall(2)" (spu_create.2, SYNOPSIS) |
| Aliases covered | none; companion execution call is [spu_run](spu_run.md) |
| Ledger ID | SC-spu_create |

## Purpose

spu_create() created a logical context for one of the Cell Broadband Engine's Synergistic Processor Units: it created a new context directory at `path` under the spufs filesystem and returned a file descriptor bound to that context (spu_create.2, DESCRIPTION). The returned fd's only legal uses were spu_run(2), the *at() family as dirfd, or close (spu_create.2, DESCRIPTION) -- an early example of the "syscall returns an fd, everything else goes through file operations" design.

## Synopsis

```c
#include <sys/spu.h>   /* SPU_* constants */
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_spu_create, const char *path, unsigned int flags,
            mode_t mode, int neighbor_fd);
```

## Arguments and behavior

`path` had to name a nonexistent directory inside the spufs mount point; on success the kernel creates it and populates it with the spufs(7) file set (spu_create.2, DESCRIPTION). `flags` included SPU_CREATE_EVENTS_ENABLED (event reporting through spu_run's event out-param) and SPU_CREATE_GANG (attach to a gang for group scheduling, via `neighbor_fd`); an isolated (protected) context required SPU_CREATE_ISOLATED and hardware support -- ENODEV when unsupported, EPERM when the isolation flag was misused (spu_create.2, DESCRIPTION/ERRORS). Contexts were destroyed when the last fd closed (spu_create.2, DESCRIPTION).

## Return value and errors

New file descriptor on success; -1 with errno (spu_create.2, RETURN VALUE). Errors include: EACCES (no write access to the spufs mount), EEXIST (path taken), EFAULT, EINVAL (path not in spufs; bad flags), EMFILE/ENFILE (fd limits), ENOSPC (SPU resources or per-user context limit), ENOSYS (no SPUs or spufs module unloaded), EPERM (isolation misuse), plus the usual path-resolution set (spu_create.2, ERRORS).

## Flags and constants

SPU_CREATE_EVENTS_ENABLED, SPU_CREATE_GANG, SPU_CREATE_ISOLATED (<sys/spu.h>).

## Security and notes

Access control was the spufs mount's permission bits -- root-configurable, typically delegated to a Cell compute group. The man page's NOTES point out the call "is meant to be used from libraries that implement a more abstract interface to SPUs, not to be used from regular applications" (spu_create.2, NOTES). The Cell's decline retired the whole pair; the design DNA (fd-scoped accelerator contexts) lives on in GPU/accelerator frameworks. Cross-reference: [spu_run](spu_run.md), [perf_event_open](perf_event_open.md).

## References

- https://man7.org/linux/man-pages/man2/spu_create.2.html
- man-pages syscalls(2) (2.6.16)
