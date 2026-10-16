# sethae(2) (Alpha)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (Alpha table only) |
| Since (kernel) | 2.0 |
| Man page | none (no man2/sethae.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none |
| Ledger ID | SC-sethae |

## Purpose

sethae() writes the Alpha HAE (Hardware Address Extension) register: the verified body is `current_pt_regs()->hae = val; return 0;` (arch/alpha/kernel/osf_sys.c:1299, fetched 2026-10-17). The HAE was OSF/1's mechanism for extending sparse I/O addressing on early Alpha platforms -- a platform register that the kernel tracks in the process's saved register state so it can be restored across context switches.

## Synopsis

```c
/* Alpha syscall (OSF/1 legacy) */
long syscall(SYS_sethae, unsigned long val);   /* returns 0 */
```

## Arguments and behavior

One argument: the new HAE value (verified source).

## Return value and errors

Always returns 0 (verified source).

## Flags and constants

None.

## Security and notes

Source-limited: implementation verified in the fetched source; no man page exists. The call is OSF/1 heritage kept for binaries of that era -- a good interview example of a syscall whose entire purpose is one platform register. Cross-reference: [getxuid](getxuid.md) (same table neighborhood), [ioperm](ioperm.md), [iopl](iopl.md).

## References

- Kernel source: arch/alpha/kernel/osf_sys.c (SYSCALL_DEFINE1(sethae), torvalds/linux master, fetched 2026-10-17)
- Ledger row SC-sethae

