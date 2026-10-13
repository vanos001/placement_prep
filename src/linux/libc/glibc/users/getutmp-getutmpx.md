# `getutmp` / `getutmpx` (3) - glibc

> Split from the chapter *glibc: Users and Groups* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `utmpx.h`, under `__USE_GNU` |
| Standards | Nonstandard glibc extension, also on Solaris and NetBSD (`getutmp(3)` CONFORMING TO) |
| Exported | `getutmp@@GLIBC_2.2.5`, `getutmpx@@GLIBC_2.2.5`; nm shows both at the same address, 0x15e890 (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`getutmp(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-getutmp, GLIBC-getutmpx |

## Declaration and gates

```c
#define _GNU_SOURCE
#include <utmpx.h>

void getutmp(const struct utmpx *ux, struct utmp *u);
void getutmpx(const struct utmp *u, struct utmpx *ux);
```

Both prototypes sit inside the `#ifdef __USE_GNU` block of
`/usr/include/utmpx.h` (lines 86-121, `getutmp` at 111, `getutmpx` at
120). The gate at lines 42-44 forward-declares `struct utmp`, because
plain `<utmpx.h>` would not otherwise make the type visible.

## Semantics

`getutmp` copies the fields of a `struct utmpx` into the corresponding
fields of a `struct utmp`; `getutmpx` performs the converse. Neither
function touches any database file -- they are pure struct converters,
returning no value. On Linux the two structures have the same fields
with the same sizes (manual, *XPG User Accounting Database*: "identical
to `struct utmp` except that including `utmpx.h` does not make visible
the declaration of `struct exit_status`"), so both functions compile to
a member-wise copy; nm confirming one shared address shows they are
interchangeable aliases on this platform.

## Gotchas and portability

- The functions exist for systems where `struct utmpx` is a superset of
  `struct utmp` with larger fields (Solaris keeps parallel
  `utmpx`/`wtmpx` files); code that must be portable to those systems
  converts through these helpers instead of assigning one struct to the
  other.
- Because the Linux structures agree, dropping the conversion is
  tempting, but a plain struct assignment would break compilation on
  SVr4-derived systems where it is required.
- First appeared in glibc 2.1.1 (`getutmp(3)` VERSIONS).
- musl 1.2.5: absent -- `include/utmpx.h` declares no `getutmp`/`getutmpx`
  and no sources implement them; musl's `utmp` family lives in
  `src/legacy/utmpx.c` and is stubbed anyway.

## References

- glibc manual: `users.texi`, node *XPG Functions* (struct equality note)
- man3: `getutmp.3` (covers `getutmpx`)
- headers: `/usr/include/utmpx.h`
- siblings: [utmpx page](utmpx-getutxent-family.md),
  [utmp page](utmp-getutent-family.md)
- symbols: `nm -D --with-symbol-versions libc.so.6`
