# statx(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 332 / 383 / 291 / 397 |
| Since (kernel) | 4.11 (glibc 2.28) |
| Man page | man2/statx.2 |
| glibc wrapper | statx() declared in <sys/stat.h>, AT_* constants from <fcntl.h>; host glibc 2.41 exports statx@@GLIBC_2.28 (nm -D); struct statx comes from the kernel UAPI header <linux/stat.h> |
| Aliases covered | none |
| Ledger ID | SC-statx |

## Purpose

statx() returns extended file status into a caller-supplied struct statx. It is the fd-relative, mask-driven successor to stat()/fstat()/lstat()/fstatat() (stat.md): the mask argument negotiates which fields the caller wants, the returned stx_mask reports which fields the kernel and filesystem actually filled, and the structure carries 64-bit sizes and inode numbers, sub-second timestamps including the creation time stx_btime, separate device IDs, a mount ID, and attribute flags. Fields the filesystem cannot provide get their stx_mask bit cleared even when requested, and the kernel may return unrequested fields for free. Because the mask is an extension mechanism, callers must not pass UINT_MAX; do the negotiation through the documented bits. statx() can also tune remote-filesystem synchronization behavior explicitly (AT_STATX_* sync modes), something stat() cannot express.

## Synopsis

```c
#include <fcntl.h>      /* Definition of AT_* constants */
#include <sys/stat.h>
int statx(int dirfd, const char *restrict pathname, int flags,
          unsigned int mask, struct statx *restrict statxbuf);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| dirfd | As for openat()/fstatat(): absolute pathname ignores it; relative + AT_FDCWD is cwd-relative; relative + directory fd is relative to that directory. With AT_EMPTY_PATH and an empty pathname, dirfd is the file itself (may be an O_PATH fd). |
| pathname | Path to the target file, or "" with AT_EMPTY_PATH. |
| flags | Lookup flags: AT_EMPTY_PATH, AT_NO_AUTOMOUNT, AT_SYMLINK_NOFOLLOW (like lstat). Plus exactly one sync mode: AT_STATX_SYNC_AS_STAT (default, filesystem-specific), AT_STATX_FORCE_SYNC (force server synchronization; may force writeback on network filesystems), AT_STATX_DONT_SYNC (use cached values, may be approximate). |
| mask | OR of STATX_* bits naming the wanted fields (table below). |
| statxbuf | Receives struct statx. |

struct statx (kernel UAPI layout, /usr/include/linux/stat.h; man2/statx.2 for the field semantics): stx_mask, stx_blksize, stx_attributes, stx_nlink, stx_uid, stx_gid, stx_mode, stx_ino, stx_size, stx_blocks, stx_attributes_mask, timestamps stx_atime/stx_btime/stx_ctime/stx_mtime (struct statx_timestamp: __s64 tv_sec, __u32 tv_nsec), stx_rdev_major/minor, stx_dev_major/minor, stx_mnt_id (5.8), then the newer alignment, subvolume, and atomic-write fields.

STATX_* mask bits (values from /usr/include/linux/stat.h; since dates from man2/statx.2 and the man-pages 6.19 statx.2 fetched from man7.org, source-cache/fetched/statx.2.current.plain):

| Constant | Value | Since | Wants |
|---|---|---|---|
| STATX_TYPE | 0x00000001 | 4.11 | stx_mode & S_IFMT |
| STATX_MODE | 0x00000002 | 4.11 | stx_mode & ~S_IFMT |
| STATX_NLINK | 0x00000004 | 4.11 | stx_nlink |
| STATX_UID | 0x00000008 | 4.11 | stx_uid |
| STATX_GID | 0x00000010 | 4.11 | stx_gid |
| STATX_ATIME | 0x00000020 | 4.11 | stx_atime |
| STATX_MTIME | 0x00000040 | 4.11 | stx_mtime |
| STATX_CTIME | 0x00000080 | 4.11 | stx_ctime |
| STATX_INO | 0x00000100 | 4.11 | stx_ino |
| STATX_SIZE | 0x00000200 | 4.11 | stx_size |
| STATX_BLOCKS | 0x00000400 | 4.11 | stx_blocks |
| STATX_BASIC_STATS | 0x000007ff | 4.11 | all of the above |
| STATX_BTIME | 0x00000800 | 4.11 | stx_btime |
| STATX_MNT_ID | 0x00001000 | 5.8 | stx_mnt_id |
| STATX_DIOALIGN | 0x00002000 | 6.1 | stx_dio_mem_align, stx_dio_offset_align |
| STATX_MNT_ID_UNIQUE | 0x00004000 | 6.8 | unique stx_mnt_id (listmount(2) namespace) |
| STATX_SUBVOL | 0x00008000 | 6.10 | stx_subvol (filesystem-dependent) |
| STATX_WRITE_ATOMIC | 0x00010000 | 6.11 | stx_atomic_write_unit_min, stx_atomic_write_unit_max, stx_atomic_write_segments_max, stx_atomic_write_unit_max_opt |
| STATX__RESERVED | 0x80000000 | 4.11 | reserved; passing it fails EINVAL |
| STATX_ALL | 0x00000fff | 4.11 | deprecated alias for STATX_BASIC_STATS plus STATX_BTIME; do not use |

stx_attributes bits (values from /usr/include/linux/stat.h; ATTR_* semantics from man2/statx.2; gated by stx_attributes_mask): STATX_ATTR_COMPRESSED 0x00000004, STATX_ATTR_IMMUTABLE 0x00000010, STATX_ATTR_APPEND 0x00000020, STATX_ATTR_NODUMP 0x00000040, STATX_ATTR_ENCRYPTED 0x00000800, STATX_ATTR_AUTOMOUNT 0x00001000, STATX_ATTR_MOUNT_ROOT 0x00002000, STATX_ATTR_VERITY 0x00100000 (5.5), STATX_ATTR_DAX 0x00200000 (5.8), STATX_ATTR_WRITE_ATOMIC 0x00400000 (6.11, file supports torn-write protection).

## Return value and errors

0 on success; on error -1 and errno: EACCES (search permission denied on a path prefix), EBADF (relative pathname with a dirfd that is neither AT_FDCWD nor valid), EFAULT (pathname or statxbuf outside the address space), EINVAL (invalid flag in flags; reserved mask bit STATX__RESERVED), ELOOP, ENAMETOOLONG, ENOENT (missing component; empty pathname without AT_EMPTY_PATH), ENOMEM, ENOTDIR (path component not a directory; relative pathname with a non-directory dirfd).

## Flags and constants

See the STATX_* and stx_attributes tables above. Atomic-write fields (sourced from man-pages 6.19 statx.2 fetched from man7.org this session; worklog 1-c flagged them as a follow-up): stx_atomic_write_unit_min and stx_atomic_write_unit_max give the power-of-2 size range supported for O_DIRECT torn-write-protected writes (RWF_ATOMIC on pwritev2(), write.md); stx_atomic_write_segments_max caps iovcnt for such writes; stx_atomic_write_unit_max_opt (man-pages 6.19 only) is the optimised upper bound, 0 meaning stx_atomic_write_unit_max is already optimised. STATX_WRITE_ATOMIC is supported on block devices since 6.11 and on regular files by xfs and ext4 since 6.13 (support varies by filesystem).

Version honesty: the cached man2/statx.2 (2021-08-27) stops at stx_mnt_id; the alignment (6.1), MNT_ID_UNIQUE (6.8), SUBVOL (6.10), and atomic-write (6.11+) fields come from the fetched man-pages 6.19 page and from /usr/include/linux/stat.h, which carries stx_atomic_write_unit_min/max and stx_atomic_write_segments_max but not stx_atomic_write_unit_max_opt (header older than the 6.19 man page on that one field).

## Security and notes

- No permission is needed on the file itself; search permission on every directory of the path prefix is required (man2/statx.2).
- Fields may reflect different moments: concurrent chmod()/chown() can yield an old stx_mode with a new stx_uid (VFS reads attributes without a lock; man page Note) -- true for stat() too.
- Mask negotiation is the API: a cleared stx_mask bit means "not available", not "zero"; dummy values may be filled for compatibility.
- stx_mnt_id matches name_to_handle_at(2) output and the first field of /proc/self/mountinfo records; the unique variant matches listmount(2)/statmount(2) IDs (fetched man page).
- The cached struct statx in glibc's <sys/stat.h> is the kernel UAPI definition; field offsets are fixed by the kernel, so callers must use the UAPI layout, not a locally declared one.

## References

- man2/statx.2 in the cached man-pages tree (dated 2021-08-27); man-pages 6.19 statx.2 fetched from man7.org (source-cache/fetched/statx.2.current.html and .plain).
- Constants and struct: /usr/include/linux/stat.h; AT_* constants: /usr/include/linux/fcntl.h.
- [Syscalls ledger](../ledger.md) row SC-statx; siblings [stat](stat.md), [write](write.md) (RWF_ATOMIC), [readv](readv.md); [domain hub](overview.md).
