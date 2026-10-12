# `brk` / `sbrk` - glibc

> Split from the chapter *glibc: Virtual Memory Allocation And Paging* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `unistd.h` lines 1063-1076, gated on `__USE_XOPEN_EXTENDED` (pre-XOPEN2K) or `__USE_MISC` |
| Standards | 4.3BSD; SUSv1, marked LEGACY in SUSv2, removed in POSIX.1-2001 (brk.2 CONFORMING TO) |
| Exported | `brk@@GLIBC_2.2.5` (W), `sbrk@@GLIBC_2.2.5` (W), plus the break global `__curbrk@@GLIBC_2.2.5` (B) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe / AS-safe / AC-safe (manual safety notes, memory.texi *Resizing the Data Segment*; no ATTRIBUTES table in brk.2) |
| Ledger ID | GLIBC-brk, GLIBC-sbrk |

## Declaration and gates

```c
#include <unistd.h>

/* unistd.h:1063 gate: (__USE_XOPEN_EXTENDED && !__USE_XOPEN2K) || __USE_MISC */
int brk(void *addr);                 /* unistd.h:1070 */
void *sbrk(intptr_t delta);          /* unistd.h:1076 */
```

## Semantics

The program break is the end of the heap's data segment. `brk(addr)` sets
the break to `addr`: zero on success, -1 with `ENOMEM` when the request
would collide with another segment or exceed the data-size limit; an
`addr` below the segment's low end has no effect and is counted as
success (brk.2; manual, *Resizing the Data Segment*). `sbrk(delta)` moves
the break by `delta` and returns the *previous* break -- i.e. the start
of the freshly allocated region when `delta > 0` -- or `(void *) -1` on
error; `sbrk(0)` reports the current break without changing it.

glibc's `brk` wrapper returns 0/-1, but the raw `brk` syscall returns the
new break on success -- a C library/kernel difference brk.2 spells out.
The wrapper keeps the break in the `__curbrk` global. Raw syscall page:
[brk](../../../syscalls/memory/brk.md).

## Gotchas and portability

- "Avoid using `brk` and `sbrk`" -- malloc(3) is the supported interface;
  malloc itself uses these (or `mmap`), and mixing raw `sbrk` with malloc
  corrupts the allocator's view of the heap (brk.2 NOTES).
- The `sbrk` argument type differs across systems (`int`, `ssize_t`,
  `ptrdiff_t`, `intptr_t`); glibc uses `intptr_t` (brk.2 NOTES).
- The break abstraction barely exists in modern mm implementations --
  malloc mostly `mmap`s -- so portable code should not observe heap growth
  through `sbrk(0)`.
- musl 1.2.5: both present (`include/unistd.h` lines 163-164,
  `src/linux/brk.c`); same semantics.

## Errors

`ENOMEM` for both: the request would overlap another segment or exceed
the process's data storage limit (brk.2, manual).

## References

- man2: `brk.2` (covers `sbrk`; `sbrk.2` is a `.so` link); man3 has no separate page
- glibc manual: `memory.texi`, node *Resizing the Data Segment*
- headers: `/usr/include/unistd.h` (lines 1063-1076)
- symbols: `nm -D --with-symbol-versions libc.so.6`
