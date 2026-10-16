# setup(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (i386 slot 127 in its day; never in x86_64/asm-generic) |
| Since (kernel) | 1.0; removed in 2.1.121 (setup.2 VERSIONS) |
| Man page | man2/setup.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | none (declared [[deprecated]] for syscall(2) use on the legacy tables) |
| Aliases covered | none |
| Ledger ID | SC-setup |

## Purpose

setup() was the one-shot bootstrap syscall: called once from linux/init/main.c, it ran the device and filesystem initialization functions configured into the kernel and mounted the root filesystem (setup.2, DESCRIPTION). No user process may call it -- "Any user process, even a process with superuser permission, will receive EPERM" (setup.2, DESCRIPTION).

## Synopsis

```c
#include <unistd.h>
[[deprecated]] int setup(void);
```

## Arguments and behavior

The man page records that the calling sequence varied over time -- sometimes a single `void *BIOS` argument, sometimes an `int magic` -- before removal in 2.1.121 (setup.2, VERSIONS). What modern kernels do at that point of boot (device init, rootfs mount) is in-kernel initcall machinery; the syscall slot survived as an i386 table fossil.

## Return value and errors

Always -1 for a user process (setup.2, RETURN VALUE). Errors: EPERM, always, for user processes (setup.2, ERRORS).

## Flags and constants

None.

## Security and notes

Like [idle](idle.md), setup() is privileged-by-identity: the check is "are you process 0 during boot", not a capability. Interview angle: these two slots are the answer to "did Linux ever have syscalls only the kernel's own bootstrap could call?" -- yes, and both were retired in the 2.1/2.3 era. Cross-reference: [idle](idle.md), [unimplemented](unimplemented.md), [reboot](reboot.md).

## References

- https://man7.org/linux/man-pages/man2/setup.2.html
- man-pages syscalls(2) (setup listed among the removed/bootstrap calls)
