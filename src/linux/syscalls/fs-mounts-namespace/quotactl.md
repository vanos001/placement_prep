# quotactl(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | quotactl: x64 179 / i386 131 / arm64-generic 60 / arm32 131; quotactl_fd: x64 443 / i386 443 / arm64-generic 443 / arm32 443 |
| Since (kernel) | 1.0 (quotactl); quotactl_fd 5.14 (fetched man page HISTORY; ledger 5.14) |
| Man page | man2/quotactl.2 (cached, 2021-03-22) covers quotactl and the Q_* commands; quotactl_fd.2 fetched from man7.org (man-pages 6.19, shares one page titled quotactl(2)) |
| glibc wrapper | Yes for `quotactl()` (`<sys/quota.h>`); no wrapper for `quotactl_fd()` -- use `syscall(2)` |
| Aliases covered | `quotactl_fd` (SC-quotactl_fd) |
| Ledger ID | SC-quotactl |

## Purpose

The quota system sets per-user, per-group and (since 4.1) per-project limits
on disk space and inode usage per filesystem: a hard limit that cannot be
exceeded and a soft limit that may be exceeded only for the grace period
(one week by default). `quotactl()` operates on a named block device;
`quotactl_fd()` (5.14) operates on a file descriptor for any file or
directory on the target filesystem, which works for filesystems without a
backing block device (tmpfs) and avoids `/proc/self/mounts` scanning.

## Synopsis

    #include <sys/quota.h>
    int quotactl(int cmd, const char *special, int id, caddr_t addr);

    /* via syscall(2): */
    int syscall(SYS_quotactl_fd, int fd, int op, int id, caddr_t addr);

## Arguments and behavior

`cmd` is built with the `QCMD(subop, type)` macro. `type` is `USRQUOTA`,
`GRPQUOTA`, or `PRJQUOTA` (since 4.1); `id` is the user/group/project ID.
For `quotactl()`, `special` names the mounted block device; for
`quotactl_fd()`, `fd` may be opened `O_PATH`. `addr` points to an
operation-specific structure copied in or out.

## Return value and errors

Returns 0 on success, -1 on error: `EACCES` (Q_QUOTAON quota file wrong type
or filesystem), `EBUSY` (quotas already on), `EFAULT`, `EINVAL` (bad cmd or
type; corrupt quota file; bad Q_XQUOTARM types since 5.5), `ENOENT`,
`ENOSYS` (kernel without `CONFIG_QUOTA`), `ENOTBLK` (`special` not a block
device), `EPERM` (missing `CAP_SYS_ADMIN`), `ERANGE` (Q_SETQUOTA limits out
of format range), `ESRCH` (no quota for the ID; quotas off; quota format
missing; no next ID for Q_GETNEXTQUOTA).

## Flags and constants (Q_* suboperations)

| Subop | Meaning | Since |
|---|---|---|
| `Q_QUOTAON` | Enable enforcement; `addr` names the quota file; format in `id`: `QFMT_VFS_OLD`, `QFMT_VFS_V0`, `QFMT_VFS_V1` (32-bit IDs, 2^64-byte limits); hidden system inodes need no quota file; `CAP_SYS_ADMIN` | 1.0 |
| `Q_QUOTAOFF` | Disable quotas; `CAP_SYS_ADMIN` | 1.0 |
| `Q_GETQUOTA` | Fill `struct dqblk` (limits, usage, grace times, `QIF_*` validity bits); unprivileged users may query their own quota | 1.0 |
| `Q_GETNEXTQUOTA` | Like Q_GETQUOTA for the next ID >= `id` with a quota (`struct nextdqblk`) | 4.6 |
| `Q_SETQUOTA` | Write limits/usage from a `dqblk` (`dqb_valid` selects fields); `CAP_SYS_ADMIN` | 1.0 |
| `Q_GETINFO` / `Q_SETINFO` | Read/write `struct dqinfo` (grace times, `DQF_ROOT_SQUASH`, `DQF_SYS_FILE`) | 2.4.22 |
| `Q_GETFMT` | 4-byte buffer receives the quota format number | 2.4.22 |
| `Q_SYNC` | Flush on-disk quota usage; NULL `special` syncs all active filesystems | 1.0 |
| `Q_GETSTATS` | Quota subsystem statistics; removed 2.4.22 (use `/proc/sys/fs/quota/`) | <= 2.4.21 |
| `Q_XQUOTAON` ... `Q_XQUOTASYNC` | XFS Quota Manager operations (`<xfs/xqm.h>`; XFS_QUOTA_[UGP]DQ_ACCT/ENFD flags, `fs_disk_quota`, `fs_quota_stat[v]`) | Q_XQUOTASYNC no-op since 3.4; Q_XQUOTARM 3.16 |

## Security and notes

Most operations require `CAP_SYS_ADMIN`; `Q_GETQUOTA` self-queries and
`Q_SYNC` are the common exceptions (the man page marks the privileged ones
explicitly). Prefer `quotactl_fd()` for new code: device-path-based lookup
breaks on deviceless filesystems. The XFS header `<linux/dqblk_xfs.h>`
alternative drops the leading `X` from flag names (FS_QUOTA_* / FS_*_QUOTA)
-- naming discrepancies documented in man NOTES. Limits in `dqblk` are
bytes/inodes, 2^64-capable in the V1 format. Note this is a per-filesystem
storage limit mechanism, distinct from per-process `getrlimit(2)` resource
limits.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/quotactl.2`
- Fetched: `source-cache/fetched/quotactl_fd.2.txt` + `.html` (man-pages 6.19,
  HISTORY: quotactl_fd Linux 5.14)
- Online: https://man7.org/linux/man-pages/man2/quotactl.2.html
- Constants: `/usr/include/x86_64-linux-gnu/sys/quota.h`;
  kernel tables `source-cache/kernel/syscall_64.tbl` (179, 443)
