# `setuid` / `seteuid` / `setgid` / `setegid` / `setreuid` / `setregid` (2, via unistd.h) - glibc

> Split from the chapter *glibc: Users and Groups* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `unistd.h` (prototypes unconditional) |
| Standards | `setuid`, `setgid`: POSIX.1; `seteuid`, `setegid`: POSIX.1-2001 (`_POSIX_C_SOURCE >= 200112` or `_BSD_SOURCE`, `seteuid(2)`); `setreuid`, `setregid`: XSI (`_XOPEN_SOURCE >= 500` or `_DEFAULT_SOURCE`) |
| Exported | `setuid`, `setgid`, `setreuid`, `setregid` weak `@@GLIBC_2.2.5` (syscall aliases); `seteuid`, `setegid` `@@GLIBC_2.2.5` regular (libc-side, built on `setresuid`/`setresgid`) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe with `asulock`/`aculock` -- the setxid broadcast marks other threads and signals them with `SIGSETXID` (manual safety comments, `users.texi` *Setting User ID*) |
| Ledger ID | GLIBC-setuid, GLIBC-seteuid, GLIBC-setgid, GLIBC-setegid, GLIBC-setreuid, GLIBC-setregid |

## Declaration and gates

```c
#include <unistd.h>

int setuid(uid_t uid);                     /* unistd.h line 722 */
int seteuid(uid_t uid);                    /* line 732 */
int setreuid(uid_t ruid, uid_t euid);      /* line 727 */
int setgid(gid_t gid);                     /* line 739 */
int setegid(gid_t gid);                    /* line 749 */
int setregid(gid_t rgid, gid_t egid);      /* line 744 */
```

All unconditional in `/usr/include/unistd.h`, each marked
`__THROW __wur` -- the warn-unused-result attribute encodes the
security rule that the return value must be checked.

## Semantics

`setuid` sets the effective user ID; for a process with `CAP_SETUID`
it also sets real and saved set-user-ID -- so a setuid-root program
that calls `setuid(nonroot)` can never regain root, the POSIX
`_POSIX_SAVED_IDS` behavior (`setuid(2)`). To drop and regain
privileges, use `seteuid`: an unprivileged process may set its
effective ID to real, effective or saved value; `setegid` is the same
for groups. `setreuid`/`setregid` set real and effective IDs
independently, with -1 meaning "unchanged"; setting the real ID (or an
effective ID different from the previous real one) also moves the
saved ID to the new effective value (`setreuid(2)`). In an NPTL
program the identity change is broadcast to every thread via
`SIGSETXID` (manual *Setting User ID* implementation comments).

## Gotchas and portability

- "There are cases where `setuid()` can fail even when the caller is
  UID 0; it is a grave security error to omit checking" (`setuid(2)`,
  `setreuid(2)`, `seteuid(2)` all carry this note).
- glibc implements `seteuid`/`setegid` on `setresuid`/`setresgid`, so
  an interrupted `seteuid` can leave all three IDs altered -- see
  [setresuid](../../../syscalls/process/setresuid.md).
- Syscall-level detail lives in
  [setuid](../../../syscalls/process/setuid.md) and
  [setreuid](../../../syscalls/process/setreuid.md); manual rationale in
  *Why Change Persona* / *How Change Persona*.
- musl 1.2.5: all six present (`src/unistd/setuid.c`, `seteuid.c`,
  `setgid.c`, `setegid.c`, `setreuid.c`, `setregid.c`), same syscall
  basis.

## Errors

`EPERM` (unprivileged change outside the allowed set), `EINVAL` (ID
invalid in the user namespace), `EAGAIN` (`setreuid`: `RLIMIT_NPROC`
hit; no longer since Linux 3.1 but still worth checking).

## References

- glibc manual: `users.texi`, nodes *Setting User ID*, *Why Change
  Persona*, *How Change Persona*, *Enable/Disable Setuid*
- man2: `setuid.2`, `seteuid.2` (covers `setegid`), `setreuid.2`
  (covers `setregid`), `setgid.2`
- header: `/usr/include/unistd.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
