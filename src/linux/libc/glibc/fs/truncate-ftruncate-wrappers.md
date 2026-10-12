# `truncate` / `ftruncate` (3) - glibc

> Per-function page for the file-size setters of the glibc File System
> Interface; see the [method page](../../../interface-encyclopedia.md) and
> the [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [truncate(2)](../../../syscalls/descriptors-io/truncate.md).

| Field | Value |
|---|---|
| Header | `unistd.h` |
| Standards | X/Open (`truncate`), POSIX.1 (`ftruncate`; "introduced in BSD Unix, ftruncate later added to POSIX.1", manual) |
| Exported | `truncate`/`truncate64`/`ftruncate`/`ftruncate64` all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual safety annotations) |
| Ledger ID | GLIBC-truncate, GLIBC-ftruncate (both researched rows) |

## Declaration and gates

```c
#include <unistd.h>

int truncate(const char *file, off_t length);
int ftruncate(int fd, off_t length);
/* _FILE_OFFSET_BITS == 64 remaps off_t and the calls to the *64 forms
   (manual, File Size node). */
```

## Semantics

`truncate` sets the size of the named file to `length`; if shorter, data at
the end is lost. The file must be writable by the user. If longer, holes are
added - the manual warns some systems instead leave the file unchanged, so
extension is not portable even though Linux extends with zeros
(manual, *File Size*). `ftruncate` works on an open descriptor, which must
be open for writing; POSIX leaves extension above the old size
implementation-defined, "no reliable way to increase the file size but ...
probably the fastest way" when it works (manual). Errors: `EACCES`
(directory or not writable), `EINVAL` (negative length), `EFBIG`, `EIO`,
`EPERM` (append-only or immutable file), `EINTR`, plus `EBADF` for
`ftruncate` (manual).

## Gotchas and portability

- Using these on anything but a regular file gives *undefined* results; on
  many systems the call "appears to succeed, without actually accomplishing
  anything" (manual). `ftruncate` additionally operates on POSIX shared
  memory objects where the system implements them (manual).
- The documented `mmap` recipe: a mapping has fixed size, so grow the file
  with `ftruncate` first, then remap with the new size (manual example
  context in *File Size*).
- Zero-fill-on-extension is the Linux behavior; the manual's hole language
  is the portable description, not a guarantee.
- musl 1.2.5: `src/unistd/truncate.c` and `src/unistd/ftruncate.c` are
  direct syscall calls.

## References

- glibc manual: `filesys.texi`, node *File Size* (truncate/ftruncate, 64-bit
  twins, error table)
- man2: `truncate.2`
- headers: `/usr/include/unistd.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
