# create_module(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 174 / 127 / -- / -- |
| Since (kernel) | 1.0; removed in 2.6 (create_module.2 HISTORY) |
| Man page | man2/create_module.2 (man-pages 6.19 HTML set, fetched 2026-10-17): "This system call is present only before Linux 2.6" |
| glibc wrapper | not supported: no declaration in glibc headers, and the exported create_module @GLIBC_2.2.5 symbol in glibc 2.41 (nm -D) is the pre-2.23-era ABI kept as a leftover (create_module.2, HISTORY) |
| Aliases covered | none |
| Ledger ID | SC-create_module |

## Purpose

create_module() created a loadable-module entry and reserved the contiguous kernel memory the module would occupy, returning the kernel address where it would land (create_module.2, DESCRIPTION). It was step one of the pre-2.6 module-loading dance: create_module -> init_module, with the userspace linker fixing up relocations against that address.

## Synopsis

```c
#include <linux/module.h>
[[deprecated]] caddr_t create_module(const char *name, size_t size);
```

## Arguments and behavior

`name` names the new module; `size` is the memory to reserve, rejected with EINVAL if smaller than the module header (create_module.2, DESCRIPTION/ERRORS). Requires privilege (CAP_SYS_MODULE, phrased in the man page as "requires privilege") (create_module.2, DESCRIPTION). Linux 2.6 replaced the whole flow with init_module(2)/finit_module(2) (see [delete_module](delete_module.md)) doing allocation and relocation in-kernel.

## Return value and errors

Returns the kernel address where the module will reside; -1 with errno on error (create_module.2, RETURN VALUE). Errors: EEXIST (name taken), EFAULT (bad name pointer), EINVAL (size too small), ENOMEM (no contiguous block), ENOSYS (2.6+), EPERM (unprivileged caller) (create_module.2, ERRORS).

## Flags and constants

None.

## Security and notes

The contiguous-allocation requirement was a physical-memory fragmentation time bomb -- one of the reasons the 2.6 redesign moved loading into the kernel with vmalloc-backed module memory. The symbol-archaeology note (exported ABI long after the man page says "not supported by glibc") is a good interview illustration of how compat symbols outlive the interfaces they front. Cross-reference: [delete_module](delete_module.md), [finit_module family](delete_module.md), [get_kernel_syms](get_kernel_syms.md), [query_module](query_module.md).

## References

- https://man7.org/linux/man-pages/man2/create_module.2.html
- man-pages syscalls(2) ("Removed in 2.6")
- worklog: leftover glibc symbol create_module @GLIBC_2.2.5 verified with nm -D (2026-10-17)
