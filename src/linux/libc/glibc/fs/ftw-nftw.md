# `ftw` / `nftw` (3) - glibc

> Per-function page for the file-tree walkers of the glibc File System
> Interface; see the [method page](../../../interface-encyclopedia.md) and
> the [glibc ledger](../../ledger-glibc.md) for coverage status. Not related
> to the fts(3) family, which glibc does not provide (man3 carries a BSD
> `fts.3` page; no glibc manual node exists for it).

| Field | Value |
|---|---|
| Header | `ftw.h` |
| Standards | SVID (`ftw`), XPG4.2 (`nftw`), Unix98 (`ftw64`, `nftw64`); POSIX.1-2008 marks `ftw` obsolete (man `ftw.3`, CONFORMING TO) |
| Exported | `ftw@@GLIBC_2.2.5`; `nftw@@GLIBC_2.3.3` with an `nftw@GLIBC_2.2.5` compat alias (nm, host glibc 2.41) |
| Thread-safety | MT-Safe; `nftw` with `FTW_CHDIR` is MT-Unsafe race:cwd / AS-Unsafe cwd / AC-Unsafe cwd (manual safety annotations); each call uses a private search tree |
| Ledger ID | GLIBC-ftw, GLIBC-nftw (both documented, grouped) |

## Declaration and gates

```c
#include <ftw.h>

int ftw(const char *path,            /* callback: (path, stat*, typeflag) */
        int (*fn)(const char *, const struct stat *, int), int descriptors);
int nftw(const char *path,
         int (*fn)(const char *, const struct stat *, int, struct FTW *),
         int descriptors, int flags);
/* struct FTW: int base (name offset into path), int level (depth, 0-based) */
```

`FTW_F`, `FTW_D`, `FTW_DNR`, `FTW_NS` are unconditioned in `ftw.h`;
`FTW_SL` needs `__USE_MISC` or `__USE_XOPEN_EXTENDED`; `FTW_DP`/`FTW_SLN`
and the `FTW_PHYS`/`FTW_MOUNT`/`FTW_CHDIR`/`FTW_DEPTH` flags need
`__USE_XOPEN_EXTENDED`; `FTW_ACTIONRETVAL` plus the callback returns
`FTW_CONTINUE`/`FTW_STOP`/`FTW_SKIP_SUBTREE`/`FTW_SKIP_SIBLINGS` need
`__USE_GNU` (header; man `ftw.3` dates `FTW_ACTIONRETVAL` to glibc 2.3.3).

## Semantics

Both walkers call the callback for every item under `path` and below, at most
`descriptors` file descriptors used, and stop only when a callback returns
nonzero - that value becomes the return value; internal failures return -1
with `errno` (manual). `ftw` follows symbolic links and never reports an
item twice; a failed stat surfaces as `FTW_NS`. `nftw` adds: `FTW_PHYS`
(no link following; links become `FTW_SL`), `FTW_MOUNT` (same filesystem
only), `FTW_DEPTH` (children before the directory, reporting `FTW_DP`
instead of `FTW_D`), `FTW_CHDIR` (walk in each directory, restored on
return), and the GNU `FTW_ACTIONRETVAL` protocol for subtree and sibling
skipping (manual, *Working with Directory Trees*).

## Gotchas and portability

- The manual forbids leaving `ftw`/`nftw` via `setjmp`: allocated resources
  would leak; return nonzero instead.
- man `ftw.3` NOTES: results are unspecified if the callback does not
  preserve the working directory; and whether a dangling link gives
  `FTW_NS` or `FTW_SL` is implementation-defined.
- musl 1.2.5: `src/legacy/ftw.c` implements `ftw` as
  `nftw(path, fn, fd_limit, FTW_PHYS)` through a function-pointer cast
  (comment in source calls the extra-argument call undefined but working).

## References

- glibc manual: `filesys.texi`, node *Working with Directory Trees*
- man3: `ftw.3` (obsolete marking, `FTW_ACTIONRETVAL` since glibc 2.3.3)
- headers: `/usr/include/ftw.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
