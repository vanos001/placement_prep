# mseal(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 462 / 462 / 462 / 462 (hub) |
| Since (kernel) | 6.10 (hub; worklog 1-b tag-probed absent 6.9 / present 6.10) |
| Man page | none (no man2/mseal.2 exists as of man-pages 6.19; documented from kernel source: mm/mseal.c + Documentation/userspace-api/mseal.rst, both fetched -- this page is a source-sourced entry, marked as such) |
| glibc wrapper | none in release glibc; glibc NEWS 2.43 (development section of the cached snapshot): "On Linux, the mseal function has been added. It allows for sealing memory mappings to prevent further changes during process execution, such as changes to protection permissions, unmapping, relocation to another location, or shrinking the size." |
| Aliases covered | none |
| Ledger ID | SC-mseal |

## Purpose

mseal() seals a virtual memory range: after the call, the kernel blocks
mm syscalls that would modify the sealed mapping's attributes or layout
-- munmap(2) ([munmap](munmap.md)), mmap(2) ([mmap](mmap.md)),
mremap(2) ([mremap](mremap.md)), mprotect(2) and pkey_mprotect(2)
([mprotect](mprotect.md)), and the destructive madvise behaviors
MADV_DONTNEED, MADV_FREE, MADV_DONTNEED_LOCKED, MADV_WIPEONFORK and
MADV_DONTFORK (mseal.rst list). Blocked calls fail with `EPERM`. The
goal is fault mitigation: a corrupted pointer can no longer turn
.text/.rodata writable or remap trusted memory (mseal.rst; same idea as
XNU VM_FLAGS_PERMANENT and OpenBSD mimmutable).

## Synopsis

```c
/* kernel 6.10+, 64-bit only; no libc declaration in release glibc */
int mseal(void *addr, size_t len, unsigned long flags);
```

(mseal.rst signature; mm/mseal.c implements
SYSCALL_DEFINE3(mseal, unsigned long, start, size_t, len,
unsigned long, flags).)

## Arguments and behavior

`addr`/`len` name the range: start must be page-aligned (after
untagged_addr) inside an allocated VMA, the end must lie in an allocated
VMA with no gap; `len` is page-aligned implicitly by the kernel.
`flags` is reserved and must be 0 (mm/mseal.c returns `EINVAL`
otherwise). Sealing is idempotent: re-sealing an already sealed range
is a no-action, not an error. There is no munseal, consistent with
F_SEAL_SEAL for files; a sealed mapping stays until the process
terminates or execve(2) (mseal.rst).

## Return value and errors

0 on success; negated errors from the raw call: `EINVAL` (flags nonzero,
unaligned start, addr+len overflow), `ENOMEM` (start or end unallocated,
gap in range), `ENOSYS` (kernel without mseal, and 32-bit kernels: the
feature is built only for 64-bit kernels per mseal.rst). For these
errors the range is left unmodified; internal errors (VMA merge/split,
max-VMA count) may partially update the range. Blocked-syscall `EPERM`
return is atomic for munmap; mprotect/madvise may have partially applied
changes; mmap/mremap is undefined (mseal.rst).

## Flags and constants

None: `flags` must be 0. Config gates: CONFIG_ARCH_HAS_MMAP_SEAL /
mseal support in mm/mseal.c; CONFIG_MSEAL_SYSTEM_MAPPINGS seals kernel
created system mappings (vdso, vvar, vectors, sigpage, uprobes) on
architectures with CONFIG_ARCH_SUPPORTS_MSEAL_SYSTEM_MAPPINGS (mseal.rst).

## Security and notes

- mseal does not make memory immutable: /proc/self/mem (FOLL_FORCE),
  ptrace PTRACE_POKETEXT and userfaultfd can still write read-only
  sealed pages (mseal.rst, crediting Jann Horn's analysis).
- Do not seal malloc'd heap: the allocator must shrink/unmap (mseal.rst
  "When not to use mseal"); same warning for aio/shm-managed mappings.
- Since 6.10 (worklog 1-b); no man page -- all semantics here are from
  the kernel sources named above.

## References

- Kernel source: source-cache/fetched/master-mm-mseal.c;
  master-Documentation-userspace-api-mseal.rst (author Jeff Xu).
- glibc NEWS: source-cache/glibc-sparse/NEWS (2.43 section, mseal).
- Numbers/Since: hub [overview](overview.md); worklog Task 1-b.
