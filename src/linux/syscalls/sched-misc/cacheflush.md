# cacheflush(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (per-arch tables only: MIPS, ARC, CSKY, NIOS2, M68K, SH, NDS32) |
| Since (kernel) | 1.2 (first on MIPS; cacheflush.2 VERSIONS: "this call first appeared on the MIPS architecture") |
| Man page | man2/cacheflush.2 (man-pages 6.19 HTML set, fetched 2026-10-17) |
| glibc wrapper | provided on ARC, CSKY, MIPS and NIOS2 with the canonical prototype; on M68K/SH/NDS32 the call exists with different arguments and glibc provides no wrapper (cacheflush.2, VERSIONS) |
| Aliases covered | none |
| Ledger ID | SC-cacheflush |

## Purpose

cacheflush() flushes the instruction and/or data cache over a user address range -- the self-modifying-code primitive on cache-incoherent architectures: after writing code bytes, the data cache must be written back and the instruction cache invalidated before execution (cacheflush.2, DESCRIPTION).

## Synopsis

```c
#include <sys/cachectl.h>
int cacheflush(void addr[int nbytes], int nbytes, int cache);
```

## Arguments and behavior

`addr`/`nbytes` bound the range; `cache` selects ICACHE, DCACHE, or BCACHE (both) (cacheflush.2, DESCRIPTION). The x86 world never needed it (coherent caches), which is why the ledger's x64/i386/g64/arm columns read `--`. Architectures diverge in signature: M68K `cacheflush(addr, scope, cache, size)`, SH `(addr, size, op)`, NDS32 `(start, end, cache)` (cacheflush.2, VERSIONS). Kernels older than 2.6.11 ignored addr/nbytes and always flushed everything, acting as if BCACHE were passed (cacheflush.2, BUGS).

## Return value and errors

0 on success; -1 with errno: EFAULT (range not accessible), EINVAL (bad `cache` value) (cacheflush.2, RETURN VALUE/ERRORS).

## Flags and constants

ICACHE, DCACHE, BCACHE (<sys/cachectl.h>).

## Security and notes

The portable spelling is GCC's `__builtin___clear_cache(begin, end)`, which the man page recommends over direct use and which compiles to no-op on coherent targets (cacheflush.2, VERSIONS, GCC alternative). JIT authors on MIPS/ARM-class chips pair it with W^X mappings; getting the order wrong (icache invalidation before dcache writeback) is the classic invisible-corruption bug interviews occasionally probe. Cross-reference: [mmap](../memory/mmap.md), [mprotect](../memory/mprotect.md), [riscv_flush_icache](riscv_flush_icache.md).

## References

- https://man7.org/linux/man-pages/man2/cacheflush.2.html
- man-pages syscalls(2) ("Not on x86")
