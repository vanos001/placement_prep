# `cfgetispeed` / `cfgetospeed` / `cfsetispeed` / `cfsetospeed` / `cfsetspeed` / `cfgetibaud` / `cfgetobaud` / `cfsetibaud` / `cfsetobaud` / `cfsetbaud` (3) - glibc

> Split from the chapter *glibc: Low-Level Terminal Interface* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `termios.h` (speed functions; the `baud_t` rows are documented in the manual but absent from host headers) |
| Standards | POSIX.1 (`cfgetispeed`, `cfgetospeed`, `cfsetispeed`, `cfsetospeed`); BSD (`cfsetspeed`, 4.4BSD); GNU (`baud_t` family: `cfgetibaud`, `cfgetobaud`, `cfsetibaud`, `cfsetobaud`, `cfsetbaud`) |
| Exported | `cfgetispeed@@GLIBC_2.2.5`, `cfgetospeed@@GLIBC_2.2.5`, `cfsetispeed@@GLIBC_2.2.5`, `cfsetospeed@@GLIBC_2.2.5`, `cfsetspeed@@GLIBC_2.2.5`; none of the five `baud_t` names (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (`termios(3)` ATTRIBUTES; manual @safety notes warn about shared non-opaque `termios` objects) |
| Ledger ID | GLIBC-cfgetispeed, GLIBC-cfgetospeed, GLIBC-cfsetispeed, GLIBC-cfsetospeed, GLIBC-cfsetspeed, GLIBC-cfgetibaud, GLIBC-cfgetobaud, GLIBC-cfsetibaud, GLIBC-cfsetobaud, GLIBC-cfsetbaud |

## Declaration and gates

```c
#include <termios.h>

speed_t cfgetispeed(const struct termios *termios_p);
speed_t cfgetospeed(const struct termios *termios_p);
int cfsetispeed(struct termios *termios_p, speed_t speed);
int cfsetospeed(struct termios *termios_p, speed_t speed);
int cfsetspeed(struct termios *termios_p, speed_t speed);  /* __USE_MISC */
```

The first four are unconditional in `/usr/include/termios.h` (lines
48-57), `cfsetspeed` in the `__USE_MISC` block (lines 59-62); the man
page gate for `cfsetspeed` is `_DEFAULT_SOURCE` since glibc 2.19
(`termios(3)`). The five `baud_t` functions (`cfgetobaud`, `cfgetibaud`,
`cfsetobaud`, `cfsetibaud`, `cfsetbaud`, standards "GNU, termios.h")
are documented in the manual's *baud_t interface* section but are
neither declared in any `/usr/include` header nor exported by
`libc.so.6` on this host (rg + nm, zero hits) -- documented from the
manual only, pending the glibc release that ships them.

## Semantics

Two line speeds exist per terminal. The `speed_t` functions store and
return the encoded constants (`B110`, `B300`, ...; `B0` on output means
modem disconnect). Setting the input speed to numeric `0` means "same
as output", deprecated by POSIX.1-2024 (manual, *Line Speed*).
`cfsetspeed` sets both directions at once (4.4BSD extension,
`termios(3)`). The `baud_t` family is the GNU plain-numeric counterpart
returning real rates (`baud_t`/`BAUD_MAX`, manual). Speed setters fail
with `EINVAL` for implausible values and are the only validation point;
hardware limits are enforced later by `tcsetattr`.

## Gotchas and portability

- In current glibc `speed_t` happens to be numerically identical to the
  rate, but portable code must use the `B*` constants (manual
  *Portability note*).
- musl 1.2.5: the five POSIX/BSD functions exist, but `cfsetspeed` is a
  weak alias of `cfsetospeed` -- it sets only the output speed, unlike
  BSD/glibc (`musl src/termios/cfsetospeed.c`); no `baud_t` names.

## References

- glibc manual: `terminal.texi`, nodes *Line Speed*, *The speed_t
  interface*, *The baud_t interface*
- man3: `termios(3)` (covers the speed functions)
- headers: `/usr/include/termios.h`, `bits/termios-baud.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
