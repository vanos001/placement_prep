# setxattr(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | setxattr: x64 188 / i386 226 / arm64-generic 5 / arm32 226; lsetxattr: 189 / 227 / 6 / 227; fsetxattr: 190 / 228 / 7 / 228; getxattr: 191 / 229 / 8 / 229; lgetxattr: 192 / 230 / 9 / 230; fgetxattr: 193 / 231 / 10 / 231; listxattr: 194 / 232 / 11 / 232; llistxattr: 195 / 233 / 12 / 233; flistxattr: 196 / 234 / 13 / 234; removexattr: 197 / 235 / 14 / 235; lremovexattr: 198 / 236 / 15 / 236; fremovexattr: 199 / 237 / 16 / 237 |
| Since (kernel) | 2.6 for the whole family (man VERSIONS; glibc 2.3). The 6.13 dirfd batch `setxattrat` / `getxattrat` / `listxattrat` / `removexattrat` (x64 463-466) is a separate source-limited page set, not covered here |
| Man page | man2/setxattr.2 covers the three setters; getxattr.2 / listxattr.2 / removexattr.2 are the readers and remover (cached, 2021-08-27); the `l*`/`f*` names are roff `.so` aliases. Namespace concepts: xattr.7 (fetched, man-pages 6.19) |
| glibc wrapper | Yes for all twelve; `<sys/xattr.h>` (glibc 2.3) |
| Aliases covered | `lsetxattr`, `fsetxattr`, `getxattr`, `lgetxattr`, `fgetxattr`, `listxattr`, `llistxattr`, `flistxattr`, `removexattr`, `lremovexattr`, `fremovexattr` (SC-getxattr ... SC-fremovexattr rows) |
| Ledger ID | SC-setxattr |

## Purpose

Extended attributes are name:value pairs attached to inodes, extending the
`stat(2)` attribute set. The family has three operations times three file
selectors: set (`setxattr` / `lsetxattr` / `fsetxattr`), get
(`getxattr` / `lgetxattr` / `fgetxattr`), list
(`listxattr` / `llistxattr` / `flistxattr`) and remove
(`removexattr` / `lremovexattr` / `fremovexattr`). The `l` prefix does not
dereference symlinks; the `f` prefix operates on an open descriptor.

## Synopsis

    #include <sys/xattr.h>
    int setxattr(const char *path, const char *name,
                 const void *value, size_t size, int flags);
    int lsetxattr(const char *path, const char *name,
                  const void *value, size_t size, int flags);
    int fsetxattr(int fd, const char *name,
                  const void *value, size_t size, int flags);

    ssize_t getxattr(const char *path, const char *name,
                     void *value, size_t size);
    ssize_t listxattr(const char *path, char *list, size_t size);
    int removexattr(const char *path, const char *name);
    /* the l* variants are identical but never dereference symlinks;
       the f* variants replace path with an open file descriptor fd */

## Arguments and behavior

`name` is a null-terminated, fully qualified `namespace.attribute` string
(for example `user.mime_type`, `security.selinux`, `system.posix_acl_access`,
`trusted.md5sum`). `setxattr()` writes `size` bytes of `value` (zero length
permitted); by default it creates or replaces the attribute.
`getxattr()` copies the value into `value` and returns its length; with
`size` 0 it returns the size the value would need. `listxattr()` fills
`list` with null-terminated names and returns the list length; with `size`
0 it returns the needed size. Names of attributes the caller cannot access
may be omitted from the list. Attributes are read and written as atomic
objects; the space they consume may be counted against disk quotas.

## Return value and errors

`setxattr()` / `removexattr()` return 0 on success; `getxattr()` /
`listxattr()` return byte counts. On failure all return -1: `EDQUOT`
(out of quota space), `EEXIST` (`XATTR_CREATE` on an existing name),
`ENODATA` (`XATTR_REPLACE` on a missing name; also getxattr for a missing
name; `ENOATTR` is the historical synonym), `ENOSPC`, `ENOTSUP`
(invalid namespace prefix; xattrs unsupported or disabled), `EPERM`
(immutable or append-only file), `ERANGE` (name or value beyond
filesystem limits; buffer too small), plus the `stat(2)` path errors.

## Flags and constants

| Constant | Value | Meaning |
|---|---|---|
| `XATTR_CREATE` | 0x1 | Pure create: fail if the attribute exists |
| `XATTR_REPLACE` | 0x2 | Pure replace: fail if the attribute does not exist |

Namespaces (xattr.7) and their access rules:

| Namespace | Rules |
|---|---|
| `user.` | Arbitrary user data on regular files and directories only; read needs read permission, write needs write permission; on sticky directories restricted to owner / appropriate capabilities |
| `security.` | Used by security modules (SELinux) and file capabilities; module-defined policy, write is `CAP_SYS_ADMIN` when no module is loaded |
| `system.` | Kernel objects such as POSIX ACLs; policy implemented per attribute by the filesystem |
| `trusted.` | Visible and settable only with `CAP_SYS_ADMIN` |

## Security and notes

VFS limits: names 255 bytes, values 64 kB, name list 64 kB (xattr.7).
ext2/3/4 keep all of a file's xattrs within one filesystem block; Btrfs,
XFS and Reiserfs scale further; older Reiserfs/ext2/ext3 needed the
`user_xattr` mount option. Since kernel 6.13 the dirfd-based batch
`setxattrat()` / `getxattrat()` / `listxattrat()` / `removexattrat()`
(x64 463-466, worklog 1-d tag probe; no man page) adds `struct xattr_args`
and `AT_EMPTY_PATH` support; their pages are separate source-limited
entries. Related: [chmod.md](chmod.md) (permission bits govern `user.`
access), [mknod.md](mknod.md) (special-file permission semantics motivate
the `user.` restrictions).

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/setxattr.2`,
  `getxattr.2`, `listxattr.2`, `removexattr.2` (+ `.so` aliases)
- Namespace overview: `source-cache/fetched/xattr.7.txt` (man-pages 6.19)
- Online: https://man7.org/linux/man-pages/man2/setxattr.2.html,
  https://man7.org/linux/man-pages/man7/xattr.7.html
- Constants: `/usr/include/linux/xattr.h`, `sys/xattr.h`; kernel tables
  `source-cache/kernel/syscall_64.tbl` (188-199)
