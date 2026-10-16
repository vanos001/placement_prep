# subpage_prot(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (PowerPC table only) |
| Since (kernel) | 2.6.25 (subpage_prot.2 HISTORY: "Linux 2.6.25 (PowerPC)"; provided only with CONFIG_PPC_64K_PAGES) |
| Man page | man2/subpage_prot.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | none -- "glibc provides no wrapper for subpage_prot(), necessitating the use of syscall(2)" (subpage_prot.2, SYNOPSIS) |
| Aliases covered | none |
| Ledger ID | SC-subpage_prot |

## Purpose

subpage_prot() applies per-4kB-subpage protection within 64kB pages on PowerPC systems configured with 64kB pages: a 2-bit protection map covering the address range [addr, addr+size) lets callers restrict access below the hardware's page granularity (subpage_prot.2, DESCRIPTION). The man page's stated rationale is emulator support -- x86-style guest MMUs with 4kB pages cannot be implemented efficiently on 64kB-page hosts without it (subpage_prot.2, NOTES, Rationale).

## Synopsis

```c
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_subpage_prot, unsigned long addr, unsigned long size,
            uint32_t *map);
```

## Arguments and behavior

`addr` and `size` must be 64kB-aligned and must not describe a region outside the process's address space or containing huge pages (EINVAL otherwise) (subpage_prot.2, DESCRIPTION/ERRORS). `map` supplies 2 bits per 4kB subpage -- each 32-bit word covers 16 subpages of one 64kB page; field values: 0 = any access, 1 = no writes, 2 = no reads, 3 = no accesses (subpage_prot.2, DESCRIPTION). Normal page-level protections still apply and compose as an additional constraint -- "putting 0 in a 2-bit field won't allow writes to a page that is otherwise write-protected" (subpage_prot.2, NOTES).

## Return value and errors

0 on success; a negated error on the raw path: EFAULT (map not accessible), EINVAL (addr/size alignment or range violations), ENOMEM (out of memory) (subpage_prot.2, RETURN VALUE/ERRORS).

## Flags and constants

The 2-bit per-subpage codes (0/1/2/3) documented above (subpage_prot.2, DESCRIPTION).

## Security and notes

The mechanism composes with, but cannot bypass, ordinary [mprotect](../memory/mprotect.md) rules -- an additional constraint only, which keeps the security model intact (subpage_prot.2, NOTES). Interview angle: the emulator rationale is the same problem pKVM/SEV-style nested memory control later attacked at other layers; PowerPC answered it in the MMU with subpage bits. Cross-reference: [mprotect](../memory/mprotect.md), [madvise](../memory/madvise.md), [map_shadow_stack](../memory/map_shadow_stack.md).

## References

- https://man7.org/linux/man-pages/man2/subpage_prot.2.html
- man-pages syscalls(2) (2.6.25, PowerPC only)
