# `mtrace` / `muntrace` - glibc

> Split from the chapter *glibc: Virtual Memory Allocation And Paging* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `mcheck.h` (no feature-test gate in the header) |
| Standards | GNU extension, "generally not available on other systems" (mtrace.3 CONFORMING TO; manual, *Tracing malloc*) |
| Exported | `mtrace@@GLIBC_2.2.5`, `muntrace@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe (mtrace.3 ATTRIBUTES; the manual's finer marking is `env race:mtrace const:malloc_hooks init` for `mtrace`) |
| Ledger ID | GLIBC-mtrace, GLIBC-muntrace |

## Declaration and gates

```c
#include <mcheck.h>

void mtrace(void);
void muntrace(void);
```

Declared unconditionally at `/usr/include/mcheck.h` lines 56-57; no
feature-test macro is involved.

## Semantics

`mtrace` installs hook functions around the memory-allocation functions
(`malloc`, `realloc`, `memalign`, `free`) that record a trace of every
allocation and deallocation, to find leaks and frees of unallocated
memory (mtrace.3). Behavior is driven by the environment:

- `MALLOC_TRACE` names the log file. `mtrace` opens it truncated; on
  failure -- unset, unwritable, invalid -- no hooks are installed and
  nothing changes.
- In set-user-ID / set-group-ID programs `MALLOC_TRACE` is ignored.
- `muntrace` uninstalls the hooks and closes the log; it does nothing if
  `mtrace` never succeeded.

The log is textual but machine-oriented; the glibc-distributed Perl
script `mtrace(1)` turns it into a leak report (address, size, caller).
Compile the traced program with `-g` so line numbers resolve (mtrace.3
NOTES); the script's line numbers can be off by a line (BUGS).

## Gotchas and portability

- Since glibc 2.34 tracing is disabled in the main libc and requires
  `LD_PRELOAD=libc_malloc_debug.so` (manual, *Tracing malloc*; NEWS 2.34:
  mtrace "disabled by default in the main C library").
- Normal usage calls `mtrace` once at startup and never calls
  `muntrace` (mtrace.3 NOTES).
- Tracing costs performance on every allocation; do not ship it enabled.
- Replacements: valgrind, ASan/LSan.
- musl 1.2.5: absent -- no `mcheck.h`, no `mtrace`/`muntrace` symbols,
  nothing in `src/` (searched); glibc-only debugging aid.

## References

- man3: `mtrace.3` (covers `muntrace`)
- glibc manual: `memory.texi`, node *Tracing malloc*; NEWS (2.34 hooks removal)
- headers: `/usr/include/mcheck.h` (lines 56-57)
- symbols: `nm -D --with-symbol-versions libc.so.6`
