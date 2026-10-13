# brk(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 12 / 45 / 214 / 45 |
| Since (kernel) | 1.0 |
| Man page | man2/brk.2 (cached, dated 2021-03-22) |
| glibc wrapper | yes, in libc; exposed since glibc 2.19 via _DEFAULT_SOURCE (earlier: _BSD_SOURCE || _SVID_SOURCE rules) |
| Aliases covered | none (sbrk is a libc function, not a syscall alias) |
| Ledger ID | SC-brk |

## Purpose

`brk()` sets the location of the **program break**: the first address after
the process's uninitialized data segment (BSS). Raising the break allocates
memory; lowering it releases memory. It is the oldest Linux allocation
primitive (since 1.0, inherited from 4.3BSD) and what classic `malloc(3)`
arena implementations are built on. The man page says to avoid
`brk()`/`sbrk()` in new code and use `malloc(3)`. Domain index:
[memory hub](overview.md).

## Synopsis

```c
#include <unistd.h>
int brk(void *addr);
void *sbrk(intptr_t increment);   /* libc only; no syscall */
```

## Arguments and behavior

`addr` is the requested new break; it succeeds only when the value is
reasonable, memory is available, and the process stays within its maximum
data size (`RLIMIT_DATA`, `setrlimit(2)`). `sbrk(increment)` moves the break
relatively; `sbrk(0)` reports the current break. On Linux `sbrk()` is a pure
library function that calls the `brk()` syscall and keeps bookkeeping so it
can return the old break.

## Return value and errors

The **raw syscall** returns the new break on success and the *current*
(unchanged) break on failure -- there is no -1 value. The **glibc wrapper**
compares the result against `addr` and produces the documented 0 on success
/ -1 with `errno` convention. Only `ENOMEM` is documented (limit exceeded,
out of memory). `sbrk()` returns the previous break, or `(void *) -1` with
`errno` = `ENOMEM` on failure.

## Flags and constants

None; one pointer argument, no flags. Conforming to 4.3BSD; SUSv1, marked
LEGACY in SUSv2, removed in POSIX.1-2001.

## Security and notes

- `RLIMIT_DATA` caps how far the break may grow (man page "maximum data
  size" check).
- Modern glibc malloc uses `brk()` only for the main arena and `mmap(2)`
  elsewhere, so a failed `brk()` does not mean the process is out of memory.
- Portability trap: code checking `brk() == -1` on the raw syscall (or via
  `syscall(2)`) is wrong -- only the glibc wrapper yields -1.
- The `sbrk()` argument type varies across systems (`int`, `ssize_t`,
  `ptrdiff_t`, `intptr_t`); glibc uses `intptr_t`.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/brk.2` (RETURN
  VALUE, "C library/kernel differences", CONFORMING TO).
- Numbers cross-checked against cached `syscall_64.tbl` (12),
  `syscall_32.tbl` (45), `syscall_generic.tbl` (214), `syscall_arm.tbl`
  (45); hub: [overview](overview.md).
