# `truncate` / `truncate64` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [truncate(2)](../../../syscalls/descriptors-io/truncate.md); fd-based
> sibling: [ftruncate-ftruncate64.md](ftruncate-ftruncate64.md).

| Field | Value |
|---|---|
| Header | `unistd.h` |
| Standards | X/Open (`truncate`, manual standards tag); POSIX.1-2001 as an XSI extension; `truncate64` Unix98 LFS |
| Exported | `truncate@@GLIBC_2.2.5`, `truncate64@@GLIBC_2.2.5` at the same address (alias, nm, host glibc 2.41) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual safety annotations; `truncate.2` carries no ATTRIBUTES table in man-pages 5.14) |
| Ledger ID | GLIBC-truncate, GLIBC-truncate64 |

## Declaration and gates

```c
#include <unistd.h>

int truncate(const char *path, off_t length);
int truncate64(const char *path, off64_t length);  /* __USE_LARGEFILE64 */
```

`truncate` is declared in the X/Open/POSIX.1-2008 gate block
`__USE_XOPEN_EXTENDED || __USE_XOPEN2K8`
(`/usr/include/unistd.h` lines 1024-1036, prototype at 1026), matching
`truncate.2`'s gate table
(`_XOPEN_SOURCE >= 500`, or `_POSIX_C_SOURCE >= 200809L` since glibc
2.12). `truncate64` (line 1038) needs `__USE_LARGEFILE64`; with
`_FILE_OFFSET_BITS == 64` the name redirects to it.

## Semantics

Truncates the regular file named by `path` to exactly `length` bytes:
shrink loses data, grow extends with null bytes, the file must be
writable, and the file offset concept does not apply since no
descriptor is involved. Size change updates `st_ctime`/`st_mtime` and
may clear the set-user-ID/set-group-ID bits (`truncate.2`; manual
*File Size*). When no `truncate` syscall exists on the platform the
manual notes the wrapper is built from `open` plus `ftruncate`
(safety comment in filesys.texi).

## Gotchas and portability

- Manual, *File Size*: using these functions on anything other than a
  regular file gives *undefined* results -- on many systems the call
  appears to succeed and does nothing.
- Extension past the current size is not universal: VFAT refuses it
  with `EPERM`, and non-XSI systems may reject it outright
  (`truncate.2` NOTES).
- The manual lists `EPERM` for "append-only" or "immutable" files, an
  error the man page expresses via file seals and unsupported
  filesystems.
- On x86_64 `truncate` and `truncate64` share one symbol and one
  syscall slot (nm address match; numbers table in the
  [truncate(2)](../../../syscalls/descriptors-io/truncate.md) page;
  the 64-bit slots exist only on 32-bit kernels).
- musl 1.2.5: `#define truncate64 truncate` under LFS
  (`include/unistd.h` line 205); thin `SYS_truncate` wrapper
  (`src/unistd/truncate.c`).

## Errors

`EACCES` (path prefix search denied, or file not writable), `EFAULT`,
`EFBIG`, `EINTR`, `EINVAL` (negative length), `EIO`, `EISDIR`, `ELOOP`,
`ENAMETOOLONG`, `ENOENT`, `ENOTDIR`, `EPERM` (seals, unsupported
extension), `EROFS` (`truncate.2`).

## References

- glibc manual: `filesys.texi`, nodes *File Size*, *Storage Allocation*
- man2: `truncate.2` (covers `ftruncate`)
- headers: `/usr/include/unistd.h` lines 1024-1042
- symbols: `nm -D --with-symbol-versions libc.so.6`
