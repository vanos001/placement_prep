# getxgid(2) (Alpha)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (Alpha table only) |
| Since (kernel) | 2.0 |
| Man page | none (no man2/getxgid.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; companions [getxuid](getxuid.md), [getxpid](getxpid.md) |
| Ledger ID | SC-getxgid |

## Purpose

getxgid() is the group-ID member of the Alpha dual-return family: the verified body is `current_pt_regs()->r20 = sys_getegid(); return sys_getgid();` (arch/alpha/kernel/osf_sys.c:1275, fetched 2026-10-17) -- real GID in the return register, effective GID in r20.

## Synopsis

```c
/* Alpha syscall */
long syscall(SYS_getxgid);   /* returns rgid; egid lands in r20 */
```

## Arguments and behavior

No arguments.

## Return value and errors

Returns the real GID; the effective GID is placed in register r20 (verified source).

## Flags and constants

None.

## Security and notes

Source-limited: implementation verified in the fetched source; no man page exists. Cross-reference: [getxuid](getxuid.md), [getxpid](getxpid.md), [getgid](../process/getgid.md).

## References

- Kernel source: arch/alpha/kernel/osf_sys.c (SYSCALL_DEFINE0(getxgid), torvalds/linux master, fetched 2026-10-17)
- Ledger row SC-getxgid

