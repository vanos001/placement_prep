# get_tls(2) (ARM private)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (ARM private range __ARM_NR_GET_TLS = 0x0f000000+6) |
| Since (kernel) | 4.15 per the man-pages syscalls(2) table ("ARM OABI only, has __ARM_NR"); the slot is far older in the ARM tree |
| Man page | none (no man2/get_tls.2; ARM private syscalls have no man pages) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; companion [set_tls](set_tls.md) |
| Ledger ID | SC-get_tls |

## Purpose

get_tls() returns the calling thread's TLS pointer on ARM: the dispatcher reads current_thread_info()->tp_value[0] and returns it (verified in arch/arm/kernel/traps.c, fall 2026). It is the read side of [set_tls](set_tls.md), and the same value the __kuser_get_tls helper page exposes at the kuser helper address -- libc picks whichever access path the kernel offers.

## Synopsis

```c
/* ARM private syscall: __ARM_NR_get_tls (0x0f000006) */
long syscall(0x0f000006);   /* returns the thread pointer */
```

## Arguments and behavior

No arguments.

## Return value and errors

Returns the thread's TLS pointer (tp_value[0]); undefined names in the private range return -ENOSYS rather than raising SIGILL, so callers can probe gracefully (arch/arm/kernel/traps.c, default case).

## Flags and constants

None.

## Security and notes

Source-limited: dispatcher verified in the fetched source; no man page exists. syscalls(2) dates the name's table entry at 4.15 and marks it ARM-only -- the ledger copies that value. Cross-reference: [set_tls](set_tls.md), [arc_gettls](arc_gettls.md), [arch_prctl](../process/arch_prctl.md).

## References

- Kernel source: arch/arm/kernel/traps.c (case NR(get_tls), torvalds/linux master, fetched 2026-10-17)
- UAPI: arch/arm/include/uapi/asm/unistd.h (__ARM_NR_get_tls = __ARM_NR_BASE+6)
- man-pages syscalls(2) (get_tls(2), 4.15, ARM only)

