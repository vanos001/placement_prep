# `mount` / `umount` / `umount2` - glibc

> Split from the chapter *glibc: System Management* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sys/mount.h` (`mount` lines 281-282, `umount` line 286, `umount2` line 289 -- all unconditional in this header; MS_* flag enum from line 44, MNT_* lines 179-184) |
| Standards | Linux-specific: "should not be used in programs intended to be portable" (mount.2, umount.2 CONFORMING TO) |
| Exported | `mount@@GLIBC_2.2.5` (W), `umount@@GLIBC_2.2.5` (W), `umount2@@GLIBC_2.2.5` (W) (nm, host glibc 2.41) |
| Thread-safety | no ATTRIBUTES tables in mount.2/umount.2; thin syscall wrappers |
| Ledger ID | GLIBC-mount, GLIBC-umount, GLIBC-umount2 |

## Declaration and gates

```c
#include <sys/mount.h>

int mount(const char *source, const char *target,
          const char *filesystemtype, unsigned long mountflags,
          const void *data);                       /* sys/mount.h:281 */
int umount(const char *target);                    /* sys/mount.h:286 */
int umount2(const char *target, int flags);        /* sys/mount.h:289 */

#define MS_RDONLY   1    /* sys/mount.h enum, line 45 onward */
#define MS_BIND     4096
#define MS_MOVE     8192
#define MS_REC      16384
#define MNT_FORCE   1    /* umount2, sys/mount.h:179 */
#define MNT_DETACH  2    /* sys/mount.h:181 */
#define MNT_EXPIRE  4    /* sys/mount.h:183 */
```

No feature-test gate: sys/mount.h is a Linux-only header declaring all
three unconditionally (next to the new mount API: `fsopen`, `fsmount`,
`move_mount`, `fsconfig`, `fspick`, `open_tree`, `mount_setattr`,
lines 293-325).

## Semantics

`mount` attaches `source` at `target` for `filesystemtype` (types listed
in `/proc/filesystems`), with per-filesystem `data` options and the
`MS_*` bits selecting the operation class (plain mount, `MS_BIND`,
`MS_REMOUNT`, `MS_MOVE`, `MS_SHARED`/`SLAVE`/`PRIVATE`/`UNBINDABLE`,
`MS_REC` to recurse). `umount` detaches; `umount2` refines it: `MNT_FORCE`
aborts pending requests (NFS-class availability limits per filesystem),
`MNT_DETACH` is the lazy unmount that waits for last use, `MNT_EXPIRE`
marks the mount for expiry -- first call fails with `EAGAIN` unless
unused, and it conflicts with `MNT_DETACH` (mount.2, umount.2). All need
`CAP_SYS_ADMIN`. Raw pages:
[mount](../../../syscalls/fs-mounts-namespace/mount.md),
[umount2](../../../syscalls/fs-mounts-namespace/umount2.md).

## Gotchas and portability

- `MS_MGC_VAL` (0xC0ED in the top 16 bits) was mandatory before kernel
  2.4 and is now ignored (mount.2 NOTES).
- The mount API moved on: file-descriptor-based `fsopen`/`fsmount`/
  `move_mount`/`mount_setattr` live in the same header and have their own
  syscall pages under fs-mounts-namespace.
- No portable equivalent exists on non-Linux; guard with `__linux__`.
- musl 1.2.5: all three present (`include/sys/mount.h` lines 67-69,
  `src/linux/mount.c`).

## Errors

`EPERM` (missing `CAP_SYS_ADMIN`), `EBUSY` (target busy / source already
mounted), `EINVAL` (bad flags, `MNT_EXPIRE` with `MNT_DETACH`, locked
mount), `ELOOP`, `ENAMETOOLONG`, `ENOTDIR`/`EISDIR`, `ENXIO`, plus
per-filesystem `data` errors -- full lists in mount.2/umount.2.

## References

- man2: `mount.2`, `umount.2` (covers `umount2`; `umount2.2` is a `.so` link)
- headers: `/usr/include/x86_64-linux-gnu/sys/mount.h` (lines 21-325)
- symbols: `nm -D --with-symbol-versions libc.so.6`
