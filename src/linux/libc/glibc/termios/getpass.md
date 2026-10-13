# `getpass` (3) - glibc

> Split from the chapter *glibc: Low-Level Terminal Interface* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `unistd.h` (under `__USE_MISC` || `__USE_XOPEN && !__USE_XOPEN2K`) |
| Standards | SUSv2 LEGACY, removed in POSIX.1-2001 |
| Exported | `getpass@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe term (`getpass(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getpass |

## Declaration and gates

```c
#include <unistd.h>

char *getpass(const char *prompt);
```

The declaration is inside the
`#if defined __USE_MISC || (defined __USE_XOPEN && !defined
__USE_XOPEN2K)` block of `/usr/include/unistd.h` (lines 974-982). The
man page's historical gate: since glibc 2.2.2 `_XOPEN_SOURCE &&
!(_POSIX_C_SOURCE >= 200112L)` or `_DEFAULT_SOURCE` (before 2.19:
`_BSD_SOURCE`) (`getpass(3)`).

## Semantics

`getpass` opens `/dev/tty`, prints `prompt`, turns off terminal echo,
reads one line, restores the terminal state and closes `/dev/tty`
again. It returns a pointer to a static buffer holding the first
`PASS_MAX` bytes of the password without the trailing newline, or NULL
on error with `errno` set and the terminal state restored (`getpass(3)`).
In the glibc implementation, when `/dev/tty` cannot be opened the
prompt goes to stderr and the line is read from stdin; there is no
length limit and line editing is not disabled (`getpass(3)` NOTES).

## Errors

`ENXIO`: the process has no controlling terminal (`getpass(3)` ERRORS).

## Gotchas and portability

- Obsolete by design: the man page opens with "This function is
  obsolete. Do not use it." and points to the `ECHO` flag of
  `termios(3)` for hand-rolled no-echo input.
- Static return buffer: MT-Unsafe and trampled by the next call; the
  buffer is not zeroized, and the man page BUGS section tells callers
  to clear the password as soon as possible.
- `PASS_MAX` / `sysconf(_SC_PASS_MAX)` are withdrawn (POSIX.2); glibc
  accepts `_SC_PASS_MAX` and returns `BUFSIZ` (`getpass(3)` NOTES).
- musl 1.2.5: present in `src/legacy/getpass.c`, declared in
  `include/unistd.h` under `_GNU_SOURCE || _BSD_SOURCE`.

## References

- glibc manual: `terminal.texi` (terminal modes behind the echo toggle)
- man3: `getpass(3)`
- headers: `/usr/include/unistd.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
