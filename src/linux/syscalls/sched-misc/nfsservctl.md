# nfsservctl(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 180 / 169 / 42 / 169 |
| Since (kernel) | 2.2; removed in 3.1 (nfsservctl.2 HISTORY) |
| Man page | man2/nfsservctl.2 (man-pages 6.19 HTML set, fetched 2026-10-17): "Since Linux 3.1, this system call no longer exists" |
| glibc wrapper | nfsservctl T @GLIBC_2.2.5 still exported by glibc 2.41 (nm -D) as a leftover compat symbol; man-pages HISTORY records the wrapper removed in glibc 2.28 |
| Aliases covered | none; replaced by the nfsd filesystem (nfsd(7)) |
| Ledger ID | SC-nfsservctl |

## Purpose

nfsservctl() was the syscall interface to the kernel NFS daemon: commands to start/stop the server, add and remove clients, and export or unexport filesystems, passed through `struct nfsctl_arg` (nfsservctl.2, DESCRIPTION, NFSCTL_* command list). Since 3.1 the same control surface lives in files under the nfsd filesystem -- writing to /proc/fs/nfsd/exports replaced the NFSCTL_EXPORT call, and so on (nfsservctl.2, DESCRIPTION).

## Synopsis

```c
#include <linux/nfsd/syscall.h>
long nfsservctl(int cmd, struct nfsctl_arg *argp, union nfsctl_res *resp);
```

## Arguments and behavior

`cmd` selected the operation: NFSCTL_SVC (0, server process), NFSCTL_ADDCLIENT (1), NFSCTL_DELCLIENT (2), NFSCTL_EXPORT (3), NFSCTL_UNEXPORT (4), plus the 2.4-and-earlier-only NFSCTL_UGIDUPDATE (5) and NFSCTL_GETFH (6) (nfsservctl.2, DESCRIPTION). `argp` carried a version-guarded (`ca_version`) union of per-command structs; `resp` received results (nfsservctl.2, DESCRIPTION).

## Return value and errors

0 on success; -1 with errno on error (nfsservctl.2, RETURN VALUE); the syscall itself is gone from kernels since 3.1.

## Flags and constants

NFSCTL_* command constants (<linux/nfsd/syscall.h>).

## Security and notes

The migration from syscall to pseudo-filesystem is the interview point: file-based control gives the same capability model as every other kernel knob (owner, permission bits, LSM hooks at open/write) instead of a bespoke entry point. The glibc symbol lingering after "removed in glibc 2.28" parallels [sysctl](sysctl.md) and [ustat](ustat.md) -- compat symbols outliving their man-page promises. Cross-reference: [sysctl](sysctl.md), [ustat](ustat.md), [quotactl](../fs-mounts-namespace/quotactl.md).

## References

- https://man7.org/linux/man-pages/man2/nfsservctl.2.html
- man-pages syscalls(2) ("Removed in 3.1")
- worklog: leftover glibc symbol nfsservctl @GLIBC_2.2.5 verified with nm -D (2026-10-17)
