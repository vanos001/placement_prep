# landlock_create_ruleset(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | landlock_create_ruleset 444 / 444 / 444 / 444; landlock_add_rule 445 / 445 / 445 / 445; landlock_restrict_self 446 / 446 / 446 / 446 (identical across the four tables; cached kernel tables and hub agree) |
| Since (kernel) | 5.13 (fetched man HISTORY: "Linux 5.13"; hub agrees) |
| Man page | NOT in the local man2 cache. Fetched this session from man7.org (man-pages 6.19): landlock_create_ruleset.2 (2026-04-21), landlock_add_rule.2 (2026-05-04), landlock_restrict_self.2 (2026-05-04), landlock.7; text copies cached in source-cache/fetched/ |
| glibc wrapper | None (nm -D on glibc 2.41 shows no landlock symbols); all three are invoked via `syscall(SYS_landlock_*, ...)` as documented in the fetched man pages |
| Aliases covered | landlock_add_rule, landlock_restrict_self (one page per the three-syscall API per task brief; hub/ledger rows SC-landlock_add_rule and SC-landlock_restrict_self point at separate pages not written by this task -- merge note) |
| Ledger ID | SC-landlock_create_ruleset (family: SC-landlock_add_rule, SC-landlock_restrict_self) |

## Purpose

Landlock is an unprivileged access-control (sandboxing) facility enabled by
`CONFIG_SECURITY_LANDLOCK`. The API is a three-call protocol over file
descriptors: (1) `landlock_create_ruleset()` creates a ruleset file descriptor
that declares which access rights the ruleset will *handle* (deny by default
once enforced); (2) `landlock_add_rule()` populates the ruleset with
per-object exceptions; (3) `landlock_restrict_self()` enforces the ruleset on
the calling thread, composing it with any existing Landlock domain. Restrictions
can only grow: an enforced domain constrains the thread and all its future
children for their entire life (fetched man pages, landlock.7).

## Synopsis

    #include <linux/landlock.h>
    int syscall(SYS_landlock_create_ruleset,
                const struct landlock_ruleset_attr *attr, size_t size,
                uint32_t flags);
    int syscall(SYS_landlock_add_rule, int ruleset_fd,
                enum landlock_rule_type rule_type, const void *rule_attr,
                uint32_t flags);            /* flags must be 0 */
    int syscall(SYS_landlock_restrict_self, int ruleset_fd, uint32_t flags);

## Arguments and behavior

`struct landlock_ruleset_attr` (installed linux/landlock.h):
`handled_access_fs` (bitmask of `LANDLOCK_ACCESS_FS_*`), `handled_access_net`
(`LANDLOCK_ACCESS_NET_*`, ABI v4), `scoped` (`LANDLOCK_SCOPE_*`). `size` must
be `sizeof(struct landlock_ruleset_attr)`. Ruleset flags: 0 with an `attr`, or
`LANDLOCK_CREATE_RULESET_VERSION` (1U << 0), which returns the highest
supported Landlock ABI version, or `LANDLOCK_CREATE_RULESET_ERRATA` (1U << 1),
which returns a bitmask of fixed errata; both require NULL `attr` and size 0.

| Rule type | Value | rule_attr |
|---|---|---|
| `LANDLOCK_RULE_PATH_BENEATH` | 1 | `struct landlock_path_beneath_attr { __u64 allowed_access; __s32 parent_fd; }` (packed); `parent_fd` is an fd, preferably opened `O_PATH`, on the allowed hierarchy |
| `LANDLOCK_RULE_NET_PORT` | 2 (ABI v4) | `struct landlock_net_port_attr { __u64 allowed_access; __u64 port; }`; port in host byte order, 0 means the ephemeral bind range for `LANDLOCK_ACCESS_NET_BIND_TCP` |

Filesystem access rights (installed linux/landlock.h; ABI-version notes from
fetched landlock.7):

