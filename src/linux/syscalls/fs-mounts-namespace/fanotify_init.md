# fanotify_init(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 300 / i386 338 / arm64-generic 262 / arm32 367 |
| Since (kernel) | 2.6.37 (introduced 2.6.36, enabled 2.6.37; man VERSIONS; hub 2.6.37) |
| Man page | man2/fanotify_init.2 (cached, 2021-08-27); overview in fanotify(7) |
| glibc wrapper | Yes; `<sys/fanotify.h>` |
| Aliases covered | none |
| Ledger ID | SC-fanotify_init |

## Purpose

`fanotify_init()` initializes a new fanotify group and returns a file
descriptor for its event queue. Marks are attached with
[fanotify_mark.md](fanotify_mark.md); events are consumed by `read(2)` and,
for permission events, answered by writing decisions back to the descriptor.
Requires `CAP_SYS_ADMIN`. Per-user limit: 128 fanotify groups (not
overridable).

## Synopsis

    #include <sys/fanotify.h>
    int fanotify_init(unsigned int flags, unsigned int event_f_flags);

## Arguments and behavior

`flags` must contain exactly one notification class: `FAN_CLASS_NOTIF`
(default; notification only), `FAN_CLASS_CONTENT` (access plus permission
events for final-content readers, e.g. malware scanners) or
`FAN_CLASS_PRE_CONTENT` (same, for listeners that must see files before their
final data). Class ordering when multiple listeners exist:
`FAN_CLASS_PRE_CONTENT`, then `FAN_CLASS_CONTENT`, then `FAN_CLASS_NOTIF`.
`event_f_flags` sets the status flags of the open file descriptions created
for events: access mode `O_RDONLY` / `O_WRONLY` / `O_RDWR` plus useful bits
`O_LARGEFILE`, `O_APPEND`, `O_DSYNC`, `O_NOATIME`, `O_NONBLOCK`, `O_SYNC`,
and `O_CLOEXEC` (since 3.18); any other flag yields `EINVAL`.

## Return value and errors

Returns the new file descriptor on success, -1 on error: `EINVAL` (invalid
`flags` or `event_f_flags`), `EMFILE` (128-group limit or per-process fd
limit), `ENOMEM`, `ENOSYS` (kernel without `CONFIG_FANOTIFY`), `EPERM`
(missing `CAP_SYS_ADMIN`).

## Flags and constants

| Constant | Meaning | Since |
|---|---|---|
| `FAN_CLOEXEC` | Set close-on-exec on the returned fd | header |
| `FAN_NONBLOCK` | Set `O_NONBLOCK` (reads give `EAGAIN` when empty) | header |
| `FAN_UNLIMITED_QUEUE` | Drop the 16384-event queue limit (needs `CAP_SYS_ADMIN`) | header |
| `FAN_UNLIMITED_MARKS` | Drop the 8192-mark limit (needs `CAP_SYS_ADMIN`) | header |
| `FAN_REPORT_TID` | Report TID instead of PID in event metadata | 4.20 |
| `FAN_ENABLE_AUDIT` | Enable audit records for permission decisions | 4.15 |
| `FAN_REPORT_FID` | Identify objects by file handle records | 5.1 |
| `FAN_REPORT_DIR_FID` | Add a parent-directory file handle record | 5.9 |
| `FAN_REPORT_NAME` | Add directory-entry name records (requires `FAN_REPORT_DIR_FID`) | 5.9 |
| `FAN_REPORT_DFID_NAME` | Synonym for `FAN_REPORT_DIR_FID` combined with `FAN_REPORT_NAME` | header |

`FAN_ALL_INIT_FLAGS` (all allowable bits) is deprecated since 4.20. The
file-handle reporting flags conflict with `FAN_CLASS_CONTENT` /
`FAN_CLASS_PRE_CONTENT` (`EINVAL`).

## Security and notes

Bug history (man BUGS): before 3.18 `O_CLOEXEC` in `event_f_flags` was
ignored; before 3.14 `event_f_flags` was not validated (`FMODE_EXEC` could
leak through). Marks and the `FAN_*` event bits: [fanotify_mark.md](fanotify_mark.md).
Lightweight unprivileged watching is inotify: [inotify_init.md](inotify_init.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/fanotify_init.2`
- Online: https://man7.org/linux/man-pages/man2/fanotify_init.2.html
- Constants: `/usr/include/x86_64-linux-gnu/sys/fanotify.h`, `linux/fanotify.h`
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (300)
