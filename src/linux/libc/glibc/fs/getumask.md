# `getumask` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Source-limited:
> declared on Linux glibc, implemented on GNU/Hurd only.

| Field | Value |
|---|---|
| Header | `sys/stat.h` (under `__USE_GNU`) |
| Standards | GNU extension, "only available under the GNU Hurd" (manual, header comment) |
| Exported | NOT exported by glibc 2.41 (nm negative check: zero `getumask` symbols in `libc.so.6`) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual safety annotations; the point of the function is reentrancy) |
| Ledger ID | GLIBC-getumask |

## Declaration and gates

```c
#include <sys/stat.h>

mode_t getumask(void);    /* __USE_GNU */
```

Declared at `/usr/include/x86_64-linux-gnu/sys/stat.h` lines 384-386
inside `#ifdef __USE_GNU`, with the header comment "Get the current
umask value without changing it. This function is only available
under the GNU Hurd." The manual (filesys.texi, *Assigning File
Permissions*) tags it `@standards{GNU, sys/stat.h}` and repeats the
Hurd-only restriction.

## Semantics

Returns the calling process's file creation mask without modifying it.
It exists because the only POSIX way to read the mask is the
round-trip `mode_t old = umask(0); umask(old);` -- two calls with a
window in between. The manual recommends `getumask` on GNU/Hurd as the
reentrant alternative and ships the portable two-step `read_umask`
example for everywhere else (*Setting Permissions*).

## Gotchas and portability

- On Linux the declaration compiles but the symbol does not exist:
  `nm -D /lib/x86_64-linux-gnu/libc.so.6` finds no `getumask`
  (negative check recorded), so linking fails at runtime resolution.
  Code using it must be guarded for Hurd only.
- The Linux-native read alternatives: the atomic-ish
  `umask(0)`/restore pair, or a read-only peek at the `Umask` field of
  `/proc/self/status`, available since Linux 4.7 (`umask.2` NOTES).
- The two-step read is itself racy in multithreaded programs because
  another thread can create files between the two calls
  (`umask.2` NOTES) -- see [umask.md](umask.md) for the full story.
- musl 1.2.5: no `getumask` anywhere in the tree (rg negative over
  `include/` and `src/`); `umask` is a bare `SYS_umask` wrapper
  (`src/stat/umask.c`).

## References

- glibc manual: `filesys.texi`, node *Assigning File Permissions*
  (the `umask`/`getumask` pair)
- headers: `/usr/include/x86_64-linux-gnu/sys/stat.h` lines 384-386
- symbols: `nm -D --with-symbol-versions libc.so.6` (negative result
  is the finding)
