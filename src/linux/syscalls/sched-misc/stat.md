# oldstat(2) / oldfstat(2) / oldlstat(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | oldstat -- / 18 / -- / --; oldfstat -- / 28 / -- / --; oldlstat -- / 84 / -- / -- |
| Since (kernel) | 1.0 (the original i386 stat slots, superseded within the 1.x series) |
| Man page | man2/oldstat.2, man2/oldfstat.2 and man2/oldlstat.2 are one-line .so aliases into man2/stat.2 (fetched 2026-10-17) -- the modern stat(2) page, which does not document the dead slots' layouts |
| glibc wrapper | none for the dead slots (no oldstat/oldfstat/oldlstat symbols in glibc 2.41, nm -D); the stat(3) family wraps the modern entries ([stat](../descriptors-io/stat.md)) |
| Aliases covered | oldstat (SC-oldstat), oldfstat (SC-oldfstat), oldlstat (SC-oldlstat) |
| Ledger ID | SC-oldstat |

## Purpose

oldstat()/oldfstat()/oldlstat() are the original i386 file-status syscalls from Linux 1.0: the same stat/fstat/lstat contract as today (see [stat](../descriptors-io/stat.md)) but filling the 1.0-era `struct stat` layout. As the structure grew (larger inode/device/size fields and the 32-bit uid/gid work), Linux added replacement entries (the "newstat" family that x86_64 inherited as sys_stat/sys_fstat/sys_lstat) and kept the old slots for pre-existing i386 binaries only.

## Synopsis

```c
/* dead slots; no modern prototype exists */
long syscall(SYS_oldstat, const char *path,  struct old_stat *buf);
long syscall(SYS_oldfstat, unsigned int fd,  struct old_stat *buf);
long syscall(SYS_oldlstat, const char *path, struct old_stat *buf);
```

## Arguments and behavior

Path/descriptor selection matches the modern calls; the difference is the binary layout of the returned structure -- smaller ino_t/off_t fields and 16-bit uid/gid in the 1.0 layout, which is exactly what the newstat family widened (kernel fs/stat.c history; the man-page .so aliases point at stat.2 for the modern contract). Nothing new can be built against these slots: x86_64 and asm-generic have no such numbers (`--` columns), and the i386 slots exist only for 1.x-era executables.

## Return value and errors

Same shape as the modern calls: 0 on success, -1 with errno on error; the errors follow the modern stat(2) set (stat.2, ERRORS, via the .so alias).

## Flags and constants

None.

## Security and notes

Why keep three dead slots? The same ABI-stability rule as the [unimplemented](unimplemented.md) set: i386 binaries from 1991-1994 would break if the numbers were reassigned. Interview angle: the oldstat -> newstat -> stat64 -> statx (see [statx](../descriptors-io/statx.md)) progression is the canonical example of struct-stat layout churn driving syscall-number churn. This page is source-limited: the man pages for the slots are .so aliases that document only the modern calls; the old-layout claims rest on the kernel's stat.c history rather than a dedicated man page.

## References

- https://man7.org/linux/man-pages/man2/stat.2.html (oldstat.2/oldfstat.2/oldlstat.2 .so alias target)
- https://man7.org/linux/man-pages/man2/statx.2.html (modern successor)
- worklog: no oldstat/oldfstat/oldlstat symbols in glibc 2.41 (nm -D, 2026-10-17)
