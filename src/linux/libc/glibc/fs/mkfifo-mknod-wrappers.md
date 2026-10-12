# `mkfifo` / `mknod` (3) - glibc

> Per-function page for the special-file creators of the glibc File System
> Interface and FIFO families; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. The FIFO
> read/write story lives in the pipe chapter of the manual, not in
> `filesys.texi`.

| Field | Value |
|---|---|
| Header | `sys/stat.h` (both; the manual's `pipe.texi` also names `sys/stat.h` for `mkfifo`) |
| Standards | POSIX.1 (`mkfifo`), POSIX.1-2008 (`mkfifoat`), BSD (`mknod`, `mknodat`) |
| Exported | `mkfifo@@GLIBC_2.2.5`; `mkfifoat@@GLIBC_2.4`; `mknod`/`mknodat` `@@GLIBC_2.33` on this host (nm, glibc 2.41; internal `__xmknod@@GLIBC_2.2.5` also visible) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual safety annotations) |
| Ledger ID | GLIBC-mkfifo (documented, pipe/pipe2 group), GLIBC-mknod (researched), GLIBC-mkfifoat, GLIBC-mknodat (triage rows) |

## Declaration and gates

```c
#include <sys/stat.h>

int mkfifo(const char *path, mode_t mode);
int mkfifoat(int fd, const char *path, mode_t mode);  /* __USE_ATFILE */
int mknod(const char *path, mode_t mode, dev_t dev);
int mknodat(int fd, const char *path, mode_t mode, dev_t dev);
```

## Semantics

`mkfifo` makes a FIFO special file with permissions taken from `mode`
(modified by the umask, like every creator). Any process can then open it
for reading or writing like an ordinary file, but a FIFO must be open at
both ends before I/O proceeds: opening for reading blocks until a writer
arrives, and vice versa (manual `pipe.texi`, *FIFO Special Files*). Errors:
`EEXIST`, `ENOSPC`, `EROFS` plus the usual name errors (manual). `mknod` is
the primitive for special files: `mode` may carry `S_IFCHR` or `S_IFBLK`
type bits and `dev` selects the device, built with `makedev` (manual,
*Making Special Files*; the `dev` interpretation depends on the file kind).
The device-number helpers and the `st_rdev` field they decode live on
[test-file-types-macros.md](./test-file-types-macros.md).

## Gotchas and portability

- Privilege: the manual states only the superuser can create special files
  with `mknod` (`EPERM`). On Linux the kernel allows unprivileged FIFO and
  socket creation and gates only device nodes behind `CAP_MKNOD`
  (man2 `mknod.2`); the manual's blanket sentence predates that nuance, so
  treat Linux privilege questions by the man2 wording.
- The POSIX producer/consumer use of FIFOs (atomicity up to `PIPE_BUF`) is
  the manual's *Pipe Atomicity* node, shared with `pipe(2)`.
- musl 1.2.5: `src/stat/mkfifo.c` is `mknod(path, mode | S_IFIFO, 0)` and
  `src/stat/mknod.c` calls `SYS_mknod` with an `mknodat` fallback.

## References

- glibc manual: `filesys.texi` node *Making Special Files*; `pipe.texi`
  nodes *FIFO Special Files*, *Pipe Atomicity*
- man2: `mknod.2`; man3 `mkfifo.3`, `mkfifoat.3`
- headers: `/usr/include/x86_64-linux-gnu/sys/stat.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
