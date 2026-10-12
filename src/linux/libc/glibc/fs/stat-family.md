# `stat` / `fstat` / `lstat` / `fstatat` / `statx` (3) - glibc

> Per-function page for the file-attribute readers of the glibc File System
> Interface family; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status. The
> kernel-side story lives in
> [stat(2)](../../../syscalls/descriptors-io/stat.md) and
> [statx(2)](../../../syscalls/descriptors-io/statx.md).

| Field | Value |
|---|---|
| Header | `sys/stat.h` |
| Standards | POSIX.1 (`stat`, `fstat`, `fstatat`), BSD (`lstat`), Linux (glibc 2.28 wrapper for `statx`) |
| Exported | `stat`/`stat64`, `fstat`/`fstat64`, `lstat`/`lstat64`, `fstatat`/`fstatat64` all `@@GLIBC_2.33` on this host; `statx@@GLIBC_2.28` (nm, host glibc 2.41; no `@GLIBC_2.2.5` compat aliases exist for these names on x86_64, stated from nm) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual safety annotations on all of `stat`, `fstat`, `fstatat`, `lstat`) |
| Ledger ID | GLIBC-stat (grouped), GLIBC-fstat, GLIBC-lstat, GLIBC-fstatat (all documented), GLIBC-statx (triage row) |

## Declaration and gates

```c
#include <sys/stat.h>

int stat(const char *restrict file, struct stat *restrict buf);
int fstat(int fd, struct stat *buf);
int lstat(const char *restrict file, struct stat *restrict buf);
int fstatat(int fd, const char *restrict file,        /* __USE_ATFILE */
            struct stat *restrict buf, int flag);
int statx(int dirfd, const char *restrict pathname,   /* __USE_GNU,
                                                         bits/statx.h */
          int flags, unsigned int mask, struct statx *restrict statxbuf);
```

`struct stat` members on this host (`bits/struct_stat.h`): `st_dev`,
`st_ino`, `st_mode`, `st_nlink`, `st_uid`, `st_gid`, `st_rdev`, `st_size`,
`st_blksize`, `st_blocks`, and the `struct timespec` members `st_atim`,
`st_mtim`, `st_ctim` (with `st_atime`/`st_mtime`/`st_ctime` compatibility
spelling). The manual documents `st_mtime` as last modification of the file
contents and `st_ctime` as last modification of the attributes.

## Semantics

`stat` follows symbolic links: if `file` names a link, the attributes
describe the target, and a dangling link fails with `ENOENT` (manual,
*Reading Attributes*). `lstat` does not follow links and reports the link
itself. `fstat` takes an open descriptor (`EBADF` otherwise). `fstatat`
resolves `file` relative to `fd` (`AT_FDCWD` for the current directory) and
accepts `AT_EMPTY_PATH`, `AT_NO_AUTOMOUNT` and `AT_SYMLINK_NOFOLLOW`
(manual; man2 stamps the first two `since Linux 2.6.39` and `2.6.38`).
`statx` is the extensible Linux variant; NEWS 2.28 records that glibc
provides "basic stat support based on the fstatat64 function" when the
kernel lacks statx. `st_blocks` counts 512-byte blocks, and the manual's
sparse-file test is `st.st_blocks * 512 < st.st_size`.

## Gotchas and portability

- LFS: with `_FILE_OFFSET_BITS == 64` the plain names redirect to the
  `stat64`-style implementations (manual, header `#define` redirects above).
- The `@@GLIBC_2.33` default versions on an x86_64 host are an nm observation;
  no cached source states why these names carry no `@GLIBC_2.2.5` compat
  aliases there - left unverified rather than guessed.
- musl 1.2.5: `src/stat/stat.c` is `fstatat(AT_FDCWD, path, buf, 0)`, and
  `src/stat/fstatat.c` issues `SYS_statx` with mask `0x7ff`
  (`STATX_BASIC_STATS`) plus `AT_NO_AUTOMOUNT`, with a legacy fallback.

## References

- glibc manual: `filesys.texi`, nodes *Attribute Meanings*, *Reading
  Attributes*; NEWS 2.28 (statx wrapper added)
- man2: `stat.2`, `statx.2`
- headers: `/usr/include/x86_64-linux-gnu/sys/stat.h`,
  `bits/statx.h`, `bits/struct_stat.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
