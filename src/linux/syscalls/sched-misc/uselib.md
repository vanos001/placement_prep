# uselib(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 134 / 86 / -- / 86 |
| Since (kernel) | 1.0; available only with CONFIG_USELIB since 3.15 (uselib.2 HISTORY) |
| Man page | man2/uselib.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | not supported: no declaration in headers; uselib T @GLIBC_2.2.5 still exported by glibc 2.41 (nm -D) as the pre-2.23 leftover ABI (uselib.2, HISTORY) |
| Aliases covered | none |
| Ledger ID | SC-uselib |

## Purpose

uselib() loaded a shared library for the calling process: given a pathname, the load address came from the library file itself, and the binary could be any recognized format (uselib.2, DESCRIPTION). It is the a.out-era dynamic linking primitive -- in ancient libc versions, ld.so used uselib() to map the shared libraries named in the executable (uselib.2, HISTORY).

## Synopsis

```c
#include <unistd.h>
[[deprecated]] int uselib(const char *library);
```

## Arguments and behavior

One argument, the library pathname (uselib.2, DESCRIPTION). The kernel maps the library per its embedded load address -- which is why the call could only ever serve the a.out format's fixed-address model; ELF dynamic linking (mmap-backed segments, position independence) replaced it wholesale. Since 3.15 the call exists only under CONFIG_USELIB (uselib.2, HISTORY).

## Return value and errors

0 on success; -1 with errno (uselib.2, RETURN VALUE). Errors: everything open(2) and mmap(2) can return, plus EACCES (no read/execute permission on the library or search permission on the path), ENFILE (system-wide fd limit), ENOEXEC (not a recognized binary format) (uselib.2, ERRORS).

## Flags and constants

None.

## Security and notes

Fixed-address library loading is a textbook ASLR defeat and a textbook address-space-collision hazard -- which is why the ELF/mmap model won completely. The interface also let any process map executable content with the kernel's historical laxer checks, another reason it is disabled by default (CONFIG_USELIB). Interview angle: uselib() is the shortest possible answer to "how did Linux load shared libraries before ELF?" Cross-reference: [mmap](../memory/mmap.md), [open](../descriptors-io/open.md), [execve](../process/execve.md).

## References

- https://man7.org/linux/man-pages/man2/uselib.2.html
- man-pages syscalls(2)
- worklog: leftover glibc symbol uselib @GLIBC_2.2.5 verified with nm -D (2026-10-17)
