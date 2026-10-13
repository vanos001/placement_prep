# `memccpy` / `mempcpy` / `memrchr` / `rawmemchr` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` |
| Standards | POSIX.1-2001/2008, SVr4, 4.3BSD (`memccpy`); GNU extensions (`mempcpy`, `memrchr`, `rawmemchr`) |
| Exported | `memccpy@@GLIBC_2.2.5` (weak), `mempcpy@@GLIBC_2.2.5`, `memrchr@@GLIBC_2.2.5`, `rawmemchr@@GLIBC_2.2.5` (ifunc symbols) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (`memccpy(3)`, `mempcpy(3)`, `memchr(3)` - which covers `memrchr`/`rawmemchr` - ATTRIBUTES) |
| Ledger ID | GLIBC-memccpy, GLIBC-mempcpy, GLIBC-memrchr, GLIBC-rawmemchr |

## Declaration and gates

```c
#include <string.h>

void *memccpy(void *restrict dest, const void *restrict src,
              int c, size_t n);          /* __USE_MISC || __USE_XOPEN || ISOC23 */
void *mempcpy(void *restrict dest, const void *restrict src, size_t n);
void *memrchr(const void *s, int c, size_t n);       /* __USE_GNU */
void *rawmemchr(const void *s, int c);               /* __USE_GNU */
```

`memccpy` is gated `__USE_MISC || __USE_XOPEN || __GLIBC_USE(ISOC23)`
(`/usr/include/string.h` lines 53-58). `mempcpy` (with private
`__mempcpy`) sits under `__USE_MISC` at lines 395-402, although
`mempcpy(3)` documents the `_GNU_SOURCE` spelling. `memrchr` and
`rawmemchr` share the `__USE_GNU` block at lines 111-135; `memchr(3)`
records their macros as plain `_GNU_SOURCE`.

## Semantics

`memccpy` copies at most `n` bytes, stopping after byte `c` is copied,
and returns a pointer just past that byte in `dest` - or NULL if `c`
never appeared in the first `n` bytes of `src`; overlapping areas are
undefined (`memccpy(3)`). `mempcpy` is `memcpy` that returns `dest + n`,
so chained copies fill consecutive regions without arithmetic; the man
page's `combine` example builds one buffer from two objects with nested
calls (`mempcpy(3)`). `memrchr` scans the `n` bytes *backward* from the
end; `rawmemchr` drops the count entirely and assumes an occurrence
exists - the documented idiom `rawmemchr(s, '\0')` is the fast strlen
endpoint finder - with unspecified results when `c` is absent
(`memchr(3)`, which also documents both GNU names). Versions per
`memchr(3)`/`mempcpy(3)`: `rawmemchr` glibc 2.1, `memrchr` 2.2,
`mempcpy` 2.1.

## Gotchas and portability

- `memccpy`'s return is "one past the copied `c`", not the copied byte:
  `*memccpy(buf, src, '\n', n) = '\0'` writes the terminator *after*
  the newline - check NULL before dereferencing.
- `rawmemchr` without a guaranteed match is undefined behavior; it is
  the one member of this batch that cannot be used defensively.
- musl 1.2.5: `memccpy`, `mempcpy`, `memrchr` present
  (`musl include/string.h` lines 81, 96-97); `rawmemchr` absent.

## References

- glibc manual: `string.texi`, nodes *Copying Strings and Arrays*,
  *Search Functions* (`rawmemchr`, `mempcpy` documented inline)
- man3: `memccpy(3)`, `mempcpy(3)` (covers `wmempcpy`), `memchr(3)`
  (covers `memrchr`, `rawmemchr`)
- header: `/usr/include/string.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
