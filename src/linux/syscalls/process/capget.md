# capget(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 125 / 184 / 90 / 184 |
| Since (kernel) | 2.2 |
| Man page | man2/capget.2 (cached roff, dated 2021-03-22, covers both calls); man2/capset.2 is a one-line .so alias to capget.2 |
| glibc wrapper | cached man page: "glibc provides no wrappers for these system calls, necessitating the use of syscall(2)"; however nm -D on glibc 2.41 exports capget/capset @@GLIBC_2.2.5 (undocumented T symbols) -- use libcap or syscall(2) either way |
| Aliases covered | capset (126 / 185 / 91 / 185, SC-capset) |
| Ledger ID | SC-capget |

## Purpose

capget() and capset() are the raw kernel interface for reading and setting the capabilities of a thread -- the effective, permitted, and inheritable capability sets that supersede all-or-nothing root privilege checks.

## Synopsis

```c
#include <linux/capability.h>   /* sys/capability.h absent on this host */
#include <sys/syscall.h>
#include <unistd.h>
int syscall(SYS_capget, cap_user_header_t hdrp, cap_user_data_t datap);
int syscall(SYS_capset, cap_user_header_t hdrp, const cap_user_data_t datap);
```

## Arguments and behavior

Both calls take a version/pid header and a data array (capget.2, Current details). The header is struct __user_cap_header_struct { __u32 version; int pid; }; the data is an array of struct __user_cap_data_struct { __u32 effective; __u32 permitted; __u32 inheritable; }, bit masks of CAP_* values -- the header constants are bit indexes and must be shifted before ORing. Versioning: V1 0x19980330 (1 u32 per set); V2 0x20071026 added 64-bit sets in 2.6.25 but was deprecated for an API glitch; V3 0x20080522 (2 u32s per set, datap[0] and datap[1]) fixed it in 2.6.26. On an unsupported version the kernel fails with EINVAL after writing its preferred version into hdrp->version -- the documented probe. capget() may target any process via hdrp->pid. The structs come from /usr/include/linux/capability.h, which also carries the VFS_CAP_* file-capability xattr definitions.

## Return value and errors

0 on success, -1 with errno (capget.2, RETURN VALUE). Errors: EFAULT, bad address; hdrp must not be NULL, and datap may be NULL only when probing the preferred version; EINVAL, invalid argument, including an unsupported version; EPERM, adding a capability not in the permitted set, adding to the inheritable set a capability absent from the bounding set (or lacking CAP_SETPCAP), or targeting another thread without privilege; ESRCH, no such thread.

## Flags and constants

Version constants above (linux/capability.h). CAP_SETPCAP is 8, CAP_SETUID 7, CAP_SETGID 6, CAP_SYS_PTRACE 19, CAP_SYS_PACCT 20, CAP_SYS_ADMIN 21 (linux/capability.h).

## Security and notes

VFS (file) capabilities -- an xattr on executables, optional in 2.6.24 and fixed in 2.6.33 -- obsolete async cross-thread capset(): on kernels with VFS capability support the only permitted hdrp->pid values are 0 or gettid(2) (capget.2, With VFS capabilities support). Without VFS support, a CAP_SETPCAP caller could change other threads' sets, with pid -1 meaning all threads except the caller and init(1), and pid < -1 meaning process group -pid; a pre-2.6.11 bug made self-targeting via a nonzero pid fail (capget.2, Without VFS capabilities support). The portable interface is libcap's cap_get_proc(3)/cap_set_proc(3) (capget.2, NOTES). Background: [linux-capabilities](../../kernel/security/linux-capabilities.md). Cross-reference: [prctl](prctl.md), [getpid](getpid.md).

## References

- https://man7.org/linux/man-pages/man2/capget.2.html
- /usr/include/linux/capability.h (versions, struct definitions, CAP_* values)
- worklog Task 1-a (capget+capset grouped entry)
