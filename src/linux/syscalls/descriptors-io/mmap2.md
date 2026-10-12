# mmap2(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | - / 192 / - / 192 (cached kernel tables; hub agrees) |
| Since (kernel) | 2.4 (hub/ledger); man page VERSIONS says 2.3.31 -- man-page value noted here |
| Man page | man2/mmap2.2 (local cache, dated 2021-03-22) |
| glibc wrapper | None by name; where the slot exists the glibc mmap() wrapper invokes mmap2() instead of mmap(2) (man NOTES) |
| Aliases covered | none |
| Ledger ID | SC-mmap2 (researched/BRIEF) |

## Purpose

mmap2() is the 32-bit architecture variant of mmap(2): the interface is identical except that the final offset argument is in 4096-byte units rather than bytes. The page-offset encoding lets a 32-bit off_t address mappings in files up to 2^44 bytes. It exists on i386 and arm32 (slot 192 on both); it does not exist on x86-64, where glibc's mmap() wrapper issues mmap(2) directly. On ia64 the unit is the system page size rather than a fixed 4096 bytes.

## Synopsis

```c
void *syscall(SYS_mmap2, unsigned long addr, unsigned long length,
              unsigned long prot, unsigned long flags,
              unsigned long fd, unsigned long pgoffset);
```

## Return value and errors

Returns the mapped address on success; -1 with errno on error. EINVAL where the page size is not 4096 bytes and offset * 4096 is not a multiple of the system page size; otherwise the mmap(2) error set applies.

## Security and notes

- This is probably not the call you want (man page): applications use mmap(2) and glibc selects the slot.
- No glibc SYS_mmap2-facing wrapper is exported; direct use needs syscall(2).

## References

- man2/mmap2.2 in the cached man-pages tree (dated 2021-03-22).
- [Syscalls ledger](../ledger.md) row SC-mmap2; kernel tables in source-cache/kernel (i386 192, arm 192).
- [Domain hub](overview.md) for status and sibling pages.
