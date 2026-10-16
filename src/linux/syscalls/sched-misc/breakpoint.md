# breakpoint(2) (ARM private)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (ARM private range __ARM_NR_BREAKPOINT = 0x0f000000+1) |
| Since (kernel) | 2.2 (ledger; pre-dates the 2.4.8.1-era OABI table notes) |
| Man page | none (no man2/breakpoint.2; the ARM private syscalls have no man pages) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; ARM-private companions [usr26](usr26.md), [usr32](usr32.md), [set_tls](set_tls.md) |
| Ledger ID | SC-breakpoint |

## Purpose

breakpoint() is the ARM kernel-debugger hook: the dispatcher in arch/arm/kernel/traps.c labels it "SWI BREAK_POINT", rewinds the PC by the instruction width (2 for Thumb, 4 for ARM) and enters ptrace_break() -- i.e. it raises the breakpoint event into the ptrace layer (verified in the fetched source, fall 2026). Kernel-aware debuggers and early JIT toolkits used it as the software-breakpoint primitive on ARM.

## Synopsis

```c
/* ARM private syscall: __ARM_NR_breakpoint (0x0f000001) */
long syscall(0x0f000001);
```

## Arguments and behavior

No arguments. The effect is entirely on the calling thread's execution state: PC rewind plus a ptrace stop (arch/arm/kernel/traps.c, case NR(breakpoint)).

## Return value and errors

Returns regs->ARM_r0 (the caller's r0 is passed through); under a debugger the observable result is the ptrace stop.

## Flags and constants

None.

## Security and notes

Source-limited: the dispatcher body was verified in the fetched source; no man page exists. Interview angle: the ARM private range (0x0f000000+) is where Linux keeps ABI calls that are not part of the generic syscall tables -- breakpoint, cacheflush, usr26/usr32, set_tls/get_tls -- each existing because the platform needed a userspace-reachable kernel hook that generic ABIs never got. Cross-reference: [set_tls](set_tls.md), [usr26](usr26.md), [cacheflush](cacheflush.md), [ptrace](../process/ptrace.md).

## References

- Kernel source: arch/arm/kernel/traps.c (case NR(breakpoint): "SWI BREAK_POINT", torvalds/linux master, fetched 2026-10-17)
- UAPI: arch/arm/include/uapi/asm/unistd.h (__ARM_NR_breakpoint = __ARM_NR_BASE+1)
- Ledger row SC-breakpoint

