# alloc_hugepages(2) / free_hugepages(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (i386/ia64 slots in their day; never in the x86_64 or asm-generic tables) |
| Since (kernel) | 2.5.36; removed in 2.5.54 (man-pages HISTORY: "existed only in Linux 2.5.36 through to Linux 2.5.54") |
| Man page | man2/alloc_hugepages.2 (man-pages 6.19 HTML set, fetched 2026-10-17) covers both calls; man2/free_hugepages.2 is the .so alias |
| glibc wrapper | none -- "glibc provides no wrappers for these system calls, necessitating the use of syscall(2)" (alloc_hugepages.2, SYNOPSIS) |
| Aliases covered | free_hugepages (SC-free_hugepages, grouped) |
| Ledger ID | SC-alloc_hugepages |

## Purpose

alloc_hugepages() and free_hugepages() were the first attempt to hand huge pages to processes: they mapped or freed locked, non-swappable huge pages (2 or 4 MiB on i386, several sizes on ia64) through a key-based sharing scheme (alloc_hugepages.2, DESCRIPTION). They lived only in the 2.5.36-2.5.54 development window and only on i386/ia64 with CONFIG_HUGETLB_PAGE.

## Synopsis

```c
void *syscall(size_t size; SYS_alloc_hugepages, int key,
              void addr[size], size_t size, int prot, int flag);
int syscall(SYS_free_hugepages, void *addr);
```

## Arguments and behavior

`key` selects sharing: zero makes the pages private and non-inherited by children; positive keys share the mapping with every process using the same key and inherit it to children (alloc_hugepages.2, DESCRIPTION). `addr`/`size`/`prot` behave as the mapping arguments of the era; free_hugepages() takes the address previously returned by alloc_hugepages() (alloc_hugepages.2, DESCRIPTION). On 2.4.20 the numbers still existed but the calls failed with ENOSYS (alloc_hugepages.2, DESCRIPTION).

## Return value and errors

alloc_hugepages() returned the virtual address, free_hugepages() returned 0; -1 with errno on error, and the one documented error is ENOSYS (the call is not supported on this kernel) (alloc_hugepages.2, RETURN VALUE/ERRORS).

## Flags and constants

None.

## Security and notes

Huge pages were locked in memory and never swapped -- a kernel-memory-exhaustion vector by design, which is part of why the interface was dropped rather than hardened. The replacement is the hugetlbfs filesystem plus mmap(2), with sizing via /proc/sys/vm/nr_hugepages and the hugepages= boot parameter (alloc_hugepages.2, NOTES/FILES); the modern chapter of the same story is MAP_HUGETLB and memfd_secret-style special mappings (see [mmap](../memory/mmap.md), [memfd_create](../memory/memfd_create.md)). Interview angle: this page is the "the kernel once had a direct huge-page syscall and killed it" datapoint. Cross-reference: [mmap](../memory/mmap.md), [brk](../memory/brk.md), [madvise](../memory/madvise.md).

## References

- https://man7.org/linux/man-pages/man2/alloc_hugepages.2.html
- man-pages syscalls(2) (2.5.36, removed 2.5.44/2.5.54)
