# getunwind(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (IA-64 only) |
| Since (kernel) | 2.4.8 (syscalls(2): "IA-64 only; deprecated") |
| Man page | man2/getunwind.2 (man-pages 6.19 HTML set, fetched 2026-10-17): "Note: this system call is obsolete" |
| glibc wrapper | none -- invoked via syscall(2) per the man page SYNOPSIS |
| Aliases covered | none |
| Ledger ID | SC-getunwind |

## Purpose

getunwind() copied the kernel's call-frame unwind data -- the tables describing the gate page (kernel code mapped into user space on IA-64, i.e. thesyscall/vDSO equivalent) -- into a caller buffer, returning the size of the data (getunwind.2, DESCRIPTION). Unwinders (libunwind, debuggers, exception machinery) needed it to trace through the gate page's frames.

## Synopsis

```c
#include <linux/unwind.h>
#include <sys/syscall.h>
#include <unistd.h>
[[deprecated]] long syscall(SYS_getunwind, void buf[size], size_t size);
```

## Arguments and behavior

`buf`/`size` describe the destination buffer; data is copied only when `size` is at least the unwind-data size and `buf` is non-NULL -- otherwise the call still succeeds and returns the required size, a pure probe (getunwind.2, DESCRIPTION). The payload begins with an unwind table (u64 start / u64 end / info pointer triples per function) followed by the associated unwind information records (getunwind.2, DESCRIPTION).

## Return value and errors

Returns the size of the unwind data; -1 with EFAULT when the buffer cannot hold it (getunwind.2, RETURN VALUE/ERRORS).

## Flags and constants

None.

## Security and notes

The modern route is the vDSO -- the man page HISTORY says so verbatim: "The modern way to obtain the kernel's unwind data is via the vdso(7)" (getunwind.2, HISTORY). Interview angle: getunwind is the IA-64-specific answer to "how do you stack-trace through kernel-mapped user pages", the problem x86 solves with the vsyscall/vDSO page's own DWARF tables. Cross-reference: [getauxval(3) topics in the auxv page](../sched-misc/getcpu.md), [uname](uname.md).

## References

- https://man7.org/linux/man-pages/man2/getunwind.2.html
- man-pages syscalls(2) (2.4.8, IA-64 only, deprecated)
