# vhangup(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 153 / 111 / 58 / 111 (cached kernel tables; hub agrees) |
| Since (kernel) | 1.0 |
| Man page | man2/vhangup.2 (local cache, dated 2021-03-22) |
| glibc wrapper | Declared in <unistd.h>; feature macros: _DEFAULT_SOURCE since glibc 2.21 (_BSD_SOURCE or a low _XOPEN_SOURCE before); vhangup@@GLIBC_2.2.5 (nm -D on glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-vhangup (researched/BRIEF) |

## Purpose

vhangup() simulates a hangup on the current terminal, terminating the existing session's access so that the next login finds a "clean" terminal. It is the mechanism init(1)/login(1) use when reinitializing a tty line: the virtual hangup severs the previous users' association with the terminal device the way a carrier loss would.

## Synopsis

```c
#include <unistd.h>
int vhangup(void);
```

## Arguments and behavior

No arguments; the call operates on the controlling terminal of the calling process.

## Return value and errors

Returns 0 on success; -1 with errno: EPERM (insufficient privilege).

## Flags and constants

No flag arguments.

## Security and notes

- The gate is explicit in the man page: the CAP_SYS_TTY_CONFIG capability is required; anything else gets EPERM.
- Linux-specific and nonportable by its own man page; user-space code should not call it.

## References

- man2/vhangup.2 in the cached man-pages tree (dated 2021-03-22).
- [Syscalls ledger](../ledger.md) row SC-vhangup; [Domain hub](overview.md).
