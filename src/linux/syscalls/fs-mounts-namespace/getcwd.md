# getcwd(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 79 / i386 183 / arm64-generic 17 / arm32 183 |
| Since (kernel) | 2.2 (ledger and hub; getcwd.3 NOTES state the syscall has been available since 2.1.92) |
| Man page | man2/getcwd.2 is a roff `.so` alias of man3/getcwd.3 (cached, 2021-03-22) |
| glibc wrapper | Yes; `getcwd()` in `<unistd.h>` (POSIX.1-2001); plus `getwd()` (removed from POSIX.1-2008) and `get_current_dir_name()` (`_GNU_SOURCE`) |
| Aliases covered | none (getwd / get_current_dir_name are libc functions, not syscall aliases) |
| Ledger ID | SC-getcwd |

## Purpose

`getcwd()` places an absolute, null-terminated pathname of the calling
process's current working directory into the caller-supplied buffer. It is the
syscall behind the C library's `getcwd(3)`, `getwd(3)` and
`get_current_dir_name(3)`.

## Synopsis

    #include <unistd.h>
    char *getcwd(char *buf, size_t size);

    /* libc layer only: */
    char *getwd(char *buf);                  /* deprecated */
    char *get_current_dir_name(void);        /* _GNU_SOURCE */

## Arguments and behavior

`buf` points to a buffer of `size` bytes that receives the path including the
terminating null byte. If the path plus null byte exceeds `size`, the call
fails with `ERANGE` and the application must retry with a larger buffer. As a
glibc extension to POSIX.1-2001, a NULL `buf` makes the library allocate the
buffer with `malloc(3)` (of `size` bytes, or as large as needed when `size`
is zero); the caller must `free(3)` it. `get_current_dir_name()` consults the
`PWD` environment variable when it is correct; `getwd()` requires a
`PATH_MAX`-sized buffer and is marked LEGACY -- use `getcwd()`.

## Return value and errors

The libc functions return `buf` (or the allocated buffer) on success and NULL
on error: `EACCES` (read/search permission denied -- only possible on Linux
via the generic fallback implementation), `EFAULT` (bad `buf`), `EINVAL`
(`size` is zero while `buf` is not NULL; `getwd()` with NULL `buf`),
`ENAMETOOLONG` (`getwd()`: path exceeds `PATH_MAX`), `ENOENT` (the working
directory has been unlinked), `ENOMEM`, `ERANGE` (buffer too small). The
contents of `buf` are undefined on error.

## Flags and constants

None; the syscall takes exactly the two arguments shown above.

## Security and notes

The man page recommends saving the current location by opening "." and using
[fchdir](chdir.md) later -- faster and more reliable than caching a path
string, and immune to renames and `PATH_MAX` limits. `PATH_MAX` is not a
compile-time constant and may depend on the filesystem
(`pathconf(3)`). Companion navigation calls: [chdir.md](chdir.md),
[chroot.md](chroot.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/getcwd.2` -> `.so man3/getcwd.3`
- Online: https://man7.org/linux/man-pages/man3/getcwd.3.html
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (79), `syscall_32.tbl` (183),
  `syscall_generic.tbl` (17)
