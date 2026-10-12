# getdents64(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | getdents64 217 / 220 / 61 / 217; getdents 78 / 141 / - / 141 (per-call table below) |
| Since (kernel) | getdents 2.0; getdents64 2.4 |
| Man page | man2/getdents.2 (getdents64.2 is an .so alias of it) |
| glibc wrapper | getdents() has never had a glibc wrapper -- syscall(2) only, and you must define struct linux_dirent yourself; getdents64() gained a glibc wrapper in 2.30 (host glibc 2.41 exports getdents64@@GLIBC_2.30, nm -D; man2/getdents.2 NOTES) |
| Aliases covered | getdents |
| Ledger ID | SC-getdents, SC-getdents64 |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables (syscall_64.tbl, syscall_32.tbl, syscall_arm.tbl, syscall_generic.tbl):

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| getdents | 78 | 141 | - | 141 | 2.0 |
| getdents64 | 217 | 220 | 61 | 217 | 2.4 |

getdents (the 32-bit-offset original) has no arm64-generic slot; getdents64 is the only directory-entry call there, and on modern systems the only one anyone should call. Layout note for the merge step: the domain hub groups both calls under getdents.md; task 3-c2 names this page getdents64.md, the same divergence the ledger row SC-getdents64 ("getdents64 entry") already records.

## Purpose

getdents() and getdents64() read directory entries in batches from the directory referred to by fd into caller's buffer dirp of size count. The man page opens with "These are not the interfaces you are interested in" -- readdir(3) is the POSIX-conforming interface. The two calls differ in field widths: getdents fills struct linux_dirent (unsigned long d_ino, d_off; unsigned short d_reclen; char d_name[]; with a d_type byte at the end of the record since 2.6.4); getdents64 fills struct linux_dirent64 with explicit 64-bit d_ino and d_off and a real d_type field, added in 2.4 because the original could not handle large filesystems and offsets. The kernel walks the directory as far as count allows and returns the number of bytes placed in the buffer; records are variable-length (d_reclen) and the caller iterates them; 0 means end of directory. The d_off values are the cookie an fd's directory stream can later be repositioned with (lseek.md SEEK_SET on the directory fd).

readdir(3) mapping (worklog 1-c, crossref XR-007): glibc's readdir(3) is implemented on top of getdents64 -- the library issues getdents64 into a private buffer in struct DIR and hands out one struct dirent at a time, which is why readdir(3) programs need no linux_dirent64 definition and why glibc's own getdents64() wrapper only appeared in 2.30 (before that, callers who wanted the raw syscall defined the struct and used syscall(2), as the man page instructs). readdir(2) -- the even older one-entry syscall -- is obsolete; both getdents calls supersede it (man2/getdents.2 NOTES, man2/readdir.2).

## Synopsis

```c
/* raw getdents: no glibc wrapper */
#include <sys/syscall.h>
#include <unistd.h>
long syscall(SYS_getdents, unsigned int fd, struct linux_dirent *dirp,
             unsigned int count);

/* getdents64: glibc wrapper since 2.30 */
#define _GNU_SOURCE
#include <dirent.h>
ssize_t getdents64(int fd, void *dirp, size_t count);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| fd | Descriptor for the directory (open with O_DIRECTORY to refuse non-directories at open time); a non-directory fd fails ENOTDIR. |
| dirp | Buffer receiving packed variable-length linux_dirent / linux_dirent64 records; the caller advances record by record via d_reclen. |
| count | Buffer size in bytes; must be large enough for at least one record or EINVAL. |

linux_dirent64 fields: ino64_t d_ino, off64_t d_off (cookie to the next record), unsigned short d_reclen, unsigned char d_type, char d_name[] (NUL-terminated). d_type values are the DT_* constants from <dirent.h> (enum under __USE_MISC in /usr/include/dirent.h): DT_UNKNOWN 0, DT_FIFO 1, DT_CHR 2, DT_DIR 4, DT_BLK 6, DT_REG 8, DT_LNK 10, DT_SOCK 12. d_type arrived in 2.6.4 (before that the byte reads 0 = DT_UNKNOWN); only some filesystems return real types (Btrfs, ext2/3/4 named in the man page), so applications must handle DT_UNKNOWN by falling back to stat().

## Return value and errors

Success returns the number of bytes read; 0 at end of directory. On error, -1 and errno: EBADF (bad fd), EFAULT (dirp outside the address space), EINVAL (result buffer too small), ENOENT (no such directory), ENOTDIR (fd does not refer to a directory).

## Flags and constants

No flags argument. The DT_* type constants are tabled above; IFTODT()/DTTOIF() macros in <dirent.h> convert between d_type and st_mode types.

## Security and notes

- Use readdir(3) (or scandir(3)/fts(3)) unless you specifically need batch semantics; the raw interface makes you parse d_reclen records yourself and define structures glibc does not export.
- d_off is an opaque cookie for later repositioning via lseek() on the directory fd, not a byte offset you can compute with.
- DT_UNKNOWN is a first-class answer, not an error: filesystems without d_type support always return it (man2/getdents.2).
- The buffer must hold at least one full record; an EINVAL from count being too small is the usual misuse bug.
- Directory enumeration races with concurrent modifications just like readdir(3): entries may appear, disappear, or repeat across calls.

## References

- man2/getdents.2 in the cached man-pages tree (dated 2021-03-22); .so alias getdents64.2; man2/readdir.2 for the superseded one-entry syscall.
- Constants: /usr/include/dirent.h (DT_* enum, IFTODT/DTTOIF).
- [Syscalls ledger](../ledger.md) rows SC-getdents, SC-getdents64; crossref XR-007 (readdir(3) -> getdents64) in src/linux/crossref/ledger.md; siblings [lseek](lseek.md), [open](open.md); [domain hub](overview.md).
