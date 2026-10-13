# `ftruncate` / `ftruncate64` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [truncate(2)](../../../syscalls/descriptors-io/truncate.md); path-based
> sibling: [truncate-truncate64.md](truncate-truncate64.md).

| Field | Value |
|---|---|
| Header | `unistd.h` |
| Standards | POSIX.1 (XSI; "introduced in BSD Unix, `ftruncate` later added to POSIX.1", manual); `ftruncate64` Unix98 LFS |
| Exported | `ftruncate@@GLIBC_2.2.5`, `ftruncate64@@GLIBC_2.2.5` at the same address (alias, nm, host glibc 2.41) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual safety annotations; `truncate.2` carries no ATTRIBUTES table in man-pages 5.14) |
| Ledger ID | GLIBC-ftruncate, GLIBC-ftruncate64 |

## Declaration and gates

```c
#include <unistd.h>

int ftruncate(int fd, off_t length);
int ftruncate64(int fd, off64_t length);   /* __USE_LARGEFILE64 */
```

`ftruncate` sits in the POSIX.1b/XPG gate block
`__USE_POSIX199309 || __USE_XOPEN_EXTENDED || __USE_XOPEN2K`
(`/usr/include/unistd.h` lines 1044-1057, prototype at 1049). With
`_FILE_OFFSET_BITS == 64` the name redirects to `ftruncate64`
(lines 1052-1055); the explicit `ftruncate64` (line 1059) needs
`__USE_LARGEFILE64`. The `chdir(2)`-style gate table in `ftruncate.2`:
`_XOPEN_SOURCE >= 500` or `_POSIX_C_SOURCE >= 200112L` since glibc 2.3.5.

## Semantics

Truncates the regular file open on `fd` to exactly `length` bytes:
shrink discards data, grow extends with null-byte holes. The file
offset is not changed; `st_ctime`/`st_mtime` are updated when the size
changes and the set-user-ID/set-group-ID bits may be cleared. The fd
must be open for writing. `ftruncate` is also the way to size a POSIX
shared memory object created with `shm_open` (`ftruncate.2` NOTES,
manual *File Size*). glibc's wrapper transparently uses the kernel's
64-bit slot where it exists (manual *File Size*).

## Gotchas and portability

- Non-XSI POSIX permits either error or extension when `length`
  exceeds the file size; Linux follows XSI on native filesystems but
  some filesystems (notably VFAT) refuse extension with `EPERM`
  (`truncate.2` NOTES).
- glibc 2.12 header bug: the minimum `_POSIX_C_SOURCE` exposing
  `ftruncate` was wrongly 200809L instead of 200112L, fixed later
  (`truncate.2` BUGS).
- On x86_64 `ftruncate` and `ftruncate64` share one symbol and one
  syscall slot (nm address match; per-call table in the
  [truncate(2)](../../../syscalls/descriptors-io/truncate.md) page).
- musl 1.2.5: `#define ftruncate64 ftruncate` under LFS
  (`include/unistd.h` line 206); thin `SYS_ftruncate` wrapper
  (`src/unistd/ftruncate.c`).

## Errors

`EBADF` (invalid fd or not open for writing -- POSIX allows `EBADF`
or `EINVAL`, Linux produces `EINVAL`); `EINVAL` (fd does not reference
a regular file or POSIX shared memory object); `EINTR`, `EFBIG`,
`EIO`, `EPERM` (file seal, or filesystem refusing extension), `EROFS`,
`ETXTBSY` (`truncate.2`).

## References

- glibc manual: `filesys.texi`, node *File Size*
- man2: `ftruncate.2` (`.so` alias of `truncate.2`)
- headers: `/usr/include/unistd.h` lines 1044-1061
- symbols: `nm -D --with-symbol-versions libc.so.6`
