# `getuid` / `geteuid` / `getgid` / `getegid` (2, via unistd.h) - glibc

> Split from the chapter *glibc: Users and Groups* into the per-function layout; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `unistd.h` (prototypes unconditional; `uid_t`/`gid_t` from `sys/types.h`) |
| Standards | POSIX.1-2001/2008; 4.3BSD origin (`getuid(2)` CONFORMING TO) |
| Exported | `getuid`, `geteuid`, `getgid`, `getegid` all `@@GLIBC_2.2.5` weak -- direct syscall wrappers (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (manual safety annotations, `users.texi` *Reading Persona*; `getuid(2)` predates the ATTRIBUTES convention and carries none) |
| Ledger ID | GLIBC-getuid, GLIBC-geteuid, GLIBC-getgid, GLIBC-getegid |

## Declaration and gates

```c
#include <unistd.h>

uid_t getuid(void);   /* real user ID   */
uid_t geteuid(void);  /* effective UID  */
gid_t getgid(void);   /* real group ID  */
gid_t getegid(void);  /* effective GID  */
```

All four prototypes are unconditional in `/usr/include/unistd.h`:
`getuid` line 697, `geteuid` 700, `getgid` 703, `getegid` 706. In
glibc, `uid_t` and `gid_t` are aliases of `unsigned int` (manual,
*Reading Persona* deftype notes).

## Semantics

Each process carries a credential set: real and effective user and
group IDs plus saved set-IDs and the supplementary groups. `getuid`
returns the real user ID (who invoked the program), `geteuid` the
effective one (whose permissions the process uses -- the two differ
exactly in set-user-ID execution); `getgid`/`getegid` are the group
analogues. These wrappers never fail: `getuid(2)` states "These functions are
always successful and never modify `errno`" (and the header marks them
`__THROW`).

## Gotchas and portability

- The classic persona trap: a set-user-ID program that needs its
  invoker's identity must use `getuid`, not `geteuid` -- and for login
  name, `getpwuid(geteuid())` differs from `getlogin()`
  (see [getlogin page](getlogin-cuserid.md), manual *Who Logged In*).
- On 32-bit x86 the kernel entry points are the `*32` twins
  (`getuid32.2` etc.); 64-bit ABIs have single syscalls -- visible in
  `strace`, not in the API.
- Changing identities is the subject of the
  [setuid family page](setuid-family.md); the raw syscall pages live in
  [getuid](../../../syscalls/process/getuid.md) and
  [getgid](../../../syscalls/process/getgid.md).
- musl 1.2.5: same four thin wrappers (`src/unistd/getuid.c`,
  `geteuid.c`, `getgid.c`, `getegid.c`).

## References

- glibc manual: `users.texi`, nodes *User and Group IDs*, *Process
  Persona*, *Reading Persona*
- man2: `getuid.2` (covers `geteuid`), `getgid.2`, `getegid.2`
- headers: `/usr/include/unistd.h`, `sys/types.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
