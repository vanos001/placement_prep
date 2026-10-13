# `mknod` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [mknod(2)](../../../syscalls/fs-mounts-namespace/mknod.md); FIFO-only
> portable subset: [mkfifo-mknod-wrappers.md](mkfifo-mknod-wrappers.md).

| Field | Value |
|---|---|
| Header | `sys/stat.h` |
| Standards | SVr4, 4.4BSD; POSIX.1-2001 (portable use: FIFO only), POSIX.1-2008 |
| Exported | `mknod@@GLIBC_2.33`, `mknodat@@GLIBC_2.33`; internal `__xmknod@@GLIBC_2.2.5`, `__xmknodat@@GLIBC_2.4` also visible (nm, host glibc 2.41) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual safety annotations; `mknod.2` carries no ATTRIBUTES table in man-pages 5.14) |
| Ledger ID | GLIBC-mknod |

## Declaration and gates

```c
#include <sys/stat.h>

int mknod(const char *pathname, mode_t mode, dev_t dev);
int mknodat(int dirfd, const char *pathname, mode_t mode, dev_t dev);
```

`mknod` sits in `#if defined __USE_MISC || defined __USE_XOPEN_EXTENDED`
(`/usr/include/x86_64-linux-gnu/sys/stat.h` lines 403-407, prototype at
404), matching `mknod.2`'s `_DEFAULT_SOURCE`/`_XOPEN_SOURCE >= 500`
gate; `mknodat` (line 411) adds `__USE_ATFILE`. The wrapper reaches the
kernel through the internal `__xmknod` versioned shim (nm; manual
safety comment "we go through xmknod").

## Semantics

Creates a filesystem node named `pathname`: `mode` combines one file
type bit -- `S_IFREG` (zero type means regular, created empty),
`S_IFCHR`, `S_IFBLK`, `S_IFIFO`, `S_IFSOCK` -- with permission bits,
which the umask then masks; `dev` is the `makedev(3)`-built device
number, honored only for `S_IFCHR`/`S_IFBLK` (`mknod.2`, manual
*Making Special Files*). `EEXIST` fires if the name exists, including
as a symlink. Group ownership follows the parent directory's
set-group-ID bit or BSD group semantics. `mknodat` (kernel 2.6.16,
glibc 2.4) resolves relative paths against `dirfd`.

## Gotchas and portability

- POSIX.1-2001's own words: the only portable use is creating a FIFO;
  use `mkfifo(3)` even for that (`mknod.2` NOTES, manual).
- Directories cannot be made with `mknod` on Linux -- `mkdir(2)` owns
  that (`mknod.2` NOTES).
- Privilege: creating device nodes needs `CAP_MKNOD`; since Linux 2.4
  unprivileged callers may create FIFOs, sockets and regular files
  (comment in `mknod.2` ERRORS). The manual's *Making Special Files*
  still states the stricter "only the superuser can create special
  files" rule -- quoted as the manual's Hurd-flavored claim.
- The manual's FIXME list flags `mknodat` as undocumented in the
  glibc manual; the entry above follows the kernel man page.
- musl 1.2.5: `mknod` prefers `SYS_mknod` and falls back to
  `mknodat(AT_FDCWD, ...)` on architectures without the old slot
  (`src/stat/mknod.c`).

## Errors

`EACCES`, `EBADF` (`mknodat`), `EDQUOT`, `EEXIST`, `EFAULT`, `EINVAL`
(bad type), `ELOOP`, `ENAMETOOLONG`, `ENOENT`, `ENOMEM`, `ENOSPC`,
`ENOTDIR`, `EPERM` (unprivileged device node, or unsupported node
type), `EROFS` (`mknod.2`).

## References

- glibc manual: `filesys.texi`, node *Making Special Files*
- man2: `mknod.2` (covers `mknodat`)
- headers: `/usr/include/x86_64-linux-gnu/sys/stat.h` lines 403-413
- symbols: `nm -D --with-symbol-versions libc.so.6`
