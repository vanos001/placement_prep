# `posix_fallocate` / `posix_fallocate64` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [fallocate(2)](../../../syscalls/descriptors-io/fallocate.md).

| Field | Value |
|---|---|
| Header | `fcntl.h` |
| Standards | POSIX.1-2001 (behavior tightened in POSIX.1-2008) |
| Exported | `posix_fallocate@@GLIBC_2.2.5`, `posix_fallocate64@@GLIBC_2.2.5` (nm, host glibc 2.41; available since glibc 2.1.94 per `posix_fallocate.3`) |
| Thread-safety | MT-Safe "but see NOTES" (`posix_fallocate.3` ATTRIBUTES): the fallocate path is MT-safe, the write-zeros emulation is not |
| Ledger ID | GLIBC-posix_fallocate, GLIBC-posix_fallocate64 |

## Declaration and gates

```c
#include <fcntl.h>

int posix_fallocate(int fd, off_t offset, off_t len);
int posix_fallocate64(int fd, off64_t offset, off64_t len);
```

Declared at `/usr/include/fcntl.h` line 323
(`_POSIX_C_SOURCE >= 200112L` per `posix_fallocate.3`); the header
deliberately omits
`__THROW` -- "a possible cancellation point" (header comment, lines
319-321). LFS: with `_FILE_OFFSET_BITS == 64` the name redirects to
`posix_fallocate64` (lines 326-330); the explicit `*64` name (line 334)
needs `__USE_LARGEFILE64`.

## Semantics

Ensures backing store for the byte range starting at `offset` and
running `len` bytes in the file open on `fd`: later writes there can
no longer fail with `ENOSPC`, and the file grows to `offset + len` if
it was smaller. The file must be a regular file open for writing
(manual *Storage Allocation*). Distinctive convention: on failure the
function **returns the error number** and does not set `errno`
(`posix_fallocate.3` RETURN VALUE). glibc implements it with the
`fallocate(2)` syscall and, when the filesystem lacks support,
emulates by writing zero blocks -- with the caveats below.

## Gotchas and portability

- Emulation hazards, from the manual and man page: inefficient full
  re-examination of the range; concurrent writes in the range can be
  overwritten with null bytes; concurrent size growth can shrink the
  result; `O_WRONLY`/`O_APPEND` descriptors fail with `EBADF`; and
  with `len == 0` the fallback is `ftruncate`, racing concurrent
  extensions.
- POSIX.1-2001 vs 2008 differ on when `EINVAL` is mandatory for
  `len == 0` / negative values (`posix_fallocate.3` CONFORMING TO).
- Linux escape hatch: call `fallocate(2)` directly for the no-emulation
  `EOPNOTSUPP` contract -- glibc never emulates `fallocate` itself
  (manual *Storage Allocation*).
- musl 1.2.5: direct `SYS_fallocate`, no emulation -- unsupported
  filesystems surface as the negative kernel error (`EOPNOTSUPP`),
  which the man page calls out by name (`src/fcntl/posix_fallocate.c`);
  `posix_fallocate64` is a macro alias (`include/fcntl.h` line 207).

## Errors

Returned, not in `errno`: `EBADF` (bad fd or not open for writing),
`EFBIG`, `EINTR`, `EINVAL` (negative `offset`, non-positive `len`,
unsupported operation), `ENODEV` (not a regular file), `ENOSPC`,
`EOPNOTSUPP` (filesystem refusal, musl path), `ESPIPE`
(`posix_fallocate.3`).

## References

- glibc manual: `filesys.texi`, node *Storage Allocation*
- man3: `posix_fallocate.3`
- headers: `/usr/include/fcntl.h` lines 319-335
- symbols: `nm -D --with-symbol-versions libc.so.6`
