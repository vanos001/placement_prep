# `syscall` (2) - glibc

> Split from the chapter *glibc: System Calls* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `unistd.h` (declaration); `sys/syscall.h` for `SYS_*` numbers |
| Standards | BSD; glibc wrapper (gate `_DEFAULT_SOURCE`, formerly `_BSD_SOURCE`/`_SVID_SOURCE`) |
| Exported | `syscall@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | Not stated: `syscall(2)` carries no ATTRIBUTES table |
| Ledger ID | GLIBC-syscall |

## Declaration and gates

```c
#include <sys/syscall.h>   /* SYS_* constants -> <bits/syscall.h> */
#include <unistd.h>

long syscall(long number, ...);   /* /usr/include/unistd.h line 1091,
                                     inside __USE_MISC (lines 1080-1093) */
```

`/usr/include/x86_64-linux-gnu/sys/syscall.h` includes
`<bits/syscall.h>` (lines 27-29), which defines the per-arch `SYS_*`
constants.

## Semantics

`syscall` invokes the kernel system call with number `number`,
passing the remaining arguments through the architecture's ABI
registers, saving and restoring CPU registers around the call
(`syscall(2)`). It is the escape hatch for calls without a glibc
wrapper. The raw kernel convention leaks through: most calls return a
nonnegative value or a small negative error, and the wrapper
translates errors into -1 with `errno` set -- but the return type is
`long`, so callers must not assume `int` truncation semantics
(`syscall(2)` RETURN VALUE).

## Gotchas and portability

- Variadic promotion: arguments arrive as `long`s; on 32-bit
  architectures a 64-bit value may need manual splitting into an
  aligned register pair -- the man page's readahead-on-ARM-EABI
  example shows inserting a dummy argument (`syscall(2)` NOTES).
  glibc wrappers handle this per architecture; raw `syscall` does not.
- `SYS_*` numbers are architecture-specific; never hardcode them.
  New kernels add calls that old glibc wrappers lack -- that is the
  main legitimate use.
- `syscall` is variadic and `__THROW`-marked; it is not a
  cancellation point.
- Cross-reference: raw syscall coverage starts at the encyclopedia's
  syscall layer -- see [syscalls overview](../../../syscalls/overview.md)
  (from this directory: `../../../syscalls/overview.md`); e.g. the
  `getrandom` wrapper is documented alongside its raw call at
  `../../../syscalls/sched-misc/getrandom.md`.
- musl 1.2.5 provides `syscall` (`src/misc/syscall.c` plus per-arch
  assembly).

## References

- man2: `syscall(2)`, `syscalls(2)`
- headers: `/usr/include/unistd.h`,
  `/usr/include/x86_64-linux-gnu/sys/syscall.h`
- symbols: `nm -D libc.so.6`
- musl: `src/misc/syscall.c`
