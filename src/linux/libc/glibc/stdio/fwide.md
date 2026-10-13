# `fwide` (3) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` |
| Standards | C95 (Amendment 1) / C99 / POSIX.1-2001 |
| Exported | `fwide@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`fwide.3` has no ATTRIBUTES table; glibc manual safety notes call it MT-Safe with corrupt-on-cancel caveats) |
| Ledger ID | GLIBC-fwide |

## Declaration and gates

```c
#include <wchar.h>

int fwide(FILE *fp, int mode);
```

Declared in the `#if defined __USE_ISOC95 || defined __USE_UNIX98`
block of `wchar.h` (`/usr/include/wchar.h` line 725); the man page gate
is `_XOPEN_SOURCE >= 500 || _ISOC99_SOURCE || _POSIX_C_SOURCE >=
200112L` (`fwide(3)`).

## Semantics

`fwide` queries or sets the orientation of `fp`. With `mode == 0` it
only reports: positive when the stream is wide oriented, negative when
byte oriented, zero when not yet oriented. With `mode > 0` it first
tries to make the stream wide oriented, with `mode < 0` byte oriented,
and then reports the resulting orientation (`fwide(3)`). Orientation
can never be changed again once fixed -- neither by `fwide` nor any
other call; only `freopen` resets it, and the first narrow or wide I/O
operation on an unoriented stream sets it implicitly (manual node
*Streams and I18N*).

## Gotchas and portability

- Mixing narrow and wide operations on one oriented stream is undefined
  and completely undiagnosed: "the application behavior will simply be
  strange or the application will simply crash" (manual, *Streams and
  I18N*). Calling `fwide(stream, 1)` early is the cheap guard.
- `fwide` reports but cannot flip an existing orientation; the return
  value, not success/failure, is the information channel.
- Orientation is per-`FILE`, so `,ccs=` `fopen` modes pre-orient a
  stream wide before the first operation.
- Wide output is still possible on byte-oriented streams through
  `fprintf` `%lc`/`%ls`, and narrow output through `fwprintf`
  `%c`/`%s` (`fwide(3)` NOTES).
- musl 1.2.5: present (`musl include/wchar.h` line 108,
  `src/stdio/fwide.c`).

## References

- glibc manual: `stdio.texi`, node *Streams and I18N*
- man3: `fwide(3)`
- headers: `/usr/include/wchar.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
