# `parse_printf_format` / `register_printf_function` / `printf_size` / `printf_size_info` (3) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `printf.h` (no feature-test gate; the whole header is a GNU extension) |
| Standards | GNU only (ISO C has nothing similar; manual *Customizing printf*) |
| Exported | `parse_printf_format@@GLIBC_2.2.5`, `register_printf_function@@GLIBC_2.2.5` (weak), `printf_size@@GLIBC_2.2.5`, `printf_size_info@@GLIBC_2.2.5`; related `register_printf_specifier@@GLIBC_2.10` (nm, host glibc 2.41) |
| Thread-safety | `register_printf_function` MT-Unsafe (global lock, `printfext`; manual safety notes), `printf_size` MT-Safe race:fp, `parse_printf_format`/`printf_size_info` AS-safe (manual @safety annotations) |
| Ledger ID | GLIBC-parse_printf_format, GLIBC-register_printf_function, GLIBC-printf_size, GLIBC-printf_size_info |

## Declaration and gates

```c
#include <printf.h>

size_t parse_printf_format(const char *restrict fmt, size_t n,
                           int *restrict argtypes);
int register_printf_function(int spec, printf_function func,
                             printf_arginfo_function arginfo);
int printf_size(FILE *restrict fp, const struct printf_info *info,
                const void *const *restrict args);
int printf_size_info(const struct printf_info *restrict info,
                     size_t n, int *restrict argtypes);
```

All four are declared in `/usr/include/printf.h` with no internal
feature-test gate (lines 99-110, 137-138, 176-183); `printf.h` itself
is the gate. `register_printf_function` carries
`__attribute_deprecated__` (line 108).

## Semantics

`parse_printf_format` parses `fmt` and fills up to `n` entries of
`argtypes` with the type codes (`PA_INT`, `PA_STRING`, ..., or'd with
`PA_FLAG_LONG` etc.) each conversion needs, returning the number of
arguments required (manual, *Parsing a Template String*).
`register_printf_function` defines conversion `%spec` by pairing an
output handler with an arginfo function; flags like `#` and modifiers
like `l` cannot be registered, and a null `func` removes the handler
(manual, *Registering New Conversions*). `printf_size` is glibc's
predefined handler printing floats with `k`/`m`/`g`... suffixes --
powers of 1024 for lowercase specifiers, 1000 for uppercase -- together
with its mandatory `printf_size_info` arginfo function (manual,
*Predefined Printf Handlers*).

## Gotchas and portability

- glibc-only: musl 1.2.5 has no `printf.h` at all and none of these
  symbols (verified absence in `musl include/` and `src/`).
- Prefer `register_printf_specifier` (glibc 2.10): the old function
  cannot carry the size information user-defined types need.
- Registering at runtime mutates global printf state guarded by a
  non-recursive lock -- do not register from signal handlers or while
  other threads print (manual safety notes).
- musl absence means format-extension code needs a fallback path.

## References

- glibc manual: `stdio.texi`, nodes *Customizing Printf*,
  *Registering New Conversions*, *Predefined Printf Handlers*
- headers: `/usr/include/printf.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
