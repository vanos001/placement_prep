# `chmod` / `fchmod` / `chown` / `umask` (3) - glibc

> Per-function page for the permission and ownership mutators of the glibc
> File System Interface family; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Kernel side:
> [umask(2)](../../../syscalls/descriptors-io/umask.md) is documented in the
> syscall chapter; `chmod(2)` has no per-call page there at write time.

| Field | Value |
|---|---|
| Header | `sys/stat.h` (`chmod`, `fchmod`, `umask`, `getumask`); `unistd.h` (`chown`, `fchown`, `fchownat`) |
| Standards | POSIX.1 (`chmod`, `umask`, `chown`), BSD (`fchmod`, `fchown`), POSIX.1-2008 (`fchmodat`, `fchownat`), GNU (`getumask`) |
| Exported | `chmod`/`fchmod`/`umask`/`chown`/`fchown` `@@GLIBC_2.2.5`; `fchmodat`/`fchownat` `@@GLIBC_2.4`; `getumask` NOT exported by glibc 2.41 (nm negative check) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual safety annotations); `umask` is a process-global property, not per-thread |
| Ledger ID | GLIBC-chmod, GLIBC-fchmod, GLIBC-chown, GLIBC-fchown (documented), GLIBC-fchownat (triage), GLIBC-umask (researched) |

## Declaration and gates

```c
#include <sys/stat.h>
#include <unistd.h>

int chmod(const char *file, mode_t mode);
int fchmod(int fd, mode_t mode);
int fchmodat(int fd, const char *file, mode_t mode, int flag); /* __USE_ATFILE */
int chown(const char *file, uid_t owner, gid_t group);   /* unistd.h */
int fchown(int fd, uid_t owner, gid_t group);
int fchownat(int fd, const char *file, uid_t owner,
             gid_t group, int flag);                     /* __USE_ATFILE */
mode_t umask(mode_t mask);
mode_t getumask(void);                                   /* __USE_GNU, Hurd */
```

Permission bit macros (`S_IRUSR` 0400 ... `S_ISVTX` sticky 01000) come from
`sys/stat.h`; the manual notes the octal values are typical, not guaranteed,
and urges symbolic names.

## Semantics

`umask` sets the file-creation mask and returns the previous one; bits set in
the mask are "always to be disabled" in every later `open`/`mkdir`-style
mode argument (manual, *Setting Permissions*). `chmod` sets the permission
bits of an existing file and ignores the umask; on a symlink it acts on the
target. `chown`/`fchown` change owner and group; changing owner may clear the
set-user-ID and set-group-ID bits (manual). Only the owner (by effective UID)
or a privileged process may change either (manual, `EPERM`).

## Gotchas and portability

- The manual's own advice for bypassing the umask: open the file, then
  `fchmod` it; changing the umask is normally shells' business only.
- Reading the mask without losing it takes two calls (`umask(0); umask(old)`,
  manual example). `getumask` exists only on the GNU Hurd (header comment,
  manual) and has no glibc symbol on this host.
- `EFTYPE`: some systems refuse the sticky bit on non-directories via
  `chmod`; the manual says clearing `S_ISVTX` and retrying is always safe.
- musl 1.2.5: `src/stat/chmod.c` calls `SYS_chmod` (or `fchmodat`), and
  `src/stat/umask.c` is a direct `SYS_umask` call.

## References

- glibc manual: `filesys.texi`, nodes *Permission Bits*, *Setting
  Permissions*, *File Owner*
- man2: `chmod.2`, `umask.2`
- headers: `/usr/include/x86_64-linux-gnu/sys/stat.h`, `/usr/include/unistd.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
