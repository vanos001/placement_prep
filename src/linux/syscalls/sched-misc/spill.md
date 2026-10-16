# spill(2) (Xtensa)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (Xtensa table only) |
| Since (kernel) | 2.6.13 (syscalls(2): "Xtensa only") |
| Man page | none (no man2/spill.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; table neighbor [xtensa](xtensa.md) |
| Ledger ID | SC-spill |

## Purpose

spill() forces the Xtensa register-window spill: Xtensa architectures with register windows keep procedure state in a rotating window file, and deep call chains must spill window frames to the stack -- the kernel-side spill syscall lets the window-overflow machinery be driven explicitly (the Xtensa port's window-overflow support, added alongside the arch's 2.6.13 merge).

## Synopsis

```c
/* Xtensa syscall */
long syscall(SYS_spill);
```

## Arguments and behavior

No arguments documented; the operation is entirely architectural (window spill) -- the gap this entry names is the absence of any man page or public ABI note beyond the table row.

## Return value and errors

0 on success; a negated error on the raw path for non-Xtensa kernels (ENOSYS).

## Flags and constants

None.

## Security and notes

Source-limited: no man page and no implementation file fetched this round; the entry rests on the syscalls(2) listing (2.6.13, Xtensa only) and the ledger. Cross-reference: [xtensa](xtensa.md), [swapcontext](swapcontext.md).

## References

- man-pages syscalls(2) (spill(2), 2.6.13, Xtensa only)
- Ledger row SC-spill

