# `getentropy` / `getrandom` (3) - glibc

> Split from the chapter *glibc: Cryptographic Functions* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sys/random.h` (both; `getentropy` also in `unistd.h` under `__USE_MISC`) |
| Standards | GNU extensions, glibc 2.25; `getentropy` derived from OpenBSD |
| Exported | `getentropy@@GLIBC_2.25`, `getrandom@@GLIBC_2.25` (nm, host glibc 2.41) |
| Thread-safety | Not stated in man (no ATTRIBUTES table); glibc manual marks both `@mtsafe` (`crypt.texi` node *Unpredictable Bytes*) |
| Ledger ID | GLIBC-getentropy, GLIBC-getrandom |

## Declaration and gates

```c
#include <sys/random.h>

#define GRND_NONBLOCK 0x01   /* line 26 (same in <linux/random.h> 54) */
#define GRND_RANDOM   0x02   /* line 27 (same in <linux/random.h> 55) */
#define GRND_INSECURE 0x04   /* line 28, non-cryptographic bytes */

ssize_t getrandom(void *buffer, size_t length,
                  unsigned int flags);          /* lines 34-36 */
int getentropy(void *buffer, size_t length);    /* lines 40-41 */
```

Both are declared unconditionally in
`/usr/include/x86_64-linux-gnu/sys/random.h`; `getentropy` is
additionally in the `__USE_MISC` block of `/usr/include/unistd.h`
(lines 1198-1203). Gate per man: `_DEFAULT_SOURCE`.

## Semantics

Both fill a buffer from the kernel's random pool; glibc's manual
advises "most applications should use `getentropy`" and reserves
`getrandom` for low-level callers needing blocking control
(`crypt.texi`). `getentropy` writes exactly `length` bytes, `length`
capped at 256, and returns 0 or -1 with `errno`; it cannot be
interrupted by signals or cancellation even when it blocks during
early boot (`getentropy(3)`, manual). `getrandom` writes *up to*
`length` bytes from the urandom source by default: reads of at most
256 bytes from an initialized pool are complete and
signal-untouched; larger reads may be partial or fail with `EINTR`.
`GRND_RANDOM` switches to the entropy-limited `/dev/random` source;
`GRND_NONBLOCK` turns pool-not-ready blocking into `EAGAIN`;
`GRND_INSECURE` requests non-cryptographic bytes for early-boot use
(`getrandom(2)`). Raw-syscall counterparts live at
[syscalls: getrandom](../../../syscalls/sched-misc/getrandom.md).

## Gotchas and portability

- 256 is a hard API boundary for `getentropy` (`EIO` above it); seed
  a userspace CRNG for larger needs (manual, *Unpredictable Bytes*).
- glibc's `getrandom` wrapper is a cancellation point;
  `getentropy` is not (`getentropy(3)` NOTES).
- musl 1.2.5 implements both (`src/misc/getentropy.c`,
  `src/linux/getrandom.c`).

## Errors

`getentropy`: `EFAULT`, `EIO` (length > 256 or pool failure),
`ENOSYS`. `getrandom`: `EAGAIN` (`GRND_NONBLOCK`, not yet ready),
`EFAULT`, `EINTR`, `EINVAL` (bad flags), `ENOSYS`.

## References

- glibc manual: `crypt.texi`, node *Unpredictable Bytes*
- man3/man2: `getentropy(3)`, `getrandom(2)`
- headers: `/usr/include/x86_64-linux-gnu/sys/random.h`,
  `/usr/include/linux/random.h`
- musl: `src/misc/getentropy.c`, `src/linux/getrandom.c`
