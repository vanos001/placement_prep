# `mcheck` / `mprobe` - glibc

> Split from the chapter *glibc: Virtual Memory Allocation And Paging* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `mcheck.h` (no feature-test gate in the header -- the declarations are unconditional; `mcheck.3` shows plain `#include <mcheck.h>`) |
| Standards | GNU extension (mcheck.3 CONFORMING TO) |
| Exported | `mcheck@@GLIBC_2.2.5`, `mprobe@@GLIBC_2.2.5`, `mcheck_pedantic@@GLIBC_2.2.5`, `mcheck_check_all@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe `race:mcheck` `const:malloc_hooks` (mcheck.3 ATTRIBUTES, covers all four) |
| Ledger ID | GLIBC-mcheck, GLIBC-mprobe |

## Declaration and gates

```c
#include <mcheck.h>

int mcheck(void (*abortfunc)(enum mcheck_status mstatus));
int mcheck_pedantic(void (*abortfunc)(enum mcheck_status mstatus));
void mcheck_check_all(void);
enum mcheck_status mprobe(void *ptr);

/* mcheck.h lines 27-34 */
enum mcheck_status { MCHECK_DISABLED = -1, MCHECK_OK, MCHECK_FREE,
                     MCHECK_HEAD, MCHECK_TAIL };
```

No `__USE_GNU` / `__USE_MISC` wrapper: `mcheck.h` declares everything
unconditionally (`/usr/include/mcheck.h` lines 41-53).

## Semantics

`mcheck` installs debugging hooks for the `malloc` family that run heap
consistency checks: double frees and clobbered bookkeeping data in front
of a block are detected (mcheck.3). It must be called before the first
allocation; it returns 0 then, -1 if called too late (in which case it
does nothing). Linking with `-lmcheck` inserts an implicit
`mcheck(NULL)` early enough. On inconsistency, `abortfunc` is invoked
with the status; a NULL `abortfunc` means print to `stderr` and `abort`.
`mcheck_pedantic` re-checks every block on every allocation call (slow);
`mcheck_check_all` forces a sweep; `mprobe` checks one block on demand
and returns `MCHECK_DISABLED` if `mcheck` was never active, `MCHECK_OK`
when clean, else `MCHECK_HEAD` (prefix clobbered), `MCHECK_TAIL`
(suffix clobbered) or `MCHECK_FREE` (freed twice).

## Gotchas and portability

- Since glibc 2.34 the hooks are disabled in the main libc: mcheck needs
  `LD_PRELOAD=libc_malloc_debug.so` at runtime, or it silently does
  nothing (glibc manual, *Heap Consistency Checking*; NEWS 2.34).
- `MALLOC_CHECK_` (a `mallopt(3)` topic) detects the same error classes
  without relinking (mcheck.3 NOTES).
- Modern practice is ASan/valgrind; mcheck is a legacy tool.
- musl 1.2.5: absent -- no `mcheck.h`, no symbols anywhere in the tree.

## References

- man3: `mcheck.3` (covers `mprobe`, `mcheck_pedantic`, `mcheck_check_all`)
- glibc manual: `memory.texi`, node *Heap Consistency Checking*
- headers: `/usr/include/mcheck.h` (lines 27-53)
- symbols: `nm -D --with-symbol-versions libc.so.6`
