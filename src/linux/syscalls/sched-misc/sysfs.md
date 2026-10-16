# sysfs(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 139 / 135 / -- / 135 |
| Since (kernel) | 1.2 |
| Man page | man2/sysfs.2 (man-pages 6.19 HTML set, fetched 2026-10-17); the page warns up front: "if you are looking for information about the sysfs filesystem that is normally mounted at /sys, see sysfs(5)" |
| glibc wrapper | none -- "There is no libc or glibc support" (sysfs.2, BUGS); invoke via syscall(2) |
| Aliases covered | none |
| Ledger ID | SC-sysfs |

## Purpose

The obsolete sysfs() system call returned filesystem-type information: translate a filesystem name to its index, an index to its name, or count the registered filesystem types (sysfs.2, DESCRIPTION). It is the SVr4-era introspection call that /proc/filesystems replaced, and shares only a name with today's /sys sysfs(5) filesystem.

## Synopsis

```c
[[deprecated]] int sysfs(int option, const char *fsname);
[[deprecated]] int sysfs(int option, unsigned int fs_index, char *buf);
[[deprecated]] int sysfs(int option);
```

## Arguments and behavior

`option` 1 translates the filesystem identifier string `fsname` into a type index; option 2 writes the identifier for `fs_index` into `buf` (the man page warns there is no way to guess how large buf should be); option 3 returns the total number of registered filesystem types (sysfs.2, DESCRIPTION). The same information today: read /proc/filesystems, or statfs(2)'s f_type for a mounted instance (see [statfs](../descriptors-io/statfs.md)).

## Return value and errors

The filesystem index (option 1), 0 (option 2), or the configured-filesystem count (option 3) on success; -1 with errno (sysfs.2, RETURN VALUE). Errors: EFAULT (fsname/buf outside address space), EINVAL (bad name, out-of-bounds index, invalid option) (sysfs.2, ERRORS).

## Flags and constants

None.

## Security and notes

The man page's verdict: "This System-V derived system call is obsolete; don't use it. On systems with /proc, the same information can be obtained via /proc; use that interface instead" (sysfs.2, HISTORY). Interview angle: sysfs(2) vs sysfs(5) is a naming-collision trap question; the syscall's information lives in /proc/filesystems, the pseudo-filesystem in /sys is a different thing entirely. Cross-reference: [statfs](../descriptors-io/statfs.md), [ustat](ustat.md), [sysctl](sysctl.md).

## References

- https://man7.org/linux/man-pages/man2/sysfs.2.html
- man-pages syscalls(2)
