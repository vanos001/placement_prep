# `cfmakeraw` / `tcdrain` / `tcflow` / `tcflush` / `tcsendbreak` (3) - glibc

> Split from the chapter *glibc: Low-Level Terminal Interface* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `termios.h` (`cfmakeraw` under `__USE_MISC`) |
| Standards | POSIX.1-2001 (`tcdrain`, `tcflow`, `tcflush`, `tcsendbreak`); BSD (`cfmakeraw`) |
| Exported | `cfmakeraw@@GLIBC_2.2.5`, `tcdrain@@GLIBC_2.2.5` (weak), `tcflow@@GLIBC_2.2.5`, `tcflush@@GLIBC_2.2.5`, `tcsendbreak@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (`termios(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-cfmakeraw, GLIBC-tcdrain, GLIBC-tcflow, GLIBC-tcflush, GLIBC-tcsendbreak |

## Declaration and gates

```c
#include <termios.h>

void cfmakeraw(struct termios *termios_p);              /* __USE_MISC */

int tcsendbreak(int fd, int duration);
int tcdrain(int fd);                 /* no __THROW: cancellation point */
int tcflush(int fd, int queue_selector);
int tcflow(int fd, int action);
```

`cfmakeraw` sits in the `__USE_MISC` block of
`/usr/include/termios.h` (lines 74-77; man gate `_DEFAULT_SOURCE` since
glibc 2.19). `tcsendbreak`/`tcflush`/`tcflow` are unconditional (lines
80-94) and `tcdrain` is declared without `__THROW` (line 86) because it
is a cancellation point.

## Semantics

`cfmakeraw` turns a `termios` structure into BSD "raw mode" by clearing
`IGNBRK|BRKINT|PARMRK|ISTRIP|INLCR|IGNCR|ICRNL|IXON` on `c_iflag`,
`OPOST` on `c_oflag`, `ECHO|ECHONL|ICANON|ISIG|IEXTEN` on `c_lflag`,
and `CSIZE|PARENB` while setting `CS8` on `c_cflag` (manual, *Raw
Mode*; the code is quoted verbatim there). `tcdrain` blocks until all
output written to `fd` has been transmitted. `tcsendbreak` transmits a
break for `duration` units (zero means about 0.25-0.5 s). `tcflush`
discards queued input and/or output per `TCIFLUSH`, `TCOFLUSH`,
`TCIOFLUSH`. `tcflow` suspends or resumes output (`TCOOFF`, `TCOON`) or
sends stop/start input control characters (`TCIOFF`, `TCION`).

## Gotchas and portability

- All five return 0 on success, -1 with `errno` on failure
  (`termios(3)` RETURN VALUE).
- `tcdrain`'s cancellation-point status matters for pthreads code: a
  canceled thread can abort mid-drain.
- `cfmakeraw` only edits the structure; the change reaches the device
  only via `tcsetattr`, which can partially succeed (see
  `termios(3)`).
- musl 1.2.5: all five present (`musl src/termios/cfmakeraw.c`,
  `tcdrain.c`, `tcflow.c`, `tcflush.c`, `tcsendbreak.c`).

## References

- glibc manual: `terminal.texi`, nodes *Raw Mode*, *Line Control*,
  *Noncanonical Input*
- man3: `termios(3)` (covers all five)
- headers: `/usr/include/termios.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
