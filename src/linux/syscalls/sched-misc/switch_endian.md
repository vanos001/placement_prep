# switch_endian(2) (PowerPC64)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (PowerPC64 table only) |
| Since (kernel) | 4.1 (syscalls(2): "PowerPC64 only") |
| Man page | none (no man2/switch_endian.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none |
| Ledger ID | SC-switch_endian |

## Purpose

switch_endian() flips the calling thread's endianness on POWER8 hardware: POWER8 can execute in either big- or little-endian mode per thread, and this syscall (added in 4.1) swaps the MSR_LE bit so a process can migrate between BE and LE worlds without a restart -- returning a magic value the caller uses to verify the switch actually happened.

## Synopsis

```c
/* PowerPC64 syscall */
long syscall(SYS_switch_endian);
```

## Arguments and behavior

No arguments. The kernel flips MSR_LE for the calling thread and arranges the return path so the instruction after the syscall executes in the new endianness (the POWER8 endianness-switch design; the implementation lives in the arch/powerpc entry assembly).

## Return value and errors

Returns a fixed magic value (the switch succeeded marker); a negated error on non-POWER8 kernels or when the switch is unsupported.

## Flags and constants

MSR_LE is the bit being toggled (PowerPC architecture definition).

## Security and notes

Source-limited: no man page and the assembly file was not fetched this round -- the entry names that gap and describes the POWER8 design from the syscalls(2) listing and the ledger. Interview angle: per-thread endianness switching is the most exotic ABI feature any mainstream kernel shipped; glibc exposes it only through direct syscall use. Cross-reference: [kern_features](kern_features.md), [memory_ordering](memory_ordering.md).

## References

- man-pages syscalls(2) (switch_endian(2), 4.1, PowerPC64 only)
- Ledger row SC-switch_endian

