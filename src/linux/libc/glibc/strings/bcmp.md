# `bcmp` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `strings.h` |
| Standards | 4.3BSD; LEGACY in POSIX.1-2001, **removed** in POSIX.1-2008 (`bcmp(3)` CONFORMING TO) |
| Exported | `bcmp@@GLIBC_2.2.5` (ifunc-selected indirect symbol, nm `i` type) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`bcmp(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-bcmp |

## Declaration and gates

```c
#include <strings.h>

int bcmp(const void *s1, const void *s2, size_t n);
```

Declared in `strings.h` at line 34 under the same
`__USE_MISC || !__USE_XOPEN2K8` gate as the rest of the BSD byte-string
family (`/usr/include/strings.h`; see the sibling page
[bcopy-bzero-index-rindex.md](bcopy-bzero-index-rindex.md), which covers
`bcopy`, `bzero`, `index` and `rindex` but only mentions `bcmp` in
passing). Strict `_POSIX_C_SOURCE >= 200809L` builds hide the prototype;
legacy code needs `_DEFAULT_SOURCE`.

## Semantics

`bcmp` compares the two byte sequences `s1` and `s2`, each of length
`n`. It returns 0 when they are equal - in particular when `n` is zero -
and some nonzero value otherwise (`bcmp(3)` DESCRIPTION and RETURN
VALUE). It is the BSD spelling of `memcmp`; glibc implements it as an
IFUNC-resolved alias in the same object family as `memcmp`.

## Gotchas and portability

- Only the *zero/nonzero* distinction is documented, not the sign:
  `bcmp(3)` never promises `s1 < s2` ordering the way `memcmp(3)` does
  (return sign of the first difference). Code that relies on the sign
  must use `memcmp`.
- Obsolescence is documented, not folkloric: `bcmp(3)` CONFORMING TO
  marks it LEGACY in POSIX.1-2001 and removed in POSIX.1-2008, directing
  new programs to `memcmp(3)`.
- Unlike `index`/`rindex`, which nm shows as literal address aliases of
  `strchr`/`strrchr`, `bcmp` is an ifunc-dispatched symbol (nm type `i`
  at address 0x...a66d0 on this host) - still semantically `memcmp`.
- musl 1.2.5 keeps it for compatibility (`musl src/string/bcmp.c`),
  though its `include/string.h` does not declare it - a prototype is
  needed in user code.

## References

- glibc manual: `string.texi`, node *String/Array Comparison* (memcmp
  context; the BSD names are not documented as a family there)
- man3: `bcmp(3)` (also `bstring(3)` overview)
- header: `/usr/include/strings.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
