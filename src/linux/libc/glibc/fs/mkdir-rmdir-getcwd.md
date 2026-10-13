# `mkdir` / `rmdir` / `getcwd` (3) - glibc

> Per-function page for directory creation, removal and the working
> directory in the glibc File System Interface family; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sys/stat.h` (`mkdir`); `unistd.h` (`rmdir`, `getcwd`, `getwd`, `get_current_dir_name`) |
| Standards | POSIX.1 (`mkdir`, `rmdir`, `getcwd`), POSIX.1-2008 (`mkdirat`), BSD (`getwd`, deprecated), GNU (`get_current_dir_name`) |
| Exported | `mkdir`/`rmdir`/`getcwd`/`getwd`/`get_current_dir_name` `@@GLIBC_2.2.5`; `mkdirat` `@@GLIBC_2.4` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe on `mkdir`/`rmdir`/`chdir`/`fchdir` (manual annotations); `getcwd` AS-Unsafe (heap) AC-Unsafe (mem, fd) since it may allocate |
| Ledger ID | GLIBC-mkdir, GLIBC-rmdir, GLIBC-getcwd (researched), GLIBC-get_current_dir_name (researched), GLIBC-getwd (triage row) |

## Declaration and gates

```c
#include <sys/stat.h>
#include <unistd.h>

int mkdir(const char *path, mode_t mode);           /* mode minus umask */
int mkdirat(int fd, const char *path, mode_t mode); /* __USE_ATFILE */
int rmdir(const char *path);
char *getcwd(char *buf, size_t size);               /* __wur */
char *getwd(char *buf);                             /* deprecated, BSD */
char *get_current_dir_name(void);                   /* __USE_GNU */
```

## Semantics

`mkdir` creates a new, empty directory whose permissions are `mode` as
modified by the umask (manual, *Creating Directories*; `EEXIST` if the name
is taken, `EMLINK` on full parent, `ENOSPC`, `EROFS`). `rmdir` deletes a
directory that contains only `.` and `..`; the not-empty error arrives as
`ENOTEMPTY` or `EEXIST`, and the manual notes GNU systems always use
`ENOTEMPTY`. `getcwd` stores an absolute name for the working directory in
`buf`/`size`; glibc additionally accepts `buf == NULL` and allocates the
buffer with `malloc` (size zero means "as large as necessary"), returning
`buffer` or NULL with `EINVAL` (size zero, non-NULL buf) and `ERANGE`
(manual). `chdir`/`fchdir` switch the working directory and are the only
process-wide, not per-thread, part of this family (manual, *Working
Directory*).

## Gotchas and portability

- `getwd` has no size parameter and needs `PATH_MAX` bytes; the manual marks
  it deprecated for exactly that reason.
- `get_current_dir_name` consults `$PWD` first, so the result may differ
  from `getcwd` when `PWD` keeps symlinks unresolved (manual).
- The working directory is a process-wide resource, so one thread's `chdir`
  affects all threads; the manual offers descriptor-relative `*at` access
  (node *Descriptor-Relative Access*) as the thread-safe alternative.
- musl 1.2.5: `src/stat/mkdir.c` is a `mkdir`/`mkdirat` syscall call;
  `src/unistd/getcwd.c` issues `SYS_getcwd`.

## References

- glibc manual: `filesys.texi`, nodes *Working Directory*, *Creating
  Directories*, *Deleting Files*
- man2: `mkdir.2`; man3 `getcwd.3`
- headers: `/usr/include/x86_64-linux-gnu/sys/stat.h`, `/usr/include/unistd.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
