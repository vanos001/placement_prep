# `mcheck` / `mtrace` / `memusage` (3) - glibc

> Per-function page for the malloc debugging helpers; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. These hook the
> allocator described on the malloc pages; the statistics knobs are on
> [mallinfo3-deprecated-malloc_usable_size.md](./mallinfo3-deprecated-malloc_usable_size.md).

| Field | Value |
|---|---|
| Header | `mcheck.h` (`mcheck`, `mcheck_pedantic`, `mcheck_check_all`, `mprobe`, `mtrace`, `muntrace`, `enum mcheck_status`) |
| Standards | GNU extensions ("generally not available on other systems", manual) |
| Exported | `mcheck`, `mcheck_pedantic`, `mprobe`, `mtrace`, `muntrace` all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe race:mcheck / const:malloc-hooks (manual: hooks manage an unguarded list, designed for single-threaded fully-synchronous operation); `mtrace` MT-Unsafe env/race:mtrace |
| Ledger ID | GLIBC-mcheck, GLIBC-mtrace (researched rows); mcheck_pedantic/mprobe/muntrace grouped into them |

## Declaration and gates

```c
#include <mcheck.h>

int mcheck(void (*abortfn)(enum mcheck_status status));  /* 0 or -1 (late) */
int mcheck_pedantic(void (*abortfn)(enum mcheck_status));
void mcheck_check_all(void);
enum mcheck_status mprobe(void *pointer); /* MCHECK_DISABLED/OK/HEAD/
                                             TAIL/FREE */
void mtrace(void);
void muntrace(void);
```

## Semantics

`mcheck` asks malloc to run occasional consistency checks that catch, for
example, writes past the end of a block; it must run before the first
allocation, so it returns -1 when called too late and does nothing
(manual, *Heap Consistency Checking*); the `-lmcheck` link option is the
manual's no-source-edit way in. `mprobe` re-checks one block on demand and
reports `MCHECK_HEAD`,
`MCHECK_TAIL` or `MCHECK_FREE` etc. `MALLOC_CHECK_` set to a non-zero value
below 4 selects a tolerant checking implementation; it requires preloading
`libc_malloc_debug` via `LD_PRELOAD` - "Without this preloaded library,
setting MALLOC_CHECK_ will have no effect" (manual). NEWS 2.34 records the
change: "Debugging features in malloc such as the MALLOC_CHECK_
environment variable (or the glibc.malloc.check tunable), mtrace() and
mcheck() have now been disabled by default in the main C library",
preloading `libc_malloc_debug.so` to get them back; it is disabled for
SUID/SGID binaries. `mtrace` honors
`MALLOC_TRACE` as a trace file name (truncated if it exists; no-op when
unset or unwritable or SUID/SGID), installs hooks for malloc/realloc/free
and logs every call; `muntrace` removes them (manual, *Tracing malloc*).

## Gotchas and portability

- The traced stream includes library-internal allocations, which is why the
  manual advises calling `mtrace` first thing and never `muntrace`, and
  guarding the call in debug builds only.
- The trace file is machine-readable; the `mtrace` perl script that
  post-processes it ships with glibc, not with the manual (man3
  `mtrace.3` shows the `mtrace ./prog $MALLOC_TRACE` usage).
- `memusage`: no manual node and no man3 page exist in the cached sources;
  the name is kept in this page's title per the family brief, with no
  behavior claims made here (unverified from cache).
- musl 1.2.5: none of mcheck/mtrace/memusage exist (no `mcheck.h`, no
  debug hooks in `src/malloc/`).

## References

- glibc manual: `memory.texi`, nodes *Heap Consistency Checking*,
  *Allocation Debugging*, *Tracing malloc*, *Using the Memory Debugger*;
  NEWS 2.34 (debug features disabled by default, libc_malloc_debug.so)
- man3: `mcheck.3`, `mtrace.3`
- headers: `/usr/include/mcheck.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
