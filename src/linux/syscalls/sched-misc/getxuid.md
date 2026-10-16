# getxuid(2) (Alpha)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (Alpha table only) |
| Since (kernel) | 2.0 (syscalls(2): "Alpha only; see NOTES" for the getx* family) |
| Man page | none (no man2/getxuid.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; companions [getxgid](getxgid.md), [getxpid](getxpid.md) |
| Ledger ID | SC-getxuid |

## Purpose

getxuid() returns the real UID and smuggles the effective UID out through r20 -- Alpha's second return-value register. The verified implementation reads, in full: `current_pt_regs()->r20 = sys_geteuid(); return sys_getuid();` (arch/alpha/kernel/osf_sys.c:1269, torvalds/linux master fetched 2026-10-17). OSF/1's calling convention exposed two result registers, so one call could deliver what x86 needed two for.

## Synopsis

```c
/* Alpha syscall */
long syscall(SYS_getxuid);   /* returns ruid; euid lands in r20 */
```

## Arguments and behavior

No arguments.

## Return value and errors

Returns the real UID; the effective UID is placed in register r20 (arch/alpha/kernel/osf_sys.c, verified source).

## Flags and constants

None.

## Security and notes

Source-limited: implementation verified in the fetched source; no man page exists. Interview angle: the getx* family is the canonical example of a calling convention (dual return registers) shaping syscall design -- the same trick alpha_pipe uses for pipe(2)'s two fds. Cross-reference: [getxgid](getxgid.md), [getxpid](getxpid.md), [getuid](../process/getuid.md).

## References

- Kernel source: arch/alpha/kernel/osf_sys.c (SYSCALL_DEFINE0(getxuid), torvalds/linux master, fetched 2026-10-17)
- man-pages syscalls(2) (old_adjtimex(2) NOTES references the Alpha-only family; getxuid listed in the per-arch table discussion)

