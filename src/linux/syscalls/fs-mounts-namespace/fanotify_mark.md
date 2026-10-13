# fanotify_mark(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | x64 301 / i386 339 / arm64-generic 263 / arm32 368 |
| Since (kernel) | 2.6.37 (introduced 2.6.36, enabled 2.6.37; man VERSIONS; hub 2.6.37) |
| Man page | man2/fanotify_mark.2 (cached, 2021-08-27) |
| glibc wrapper | Yes; `<sys/fanotify.h>` |
| Aliases covered | none |
| Ledger ID | SC-fanotify_mark |

## Purpose

`fanotify_mark()` adds, removes, or modifies a fanotify mark on a filesystem
object: a file, a directory, a whole mount, or a whole filesystem. Marks
select which events from the group created by
[fanotify_init.md](fanotify_init.md) are delivered for the object. The caller
must have read permission on the object being marked.

## Synopsis

    #include <sys/fanotify.h>
    int fanotify_mark(int fanotify_fd, unsigned int flags, uint64_t mask,
                      int dirfd, const char *pathname);

## Arguments and behavior

`flags` must contain exactly one of `FAN_MARK_ADD` / `FAN_MARK_REMOVE`
(`mask` must be nonempty) or `FAN_MARK_FLUSH` (drop all marks of one scope:
mounts with `FAN_MARK_MOUNT`, filesystems with `FAN_MARK_FILESYSTEM`, else
directories and files; `mask` ignored). Optional modifiers: `FAN_MARK_DONT_FOLLOW`
(mark the symlink itself), `FAN_MARK_ONLYDIR` (`ENOTDIR` otherwise),
`FAN_MARK_MOUNT` (mark the mount containing `pathname` -- all directories,
subdirectories and files on that mount), `FAN_MARK_FILESYSTEM` (since 4.20;
mark the whole filesystem across all mount points), `FAN_MARK_IGNORED_MASK`
and `FAN_MARK_IGNORED_SURV_MODIFY` (an ignore mask that survives modify
events; without it the ignore mask clears on the first modify). The object is
resolved with `dirfd`/`pathname` in the usual `*at()` style, except that
`pathname` may be NULL, in which case `dirfd` names the object directly.

## Return value and errors

Returns 0 on success, -1 on error: `EBADF`, `EINVAL` (bad `flags`/`mask`;
permission-event masks on a `FAN_CLASS_NOTIF` group or file-handle group),
`ENODEV` (filesystem without `fsid`, file-handle groups), `ENOENT` (object
missing, or removing a nonexistent mark), `ENOMEM`, `ENOSPC` (8192-mark
limit without `FAN_UNLIMITED_MARKS`), `ENOSYS` (no `CONFIG_FANOTIFY`),
`ENOTDIR`, `EOPNOTSUPP` (filesystem cannot encode file handles), `EXDEV`
(btrfs subvolume with a different `fsid`, file-handle groups).

## Flags and constants (event mask bits)

| Constant | Meaning | Since |
|---|---|---|
| `FAN_ACCESS` | File/dir was read | header |
| `FAN_MODIFY` | File data changed | header |
| `FAN_CLOSE_WRITE` / `FAN_CLOSE_NOWRITE` | Close after write / read-only close | header |
| `FAN_OPEN` | Open | header |
| `FAN_OPEN_EXEC` | Open for execution | 5.0 |
| `FAN_ATTRIB`, `FAN_CREATE`, `FAN_DELETE`, `FAN_DELETE_SELF` | Metadata/create/delete events (file-handle groups) | 5.1 |
| `FAN_MOVED_FROM`, `FAN_MOVED_TO`, `FAN_MOVE_SELF` | Move events (file-handle groups) | 5.1 |
| `FAN_OPEN_PERM`, `FAN_ACCESS_PERM`, `FAN_OPEN_EXEC_PERM` | Permission-request events (need CONTENT or PRE_CONTENT class) | header / 5.0 |
| `FAN_ONDIR` | Also deliver events for directories (needed for mkdir/rmdir entry events) | header |
| `FAN_EVENT_ON_CHILD` | Events for immediate children of a marked directory | header |
| `FAN_CLOSE` | Composed: `FAN_CLOSE_WRITE` plus `FAN_CLOSE_NOWRITE` | header |
| `FAN_MOVE` | Composed: `FAN_MOVED_FROM` plus `FAN_MOVED_TO` | header |

## Security and notes

Mark scoping: inode marks fire only on that object; mount marks fire for the
entire mount; filesystem marks fire across every mount of the superblock.
File-handle-required events (`FAN_ATTRIB`, `FAN_CREATE`, `FAN_DELETE`,
`FAN_MOVE*`, `FAN_DELETE_SELF`) cannot be used with `FAN_MARK_MOUNT`
(`EINVAL`). `FAN_OPEN_EXEC*` fires only for direct `execve(2)`/`execveat(2)`
opens, not for interpreter-script reads; the dynamic linker gets its own
event. Before 3.16, `FAN_MARK_FLUSH` still demanded a valid object and
`readdir(2)` did not raise `FAN_ACCESS` (man BUGS). Unprivileged alternative:
[inotify_add_watch.md](inotify_add_watch.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/fanotify_mark.2`
- Online: https://man7.org/linux/man-pages/man2/fanotify_mark.2.html
- Constants: `/usr/include/x86_64-linux-gnu/sys/fanotify.h`, `linux/fanotify.h`
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (301)
