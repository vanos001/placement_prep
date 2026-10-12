# `iconv_open` / `iconv` / `iconv_close` (3) - glibc

> Split from the chapter *glibc: Character Set Handling* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `iconv.h` |
| Standards | XPG2 family; POSIX.1-2001/2008, SUSv2 |
| Exported | `iconv_open@@GLIBC_2.2.5`, `iconv@@GLIBC_2.2.5`, `iconv_close@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe `locale` (`iconv_open`); MT-Unsafe `race:cd` (`iconv`, safe under mutual exclusion on `cd`); MT-Safe (`iconv_close`) (`iconv(3)`, `iconv_open(3)`, `iconv_close(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-iconv_open, GLIBC-iconv, GLIBC-iconv_close |

## Declaration and gates

```c
#include <iconv.h>

typedef void *iconv_t;                 /* /usr/include/iconv.h line 29 */

int iconv_close(iconv_t cd);           /* line 36, cancellation point */
iconv_t iconv_open(const char *tocode, const char *fromcode);
                                       /* lines 43-44, cancellation point */
size_t iconv(iconv_t cd, char **restrict inbuf,
             size_t *restrict inbytesleft,
             char **restrict outbuf,
             size_t *restrict outbytesleft);   /* lines 49-51 */
```

No feature-test gate: the three prototypes are unconditional in
`/usr/include/iconv.h` (lines 29-56).

## Semantics

`iconv_open` allocates a descriptor converting `fromcode` to `tocode`
and returns it, or `(iconv_t) -1` with `errno` `EINVAL`/`EMFILE`/
`ENFILE`/`ENOMEM` when the pair is unsupported or resources are short
(`iconv_open(3)`, manual *Generic Conversion Interface*). The
descriptor carries conversion state; appending `//TRANSLIT` or
`//IGNORE` to `tocode` enables transliteration or silent dropping of
unconvertible characters (`iconv_open(3)`). `iconv` converts
byte-by-byte, advancing both buffer pointers and counters, and returns
the number of nonreversible conversions; it stops with
`(size_t) -1` on `E2BIG` (output full), `EILSEQ` (invalid input),
`EINVAL` (incomplete trailing sequence). Calling `iconv` with a NULL
`inbuf` resets `cd` to the initial state, optionally emitting the
reset shift sequence. `iconv_close` frees the descriptor (`iconv(3)`).

## Gotchas and portability

- Count check: the host gconv directory
  (`/usr/lib/x86_64-linux-gnu/gconv/`) ships 253 `.so` conversion
  modules and `iconv --list` enumerates 1180 names including aliases
  (live count; the worklog's "256" is stale by 3 modules). Module
  availability is a runtime property -- `iconv_open` can fail on an
  otherwise valid name.
- `iconv` updates `cd`'s state, so one descriptor must not be shared
  between threads without locking (`iconv(3)` ATTRIBUTES).
- EILSEQ stops at the first bad sequence; `*inbuf` points at it.
- musl 1.2.5 implements all three in one file
  (`musl src/locale/iconv.c`).

## References

- glibc manual: `charset.texi`, nodes *Generic Conversion Interface*,
  *Converting a Character*, *Converting Strings*
- man3: `iconv(3)`, `iconv_open(3)`, `iconv_close(3)`
- headers: `/usr/include/iconv.h`
- musl: `include/iconv.h`, `src/locale/iconv.c`
