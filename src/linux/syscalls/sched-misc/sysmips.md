# sysmips(2) (MIPS)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (MIPS table only) |
| Since (kernel) | 2.6.0 (syscalls(2): "MIPS only") |
| Man page | none (no man2/sysmips.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction; the MIPS kernel documents the commands in its arch headers |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none |
| Ledger ID | SC-sysmips |

## Purpose

sysmips() is the MIPS multiplexer syscall: one table slot, several platform operations selected by a command code -- historically MIPS_ATOMIC_SET (emulated atomic set), MIPS_FIXADE (control of unaligned-access fixup behavior for the calling process), MIPS_RDNVRAM, and flush-cache-adjacent commands (the MIPS port's userspace-services syscall, dating from the 2.6 table era; syscalls(2) dates the name at 2.6.0).

## Synopsis

```c
/* MIPS syscall */
long syscall(SYS_sysmips, int cmd, long arg1, long arg2, long arg3);
```

## Arguments and behavior

`cmd` selects the operation; the arg triple is per-command (the MIPS arch headers define the codes; e.g. MIPS_FIXADE toggles whether the kernel fixes up unaligned accesses for the process rather than delivering SIGBUS).

## Return value and errors

Per-command: success values vary; a negated error on the raw path for unknown commands (EINVAL-class) or ENOSYS where the command is not built in.

## Flags and constants

MIPS_ATOMIC_SET, MIPS_FIXADE, MIPS_RDNVRAM and the other command codes (MIPS uabi headers).

## Security and notes

Source-limited: no man page and the implementation file was not fetched this round -- the entry names that gap and describes the multiplexer design from the syscalls(2) listing and the ledger. Interview angle: sysmips(2) is the classic "one number, many operations" design that modern syscalls replaced with dedicated entries (see the xattrat family's approach). Cross-reference: [atomic_cmpxchg_32](atomic_cmpxchg_32.md), [cacheflush](cacheflush.md).

## References

- man-pages syscalls(2) (sysmips(2), 2.6.0, MIPS only)
- Ledger row SC-sysmips

