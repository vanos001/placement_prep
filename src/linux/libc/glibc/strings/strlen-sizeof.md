# `strlen` / `wcslen` / `strnlen` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` (`wcslen`: `wchar.h`) |
| Standards | ISO C (`strlen`, `wcslen`); POSIX.1-2008 (`strnlen`) |
| Exported | `strlen@@GLIBC_2.2.5`, `wcslen@@GLIBC_2.2.5`, `strnlen@@GLIBC_2.2.5` (nm, host glibc 2.41, all ifunc-selected) |
| Thread-safety | MT-Safe (ATTRIBUTES in `strlen(3)`, `strnlen(3)`, `wcslen(3)`) |
| Ledger ID | GLIBC-strlen (full), GLIBC-wcslen, GLIBC-strnlen |

## Declaration and gates

```c
#include <string.h>
#include <wchar.h>

size_t strlen(const char *s);            /* __attribute_pure__, __nonnull((1)) */
size_t strnlen(const char *s, size_t maxlen);  /* gated __USE_XOPEN2K8 in string.h */
size_t wcslen(const wchar_t *ws);        /* wchar.h */
```

`strnlen` in glibc headers is declared under `__USE_XOPEN2K8` (POSIX.1-2008);
the man page records the gate history as `_POSIX_C_SOURCE >= 200809L` since
glibc 2.10, `_GNU_SOURCE` before that (`strnlen(3)` SYNOPSIS). The prototypes
above are `/usr/include/string.h` lines 406-415 and `wcslen(3)`.

## Semantics

`strlen` returns the length of the string `s` in bytes, i.e. the offset of the
terminating null byte within the array (glibc manual, *String Length* node of
`string.texi`). `strnlen` returns `strlen(s)` if that is less than `maxlen`,
otherwise `maxlen`; it never reads past `s[maxlen-1]` (`strnlen(3)`). `wcslen`
is the wide-character equivalent: it counts `wchar_t` elements before the
terminating `L'\0'` (`wcslen(3)`).

## Gotchas and portability

- `sizeof` vs `strlen`: for `char string[32] = "hello, world";` the manual's own
  example gives `sizeof(string)` = 32 and `strlen(string)` = 12; on a pointer
  `char *ptr = string;`, `sizeof(ptr)` is the pointer size, not the string
  length (manual *String Length*). `sizeof` on a function parameter is always
  the pointer size.
- `strlen` on a buffer that may lack a terminator is undefined behavior;
  `strlen(3)` NOTES says to use `strnlen` in that case.
- Bytes, not characters: for multibyte-encoded strings the return value need
  not equal the character count; the manual suggests `mbsrtowcs`/`wcslen` for
  that (manual *String Length*).
- `_FORTIFY_SOURCE`: unlike the copy family, glibc defines no runtime
  `__strlen_chk`; `bits/string_fortified.h` (checked on this host) contains no
  `strlen` wrapper and `nm -D libc.so.6` exports no `__strlen_chk`, so
  fortification of `strlen` is compile-time only.
- musl 1.2.5: `strlen` is a plain loop and `strnlen` is `memchr`-based
  (`src/string/strlen.c`, `src/string/strnlen.c`).

## References

- glibc manual: `string.texi`, node *String Length*
- man3: `strlen(3)`, `strnlen(3)`, `wcslen(3)`
- headers: `/usr/include/string.h`, `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
