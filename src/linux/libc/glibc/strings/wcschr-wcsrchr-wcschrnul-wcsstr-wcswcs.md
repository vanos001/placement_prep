# `wcschr` / `wcsrchr` / `wcschrnul` / `wcsstr` / `wcswcs` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` |
| Standards | C99 / POSIX.1-2001 (`wcschr`, `wcsrchr`, `wcsstr`); XPG4 / XPG (`wcswcs`); GNU extension (`wcschrnul`) |
| Exported | `wcschr@@GLIBC_2.2.5`, `wcsrchr@@GLIBC_2.2.5` (ifunc symbols), `wcsstr@@GLIBC_2.2.5` and `wcswcs@@GLIBC_2.2.5` (same address 0x...bf700 - alias evidence), `wcschrnul@@GLIBC_2.2.5` (weak) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`wcschr(3)`, `wcsrchr(3)`, `wcsstr(3)` ATTRIBUTES; `wcschrnul`/`wcswcs` have no separate man page - alias/family evidence) |
| Ledger ID | GLIBC-wcschr, GLIBC-wcsrchr, GLIBC-wcschrnul, GLIBC-wcsstr, GLIBC-wcswcs |

## Declaration and gates

```c
#include <wchar.h>

wchar_t *wcschr(const wchar_t *wcs, wchar_t wc);
wchar_t *wcsrchr(const wchar_t *wcs, wchar_t wc);
wchar_t *wcsstr(const wchar_t *haystack, const wchar_t *needle);

wchar_t *wcschrnul(const wchar_t *s, wchar_t wc);   /* __USE_GNU */
wchar_t *wcswcs(const wchar_t *haystack,
                const wchar_t *needle);             /* __USE_XOPEN */
```

`wcschr`/`wcsrchr` are unconditional (`/usr/include/wchar.h` lines
184-199), `wcsstr` likewise (lines 231-237). `wcschrnul` sits under
`__USE_GNU` at lines 203-207; `wcswcs` under `__USE_XOPEN` at lines
250-258 with the comment "Another name for `wcsstr' from XPG4".

## Semantics

`wcschr`/`wcsrchr` find the first/last occurrence of wide character
`wc` - the terminating L'\0' is part of the string, so searching for it
always succeeds (`wcschr(3)`, `wcsrchr(3)`). `wcsstr` locates the first
occurrence of `needle` in `haystack`; an empty needle returns `haystack`
itself (`wcsstr(3)`). `wcswcs` is the same function under its XPG4 name
- the manual calls it "a deprecated alias for `wcsstr`" (`string.texi`,
Search Functions). `wcschrnul` is `wcschr` that never fails: when `wc`
is absent it returns a pointer to the closing L'\0' (header comment
lines 204-205; manual *Search Functions*), which makes
length-plus-position scans allocation-free.

## Gotchas and portability

- `wcschrnul` changes the failure mode from NULL to "end pointer": code
  must not test it against NULL but against `wcs + wcslen(wcs)` - the
  manual explicitly recommends it for such scans.
- `wcswcs` survives only under `__USE_XOPEN`; mixing it into portable
  C99 code pulls an XPG dependency for nothing, since `wcsstr` is the
  same address (nm alias evidence on this host).
- All searches here are by one wide *character*, never by byte value;
  `wmemchr` (see
  [wmemchr-wmemcmp-wmemcpy-wmemmove-wmemset-wmempcpy.md](wmemchr-wmemcmp-wmemcpy-wmemmove-wmemset-wmempcpy.md))
  is the counted-array variant.
- musl 1.2.5: `wcschr`, `wcsrchr`, `wcsstr`, `wcswcs` present
  (`musl src/string/`); `wcschrnul` absent - it is a glibc extension.

## References

- glibc manual: `string.texi`, node *Search Functions*
  (`wcschrnul`, `wcswcs` documented inline)
- man3: `wcschr(3)` (covers `wcsrchr`), `wcsstr(3)`
- header: `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
