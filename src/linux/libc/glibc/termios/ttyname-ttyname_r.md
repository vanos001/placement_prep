# `ttyname` / `ttyname_r` (3) - glibc

> Split from the chapter *glibc: Low-Level Terminal Interface* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `unistd.h` (no feature-test gate) |
| Standards | POSIX.1-2001, 4.2BSD |
| Exported | `ttyname@@GLIBC_2.2.5`, `ttyname_r@@GLIBC_2.2.5` (weak) (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe race:ttyname (`ttyname`), MT-Safe (`ttyname_r`) (`ttyname(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-ttyname, GLIBC-ttyname_r |

## Declaration and gates

```c
#include <unistd.h>

char *ttyname(int fd);
int ttyname_r(int fd, char *buf, size_t buflen);
```

Both sit in the unconditional region of `/usr/include/unistd.h` (lines
797-805), next to `isatty` (line 812, documented in the sibling page
[isatty](../stdio/isatty.md)). No feature-test gate is needed.

## Semantics

`ttyname` returns the null-terminated pathname of the terminal open on
`fd`, or NULL on error (for example when `fd` is not a terminal); the
pointer may refer to static data overwritten by the next call.
`ttyname_r` stores the same pathname in `buf` of `buflen` bytes,
returning 0 on success and an error number on failure (`ttyname(3)`).
The lookup is done by matching `fd`'s device against `/dev` entries, so
it reflects the current mount namespace, not a property of the file
description.

## Errors

`ttyname`: `EBADF` (bad descriptor), `ENOTTY` (not a terminal), `ENODEV`
(slave pty whose pathname cannot be found). `ttyname_r` adds `ERANGE`
when `buflen` is too small (`ttyname(3)` ERRORS).

## Gotchas and portability

- `ttyname` is the only thread-unsafe form; `ttyname_r` exists exactly
  because of the static buffer. glibc also fortifies `ttyname_r`
  (`__fortified_attr_access` in the header).
- Mount-namespace trap (`ttyname(3)` NOTES): a process keeping a pty
  descriptor open across a switch to a namespace with a different
  `/dev/ptmx` may find a same-named but different device; both
  functions then return failure with `ENODEV`.
- The name is only useful if the device node exists; a missing
  `/dev` entry yields `ENODEV` even though the terminal works.
- musl 1.2.5: both present unconditionally
  (`musl src/unix/ttyname.c`).

## References

- glibc manual: `terminal.texi` (terminal identification)
- man3: `ttyname(3)`; man4: `pts(4)`
- headers: `/usr/include/unistd.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
