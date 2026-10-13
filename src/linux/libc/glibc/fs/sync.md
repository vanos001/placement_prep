# `sync` (3) - glibc

> Split from the chapter *glibc: Low-Level I/O* into the per-function layout;
> see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [sync(2)](../../../syscalls/descriptors-io/sync.md) and
> [fsync(2)](../../../syscalls/descriptors-io/fsync.md).

| Field | Value |
|---|---|
| Header | `unistd.h` |
| Standards | POSIX.1-2001/2008, SVr4, 4.3BSD; manual tags it X/Open with `void` return |
| Exported | `sync@@GLIBC_2.2.5`; sibling `syncfs@@GLIBC_2.14` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual, *Synchronizing I/O Operations*; `sync.2` carries no ATTRIBUTES table in man-pages 5.14) |
| Ledger ID | GLIBC-sync |

## Declaration and gates

```c
#include <unistd.h>

void sync(void);
int  syncfs(int fd);    /* __USE_GNU */
```

`sync` sits in the misc/XPG gate block
`__USE_MISC || __USE_XOPEN_EXTENDED`
(`/usr/include/unistd.h` lines 1001-1006, prototype at 1005), matching
`sync.2`'s gate table (`_XOPEN_SOURCE >= 500`, `_DEFAULT_SOURCE` since
glibc 2.19). `syncfs` is under `__USE_GNU` (lines 993-995).

## Semantics

`sync` causes all pending modifications of filesystem metadata and
cached file data on every mounted filesystem to be written to the
underlying devices; it takes no argument, returns nothing, and per
POSIX it may merely schedule the writes and return before they finish.
`syncfs` is the per-filesystem variant: only the filesystem containing
`fd` is flushed, and it does report failures (`sync.2`, manual
*Synchronizing I/O Operations*).

## Gotchas and portability

- Prototype history is version-visible: through glibc 2.2.1 Linux
  declared `int sync(void)` (always returning 0); since glibc 2.2.2 it
  is the standard `void sync(void)` (`sync.2` NOTES).
- BSD vs Linux semantics: the standard (and BSD tradition) allows
  schedule-and-return; Linux instead waits for I/O completion -- since
  kernel 1.3.20 -- so `sync(2)` there guarantees what `fsync` on every
  file would, while `sync(1)`/`sync(2)` on scheduling-only systems
  gives no such guarantee (`sync.2` NOTES/BUGS; the `sync(1)` utility
  is the command-line front end).
- For one file's data, `sync` is overkill: the manual points to
  `fsync`/`fdatasync` (*Synchronizing I/O Operations*; llio.texi).
- Kernel 5.8 taught `syncfs` to report writeback errors since the
  last call; before that it failed only on `EBADF` (`sync.2` NOTES).
- musl 1.2.5: `void sync` issuing bare `SYS_sync`
  (`src/unistd/sync.c`); `syncfs` wrapper in `src/linux/syncfs.c`.

## Errors

`sync` cannot fail -- it has no return value ("`sync()` is always
successful", `sync.2`). `syncfs` returns 0 or -1 with `EBADF`, `EIO`,
`ENOSPC`/`EDQUOT` (deferred write failures, NFS-style late
allocation).

## References

- glibc manual: `llio.texi`, node *Synchronizing I/O Operations*
- man2: `sync.2` (covers `syncfs`; `syncfs.2` sibling in cache)
- headers: `/usr/include/unistd.h` lines 993-1006
- symbols: `nm -D --with-symbol-versions libc.so.6`
