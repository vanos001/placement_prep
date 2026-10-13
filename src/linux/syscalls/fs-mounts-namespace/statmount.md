# statmount(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | statmount: x64 457 / i386 457 / arm64-generic 457 / arm32 457; listmount: x64 458 / i386 458 / arm64-generic 458 / arm32 458 |
| Since (kernel) | 6.8 for both (worklog 1-d tag probe of asm-generic unistd.h: present v6.8, absent v6.7; ledger date "--"; man pages state no version) |
| Man page | statmount.2 / listmount.2 fetched from man7.org (man-pages 6.19), cached at `source-cache/fetched/statmount.2.txt` and `listmount.2.txt`; no glibc-wrapped release |
| glibc wrapper | None for either -- both are invoked via `syscall(2)` |
| Aliases covered | `listmount` (SC-listmount) |
| Ledger ID | SC-statmount |

## Purpose

`statmount()` returns a structured snapshot of one mount (superblock and
mount properties); `listmount()` walks the mount tree by returning batches
of mount IDs. Together they replace the parse-`/proc/self/mountinfo` idiom
with a stable binary interface. Requires `CAP_SYS_ADMIN` in the user
namespace; a foreign mount namespace may be queried only if it is a child
of the caller's.

## Synopsis

    #include <linux/mount.h>   /* STATMOUNT_* constants */
    #include <unistd.h>
    int syscall(SYS_statmount, struct mnt_id_req *req,
                struct statmount *smbuf, size_t bufsize, unsigned int flags);
    int syscall(SYS_listmount, struct mnt_id_req *req,
                uint64_t mnt_ids[n], size_t n, unsigned long flags);

    struct mnt_id_req {
        __u32 size;          /* sizeof(struct mnt_id_req) */
        union {
            __u32 mnt_ns_fd; /* fd of foreign mnt_ns (since 6.18) */
            __u32 mnt_fd;    /* fd on a mount (STATMOUNT_BY_FD, since 7.0) */
        };
        __u64 mnt_id;        /* mount being queried / parent to list under */
        __u64 param;         /* STATMOUNT_* mask / resume point for listmount */
        __u32 mnt_ns_id;     /* foreign mnt_ns id (since 6.11) */
    };

## Arguments and behavior

For `statmount()`, `req.mnt_id` identifies the mount (from `statx(2)` with
`STATX_MNT_ID_UNIQUE` or from `listmount()`); `req.param` is an OR of
`STATMOUNT_*` request bits (`SB_BASIC`, `MNT_BASIC`, `PROPAGATE_FROM`,
`MNT_ROOT`, `MNT_POINT`, `FS_TYPE`, `MNT_NS_ID`, `MNT_OPTS`, `FS_SUBTYPE`,
`SB_SOURCE`, `OPT_ARRAY`, `OPT_SEC_ARRAY`, `MNT_UIDMAP`, `MNT_GIDMAP`,
`SUPPORTED_MASK`); `flags` is 0 or `STATMOUNT_BY_FD` (since 7.0). The kernel
fills `struct statmount` (fixed fields plus a trailing `char str[]` area
holding offset-addressed strings) and reports what it supplied in
`smbuf.mask`. Do not set `req.param` to all bits -- future bits may change
the buffer layout. For `listmount()`, `req.mnt_id` is the parent mount
(`LSMT_ROOT` for the namespace root) and `req.param` is the resume point
(last returned ID); the call fills up to `n` entries.

## Return value and errors

`statmount()` returns 0 on success; `listmount()` returns the number of
entries filled, 0 when no mounts remain. Both return -1 on error: `EPERM`
(missing `CAP_SYS_ADMIN`), `EFAULT`, `EINVAL` (bad flags; undersized
`req`; both `mnt_ns_id` and `mnt_ns_fd` set; id/`mnt_ns_id` alongside
`mnt_fd`), `EBADF` (bad `mnt_fd`), `E2BIG` (`req` too large; listmount
limit is the page size), `EOVERFLOW` (`smbuf` too small for the strings --
retry with a larger buffer), `ENOENT` (unknown `mnt_id`), `ENOMEM`.

## Flags and constants

| Constant | Meaning | Since |
|---|---|---|
| `STATMOUNT_BY_FD` | Query the mount holding `req.mnt_fd` instead of `req.mnt_id` | 7.0 |
| `LSMT_ROOT` | listmount pseudo-ID for the namespace root mount | 6.8 |
| `mnt_ns_id` field | Query a foreign mount namespace by its unique ID | 6.11 |
| `smbuf.mnt_opts`, `smbuf.mnt_ns_id` | Mount options string; owning mount namespace ID | 6.11 |
| `fs_subtype`, `sb_source`, `opt_*` array fields | Subtype/source strings; per-option arrays | 6.13 |
| `mnt_uidmap`/`mnt_gidmap`/`supported_mask` | ID-mapping strings; kernel-supported STATMOUNT mask | 6.15 |
| `req.mnt_ns_fd` | Foreign namespace by pidfd/`/proc/pid/ns/mnt` fd | 6.18 |

## Security and notes

Version honesty: the syscall pair dates to 6.8 (worklog 1-d probe), but most
`struct statmount` fields are 6.9+ extensions as tabled above; the
`mnt_ns_fd` (6.18) and `STATMOUNT_BY_FD` (7.0) additions come from the live
man-pages 6.19 page and are release-pinned only by that document. Iterate
the whole tree by listing under `LSMT_ROOT` recursively, or combine with
[open_tree.md](open_tree.md) / [move_mount.md](move_mount.md) for
fd-based mount management; [umount2.md](umount2.md) `MNT_DETACH` mounts
report without `MNT_POINT`/`MNT_NS_ID`.

## References

- Fetched man pages: `source-cache/fetched/statmount.2.txt`, `listmount.2.txt`
  (man-pages 6.19)
- Online: https://man7.org/linux/man-pages/man2/statmount.2.html
- Version pins: worklog Task 1-d (unistd.h tag probes v6.7/v6.8);
  `SYS_statmount`/`SYS_listmount` in `<bits/syscall.h>`
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (457, 458, `common`)
