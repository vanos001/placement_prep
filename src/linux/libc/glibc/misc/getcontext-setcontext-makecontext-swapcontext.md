# `getcontext` / `setcontext` / `makecontext` / `swapcontext` (3) - glibc

> Split from the System V user-context machinery of the glibc interface encyclopedia into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `ucontext.h` |
| Standards | SUSv2, POSIX.1-2001; POSIX.1-2008 removed `makecontext`/`swapcontext` (obsolescent, portability cited) |
| Exported | `getcontext@@GLIBC_2.2.5`, `setcontext@@GLIBC_2.2.5`, `makecontext@@GLIBC_2.2.5`, `swapcontext@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe `race:ucp` (`getcontext`/`setcontext`/`makecontext`); `race:oucp race:ucp` (`swapcontext`) (`getcontext(3)`, `makecontext(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getcontext, GLIBC-setcontext, GLIBC-makecontext, GLIBC-swapcontext |

## Declaration and gates

```c
#include <ucontext.h>

int getcontext(ucontext_t *ucp);                        /* line 34 */
int setcontext(const ucontext_t *ucp);                  /* line 37 */
int swapcontext(ucontext_t *restrict oucp,
                const ucontext_t *restrict ucp);        /* lines 41-42 */
void makecontext(ucontext_t *ucp, void (*func)(void),
                 int argc, ...);                        /* lines 51-52 */
```

No feature-test gate in `/usr/include/ucontext.h` (lines 34-52).

## Semantics

`ucontext_t` bundles the machine context (`uc_mcontext`), the blocked
signal mask (`uc_sigmask`), the stack (`uc_stack`) and the successor
context (`uc_link`) (`getcontext(3)`). `getcontext` snapshots the
caller into `*ucp`; `setcontext` restores one, never returning on
success. `makecontext` prepares such a snapshot so that activating it
calls `func` with `argc` integer arguments, and when `func` returns,
control resumes in `ucp->uc_link` (or the thread exits if that is
NULL) -- the caller must first `getcontext(ucp)`, install a fresh
`uc_stack`, and set `uc_link`. `swapcontext` atomically saves the
current context into `*oucp` and activates `*ucp`; on later
reactivation of `*oucp` it looks like `swapcontext` returned 0
(`makecontext(3)`).

## Gotchas and portability

- `makecontext`'s varargs pass `int`s: routing pointers through it is
  undefined by the standards, but works on x86-64 with glibc 2.8+
  where `int` and pointer widths differ (`makecontext(3)` NOTES).
- There is no flag distinguishing a first `getcontext` return from a
  `setcontext` resurrection; the program invents its own bookkeeping
  (`getcontext(3)` NOTES).
- POSIX.1-2008 dropped `makecontext`/`swapcontext` and recommends
  pthreads; the glibc implementation is per-architecture assembly.
- musl 1.2.5 declares the four in `include/ucontext.h` but implements
  none of them -- linking fails (verified: no `makecontext.c` or
  `setcontext` implementation anywhere under `musl src/`).

## Errors

`ENOMEM` (insufficient stack space, `swapcontext`); otherwise no
errnos are defined by the man pages.

## References

- man3: `getcontext(3)`, `makecontext(3)`, `ucontext.h` struct docs
- headers: `/usr/include/ucontext.h`
- musl: `include/ucontext.h` (declaration only, no implementation)