| Right | Value | ABI |
|---|---|---|
| `LANDLOCK_ACCESS_FS_EXECUTE` | 1ULL << 0 | 1 |
| `LANDLOCK_ACCESS_FS_WRITE_FILE` | 1ULL << 1 | 1 |
| `LANDLOCK_ACCESS_FS_READ_FILE` | 1ULL << 2 | 1 |
| `LANDLOCK_ACCESS_FS_READ_DIR` | 1ULL << 3 | 1 |
| `LANDLOCK_ACCESS_FS_REMOVE_DIR` | 1ULL << 4 | 1 |
| `LANDLOCK_ACCESS_FS_REMOVE_FILE` | 1ULL << 5 | 1 |
| `LANDLOCK_ACCESS_FS_MAKE_CHAR` | 1ULL << 6 | 1 |
| `LANDLOCK_ACCESS_FS_MAKE_DIR` | 1ULL << 7 | 1 |
| `LANDLOCK_ACCESS_FS_MAKE_REG` | 1ULL << 8 | 1 |
| `LANDLOCK_ACCESS_FS_MAKE_SOCK` | 1ULL << 9 | 1 |
| `LANDLOCK_ACCESS_FS_MAKE_FIFO` | 1ULL << 10 | 1 |
| `LANDLOCK_ACCESS_FS_MAKE_BLOCK` | 1ULL << 11 | 1 |
| `LANDLOCK_ACCESS_FS_MAKE_SYM` | 1ULL << 12 | 1 |
| `LANDLOCK_ACCESS_FS_REFER` | 1ULL << 13 | 2 (denied by default even when not handled) |
| `LANDLOCK_ACCESS_FS_TRUNCATE` | 1ULL << 14 | 3 |
| `LANDLOCK_ACCESS_FS_IOCTL_DEV` | 1ULL << 15 | 5 |

Network rights: `LANDLOCK_ACCESS_NET_BIND_TCP` (1ULL << 0),
`LANDLOCK_ACCESS_NET_CONNECT_TCP` (1ULL << 1), both ABI v4. Scope rights:
`LANDLOCK_SCOPE_ABSTRACT_UNIX_SOCKET` (1ULL << 0) and
`LANDLOCK_SCOPE_SIGNAL` (1ULL << 1), ABI v6 per fetched landlock.7.

`landlock_restrict_self()` requires the `no_new_privs` bit
(`prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)`) or `CAP_SYS_ADMIN` in the user
namespace -- the same rule as [seccomp(2)](seccomp.md) -- to keep unprivileged
processes from constraining privileged children. Restrict flags (fetched
restrict_self page): `LANDLOCK_RESTRICT_SELF_LOG_SAME_EXEC_OFF`,
`LANDLOCK_RESTRICT_SELF_LOG_NEW_EXEC_ON`,
`LANDLOCK_RESTRICT_SELF_LOG_SUBDOMAINS_OFF` (all ABI v7, audit-logging
controls) and `LANDLOCK_RESTRICT_SELF_TSYNC` (ABI v8, apply atomically to all
threads). These four names are NOT defined by the installed linux/landlock.h
(header gap; source is the fetched man page).

## Return value and errors

`landlock_create_ruleset()` returns a new ruleset fd, an ABI version, or an
errata bitmask according to flags; the other two return 0 on success. Errors:
create -- `E2BIG` (size too big), `EFAULT`, `EINVAL` (unknown flags/access/
scope, too small size, or attr/size combined with VERSION/ERRATA), `ENOMSG`
(empty handled accesses), `EOPNOTSUPP` (Landlock disabled at boot);
add_rule -- `EAFNOSUPPORT` (TCP unsupported), `EBADF`, `EBADFD` (fd is not a
ruleset), `EFAULT`, `EINVAL` (nonzero flags; allowed_access not a subset of
handled accesses; directory-only rights on a file; port > 65535), `ENOMSG`
(empty allowed_access), `EOPNOTSUPP`, `EPERM` (no write access to the ruleset);
restrict_self -- `E2BIG` (composed-ruleset limit, currently 64), `EBADF`,
`EBADFD`, `EINVAL` (invalid flags), `EOPNOTSUPP`, `EPERM` (no read access, and
neither no_new_privs nor CAP_SYS_ADMIN).

## Flags and constants

See tables above. Feature discovery rule from landlock.7: query the ABI version
rather than testing kernel versions; access rights missing from an older ABI
must not be set in `handled_access_fs` or the ruleset creation fails.

## Security and notes

Files and directories opened before `landlock_restrict_self()` are not subject
to the restrictions (landlock.7 caveats). Some actions are not restrictable
even in current ABIs: chdir(2), stat(2), flock(2), chmod(2), chown(2),
setxattr(2), utime(2), fcntl(2), access(2) (landlock.7 CAVEATS). The `lsm=`
boot parameter must include `landlock` (or CONFIG_LSM default must);
`landlock: Up and running.` in the kernel log confirms it. Denied accesses are
audit-logged by default for self-sandboxed programs.

## References

- Fetched man pages (man7.org, man-pages 6.19): text cached at
  `source-cache/fetched/landlock_create_ruleset.2.txt`,
  `landlock_add_rule.2.txt`, `landlock_restrict_self.2.txt`, `landlock.7.txt`
- Header: installed `/usr/include/linux/landlock.h`
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (444-446; same on all
  four archs)
- Online: https://man7.org/linux/man-pages/man2/landlock_create_ruleset.2.html
