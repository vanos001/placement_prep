# usr26(2) (ARM private)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (ARM private range __ARM_NR_usr26 = 0x0f000000+3) |
| Since (kernel) | 2.4.8.1 (ledger; the OABI-era table generation) |
| Man page | none (no man2/usr26.2; ARM private syscalls have no man pages) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; companions [usr32](usr32.md), [breakpoint](breakpoint.md) |
| Ledger ID | SC-usr26 |

## Purpose

usr26() switches the calling thread's CPSR out of 32-bit mode -- the dispatcher clears MODE32_BIT (verified: `regs->ARM_cpsr &= ~MODE32_BIT; return regs->ARM_r0;`, arch/arm/kernel/traps.c) -- putting the thread into the legacy 26-bit PC+PSR execution mode that pre-ARMv4 programs expect. It only works when the kernel advertises HWCAP_26BIT: without the capability the case falls through to the default -ENOSYS handling (verified source).

## Synopsis

```c
/* ARM private syscall: __ARM_NR_usr26 (0x0f000003) */
long syscall(0x0f000003);
```

## Arguments and behavior

No arguments; the effect is on the calling thread's CPSR (verified source).

## Return value and errors

Returns the caller's r0 unchanged on success; falls through to -ENOSYS when HWCAP_26BIT is absent.

## Flags and constants

None (HWCAP_26BIT is the gating ELF hardware capability).

## Security and notes

Source-limited: dispatcher verified in the fetched source; no man page exists. The pair usr26/usr32 exists for the 26-bit-mode compatibility story that died with ARMv7 -- a nice interview datapoint on how far CPU-mode compatibility was pushed into Linux's ABI. Cross-reference: [usr32](usr32.md), [breakpoint](breakpoint.md), [vm86](vm86.md) (the x86 analogue of mode-switch syscalls).

## References

- Kernel source: arch/arm/kernel/traps.c (case NR(usr26)), torvalds/linux master, fetched 2026-10-17
- UAPI: arch/arm/include/uapi/asm/unistd.h (__ARM_NR_usr26 = __ARM_NR_BASE+3)
- Ledger row SC-usr26

