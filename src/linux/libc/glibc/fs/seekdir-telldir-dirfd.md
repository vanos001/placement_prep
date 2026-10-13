# `seekdir` / `telldir` / `dirfd` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `dirent.h` (all three) |
| Standards | POSIX.1-2001/2008, 4.3BSD (`seekdir`, `telldir`); POSIX.1-2008, BSD 4.3BSD-Reno origin (`dirfd`) |
| Exported | `seekdir@@GLIBC_2.2.5`, `telldir@@GLIBC_2.2.5`, `dirfd@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (`telldir(3)`, `seekdir(3)`, `dirfd(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-seekdir, GLIBC-telldir, GLIBC-dirfd |

## Declaration and gates

```c
#include <dirent.h>

void seekdir(DIR *dirp, long loc);
long telldir(DIR *dirp);
int  dirfd(DIR *dirp);
```

`seekdir` and `telldir` are declared in the
`#if defined __USE_MISC || defined __USE_XOPEN` block
(`/usr/include/dirent.h` lines 213-221, prototypes at 217 and 220).
`dirfd` is under `__USE_XOPEN2K8` (lines 224-226), with an
`__OPTIMIZE__`-only macro form when `_DIR_dirfd` is defined
(lines 228-229).

## Semantics

`telldir` returns the current position of the directory stream;
`seekdir` sets the position from which the next `readdir` starts, and
`loc` must be a value `telldir` returned for that same stream -- closing
and reopening the directory can invalidate it (`seekdir(3)`,
`telldir(3)`; manual *Random Access in a Directory Stream*). To rewind,
use `rewinddir`, not `seekdir`. `dirfd` returns the file descriptor the
stream uses internally; it stays valid until `closedir` and is useful
only for calls that do not depend on or alter the file position, such as
`fstat` and `fchdir` (`dirfd.3`, manual *Opening a Directory*).

## Gotchas and portability

- The `telldir` value is an opaque cookie: modern filesystems store
  directories as trees or hashes, so it is not a byte offset, may not
  match `struct dirent`'s `d_off`, and cannot be fed to `lseek`
  (`telldir(3)` NOTES, manual: "may not unambiguously identify the
  position"). Both man pages and the manual discourage the pair.
- Type history: glibc up to 2.1.1 used `off_t`; POSIX.1-2001 fixed
  `long`, used since glibc 2.1.2 (`telldir.3`, `seekdir.3` NOTES).
- `dirfd` hands out a live descriptor: `lseek` on it desynchronizes
  `readdir`'s buffer and `close` on it double-closes at `closedir`.
- musl 1.2.5: `telldir` returns `dir->tell` and `seekdir` literally
  `lseek`s the fd and drops buffered entries
  (`src/dirent/{telldir,seekdir}.c`); `dirfd` is `d->fd`
  (`src/dirent/dirfd.c`). All three are declared ungated.

## References

- glibc manual: `filesys.texi`, nodes *Opening a Directory*,
  *Random Access in a Directory Stream*
- man3: `seekdir.3`, `telldir.3`, `dirfd.3`
- headers: `/usr/include/dirent.h` lines 213-229
- symbols: `nm -D --with-symbol-versions libc.so.6`
