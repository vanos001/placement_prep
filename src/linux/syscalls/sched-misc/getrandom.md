# getrandom(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 318 / 355 / 278 / 384 (cached kernel tables; hub agrees) |
| Since (kernel) | 3.17 (man VERSIONS: "introduced in version 3.17 of the Linux kernel"; hub agrees); glibc support since 2.25 (man VERSIONS; symbol getrandom@@GLIBC_2.25) |
| Man page | man2/getrandom.2 (local cache, dated 2021-03-22) |
| glibc wrapper | Declared in `<sys/random.h>`; getrandom@@GLIBC_2.25 (nm -D on glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-getrandom |

## Purpose

`getrandom()` fills the buffer at `buf` with up to `buflen` random bytes drawn
by default from the same source as `/dev/urandom`, suitable for seeding
user-space RNGs and for cryptographic use. Unlike `/dev/random` and
`/dev/urandom` it involves no pathname or file descriptor, so it works where
`chroot(2)` hides `/dev` or where a library's pre-opened device fd was closed
(man page).

## Synopsis

    #include <sys/random.h>
    ssize_t getrandom(void *buf, size_t buflen, unsigned int flags);

## Arguments and behavior

| Flag | Value (installed linux/random.h) | Meaning (cached man page; INSECURE header comment) |
|---|---|---|
| `GRND_NONBLOCK` | 0x0001 | Do not block; return -1 with `EAGAIN` instead |
| `GRND_RANDOM` | 0x0002 | Draw from the random source (same source as `/dev/random`) instead of urandom |
| `GRND_INSECURE` | 0x0004 | Return non-cryptographic random bytes (header-sourced; not documented in the cached 2021 man page; kernel since-version unverified here) |

Blocking behavior (man page): when the urandom source is not yet initialized the
call blocks unless `GRND_NONBLOCK` is set. Reads of up to 256 bytes from the
initialized urandom source always return the full request and are not
interrupted by signals; larger requests may return a partially filled buffer or
fail with `EINTR`. With `GRND_RANDOM`, the call returns only the currently
available bytes and any size request can be interrupted by a signal.

## Return value and errors

Returns the number of bytes copied, which can be less than `buflen` (with
`GRND_RANDOM`, or after a signal interruption); the caller must always check it.
On error -1 with `errno`: `EAGAIN` (would have blocked; `GRND_NONBLOCK` set),
`EFAULT` (bad `buf`), `EINTR`, `EINVAL` (unknown flag), `ENOSYS` (kernel too
old).

## Flags and constants

Maximum bytes per call as of Linux 3.19 (man page): 33554431 from the urandom
source on 32-bit `int` systems; 512 from the random source. Reading small
buffers (<= 256 bytes) from urandom is the preferred usage; the special
treatment of small requests was designed for compatibility with OpenBSD's
getentropy(3), nowadays supported by glibc (man page).

## Security and notes

The 256-byte no-EINTR guarantee does not extend to larger buffers, and the man
page BUGS section notes that as of Linux 3.19 the call may not react to
interrupts before reading all requested bytes depending on CPU load. Do not
assume a full buffer without checking the return value.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/getrandom.2`
- Header: installed `/usr/include/linux/random.h` (`GRND_*` values)
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (318), `syscall_32.tbl`
  (355), `syscall_generic.tbl` (278), `syscall_arm.tbl` (384)
- Online: https://man7.org/linux/man-pages/man2/getrandom.2.html
