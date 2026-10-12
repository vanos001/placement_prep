# `getdents64` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [getdents64(2)](../../../syscalls/descriptors-io/getdents64.md); buffered
> alternative: [opendir-readdir-scandir.md](opendir-readdir-scandir.md).

| Field | Value |
|---|---|
| Header | `dirent.h` (via `bits/dirent_ext.h`, under `__USE_GNU`) |
| Standards | None: raw Linux syscall interface; the glibc wrapper is a GNU extension |
| Exported | `getdents64@@GLIBC_2.30` (nm, host glibc 2.41); glibc provides no `getdents()` wrapper at all |
| Thread-safety | Not rated -- raw kernel buffer fill; no ATTRIBUTES row exists in `getdents(2)` |
| Ledger ID | GLIBC-getdents64 |

## Declaration and gates

```c
#include <dirent.h>          /* with #define _GNU_SOURCE */

ssize_t getdents64(int fd, void *buffer, size_t length);
```

Declared in `/usr/include/x86_64-linux-gnu/bits/dirent_ext.h` lines
25-31 under `__USE_GNU` (`__ssize_t` return, `__nonnull` on buffer);
that file is included unconditionally at the end of
`/usr/include/dirent.h` (line 406). glibc defines **no**
`struct linux_dirent64` in any header -- the application must lay the
struct out itself (`getdents.2` NOTES; confirmed by a grep of the
host's glibc headers).

## Semantics

Reads as many directory entries as fit into `length` bytes at
`buffer` from the directory open on `fd`, returning the byte count, 0
at end of directory, or -1 with `errno`. The buffer holds packed
`linux_dirent64` records -- `ino64_t d_ino`, `off64_t d_off`,
`unsigned short d_reclen`, `unsigned char d_type`, `char d_name[]` --
walked with `bpos += d_reclen`; `d_type` carries the `DT_*` constants,
convertible with the [DTTOIF/IFTODT](dttoif-iftodt.md) macros
(`getdents.2`). The kernel added `getdents64` in 2.4 for large
filesystems; on x86_64 it is the only getdents slot (numbers table in
the syscall page).

## Gotchas and portability

- "These are not the interfaces you are interested in" -- `readdir(3)`
  handles buffering, alignment and `DT_UNKNOWN` for you
  (`getdents.2` DESCRIPTION/NOTES).
- The 32-bit `getdents` syscall never got a glibc wrapper: before
  glibc 2.30 even `getdents64` required `syscall(2)`; the wrapper
  appeared with glibc 2.30 (`getdents.2` NOTES).
- Filesystem-dependent `d_type`: ext2/3/4, Btrfs and friends return
  real types, others only `DT_UNKNOWN` (`getdents.2`).
- musl 1.2.5: there is no `getdents64` function -- under
  `_LARGEFILE64_SOURCE` it is a macro mapping to `getdents`
  (`include/dirent.h` line 68), and musl's `getdents` wrapper issues
  `SYS_getdents` (`src/linux/getdents.c`); the raw call needs the
  same self-defined struct.

## Errors

`EBADF` (invalid fd), `EFAULT` (buffer outside address space),
`EINVAL` (result buffer too small for one record), `ENOENT`,
`ENOTDIR` (fd not a directory) (`getdents.2`).

## References

- man2: `getdents.2` (covers `getdents64`; `getdents64.2` is a `.so`
  alias)
- headers: `/usr/include/x86_64-linux-gnu/bits/dirent_ext.h`,
  `/usr/include/dirent.h` line 406
- symbols: `nm -D --with-symbol-versions libc.so.6`
