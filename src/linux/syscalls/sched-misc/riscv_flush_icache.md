# riscv_flush_icache(2) (RISC-V)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (RISC-V table only) |
| Since (kernel) | 4.15 (syscalls(2): "RISC-V only") |
| Man page | none (no man2/riscv_flush_icache.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; x86-irrelevant sibling [cacheflush](cacheflush.md) |
| Ledger ID | SC-riscv_flush_icache |

## Purpose

riscv_flush_icache() flushes the instruction cache over a virtual address range on RISC-V -- the self-modifying-code primitive for a platform where the I-cache is not coherent with stores: the verified implementation is `SYSCALL_DEFINE3(riscv_flush_icache, uintptr_t, start, uintptr_t, end, unsigned int, flags)` calling flush_icache_mm(current->mm, flags & SYS_RISCV_FLUSH_ICACHE_LOCAL) (arch/riscv/kernel/sys_riscv.c:69, fetched 2026-10-17). The source comment states the contract: flush the instruction cache over [start, end), where start and end need not be page-aligned.

## Synopsis

```c
/* RISC-V syscall */
long syscall(SYS_riscv_flush_icache, uintptr_t start,
             uintptr_t end, unsigned int flags);
/* SYS_RISCV_FLUSH_ICACHE_LOCAL: 1UL << 0 -- flush only the local hart */
```

## Arguments and behavior

`start`/`end` bound the range (exclusive end, no alignment requirement per the source comment); `flags` may be 0 (broadcast to all harts running the mm) or SYS_RISCV_FLUSH_ICACHE_LOCAL (current hart only) (verified source; the UAPI constants live in the RISC-V uapi headers).

## Return value and errors

0 on success; a negated error on the raw path (the implementation's flush helper can fail on invalid ranges).

## Flags and constants

SYS_RISCV_FLUSH_ICACHE_LOCAL (0x1); 0 means flush across all harts (uapi asm/unistd.h, RISC-V).

## Security and notes

Source-limited: implementation and contract comment verified in the fetched source; no man page exists. JIT authors on RISC-V pair it with writable+executable mappings (or W^X flip plus flush); getting the LOCAL flag wrong on multi-hart cores is the classic missing-invalidation bug. Cross-reference: [cacheflush](cacheflush.md), [mmap](../memory/mmap.md), [mprotect](../memory/mprotect.md).

## References

- Kernel source: arch/riscv/kernel/sys_riscv.c (SYSCALL_DEFINE3(riscv_flush_icache)), torvalds/linux master, fetched 2026-10-17
- man-pages syscalls(2) (riscv_flush_icache(2), 4.15, RISC-V only)

