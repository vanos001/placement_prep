# `opendir` / `readdir` / `scandir` (3) - glibc

> Per-function page for the directory-stream family of the glibc File System
> Interface; see the [method page](../../../interface-encyclopedia.md) and
> the [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [getdents64(2)](../../../syscalls/descriptors-io/getdents64.md) and the
> cached [readdir(2)](../../../syscalls/descriptors-io/readdir.md) note.

| Field | Value |
|---|---|
| Header | `dirent.h` |
| Standards | POSIX.1 (`opendir`, `readdir`, `closedir`, `rewinddir`), GNU (`fdopendir`, `dirfd`), BSD/SVID (`scandir`, `alphasort`), GNU (`versionsort`, `scandirat`) |
| Exported | `opendir`/`readdir`/`closedir`/`readdir_r`/`rewinddir`/`telldir`/`seekdir`/`scandir`/`alphasort`/`versionsort` `@@GLIBC_2.2.5`; `fdopendir` `@@GLIBC_2.4`; `scandirat` `@@GLIBC_2.15`; `getdents64` `@@GLIBC_2.30` (nm, host glibc 2.41) |
| Thread-safety | `readdir`: MT-Unsafe (lock, returned buffer is stream-owned); `_r` twin MT-Safe; `scandir` MT-Safe (private stream); manual: safe to call `readdir` from several threads with separate `DIR` objects |
| Ledger ID | GLIBC-opendir, GLIBC-readdir, GLIBC-readdir_r, GLIBC-closedir, GLIBC-fdopendir, GLIBC-scandir, GLIBC-alphasort, GLIBC-versionsort (documented), GLIBC-telldir, GLIBC-seekdir, GLIBC-rewinddir (researched), GLIBC-scandirat (triage) |

## Declaration and gates

```c
#include <dirent.h>

DIR *opendir(const char *name);
DIR *fdopendir(int fd);                    /* GNU, takes ownership of fd */
struct dirent *readdir(DIR *dirp);
int readdir_r(DIR *restrict dirp,          /* deprecated */
              struct dirent *restrict entry, struct dirent **restrict result);
int closedir(DIR *dirp);
int scandir(const char *dir, struct dirent ***namelist,
            int (*sel)(const struct dirent *),
            int (*cmp)(const struct dirent **, const struct dirent **));
int alphasort(const struct dirent **a, const struct dirent **b);
int versionsort(const struct dirent **a, const struct dirent **b);
```

## Semantics

`opendir` opens a directory stream; `DIR` and `struct dirent` are library
allocated and must never be allocated by the caller (manual). `readdir`
returns a pointer into the stream's internal buffer that the next call
overwrites, so `d_name` must be copied if kept; `d_name` is the only field
portable across POSIX systems. End-of-directory and error both return NULL,
so set `errno` to zero first and stop after the first error (manual).
`d_type` (`DT_REG`, `DT_DIR`, ..., `DT_UNKNOWN`) is a BSD extension whose
value "possibly unknown": some filesystems always return `DT_UNKNOWN`;
`IFTODT`/`DTTOIF` convert against `st_mode` bits. `scandir` selects entries
through `sel`, mallocs the array plus copies, sorts via `cmp`, and returns
the entry count or -1; `alphasort` is `strcoll` over `d_name` and
`versionsort` uses `strverscmp` (manual).

## Gotchas and portability

- `readdir_r` is deprecated by the manual itself (no `NAME_MAX` bound on
  callers, ENAMETOOLONG on long names) and `readdir.3` recommends `readdir`
  with external synchronization over it.
- `d_reclen` is undefined under `readdir`; it only means something when
  walking `getdents64` buffers (manual, *Directory Entries*).
- The stream interface is not AS-Safe and unusable after `vfork`; the manual
  offers `getdents64` for those contexts (Linux-specific, declared in
  `dirent.h`).
- musl 1.2.5: `src/dirent/opendir.c` opens `O_RDONLY|O_DIRECTORY|O_CLOEXEC`
  and callocs the `DIR`; `readdir` refills a fixed buffer via
  `SYS_getdents`; `scandir` copies entries by `d_reclen` and restores
  `errno`.

## References

- glibc manual: `filesys.texi`, nodes *Directory Entries*, *Opening a
  Directory*, *Reading/Closing Directory*, *Scanning Directory Content*,
  *Low-level Directory Access*
- man3: `opendir.3`, `readdir.3`, `readdir_r.3`, `scandir.3`, `versionsort.3`
- headers: `/usr/include/dirent.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
