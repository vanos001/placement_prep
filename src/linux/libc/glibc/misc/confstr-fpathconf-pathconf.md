# `confstr` / `pathconf` / `fpathconf` (3) - glibc

> Split from the ledger chapter *pathconf/confstr* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `unistd.h` (`pathconf` lines 633-634, `fpathconf` line 637, `confstr` lines 644-645 under `__USE_POSIX2`, lines 642-646; `_PC_*`/`_CS_*` constants from `bits/confname.h`, included at line 630) |
| Standards | POSIX.1-2001 (`pathconf`, `fpathconf`); POSIX.2, POSIX.1-2001 (`confstr`; man gates `_POSIX_C_SOURCE >= 2 || _XOPEN_SOURCE`) |
| Exported | `confstr@@GLIBC_2.2.5`, `fpathconf@@GLIBC_2.2.5`, `pathconf@@GLIBC_2.2.5` (nm marks `pathconf`/`fpathconf` `W`, interposable), fortified `__confstr_chk@@GLIBC_2.4` (host glibc 2.41) |
| Thread-safety | MT-Safe all (`confstr(3)`, `fpathconf(3)` ATTRIBUTES); manual safety notes for `pathconf`/`fpathconf` carry AS/AC caveats (`conf.texi` lines 1283, 1314) |
| Ledger ID | GLIBC-confstr, GLIBC-fpathconf, GLIBC-pathconf |

## Declaration and gates

```c
#include <unistd.h>

long int pathconf (const char *path, int name);
long int fpathconf (int fd, int name);
size_t confstr (int name, char *buf, size_t len);   /* __USE_POSIX2 */
```

`pathconf`/`fpathconf` are declared unconditionally (lines 633-637);
`confstr` only when `__USE_POSIX2` is in effect (`_POSIX_C_SOURCE >= 2`
or `_XOPEN_SOURCE`, `confstr(3)` synopsis). The `name` selectors come
from `bits/confname.h` (multiarch path on Debian): `_PC_LINK_MAX` at
line 26 through `_PC_2_SYMLINKS` at line 66; `_CS_PATH` at line 541,
`_CS_GNU_LIBC_VERSION` at line 548, `_CS_GNU_LIBPTHREAD_VERSION` at
line 550.

## Semantics

`confstr` reads a string-valued system parameter into `buf`; it returns
the full length including the terminating NUL, so a return value `>=
len` means truncation, `0` with `EINVAL` means invalid `name` (`confstr(3)`,
manual *String-Valued Parameters*). Documented values: `_CS_PATH`
(default utility search path) and the glibc-specific
`_CS_GNU_LIBC_VERSION` / `_CS_GNU_LIBPTHREAD_VERSION` (`confstr(3)`).
`pathconf`/`fpathconf` answer the same question for a file (`path`) or
an open descriptor (`fd`), with `_PC_*` selectors such as
`_PC_LINK_MAX`, `_PC_NAME_MAX`, `_PC_PATH_MAX`, `_PC_PIPE_BUF`,
`_PC_CHOWN_RESTRICTED` (`fpathconf(3)`). A `-1` return means either an
error (errno set) or an indeterminate limit (errno unchanged); the
manual calls clearing `errno` to 0 before the call the only robust
usage (`conf.texi` lines 1294-1300).

## Gotchas and portability

- `_PC_*` answers are per-file/per-filesystem on Linux: glibc implements
  some via `statfs` and may read `/proc/mounts` or
  `/proc/sys/fs/xfs/restrict_chown` (manual source comments,
  `conf.texi` lines 1284-1287).
- Some returned values may be huge and are not suitable for allocating
  memory (`fpathconf(3)` NOTES).
- The man page FIXMEs note many more `_PC_*`/`_CS_*` selectors exist in
  `bits/confname.h` than the pages document (`confstr(3)`, `fpathconf(3)`).
- musl 1.2.5 declares all three in `unistd.h` (lines 131-134) with the
  same POSIX semantics.

## Errors

- `confstr`: `EINVAL` invalid `name`.
- `pathconf`: `EACCES`, `ELOOP`, `ENAMETOOLONG`, `ENOENT`, `ENOTDIR`,
  `EINVAL` (`fpathconf(3)` ERRORS).
- `fpathconf`: `EBADF` bad descriptor, `EINVAL`.

## References

- glibc manual: `conf.texi`, nodes *Using `pathconf`*, *String-Valued Parameters*
- man3: `confstr(3)`, `fpathconf(3)` (covers `pathconf(3)` via `.so` link)
- headers: `/usr/include/unistd.h`, `/usr/include/x86_64-linux-gnu/bits/confname.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
