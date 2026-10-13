# lsm_get_self_attr(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | lsm_get_self_attr 459 / 459 / 459 / 459; lsm_set_self_attr 460 / 460 / 460 / 460; lsm_list_modules 461 / 461 / 461 / 461 (uniform "common" rows in the kernel tables; hub agrees) |
| Since (kernel) | 6.8: include/uapi/linux/lsm.h is absent at tag v6.7 and present at v6.8 (probed this session); hub/ledger Since columns show -- |
| Man page | None: man7.org has no lsm_get_self_attr.2 (HTTP 404 this session); sources are the kernel UAPI header and security/lsm_syscalls.c |
| glibc wrapper | None; constants in <linux/lsm.h> (installed glibc 2.41 headers ship it); no lsm_* symbol in libc (nm -D) |
| Aliases covered | lsm_set_self_attr, lsm_list_modules |
| Ledger ID | SC-lsm_get_self_attr, SC-lsm_set_self_attr, SC-lsm_list_modules |

Provenance note: this page is built from /usr/include/linux/lsm.h (installed), kernel include/uapi/linux/lsm.h and security/lsm_syscalls.c (fetched, source-cache/fetched/master-lsm-syscalls.c), and the 6.8 tag probe above. No man page exists for these calls.

## Purpose

The three calls are the syscall face of the Linux Security Module user-space API (6.8): they read and write the calling task's LSM attributes (security contexts such as the SELinux or AppArmor label) and enumerate active LSMs, replacing the per-LSM /proc/self/attr/* writes with a uniform, size-checked, fd-free interface. Every argument is a struct lsm_ctx: {__u64 id; __u64 flags; __u64 len; __u64 ctx_len; __u8 ctx[]}, where len covers the whole structure and ctx_len the context payload.

## Synopsis

```c
#include <linux/lsm.h>
int lsm_get_self_attr(unsigned int attr, struct lsm_ctx *ctx,
                      u32 *size, u32 flags);
int lsm_set_self_attr(unsigned int attr, struct lsm_ctx *ctx,
                      u32 size, u32 flags);
int lsm_list_modules(u64 *ids, u32 *size, u32 flags);
```

## Arguments and behavior

| Call | Behavior |
|---|---|
| lsm_get_self_attr | Fills ctx with the task's contexts for attr (LSM_ATTR_CURRENT 100, EXEC 101, FSCREATE 102, KEYCREATE 103, PREV 104, SOCKCREATE 105); returns the number of array elements (0 possible); LSM_FLAG_SINGLE (0x0001) restricts to the LSM named in the passed ctx; on short buffer returns E2BIG and writes the required size through size |
| lsm_set_self_attr | Sets the attribute from one lsm_ctx; runs under the cred_guard_mutex; flags reserved |
| lsm_list_modules | Fills ids with the active LSM ids (LSM_ID_CAPABILITY 100 through LSM_ID_IPE 113: SELINUX, SMACK, TOMOYO, APPARMOR, YAMA, LOADPIN, SAFESETID, LOCKDOWN, BPF, LANDLOCK, IMA, EVM, IPE); flags must be 0 |

## Return value and errors

Element count (possibly 0) on success for get/list; 0 for set. Errors follow the kernel-doc comments and security/security.c plumbing: E2BIG (insufficient *size, updated to the minimum), EFAULT, EINVAL (unknown attribute, nonzero reserved flags), EOPNOTSUPP/ENODATA for attributes the active LSMs do not provide (attribute support varies; none is required per the header).

## Flags and constants

LSM_FLAG_SINGLE is the only defined flag (installed header). Attribute ids and LSM ids share the 100+ numbering space but are separate namespaces.

## Security and notes

- Writing an attribute is the kernel-checked equivalent of writing /proc/self/attr/current; LSM-specific rules (relabeling permissions, for example) still apply inside each module.
- The proc filesystem remains the readable form: /proc/self/attr/current, /proc/self/attr/prev (SELinux and AppArmor), /proc/self/attr/sockcreate (SELinux), per Documentation/userspace-api/lsm.rst.

## References

- /usr/include/linux/lsm.h (struct lsm_ctx, LSM_ID_*, LSM_ATTR_*, LSM_FLAG_SINGLE).
- Kernel: include/uapi/linux/lsm.h, security/lsm_syscalls.c, Documentation/userspace-api/lsm.rst (source-cache/fetched/master-lsm-syscalls.c, master-lsm.rst); v6.7/v6.8 tag probe for the since value.
- [Syscalls ledger](../ledger.md) rows SC-lsm_get_self_attr, SC-lsm_set_self_attr, SC-lsm_list_modules.
