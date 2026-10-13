# `ffs` / `ffsl` / `ffsll` / `strverscmp` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `strings.h` (`ffs`); `string.h` per man NOTES for BSD prototypes of `ffsl`/`ffsll` (`strings.h` under `__USE_MISC` in glibc); `string.h` (`strverscmp`) |
| Standards | POSIX.1-2001 XSI / 4.3BSD (`ffs`); glibc extensions (`ffsl`, `ffsll`, `strverscmp`) |
| Exported | `ffs@@GLIBC_2.2.5`, `ffsl@@GLIBC_2.2.5` (weak), `ffsll@@GLIBC_2.2.5` (weak; `ffsl`/`ffsll` share one address), `strverscmp@@GLIBC_2.2.5` (weak) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`ffs(3)`, `strverscmp(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-ffs, GLIBC-ffsl, GLIBC-ffsll, GLIBC-strverscmp |

## Declaration and gates

```c
#include <strings.h>

int ffs(int i);
int ffsl(long i);       /* __USE_MISC (GNU) */
int ffsll(long long i); /* __USE_MISC (GNU) */

#define _GNU_SOURCE
#include <string.h>
int strverscmp(const char *s1, const char *s2);
```

`ffs` gate per `ffs(3)`: `_XOPEN_SOURCE >= 700 || !(_POSIX_C_SOURCE >=
200809L) || _DEFAULT_SOURCE` since glibc 2.12; `ffsl`/`ffsll` moved from
`_GNU_SOURCE` to `_DEFAULT_SOURCE` in glibc 2.27 (`/usr/include/strings.h`
lines 101-113).

## Semantics

`ffs` returns the 1-based position of the least significant set bit of
`i` (bit 1 = value 1), or 0 when `i` is 0; `ffsl`/`ffsll` widen the
argument to `long`/`long long` (`ffs(3)`). `strverscmp` compares two
strings "version-style": it locates the first difference, takes the
maximal digit runs touching that position, and compares those runs
numerically, treating leading zeros as a fractional part, so that
`jan1 < jan10` and the ordering `000, 00, 01, 010, 09, 0, 1, 9, 10`
holds (`strverscmp(3)`, manual `string.texi` *Shuffling Bytes* area
neighbor).

## Gotchas and portability

- The 0 vs 1 asymmetry: `ffs(0)` returns 0, but a *set* LSB is position
  1, so `pos == 0` is "no bits" while `pos == 1` is bit zero. Off-by-one
  bugs cluster here.
- `ffs` is XSI (POSIX.1-2001), not base POSIX; `ffsl`/`ffsll` are glibc
  extensions that other BSDs also carry (`ffs(3)` CONFORMING TO). GCC
  offers `__builtin_ffs`/`__builtin_ctz` as portable-fast alternatives.
- Header mismatch trap: `ffs(3)` NOTES observes BSDs prototype `ffs` in
  `string.h`; glibc puts all three in `strings.h` (with `ffsl`/`ffsll`
  additionally visible via `string.h` only under `_DEFAULT_SOURCE`
  because `string.h` includes `strings.h` there).
- `strverscmp` ignores `LC_COLLATE` entirely and assumes ASCII-ish digit
  semantics; it is a GNU extension shared with `versionsort(3)`/`ls -v`
  (`strverscmp(3)` DESCRIPTION, manual node reference above).
- `strverscmp` man ATTRIBUTES mark it plain MT-Safe, while the glibc
  manual marks it `MT-Safe locale` because it calls `isdigit`; the man
  page carries an explicit FIXME on this discrepancy - recorded here as
  unresolved (both sources named).
- musl 1.2.5 provides `strverscmp` (`musl src/string/strverscmp.c`);
  `ffs` family comes via its legacy layer.

## References

- glibc manual: `string.texi` (comparison functions context)
- man3: `ffs(3)` (covers `ffsl`, `ffsll`), `strverscmp(3)`
- header: `/usr/include/strings.h`, `/usr/include/string.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
