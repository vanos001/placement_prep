# query_module(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 178 / 167 / -- / -- |
| Since (kernel) | 2.2; removed in 2.6 (query_module.2 VERSIONS) |
| Man page | man2/query_module.2 (man-pages 6.19 HTML set, fetched 2026-10-17): "This system call is present only before Linux 2.6" |
| glibc wrapper | not supported: no declaration in headers; glibc 2.41 still exports query_module @GLIBC_2.2.5 (nm -D) as the pre-2.23 leftover ABI (query_module.2, VERSIONS) |
| Aliases covered | none |
| Ledger ID | SC-query_module |

## Purpose

query_module() asked the kernel about loadable modules: loaded-module names, per-module symbol/export tables, export information -- selected by the `which` code and returned into a caller buffer with a companion `size_t *ret` (query_module.2, DESCRIPTION). It was the 2.2-era successor to [get_kernel_syms](get_kernel_syms.md) and died with the 2.6 module rewrite.

## Synopsis

```c
#include <linux/module.h>
[[deprecated]] int query_module(const char *name, int which,
                                void buf[bufsize], size_t bufsize,
                                size_t *ret);
```

## Arguments and behavior

`name` selects the module (NULL meaning the kernel proper, where the operation allows it); `which` selects the operation: 0 probes availability; QM_MODULES lists loaded-module names as NUL-separated strings with `*ret` = count; QM_DEPS/QM_REFS/QM_SYMBOLS/QM_INFO return per-module dependency, reference, symbol and info blocks respectively (query_module.2, DESCRIPTION). ENOSPC leaves `*ret` at the required buffer size, the standard two-phase pattern (query_module.2, ERRORS).

## Return value and errors

0 on success; -1 with errno (query_module.2, RETURN VALUE). Errors: EFAULT (bad name/buf/ret), EINVAL (bad which; NULL name where not permitted), ENOENT (no such module), ENOSPC (buffer too small; ret set to minimum), ENOSYS (2.6+) (query_module.2, ERRORS).

## Flags and constants

QM_MODULES, QM_DEPS, QM_REFS, QM_SYMBOLS, QM_INFO (<linux/module.h>).

## Security and notes

The modern readouts are /proc/modules, /proc/kallsyms and /sys/module/ (query_module.2, VERSIONS -- the man page names them explicitly), with loading itself moved to init_module/finit_module (see [delete_module](delete_module.md)). Interview angle: query_module is the middle frame of the module-info API arc get_kernel_syms -> query_module -> /proc + kmod tooling. Cross-reference: [create_module](create_module.md), [get_kernel_syms](get_kernel_syms.md), [delete_module](delete_module.md).

## References

- https://man7.org/linux/man-pages/man2/query_module.2.html
- man-pages syscalls(2) ("Removed in 2.6")
- worklog: leftover glibc symbol query_module @GLIBC_2.2.5 verified with nm -D (2026-10-17)
