# `access` / `faccessat` / `euidaccess` (3) - glibc

> Per-function page for the permission probes of the glibc File System
> Interface; see the [method page](../../../interface-encyclopedia.md) and
> the [glibc ledger](../../ledger-glibc.md) for coverage status. The real-uid
> vs effective-uid syscall story is in
> [access(2)](../../../syscalls/descriptors-io/access.md); a stdio-family
> sibling page exists at
> [../stdio/access-faccessat.md](../stdio/access-faccessat.md).

| Field | Value |
|---|---|
| Header | `unistd.h` (all four) |
| Standards | POSIX.1 (`access`), POSIX.1-2008 (`faccessat`), GNU (`euidaccess`, `eaccess`) |
| Exported | `access@@GLIBC_2.2.5`, `faccessat@@GLIBC_2.4`, `euidaccess@@GLIBC_2.2.5`, `eaccess@@GLIBC_2.4` (nm, host glibc 2.41; `eaccess` and `euidaccess` share one address - alias evidence). No `faccessat2` symbol exists in glibc 2.41 (nm negative check, matching the syscall chapter's faccessat2 story) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe on `access` (manual annotation); `faccessat` unaudited in the manual (default unsafe marks) |
| Ledger ID | GLIBC-access, GLIBC-faccessat (documented, access/faccessat group), GLIBC-euidaccess (triage row) |

## Declaration and gates

```c
#include <unistd.h>

int access(const char *name, int type);   /* F_OK R_OK W_OK X_OK */
int faccessat(int fd, const char *file, int type, int flag);
int euidaccess(const char *name, int type);
int eaccess(const char *name, int type);  /* alias of euidaccess */
```

## Semantics

`access` checks whether the *real* user and group IDs could access `name` in
the way `type` requests (`R_OK`, `W_OK`, `X_OK`, or existence `F_OK`): it
returns 0 if permitted and -1 otherwise, so as a predicate it is true when
access is *denied* (manual). The real-ID choice exists for setuid programs,
whose effective ID differs from the user who ran them; the manual says
`access` is "only appropriate to use in setuid programs" because everyone
else's effective IDs already decide. `faccessat` is the descriptor-relative
twin whose `flag` may carry `AT_EACCESS` (check effective IDs instead),
`AT_EMPTY_PATH` and `AT_SYMLINK_NOFOLLOW` (manual). `euidaccess`/`eaccess`
check effective IDs by path (GNU).

## Gotchas and portability

- TOCTOU: man2 `access.2` warns that check-then-open leaves a window the
  user can exploit; when possible, drop privileges and just try the open.
- The `AT_*` flags story: the raw `faccessat` syscall has no flags argument,
  so glibc emulated them (pre-2.33 via `fstatat`, man2 BUGS wording); Linux
  5.8 added `faccessat2`, and the manual notes `faccessat` "may not work
  correctly on older kernels missing the faccessat2 system call". glibc
  2.41 still exports only `faccessat` (nm).
- musl 1.2.5: `src/unistd/access.c` calls `SYS_access`, falling back to
  `faccessat` with zero flags; `src/legacy/euidaccess.c` implements the
  effective-ID probe.

## References

- glibc manual: `filesys.texi`, node *Testing File Access*
- man2: `access.2` (faccessat2 section, BUGS, security note)
- headers: `/usr/include/unistd.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
