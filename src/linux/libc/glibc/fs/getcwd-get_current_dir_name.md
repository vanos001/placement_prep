# `getcwd` / `get_current_dir_name` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [getcwd(2)](../../../syscalls/fs-mounts-namespace/getcwd.md); directory
> changing side: [chdir-fchdir.md](chdir-fchdir.md).

| Field | Value |
|---|---|
| Header | `unistd.h` (both) |
| Standards | POSIX.1-2001 (`getcwd`; behavior with NULL `buf` left unspecified); GNU extension (`get_current_dir_name`) |
| Exported | `getcwd@@GLIBC_2.2.5`, `get_current_dir_name@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `getcwd`: MT-Safe but AS-Unsafe (heap), AC-Unsafe (mem, fd) -- may malloc/realloc/free and open directories as fallback (manual, `getcwd(3)`); `get_current_dir_name`: MT-Safe env, same heap caveats |
| Ledger ID | GLIBC-getcwd, GLIBC-get_current_dir_name |

## Declaration and gates

```c
#include <unistd.h>

char *getcwd(char *buf, size_t size);
char *get_current_dir_name(void);       /* __USE_GNU */
```

`getcwd` is declared ungated (`/usr/include/unistd.h` line 531);
`get_current_dir_name` under `#ifdef __USE_GNU` (lines 536-538). The
deprecated `getwd` (BSD, removed by POSIX.1-2008) lives nearby under
`(XOPEN_EXTENDED && !XOPEN2K8) || MISC` and is only a group-page
mention here.

## Semantics

`getcwd` copies an absolute pathname of the current working directory
into `buf`, failing with `ERANGE` when it needs more than `size` bytes
including the terminator. glibc extends POSIX: `buf == NULL` mallocs a
buffer of `size` bytes (or exactly as needed when `size` is 0); the
caller frees it (`getcwd(3)`, manual *Working Directory*).
`get_current_dir_name` is `getcwd(NULL, 0)` plus a `PWD` shortcut: if
`PWD` is set and stat-identical to `.`, its (possibly symlink-laden)
value is returned instead of the resolved path (manual: the visible
difference when `PWD` traverses symlinks). musl's implementation makes
the stat-check explicit (`src/misc/get_current_dir_name.c`).

## Gotchas and portability

- Linux offers the `getcwd` syscall (since 2.1.92) but caps it at
  `PATH_MAX` (page size before 3.12); past that the library falls back
  to a slower parent-walking implementation (`getcwd.3`, C
  library/kernel differences).
- Since Linux 2.6.36 the syscall can prefix "(unreachable)" when cwd
  is outside the root (chroot or mount-namespace games); glibc < 2.27
  propagated that non-absolute string, glibc >= 2.27 fails with
  `ENOENT` (`getcwd.3` BUGS). Treat returned paths starting with `(`
  as hostile.
- NULL-buf reliance is non-portable; POSIX.1-2001 leaves it
  unspecified. The faster save/restore idiom is `open(".")` +
  `fchdir` (`getcwd.3` NOTES).
- musl 1.2.5: `getcwd` is a single `SYS_getcwd` call with no
  fallback -- `EINVAL` for `size == 0` with non-NULL `buf`, `ENOENT`
  when the kernel answer is not absolute, `strdup` when `buf == NULL`
  (`src/unistd/getcwd.c`); `get_current_dir_name` is provided.

## Errors

`EINVAL` (zero size with non-NULL buf), `ERANGE` (buffer too small),
`EACCES`, `ENOENT` (cwd unlinked, or the unreachable case on glibc >=
2.27), `ENOMEM`, `EFAULT` (`getcwd.3`).

## References

- glibc manual: `filesys.texi`, node *Working Directory*
- man3: `getcwd.3` (covers `getwd`, `get_current_dir_name`)
- headers: `/usr/include/unistd.h` lines 531-538
- symbols: `nm -D --with-symbol-versions libc.so.6`
