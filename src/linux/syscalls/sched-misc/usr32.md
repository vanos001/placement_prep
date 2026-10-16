# usr32(2) (ARM private)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (ARM private range __ARM_NR_usr32 = 0x0f000000+4) |
| Since (kernel) | 2.4.8.1 (ledger) |
| Man page | none (no man2/usr32.2; ARM private syscalls have no man pages) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; companions [usr26](usr26.md), [breakpoint](breakpoint.md) |
| Ledger ID | SC-usr32 |

## Purpose

usr32() switches the calling thread's CPSR back into 32-bit mode -- the dispatcher sets MODE32_BIT (verified: `regs->ARM_cpsr |= MODE32_BIT; return regs->ARM_r0;`, arch/arm/kernel/traps.c) -- restoring normal ARM32 execution after a usr26 excursion into 26-bit mode. Same HWCAP_26BIT gate as its sibling: without the capability the call falls through to -ENOSYS.

## Synopsis

```c
/* ARM private syscall: __ARM_NR_usr32 (0x0f000004) */
long syscall(0x0f000004);
```

## Arguments and behavior

No arguments; the effect is on the calling thread's CPSR (verified source).

## Return value and errors

Returns the caller's r0 unchanged on success; -ENOSYS when HWCAP_26BIT is absent.

## Flags and constants

None (HWCAP_26BIT is the gating capability).

## Security and notes

Source-limited: dispatcher verified in the fetched source; no man page exists. Cross-reference: [usr26](usr26.md), [breakpoint](breakpoint.md), [set_tls](set_tls.md).

## References

- Kernel source: arch/arm/kernel/traps.c (case NR(usr32)), torvalds/linux master, fetched 2026-10-17
- UAPI: arch/arm/include/uapi/asm/unistd.h (__ARM_NR_usr32 = __ARM_NR_BASE+4)
- Ledger row SC-usr32

