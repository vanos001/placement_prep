# getpagesize(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (Alpha and SPARC/SPARC64 slots only) |
| Since (kernel) | 2.0 |
| Man page | man2/getpagesize.2 (man-pages 6.19 HTML set, fetched 2026-10-17); the page itself explains its section: "This manual page is in section 2 because Alpha, SPARC, and SPARC64 all have a Linux system call getpagesize() though other architectures do not" |
| glibc wrapper | getpagesize(3) W @@GLIBC_2.2.5 (nm -D, glibc 2.41) -- on x86_64 it answers from a constant/auxv, not a syscall |
| Aliases covered | none |
| Ledger ID | SC-getpagesize |

## Purpose

getpagesize() returns the memory page size in bytes -- the fixed-length allocation and mapping unit used by mmap(2) (getpagesize.2, DESCRIPTION). Only Alpha and SPARC/SPARC64 ever had a kernel entry; every other architecture answers from the ELF auxiliary vector or a compile-time constant (getpagesize.2, VERSIONS).

## Synopsis

```c
#include <unistd.h>
int getpagesize(void);
```

Feature-test macros: `_DEFAULT_SOURCE` under glibc >= 2.20 (getpagesize.2, SYNOPSIS).

## Arguments and behavior

No arguments. The man page's core guidance: do not hard-code the result, "neither as a literal nor using the PAGE_SIZE macro, because some architectures support multiple page sizes" (getpagesize.2, VERSIONS) -- the same rule that later forced [mmap](../memory/mmap.md) to gain huge-page-capable flavors.

## Return value and errors

Returns the page size in bytes (getpagesize.2, DESCRIPTION); no error returns are documented for the library form.

## Flags and constants

None.

## Security and notes

History worth quoting in interviews: SUSv2 marked getpagesize() LEGACY and POSIX.1-2001 removed it (getpagesize.2, HISTORY); glibc 2.0 famously "returned a constant even on architectures with multiple page sizes" (HISTORY) -- the exact bug class the auxv approach fixes. Modern replacements: sysconf(_SC_PAGESIZE) or getauxval(AT_PAGESZ). Cross-reference: [mmap](../memory/mmap.md), [mprotect](../memory/mprotect.md), [msync](../memory/msync.md).

## References

- https://man7.org/linux/man-pages/man2/getpagesize.2.html
- man-pages syscalls(2) ("Alpha, SPARC/SPARC64 only")
- worklog: wrapper symbol getpagesize W @@GLIBC_2.2.5 verified with nm -D (2026-10-17)
