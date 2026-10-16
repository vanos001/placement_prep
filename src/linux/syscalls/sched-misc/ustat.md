# ustat(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 136 / 62 / -- / 62 |
| Since (kernel) | 1.0 (only meaningful from 1.3.16 per the ENOSYS error text; ustat.2 HISTORY) |
| Man page | man2/ustat.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | ustat T @GLIBC_2.2.5 still exported by glibc 2.41 (nm -D) as a leftover compat symbol; man-pages HISTORY records the wrapper removed in glibc 2.28 |
| Aliases covered | none; replaced by statfs(2) (see [statfs](../descriptors-io/statfs.md)) |
| Ledger ID | SC-ustat |

## Purpose

ustat() returned free-block and free-inode counts for the mounted filesystem identified by device number `dev`, filling a `struct ustat { daddr_t f_tfree; ino_t f_tinode; char f_fname[6]; char f_fpack[6]; }` (ustat.2, DESCRIPTION). The name fields were never implemented and always came back as NULs (ustat.2, DESCRIPTION).

## Synopsis

```c
#include <sys/types.h>
#include <unistd.h>   /* libc[45] */
#include <ustat.h>    /* glibc2 */
[[deprecated]] int ustat(dev_t dev, struct ustat *ubuf);
```

## Arguments and behavior

`dev` is the device number of a mounted filesystem; `ubuf` receives the counts (ustat.2, DESCRIPTION). The man page's own verdict: "ustat() is deprecated and has been provided only for compatibility. All new programs should use statfs(2) instead" (ustat.2, HISTORY); on 64-bit-capable systems statfs(2) is itself the legacy twin of statfs64/statx-era interfaces.

## Return value and errors

0 on success with ubuf filled; -1 with errno (ustat.2, RETURN VALUE). Errors: EFAULT (ubuf outside address space), EINVAL (dev is not a mounted filesystem), ENOSYS (filesystem does not support the operation, or Linux < 1.3.16) (ustat.2, ERRORS).

## Flags and constants

None.

## Security and notes

Identifying a filesystem by raw device number -- rather than a path or fd -- is the design flaw that made ustat(2) unfixable: it races mount/unmount and leaks cross-namespace information. statfs(2) takes a path and follows the mount table correctly. The HP-UX portability notes in the man page (f_blksize divergence, dynamic-inode filesystems returning -1 in f_tinode) are interview color for "filesystem statistics are inherently per-fs" (ustat.2, HISTORY, HP-UX notes). Cross-reference: [statfs](../descriptors-io/statfs.md), [sysfs](sysfs.md), [quotactl](../fs-mounts-namespace/quotactl.md).

## References

- https://man7.org/linux/man-pages/man2/ustat.2.html
- man-pages syscalls(2)
- worklog: leftover glibc symbol ustat @GLIBC_2.2.5 verified with nm -D (2026-10-17)
