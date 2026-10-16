# getxpid(2) (Alpha)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (Alpha table only) |
| Since (kernel) | 2.0 |
| Man page | none (no man2/getxpid.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; companions [getxuid](getxuid.md), [getxgid](getxgid.md) |
| Ledger ID | SC-getxpid |

## Purpose

getxpid() completes the Alpha dual-return family: the verified body is `current_pt_regs()->r20 = sys_getppid(); return sys_getpid();` (arch/alpha/kernel/osf_sys.c:1281, fetched 2026-10-17) -- PID in the return register, parent PID in r20.

## Synopsis

```c
/* Alpha syscall */
long syscall(SYS_getxpid);   /* returns pid; ppid lands in r20 */
```

## Arguments and behavior

No arguments.

## Return value and errors

Returns the PID; the parent PID is placed in register r20 (verified source).

## Flags and constants

None.

## Security and notes

Source-limited: implementation verified in the fetched source; no man page exists. Cross-reference: [getxuid](getxuid.md), [getxgid](getxgid.md), [getpid](../process/getpid.md).

## References

- Kernel source: arch/alpha/kernel/osf_sys.c (SYSCALL_DEFINE0(getxpid), torvalds/linux master, fetched 2026-10-17)
- Ledger row SC-getxpid

