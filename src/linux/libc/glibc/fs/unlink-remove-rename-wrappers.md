# `unlink` / `remove` / `rename` (3) - glibc

> Per-function page for name deletion and renaming in the glibc File System
> Interface; see the [method page](../../../interface-encyclopedia.md) and
> the [glibc ledger](../../ledger-glibc.md) for coverage status. The stdio
> family carries a sibling page with the same functions at
> [../stdio/remove-rename.md](../stdio/remove-rename.md); this page adds the
> `*at` twins and the unlink-specific error set.

| Field | Value |
|---|---|
| Header | `unistd.h` (`unlink`, `unlinkat`, `rmdir`); `stdio.h` (`remove`, `rename`, `renameat`) |
| Standards | POSIX.1 (`unlink`, `rmdir`, `rename`), ISO C (`remove`, `rename`), POSIX.1-2008 (`unlinkat`, `renameat`) |
| Exported | `unlink`/`remove`/`rename` `@@GLIBC_2.2.5`; `unlinkat`/`renameat` `@@GLIBC_2.4` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe on `unlink`/`rmdir`/`remove`/`rename` (manual annotations) |
| Ledger ID | GLIBC-unlink, GLIBC-unlinkat, GLIBC-remove, GLIBC-rename, GLIBC-renameat (documented; remove/rename also grouped into the stdio page) |

## Declaration and gates

```c
#include <unistd.h>
#include <stdio.h>

int unlink(const char *name);
int unlinkat(int fd, const char *name, int flags);   /* AT_REMOVEDIR */
int rmdir(const char *path);
int remove(const char *filename);                    /* stdio.h */
int rename(const char *old, const char *new);        /* stdio.h */
int renameat(int oldfd, const char *old,
             int newfd, const char *new);
```

## Semantics

Deletion removes a *name*; the file itself disappears when the last link
goes, and even then only after no process still holds it open (manual,
*Deleting Files*). `unlink` refuses directories on GNU systems (`EPERM`;
use `rmdir`, which requires an empty directory and reports `ENOTEMPTY` on
Linux). `remove` is the ISO C dispatcher: like `unlink` for files, like
`rmdir` for directories (manual). `rename` moves a name atomically: there is
no instant at which `new` does not resolve, and after a crash `new` is either
absent or intact (manual, *Renaming Files*). A non-directory `old` never
replaces a directory and vice versa; renaming a directory onto a non-empty
one fails (`ENOTEMPTY` on Linux), and a directory cannot be renamed inside
itself (`EINVAL`). Both names must be on one filesystem (`EXDEV`).

## Gotchas and portability

- The manual flags one POSIX inconsistency: when `old` and `new` are two
  names of the same file, POSIX requires rename to do nothing yet report
  success, "which is inconsistent" - behavior varies across systems.
- The open file, not the name, keeps inode and data alive: the classic
  "unlink an open log file and keep writing" trick rests on the postponed
  deletion sentence above.
- musl 1.2.5: `src/stdio/remove.c` tries `unlink` and retries `rmdir`
  (or `unlinkat` + `AT_REMOVEDIR`) on `EISDIR`; `src/unistd/unlink.c` is a
  direct syscall call.

## References

- glibc manual: `filesys.texi`, nodes *Deleting Files*, *Renaming Files*;
  `stdio.texi` *Deleting Files* comment for the remove dispatch
- man2: `unlink.2`, `rename.2`; man3 `remove.3`
- headers: `/usr/include/unistd.h`, `/usr/include/stdio.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
