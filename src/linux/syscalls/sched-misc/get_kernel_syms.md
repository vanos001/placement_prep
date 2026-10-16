# get_kernel_syms(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 177 / 130 / -- / -- |
| Since (kernel) | 1.0; removed in 2.6 (get_kernel_syms.2 HISTORY) |
| Man page | man2/get_kernel_syms.2 (man-pages 6.19 HTML set, fetched 2026-10-17): "present only before Linux 2.6" |
| glibc wrapper | not supported: no declaration in headers; the get_kernel_syms @GLIBC_2.2.5 symbol still exported by glibc 2.41 (nm -D) is the pre-2.23 leftover ABI (get_kernel_syms.2, HISTORY) |
| Aliases covered | none |
| Ledger ID | SC-get_kernel_syms |

## Purpose

get_kernel_syms() retrieved exported kernel and module symbols so the userspace module linker could resolve relocations: with a NULL table it returns the symbol count; otherwise it fills `struct kernel_sym { unsigned long value; char name[60]; }` entries, with magic `#module-name` tags interspersed to mark module load addresses, modules listed in reverse load order (get_kernel_syms.2, DESCRIPTION).

## Synopsis

```c
#include <linux/module.h>
[[deprecated]] int get_kernel_syms(struct kernel_sym *table);
```

## Arguments and behavior

One argument, the table pointer (NULL for the count probe) (get_kernel_syms.2, DESCRIPTION). The man page documents the fatal design flaw: the caller cannot state the buffer size, so symbols added between the count probe and the fill pass corrupt memory (get_kernel_syms.2, BUGS); symbol names cap at 59 characters. query_module(2) (see [query_module](query_module.md)) superseded it and was itself superseded by /proc/kallsyms and the kallsyms machinery.

## Return value and errors

Returns the number of symbols copied (or available); -1 with the single documented error ENOSYS when unsupported (get_kernel_syms.2, RETURN VALUE/ERRORS).

## Flags and constants

None.

## Security and notes

Beyond the buffer bug, the interface leaked kernel symbol addresses to unprivileged callers -- moot in its era but a textbook example of why symbol exposure moved behind root-only /proc/kallsyms (kptr_restrict). Interview angle: get_kernel_syms -> query_module -> /proc/kallsyms + finit_module is the module-loading API's full arc. Cross-reference: [create_module](create_module.md), [query_module](query_module.md), [delete_module](delete_module.md).

## References

- https://man7.org/linux/man-pages/man2/get_kernel_syms.2.html
- man-pages syscalls(2) ("Removed in 2.6")
- worklog: leftover glibc symbol get_kernel_syms @GLIBC_2.2.5 verified with nm -D (2026-10-17)
