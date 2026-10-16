# set_tls(2) (ARM private)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (ARM private range __ARM_NR_SET_TLS = 0x0f000000+5) |
| Since (kernel) | 2.6.11 (syscalls(2): "ARM OABI/EABI only") |
| Man page | none (no man2/set_tls.2; ARM private syscalls have no man pages) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; companion [get_tls](get_tls.md) |
| Ledger ID | SC-set_tls |

## Purpose

set_tls() sets the calling thread's TLS pointer on ARM: the dispatcher calls set_tls(regs->ARM_r0) and returns 0 (verified in arch/arm/kernel/traps.c, fall 2026). The kernel-side set_tls() writes thread_info->tp_value and, on cores with the TPIDRURO user-readable register, programs it -- the mechanism glibc's TLS variants and __aeabi_read_tp use on ARM (arch/arm/include/asm/tls.h implements the inline).

## Synopsis

```c
/* ARM private syscall: __ARM_NR_set_tls (0x0f000005) */
long syscall(0x0f000005, void *tls_ptr);   /* returns 0 */
```

## Arguments and behavior

One argument: the new thread-pointer value (arch/arm/kernel/traps.c, case NR(set_tls)).

## Return value and errors

Always returns 0 on the dispatcher path (verified source).

## Flags and constants

None.

## Security and notes

Source-limited: dispatcher and the asm/tls.h inline verified in fetched sources; no man page exists. Interview angle: before TPIDRURW/TPIDRURO existed, ARM TLS needed a kernel write per thread-creation AND per clone (CLONE_SETTLS), and the kuser-helper page was the fast read path -- this syscall is the write path. Cross-reference: [get_tls](get_tls.md), [clone](../process/clone.md), [arc_settls](arc_settls.md).

## References

- Kernel source: arch/arm/kernel/traps.c (case NR(set_tls)); arch/arm/include/asm/tls.h (set_tls inline), torvalds/linux master, fetched 2026-10-17
- UAPI: arch/arm/include/uapi/asm/unistd.h (__ARM_NR_set_tls = __ARM_NR_BASE+5)
- man-pages syscalls(2) (set_tls(2), 2.6.11, ARM only)

